import { useQuery } from "@tanstack/react-query";
import { generateSupplierRisk, type SupplierRiskSnapshot } from "./mockSupplierRisk";

// Supplier Risk data hook — same shape as lib/useProjectMemory.ts and
// lib/usePredictiveIntelligence.ts: a useQuery wrapper other pages already
// call this way. Swap the queryFn body below for a real supplier-scoring
// endpoint later (e.g. `/api/v1/suppliers/risk`) and no component under
// pages/ai-center/workspaces/supplier-risk/ needs to change — they only
// ever consume `data`/`isLoading`/`isError` from this hook.

type SupplierInput = { id: number; supplier_name: string; category: string | null; city: string | null; status: string };
type ProjectInput = { id: number; project_code: string; project_name: string };

async function loadSupplierRisk(suppliers: SupplierInput[], projects: ProjectInput[]): Promise<SupplierRiskSnapshot> {
  await new Promise((resolve) => setTimeout(resolve, 500));
  return generateSupplierRisk(suppliers, projects);
}

export function useSupplierRisk(suppliers: SupplierInput[] | undefined, projects: ProjectInput[] | undefined) {
  return useQuery<SupplierRiskSnapshot>({
    queryKey: ["supplier-risk", (suppliers ?? []).map((s) => s.id).join(","), (projects ?? []).map((p) => p.id).join(",")],
    queryFn: () => loadSupplierRisk(suppliers ?? [], projects ?? []),
    enabled: !!suppliers && suppliers.length > 0,
    staleTime: 60_000,
  });
}
