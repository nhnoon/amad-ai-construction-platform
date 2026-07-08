"""Deterministic FakeLLMProvider — used for tests and when no API key is set.

Behaviour
─────────
  1. If ``fixed_response`` is set, return it (test-injection).
  2. If ``simulate_unavailable`` is set, raise ProviderUnavailableError.
  3. Otherwise, parse the evidence block from the system prompt and build a
     concise, evidence-grounded summary so that:
     - grounding validation passes (answer tokens appear in evidence)
     - the answer is more useful than a generic template phrase
     - regression tests can assert specific values are present

Note: the pipeline's deterministic analytical layer (analyst.py) handles
specific analytical questions BEFORE calling any provider, so this provider
is only reached for general/synthesis questions and executive summaries.
"""
from __future__ import annotations

import re
import time
from typing import Optional

from .base import LLMRequest, LLMResponse, ProviderUnavailableError

_EVIDENCE_BLOCK_RE = re.compile(r"EVIDENCE:\s*(.+)", re.DOTALL)
_ITEM_RE = re.compile(r"\[\d+\]\s+(.+?)(?=\n\[\d+\]|\Z)", re.DOTALL)
# Grab the first label (before the snippet line)
_LABEL_RE = re.compile(r"^\s*(.+?)\n", re.DOTALL)


def _is_arabic(text: str) -> bool:
    """Return True if more than 20% of characters are Arabic script."""
    arabic = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    return arabic > len(text) * 0.2


class FakeLLMProvider:
    """Deterministic provider that returns configurable canned responses."""

    def __init__(
        self,
        fixed_response: Optional[str] = None,
        simulate_unavailable: bool = False,
    ) -> None:
        self._fixed_response = fixed_response
        self._simulate_unavailable = simulate_unavailable
        self._call_count: int = 0

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake-model-v1"

    def is_available(self) -> bool:
        return not self._simulate_unavailable

    def set_response(self, response: str) -> None:
        self._fixed_response = response

    @property
    def call_count(self) -> int:
        return self._call_count

    def generate(self, request: LLMRequest) -> LLMResponse:
        self._call_count += 1
        start = time.monotonic()
        content = self._build_response(request)
        latency = (time.monotonic() - start) * 1000
        return LLMResponse(
            content=content,
            model=self.model_name,
            provider=self.provider_name,
            prompt_tokens=len(request.system_prompt.split()) + len(request.user_prompt.split()),
            completion_tokens=len(content.split()),
            latency_ms=latency,
        )

    def _build_response(self, request: LLMRequest) -> str:
        if self._fixed_response is not None:
            return self._fixed_response

        # Extract evidence items from the system prompt
        evidence_match = _EVIDENCE_BLOCK_RE.search(request.system_prompt)
        if not evidence_match:
            return (
                "I can assist with construction project intelligence. "
                "Please ask about projects, procurement, safety, site reports, or meetings."
            )

        raw_block = evidence_match.group(1).strip()
        if raw_block == "[No evidence retrieved]" or not raw_block:
            return "INSUFFICIENT_EVIDENCE: No records were retrieved for this query."

        # Parse individual evidence items
        items = _ITEM_RE.findall(raw_block)
        if not items:
            items = [raw_block]

        # Build a grounded summary using the actual labels and snippets
        labels = []
        snippet_tokens: list[str] = []
        for item in items[:8]:
            lines = item.strip().splitlines()
            if lines:
                labels.append(lines[0].strip())
            for line in lines:
                snippet_tokens.extend(line.strip().split())

        count = len(items)
        is_ar = _is_arabic(request.user_prompt)

        # Detect dominant evidence type from labels
        is_safety = any("SE-" in l or "Safety" in l for l in labels)
        is_ncr = any("NCR-" in l for l in labels)
        is_project = any("Project PRJ-" in l or "PRJ-" in l for l in labels)
        is_procurement = any("PO-" in l or "PR-" in l or "Purchase" in l for l in labels)

        # Build a context-aware but evidence-grounded response
        if is_project:
            cited = " ".join(re.findall(r"PRJ-\d+", " ".join(labels))[:6])
            if is_ar:
                summary = (
                    f"بناءً على السجلات المسترجعة، {count} مشروع في النطاق: "
                    f"{', '.join(labels[:4])}. "
                    f"راجع {cited} للتفاصيل الكاملة."
                )
            else:
                summary = (
                    f"Based on the retrieved records, {count} project(s) are in scope: "
                    f"{', '.join(labels[:4])}. "
                    f"The data includes status, budget, client, and timeline information. "
                    f"Refer to {cited} for full details."
                )
        elif is_safety:
            cited = " ".join(re.findall(r"SE-\d+", " ".join(labels))[:6])
            if is_ar:
                summary = (
                    f"تم العثور على {count} حدث سلامة: "
                    f"{', '.join(labels[:4])}. "
                    f"راجع {cited} للتفاصيل."
                )
            else:
                summary = (
                    f"{count} safety event(s) found: "
                    f"{', '.join(labels[:4])}. "
                    f"Review {cited} for severity and corrective action details."
                )
        elif is_ncr:
            cited = " ".join(re.findall(r"NCR-\d+", " ".join(labels))[:6])
            if is_ar:
                summary = (
                    f"{count} طلب تصحيح مفتوح: "
                    f"{', '.join(labels[:4])}. "
                    f"راجع {cited} للتفاصيل."
                )
            else:
                summary = (
                    f"{count} open NCR(s) on record: "
                    f"{', '.join(labels[:4])}. "
                    f"See {cited} for type and corrective action status."
                )
        elif is_procurement:
            cited = " ".join(re.findall(r"(?:PO|PR)-[\w-]+", " ".join(labels))[:6])
            if is_ar:
                summary = (
                    f"تم العثور على {count} سجل مشتريات: "
                    f"{', '.join(labels[:4])}. "
                    f"راجع {cited} للتفاصيل."
                )
            else:
                summary = (
                    f"{count} procurement record(s) found: "
                    f"{', '.join(labels[:4])}. "
                    f"Check {cited} for value, status, and delivery details."
                )
        else:
            if is_ar:
                summary = (
                    f"تم العثور على {count} سجل: "
                    f"{', '.join(labels[:4])}. "
                    "راجع المصادر المذكورة للتفاصيل."
                )
            else:
                summary = (
                    f"{count} record(s) found: "
                    f"{', '.join(labels[:4])}. "
                    "Review the cited sources for full details."
                )

        return summary
