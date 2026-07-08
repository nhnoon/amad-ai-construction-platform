import { useQuery } from "@tanstack/react-query";
import { getToken } from "./auth";

// ── Types ──────────────────────────────────────────────────────────────────────

export type AlertSeverity = "critical" | "high" | "medium" | "low";
export type AlertCategory = "health" | "safety" | "procurement" | "quality" | "schedule";

export interface Alert {
  id: string;
  title: string;
  description: string;
  severity: AlertSeverity;
  category: AlertCategory;
  project_id: number | null;
  project_code: string | null;
  project_name: string | null;
  source_type: string;
  source_id: string;
  detected_at: string;
  recommended_action: string;
}

export interface AlertsResponse {
  alerts: Alert[];
  total: number;
}

export interface AlertsSummary {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  by_category: Record<string, number>;
}

// ── Fetch helper ───────────────────────────────────────────────────────────────

async function alertsFetch<T>(path: string): Promise<T> {
  const token = getToken();
  const resp = await fetch(path, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!resp.ok) throw new Error(`Alerts API error: ${resp.status}`);
  return resp.json() as Promise<T>;
}

// ── Hooks ──────────────────────────────────────────────────────────────────────

export interface UseAlertsOptions {
  severity?: string;
  category?: string;
  project_id?: number;
  limit?: number;
  offset?: number;
  enabled?: boolean;
}

export function useAlerts(opts: UseAlertsOptions = {}) {
  const { severity, category, project_id, limit = 100, offset = 0, enabled = true } = opts;

  const params = new URLSearchParams();
  if (severity) params.set("severity", severity);
  if (category) params.set("category", category);
  if (project_id !== undefined) params.set("project_id", String(project_id));
  params.set("limit", String(limit));
  if (offset) params.set("offset", String(offset));

  return useQuery<AlertsResponse>({
    queryKey: ["alerts", severity, category, project_id, limit, offset],
    queryFn: () => alertsFetch<AlertsResponse>(`/api/v1/alerts?${params.toString()}`),
    enabled,
    staleTime: 30_000,
  });
}

export function useAlertsSummary(enabled = true) {
  return useQuery<AlertsSummary>({
    queryKey: ["alerts-summary"],
    queryFn: () => alertsFetch<AlertsSummary>("/api/v1/alerts/summary"),
    enabled,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
}
