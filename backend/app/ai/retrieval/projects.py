"""Project overview and risk retrieval tools."""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.ai.scope import AIAuthScope
from app.models.projects import Project, ProjectRisk, ProjectIssue, ProjectMilestone
from .base import Evidence, RetrievalResult


def get_project_overview(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int] = None,
    limit: int = 10,
) -> RetrievalResult:
    q = db.query(Project)
    if project_id is not None:
        scope.enforce_project_access(project_id)
        q = q.filter(Project.id == project_id)
    else:
        if not scope.has_global_read:
            ids = list(scope.accessible_project_ids)
            if not ids:
                return RetrievalResult(data={}, evidence=[])
            q = q.filter(Project.id.in_(ids))

    projects = q.order_by(Project.id).limit(limit).all()
    if not projects:
        return RetrievalResult(data={}, evidence=[])

    rows = []
    evidence = []
    for p in projects:
        rows.append({
            "id": p.id,
            "code": p.project_code,
            "name": p.project_name,
            "type": p.project_type,
            "client": p.client_name,
            "city": p.city,
            "status": p.status,
            "start_date": p.start_date,
            "planned_finish": p.planned_finish,
            "actual_finish": p.actual_finish,
            "budget": p.budget,
        })
        evidence.append(Evidence(
            source_type="project",
            source_id=p.project_code,
            label=f"Project {p.project_code} — {p.project_name}",
            snippet=(
                f"{p.project_name} ({p.project_code}): status={p.status}, "
                f"client={p.client_name}, city={p.city}, "
                f"start={p.start_date}, planned_finish={p.planned_finish}, "
                f"budget={p.budget:,.0f} SAR"
            ),
            project_id=p.id,
            ui_metadata={"href": f"/projects/{p.id}", "icon": "briefcase"},
        ))

    return RetrievalResult(data={"projects": rows, "total": len(rows)}, evidence=evidence)


def get_additional_project_for_comparison(
    db: Session,
    scope: AIAuthScope,
    exclude_codes: list[str],
    preferred_status: str = "Delayed",
) -> Optional[Evidence]:
    """Retrieve one authorized project not already cited, for comparison expansion.

    Used when a comparison query ("compare it with another project") has fewer
    than two project evidence items.  Authorisation is enforced by scope —
    the same rules as the main retrieval path.

    Preference order:
      1. A project whose status matches ``preferred_status`` and whose code
         is not in ``exclude_codes``.
      2. Any authorized project not in ``exclude_codes`` (different status).

    Returns an Evidence item or None if no additional project can be found.
    """
    q = db.query(Project)
    if not scope.has_global_read:
        ids = list(scope.accessible_project_ids)
        if not ids:
            return None
        q = q.filter(Project.id.in_(ids))

    if exclude_codes:
        q = q.filter(~Project.project_code.in_(exclude_codes))

    # First try preferred status
    p = q.filter(Project.status == preferred_status).order_by(Project.id).first()

    # Fallback: any status
    if p is None:
        p = q.order_by(Project.id).first()

    if p is None:
        return None

    return Evidence(
        source_type="project",
        source_id=p.project_code,
        label=f"Project {p.project_code} — {p.project_name}",
        snippet=(
            f"{p.project_name} ({p.project_code}): status={p.status}, "
            f"client={p.client_name}, city={p.city}, "
            f"start={p.start_date}, planned_finish={p.planned_finish}, "
            f"budget={p.budget:,.0f} SAR"
        ),
        project_id=p.id,
        ui_metadata={"href": f"/projects/{p.id}", "icon": "briefcase"},
    )


def get_project_risks(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int] = None,
    limit: int = 20,
) -> RetrievalResult:
    q = db.query(ProjectRisk)
    if project_id is not None:
        scope.enforce_project_access(project_id)
        q = q.filter(ProjectRisk.project_id == project_id)
    else:
        if not scope.has_global_read:
            ids = list(scope.accessible_project_ids)
            if not ids:
                return RetrievalResult(data={}, evidence=[])
            q = q.filter(ProjectRisk.project_id.in_(ids))

    risks = q.order_by(ProjectRisk.id.desc()).limit(limit).all()
    if not risks:
        return RetrievalResult(data={"risks": [], "total": 0}, evidence=[])

    rows = []
    evidence = []
    for r in risks:
        rows.append({
            "id": r.id,
            "project_id": r.project_id,
            "title": r.title,
            "probability": r.probability,
            "impact": r.impact,
            "status": r.status,
            "owner": r.owner,
            "mitigation": r.mitigation,
        })
        evidence.append(Evidence(
            source_type="project_risk",
            source_id=str(r.id),
            label=f"Risk #{r.id} — {r.title}",
            snippet=(
                f"Risk: {r.title} (probability={r.probability}, "
                f"impact={r.impact}, status={r.status})"
            ),
            project_id=r.project_id,
            ui_metadata={"href": f"/projects/{r.project_id}", "icon": "alert-triangle"},
        ))

    return RetrievalResult(data={"risks": rows, "total": len(rows)}, evidence=evidence)


def get_health_overview(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int] = None,
    limit: int = 60,
) -> RetrievalResult:
    """Compute health scores for projects and return as Evidence snippets.

    Snippet format:
      {name} ({code}): score={score}, level={level}, status={status}, reasons={reasons}
    """
    from app.ai.health_score import compute_health_score

    q = db.query(Project).options(
        joinedload(Project.safety_events),
        joinedload(Project.ncrs),
        joinedload(Project.purchase_orders),
        joinedload(Project.risks),
    )
    if project_id is not None:
        scope.enforce_project_access(project_id)
        q = q.filter(Project.id == project_id)
    else:
        if not scope.has_global_read:
            ids = list(scope.accessible_project_ids)
            if not ids:
                return RetrievalResult(data={}, evidence=[])
            q = q.filter(Project.id.in_(ids))

    projects = q.limit(limit).all()
    if not projects:
        return RetrievalResult(data={}, evidence=[])

    results = []
    for p in projects:
        r = compute_health_score(p)
        results.append(r)

    # Sort by score ascending (worst first) for relevance
    results.sort(key=lambda r: r.score)

    rows = []
    evidence = []
    for r in results:
        reasons_str = " | ".join(r.reasons) if r.reasons else "No issues detected"
        rows.append({
            "project_id": r.project_id,
            "project_code": r.project_code,
            "score": r.score,
            "level": r.level,
            "reasons": r.reasons,
        })
        evidence.append(Evidence(
            source_type="project_health",
            source_id=r.project_code,
            label=f"Health Score — {r.project_name} ({r.project_code})",
            snippet=(
                f"{r.project_name} ({r.project_code}): "
                f"score={r.score}, level={r.level}, status={r.status}, "
                f"reasons={reasons_str}"
            ),
            project_id=r.project_id,
            ui_metadata={"href": f"/projects/{r.project_id}", "icon": "heart-pulse"},
        ))

    return RetrievalResult(data={"health_scores": rows, "total": len(rows)}, evidence=evidence)
