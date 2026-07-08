"""Post-generation grounding validator.

Checks whether the generated answer is appropriately grounded in the
supplied evidence.  If the answer makes factual claims without evidence
support, returns is_grounded=False so the pipeline can return a controlled
fallback instead of unsupported claims.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from app.ai.retrieval.base import Evidence


@dataclass
class GroundingResult:
    is_grounded: bool
    reason: Optional[str] = None


_NUMBER_RE = re.compile(r"\b\d[\d,]*(?:\.\d+)?\b")

_SAFE_FALLBACK = (
    "I don't have sufficient evidence from the platform data to answer this "
    "question accurately. Please refine your question or check the relevant "
    "module directly."
)
_SAFE_FALLBACK_AR = (
    "لا تتوفر لديّ أدلة كافية من بيانات المنصة للإجابة على هذا السؤال بدقة. "
    "يُرجى تحسين سؤالك أو مراجعة الوحدة ذات الصلة مباشرةً."
)


class GroundingValidator:
    """Validates that the generated answer is grounded in supplied evidence."""

    def validate(
        self,
        question: str,
        answer: str,
        evidence: list[Evidence],
    ) -> GroundingResult:
        if not evidence:
            if self._contains_specific_claim(answer):
                return GroundingResult(
                    is_grounded=False,
                    reason="answer_without_evidence",
                )
            return GroundingResult(is_grounded=True)

        if self._is_insufficient_evidence_response(answer):
            return GroundingResult(is_grounded=True, reason="insufficient_evidence_acknowledged")

        answer_numbers = set(_NUMBER_RE.findall(answer.replace(",", "")))
        evidence_text = " ".join(e.snippet for e in evidence).replace(",", "")
        evidence_numbers = set(_NUMBER_RE.findall(evidence_text))

        unsupported = answer_numbers - evidence_numbers
        suspicious = {n for n in unsupported if len(n) >= 4 and int(n.split(".")[0]) > 99}

        if len(suspicious) > 3:
            return GroundingResult(
                is_grounded=False,
                reason="ungrounded_numerical_claims",
            )

        return GroundingResult(is_grounded=True)

    @staticmethod
    def _contains_specific_claim(text: str) -> bool:
        numbers = _NUMBER_RE.findall(text.replace(",", ""))
        significant = [n for n in numbers if len(n) >= 3 and int(n.split(".")[0]) > 9]
        return len(significant) >= 1

    @staticmethod
    def _is_insufficient_evidence_response(text: str) -> bool:
        markers = [
            "don't have sufficient",
            "insufficient evidence",
            "no data",
            "لا تتوفر",
            "cannot find",
            "no information",
            "no records",
        ]
        lower = text.lower()
        return any(m in lower for m in markers)

    @staticmethod
    def fallback_response(is_arabic: bool = False) -> str:
        return _SAFE_FALLBACK_AR if is_arabic else _SAFE_FALLBACK
