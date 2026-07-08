import { useQuery } from "@tanstack/react-query";
import { getToken } from "./auth";
import type { ProjectBrief, RiskCategory } from "./useExecutive";

// ── Types matching backend ExecutiveWeeklyReport schema ───────────────────────

export interface ReportPeriod {
  start_date: string;
  end_date: string;
  week_number: number;
  year: number;
  label: string;
}

export interface HealthDistribution {
  excellent: number;
  good: number;
  at_risk: number;
  critical: number;
  total: number;
  average_score: number;
}

export interface ReportAlert {
  severity: string;
  category: string;
  title: string;
  description: string;
  project_code: string | null;
}

export interface ProcurementBlocker {
  label: string;
  count: number;
  detail: string;
  severity: string;
}

export interface SafetyHighlight {
  label: string;
  count: number;
  detail: string;
  severity: string;
}

export interface QualityHighlight {
  label: string;
  count: number;
  detail: string;
  severity: string;
}

export interface RecommendedAction {
  priority: number;
  area: string;
  action: string;
  rationale: string;
}

export interface SourceReference {
  source: string;
  record_count: number;
  description: string;
}

export interface ExecutiveWeeklyReport {
  report_period: ReportPeriod;
  generated_at: string;
  portfolio_summary: string;
  portfolio_status: string;
  portfolio_score: number;
  health_distribution: HealthDistribution;
  top_priorities: ProjectBrief[];
  biggest_risks: RiskCategory[];
  critical_alerts: ReportAlert[];
  procurement_blockers: ProcurementBlocker[];
  safety_highlights: SafetyHighlight[];
  quality_highlights: QualityHighlight[];
  recommended_actions: RecommendedAction[];
  sources: SourceReference[];
}

// ── Fetch helper ───────────────────────────────────────────────────────────────

async function reportFetch<T>(path: string): Promise<T> {
  const token = getToken();
  const resp = await fetch(path, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!resp.ok) throw new Error(`Reports API error: ${resp.status}`);
  return resp.json() as Promise<T>;
}

// ── Hook ───────────────────────────────────────────────────────────────────────

export function useExecutiveWeeklyReport(enabled = true) {
  return useQuery<ExecutiveWeeklyReport>({
    queryKey: ["executive-weekly-report"],
    queryFn: () =>
      reportFetch<ExecutiveWeeklyReport>("/api/v1/reports/executive-weekly"),
    enabled,
    staleTime: 300_000,   // 5 min — reports don't need to refresh often
    refetchInterval: 600_000, // 10 min
  });
}
