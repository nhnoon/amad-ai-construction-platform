import { useQuery } from "@tanstack/react-query";
import { generatePredictiveIntelligence, type PredictivePortfolioSnapshot } from "./mockPredictiveIntelligence";

// Predictive Intelligence data hook — same shape as lib/useProjectMemory.ts
// and lib/useExecutive.ts: a useQuery wrapper other pages already call this
// way. Swap the queryFn body below for a real forecasting endpoint later
// (e.g. `/api/v1/projects/predictions`) and no component under
// pages/ai-center/workspaces/predictive-intelligence/ needs to change —
// they only ever consume `data`/`isLoading`/`isError` from this hook.

type ProjectInput = { id: number; project_code: string; project_name: string; status: string };

async function loadPredictiveIntelligence(projects: ProjectInput[]): Promise<PredictivePortfolioSnapshot> {
  await new Promise((resolve) => setTimeout(resolve, 500));
  return generatePredictiveIntelligence(projects);
}

export function usePredictiveIntelligence(projects: ProjectInput[] | undefined) {
  return useQuery<PredictivePortfolioSnapshot>({
    queryKey: ["predictive-intelligence", (projects ?? []).map((p) => p.project_code).join(",")],
    queryFn: () => loadPredictiveIntelligence(projects ?? []),
    enabled: !!projects && projects.length > 0,
    staleTime: 60_000,
  });
}
