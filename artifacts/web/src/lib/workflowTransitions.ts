// Client-side mirrors of the backend's transition matrices
// (backend/app/ai/workflow_engine.py, backend/app/ai/approval_engine.py).
//
// These exist ONLY so the UI offers the right set of buttons — the
// backend remains the sole enforcement authority. If this copy ever
// drifts from the real matrix, the worst case is a 409 the UI already
// has to handle (see status-transition-control.tsx), never a silent
// incorrect transition.

export const MANAGER_ROLES = ["admin", "executive", "project_manager"] as const;

export type EntityKind =
  | "project_risk"
  | "project_issue"
  | "action_item"
  | "safety_event"
  | "ncr"
  | "purchase_request";

export const TRANSITIONS: Record<EntityKind, Record<string, string[]>> = {
  project_risk: {
    open: ["mitigating", "closed"],
    mitigating: ["open", "closed"],
    closed: ["open"],
  },
  project_issue: {
    open: ["In Progress", "Resolved"],
    "In Progress": ["open", "Resolved"],
    Resolved: ["open"],
  },
  action_item: {
    open: ["In Progress", "Completed"],
    "In Progress": ["open", "Completed"],
    Completed: ["open"],
  },
  safety_event: {
    Open: ["Closed"],
    Closed: ["Open"],
  },
  ncr: {
    Open: ["Under Corrective Action", "Closed"],
    "Under Corrective Action": ["Closed", "Open"],
    Closed: ["Open"],
  },
  purchase_request: {
    "Pending Clarification": ["Under Review", "Returned to Requester"],
    "Under Review": ["Approved", "Needs Rework", "Rejected", "Returned to Requester"],
    "Needs Rework": ["Under Review", "Pending Clarification"],
    "Returned to Requester": ["Pending Clarification", "Under Review"],
    Approved: ["Converted to PO"],
    "Converted to PO": [],
    Rejected: [],
  },
};

// entity kind -> { target status -> field on the patch body that must be
// non-empty for that transition (mirrors workflow_engine.py's
// _require_nonempty call sites exactly). action_item -> Completed is
// deliberately NOT listed here: the backend auto-stamps completed_at to
// today when omitted (see update_action_item), so there's nothing the
// UI needs to force the caller to type.
export const REQUIRED_FIELD_FOR_TRANSITION: Record<EntityKind, Record<string, { field: string; label: string }>> = {
  project_risk: { closed: { field: "mitigation", label: "Mitigation" } },
  project_issue: { Resolved: { field: "resolution", label: "Resolution" } },
  action_item: {},
  safety_event: { Closed: { field: "corrective_action", label: "Corrective action" } },
  ncr: { Closed: { field: "corrective_action", label: "Corrective action" } },
  purchase_request: {
    Rejected: { field: "rework_reason", label: "Reason" },
    "Returned to Requester": { field: "rework_reason", label: "Reason" },
  },
};

export function nextStatuses(entity: EntityKind, currentStatus: string): string[] {
  return TRANSITIONS[entity]?.[currentStatus] ?? [];
}

export function requiredFieldFor(entity: EntityKind, targetStatus: string) {
  return REQUIRED_FIELD_FOR_TRANSITION[entity]?.[targetStatus] ?? null;
}

// Approval Engine (Sprint 5 — app/ai/approval_engine.py::APPROVAL_TRANSITIONS).
export const APPROVAL_TRANSITIONS: Record<string, string[]> = {
  Pending: ["Under Review", "Approved", "Rejected", "Returned", "Cancelled"],
  "Under Review": ["Approved", "Rejected", "Returned", "Cancelled"],
  Returned: ["Under Review", "Approved", "Rejected", "Cancelled"],
  Approved: [],
  Rejected: [],
  Cancelled: [],
};
