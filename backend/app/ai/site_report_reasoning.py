"""Site Report Intelligence — the actual reasoning layer.

This is the one Hermes call in the whole pipeline (see the performance
note at the bottom of this docstring). Everything upstream
(site_report_evidence.py, site_report_risk_scoring.py) is deterministic
retrieval and math; this module is where the report's own text and its
surrounding evidence are turned into judgment: root causes, hidden risks,
dependencies, likely consequences, blocked work, missing information,
contradictions, and evidence-grounded recommendations.

Hard rules enforced here, not just requested in the prompt:
  - Every finding/recommendation the model returns is required (by
    schema + a post-parse filter) to cite at least one evidence code
    (SR-/DA-/SE-/NCR-/PO-/PR-/MTG-/DOC-/RISK-/ISSUE-<id>) that actually
    exists in the evidence bundle given to it. A bullet with no citation,
    or a citation that doesn't correspond to real retrieved evidence, is
    dropped — never shown as if it were grounded.
  - If Hermes is unavailable, or returns output that still fails
    validation after one retry, this module does NOT fall back to a
    keyword-template narrative (the old implementation's entire design).
    It returns an explicitly-labeled "reasoning unavailable" result. The
    deterministic evidence bundle and risk score are still returned
    separately by the caller — only the narrative reasoning is honestly
    marked unavailable, never silently replaced by a rule engine dressed
    up as AI.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field, ValidationError, model_validator

from app.ai.llm_json import extract_json_text
from app.ai.providers.base import LLMRequest, ProviderUnavailableError
from app.ai.providers.factory import get_llm_provider
from app.ai.providers.hermes import HermesProvider
from app.ai.site_report_evidence import EvidenceItem, ReportEvidence
from app.ai.site_report_risk_scoring import RiskScoreBreakdown
from app.config import settings

logger = logging.getLogger(__name__)

_EVIDENCE_CODE_RE = re.compile(r"\b(?:SR|DA|SE|NCR|PO|PR|MTG|DOC|RISK|ISSUE)-\d+\b")

# String-array fields — a bare string here (instead of a 1-item array) is a
# common small-model looseness, not a real structural failure; coerced to
# [value] rather than rejected. Distinct from the object-array fields below
# (recommended_actions/priority_matrix), where a bare string can't be
# meaningfully coerced into a structured item and is left to fail validation.
_REASONING_STRING_LIST_FIELDS = (
    "major_findings", "safety_findings", "quality_findings", "schedule_findings",
    "procurement_findings", "equipment_issues", "blocked_activities", "critical_risks",
    "next_site_visit_focus", "questions_for_site_team", "contradictions",
)
_REASONING_OBJECT_LIST_FIELDS = ("recommended_actions", "priority_matrix")
_REASONING_STRING_FIELDS = ("weather_impact", "executive_summary")


def _stringify(value):
    """The model is instructed to use High/Medium/Low(/Critical) labels for
    priority/urgency/impact but occasionally substitutes a numeric scale
    instead. Coercing to str (rather than rejecting the response outright,
    or guessing an unstated number->label mapping) keeps an otherwise
    complete, well-reasoned analysis instead of discarding it over one
    field's format — and stays honest: the raw value is shown as-is rather
    than silently remapped to a label the model didn't actually choose."""
    if isinstance(value, (int, float)):
        return str(value)
    return value


class RecommendedActionOut(BaseModel):
    action: str
    priority: str  # Critical | High | Medium | Low
    # reason/expected_benefit are occasionally omitted entirely (not even
    # null — the key is just missing) on a long, multi-item
    # recommended_actions array, observed directly during benchmarking on a
    # richer report (28 evidence items). Defaulting to "" rather than
    # rejecting the whole action preserves the action/priority/evidence_refs
    # that ARE present instead of discarding a real, cited recommendation
    # over one incomplete sub-field.
    reason: str = ""
    evidence_refs: list[str] = Field(default_factory=list)
    expected_benefit: str = ""

    model_config = {"extra": "ignore"}

    @model_validator(mode="before")
    @classmethod
    def _normalize_nulls(cls, data):
        if isinstance(data, dict):
            if data.get("evidence_refs") is None:
                data["evidence_refs"] = []
            if data.get("reason") is None:
                data["reason"] = ""
            if data.get("expected_benefit") is None:
                data["expected_benefit"] = ""
            data["priority"] = _stringify(data.get("priority"))
        return data


class PriorityMatrixItemOut(BaseModel):
    item: str
    urgency: str  # High | Medium | Low
    impact: str  # High | Medium | Low
    evidence_refs: list[str] = Field(default_factory=list)

    model_config = {"extra": "ignore"}

    @model_validator(mode="before")
    @classmethod
    def _normalize_nulls(cls, data):
        if isinstance(data, dict):
            if data.get("evidence_refs") is None:
                data["evidence_refs"] = []
            data["urgency"] = _stringify(data.get("urgency"))
            data["impact"] = _stringify(data.get("impact"))
        return data


class TrendAnalysisOut(BaseModel):
    available: bool = False
    summary: Optional[str] = None
    signals: list[str] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


class SiteReportReasoningOutput(BaseModel):
    insufficient_evidence: bool = False
    insufficient_evidence_reason: Optional[str] = None
    ocr_quality_note: Optional[str] = None
    executive_summary: str
    major_findings: list[str] = Field(default_factory=list)
    safety_findings: list[str] = Field(default_factory=list)
    quality_findings: list[str] = Field(default_factory=list)
    schedule_findings: list[str] = Field(default_factory=list)
    procurement_findings: list[str] = Field(default_factory=list)
    equipment_issues: list[str] = Field(default_factory=list)
    weather_impact: str = ""
    blocked_activities: list[str] = Field(default_factory=list)
    critical_risks: list[str] = Field(default_factory=list)
    recommended_actions: list[RecommendedActionOut] = Field(default_factory=list)
    priority_matrix: list[PriorityMatrixItemOut] = Field(default_factory=list)
    next_site_visit_focus: list[str] = Field(default_factory=list)
    questions_for_site_team: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    trend_analysis: TrendAnalysisOut = Field(default_factory=TrendAnalysisOut)

    model_config = {"extra": "ignore"}

    @model_validator(mode="before")
    @classmethod
    def _normalize_nulls(cls, data):
        """Small local models are consistently loose about two things in
        this kind of structured output, neither of which reflects a failure
        to reason:
          - `null` for "nothing to report" instead of an empty string/array
            (even when explicitly told the field is required).
          - a bare string instead of a 1-item array when there's only one
            thing to say for a list field.
        Coercing both here keeps an otherwise complete, well-reasoned
        analysis instead of discarding the entire response over one field's
        shape — measured directly during implementation: real Hermes runs
        against real evidence produced correct, well-cited content but were
        being rejected on exactly these two patterns before this fix."""
        if not isinstance(data, dict):
            return data
        for key in _REASONING_STRING_LIST_FIELDS:
            val = data.get(key)
            if val is None:
                data[key] = []
            elif isinstance(val, str):
                data[key] = [val] if val.strip() else []
        for key in _REASONING_OBJECT_LIST_FIELDS:
            if data.get(key) is None:
                data[key] = []
        for key in _REASONING_STRING_FIELDS:
            if data.get(key) is None:
                data[key] = ""
        if data.get("trend_analysis") is None:
            data["trend_analysis"] = {"available": False, "summary": None, "signals": []}
        return data


@dataclass
class ReasoningResult:
    status: str  # completed | unavailable
    output: Optional[SiteReportReasoningOutput]
    provider: Optional[str]
    model_name: Optional[str]
    error_message: Optional[str] = None
    dropped_unsupported_count: int = 0


_SECTION_TITLES = {
    "safety": "SAFETY EVENTS (this report's evidence window)",
    "quality": "QUALITY / NCRs (this report's evidence window)",
    "procurement": "PROCUREMENT (this report's evidence window)",
    "meeting": "MEETINGS (this report's evidence window)",
    "document": "ATTACHED DOCUMENTS / OCR TEXT (date-correlated to this report)",
    "activity": "DAILY ACTIVITIES LOGGED AGAINST THIS REPORT",
    "risk": "OPEN PROJECT RISKS (current portfolio state, NOT window-scoped)",
    "issue": "OPEN PROJECT ISSUES (current portfolio state, NOT window-scoped)",
    "report": "THE SITE REPORT ITSELF",
}


def _format_evidence_block(ev: ReportEvidence, risk: RiskScoreBreakdown) -> str:
    by_cat: dict[str, list[EvidenceItem]] = {}
    for item in ev.evidence_items:
        by_cat.setdefault(item.category, []).append(item)

    lines: list[str] = []
    lines.append(f"PROJECT: {ev.project.project_code} — {ev.project.project_name} (status: {ev.project.status})")
    if ev.window_start is not None:
        lines.append(f"THIS REPORT'S EVIDENCE WINDOW: {ev.window_start} (exclusive) to {ev.window_end} (inclusive)")
    else:
        lines.append(
            f"THIS REPORT'S EVIDENCE WINDOW: no earlier report exists for this project; "
            f"showing evidence up to and including {ev.window_end} within the default lookback."
        )
    lines.append(f"MANPOWER: {ev.total_workers} workers across {len(ev.manpower_breakdown)} subcontractor(s).")
    lines.append("")

    for cat in ("report", "activity", "safety", "quality", "procurement", "meeting", "document", "risk", "issue"):
        items = by_cat.get(cat, [])
        lines.append(f"── {_SECTION_TITLES[cat]} ──")
        if not items:
            lines.append("(none in this window)")
        else:
            for it in items:
                lines.append(f"[{it.code}] ({it.item_date or 'undated'}) {it.text}")
        lines.append("")

    if ev.ocr_quality_notes:
        lines.append("── OCR QUALITY NOTES ──")
        lines.extend(ev.ocr_quality_notes)
        lines.append("")

    lines.append("── DETERMINISTIC RISK SCORE (already computed, do not recompute — reason about WHY it is what it is) ──")
    lines.append(f"Total: {risk.total}/100 ({risk.level})")
    for c in risk.components:
        if c.points > 0:
            lines.append(f"  + {c.points}pts — {c.label} (x{c.occurrences}) — evidence: {', '.join(c.evidence_refs) or 'none'}")
    lines.append("")

    if ev.prior_reports:
        lines.append("── PRIOR REPORTS FOR THIS PROJECT (for trend comparison) ──")
        for p in ev.prior_reports:
            lines.append(
                f"[SR-{p.report_id}] ({p.report_date}): {p.safety_event_count} safety event(s) "
                f"({p.critical_safety_count} critical/high), {p.open_ncr_count} open NCR(s), "
                f"{p.late_po_count} late PO(s), {p.blocked_activity_count} blocked activit(y/ies), "
                f"subcontractors on site: {sorted(p.subcontractor_ids)}"
            )
        lines.append("")
    else:
        lines.append("── PRIOR REPORTS FOR THIS PROJECT ──")
        lines.append("(none — this is the first report on file for this project; no trend comparison is possible)")
        lines.append("")

    text = "\n".join(lines)
    if len(text) > settings.SITE_REPORT_MAX_EVIDENCE_CHARS:
        text = text[: settings.SITE_REPORT_MAX_EVIDENCE_CHARS] + "\n...(evidence truncated to fit the model's context window)"
    return text


_SYSTEM_PROMPT = """\
You are a senior construction site analyst. Reason about ONE site report \
and its evidence window below — do not summarize it. For each relevant \
area: find root causes (not just what happened), hidden risks, \
dependencies, likely consequences if unaddressed, blocked work, missing \
information, and contradictions between evidence items. Then recommend \
concrete actions.

RULES:
1. Use ONLY the evidence below. Never invent facts, names, dates, or numbers.
2. Every finding/risk/recommendation MUST end with its evidence code(s) in \
brackets, e.g. "...before inspection closes. [DA-14, NCR-3]". No bracket = \
discarded, so never omit it.
3. Infer consequences, don't restate facts. "Scaffolding inspection \
overdue" -> "Risk of delayed facade work and a possible safety violation \
if scaffolding is used past its inspection window. [DA-9]".
4. Empty section = say so plainly (e.g. "No safety events in this \
window."), never invent content to fill it.
5. If evidence overall is too thin to analyze, set insufficient_evidence=true \
with why in insufficient_evidence_reason.
6. Low-confidence/failed OCR -> say so in ocr_quality_note; treat that \
document as uncertain.
7. trend_analysis.available=true ONLY if PRIOR REPORTS are listed below — \
name concrete signals (repeated/resolved/escalating/new issue, recurring \
contractor). Otherwise available=false, signals=[].
8. Each recommended_action needs: action, priority (Critical/High/Medium/Low), \
reason, evidence_refs, expected_benefit. Be specific, never "increase \
monitoring" — e.g. "Concrete pour on Grid C should not proceed until NCR-14 \
closes, since DA-14 records exposed reinforcement there."
9. Keep every list to at most 4 items — the sharpest, highest-value ones \
only, not an exhaustive dump. priority_matrix: at most 5 rows.
10. Output ONLY one JSON object. No markdown fences, no commentary.

JSON keys (all required): insufficient_evidence (bool), \
insufficient_evidence_reason (string|null), ocr_quality_note (string|null), \
executive_summary (2-3 sentences), major_findings, safety_findings, \
quality_findings, schedule_findings, procurement_findings, \
equipment_issues (arrays of <=4 cited strings each), weather_impact \
(one cited string), blocked_activities, critical_risks (arrays of <=4 \
cited strings), recommended_actions (<=4 objects: action, priority, \
reason, evidence_refs[], expected_benefit), priority_matrix (<=5 objects: \
item, urgency, impact, evidence_refs[]), next_site_visit_focus, \
questions_for_site_team (arrays of <=4 strings), contradictions (<=3 \
cited strings, [] if none), trend_analysis (object: available, summary, \
signals[]).

EVIDENCE:
{evidence_block}
"""

_RETRY_INSTRUCTION = "Return exactly one valid JSON object matching the schema. No markdown, no explanation, no trailing text."

_UNAVAILABLE_MESSAGE_EN = "AI reasoning is currently unavailable for this report. The evidence and risk score below are still real and unaffected — only the narrative analysis could not be generated."


def _get_reasoning_provider():
    """A full 14-section structured report is a much larger generation task
    than other Hermes call sites in this codebase — see the config comment
    on SITE_REPORT_HERMES_TIMEOUT_SECONDS for the measurement behind this.
    Rather than raise the shared HERMES_TIMEOUT_SECONDS (used by Copilot,
    meeting/procurement agents, and contract extraction — all of which
    reliably finish in well under 240s today and don't need extra budget),
    this pipeline builds its own HermesProvider instance with a longer,
    dedicated timeout when Hermes is the configured provider. Any other
    provider (mock/OpenAI/OpenRouter) comes back unchanged from the shared
    factory/cache."""
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
    """Post-parse enforcement of rule 2: drop any bullet with no bracketed
    evidence code, or whose cited codes don't correspond to real evidence
    handed to the model. Returns the number of items dropped, for logging.
    This is what makes 'every conclusion must cite evidence' a guarantee,
    not a request the model can silently ignore."""
    dropped = 0

    def _filter_list(items: list[str]) -> list[str]:
        nonlocal dropped
        kept = []
        for text in items:
            codes = set(_EVIDENCE_CODE_RE.findall(text))
            if codes and codes & known_codes:
                kept.append(text)
            else:
                dropped += 1
        return kept

    output.major_findings = _filter_list(output.major_findings)
    output.safety_findings = _filter_list(output.safety_findings)
    output.quality_findings = _filter_list(output.quality_findings)
    output.schedule_findings = _filter_list(output.schedule_findings)
    output.procurement_findings = _filter_list(output.procurement_findings)
    output.equipment_issues = _filter_list(output.equipment_issues)
    output.blocked_activities = _filter_list(output.blocked_activities)
    output.critical_risks = _filter_list(output.critical_risks)
    output.contradictions = _filter_list(output.contradictions)
    output.next_site_visit_focus = _filter_list(output.next_site_visit_focus)

    kept_actions = []
    for action in output.recommended_actions:
        refs = {r for r in action.evidence_refs if r in known_codes}
        if refs:
            action.evidence_refs = list(refs)
            kept_actions.append(action)
        else:
            dropped += 1
    output.recommended_actions = kept_actions

    kept_matrix = []
    for row in output.priority_matrix:
        refs = {r for r in row.evidence_refs if r in known_codes}
        if refs:
            row.evidence_refs = list(refs)
            kept_matrix.append(row)
        else:
            dropped += 1
    output.priority_matrix = kept_matrix

    return dropped


def _validate(raw_content: str, known_codes: set[str]) -> tuple[Optional[SiteReportReasoningOutput], Optional[str], int]:
    candidate = extract_json_text(raw_content)
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as e:
        return None, f"Response was not valid JSON: {e}", 0
    if not isinstance(parsed, dict):
        return None, "Top-level JSON value was not an object.", 0
    try:
        output = SiteReportReasoningOutput.model_validate(parsed)
    except ValidationError as e:
        return None, str(e), 0

    dropped = _strip_uncited_or_unknown(output, known_codes)
    return output, None, dropped


def generate_report_reasoning(ev: ReportEvidence, risk: RiskScoreBreakdown) -> ReasoningResult:
    """The one Hermes call for a /analyze request. Deliberately singular —
    trend comparison reuses the already-retrieved prior-report snapshots
    (site_report_evidence.py) instead of re-running Hermes per prior
    report, and the risk score is pure Python, not a second LLM call. This
    keeps latency to one Hermes round-trip regardless of how much history
    exists for the project."""
    evidence_block = _format_evidence_block(ev, risk)
    system_prompt = _SYSTEM_PROMPT.format(evidence_block=evidence_block)
    known_codes = _known_codes(ev)

    provider = _get_reasoning_provider()
    if not provider.is_available():
        return ReasoningResult(
            status="unavailable", output=None, provider=provider.provider_name,
            model_name=provider.model_name, error_message="LLM provider is not available.",
        )

    response, error = _call_provider(provider, system_prompt)
    if response is None:
        logger.warning("site_report_reasoning_provider_error error=%s", str(error)[:300])
        return ReasoningResult(
            status="unavailable", output=None, provider=provider.provider_name,
            model_name=provider.model_name, error_message=f"LLM provider unavailable: {str(error)[:300]}",
        )

    output, err, dropped = _validate(response.content, known_codes)
    retried = False
    if output is None:
        retried = True
        retry_response, retry_error = _call_provider(provider, system_prompt + "\n\n" + _RETRY_INSTRUCTION)
        if retry_response is not None:
            response = retry_response
            output, err, dropped = _validate(response.content, known_codes)

    if output is None:
        logger.warning(
            "site_report_reasoning_validation_failed retried=%s error=%s",
            retried, (err or "")[:300],
        )
        return ReasoningResult(
            status="unavailable", output=None, provider=response.provider, model_name=response.model,
            error_message="Model output did not match the required structure after retry.",
        )

    logger.info(
        "site_report_reasoning_completed report_id=%s provider=%s model=%s "
        "retried=%s dropped_unsupported=%d insufficient_evidence=%s",
        ev.report.id, response.provider, response.model, retried, dropped, output.insufficient_evidence,
    )
    return ReasoningResult(
        status="completed", output=output, provider=response.provider,
        model_name=response.model, dropped_unsupported_count=dropped,
    )
