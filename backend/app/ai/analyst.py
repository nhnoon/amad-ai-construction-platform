"""Deterministic analytical layer for Copilot answer generation.

Called in the pipeline BEFORE the LLM. Returns a specific, data-grounded
answer string when the question type is recognised and evidence is
sufficient; returns None to fall through to the LLM as normal.

Supported patterns
──────────────────
  highest_budget   — which project has the highest budget?
  lowest_budget    — which has the lowest budget?
  longest_delay    — which is most delayed?
  list_by_status   — show me delayed/active/on-hold projects
  tell_more        — tell me more about that project
  compare          — compare X with Y
  has_safety_ncr   — does it have unresolved NCRs or high-severity safety?
  attention_rank   — which project needs management attention, and why?
  count            — how many projects are delayed?

Design constraints
──────────────────
  - Only uses values extracted from evidence snippets — never invents
  - Always cites source_id codes (PRJ-XXXX, SE-XX, NCR-XX)
  - Bilingual: detects Arabic question → responds in Arabic
  - Returns None for ambiguous or unsupported questions so the LLM handles them
"""
from __future__ import annotations

import re
from typing import Optional

from app.ai.retrieval.base import Evidence


# ─────────────────────────────────────────────────────────────────────────────
# Evidence field parsing helpers
# ─────────────────────────────────────────────────────────────────────────────

_BUDGET_RE = re.compile(r"budget=([\d,]+(?:\.\d+)?)\s*SAR", re.IGNORECASE)


def parse_budget(snippet: str) -> Optional[float]:
    """Extract budget in SAR from a project evidence snippet."""
    m = _BUDGET_RE.search(snippet)
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except ValueError:
        return None


def parse_field(snippet: str, field: str) -> Optional[str]:
    """Extract the value of a key=value field from an evidence snippet.

    Returns the stripped value up to the next comma or end of line.
    """
    pattern = re.compile(
        r"(?:^|[\s,])" + re.escape(field) + r"=([^,\n]+)",
        re.IGNORECASE,
    )
    m = pattern.search(snippet)
    if not m:
        return None
    return m.group(1).strip().rstrip(",").strip()


def parse_project_name(ev: Evidence) -> str:
    """Extract human-readable project name from label 'Project PRJ-0001 — Name'."""
    label = ev.label or ""
    if " — " in label:
        return label.split(" — ", 1)[1].strip()
    return label


def parse_project_code(ev: Evidence) -> str:
    """Return the project source_id (e.g. PRJ-0001)."""
    return ev.source_id or ""


def _fmt_budget(val: float) -> str:
    return f"{val:,.0f} SAR"


def _is_arabic(text: str) -> bool:
    arabic = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    return arabic > len(text) * 0.2


# ─────────────────────────────────────────────────────────────────────────────
# Question type detection
# ─────────────────────────────────────────────────────────────────────────────

_HIGHEST_BUDGET = re.compile(
    # English patterns
    r"\b(highest|largest|biggest|maximum|most expensive)\b.{0,50}"
    r"\b(budget|cost|value)\b"
    r"|\b(budget|cost|value)\b.{0,50}"
    r"\b(highest|largest|maximum)\b"
    # Arabic patterns — no \b: Arabic words with ال prefix or pronoun/possessive
    # suffixes break ASCII word-boundary matching.
    # Handles: ميزانيته (budget+his), الأعلى (the+highest), أعلى ميزانية, etc.
    r"|(?:أعلى|الأعلى|أكبر|الأكبر).{0,60}(?:ميزانية|ميزانيت|تكلفة)"
    r"|(?:ميزانية|ميزانيت|تكلفة).{0,60}(?:أعلى|الأعلى|أكبر|الأكبر)",
    re.IGNORECASE | re.DOTALL,
)
_LOWEST_BUDGET = re.compile(
    # English patterns
    r"\b(lowest|smallest|minimum|cheapest|least)\b.{0,50}"
    r"\b(budget|cost|value)\b"
    r"|\b(budget|cost|value)\b.{0,50}"
    r"\b(lowest|smallest|minimum)\b"
    # Arabic patterns — no \b for same reason as above
    r"|(?:أقل|الأقل|أصغر|الأصغر).{0,60}(?:ميزانية|ميزانيت|تكلفة)"
    r"|(?:ميزانية|ميزانيت|تكلفة).{0,60}(?:أقل|الأقل|أصغر)",
    re.IGNORECASE | re.DOTALL,
)
_LONGEST_DELAY = re.compile(
    r"\b(longest|most|worst|greatest|أكثر)\b.{0,40}"
    r"\b(delay|delayed|overdue|behind|تأخر)\b"
    r"|\bmost delayed\b|\bmost overdue\b",
    re.IGNORECASE | re.DOTALL,
)
_LIST_STATUS = re.compile(
    # English + bare Arabic verbs (these sit at word boundaries naturally)
    r"\b(show|list|display|give me|get|see|what are|اعرض|أعرض|أظهر|اذكر)\b.{0,30}"
    r"\b(delayed|active|on.?hold|completed|planning|late|behind|متأخر|نشط|معلق)\b"
    r"|\b(delayed|active|on.?hold)\s+projects?\b"
    # Arabic without \b — handles المتأخرة (ال+delayed+ة), المتأخر, متأخرة, etc.
    r"|(?:اعرض|أعرض|أظهر|اذكر|أرني|عرض).{0,80}(?:متأخر|المتأخر)"
    r"|(?:متأخر|المتأخر|المتأخرة).{0,40}(?:مشروع|مشاريع|المشاريع)"
    r"|(?:مشاريع|المشاريع).{0,30}(?:متأخر|المتأخر|المتأخرة)",
    re.IGNORECASE | re.DOTALL,
)
_TELL_MORE = re.compile(
    r"\b(tell me more|more about|more detail|elaborate|expand on|more information|"
    r"details? about|what else|أخبرني أكثر|مزيد من المعلومات|تفاصيل|المزيد)\b",
    re.IGNORECASE,
)
# Arabic: قارن matches قارنه, قارنها, قارني etc. (no trailing \b so suffix variants match)
_COMPARE = re.compile(
    r"\bcompare\b"
    r"|مقارنة"
    r"|قارن",        # intentionally no trailing \b — matches قارنه, قارنها, قارني
    re.IGNORECASE,
)
_ATTENTION = re.compile(
    r"\b(attention|focus|priority|prioritize|most important|most critical|"
    r"concerned|worry|watch|اهتمام|أولوية|أهم|الأهم|ينبغي)\b",
    re.IGNORECASE,
)
_HAS_SAFETY_NCR = re.compile(
    # English + bare Arabic keywords at natural word boundaries
    r"\b(ncrs?|non.?conformance|safety|incident|accident|سلامة|حادث|جودة)\b"
    r".{0,50}\b(unresolved|open|active|high|severe|outstanding|مفتوح)\b"
    r"|\b(unresolved|open|high.?severity)\b.{0,50}\b(ncrs?|safety|incident)\b"
    # Arabic without \b for severity adjectives: خطيرة (خطير+ة), الخطيرة, etc.
    r"|سلامة.{0,60}خطير"
    r"|حادث.{0,60}(?:خطير|شديد)",
    re.IGNORECASE | re.DOTALL,
)
_COUNT = re.compile(
    r"\bhow many\b|\bcount\b|\bكم\b.{0,15}\b(مشروع|حادث|تقرير)\b",
    re.IGNORECASE,
)
_RISK_SUMMARY = re.compile(
    # English — word-boundary safe
    r"\b(main risks?|key risks?|top risks?|primary risks?|risk summary|risk profile"
    r"|risk report|biggest risks?|major risks?|critical risks?)\b"
    r"|\bwhat are.{0,30}\brisks?\b"
    # Arabic — no \b (morphological prefixes/suffixes break ASCII boundaries)
    # Matches: ما هي المخاطر, ما المخاطر, ماهي المخاطر, what/show/list risks
    r"|(?:ما هي|ما هو|ماهي|ما\s+ال).{0,20}(?:مخاطر|الخطر)"
    r"|(?:مخاطر|المخاطر).{0,40}(?:الرئيسية|الأساسية|الأهم|الرئيسي|الكبرى)"
    r"|ملخص.{0,20}(?:مخاطر|الخطر)"
    r"|(?:اعرض|أعرض|أظهر|اذكر).{0,30}(?:مخاطر|المخاطر|الخطر)",
    re.IGNORECASE | re.DOTALL,
)
_LOWEST_HEALTH = re.compile(
    r"\b(lowest|worst|least|poorest|most unhealthy|least healthy)\b.{0,40}"
    r"\b(health|health score|health level)\b"
    r"|\b(health|health score)\b.{0,40}\b(lowest|worst|least|poorest)\b"
    r"|\bmost unhealthy\b|\bleast healthy\b"
    r"|(?:أقل|الأقل|الأسوأ).{0,40}(?:صحة|درجة صحة)"
    r"|(?:صحة|درجة صحة).{0,40}(?:أقل|الأقل|الأسوأ)",
    re.IGNORECASE | re.DOTALL,
)
_UNHEALTHY_PROJECTS = re.compile(
    r"\b(show|list|display|find|get|what are|اعرض|أعرض|أظهر)\b.{0,30}"
    r"\b(unhealthy|critical|at.?risk|poor health|low health|sick)\b.{0,30}"
    r"\bprojects?\b"
    r"|\b(unhealthy|at.?risk|critical)\s+projects?\b"
    r"|\bprojects?\b.{0,30}\b(unhealthy|at.?risk|critical|low health score)\b"
    r"|(?:مشاريع|المشاريع).{0,30}(?:حرجة|الحرجة|غير صحية)"
    r"|(?:حرجة|غير صحية).{0,30}(?:مشاريع|المشاريع)",
    re.IGNORECASE | re.DOTALL,
)
_HEALTH_EXPLAIN = re.compile(
    r"\b(why|explain|reason|what.*wrong|درجة الصحة|لماذا)\b.{0,50}"
    r"\b(unhealthy|low health|poor|health score|صحة)\b"
    r"|\b(health score for|health of)\b.{0,50}\bPRJ-\d+\b"
    r"|\bPRJ-\d+\b.{0,30}\b(health|unhealthy|score)\b",
    re.IGNORECASE | re.DOTALL,
)
# Highest health / best performing projects
_HIGHEST_HEALTH = re.compile(
    r"\b(highest|best|greatest|top|healthiest|most healthy)\b.{0,40}"
    r"\b(health|health score|health level)\b"
    r"|\b(health|health score)\b.{0,40}\b(highest|best|top|healthiest)\b"
    r"|\bhealthiest\b|\bmost healthy\b|\bbest health\b"
    r"|(?:أعلى|الأعلى|الأفضل|أحسن).{0,40}(?:صحة|درجة صحة)"
    r"|(?:صحة|درجة صحة).{0,40}(?:أعلى|الأعلى|الأفضل)",
    re.IGNORECASE | re.DOTALL,
)
# Best-performing project (by status + health)
_BEST_PERFORMING = re.compile(
    r"\b(best.?performing|performing best|best.?project|top.?performing|"
    r"most successful|best overall|doing best|performing (well|best)|"
    r"best.?managed|most efficient)\b"
    r"|(?:أفضل).{0,30}(?:أداء[ًً]?|مشروع|مشاريع)"
    r"|(?:أداء[ًً]?).{0,30}(?:أفضل|الأفضل)"
    r"|(?:الأكثر).{0,20}(?:أداء[ًً]?|نجاح[اًً]?)",
    re.IGNORECASE | re.DOTALL,
)
# Riskiest / most-at-risk project (cross-domain risk score)
_RISKIEST = re.compile(
    r"\b(riskiest|most risky|highest risk|most dangerous|most vulnerable|"
    r"most at.?risk|biggest risk|greatest risk|highest.?risk profile)\b"
    r"|(?:أكثر).{0,20}(?:خطراً|خطورة|مخاطرة|مخاطر)"
    r"|(?:الأكثر).{0,20}(?:خطراً|خطورة|مخاطرة)",
    re.IGNORECASE | re.DOTALL,
)
# Short "why?" / "explain" follow-ups — always anaphoric when very short
_WHY_EXPLAIN = re.compile(
    r"^\s*why\??\s*$"
    r"|^\s*why (that|so|is that|is this|not)\??\s*$"
    r"|^\s*explain\??\s*$"
    r"|^\s*explain (that|this|why|more)\??\s*$"
    r"|^\s*what('?s| is) the reason\??\s*$"
    r"|^\s*how (so|come)\??\s*$"
    r"|^\s*لماذا\??\s*$"
    r"|^\s*اشرح\s*$",
    re.IGNORECASE,
)


def detect_query_type(question: str) -> str:
    """Classify a question into an analytical handler type.

    Returns one of: highest_budget, lowest_budget, longest_delay,
    list_by_status, tell_more, compare, has_safety_ncr, attention_rank,
    count, risk_summary, riskiest_project, highest_health, best_performing,
    why_explain, generic.

    Order matters: more specific patterns are checked first.
    """
    # Very short explain-style follow-ups — resolve against prior context
    if _WHY_EXPLAIN.search(question):
        return "why_explain"
    if _HIGHEST_BUDGET.search(question):
        return "highest_budget"
    if _LOWEST_BUDGET.search(question):
        return "lowest_budget"
    if _LONGEST_DELAY.search(question):
        return "longest_delay"
    # RISKIEST before RISK_SUMMARY — more specific
    if _RISKIEST.search(question):
        return "riskiest_project"
    # RISK_SUMMARY before COUNT/LIST_STATUS — "what are the main risks" is
    # a risk summary query, not a count or listing query.
    if _RISK_SUMMARY.search(question):
        return "risk_summary"
    # HEALTH patterns — before generic list/count to avoid false positives
    # HIGHEST_HEALTH before LOWEST_HEALTH so "healthiest" doesn't slip through
    if _HIGHEST_HEALTH.search(question):
        return "highest_health"
    if _LOWEST_HEALTH.search(question):
        return "lowest_health"
    if _UNHEALTHY_PROJECTS.search(question):
        return "unhealthy_projects"
    if _HEALTH_EXPLAIN.search(question):
        return "health_explain"
    if _BEST_PERFORMING.search(question):
        return "best_performing"
    # COUNT before LIST_STATUS: "how many delayed projects" is a count query,
    # not a listing query — check for interrogative quantity words first.
    if _COUNT.search(question):
        return "count"
    if _COMPARE.search(question):
        return "compare"
    if _LIST_STATUS.search(question):
        return "list_by_status"
    if _TELL_MORE.search(question):
        return "tell_more"
    if _HAS_SAFETY_NCR.search(question):
        return "has_safety_ncr"
    if _ATTENTION.search(question):
        return "attention_rank"
    return "generic"


# ─────────────────────────────────────────────────────────────────────────────
# Per-type answer handlers
# ─────────────────────────────────────────────────────────────────────────────

def _project_evidence(evidence: list[Evidence]) -> list[Evidence]:
    return [e for e in evidence if e.source_type == "project"]


def _answer_ranking_by_budget(
    evidence: list[Evidence], highest: bool, is_ar: bool
) -> Optional[str]:
    project_ev = _project_evidence(evidence)
    if not project_ev:
        return None

    budgets = [(parse_budget(e.snippet), e) for e in project_ev]
    budgets = [(b, e) for b, e in budgets if b is not None]
    if not budgets:
        return None

    budgets.sort(key=lambda x: x[0], reverse=highest)
    best_budget, best_ev = budgets[0]
    name = parse_project_name(best_ev)
    code = parse_project_code(best_ev)
    status = parse_field(best_ev.snippet, "status") or "N/A"
    client = parse_field(best_ev.snippet, "client") or "N/A"
    city = parse_field(best_ev.snippet, "city") or "N/A"
    budget_fmt = _fmt_budget(best_budget)
    superlative = "highest" if highest else "lowest"
    superlative_ar = "أعلى" if highest else "أقل"

    # Add runner-up for context
    runner_note = ""
    if len(budgets) > 1:
        second_budget, second_ev = budgets[1]
        second_name = parse_project_name(second_ev)
        second_code = parse_project_code(second_ev)
        runner_note = (
            f"\n\nFor comparison, **{second_name}** ({second_code}) "
            f"has a budget of {_fmt_budget(second_budget)}."
        )

    if is_ar:
        return (
            f"المشروع ذو {superlative_ar} ميزانية هو **{name}** ({code}) "
            f"بقيمة **{budget_fmt}**.\n\n"
            f"- الحالة: {status}\n"
            f"- العميل: {client}\n"
            f"- المدينة: {city}\n"
            f"\nالمرجع: [{code}]"
        )

    return (
        f"**{name}** ({code}) has the {superlative} budget at **{budget_fmt}**.\n\n"
        f"- Status: {status}\n"
        f"- Client: {client}\n"
        f"- City: {city}"
        f"{runner_note}\n\n"
        f"Source: [{code}]"
    )


def _answer_list_by_status(evidence: list[Evidence], question: str, is_ar: bool) -> Optional[str]:
    project_ev = _project_evidence(evidence)
    if not project_ev:
        return None

    # Detect which status to filter for
    lower_q = question.lower()
    if "delayed" in lower_q or "late" in lower_q or "behind" in lower_q or "متأخر" in question:
        target_status = "delayed"
    elif "active" in lower_q or "ongoing" in lower_q or "نشط" in question:
        target_status = "active"
    elif "on hold" in lower_q or "paused" in lower_q or "معلق" in question:
        target_status = "on hold"
    elif "completed" in lower_q or "مكتمل" in question:
        target_status = "completed"
    else:
        target_status = None  # show all

    if target_status:
        filtered = [
            e for e in project_ev
            if (parse_field(e.snippet, "status") or "").lower() == target_status.lower()
        ]
        # Fallback: show all if filter yields nothing (evidence may be pre-filtered)
        if not filtered:
            filtered = project_ev
    else:
        filtered = project_ev

    if not filtered:
        return None

    lines = []
    for i, ev in enumerate(filtered, 1):
        name = parse_project_name(ev)
        code = parse_project_code(ev)
        status = parse_field(ev.snippet, "status") or "N/A"
        budget = parse_budget(ev.snippet)
        city = parse_field(ev.snippet, "city") or ""
        client = parse_field(ev.snippet, "client") or ""
        budget_str = f" | budget: {_fmt_budget(budget)}" if budget else ""
        lines.append(f"{i}. **{name}** ({code}) — {status}{budget_str}"
                     + (f" | {city}" if city else "")
                     + (f" | {client}" if client else ""))

    codes = ", ".join(f"[{parse_project_code(e)}]" for e in filtered)
    status_label = target_status.title() if target_status else "all"

    if is_ar:
        header = (
            f"تم العثور على **{len(filtered)}** مشاريع "
            f"({'متأخرة' if target_status == 'delayed' else status_label}):\n\n"
        )
    else:
        header = f"Found **{len(filtered)}** {status_label} project(s):\n\n"

    return header + "\n".join(lines) + f"\n\nSources: {codes}"


def _answer_tell_more(evidence: list[Evidence], is_ar: bool) -> Optional[str]:
    project_ev = _project_evidence(evidence)
    if not project_ev:
        return None

    # Use the first (most-relevant) project in evidence
    ev = project_ev[0]
    name = parse_project_name(ev)
    code = parse_project_code(ev)
    status = parse_field(ev.snippet, "status") or "N/A"
    client = parse_field(ev.snippet, "client") or "N/A"
    city = parse_field(ev.snippet, "city") or "N/A"
    budget = parse_budget(ev.snippet)
    start = parse_field(ev.snippet, "start") or "N/A"
    planned_finish = parse_field(ev.snippet, "planned_finish") or "N/A"
    budget_str = _fmt_budget(budget) if budget else "N/A"

    # Also collect associated safety / NCR evidence
    safety_ev = [e for e in evidence if e.source_type == "safety_event" and e.project_id == ev.project_id]
    ncr_ev = [e for e in evidence if e.source_type == "ncr" and e.project_id == ev.project_id]
    safety_note = ""
    if safety_ev:
        high = [e for e in safety_ev if (parse_field(e.snippet, "severity") or "").lower() == "high"]
        safety_note = (
            f"\n- Safety events: {len(safety_ev)} on record"
            + (f" ({len(high)} high-severity)" if high else "")
        )
    ncr_note = ""
    if ncr_ev:
        ncr_note = f"\n- Open NCRs: {len(ncr_ev)}"

    if is_ar:
        return (
            f"تفاصيل المشروع **{name}** ({code}):\n\n"
            f"- الحالة: {status}\n"
            f"- الميزانية: {budget_str}\n"
            f"- العميل: {client}\n"
            f"- المدينة: {city}\n"
            f"- تاريخ البدء: {start}\n"
            f"- الإنجاز المخطط: {planned_finish}"
            + (f"\n- أحداث السلامة: {len(safety_ev)}" if safety_ev else "")
            + (f"\n- طلبات التصحيح المفتوحة: {len(ncr_ev)}" if ncr_ev else "")
            + f"\n\nالمرجع: [{code}]"
        )

    return (
        f"Details for **{name}** ({code}):\n\n"
        f"- Status: {status}\n"
        f"- Budget: {budget_str}\n"
        f"- Client: {client}\n"
        f"- City: {city}\n"
        f"- Start date: {start}\n"
        f"- Planned finish: {planned_finish}"
        + safety_note
        + ncr_note
        + f"\n\nSource: [{code}]"
    )


def _answer_compare(evidence: list[Evidence], is_ar: bool) -> Optional[str]:
    project_ev = _project_evidence(evidence)
    if len(project_ev) < 2:
        return None

    # Compare first two projects
    a, b = project_ev[0], project_ev[1]

    def row(ev: Evidence) -> dict:
        return {
            "name": parse_project_name(ev),
            "code": parse_project_code(ev),
            "status": parse_field(ev.snippet, "status") or "N/A",
            "budget": parse_budget(ev.snippet),
            "city": parse_field(ev.snippet, "city") or "N/A",
            "client": parse_field(ev.snippet, "client") or "N/A",
            "start": parse_field(ev.snippet, "start") or "N/A",
            "planned_finish": parse_field(ev.snippet, "planned_finish") or "N/A",
        }

    ra, rb = row(a), row(b)
    ba, bb = ra["budget"], rb["budget"]
    budget_winner_en = ""
    budget_winner_ar = ""
    if ba is not None and bb is not None:
        if ba > bb:
            budget_winner_en = f" (higher — {_fmt_budget(ba - bb)} difference)"
            budget_winner_ar = f" (أعلى — فرق {_fmt_budget(ba - bb)})"
        elif bb > ba:
            budget_winner_en = f" (lower — {_fmt_budget(bb - ba)} difference)"
            budget_winner_ar = f" (أقل — فرق {_fmt_budget(bb - ba)})"

    if is_ar:
        lines = [
            f"**مقارنة: {ra['name']} مقابل {rb['name']}**\n",
            f"| السمة | {ra['name']} ({ra['code']}) | {rb['name']} ({rb['code']}) |",
            f"|---|---|---|",
            f"| الحالة | {ra['status']} | {rb['status']} |",
            f"| الميزانية | {_fmt_budget(ba) if ba else 'غير محدد'}{budget_winner_ar} | {_fmt_budget(bb) if bb else 'غير محدد'} |",
            f"| المدينة | {ra['city']} | {rb['city']} |",
            f"| العميل | {ra['client']} | {rb['client']} |",
            f"| تاريخ البدء | {ra['start']} | {rb['start']} |",
            f"| الإنجاز المخطط | {ra['planned_finish']} | {rb['planned_finish']} |",
            f"\nالمصادر: [{ra['code']}] [{rb['code']}]",
        ]
        return "\n".join(lines)

    lines = [
        f"**Comparison: {ra['name']} vs {rb['name']}**\n",
        f"| Attribute      | {ra['name']} ({ra['code']}) | {rb['name']} ({rb['code']}) |",
        f"|---------------|------|------|",
        f"| Status        | {ra['status']} | {rb['status']} |",
        f"| Budget        | {_fmt_budget(ba) if ba else 'N/A'}{budget_winner_en} | {_fmt_budget(bb) if bb else 'N/A'} |",
        f"| City          | {ra['city']} | {rb['city']} |",
        f"| Client        | {ra['client']} | {rb['client']} |",
        f"| Start         | {ra['start']} | {rb['start']} |",
        f"| Planned end   | {ra['planned_finish']} | {rb['planned_finish']} |",
        f"\nSources: [{ra['code']}] [{rb['code']}]",
    ]

    return "\n".join(lines)


def _answer_has_safety_ncr(evidence: list[Evidence], is_ar: bool) -> Optional[str]:
    safety_ev = [e for e in evidence if e.source_type == "safety_event"]
    ncr_ev = [e for e in evidence if e.source_type == "ncr"]

    if not safety_ev and not ncr_ev:
        if is_ar:
            return "لم يتم العثور على أحداث سلامة أو طلبات تصحيح مفتوحة في الأدلة المسترجعة."
        return "No safety events or open NCRs found in the retrieved evidence for this scope."

    parts = []

    if safety_ev:
        high = [e for e in safety_ev if (parse_field(e.snippet, "severity") or "").lower() == "high"]
        medium = [e for e in safety_ev if (parse_field(e.snippet, "severity") or "").lower() == "medium"]
        low_ev = [e for e in safety_ev if (parse_field(e.snippet, "severity") or "").lower() == "low"]

        if is_ar:
            parts.append(f"**أحداث السلامة:** {len(safety_ev)} حدث")
            if high:
                parts.append(f"- خطورة عالية: {len(high)}")
            if medium:
                parts.append(f"- خطورة متوسطة: {len(medium)}")
            if low_ev:
                parts.append(f"- خطورة منخفضة: {len(low_ev)}")
        else:
            parts.append(f"**Safety Events:** {len(safety_ev)} on record")
            if high:
                parts.append(f"  - High-severity: {len(high)}")
            if medium:
                parts.append(f"  - Medium-severity: {len(medium)}")
            if low_ev:
                parts.append(f"  - Low-severity: {len(low_ev)}")

        # Cite first high-severity event
        if high:
            h = high[0]
            desc = parse_field(h.snippet, "description") or h.snippet[:80]
            parts.append(f"  Notable: {desc} [SE-{h.source_id}]" if not is_ar else
                         f"  حدث بارز: {desc} [SE-{h.source_id}]")

    if ncr_ev:
        open_ncr = [e for e in ncr_ev if "open" in (parse_field(e.snippet, "status") or "").lower()
                    or "corrective" in (parse_field(e.snippet, "status") or "").lower()]
        if is_ar:
            parts.append(f"\n**طلبات التصحيح:** {len(ncr_ev)} مفتوح")
            if open_ncr:
                parts.append(f"- قيد التنفيذ: {len(open_ncr)}")
        else:
            parts.append(f"\n**Open NCRs:** {len(ncr_ev)} total")
            if open_ncr:
                parts.append(f"  - Under corrective action: {len(open_ncr)}")

    # Cite all sources
    all_src = (
        " ".join(f"[SE-{e.source_id}]" for e in safety_ev[:5])
        + " "
        + " ".join(f"[NCR-{e.source_id}]" for e in ncr_ev[:5])
    ).strip()

    parts.append(f"\nSources: {all_src}" if not is_ar else f"\nالمراجع: {all_src}")
    return "\n".join(parts)


def _answer_attention_rank(evidence: list[Evidence], is_ar: bool) -> Optional[str]:
    project_ev = _project_evidence(evidence)
    if not project_ev:
        return None

    safety_ev = [e for e in evidence if e.source_type == "safety_event"]
    ncr_ev = [e for e in evidence if e.source_type == "ncr"]
    health_ev = _health_evidence(evidence)

    # Score each project
    scored = []
    for ev in project_ev:
        score = 0
        reasons = []
        status = (parse_field(ev.snippet, "status") or "").lower()
        budget = parse_budget(ev.snippet)
        pid = ev.project_id

        if status == "delayed":
            score += 3
            reasons.append("🟠 Delayed schedule")
        if status == "on hold":
            score += 2
            reasons.append("⚠️ Project on hold")

        # Safety events for this project
        proj_safety = [s for s in safety_ev if s.project_id == pid]
        high_safety = [s for s in proj_safety if (parse_field(s.snippet, "severity") or "").lower() == "high"]
        if high_safety:
            score += len(high_safety) * 2
            reasons.append(f"🔴 {len(high_safety)} high-severity safety event(s)")
        elif proj_safety:
            score += len(proj_safety)
            reasons.append(f"🟠 {len(proj_safety)} safety event(s)")

        # NCRs for this project
        proj_ncr = [n for n in ncr_ev if n.project_id == pid]
        if proj_ncr:
            score += len(proj_ncr)
            reasons.append(f"🟡 {len(proj_ncr)} open NCR(s)")

        # Health score
        proj_health = [h for h in health_ev if h.project_id == pid]
        if proj_health:
            hs = _parse_health_score(proj_health[0].snippet) or 100
            hl = _parse_health_level(proj_health[0].snippet) or ""
            if hl == "Critical":
                score += 5
                reasons.append(f"🔴 Critical health score ({hs}/100)")
            elif hl == "At Risk":
                score += 2
                reasons.append(f"🟠 At Risk health score ({hs}/100)")

        # High budget → higher impact if delayed
        if budget and budget > 10_000_000 and any("delayed" in r.lower() or "on hold" in r.lower() for r in reasons):
            score += 1
            reasons.append(f"💰 High financial exposure ({_fmt_budget(budget)})")

        scored.append((score, ev, reasons, budget))

    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    top_score, top_ev, top_reasons, top_budget = scored[0]
    name = parse_project_name(top_ev)
    code = parse_project_code(top_ev)

    lines = []
    if is_ar:
        lines.append(f"المشروع الذي يستوجب أكبر قدر من الاهتمام الإداري هو **{name}** ({code}).\n")
        if top_reasons:
            lines.append("**عوامل الخطورة (مرتبة حسب الأولوية):**")
            for i, r in enumerate(top_reasons[:5], 1):
                lines.append(f"  {i}. {r}")
        lines.append("\n**التوصية:** يُنصح بجدولة مراجعة تنفيذية خلال 48 ساعة.")
    else:
        lines.append(
            f"**{name}** ({code}) requires the most management attention "
            f"(priority score: {top_score}).\n"
        )
        if top_reasons:
            lines.append("**Risk factors (ranked by severity):**")
            for i, r in enumerate(top_reasons[:5], 1):
                lines.append(f"  {i}. {r}")
        lines.append("\n**Recommendation:** Schedule an executive review within 48 hours.")

    # Show full ranking if multiple projects
    if len(scored) > 1:
        if not is_ar:
            lines.append("\n**Full attention ranking:**")
        else:
            lines.append("\n**ترتيب الأولوية الكامل:**")
        for i, (sc, ev, rsn, _) in enumerate(scored[:5], 1):
            n = parse_project_name(ev)
            c = parse_project_code(ev)
            st = parse_field(ev.snippet, "status") or "N/A"
            rsn_short = "; ".join(r.split(" ", 1)[-1] for r in rsn[:2]) if rsn else "no critical issues"
            lines.append(f"  {i}. **{n}** ({c}) — {st} — {rsn_short}")

    codes = " ".join(f"[{parse_project_code(e)}]" for _, e, _, _ in scored[:5])
    lines.append(f"\n{'المصادر' if is_ar else 'Sources'}: {codes}")
    return "\n".join(lines)


def _answer_count(evidence: list[Evidence], question: str, is_ar: bool) -> Optional[str]:
    lower_q = question.lower()
    project_ev = _project_evidence(evidence)

    if "delayed" in lower_q or "late" in lower_q:
        delayed = [e for e in project_ev
                   if (parse_field(e.snippet, "status") or "").lower() == "delayed"]
        count = len(delayed)
        label = "delayed" if not is_ar else "متأخرة"
        codes = ", ".join(f"[{parse_project_code(e)}]" for e in delayed[:5])
        if is_ar:
            return f"يوجد **{count}** مشروع {label} في الأدلة المسترجعة. {codes}"
        return f"There are **{count}** {label} project(s) in the retrieved data. {codes}"

    safety_ev = [e for e in evidence if e.source_type == "safety_event"]
    if "safety" in lower_q or "incident" in lower_q or "سلامة" in question:
        codes = " ".join(f"[SE-{e.source_id}]" for e in safety_ev[:5])
        if is_ar:
            return f"يوجد **{len(safety_ev)}** حادث سلامة في السجلات. {codes}"
        return f"There are **{len(safety_ev)}** safety event(s) on record. {codes}"

    ncr_ev = [e for e in evidence if e.source_type == "ncr"]
    if "ncr" in lower_q or "non" in lower_q:
        codes = " ".join(f"[NCR-{e.source_id}]" for e in ncr_ev[:5])
        if is_ar:
            return f"يوجد **{len(ncr_ev)}** طلب تصحيح مفتوح. {codes}"
        return f"There are **{len(ncr_ev)}** open NCR(s). {codes}"

    # Generic count of projects
    if project_ev:
        codes = ", ".join(f"[{parse_project_code(e)}]" for e in project_ev[:5])
        return f"Found **{len(project_ev)}** project(s) in scope. {codes}"

    return None


def _proj_code_for_pid(
    project_id: Optional[int],
    project_ev: list[Evidence],
) -> Optional[str]:
    """Return the PRJ-XXXX code for a given project_id, if available in evidence."""
    if project_id is None:
        return None
    match = next((e for e in project_ev if e.project_id == project_id), None)
    return parse_project_code(match) if match else None


def _answer_risk_summary(
    evidence: list[Evidence],
    is_ar: bool,
) -> Optional[str]:
    """Produce a ranked, cross-domain risk summary grounded in retrieved evidence.

    Categories (highest → lowest priority):
      1. Safety risks  — safety events, high-severity first
      2. Schedule risks — delayed / on-hold projects
      3. Quality risks  — open NCRs
      4. Risk-register  — formal ProjectRisk entries (high impact/probability)
      5. Procurement    — late purchase orders
    """
    project_ev = _project_evidence(evidence)
    risk_ev = [e for e in evidence if e.source_type == "project_risk"]
    safety_ev = [e for e in evidence if e.source_type == "safety_event"]
    ncr_ev = [e for e in evidence if e.source_type == "ncr"]
    po_ev = [
        e for e in evidence
        if e.source_type == "purchase_order" and "late=True" in e.snippet
    ]

    if not any([safety_ev, risk_ev, ncr_ev, po_ev]) and not project_ev:
        return None

    sections: list[str] = []
    cited: list[str] = []

    # ── 1. Safety risks ───────────────────────────────────────────────────────
    if safety_ev:
        high_sev = [
            e for e in safety_ev
            if (parse_field(e.snippet, "severity") or "").lower() == "high"
        ]
        display = high_sev[:3] or safety_ev[:3]
        affected_pids = list(dict.fromkeys(
            e.project_id for e in safety_ev if e.project_id is not None
        ))
        affected_codes = [
            c for c in (
                _proj_code_for_pid(pid, project_ev) for pid in affected_pids[:5]
            ) if c
        ]

        if is_ar:
            header = (
                f"**🔴 مخاطر السلامة** — {len(safety_ev)} حدث"
                + (f" ({len(high_sev)} عالية الخطورة)" if high_sev else "")
            )
            lines = [header]
            if affected_codes:
                lines.append(f"  - المشاريع المتأثرة: {', '.join(affected_codes)}")
            for e in display:
                desc = parse_field(e.snippet, "description") or ""
                desc_short = desc[:70] if desc else e.snippet[:70]
                code = _proj_code_for_pid(e.project_id, project_ev)
                suffix = f" [{code}]" if code else ""
                lines.append(f"  - SE-{e.source_id}: {desc_short}{suffix}")
        else:
            header = (
                f"**🔴 Safety Risks** — {len(safety_ev)} event(s)"
                + (f" ({len(high_sev)} high-severity)" if high_sev else "")
            )
            lines = [header]
            if affected_codes:
                lines.append(f"  - Affected projects: {', '.join(affected_codes)}")
            for e in display:
                desc = parse_field(e.snippet, "description") or ""
                desc_short = desc[:70] if desc else e.snippet[:70]
                code = _proj_code_for_pid(e.project_id, project_ev)
                suffix = f" [{code}]" if code else ""
                lines.append(f"  - SE-{e.source_id}: {desc_short}{suffix}")

        sections.append("\n".join(lines))
        cited.extend(f"SE-{e.source_id}" for e in display)

    # ── 2. Schedule risks (delayed / on-hold projects) ────────────────────────
    delayed_ev = [
        e for e in project_ev
        if (parse_field(e.snippet, "status") or "").lower() == "delayed"
    ]
    on_hold_ev = [
        e for e in project_ev
        if (parse_field(e.snippet, "status") or "").lower() == "on hold"
    ]

    if delayed_ev or on_hold_ev:
        if is_ar:
            lines = ["**🟠 مخاطر الجدول الزمني**"]
            if delayed_ev:
                codes = ", ".join(parse_project_code(e) for e in delayed_ev[:6])
                lines.append(f"  - {len(delayed_ev)} مشاريع متأخرة: {codes}")
            if on_hold_ev:
                codes = ", ".join(parse_project_code(e) for e in on_hold_ev[:4])
                lines.append(f"  - {len(on_hold_ev)} مشاريع معلقة: {codes}")
        else:
            lines = ["**🟠 Schedule Risks**"]
            if delayed_ev:
                codes = ", ".join(parse_project_code(e) for e in delayed_ev[:6])
                lines.append(f"  - {len(delayed_ev)} delayed project(s): {codes}")
            if on_hold_ev:
                codes = ", ".join(parse_project_code(e) for e in on_hold_ev[:4])
                lines.append(f"  - {len(on_hold_ev)} on-hold project(s): {codes}")

        sections.append("\n".join(lines))
        cited.extend(parse_project_code(e) for e in (delayed_ev + on_hold_ev)[:5])

    # ── 3. Quality risks (open NCRs) ──────────────────────────────────────────
    if ncr_ev:
        affected_pids = list(dict.fromkeys(
            e.project_id for e in ncr_ev if e.project_id is not None
        ))
        affected_codes = [
            c for c in (
                _proj_code_for_pid(pid, project_ev) for pid in affected_pids[:5]
            ) if c
        ]

        if is_ar:
            lines = [f"**🟡 مخاطر الجودة** — {len(ncr_ev)} طلب تصحيح مفتوح"]
            if affected_codes:
                lines.append(f"  - المشاريع المتأثرة: {', '.join(affected_codes)}")
            for e in ncr_ev[:3]:
                ncr_type = parse_field(e.snippet, "type") or "—"
                lines.append(f"  - NCR-{e.source_id}: {ncr_type[:60]}")
        else:
            lines = [f"**🟡 Quality Risks** — {len(ncr_ev)} open NCR(s)"]
            if affected_codes:
                lines.append(f"  - Affected projects: {', '.join(affected_codes)}")
            for e in ncr_ev[:3]:
                ncr_type = parse_field(e.snippet, "type") or "—"
                lines.append(f"  - NCR-{e.source_id}: {ncr_type[:60]}")

        sections.append("\n".join(lines))
        cited.extend(f"NCR-{e.source_id}" for e in ncr_ev[:3])

    # ── 4. Formal risk register ───────────────────────────────────────────────
    if risk_ev:
        high_risk = [
            e for e in risk_ev
            if (parse_field(e.snippet, "impact") or "").lower() == "high"
            or (parse_field(e.snippet, "probability") or "").lower() == "high"
        ]
        display = (high_risk or risk_ev)[:5]

        if is_ar:
            lines = [f"**⚠️ سجل المخاطر** — {len(risk_ev)} مخاطر مسجلة"]
            for e in display:
                title = e.label.split("—", 1)[-1].strip() if "—" in e.label else e.label
                prob = parse_field(e.snippet, "probability") or "—"
                impact = parse_field(e.snippet, "impact") or "—"
                lines.append(f"  - #{e.source_id}: {title[:70]} (احتمالية={prob}, تأثير={impact})")
        else:
            lines = [f"**⚠️ Risk Register** — {len(risk_ev)} recorded risk(s)"]
            for e in display:
                title = e.label.split("—", 1)[-1].strip() if "—" in e.label else e.label
                prob = parse_field(e.snippet, "probability") or "—"
                impact = parse_field(e.snippet, "impact") or "—"
                lines.append(f"  - #{e.source_id}: {title[:70]} (probability={prob}, impact={impact})")

        sections.append("\n".join(lines))
        cited.extend(f"#{e.source_id}" for e in display[:3])

    # ── 5. Procurement risks (late POs) ───────────────────────────────────────
    if po_ev:
        if is_ar:
            lines = [f"**📦 مخاطر المشتريات** — {len(po_ev)} أمر شراء متأخر"]
            for e in po_ev[:3]:
                lines.append(f"  - {e.source_id}: {e.snippet[:80]}")
        else:
            lines = [f"**📦 Procurement Risks** — {len(po_ev)} late purchase order(s)"]
            for e in po_ev[:3]:
                lines.append(f"  - {e.source_id}: {e.snippet[:80]}")

        sections.append("\n".join(lines))
        cited.extend(e.source_id for e in po_ev[:3])

    if not sections:
        return None

    cited_str = " ".join(f"[{c}]" for c in list(dict.fromkeys(cited))[:12])

    if is_ar:
        title = "**ملخص المخاطر الرئيسية**\n"
        footer = f"\nالمصادر: {cited_str}" if cited_str else ""
    else:
        title = "**Main Risk Summary**\n"
        footer = f"\nSources: {cited_str}" if cited_str else ""

    return title + "\n\n".join(sections) + footer


# ─────────────────────────────────────────────────────────────────────────────
# Health score answer helpers
# ─────────────────────────────────────────────────────────────────────────────

_HEALTH_SCORE_RE = re.compile(r"score=(\d+)", re.IGNORECASE)
_HEALTH_LEVEL_RE = re.compile(r"level=(Excellent|Good|At Risk|Critical)", re.IGNORECASE)
_HEALTH_REASONS_RE = re.compile(r"reasons=(.+)$", re.IGNORECASE | re.MULTILINE)


def _parse_health_score(snippet: str) -> Optional[int]:
    m = _HEALTH_SCORE_RE.search(snippet)
    return int(m.group(1)) if m else None


def _parse_health_level(snippet: str) -> Optional[str]:
    m = _HEALTH_LEVEL_RE.search(snippet)
    return m.group(1) if m else None


def _health_evidence(evidence: list[Evidence]) -> list[Evidence]:
    return [e for e in evidence if e.source_type == "project_health"]


_TRAILING_CODE_RE = re.compile(r"\s*\([A-Z]{2,}-\d+\)\s*$")


def _health_project_name(ev: Evidence) -> str:
    """Extract clean project name from a health evidence item.

    Health labels are "Health Score — Project Name (PRJ-0032)".
    parse_project_name returns "Project Name (PRJ-0032)" which, when
    formatted as **Name** (code), produces ugly duplication.
    This helper strips the trailing code from the name.
    """
    raw = parse_project_name(ev)
    return _TRAILING_CODE_RE.sub("", raw).strip()


def _answer_lowest_health(evidence: list[Evidence], is_ar: bool) -> Optional[str]:
    health_ev = _health_evidence(evidence)
    if not health_ev:
        return None

    scored = [((_parse_health_score(e.snippet) or 100), e) for e in health_ev]
    scored.sort(key=lambda x: x[0])
    worst_score, worst_ev = scored[0]
    name = _health_project_name(worst_ev)
    code = parse_project_code(worst_ev)
    level = _parse_health_level(worst_ev.snippet) or "Unknown"
    m = _HEALTH_REASONS_RE.search(worst_ev.snippet)
    reasons_raw = m.group(1) if m else ""
    reason_bullets = "\n".join(f"  • {r.strip()}" for r in reasons_raw.split("|") if r.strip())

    if is_ar:
        return (
            f"المشروع الأقل صحةً هو **{name}** ({code}) بدرجة صحة **{worst_score}/100** "
            f"(المستوى: {level}).\n\n"
            f"أسباب انخفاض الدرجة:\n{reason_bullets or '  • لا توجد أسباب محددة'}\n\n"
            f"المرجع: [{code}]"
        )
    return (
        f"The least healthy project is **{name}** ({code}) with a health score of "
        f"**{worst_score}/100** (Level: {level}).\n\n"
        f"Contributing factors:\n{reason_bullets or '  • No issues detected'}\n\n"
        f"Source: [{code}]"
    )


def _answer_unhealthy_projects(evidence: list[Evidence], is_ar: bool) -> Optional[str]:
    health_ev = _health_evidence(evidence)
    if not health_ev:
        return None

    unhealthy = [
        e for e in health_ev
        if _parse_health_level(e.snippet) in ("Critical", "At Risk")
    ]
    if not unhealthy:
        # No unhealthy projects — report good news
        total = len(health_ev)
        if is_ar:
            return f"جميع المشاريع الـ {total} في حالة جيدة أو ممتازة. لا توجد مشاريع حرجة أو في خطر."
        return f"All {total} projects are in Good or Excellent health. No projects are Critical or At Risk."

    # Sort by score ascending (worst first)
    unhealthy.sort(key=lambda e: (_parse_health_score(e.snippet) or 100))

    lines = []
    citations = []
    for e in unhealthy:
        name = _health_project_name(e)
        code = parse_project_code(e)
        score = _parse_health_score(e.snippet) or "N/A"
        level = _parse_health_level(e.snippet) or "Unknown"
        m = _HEALTH_REASONS_RE.search(e.snippet)
        top_reason = ""
        if m:
            parts = [r.strip() for r in m.group(1).split("|") if r.strip()]
            top_reason = f" — {parts[0]}" if parts else ""
        lines.append(f"  • **{name}** ({code}): Score {score}/100 ({level}){top_reason}")
        citations.append(code)

    header = (
        f"يوجد {len(unhealthy)} مشروع غير صحي (حرج أو في خطر):\n"
        if is_ar
        else f"{len(unhealthy)} project{'s' if len(unhealthy) > 1 else ''} {'are' if len(unhealthy) > 1 else 'is'} unhealthy (Critical or At Risk):\n"
    )
    cited_str = ", ".join(f"[{c}]" for c in citations)
    return header + "\n".join(lines) + (f"\n\nSources: {cited_str}" if cited_str else "")


def _answer_health_explain(evidence: list[Evidence], is_ar: bool) -> Optional[str]:
    health_ev = _health_evidence(evidence)
    if not health_ev:
        return None

    # Use the worst-scored project (most likely the one the user is asking about)
    health_ev.sort(key=lambda e: (_parse_health_score(e.snippet) or 100))
    target = health_ev[0]
    name = _health_project_name(target)
    code = parse_project_code(target)
    score = _parse_health_score(target.snippet) or "N/A"
    level = _parse_health_level(target.snippet) or "Unknown"
    m = _HEALTH_REASONS_RE.search(target.snippet)
    reasons_raw = m.group(1) if m else ""
    reason_bullets = "\n".join(f"  • {r.strip()}" for r in reasons_raw.split("|") if r.strip())

    if is_ar:
        return (
            f"**{name}** ({code}) لديها درجة صحة **{score}/100** (المستوى: {level}).\n\n"
            f"الأسباب:\n{reason_bullets or '  • لا توجد مشكلات محددة'}\n\n"
            f"المرجع: [{code}]"
        )
    return (
        f"**{name}** ({code}) has a health score of **{score}/100** (Level: {level}).\n\n"
        f"Reasons:\n{reason_bullets or '  • No issues detected'}\n\n"
        f"Source: [{code}]"
    )


def _answer_highest_health(evidence: list[Evidence], is_ar: bool) -> Optional[str]:
    """Return the project with the highest (best) health score."""
    health_ev = _health_evidence(evidence)
    if not health_ev:
        return None

    scored = [((_parse_health_score(e.snippet) or 0), e) for e in health_ev]
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_ev = scored[0]
    name = _health_project_name(best_ev)
    code = parse_project_code(best_ev)
    level = _parse_health_level(best_ev.snippet) or "Unknown"

    # Runner-up
    runner = ""
    if len(scored) > 1:
        s2, ev2 = scored[1]
        n2, c2, l2 = _health_project_name(ev2), parse_project_code(ev2), _parse_health_level(ev2.snippet) or "Unknown"
        runner = (
            f"\n\nNext: **{n2}** ({c2}) — score {s2}/100 ({l2})."
            if not is_ar
            else f"\n\nيليه: **{n2}** ({c2}) — {s2}/100 ({l2})."
        )

    if is_ar:
        return (
            f"المشروع الأكثر صحةً هو **{name}** ({code}) بدرجة صحة **{best_score}/100** "
            f"(المستوى: {level}).{runner}\n\n"
            f"المرجع: [{code}]"
        )
    return (
        f"The healthiest project is **{name}** ({code}) with a health score of "
        f"**{best_score}/100** (Level: {level}).{runner}\n\n"
        f"Source: [{code}]"
    )


def _answer_best_performing(evidence: list[Evidence], is_ar: bool) -> Optional[str]:
    """Return the best-performing project (health score primary, then status)."""
    health_ev = _health_evidence(evidence)
    project_ev = _project_evidence(evidence)

    if health_ev:
        # Use health score as the primary performance metric
        scored = [((_parse_health_score(e.snippet) or 0), e) for e in health_ev]
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_ev = scored[0]
        name = _health_project_name(best_ev)
        code = parse_project_code(best_ev)
        level = _parse_health_level(best_ev.snippet) or "Unknown"
        m = _HEALTH_REASONS_RE.search(best_ev.snippet)
        reasons_raw = m.group(1) if m else ""
        positives = [r.strip() for r in reasons_raw.split("|") if r.strip() and "No issues" not in r]

        if is_ar:
            lines = [
                f"أفضل مشروع أداءً هو **{name}** ({code}) بدرجة صحة **{best_score}/100** (المستوى: {level}).",
            ]
        else:
            lines = [
                f"**{name}** ({code}) is the best-performing project with a health score of "
                f"**{best_score}/100** (Level: {level}).",
            ]

        if positives:
            if is_ar:
                lines.append("\nالعوامل الإيجابية:")
                lines.extend(f"  • {r}" for r in positives[:4])
            else:
                lines.append("\nContributing strengths:")
                lines.extend(f"  • {r}" for r in positives[:4])

        lines.append(f"\n{'المرجع' if is_ar else 'Source'}: [{code}]")
        return "\n".join(lines)

    if project_ev:
        # No health evidence — fall back to status-based ranking
        active = [e for e in project_ev if (parse_field(e.snippet, "status") or "").lower() == "active"]
        best_pool = active or project_ev
        best_ev = best_pool[0]
        name, code = parse_project_name(best_ev), parse_project_code(best_ev)
        status = parse_field(best_ev.snippet, "status") or "N/A"
        if is_ar:
            return (
                f"بناءً على الأدلة المتاحة، يعدّ **{name}** ({code}) من أفضل المشاريع "
                f"(الحالة: {status}).\n\nالمرجع: [{code}]"
            )
        return (
            f"Based on available evidence, **{name}** ({code}) appears to be performing well "
            f"(Status: {status}).\n\nSource: [{code}]"
        )

    return None


def _compute_risk_score(
    ev: Evidence,
    safety_ev: list[Evidence],
    ncr_ev: list[Evidence],
    health_ev: list[Evidence],
) -> tuple[int, list[str]]:
    """Compute a composite risk score for a project evidence item."""
    pid = ev.project_id
    score = 0
    reasons: list[str] = []

    # Status
    status = (parse_field(ev.snippet, "status") or "").lower()
    if status == "delayed":
        score += 4
        reasons.append("delayed schedule")
    elif status == "on hold":
        score += 2
        reasons.append("on hold")

    # Safety events
    proj_safety = [s for s in safety_ev if s.project_id == pid]
    high_safety = [s for s in proj_safety if (parse_field(s.snippet, "severity") or "").lower() == "high"]
    if high_safety:
        score += len(high_safety) * 3
        reasons.append(f"{len(high_safety)} high-severity safety event(s)")
    elif proj_safety:
        score += len(proj_safety)
        reasons.append(f"{len(proj_safety)} safety event(s)")

    # Open NCRs
    proj_ncr = [n for n in ncr_ev if n.project_id == pid]
    if proj_ncr:
        score += len(proj_ncr)
        reasons.append(f"{len(proj_ncr)} open NCR(s)")

    # Health score
    proj_health = [h for h in health_ev if h.project_id == pid]
    if proj_health:
        hs = _parse_health_score(proj_health[0].snippet) or 100
        level = _parse_health_level(proj_health[0].snippet) or ""
        if level == "Critical":
            score += 6
            reasons.append(f"Critical health score ({hs}/100)")
        elif level == "At Risk":
            score += 3
            reasons.append(f"At Risk health score ({hs}/100)")

    # High budget amplifier (delayed high-budget projects = highest exposure)
    budget = parse_budget(ev.snippet)
    if budget and budget > 10_000_000 and ("delayed schedule" in reasons or "on hold" in reasons):
        score += 1
        reasons.append(f"high financial exposure ({_fmt_budget(budget)})")

    return score, reasons


def _answer_riskiest_project(evidence: list[Evidence], is_ar: bool) -> Optional[str]:
    """Return the riskiest project ranked by a composite cross-domain risk score."""
    project_ev = _project_evidence(evidence)
    if not project_ev:
        return None

    safety_ev = [e for e in evidence if e.source_type == "safety_event"]
    ncr_ev = [e for e in evidence if e.source_type == "ncr"]
    health_ev = _health_evidence(evidence)

    scored = []
    for ev in project_ev:
        sc, reasons = _compute_risk_score(ev, safety_ev, ncr_ev, health_ev)
        scored.append((sc, ev, reasons))

    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    top_score, top_ev, top_reasons = scored[0]
    name = parse_project_name(top_ev)
    code = parse_project_code(top_ev)

    def _risk_bullet(r: str, ar: bool) -> str:
        prefixes = {
            "high-severity safety": ("🔴", "🔴"),
            "safety event": ("🟠", "🟠"),
            "delayed": ("🟠", "🟠"),
            "on hold": ("⚠️", "⚠️"),
            "ncr": ("🟡", "🟡"),
            "critical health": ("🔴", "🔴"),
            "at risk health": ("🟠", "🟠"),
            "financial exposure": ("💰", "💰"),
        }
        for key, (en_pfx, ar_pfx) in prefixes.items():
            if key in r.lower():
                return f"  {en_pfx if not ar else ar_pfx} {r}"
        return f"  ⚠️ {r}"

    if is_ar:
        lines = [
            f"المشروع الأعلى خطورةً هو **{name}** ({code}) بدرجة مخاطرة مركّبة **{top_score}**.",
            "\nعوامل الخطورة الرئيسية:",
        ]
        lines.extend(_risk_bullet(r, True) for r in top_reasons[:5])
    else:
        lines = [
            f"**{name}** ({code}) is the riskiest project with a composite risk score of **{top_score}**.",
            "\n**Key risk factors:**",
        ]
        lines.extend(_risk_bullet(r, False) for r in top_reasons[:5])

    # Full ranking if multiple
    if len(scored) > 1:
        if is_ar:
            lines.append("\n**ترتيب المخاطر (جميع المشاريع):**")
        else:
            lines.append("\n**Risk ranking (all projects):**")
        for i, (sc, ev, rsn) in enumerate(scored[:5], 1):
            n, c = parse_project_name(ev), parse_project_code(ev)
            rsn_short = "; ".join(rsn[:2]) if rsn else "no major risks detected"
            lines.append(f"  {i}. {n} ({c}) — risk score {sc} — {rsn_short}")

    cited = " ".join(f"[{parse_project_code(e)}]" for _, e, _ in scored[:5])
    lines.append(f"\n{'المصادر' if is_ar else 'Sources'}: {cited}")
    return "\n".join(lines)


def _answer_why_explain(
    evidence: list[Evidence], is_ar: bool, last_answer_summary: str = ""
) -> Optional[str]:
    """Handle short 'Why?' / 'Explain' follow-up questions.

    Attempts to explain the most relevant piece of evidence in context.
    Falls back gracefully if there is nothing to explain.
    """
    # First preference: health evidence (explains health scores)
    health_ev = _health_evidence(evidence)
    if health_ev:
        return _answer_health_explain(evidence, is_ar)

    # Second: delayed project explanation
    project_ev = _project_evidence(evidence)
    delayed = [e for e in project_ev if (parse_field(e.snippet, "status") or "").lower() == "delayed"]
    if delayed:
        ev = delayed[0]
        name, code = parse_project_name(ev), parse_project_code(ev)
        planned = parse_field(ev.snippet, "planned_finish") or "N/A"
        if is_ar:
            return (
                f"**{name}** ({code}) مصنّف كمشروع متأخر بناءً على بياناته.\n"
                f"- الإنجاز المخطط: {planned}\n\n"
                f"للحصول على تحليل أعمق، يُوصى بمراجعة تقارير الموقع وسجل الاجتماعات.\n\n"
                f"المرجع: [{code}]"
            )
        return (
            f"**{name}** ({code}) is classified as delayed based on its current records.\n"
            f"- Planned finish: {planned}\n\n"
            f"For deeper analysis, review site reports and meeting records.\n\n"
            f"Source: [{code}]"
        )

    # Third: attention-rank explanation
    safety_ev = [e for e in evidence if e.source_type == "safety_event"]
    ncr_ev = [e for e in evidence if e.source_type == "ncr"]
    if project_ev and (safety_ev or ncr_ev):
        return _answer_attention_rank(evidence, is_ar)

    return None


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def compute_analytical_answer(
    question: str,
    evidence: list[Evidence],
) -> Optional[str]:
    """Compute a specific, data-grounded answer from evidence.

    Returns an answer string when the question type is recognised and
    evidence is sufficient. Returns None to signal the pipeline to fall
    through to the LLM.
    """
    if not evidence:
        return None

    is_ar = _is_arabic(question)
    qtype = detect_query_type(question)

    if qtype == "highest_budget":
        return _answer_ranking_by_budget(evidence, highest=True, is_ar=is_ar)
    if qtype == "lowest_budget":
        return _answer_ranking_by_budget(evidence, highest=False, is_ar=is_ar)
    if qtype == "longest_delay":
        # Rank delayed projects — treat delayed status as the sorting dimension
        # (no delay-days field in current schema; rank by budget as tiebreaker)
        project_ev = _project_evidence(evidence)
        delayed_ev = [e for e in project_ev
                      if (parse_field(e.snippet, "status") or "").lower() == "delayed"]
        if not delayed_ev:
            delayed_ev = project_ev  # show all if no status match
        if not delayed_ev:
            return None
        # Surface the first delayed project with the highest budget (worst impact)
        delayed_ev.sort(key=lambda e: parse_budget(e.snippet) or 0, reverse=True)
        most_critical = delayed_ev[0]
        name = parse_project_name(most_critical)
        code = parse_project_code(most_critical)
        status = parse_field(most_critical.snippet, "status") or "N/A"
        budget = parse_budget(most_critical.snippet)
        planned_finish = parse_field(most_critical.snippet, "planned_finish") or "N/A"
        budget_str = f" | Budget: {_fmt_budget(budget)}" if budget else ""

        if is_ar:
            return (
                f"المشروع الأكثر تأخراً (بناءً على الأدلة المسترجعة) هو **{name}** ({code}).\n\n"
                f"- الحالة: {status}\n"
                f"- الإنجاز المخطط: {planned_finish}"
                + (f"\n- الميزانية: {_fmt_budget(budget)}" if budget else "")
                + f"\n\nالمرجع: [{code}]"
            )
        return (
            f"The most delayed project (from retrieved evidence) is **{name}** ({code}).\n\n"
            f"- Status: {status}\n"
            f"- Planned finish: {planned_finish}"
            f"{budget_str}\n\n"
            f"Source: [{code}]"
        )

    if qtype == "list_by_status":
        return _answer_list_by_status(evidence, question, is_ar)
    if qtype == "tell_more":
        return _answer_tell_more(evidence, is_ar)
    if qtype == "compare":
        return _answer_compare(evidence, is_ar)
    if qtype == "has_safety_ncr":
        return _answer_has_safety_ncr(evidence, is_ar)
    if qtype == "attention_rank":
        return _answer_attention_rank(evidence, is_ar)
    if qtype == "count":
        return _answer_count(evidence, question, is_ar)
    if qtype == "risk_summary":
        return _answer_risk_summary(evidence, is_ar)
    if qtype == "lowest_health":
        return _answer_lowest_health(evidence, is_ar)
    if qtype == "unhealthy_projects":
        return _answer_unhealthy_projects(evidence, is_ar)
    if qtype == "health_explain":
        return _answer_health_explain(evidence, is_ar)
    if qtype == "highest_health":
        return _answer_highest_health(evidence, is_ar)
    if qtype == "best_performing":
        return _answer_best_performing(evidence, is_ar)
    if qtype == "riskiest_project":
        return _answer_riskiest_project(evidence, is_ar)
    if qtype == "why_explain":
        return _answer_why_explain(evidence, is_ar)

    return None
