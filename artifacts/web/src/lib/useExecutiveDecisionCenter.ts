import { useQuery } from "@tanstack/react-query";
import { generateExecutiveDecisionCenter, type ExecutiveDecisionSnapshot } from "./mockExecutiveDecisionCenter";

// Executive Decision Center data hook — same shape as the other AI Center
// workspace hooks (useProjectMemory, usePredictiveIntelligence,
// useSupplierRisk, useMaterialIntelligence, useCrossProjectLearning): a
// useQuery wrapper other pages already call this way. Swap the queryFn
// body below for a real executive-aggregation endpoint later — or, once
// the five source modules have real backends, replace this generator
// with real calls into each of them — and no component under
// pages/ai-center/workspaces/executive-decision-center/ needs to change;
// they only ever consume `data`/`isLoading`/`isError` from this hook.

type ProjectInput = { id: number; project_code: string; project_name: string; status: string };

async function loadExecutiveDecisionCenter(projects: ProjectInput[]): Promise<ExecutiveDecisionSnapshot> {
  await new Promise((resolve) => setTimeout(resolve, 500));
  // Stabilization fix: generateExecutiveDecisionCenter's `referenceMs` param
  // already existed for exactly this — pass the real current time so
  // `generatedAt` (and the due-date/timeline math derived from it) reflect
  // when the snapshot actually loaded, instead of silently falling back to
  // the generator's hardcoded default constant on every call.
  return generateExecutiveDecisionCenter(projects, Date.now());
}

export function useExecutiveDecisionCenter(projects: ProjectInput[] | undefined) {
  return useQuery<ExecutiveDecisionSnapshot>({
    queryKey: ["executive-decision-center", (projects ?? []).map((p) => p.id).join(",")],
    queryFn: () => loadExecutiveDecisionCenter(projects ?? []),
    enabled: !!projects && projects.length > 0,
    staleTime: 60_000,
  });
}
