import { useQuery } from "@tanstack/react-query";
import { generateMaterialIntelligence, type MaterialIntelligenceSnapshot } from "./mockMaterialIntelligence";

// Material Intelligence data hook — same shape as lib/useSupplierRisk.ts,
// lib/useProjectMemory.ts, and lib/usePredictiveIntelligence.ts: a
// useQuery wrapper other pages already call this way. Swap the queryFn
// body below for a real material-pricing endpoint or external market-data
// integration later (e.g. `/api/v1/materials/intelligence`) and no
// component under pages/ai-center/workspaces/material-intelligence/ needs
// to change — they only ever consume `data`/`isLoading`/`isError` from
// this hook.

type SupplierInput = { id: number; supplier_name: string; category: string | null };
type ProjectInput = { id: number; project_code: string; project_name: string };

async function loadMaterialIntelligence(suppliers: SupplierInput[], projects: ProjectInput[]): Promise<MaterialIntelligenceSnapshot> {
  await new Promise((resolve) => setTimeout(resolve, 500));
  return generateMaterialIntelligence(suppliers, projects);
}

export function useMaterialIntelligence(suppliers: SupplierInput[] | undefined, projects: ProjectInput[] | undefined) {
  return useQuery<MaterialIntelligenceSnapshot>({
    queryKey: ["material-intelligence", (suppliers ?? []).map((s) => s.id).join(","), (projects ?? []).map((p) => p.id).join(",")],
    queryFn: () => loadMaterialIntelligence(suppliers ?? [], projects ?? []),
    enabled: !!projects,
    staleTime: 60_000,
  });
}
