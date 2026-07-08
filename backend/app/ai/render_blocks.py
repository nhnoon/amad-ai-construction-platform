"""Structured render-block generation for Copilot answers.

Called alongside compute_analytical_answer() in the pipeline.
Produces typed block dicts directly from Evidence fields —
never by parsing answer_text — so the frontend can render
polished UI without guessing from markdown.

Block types
───────────
  project_list    — list of project cards
  project_card    — single highlighted project (ranking / detail)
  comparison      — two projects side-by-side with metrics table
  safety_summary  — severity counts + notable events
  ncr_summary     — NCR counts + items
  risk_summary    — categorised risk sections (🔴🟠🟡⚠️📦)
  citations       — grouped source codes
"""
from __future__ import annotations

from typing import Any, Optional

from app.ai.analyst import (
    _fmt_budget,
    _project_evidence,
    detect_query_type,
    parse_budget,
    parse_field,
    parse_project_code,
    parse_project_name,
)
from app.ai.retrieval.base import Evidence


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _project_dict(ev: Evidence) -> dict[str, Any]:
    budget = parse_budget(ev.snippet)
    return {
        "name": parse_project_name(ev),
        "code": parse_project_code(ev),
        "status": parse_field(ev.snippet, "status") or "",
        "budget": budget,
        "budget_fmt": _fmt_budget(budget) if budget else None,
        "city": parse_field(ev.snippet, "city") or "",
        "client": parse_field(ev.snippet, "client") or "",
        "start": parse_field(ev.snippet, "start") or None,
        "planned_finish": parse_field(ev.snippet, "planned_finish") or None,
    }


def _citations_block(codes: list[str]) -> dict[str, Any]:
    return {"type": "citations", "codes": list(dict.fromkeys(codes))}


def _proj_code_for_pid(
    project_id: Optional[int],
    project_ev: list[Evidence],
) -> Optional[str]:
    if project_id is None:
        return None
    match = next((e for e in project_ev if e.project_id == project_id), None)
    return parse_project_code(match) if match else None


# ─────────────────────────────────────────────────────────────────────────────
# Per-type block builders
# ─────────────────────────────────────────────────────────────────────────────

def _blocks_ranking_by_budget(
    evidence: list[Evidence], highest: bool
) -> list[dict[str, Any]]:
    project_ev = _project_evidence(evidence)
    if not project_ev:
        return []

    budgets = [(parse_budget(e.snippet), e) for e in project_ev]
    budgets = [(b, e) for b, e in budgets if b is not None]
    if not budgets:
        return []

    budgets.sort(key=lambda x: x[0], reverse=highest)
    best_budget, best_ev = budgets[0]
    proj = _project_dict(best_ev)

    highlight = {
        "label_en": "highest budget" if highest else "lowest budget",
        "label_ar": "أعلى ميزانية" if highest else "أقل ميزانية",
        "value": _fmt_budget(best_budget),
    }

    runner_up = None
    if len(budgets) > 1:
        _, second_ev = budgets[1]
        sb = parse_budget(second_ev.snippet)
        runner_up = {
            "name": parse_project_name(second_ev),
            "code": parse_project_code(second_ev),
            "budget_fmt": _fmt_budget(sb) if sb else None,
        }

    blocks: list[dict[str, Any]] = [
        {
            "type": "project_card",
            "project": proj,
            "highlight": highlight,
            "runner_up": runner_up,
        }
    ]
    cited = [proj["code"]]
    if runner_up:
        cited.append(runner_up["code"])
    blocks.append(_citations_block(cited))
    return blocks


def _blocks_list_by_status(
    evidence: list[Evidence], question: str
) -> list[dict[str, Any]]:
    project_ev = _project_evidence(evidence)
    if not project_ev:
        return []

    lower_q = question.lower()
    if "delayed" in lower_q or "late" in lower_q or "behind" in lower_q or "متأخر" in question:
        target_status = "delayed"
        filter_label_en = "Delayed"
        filter_label_ar = "متأخرة"
    elif "active" in lower_q or "ongoing" in lower_q or "نشط" in question:
        target_status = "active"
        filter_label_en = "Active"
        filter_label_ar = "نشطة"
    elif "on hold" in lower_q or "paused" in lower_q or "معلق" in question:
        target_status = "on hold"
        filter_label_en = "On Hold"
        filter_label_ar = "معلقة"
    elif "completed" in lower_q or "مكتمل" in question:
        target_status = "completed"
        filter_label_en = "Completed"
        filter_label_ar = "مكتملة"
    else:
        target_status = None
        filter_label_en = "All"
        filter_label_ar = "الكل"

    if target_status:
        filtered = [
            e for e in project_ev
            if (parse_field(e.snippet, "status") or "").lower() == target_status.lower()
        ]
        if not filtered:
            filtered = project_ev
    else:
        filtered = project_ev

    if not filtered:
        return []

    projects = [_project_dict(e) for e in filtered]
    blocks: list[dict[str, Any]] = [
        {
            "type": "project_list",
            "total": len(projects),
            "filter_label_en": filter_label_en,
            "filter_label_ar": filter_label_ar,
            "projects": projects,
        }
    ]
    blocks.append(_citations_block([p["code"] for p in projects]))
    return blocks


def _blocks_tell_more(evidence: list[Evidence]) -> list[dict[str, Any]]:
    project_ev = _project_evidence(evidence)
    if not project_ev:
        return []

    ev = project_ev[0]
    proj = _project_dict(ev)

    # Attach associated safety / NCR counts
    safety_ev = [e for e in evidence if e.source_type == "safety_event"
                 and e.project_id == ev.project_id]
    ncr_ev = [e for e in evidence if e.source_type == "ncr"
              and e.project_id == ev.project_id]
    if safety_ev:
        high = [e for e in safety_ev
                if (parse_field(e.snippet, "severity") or "").lower() == "high"]
        proj["safety_count"] = len(safety_ev)
        proj["safety_high"] = len(high)
    if ncr_ev:
        proj["ncr_count"] = len(ncr_ev)

    blocks: list[dict[str, Any]] = [
        {
            "type": "project_card",
            "project": proj,
            "highlight": None,
            "runner_up": None,
        }
    ]
    cited = [proj["code"]]
    cited.extend(f"SE-{e.source_id}" for e in safety_ev[:3])
    cited.extend(f"NCR-{e.source_id}" for e in ncr_ev[:3])
    blocks.append(_citations_block(cited))
    return blocks


def _blocks_compare(evidence: list[Evidence]) -> list[dict[str, Any]]:
    project_ev = _project_evidence(evidence)
    if len(project_ev) < 2:
        return []

    a, b = project_ev[0], project_ev[1]
    pa, pb = _project_dict(a), _project_dict(b)
    ba, bb = pa["budget"], pb["budget"]

    budget_winner: Optional[str] = None
    if ba is not None and bb is not None:
        budget_winner = "a" if ba > bb else ("b" if bb > ba else None)

    metrics = [
        {
            "label_en": "Status",
            "label_ar": "الحالة",
            "a": pa["status"],
            "b": pb["status"],
            "winner": None,
        },
        {
            "label_en": "Budget",
            "label_ar": "الميزانية",
            "a": pa["budget_fmt"] or "N/A",
            "b": pb["budget_fmt"] or "N/A",
            "winner": budget_winner,
        },
        {
            "label_en": "City",
            "label_ar": "المدينة",
            "a": pa["city"],
            "b": pb["city"],
            "winner": None,
        },
        {
            "label_en": "Client",
            "label_ar": "العميل",
            "a": pa["client"],
            "b": pb["client"],
            "winner": None,
        },
        {
            "label_en": "Start",
            "label_ar": "تاريخ البدء",
            "a": pa["start"] or "N/A",
            "b": pb["start"] or "N/A",
            "winner": None,
        },
        {
            "label_en": "Planned finish",
            "label_ar": "الإنجاز المخطط",
            "a": pa["planned_finish"] or "N/A",
            "b": pb["planned_finish"] or "N/A",
            "winner": None,
        },
    ]

    blocks: list[dict[str, Any]] = [
        {
            "type": "comparison",
            "projects": [pa, pb],
            "metrics": metrics,
        }
    ]
    blocks.append(_citations_block([pa["code"], pb["code"]]))
    return blocks


def _blocks_has_safety_ncr(evidence: list[Evidence]) -> list[dict[str, Any]]:
    safety_ev = [e for e in evidence if e.source_type == "safety_event"]
    ncr_ev = [e for e in evidence if e.source_type == "ncr"]

    if not safety_ev and not ncr_ev:
        return []

    blocks: list[dict[str, Any]] = []
    cited: list[str] = []

    if safety_ev:
        high = [e for e in safety_ev
                if (parse_field(e.snippet, "severity") or "").lower() == "high"]
        medium = [e for e in safety_ev
                  if (parse_field(e.snippet, "severity") or "").lower() == "medium"]
        low_ev = [e for e in safety_ev
                  if (parse_field(e.snippet, "severity") or "").lower() == "low"]

        notable = []
        for e in (high or safety_ev)[:3]:
            desc = parse_field(e.snippet, "description") or e.snippet[:80]
            sev = parse_field(e.snippet, "severity") or "Unknown"
            notable.append({
                "code": f"SE-{e.source_id}",
                "description": desc[:100],
                "severity": sev,
            })

        blocks.append({
            "type": "safety_summary",
            "total": len(safety_ev),
            "high": len(high),
            "medium": len(medium),
            "low": len(low_ev),
            "notable": notable,
        })
        cited.extend(f"SE-{e.source_id}" for e in safety_ev[:5])

    if ncr_ev:
        open_ncr = [
            e for e in ncr_ev
            if "open" in (parse_field(e.snippet, "status") or "").lower()
            or "corrective" in (parse_field(e.snippet, "status") or "").lower()
        ]
        items = []
        for e in ncr_ev[:5]:
            items.append({
                "code": f"NCR-{e.source_id}",
                "type": parse_field(e.snippet, "type") or "",
                "status": parse_field(e.snippet, "status") or "",
            })

        blocks.append({
            "type": "ncr_summary",
            "total": len(ncr_ev),
            "under_corrective_action": len(open_ncr),
            "items": items,
        })
        cited.extend(f"NCR-{e.source_id}" for e in ncr_ev[:5])

    if cited:
        blocks.append(_citations_block(cited))
    return blocks


def _blocks_risk_summary(evidence: list[Evidence]) -> list[dict[str, Any]]:
    project_ev = _project_evidence(evidence)
    risk_ev = [e for e in evidence if e.source_type == "project_risk"]
    safety_ev = [e for e in evidence if e.source_type == "safety_event"]
    ncr_ev = [e for e in evidence if e.source_type == "ncr"]
    po_ev = [
        e for e in evidence
        if e.source_type == "purchase_order" and "late=True" in e.snippet
    ]

    if not any([safety_ev, risk_ev, ncr_ev, po_ev]) and not project_ev:
        return []

    categories: list[dict[str, Any]] = []
    cited: list[str] = []

    # Safety
    if safety_ev:
        high_sev = [e for e in safety_ev
                    if (parse_field(e.snippet, "severity") or "").lower() == "high"]
        display = high_sev[:3] or safety_ev[:3]
        affected_pids = list(dict.fromkeys(
            e.project_id for e in safety_ev if e.project_id is not None
        ))
        affected_codes = [
            c for c in (
                _proj_code_for_pid(pid, project_ev) for pid in affected_pids[:5]
            ) if c
        ]
        items = []
        if affected_codes:
            items.append({"text": ", ".join(affected_codes), "codes": affected_codes, "label_en": "Affected projects", "label_ar": "المشاريع المتأثرة"})
        for e in display:
            desc = parse_field(e.snippet, "description") or ""
            items.append({"code": f"SE-{e.source_id}", "text": (desc[:70] if desc else e.snippet[:70])})

        subtitle_en = f"{len(safety_ev)} event(s)" + (f" ({len(high_sev)} high-severity)" if high_sev else "")
        subtitle_ar = f"{len(safety_ev)} حدث" + (f" ({len(high_sev)} عالية الخطورة)" if high_sev else "")
        categories.append({
            "color": "red",
            "emoji": "🔴",
            "title_en": "Safety Risks",
            "title_ar": "مخاطر السلامة",
            "subtitle_en": subtitle_en,
            "subtitle_ar": subtitle_ar,
            "items": items,
        })
        cited.extend(f"SE-{e.source_id}" for e in display)

    # Schedule
    delayed_ev = [e for e in project_ev
                  if (parse_field(e.snippet, "status") or "").lower() == "delayed"]
    on_hold_ev = [e for e in project_ev
                  if (parse_field(e.snippet, "status") or "").lower() == "on hold"]
    if delayed_ev or on_hold_ev:
        items = []
        if delayed_ev:
            codes = [parse_project_code(e) for e in delayed_ev[:6]]
            items.append({"codes": codes, "text": f"{len(delayed_ev)} delayed project(s)", "text_ar": f"{len(delayed_ev)} مشاريع متأخرة"})
        if on_hold_ev:
            codes = [parse_project_code(e) for e in on_hold_ev[:4]]
            items.append({"codes": codes, "text": f"{len(on_hold_ev)} on-hold project(s)", "text_ar": f"{len(on_hold_ev)} مشاريع معلقة"})

        categories.append({
            "color": "orange",
            "emoji": "🟠",
            "title_en": "Schedule Risks",
            "title_ar": "مخاطر الجدول الزمني",
            "subtitle_en": None,
            "subtitle_ar": None,
            "items": items,
        })
        cited.extend(parse_project_code(e) for e in (delayed_ev + on_hold_ev)[:5])

    # Quality (NCRs)
    if ncr_ev:
        affected_pids = list(dict.fromkeys(
            e.project_id for e in ncr_ev if e.project_id is not None
        ))
        affected_codes = [
            c for c in (
                _proj_code_for_pid(pid, project_ev) for pid in affected_pids[:5]
            ) if c
        ]
        items = []
        if affected_codes:
            items.append({"text": ", ".join(affected_codes), "codes": affected_codes, "label_en": "Affected projects", "label_ar": "المشاريع المتأثرة"})
        for e in ncr_ev[:3]:
            ncr_type = parse_field(e.snippet, "type") or "—"
            items.append({"code": f"NCR-{e.source_id}", "text": ncr_type[:60]})

        subtitle_en = f"{len(ncr_ev)} open NCR(s)"
        subtitle_ar = f"{len(ncr_ev)} طلب تصحيح مفتوح"
        categories.append({
            "color": "yellow",
            "emoji": "🟡",
            "title_en": "Quality Risks",
            "title_ar": "مخاطر الجودة",
            "subtitle_en": subtitle_en,
            "subtitle_ar": subtitle_ar,
            "items": items,
        })
        cited.extend(f"NCR-{e.source_id}" for e in ncr_ev[:3])

    # Formal risk register
    if risk_ev:
        high_risk = [
            e for e in risk_ev
            if (parse_field(e.snippet, "impact") or "").lower() == "high"
            or (parse_field(e.snippet, "probability") or "").lower() == "high"
        ]
        display = (high_risk or risk_ev)[:5]
        items = []
        for e in display:
            title = e.label.split("—", 1)[-1].strip() if "—" in e.label else e.label
            prob = parse_field(e.snippet, "probability") or "—"
            impact = parse_field(e.snippet, "impact") or "—"
            items.append({
                "code": f"#{e.source_id}",
                "text": f"{title[:70]} (prob={prob}, impact={impact})",
            })

        subtitle_en = f"{len(risk_ev)} recorded risk(s)"
        subtitle_ar = f"{len(risk_ev)} مخاطر مسجلة"
        categories.append({
            "color": "amber",
            "emoji": "⚠️",
            "title_en": "Risk Register",
            "title_ar": "سجل المخاطر",
            "subtitle_en": subtitle_en,
            "subtitle_ar": subtitle_ar,
            "items": items,
        })
        cited.extend(f"#{e.source_id}" for e in display[:3])

    # Procurement
    if po_ev:
        items = []
        for e in po_ev[:3]:
            items.append({"code": e.source_id, "text": e.snippet[:80]})

        subtitle_en = f"{len(po_ev)} late purchase order(s)"
        subtitle_ar = f"{len(po_ev)} أمر شراء متأخر"
        categories.append({
            "color": "blue",
            "emoji": "📦",
            "title_en": "Procurement Risks",
            "title_ar": "مخاطر المشتريات",
            "subtitle_en": subtitle_en,
            "subtitle_ar": subtitle_ar,
            "items": items,
        })
        cited.extend(e.source_id for e in po_ev[:3])

    if not categories:
        return []

    blocks: list[dict[str, Any]] = [
        {"type": "risk_summary", "categories": categories}
    ]
    blocks.append(_citations_block(list(dict.fromkeys(cited))[:12]))
    return blocks


def _blocks_longest_delay(evidence: list[Evidence]) -> list[dict[str, Any]]:
    project_ev = _project_evidence(evidence)
    delayed_ev = [e for e in project_ev
                  if (parse_field(e.snippet, "status") or "").lower() == "delayed"]
    if not delayed_ev:
        delayed_ev = project_ev
    if not delayed_ev:
        return []

    delayed_ev.sort(key=lambda e: parse_budget(e.snippet) or 0, reverse=True)
    ev = delayed_ev[0]
    proj = _project_dict(ev)

    blocks: list[dict[str, Any]] = [
        {
            "type": "project_card",
            "project": proj,
            "highlight": {
                "label_en": "most delayed (highest-budget delayed project)",
                "label_ar": "الأكثر تأخراً",
                "value": proj["budget_fmt"] or proj["status"],
            },
            "runner_up": None,
        }
    ]
    blocks.append(_citations_block([proj["code"]]))
    return blocks


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def _blocks_health_list(evidence: list[Evidence]) -> list[dict[str, Any]]:
    """Build a health_list block from project_health evidence."""
    import re
    _SCORE_RE = re.compile(r"score=(\d+)", re.IGNORECASE)
    _LEVEL_RE = re.compile(r"level=(Excellent|Good|At Risk|Critical)", re.IGNORECASE)
    _REASONS_RE = re.compile(r"reasons=(.+)$", re.IGNORECASE | re.MULTILINE)

    health_ev = [e for e in evidence if e.source_type == "project_health"]
    if not health_ev:
        return []

    items = []
    for e in health_ev:
        sm = _SCORE_RE.search(e.snippet)
        lm = _LEVEL_RE.search(e.snippet)
        rm = _REASONS_RE.search(e.snippet)
        score = int(sm.group(1)) if sm else None
        level = lm.group(1) if lm else None
        reasons_raw = rm.group(1) if rm else ""
        reasons = [r.strip() for r in reasons_raw.split("|") if r.strip()]
        if reasons == ["No issues detected"]:
            reasons = []
        code = e.source_id or ""
        # name from label: "Health Score — Project Name (CODE)"
        name = e.label.replace("Health Score — ", "").strip()
        items.append({
            "code": code,
            "name": name,
            "score": score,
            "level": level,
            "reasons": reasons,
            "href": (e.ui_metadata or {}).get("href", f"/projects/{e.project_id}"),
        })

    # Sort worst first
    items.sort(key=lambda x: (x["score"] or 100))

    codes = [e.source_id for e in health_ev if e.source_id]
    citations = _citations_block(codes) if codes else None
    blocks: list[dict[str, Any]] = [{"type": "health_list", "items": items}]
    if citations:
        blocks.append(citations)
    return blocks


def _blocks_health_card(evidence: list[Evidence]) -> list[dict[str, Any]]:
    """Build a single-project health card (for health_explain queries)."""
    import re
    _SCORE_RE = re.compile(r"score=(\d+)", re.IGNORECASE)
    _LEVEL_RE = re.compile(r"level=(Excellent|Good|At Risk|Critical)", re.IGNORECASE)
    _REASONS_RE = re.compile(r"reasons=(.+)$", re.IGNORECASE | re.MULTILINE)

    health_ev = [e for e in evidence if e.source_type == "project_health"]
    if not health_ev:
        return []

    # Worst-scoring project (most relevant for "explain" queries)
    def _score(e: Evidence) -> int:
        m = _SCORE_RE.search(e.snippet)
        return int(m.group(1)) if m else 100
    target = min(health_ev, key=_score)

    sm = _SCORE_RE.search(target.snippet)
    lm = _LEVEL_RE.search(target.snippet)
    rm = _REASONS_RE.search(target.snippet)
    score = int(sm.group(1)) if sm else None
    level = lm.group(1) if lm else None
    reasons_raw = rm.group(1) if rm else ""
    reasons = [r.strip() for r in reasons_raw.split("|") if r.strip()]
    if reasons == ["No issues detected"]:
        reasons = []

    code = target.source_id or ""
    name = target.label.replace("Health Score — ", "").strip()
    codes = [e.source_id for e in health_ev if e.source_id]
    citations = _citations_block(codes) if codes else None
    blocks: list[dict[str, Any]] = [{
        "type": "health_card",
        "code": code,
        "name": name,
        "score": score,
        "level": level,
        "reasons": reasons,
        "href": (target.ui_metadata or {}).get("href", f"/projects/{target.project_id}"),
    }]
    if citations:
        blocks.append(citations)
    return blocks


def _blocks_attention_rank(evidence: list[Evidence]) -> list[dict[str, Any]]:
    """Build a ranked project list block for attention/priority queries."""
    from app.ai.analyst import (
        _health_evidence, _parse_health_score, _parse_health_level,
    )

    project_ev = _project_evidence(evidence)
    if not project_ev:
        return []

    safety_ev = [e for e in evidence if e.source_type == "safety_event"]
    ncr_ev = [e for e in evidence if e.source_type == "ncr"]
    health_ev = _health_evidence(evidence)

    scored = []
    for ev in project_ev:
        pid = ev.project_id
        score = 0
        status = (parse_field(ev.snippet, "status") or "").lower()
        if status == "delayed":
            score += 3
        if status == "on hold":
            score += 2
        proj_safety = [s for s in safety_ev if s.project_id == pid]
        high_safety = [s for s in proj_safety
                       if (parse_field(s.snippet, "severity") or "").lower() == "high"]
        score += len(high_safety) * 2 + (len(proj_safety) if not high_safety else 0)
        proj_ncr = [n for n in ncr_ev if n.project_id == pid]
        score += len(proj_ncr)
        proj_health = [h for h in health_ev if h.project_id == pid]
        if proj_health:
            hl = _parse_health_level(proj_health[0].snippet) or ""
            if hl == "Critical":
                score += 5
            elif hl == "At Risk":
                score += 2
        scored.append((score, ev))

    scored.sort(key=lambda x: x[0], reverse=True)
    projects = []
    for sc, ev in scored[:8]:
        d = _project_dict(ev)
        d["priority_score"] = sc
        # Attach health data if available
        proj_health = [h for h in health_ev if h.project_id == ev.project_id]
        if proj_health:
            d["health_score"] = _parse_health_score(proj_health[0].snippet)
            d["health_level"] = _parse_health_level(proj_health[0].snippet)
        projects.append(d)

    if not projects:
        return []

    codes = [p["code"] for p in projects if p.get("code")]
    blocks: list[dict[str, Any]] = [
        {
            "type": "project_list",
            "total": len(projects),
            "filter_label_en": "Attention Priority",
            "filter_label_ar": "أولوية الاهتمام",
            "projects": projects,
            "ranked": True,
        }
    ]
    blocks.append(_citations_block(codes))
    return blocks


def _blocks_highest_health(evidence: list[Evidence]) -> list[dict[str, Any]]:
    """Build a health card block for the healthiest project."""
    import re as _re
    _SCORE_RE = _re.compile(r"score=(\d+)", _re.IGNORECASE)
    _LEVEL_RE = _re.compile(r"level=(Excellent|Good|At Risk|Critical)", _re.IGNORECASE)
    _REASONS_RE = _re.compile(r"reasons=(.+)$", _re.IGNORECASE | _re.MULTILINE)

    health_ev = [e for e in evidence if e.source_type == "project_health"]
    if not health_ev:
        return []

    def _score(e: Evidence) -> int:
        m = _SCORE_RE.search(e.snippet)
        return int(m.group(1)) if m else 0

    target = max(health_ev, key=_score)
    sm = _SCORE_RE.search(target.snippet)
    lm = _LEVEL_RE.search(target.snippet)
    rm = _REASONS_RE.search(target.snippet)
    score = int(sm.group(1)) if sm else None
    level = lm.group(1) if lm else None
    reasons_raw = rm.group(1) if rm else ""
    reasons = [r.strip() for r in reasons_raw.split("|") if r.strip()]
    if reasons == ["No issues detected"]:
        reasons = []

    code = target.source_id or ""
    name = target.label.replace("Health Score — ", "").strip()
    codes = [e.source_id for e in health_ev if e.source_id]
    citations = _citations_block(codes) if codes else None
    blocks: list[dict[str, Any]] = [{
        "type": "health_card",
        "code": code,
        "name": name,
        "score": score,
        "level": level,
        "reasons": reasons,
        "href": (target.ui_metadata or {}).get("href", f"/projects/{target.project_id}"),
        "highlight_best": True,
    }]
    if citations:
        blocks.append(citations)
    return blocks


def _blocks_best_performing(evidence: list[Evidence]) -> list[dict[str, Any]]:
    """Build a health_list block sorted best-first for best-performing queries."""
    import re as _re
    _SCORE_RE = _re.compile(r"score=(\d+)", _re.IGNORECASE)
    _LEVEL_RE = _re.compile(r"level=(Excellent|Good|At Risk|Critical)", _re.IGNORECASE)
    _REASONS_RE = _re.compile(r"reasons=(.+)$", _re.IGNORECASE | _re.MULTILINE)

    health_ev = [e for e in evidence if e.source_type == "project_health"]
    if not health_ev:
        return _blocks_list_by_status(evidence, "active")

    items = []
    for e in health_ev:
        sm = _SCORE_RE.search(e.snippet)
        lm = _LEVEL_RE.search(e.snippet)
        rm = _REASONS_RE.search(e.snippet)
        score = int(sm.group(1)) if sm else None
        level = lm.group(1) if lm else None
        reasons_raw = rm.group(1) if rm else ""
        reasons = [r.strip() for r in reasons_raw.split("|") if r.strip()]
        if reasons == ["No issues detected"]:
            reasons = []
        code = e.source_id or ""
        name = e.label.replace("Health Score — ", "").strip()
        items.append({
            "code": code,
            "name": name,
            "score": score,
            "level": level,
            "reasons": reasons,
            "href": (e.ui_metadata or {}).get("href", f"/projects/{e.project_id}"),
        })

    # Sort best first
    items.sort(key=lambda x: (x["score"] or 0), reverse=True)

    codes = [e.source_id for e in health_ev if e.source_id]
    citations = _citations_block(codes) if codes else None
    blocks: list[dict[str, Any]] = [{"type": "health_list", "items": items, "sort_best_first": True}]
    if citations:
        blocks.append(citations)
    return blocks


def compute_render_blocks(
    question: str,
    evidence: list[Evidence],
) -> list[dict[str, Any]]:
    """Return typed render blocks for the given question + evidence.

    Returns an empty list for generic/LLM-handled questions.
    Never raises — returns [] on any unexpected error.
    """
    if not evidence:
        return []

    try:
        qtype = detect_query_type(question)

        if qtype == "highest_budget":
            return _blocks_ranking_by_budget(evidence, highest=True)
        if qtype == "lowest_budget":
            return _blocks_ranking_by_budget(evidence, highest=False)
        if qtype == "longest_delay":
            return _blocks_longest_delay(evidence)
        if qtype == "list_by_status":
            return _blocks_list_by_status(evidence, question)
        if qtype == "tell_more":
            return _blocks_tell_more(evidence)
        if qtype == "compare":
            return _blocks_compare(evidence)
        if qtype == "has_safety_ncr":
            return _blocks_has_safety_ncr(evidence)
        if qtype == "risk_summary":
            return _blocks_risk_summary(evidence)
        if qtype in ("lowest_health", "unhealthy_projects"):
            return _blocks_health_list(evidence)
        if qtype == "health_explain":
            return _blocks_health_card(evidence)
        if qtype == "attention_rank":
            return _blocks_attention_rank(evidence)
        if qtype == "riskiest_project":
            return _blocks_attention_rank(evidence)
        if qtype == "highest_health":
            return _blocks_highest_health(evidence)
        if qtype == "best_performing":
            return _blocks_best_performing(evidence)
        if qtype == "why_explain":
            # Try health card first, then attention rank
            blocks = _blocks_health_card(evidence)
            if blocks:
                return blocks
            return _blocks_attention_rank(evidence)
        # count, generic → no structured blocks
        return []
    except Exception:
        return []
