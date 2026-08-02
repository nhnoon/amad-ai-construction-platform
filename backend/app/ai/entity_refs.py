"""Shared entity display helpers (Sprint 4) — one canonical mapping from
(entity_type, row) to a human-readable label and a frontend-agnostic
action URL, reused by app/ai/notification_service.py and app/ai/my_work.py
so the two features can never drift on how an entity is named or linked.

entity_type values match app/ai/ownership_engine.py's ENTITY_* constants
exactly ("project_risk", "project_issue", "action_item", "safety_event",
"ncr", "purchase_request") — the same six entities the Ownership Engine
(Sprint 3) and Core Workflow Engine (Sprint 2) already operate on.

Action URLs mirror the real router paths in app/api/v1/*.py (Sprint 4
Part G: no frontend routes exist to link to yet — these are relative API
paths, kept ready for whatever the frontend eventually maps them to).
"""
from __future__ import annotations

_ACTION_URL_PATH = {
    "project_risk": "/projects/{project_id}/risks/{entity_id}",
    "project_issue": "/projects/{project_id}/issues/{entity_id}",
    "action_item": "/projects/{project_id}/action-items/{entity_id}",
    "safety_event": "/projects/{project_id}/safety-events/{entity_id}",
    "ncr": "/projects/{project_id}/ncrs/{entity_id}",
    # Flat route, not project-nested — matches app/api/v1/procurement.py's
    # existing PurchaseRequest routes exactly (see
    # app/ai/ownership_engine.py::_get_purchase_request_and_project's own
    # note on why this one entity's routes differ from the other five).
    "purchase_request": "/procurement/purchase-requests/{entity_id}",
}


def build_action_url(entity_type: str, project_id: int, entity_id: int) -> str:
    template = _ACTION_URL_PATH.get(entity_type)
    if template is None:
        return f"/{entity_type}/{entity_id}"
    return template.format(project_id=project_id, entity_id=entity_id)


def entity_label(entity_type: str, row) -> str:
    """A short, human-readable label for use in notification titles/messages.
    Deliberately reads only fields that actually exist on each model — no
    entity here gets a fabricated "priority" or "assignee" label it
    doesn't really have (same discipline as workflow_engine.py's own
    per-entity comments, e.g. SafetyEvent having no investigator field)."""
    if entity_type in ("project_risk", "project_issue"):
        return row.title
    if entity_type == "action_item":
        return (row.description or "Action item")[:80]
    if entity_type == "safety_event":
        return f"Safety event ({row.severity})"
    if entity_type == "ncr":
        return f"NCR ({row.ncr_type})"
    if entity_type == "purchase_request":
        return f"Purchase request {row.request_no}"
    return entity_type
