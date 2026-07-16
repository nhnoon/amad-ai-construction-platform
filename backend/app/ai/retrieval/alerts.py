"""Alert retrieval — grounding evidence built from the existing deterministic
Smart Alerts Center generator (app/api/v1/alerts.py::_generate_alerts).

Reuses that generator as-is rather than re-deriving alert logic (per the
Knowledge Access Layer's "consolidate, don't rebuild" constraint). That
generator itself has no RBAC/org scoping — it loads every project — so this
module is the enforcement point: alerts are filtered down to the caller's
accessible projects (or returned unfiltered for has_global_read roles)
before ever becoming Evidence.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.ai.scope import AIAuthScope
from app.api.v1.alerts import _generate_alerts
from .base import Evidence, RetrievalResult

_DEFAULT_LIMIT = 10


def get_active_alerts(
    db: Session,
    scope: AIAuthScope,
    project_id: Optional[int] = None,
    limit: int = _DEFAULT_LIMIT,
) -> RetrievalResult:
    """Active deterministic alerts, scoped to the caller's accessible
    projects and bounded to `limit` (highest severity first — the
    generator already sorts critical -> high -> medium -> low)."""
    if project_id is not None:
        scope.enforce_project_access(project_id)

    alerts = _generate_alerts(db)

    if project_id is not None:
        alerts = [a for a in alerts if a.project_id == project_id]
    elif not scope.has_global_read:
        ids = set(scope.accessible_project_ids)
        alerts = [a for a in alerts if a.project_id in ids]

    alerts = alerts[:limit]
    if not alerts:
        return RetrievalResult(data={"alerts": [], "total": 0}, evidence=[])

    rows = []
    evidence = []
    for a in alerts:
        rows.append({
            "id": a.id,
            "title": a.title,
            "severity": a.severity,
            "category": a.category,
            "project_id": a.project_id,
            "project_code": a.project_code,
        })
        evidence.append(Evidence(
            source_type="alert",
            source_id=a.id,
            label=f"Alert: {a.title}",
            snippet=(
                f"[{a.severity.upper()}/{a.category}] {a.title}: {a.description} "
                f"Recommended action: {a.recommended_action}"
            ),
            project_id=a.project_id,
            ui_metadata={"href": "/alerts", "icon": "alert-triangle"},
        ))

    return RetrievalResult(data={"alerts": rows, "total": len(rows)}, evidence=evidence)
