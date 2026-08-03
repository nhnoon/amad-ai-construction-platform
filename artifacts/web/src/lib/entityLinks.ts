// Maps a backend entity_type (My Work / Notifications / Approvals all use
// the same vocabulary) to the closest real FRONTEND route. The backend's
// own `action_url` (see app/ai/entity_refs.py) is a backend API path
// (e.g. "/projects/3/risks/12"), not a frontend route — this app has no
// per-record detail pages for most of these entities yet, so every link
// lands on the relevant list/workspace page instead. "approval" links to
// the Requests workspace with a `?open=<id>` param it reads on mount to
// auto-select that approval.

import type { ElementType } from "react";
import {
  AlertTriangle,
  CircleAlert,
  ClipboardList,
  FileCheck2,
  ShieldAlert,
  ShoppingCart,
} from "lucide-react";

export type WorkEntityType =
  | "project_risk"
  | "project_issue"
  | "action_item"
  | "safety_event"
  | "ncr"
  | "purchase_request"
  | "approval";

const ENTITY_LABEL: Record<WorkEntityType, string> = {
  project_risk: "Risk",
  project_issue: "Issue",
  action_item: "Action Item",
  safety_event: "Safety Event",
  ncr: "NCR",
  purchase_request: "Purchase Request",
  approval: "Approval",
};

const ENTITY_ICON: Record<WorkEntityType, ElementType> = {
  project_risk: AlertTriangle,
  project_issue: CircleAlert,
  action_item: ClipboardList,
  safety_event: ShieldAlert,
  ncr: ShieldAlert,
  purchase_request: ShoppingCart,
  approval: FileCheck2,
};

export function entityLabel(entityType: string): string {
  return ENTITY_LABEL[entityType as WorkEntityType] ?? entityType.replace(/_/g, " ");
}

export function entityIcon(entityType: string): ElementType {
  return ENTITY_ICON[entityType as WorkEntityType] ?? ClipboardList;
}

export function frontendLinkFor(entityType: string, entityId: number): string {
  switch (entityType as WorkEntityType) {
    case "project_risk":
    case "project_issue":
      return "/risks";
    case "action_item":
      return "/meetings";
    case "safety_event":
    case "ncr":
      return "/safety";
    case "purchase_request":
      return "/procurement";
    case "approval":
      return `/requests?open=${entityId}`;
    default:
      return "/tasks";
  }
}

export function genericStatusBadgeClass(status: string): string {
  const s = status.toLowerCase();
  if (["rejected", "cancelled"].some((k) => s.includes(k))) return "badge-danger";
  if (["closed", "resolved", "completed", "approved", "converted to po"].some((k) => s.includes(k))) return "badge-success";
  if (s === "open" || s === "pending") return "badge-neutral";
  return "badge-warning";
}
