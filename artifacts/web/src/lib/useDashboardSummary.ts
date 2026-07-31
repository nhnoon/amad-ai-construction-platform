import { useQuery } from "@tanstack/react-query";
import { getToken } from "./auth";

// ── Types matching backend DashboardSummary schema ─────────────────────────
// Hand-written rather than pulled from the generated @workspace/api-client-
// react client: that client is generated from a checked-in openapi.yaml
// snapshot, which lags behind backend schema changes until someone re-runs
// codegen. Every other recent addition in this app (useExecutive.ts,
// useAlerts.ts, aiCenterClient.ts) follows this same hand-written-client
// pattern for exactly that reason — see those files for precedent.

export interface DashboardSummary {
  total_projects: number;
  active_projects: number;
  completed_projects: number;
  delayed_projects: number;
  on_hold_projects: number;
  total_suppliers: number;
  active_suppliers: number;
  total_purchase_requests: number;
  open_purchase_requests: number;
  total_purchase_orders: number;
  late_purchase_orders: number;
  total_safety_events: number;
  high_severity_events: number;
  total_ncrs: number;
  open_ncrs: number;
  total_site_reports: number;
  total_meetings: number;
  total_decisions: number;
  total_rfis: number;
}

async function dashboardFetch<T>(path: string): Promise<T> {
  const token = getToken();
  const resp = await fetch(path, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!resp.ok) throw new Error(`Dashboard API error: ${resp.status}`);
  return resp.json() as Promise<T>;
}

export function useDashboardSummary(enabled = true) {
  return useQuery<DashboardSummary>({
    queryKey: ["dashboard-summary"],
    queryFn: () => dashboardFetch<DashboardSummary>("/api/v1/dashboard/summary"),
    enabled,
    staleTime: 60_000,
    refetchInterval: 120_000,
  });
}
