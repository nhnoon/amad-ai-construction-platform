import type { QueryClient, QueryKey } from "@tanstack/react-query";
import { apiErrorDetail, isConflict } from "./apiErrors";

// Shared onError handler for ownership/workflow mutations across every
// page that uses OwnershipControl/StatusTransitionControl: a 409 means
// the row changed since it was loaded (stale expected_updated_at, or a
// transition that's no longer valid) — surface it clearly and refetch so
// the UI self-heals, per Sprint 6 Phase F's concurrency requirement.
// Anything else is a generic failure toast.
export function makeConflictAwareErrorHandler(
  toast: (opts: { title: string; description?: string; variant?: "destructive" }) => void,
  qc: QueryClient,
  invalidateKeys: QueryKey[]
) {
  return (err: unknown) => {
    if (isConflict(err)) {
      toast({ title: "This record changed", description: apiErrorDetail(err, "Reload and try again."), variant: "destructive" });
    } else {
      toast({ title: "Action failed", description: apiErrorDetail(err), variant: "destructive" });
    }
    invalidateKeys.forEach((key) => qc.invalidateQueries({ queryKey: key }));
  };
}
