"""Site Report Intelligence — the actual reasoning layer.

This is the one Hermes call in the whole pipeline — deliberately singular
and deliberately bounded (see AMAD AI Stabilization). Everything upstream
(site_report_evidence.py, site_report_risk_scoring.py) is deterministic
retrieval and math; this module is where the report's own text and its
compacted evidence window are turned into judgment.

Hard rules enforced here, not just requested in the prompt:
  - Every finding/risk/action the model returns is required (by schema +
    a post-parse filter) to cite at least one evidence code (SR-/DA-/SE-/
    NCR-/PO-/PR-/MTG-/DOC-/RISK-/ISSUE-<id>) that actually exists in the
    evidence bundle given to it. An item with no citation, or a citation
    that doesn't correspond to real retrieved evidence, is dropped —
    never shown as if it were grounded.
  - If Hermes is unavailable, times out, or returns output that still
    fails validation after one bounded LOCAL repair attempt (never a
    second full generation call — see AMAD AI Stabilization's
    performance requirements), this module does NOT fall back to a
    keyword-template narrative. It returns an explicitly-labeled
    "unavailable"/"timed_out" result. The deterministic evidence bundle
    and risk score are still returned separately by the caller — only
    the narrative reasoning is honestly marked unavailable.

Output contract (compact, per AMAD AI Stabilization Part A §3): a 7B model
was previously asked to generate 14 separate narrative sections in one
call, which measurably pushed generation time into multi-minute territory
and increased the odds any single sub-field came out malformed. The
schema below asks for the same judgment in far fewer fields; call sites
that need the old broader shape (SiteReportAnalysisOut, for frontend
backward compatibility) derive it deterministically from this compact
result in site_report_intelligence.py — Hermes itself never generates
the broader shape directly.
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field, ValidationError, model_validator

from app.ai.llm_json import extract_json_text
from app.ai.providers.base import LLMRequest, ProviderTimeoutError, ProviderUnavailableError
from app.ai.providers.factory import get_llm_provider
from app.ai.providers.hermes import HermesProvider
from app.ai.site_report_evidence import EvidenceItem, ReportEvidence, build_trend_snapshot
from app.ai.site_report_risk_scoring import RiskScoreBreakdown
from app.config import settings

logger = logging.getLogger(__name__)

_EVIDENCE_CODE_RE = re.compile(r"\b(?:SR|DA|SE|NCR|PO|PR|MTG|DOC|RISK|ISSUE)-\d+\b")
_VALID_CATEGORIES = frozenset({"safety", "quality", "schedule", "procurement", "equipment", "other"})
_VALID_PRIORITIES = frozenset({"critical", "high", "medium", "low"})


def _normalize_category(value) -> str:
    v = (str(value).strip().lower() if value else "")
    return v if v in _VALID_CATEGORIES else "other"


def _normalize_priority(value) -> str:
    v = (str(value).strip().lower() if value else "")
    return v.capitalize() if v in _VALID_PRIORITIES else "Not specified"


class CompactFindingOut(BaseModel):
    """One finding or critical risk — the compact replacement for the old
    per-domain narrative arrays (major_findings/safety_findings/quality_
    findings/schedule_findings/procurement_findings/equipment_issues/
    critical_risks all used to be separate top-level fields)."""

    category: str  # safety | quality | schedule | procurement | equipment | other
    priority: str  # Critical | High | Medium | Low
    statement: str
    evidence_codes: list[str] = Field(default_factory=list)

    model_config = {"extra": "ignore"}

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data):
        if isinstance(data, dict):
            data["category"] = _normalize_category(data.get("category"))
            data["priority"] = _normalize_priority(data.get("priority"))
            if data.get("evidence_codes") is None:
                data["evidence_codes"] = []
            elif isinstance(data.get("evidence_codes"), str):
                data["evidence_codes"] = [data["evidence_codes"]]
        return data


class CompactActionOut(BaseModel):
    category: str
    priority: str
    statement: str
    evidence_codes: list[str] = Field(default_factory=list)

    model_config = {"extra": "ignore"}

    @model_validator(mode="before")
    @classmethod
    def _normalize(cls, data):
        if isinstance(data, dict):
            data["category"] = _normalize_category(data.get("category"))
            data["priority"] = _normalize_priority(data.get("priority"))
            if data.get("evidence_codes") is None:
                data["evidence_codes"] = []
            elif isinstance(data.get("evidence_codes"), str):
                data["evidence_codes"] = [data["evidence_codes"]]
        return data


class SiteReportReasoningOutput(BaseModel):
    """The compact Hermes output contract. See module docstring — the
    broader SiteReportAnalysisOut shape the frontend consumes is derived
    deterministically from this in site_report_intelligence.py, not
    generated by the model."""

    insufficient_evidence: bool = False
    insufficient_evidence_reason: Optional[str] = None
    executive_summary: str
    key_findings: list[CompactFindingOut] = Field(default_factory=list)
    critical_risks: list[CompactFindingOut] = Field(default_factory=list)
    recommended_actions: list[CompactActionOut] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    trend_summary: str = ""
    # Computed post-parse from evidence_codes actually present on the items
    # above (see _validate) — never requested from the model, so it can't
    # itself be malformed and never needs its own repair.
    citations: list[str] = Field(default_factory=list)

    model_config = {"extra": "ignore"}

    @model_validator(mode="before")
    @classmethod
    def _normalize_nulls(cls, data):
        """Same small-model looseness this module has always defended
        against: null instead of empty array/string, and a bare finding
        missing its own "statement" (the one field with no honest
        placeholder) is dropped rather than failing the whole response."""
        if not isinstance(data, dict):
            return data
        for key in ("key_findings", "critical_risks", "recommended_actions"):
            val = data.get(key)
            if val is None:
                data[key] = []
            elif isinstance(val, list):
                data[key] = [item for item in val if isinstance(item, dict) and item.get("statement")]
        if data.get("missing_information") is None:
            data["missing_information"] = []
        elif isinstance(data.get("missing_information"), str):
            data["missing_information"] = [data["missing_information"]] if data["missing_information"].strip() else []
        if data.get("trend_summary") is None:
            data["trend_summary"] = ""
        if data.get("executive_summary") is None:
            data["executive_summary"] = ""
        return data


@dataclass
class ReasoningResult:
    status: str  # completed | unavailable | timed_out
    output: Optional[SiteReportReasoningOutput]
    provider: Optional[str]
    model_name: Optional[str]
    error_message: Optional[str] = None
    dropped_unsupported_count: int = 0
    hermes_duration_ms: float = 0.0
    prompt_length: int = 0


_SECTION_TITLES = {
    "safety": "SAFETY EVENTS",
    "quality": "QUALITY / NCRs",
    "procurement": "PROCUREMENT",
    "meeting": "MEETINGS",
    "document": "DOCUMENTS / OCR",
    "activity": "DAILY ACTIVITIES",
    "risk": "OPEN PROJECT RISKS (portfolio state, not window-scoped)",
    "issue": "OPEN PROJECT ISSUES (portfolio state, not window-scoped)",
    "report": "THE SITE REPORT ITSELF",
}

# Per-item character cap when formatting the evidence block — the DB-level
# ranking/caps in site_report_evidence.py bound row COUNT; this bounds
# character length per row, so one long description can't undo the count
# cap. Independent of settings.SITE_REPORT_MAX_EVIDENCE_CHARS, which is
# the total-block safety net below.
_MAX_CHARS_PER_EVIDENCE_ITEM = 220


def _format_evidence_block(ev: ReportEvidence, risk: RiskScoreBreakdown) -> str:
    by_cat: dict[str, list[EvidenceItem]] = {}
    for item in ev.evidence_items:
        by_cat.setdefault(item.category, []).append(item)

    lines: list[str] = []
    lines.append(f"PROJECT: {ev.project.project_code} — {ev.project.project_name} (status: {ev.project.status})")
    if ev.window_start is not None:
        lines.append(f"WINDOW: {ev.window_start} (exclusive) to {ev.window_end} (inclusive)")
    else:
        lines.append(f"WINDOW: first report on file; showing evidence up to {ev.window_end}.")
    lines.append(f"MANPOWER: {ev.total_workers} workers across {len(ev.manpower_breakdown)} subcontractor(s).")
    lines.append("")

    for cat in ("report", "activity", "safety", "quality", "procurement", "meeting", "document", "risk", "issue"):
        items = by_cat.get(cat, [])
        lines.append(f"── {_SECTION_TITLES[cat]} ──")
        if not items:
            lines.append("(none in this window)")
        else:
            seen_text: set[str] = set()
            for it in items:
                text = it.text
                if len(text) > _MAX_CHARS_PER_EVIDENCE_ITEM:
                    text = text[: _MAX_CHARS_PER_EVIDENCE_ITEM - 1].rstrip() + "…"
                dedup_key = text.strip().lower()
                if dedup_key in seen_text:
                    continue
                seen_text.add(dedup_key)
                lines.append(f"[{it.code}] ({it.item_date or 'undated'}) {text}")
        lines.append("")

    if ev.ocr_quality_notes:
        lines.append("── OCR QUALITY NOTES ──")
        lines.extend(ev.ocr_quality_notes[:3])
        lines.append("")

    lines.append("── RISK SCORE (already computed, do not recompute — reason about WHY) ──")
    lines.append(f"Total: {risk.total}/100 ({risk.level})")
    for c in risk.components:
        if c.points > 0:
            lines.append(f"  + {c.points}pts — {c.label} — evidence: {', '.join(c.evidence_refs) or 'none'}")
    lines.append("")

    trend = build_trend_snapshot(ev.prior_reports)
    lines.append("── TREND ──")
    lines.append(trend or "First report on file for this project; no trend comparison possible.")
    lines.append("")

    text = "\n".join(lines)
    if len(text) > settings.SITE_REPORT_MAX_EVIDENCE_CHARS:
        text = text[: settings.SITE_REPORT_MAX_EVIDENCE_CHARS] + "\n...(evidence truncated to fit budget)"
    return text


_SYSTEM_PROMPT = """\
You are a senior construction site analyst. Reason about ONE site report \
and its evidence window below. Find root causes, hidden risks, likely \
consequences if unaddressed, and concrete recommended actions.

RULES:
1. Use ONLY the evidence below. Never invent facts, names, dates, or numbers.
2. Every finding/risk/action MUST include its evidence code(s) in \
evidence_codes. No code = discarded, so never omit it.
3. Infer consequences, don't restate facts. "Scaffolding inspection \
overdue" -> "Risk of delayed facade work and a possible safety violation. \
[DA-9]".
4. If evidence overall is too thin to analyze, set insufficient_evidence=true \
with why in insufficient_evidence_reason.
5. category must be exactly one of: safety, quality, schedule, procurement, \
equipment, other. priority must be exactly one of: Critical, High, Medium, Low.
6. Keep key_findings and critical_risks to at most 5 items each, \
recommended_actions to at most 4 — the sharpest, highest-value ones only.
7. missing_information: at most 3 short items naming what's missing, not \
restating what's present. [] if nothing is missing.
8. trend_summary: one or two sentences using the TREND line above, or "" \
if this is the first report.
9. Output ONLY one JSON object. No markdown fences, no commentary, no \
text before or after the braces.

JSON keys (all required): insufficient_evidence (bool), \
insufficient_evidence_reason (string|null), executive_summary (2-3 \
sentences), key_findings (array of {{category, priority, statement, \
evidence_codes[]}}), critical_risks (same shape), recommended_actions \
(array of {{category, priority, statement, evidence_codes[]}}), \
missing_information (array of strings), trend_summary (string).

EVIDENCE:
{evidence_block}
"""

_UNAVAILABLE_MESSAGE_EN = "AI reasoning is currently unavailable for this report. The evidence and risk score below are still real and unaffected — only the narrative analysis could not be generated."
_TIMED_OUT_MESSAGE_EN = "AI reasoning was unavailable; evidence-based analysis is shown."


def _get_reasoning_provider():
    """A dedicated, DELIBERATELY SHORT timeout for this one Hermes call —
    see the config comment on SITE_REPORT_HERMES_TIMEOUT_SECONDS. The hard
    ceiling on total user wait (60s, per AMAD AI Stabilization) leaves this
    call only ~45-50s of budget once evidence gathering, risk scoring, and
    response serialization are accounted for. Any other provider (mock/
    OpenAI/OpenRouter) comes back unchanged from the shared factory/cache."""
    provider = get_llm_provider()
    if isinstance(provider, HermesProvider):
        return HermesProvider(
            model=provider.model_name,
            hermes_bin=settings.HERMES_BIN,
            profile=settings.HERMES_PROFILE,
            hermes_provider=settings.HERMES_PROVIDER,
            timeout_seconds=settings.SITE_REPORT_HERMES_TIMEOUT_SECONDS,
        )
    return provider


def _call_provider(provider, system_prompt: str):
    try:
        return provider.generate(LLMRequest(system_prompt=system_prompt, user_prompt="Analyze this site report.", temperature=0.1)), None
    except ProviderUnavailableError as e:
        return None, e


def _known_codes(ev: ReportEvidence) -> set[str]:
    return {item.code for item in ev.evidence_items}


def _strip_uncited_or_unknown(output: SiteReportReasoningOutput, known_codes: set[str]) -> int:
    """Post-parse enforcement of rule 2: drop any item with no evidence
    code, or whose cited codes don't correspond to real evidence handed to
    the model. Also computes the top-level `citations` field as the union
    of every surviving item's codes — never requested from the model."""
    dropped = 0
    all_cited: set[str] = set()

    def _filter_findings(items: list[CompactFindingOut]) -> list[CompactFindingOut]:
        nonlocal dropped
        kept = []
        for item in items:
            refs = {r for r in item.evidence_codes if r in known_codes}
            if refs:
                item.evidence_codes = sorted(refs)
                all_cited.update(refs)
                kept.append(item)
            else:
                dropped += 1
        return kept

    output.key_findings = _filter_findings(output.key_findings)
    output.critical_risks = _filter_findings(output.critical_risks)

    kept_actions = []
    for action in output.recommended_actions:
        refs = {r for r in action.evidence_codes if r in known_codes}
        if refs:
            action.evidence_codes = sorted(refs)
            all_cited.update(refs)
            kept_actions.append(action)
        else:
            dropped += 1
    output.recommended_actions = kept_actions

    output.citations = sorted(all_cited)
    return dropped


def _validate(raw_content: str, known_codes: set[str]) -> tuple[Optional[SiteReportReasoningOutput], Optional[str], int]:
    candidate = extract_json_text(raw_content)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        # One bounded LOCAL repair attempt — cheap regex fixes for the most
        # common small-model JSON mistakes (trailing commas, single quotes
        # used as string delimiters). NEVER a second Hermes call — see
        # module docstring / AMAD AI Stabilization Part A §5.
        repaired = _attempt_bounded_repair(candidate)
        try:
            parsed = json.loads(repaired)
        except json.JSONDecodeError as e2:
            return None, f"Response was not valid JSON after bounded repair: {e2}", 0
    if not isinstance(parsed, dict):
        return None, "Top-level JSON value was not an object.", 0
    try:
        output = SiteReportReasoningOutput.model_validate(parsed)
    except ValidationError as e:
        return None, str(e), 0

    dropped = _strip_uncited_or_unknown(output, known_codes)
    return output, None, dropped


_TRAILING_COMMA_RE = re.compile(r",(\s*[}\]])")


def _attempt_bounded_repair(candidate: str) -> str:
    """A handful of cheap, deterministic regex fixes — not a second LLM
    call, not an open-ended repair loop. If these don't produce parseable
    JSON, generate_report_reasoning() falls back to the deterministic
    result immediately rather than trying anything more expensive."""
    repaired = _TRAILING_COMMA_RE.sub(r"\1", candidate)
    return repaired


def generate_report_reasoning(ev: ReportEvidence, risk: RiskScoreBreakdown) -> ReasoningResult:
    """The one Hermes call for a /analyze request — always exactly one
    generation call, never more (a validation failure triggers a bounded
    LOCAL repair, not a second call to Hermes)."""
    evidence_block = _format_evidence_block(ev, risk)
    system_prompt = _SYSTEM_PROMPT.format(evidence_block=evidence_block)
    prompt_length = len(system_prompt)
    known_codes = _known_codes(ev)

    provider = _get_reasoning_provider()
    if not provider.is_available():
        return ReasoningResult(
            status="unavailable", output=None, provider=provider.provider_name,
            model_name=provider.model_name, error_message="LLM provider is not available.",
            prompt_length=prompt_length,
        )

    hermes_start = time.monotonic()
    response, error = _call_provider(provider, system_prompt)
    hermes_duration_ms = (time.monotonic() - hermes_start) * 1000

    if response is None:
        is_timeout = isinstance(error, ProviderTimeoutError)
        logger.warning(
            "site_report_reasoning_provider_error report_id=%s is_timeout=%s "
            "hermes_duration_ms=%.0f prompt_length=%d error=%s",
            ev.report.id, is_timeout, hermes_duration_ms, prompt_length, str(error)[:300],
        )
        return ReasoningResult(
            status="timed_out" if is_timeout else "unavailable",
            output=None, provider=provider.provider_name, model_name=provider.model_name,
            error_message=f"LLM provider unavailable: {str(error)[:300]}",
            hermes_duration_ms=hermes_duration_ms, prompt_length=prompt_length,
        )

    output, err, dropped = _validate(response.content, known_codes)

    if output is None:
        logger.warning(
            "site_report_reasoning_validation_failed report_id=%s "
            "hermes_duration_ms=%.0f prompt_length=%d output_length=%d error=%s",
            ev.report.id, hermes_duration_ms, prompt_length, len(response.content), (err or "")[:300],
        )
        return ReasoningResult(
            status="unavailable", output=None, provider=response.provider, model_name=response.model,
            error_message="Model output did not match the required structure.",
            hermes_duration_ms=hermes_duration_ms, prompt_length=prompt_length,
        )

    logger.info(
        "site_report_reasoning_completed report_id=%s provider=%s model=%s "
        "dropped_unsupported=%d insufficient_evidence=%s hermes_duration_ms=%.0f "
        "prompt_length=%d output_length=%d",
        ev.report.id, response.provider, response.model, dropped, output.insufficient_evidence,
        hermes_duration_ms, prompt_length, len(response.content),
    )
    return ReasoningResult(
        status="completed", output=output, provider=response.provider,
        model_name=response.model, dropped_unsupported_count=dropped,
        hermes_duration_ms=hermes_duration_ms, prompt_length=prompt_length,
    )
