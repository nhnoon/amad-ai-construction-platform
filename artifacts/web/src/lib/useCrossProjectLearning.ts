import { useQuery } from "@tanstack/react-query";
import { generateCrossProjectLearning, type CrossProjectLearningSnapshot } from "./mockCrossProjectLearning";

// Cross-Project Learning data hook — same shape as the other AI Center
// workspaces' hooks (useProjectMemory, usePredictiveIntelligence,
// useSupplierRisk, useMaterialIntelligence): a useQuery wrapper other
// pages already call this way. Swap the queryFn body below for a real
// knowledge-retrieval backend later — vector search, embeddings, Hermes
// memory, or a knowledge graph store — and no component under
// pages/ai-center/workspaces/cross-project-learning/ needs to change; they
// only ever consume `data`/`isLoading`/`isError` from this hook (search
// and similarity themselves are separate pure functions in
// mockCrossProjectLearning.ts, the natural seam for a real semantic
// search call).

type ProjectInput = { id: number; project_code: string; project_name: string };
type SupplierInput = { id: number; supplier_name: string; category: string | null };

async function loadCrossProjectLearning(projects: ProjectInput[], suppliers: SupplierInput[]): Promise<CrossProjectLearningSnapshot> {
  await new Promise((resolve) => setTimeout(resolve, 500));
  return generateCrossProjectLearning(projects, suppliers);
}

export function useCrossProjectLearning(projects: ProjectInput[] | undefined, suppliers: SupplierInput[] | undefined) {
  return useQuery<CrossProjectLearningSnapshot>({
    queryKey: ["cross-project-learning", (projects ?? []).map((p) => p.id).join(","), (suppliers ?? []).map((s) => s.id).join(",")],
    queryFn: () => loadCrossProjectLearning(projects ?? [], suppliers ?? []),
    enabled: !!projects,
    staleTime: 60_000,
  });
}
