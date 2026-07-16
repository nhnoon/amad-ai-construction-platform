"""Shared helpers for extracting a single JSON object out of raw LLM output.

Model output for a "respond with JSON" instruction is not always a bare
JSON document — it may be wrapped in a markdown code fence, preceded by a
sentence of preamble, or followed by trailing commentary. This module
isolates the JSON object precisely (brace-depth-aware, string-literal-safe)
rather than naively slicing from the first "{" to the last "}", which can
silently swallow trailing prose or merge two separate objects.

Extracted from the pattern already proven in app/ai/contract_extraction.py
so app/ai/site_report_reasoning.py can reuse it without duplicating the
parsing logic. contract_extraction.py itself is untouched — this module
does not change its behavior, only gives a second caller the same code.
"""
from __future__ import annotations

import re
from typing import Optional

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_balanced_json_object(text: str) -> Optional[str]:
    """Scan for the first balanced {...} object, respecting string
    literals (so a brace inside a quoted string can't confuse nesting
    depth). Returns None if no balanced object is found."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return None  # never balanced — let json.loads report the real error


def extract_json_text(raw: str) -> str:
    """Best-effort isolation of a JSON object from raw model output that may
    include markdown code fences and/or surrounding prose: strip fences
    first, then extract the first balanced {...} object."""
    text = raw.strip()
    fence_match = _JSON_FENCE_RE.search(text)
    if fence_match:
        text = fence_match.group(1).strip()
    balanced = extract_balanced_json_object(text)
    return balanced if balanced is not None else text
