import { useState } from "react";
import { ChevronDown } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { genericStatusBadgeClass } from "@/lib/entityLinks";
import { nextStatuses, requiredFieldFor, type EntityKind } from "@/lib/workflowTransitions";

// Reused across all six workflow-upgraded entities. Only ever offers
// statuses from workflowTransitions.ts — never a free-text input — and
// opens a small confirmation dialog when the target status needs a
// close-out field the backend requires (mirrors _require_nonempty).
export function StatusTransitionControl({
  entity,
  entityLabel,
  currentStatus,
  onTransition,
  disabled = false,
}: {
  entity: EntityKind;
  entityLabel: string;
  currentStatus: string;
  onTransition: (targetStatus: string, closeOutValue: string | undefined) => void;
  disabled?: boolean;
}) {
  const [pendingTarget, setPendingTarget] = useState<string | null>(null);
  const [fieldValue, setFieldValue] = useState("");

  const options = nextStatuses(entity, currentStatus);
  const requiredField = pendingTarget ? requiredFieldFor(entity, pendingTarget) : null;

  function handlePick(target: string) {
    const req = requiredFieldFor(entity, target);
    if (req) {
      setPendingTarget(target);
      setFieldValue("");
    } else {
      onTransition(target, undefined);
    }
  }

  function confirm() {
    if (!pendingTarget) return;
    onTransition(pendingTarget, fieldValue.trim() || undefined);
    setPendingTarget(null);
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild disabled={disabled || options.length === 0}>
          <button
            type="button"
            className={`badge ${genericStatusBadgeClass(currentStatus)} inline-flex items-center gap-1 ${
              options.length > 0 ? "cursor-pointer hover:opacity-80" : "cursor-default"
            }`}
            data-testid="status-transition-trigger"
          >
            {currentStatus}
            {options.length > 0 && <ChevronDown className="w-3 h-3" />}
          </button>
        </DropdownMenuTrigger>
        {options.length > 0 && (
          <DropdownMenuContent align="start">
            <DropdownMenuLabel>Change status</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {options.map((s) => (
              <DropdownMenuItem key={s} onClick={() => handlePick(s)}>
                {s}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        )}
      </DropdownMenu>

      <Dialog open={!!pendingTarget} onOpenChange={(o) => !o && setPendingTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Move {entityLabel} to "{pendingTarget}"
            </DialogTitle>
          </DialogHeader>
          {requiredField && (
            <div>
              <Label htmlFor="close-out-field">{requiredField.label}</Label>
              <Textarea
                id="close-out-field"
                value={fieldValue}
                onChange={(e) => setFieldValue(e.target.value)}
                className="mt-1"
                rows={3}
                autoFocus
              />
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingTarget(null)}>
              Cancel
            </Button>
            <Button onClick={confirm} disabled={!!requiredField && !fieldValue.trim()}>
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
