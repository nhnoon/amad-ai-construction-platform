import { BackButton } from "@/components/back-button";

// Back-to-/operations control used by pages that live one level under
// Operations (Procurement, Meetings, ...). Thin wrapper over the generic
// BackButton so both pages render byte-identical markup.
export function BackToOperations() {
  return <BackButton to="/operations" label="Back to Operations" />;
}
