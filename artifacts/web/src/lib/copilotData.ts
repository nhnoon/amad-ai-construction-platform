import { useQuery } from "@tanstack/react-query";
import { getToken } from "./auth";

// ── AMAD Copilot — project-scoped record fetchers ───────────────────────────
// These call the exact same existing backend endpoints the Claims,
// Change Orders, and RFIs pages already use (claims.tsx, change-orders.tsx,
// rfis.tsx) — no new endpoints, same auth pattern as useExecutive.ts.

async function fetchJson<T>(url: string): Promise<T> {
  const token = getToken();
  const resp = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!resp.ok) throw new Error(`Request failed: ${resp.status}`);
  return resp.json() as Promise<T>;
}

export interface ClaimRecord {
  id: number;
  project_id: number;
  claim_number: string;
  claim_type: string;
  amount: number;
  status: string;
  narrative: string;
}

export interface ChangeOrderRecord {
  id: number;
  project_id: number;
  co_number: string;
  description: string;
  value: number;
  status: string;
}

export interface DocumentRecord {
  id: number;
  doc_type: string;
  title: string;
  doc_date: string;
  content_summary: string;
}

export interface CorrespondenceRecord {
  id: number;
  related_record_type: string;
  sent_date: string;
  sender: string;
  recipient: string;
  subject: string;
}

export function useCopilotClaims(projectId: number | undefined, enabled: boolean) {
  return useQuery<ClaimRecord[]>({
    queryKey: ["copilot-claims", projectId],
    queryFn: () => fetchJson<ClaimRecord[]>(`/api/v1/projects/${projectId}/claims?limit=100`),
    enabled: enabled && projectId != null,
  });
}

export function useCopilotChangeOrders(projectId: number | undefined, enabled: boolean) {
  return useQuery<ChangeOrderRecord[]>({
    queryKey: ["copilot-change-orders", projectId],
    queryFn: () => fetchJson<ChangeOrderRecord[]>(`/api/v1/projects/${projectId}/change-orders?limit=100`),
    enabled: enabled && projectId != null,
  });
}

export function useCopilotDocuments(projectId: number | undefined, enabled: boolean) {
  return useQuery<DocumentRecord[]>({
    queryKey: ["copilot-documents", projectId],
    queryFn: () => fetchJson<DocumentRecord[]>(`/api/v1/projects/${projectId}/documents?limit=100`),
    enabled: enabled && projectId != null,
  });
}

export function useCopilotCorrespondence(projectId: number | undefined, enabled: boolean) {
  return useQuery<CorrespondenceRecord[]>({
    queryKey: ["copilot-correspondence", projectId],
    queryFn: () => fetchJson<CorrespondenceRecord[]>(`/api/v1/projects/${projectId}/correspondence?limit=100`),
    enabled: enabled && projectId != null,
  });
}

export function isRfiLike(value: string | null | undefined): boolean {
  if (!value) return false;
  return value.toLowerCase().includes("rfi");
}

// ── Page-context data fetchers (Phase 3) ────────────────────────────────────
// Same auth pattern, same existing endpoints already used by
// site-report-detail.tsx and the per-project record pages above.

async function postJson<T>(url: string): Promise<T> {
  const token = getToken();
  const resp = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!resp.ok) throw new Error(`Request failed: ${resp.status}`);
  return resp.json() as Promise<T>;
}

export interface SiteReportAnalysis {
  analysis_generated_from: string;
  executive_summary: string;
  progress_assessment: string;
  delay_analysis: string;
  risk_analysis: string;
  safety_findings: string[];
  quality_findings: string[];
  schedule_impact: string;
  recommended_actions: string[];
  priority_level: string;
  escalation_required: boolean;
  confidence_score: number;
}

// Same endpoint/method as the "Analyze with AMAD AI" button on the Site
// Report Detail page (site-report-detail.tsx) — a deterministic analysis,
// not an LLM call. Cached by React Query so asking twice doesn't re-run it.
export function useCopilotSiteReportAnalysis(
  projectId: number | undefined,
  reportId: number | undefined,
  enabled: boolean
) {
  return useQuery<SiteReportAnalysis>({
    queryKey: ["copilot-site-report-analysis", projectId, reportId],
    queryFn: () => postJson<SiteReportAnalysis>(`/api/v1/projects/${projectId}/site-reports/${reportId}/analyze`),
    enabled: enabled && projectId != null && reportId != null,
    staleTime: 5 * 60_000,
  });
}

// Aggregates real claims across every currently-loaded portfolio project via
// the same per-project claims endpoint claims.tsx uses — no portfolio-wide
// claims endpoint exists, so this is the only non-fabricated way to answer
// "how many claims does the portfolio have". Individual project fetch
// failures are excluded from the aggregate rather than failing the whole
// query.
export function useCopilotPortfolioClaims(projectIds: number[] | undefined, enabled: boolean) {
  return useQuery<ClaimRecord[]>({
    queryKey: ["copilot-portfolio-claims", (projectIds ?? []).join(",")],
    queryFn: async () => {
      const ids = projectIds ?? [];
      const results = await Promise.allSettled(
        ids.map((id) => fetchJson<ClaimRecord[]>(`/api/v1/projects/${id}/claims?limit=100`))
      );
      return results.flatMap((r) => (r.status === "fulfilled" ? r.value : []));
    },
    enabled: enabled && !!projectIds?.length,
  });
}
