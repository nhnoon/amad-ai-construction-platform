// ── AMAD Copilot — page-context resolution (Phase 3) ────────────────────────
// Pure functions, no I/O. Maps the current wouter route to a business
// context so Copilot can answer vague, page-aware questions ("Summarize
// this page") using that page's own live data — same deterministic,
// no-LLM approach as the topic Intent Engine.

export type PageContextKind =
  | "dashboard"
  | "projects"
  | "project-detail"
  | "procurement"
  | "site-reports"
  | "site-report-detail"
  | "meetings"
  | "rfis"
  | "change-orders"
  | "claims"
  | "documents"
  | "reports"
  | "other";

export interface PageContext {
  kind: PageContextKind;
  projectId?: number;
  reportId?: number;
}

export function resolvePageContext(pathname: string): PageContext {
  if (pathname === "/") return { kind: "dashboard" };

  let m = pathname.match(/^\/projects\/(\d+)\/site-reports\/(\d+)$/);
  if (m) return { kind: "site-report-detail", projectId: Number(m[1]), reportId: Number(m[2]) };

  m = pathname.match(/^\/projects\/(\d+)$/);
  if (m) return { kind: "project-detail", projectId: Number(m[1]) };

  switch (pathname) {
    case "/projects":
      return { kind: "projects" };
    case "/procurement":
      return { kind: "procurement" };
    case "/site-reports":
      return { kind: "site-reports" };
    case "/meetings":
      return { kind: "meetings" };
    case "/rfis":
      return { kind: "rfis" };
    case "/change-orders":
      return { kind: "change-orders" };
    case "/claims":
      return { kind: "claims" };
    case "/documents":
      return { kind: "documents" };
    case "/reports":
      return { kind: "reports" };
    default:
      return { kind: "other" };
  }
}

export const CONTEXT_LABEL: Record<PageContextKind, string> = {
  dashboard: "Dashboard",
  projects: "Projects",
  "project-detail": "Project",
  procurement: "Procurement",
  "site-reports": "Site Reports",
  "site-report-detail": "Site Report",
  meetings: "Meetings",
  rfis: "RFIs",
  "change-orders": "Change Orders",
  claims: "Claims",
  documents: "Documents",
  reports: "Reports",
  other: "",
};

const PAGE_AWARE_PATTERNS: RegExp[] = [
  /summarize\s+this\s+page/i,
  /summarize\s+page/i,
  /what\s+needs\s+attention/i,
  /main\s+risks?/i,
  /executive\s+overview/i,
  /give\s+me\s+an\s+overview/i,
  /لخّص هذه الصفحة|لخص هذه الصفحة/,
];

export function isPageAwareQuery(message: string): boolean {
  const trimmed = message.trim();
  if (!trimmed) return false;
  return PAGE_AWARE_PATTERNS.some((p) => p.test(trimmed));
}

export const INSUFFICIENT_DATA_REPLY = "Insufficient live data is available for this page.";
