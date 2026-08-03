import { UserCircle2 } from "lucide-react";
import { useListProjectMemberships } from "@workspace/api-client-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/context/AuthContext";
import { useUserDirectory } from "@/lib/useUserDirectory";
import { MANAGER_ROLES } from "@/lib/workflowTransitions";

// Reused across all six ownership-upgraded entities (ProjectRisk,
// ProjectIssue, MeetingActionItem, SafetyEvent, NCR, PurchaseRequest —
// backend/app/ai/ownership_engine.py). Each page passes its own
// entity-specific assign/unassign mutation callbacks; this component only
// owns the display + authorization-aware menu, never the API call shape.
export function OwnershipControl({
  projectId,
  ownerId,
  ownerText,
  onAssign,
  onUnassign,
  disabled = false,
}: {
  projectId: number;
  ownerId: number | null | undefined;
  /** Legacy free-text owner — shown ONLY as a fallback when ownerId is null. */
  ownerText?: string | null;
  onAssign: (userId: number) => void;
  onUnassign: () => void;
  disabled?: boolean;
}) {
  const { user } = useAuth();
  const { resolveUserName, isDirectoryAvailable } = useUserDirectory();
  const { data: memberships } = useListProjectMemberships(projectId, {
    query: { queryKey: ["ownership-control-memberships", projectId] },
  });

  const isManagerRole = !!user && (MANAGER_ROLES as readonly string[]).includes(user.role);
  const myRoleOnProject = memberships?.find((m) => m.user_id === user?.id)?.role_on_project;
  const canManage = isManagerRole || (!!myRoleOnProject && (MANAGER_ROLES as readonly string[]).includes(myRoleOnProject));

  const isSelfOwned = ownerId != null && ownerId === user?.id;
  const canSelfAssign = user != null && ownerId !== user.id;
  const canUnassign = ownerId != null && (isSelfOwned || canManage);
  const canReassignToOther = canManage;

  const displayName = ownerId != null ? resolveUserName(ownerId) : ownerText?.trim() || null;

  const reassignCandidates = (memberships ?? []).filter((m) => m.is_active && m.user_id !== ownerId);

  const nothingToShow = !canSelfAssign && !canUnassign && !canReassignToOther;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild disabled={disabled || nothingToShow}>
        <button
          type="button"
          className="inline-flex items-center gap-1.5 text-xs text-foreground/80 hover:text-foreground disabled:opacity-60 disabled:cursor-default"
          data-testid="ownership-control-trigger"
        >
          <UserCircle2 className="w-3.5 h-3.5 text-muted-foreground shrink-0" />
          <span className={displayName ? "" : "text-muted-foreground italic"}>
            {displayName ?? "Unassigned"}
          </span>
        </button>
      </DropdownMenuTrigger>
      {!nothingToShow && (
        <DropdownMenuContent align="start" className="w-56">
          <DropdownMenuLabel>Ownership</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {canSelfAssign && <DropdownMenuItem onClick={() => onAssign(user!.id)}>Assign to me</DropdownMenuItem>}
          {canReassignToOther && (
            <DropdownMenuSub>
              <DropdownMenuSubTrigger disabled={reassignCandidates.length === 0}>Reassign to…</DropdownMenuSubTrigger>
              <DropdownMenuSubContent>
                {reassignCandidates.length === 0 ? (
                  <DropdownMenuItem disabled>No other project members</DropdownMenuItem>
                ) : (
                  reassignCandidates.map((m) => (
                    <DropdownMenuItem key={m.id} onClick={() => onAssign(m.user_id)}>
                      {resolveUserName(m.user_id)}
                      <span className="text-muted-foreground ms-1.5 text-xs">({m.role_on_project})</span>
                    </DropdownMenuItem>
                  ))
                )}
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          )}
          {canUnassign && <DropdownMenuItem onClick={onUnassign}>Unassign</DropdownMenuItem>}
          {!isDirectoryAvailable && (
            <>
              <DropdownMenuSeparator />
              <p className="px-2 py-1 text-[10px] text-muted-foreground">
                Names shown to admins only — others see numeric IDs.
              </p>
            </>
          )}
        </DropdownMenuContent>
      )}
    </DropdownMenu>
  );
}
