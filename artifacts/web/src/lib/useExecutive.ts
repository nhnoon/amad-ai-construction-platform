import { useQuery } from "@tanstack/react-query";
import { getToken } from "./auth";

// ── Types matching backend ExecutiveIntelligence schema ────────────────────────

export interface ProjectBrief {
  project_id: number;
  project_code: string;
  project_name: string;
  status: string;
  score: number;
  level: string;
  primary_reason: string;
}

export interface RiskCategory {
  category: string;
  label: string;
  severity: string;
  count: number;
  detail: string;
}

export interface ExecutiveIntelligence {
  portfolio_status: string;
  portfolio_score: number;
  executive_summary: string;
  total_projects: number;
  critical_count: number;
  at_risk_count: number;
  good_count: number;
  excellent_count: number;
  top_priorities: ProjectBrief[];
  biggest_risks: RiskCategory[];
  best_projects: ProjectBrief[];
  attention_required: ProjectBrief[];
}

// ── Fetch helper ───────────────────────────────────────────────────────────────

async function execFetch<T>(path: string): Promise<T> {
  const token = getToken();
  const resp = await fetch(path, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!resp.ok) throw new Error(`Executive API error: ${resp.status}`);
  return resp.json() as Promise<T>;
}

// ── Hook ───────────────────────────────────────────────────────────────────────

export function useExecutive(enabled = true) {
  return useQuery<ExecutiveIntelligence>({
    queryKey: ["executive-intelligence"],
    queryFn: () =>
      execFetch<ExecutiveIntelligence>("/api/v1/executive"),
    enabled,
    staleTime: 60_000,
    refetchInterval: 120_000,
  });
}
