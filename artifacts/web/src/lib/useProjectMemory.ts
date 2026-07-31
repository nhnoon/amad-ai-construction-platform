import { useQuery } from "@tanstack/react-query";
import { generateProjectMemorySnapshot, type ProjectMemorySnapshot } from "./mockProjectMemory";

// Project Memory data hook — mirrors the shape of useExecutive.ts /
// useAlerts.ts (a useQuery wrapper other pages already call), so this is a
// drop-in seam: swap the queryFn body below for a real `fetch` against a
// future `/api/v1/projects/{code}/memory` endpoint and no component in
// pages/ai-center/workspaces/project-memory/ needs to change — they only
// ever consume `data`, `isLoading`, `isError` from this hook.
//
// The artificial delay is intentional: it's what makes the workspace's
// loading state real to exercise now, and it disappears naturally once the
// queryFn below is replaced with an actual network call.

async function loadProjectMemory(
  project: { project_code: string; project_name: string },
): Promise<ProjectMemorySnapshot> {
  await new Promise((resolve) => setTimeout(resolve, 450));
  return generateProjectMemorySnapshot(project);
}

export function useProjectMemory(project: { project_code: string; project_name: string } | null) {
  return useQuery<ProjectMemorySnapshot>({
    queryKey: ["project-memory", project?.project_code],
    queryFn: () => loadProjectMemory(project!),
    enabled: !!project,
    staleTime: 60_000,
  });
}
