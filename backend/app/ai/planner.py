"""Multi-domain query planner and executive summary aggregator.

Handles questions that require more than one retrieval domain:
  "Which delayed projects also have high severity safety events?"
  "Compare procurement delays and NCR counts for active projects."
  "Give me an executive summary."

Design constraints:
- RBAC is enforced independently for every retrieval call.
- No arbitrary SQL generation — only existing authorized retrieval tools.
- Results are bounded per domain to prevent prompt flooding.
- Executive summary is grounded from real DB data; no hallucination.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.ai.retrieval.base import Evidence, RetrievalResult
from app.ai.scope import AIAuthScope

# ------------------------------------------------------------------ #
# Multi-domain detection                                               #
# ------------------------------------------------------------------ #

# Maps intent names to their keyword signals (subset, for scoring)
_DOMAIN_SIGNALS: dict[str, list[str]] = {
    "project_overview": ["project", "projects", "delayed", "status", "budget", "client", "مشروع"],
    "procurement": ["procurement", "purchase order", "purchase request", "delivery", "مشتريات"],
    "suppliers": ["supplier", "vendor", "مورد"],
    "safety": ["safety", "incident", "accident", "سلامة", "حادث"],
    "ncr": ["ncr", "non-conformance", "quality", "defect", "جودة"],
    "site_reports": ["site report", "daily report", "manpower", "تقرير موقع"],
    "meetings": ["meeting", "decision", "اجتماع", "قرار"],
    "risks": ["risk", "issue", "مخاطر"],
}

# Short tokens that must match as whole words (not substrings)
_WORD_BOUNDARY_SIGNALS = {"po", "pr", "ncr", "risk", "issue"}

_MULTI_DOMAIN_CONNECTORS = re.compile(
    r"\b(also|and their|and the|compare|cross|both|as well as|alongside|"
    r"كذلك|مقارنة|أيضاً|وأيضاً)\b",
    re.IGNORECASE,
)

_EXECUTIVE_SUMMARY_PATTERNS = re.compile(
    r"\b(executive summary|management attention|operational risk|key findings|"
    r"what should (i|management|we) (know|focus|look at|pay attention)|"
    r"summarize|summarise|top issues|critical (items|areas|issues)|"
    r"ملخص تنفيذي|ما يجب أن يعرفه|المخاطر الرئيسية)\b",
    re.IGNORECASE,
)

_MAX_EVIDENCE_PER_DOMAIN = 8  # Keep multi-domain evidence bounded


@dataclass
class PlannerResult:
    """Aggregated result from multi-domain planning."""
    domains_used: list[str]
    retrieval_tools_used: list[str]
    evidence: list[Evidence]
    is_multi_domain: bool
    is_executive_summary: bool
    comparison_data: Optional[dict[str, Any]] = None
    key_findings: Optional[list[str]] = None


def _signal_matches(kw: str, text: str) -> bool:
    """Check if a domain signal keyword matches in text.

    Uses word-boundary matching for short tokens to avoid false positives
    (e.g. "pr" matching inside "project").
    """
    if kw in _WORD_BOUNDARY_SIGNALS or (len(kw) <= 3 and kw.isalpha()):
        return bool(re.search(r"\b" + re.escape(kw) + r"\b", text))
    return kw in text


def detect_required_domains(question: str, primary_intent: str) -> list[str]:
    """Detect which domains a question needs.

    Returns a list of domain names (may be 1 for single-domain).
    """
    lower = question.lower()
    scores: dict[str, int] = {}
    for domain, keywords in _DOMAIN_SIGNALS.items():
        score = sum(1 for kw in keywords if _signal_matches(kw, lower))
        if score > 0:
            scores[domain] = score

    if not scores:
        return [primary_intent] if primary_intent != "unknown" else []

    # Start with primary intent
    domains = [primary_intent] if primary_intent in scores else []

    # Add other domains with score > 0 (if multi-domain connectors present)
    if _MULTI_DOMAIN_CONNECTORS.search(question) or len(scores) >= 2:
        for domain, score in sorted(scores.items(), key=lambda x: -x[1]):
            if domain not in domains and score >= 1:
                domains.append(domain)
                if len(domains) >= 3:  # cap at 3 domains
                    break

    if not domains and primary_intent:
        domains = [primary_intent]

    return domains


def is_executive_summary_query(question: str) -> bool:
    """Return True if the question is asking for an executive summary."""
    return bool(_EXECUTIVE_SUMMARY_PATTERNS.search(question))


def execute_multi_domain_plan(
    domains: list[str],
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int],
) -> PlannerResult:
    """Execute retrieval for multiple domains and combine evidence.

    Each domain is authorized independently via the scope.
    Evidence is bounded per domain to keep prompt size manageable.
    """
    from app.ai.retrieval.projects import get_project_overview, get_project_risks, get_health_overview
    from app.ai.retrieval.procurement import (
        get_procurement_summary, get_late_purchase_orders, get_supplier_information,
    )
    from app.ai.retrieval.safety import get_safety_summary, get_open_ncrs
    from app.ai.retrieval.site_reports import get_recent_site_reports
    from app.ai.retrieval.meetings import get_recent_meetings, get_project_decisions

    domain_retrieval_map: dict[str, Any] = {
        "project_overview": lambda: get_project_overview(db=db, scope=scope, project_id=project_id),
        "health": lambda: get_health_overview(db=db, scope=scope, project_id=project_id),
        "procurement": lambda: get_procurement_summary(db=db, scope=scope, project_id=project_id),
        "suppliers": lambda: get_supplier_information(db=db, scope=scope),
        "safety": lambda: get_safety_summary(db=db, scope=scope, project_id=project_id),
        "ncr": lambda: get_open_ncrs(db=db, scope=scope, project_id=project_id),
        "site_reports": lambda: get_recent_site_reports(db=db, scope=scope, project_id=project_id),
        "meetings": lambda: get_recent_meetings(db=db, scope=scope, project_id=project_id),
        "decisions": lambda: get_project_decisions(db=db, scope=scope, project_id=project_id),
        "risks": lambda: get_project_risks(db=db, scope=scope, project_id=project_id),
    }

    all_evidence: list[Evidence] = []
    tools_used: list[str] = []
    domains_executed: list[str] = []

    for domain in domains:
        if domain not in domain_retrieval_map:
            continue
        try:
            result: RetrievalResult = domain_retrieval_map[domain]()
            # Bound per domain
            bounded = result.evidence[:_MAX_EVIDENCE_PER_DOMAIN]
            all_evidence.extend(bounded)
            tools_used.append(domain)
            domains_executed.append(domain)
        except Exception:
            # Authorization errors or DB errors for one domain should not
            # prevent results from others
            pass

    is_exec = len(domains) >= 3 or "project_overview" in domains_executed and len(domains_executed) >= 2

    return PlannerResult(
        domains_used=domains_executed,
        retrieval_tools_used=tools_used,
        evidence=all_evidence,
        is_multi_domain=len(domains_executed) > 1,
        is_executive_summary=is_exec,
    )


def execute_executive_summary(
    db: Session,
    scope: AIAuthScope,
) -> PlannerResult:
    """Build an executive summary by aggregating all key domains.

    Pulls a bounded slice from each major domain so the evidence block
    is comprehensive but not excessively long.
    """
    domains = ["project_overview", "procurement", "safety", "ncr", "site_reports"]
    result = execute_multi_domain_plan(
        domains=domains,
        db=db,
        scope=scope,
        project_id=None,
    )
    result.is_executive_summary = True
    return result


def build_comparison_data(
    evidence: list[Evidence],
    domains: list[str],
) -> Optional[dict[str, Any]]:
    """Build structured comparison_data from multi-domain evidence.

    Returns a dict suitable for frontend rendering, or None if there is
    insufficient data to make a useful comparison.
    """
    if len(domains) < 2 or not evidence:
        return None

    by_domain: dict[str, list[dict[str, Any]]] = {}
    for ev in evidence:
        d = ev.source_type if ev.source_type else "other"
        by_domain.setdefault(d, []).append({
            "label": ev.label,
            "snippet": ev.snippet[:150],
            "source_id": ev.source_id,
        })

    if len(by_domain) < 2:
        return None

    return {
        "domains": domains,
        "by_domain": by_domain,
        "total_evidence": len(evidence),
    }
