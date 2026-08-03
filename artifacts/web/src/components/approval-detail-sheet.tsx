import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  useApproveApproval,
  useAssignApprovalReviewer,
  useCancelApproval,
  useGetApproval,
  useGetApprovalHistory,
  useGetProjectClaim,
  useGetPurchaseRequest,
  useListProjectMemberships,
  useRejectApproval,
  useReturnApproval,
  useStartApprovalReview,
} from "@workspace/api-client-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/context/AuthContext";
import { useUserDirectory } from "@/lib/useUserDirectory";
import { apiErrorDetail, isConflict } from "@/lib/apiErrors";
import { entityLabel, genericStatusBadgeClass } from "@/lib/entityLinks";
import { MANAGER_ROLES } from "@/lib/workflowTransitions";

const APPROVAL_TRANSITIONS: Record<string, string[]> = {
  Pending: ["Under Review", "Approved", "Rejected", "Returned", "Cancelled"],
  "Under Review": ["Approved", "Rejected", "Returned", "Cancelled"],
  Returned: ["Under Review", "Approved", "Rejected", "Cancelled"],
  Approved: [],
  Rejected: [],
  Cancelled: [],
};

function approvalStatusBadgeClass(status: string) {
  const m: Record<string, string> = {
    Approved: "badge-success",
    "Under Review": "badge-warning",
    Pending: "badge-neutral",
    Returned: "badge-warning",
    Rejected: "badge-danger",
    Cancelled: "badge-neutral",
  };
  return m[status] ?? "badge-neutral";
}

export function ApprovalDetailSheet({ approvalId, onClose }: { approvalId: number | null; onClose: () => void }) {
  const { user } = useAuth();
  const { toast } = useToast();
  const qc = useQueryClient();
  const { resolveUserName } = useUserDirectory();
  const [note, setNote] = useState("");

  const open = approvalId != null;

  const { data: approval, isLoading: approvalLoading } = useGetApproval(approvalId ?? 0, {
    query: { queryKey: ["approval-detail", approvalId], enabled: open },
  });
  const { data: history } = useGetApprovalHistory(approvalId ?? 0, {
    query: { queryKey: ["approval-history", approvalId], enabled: open },
  });
  const { data: memberships } = useListProjectMemberships(approval?.project_id ?? 0, {
    query: { queryKey: ["approval-drawer-memberships", approval?.project_id], enabled: !!approval?.project_id },
  });

  const isPurchaseRequest = approval?.entity_type === "purchase_request";
  const isClaim = approval?.entity_type === "claim";
  const { data: sourcePr } = useGetPurchaseRequest(approval?.entity_id ?? 0, {
    query: { queryKey: ["approval-source-pr", approval?.entity_id], enabled: open && isPurchaseRequest },
  });
  const { data: sourceClaim } = useGetProjectClaim(approval?.project_id ?? 0, approval?.entity_id ?? 0, {
    query: { queryKey: ["approval-source-claim", approval?.project_id, approval?.entity_id], enabled: open && isClaim && !!approval?.project_id },
  });

  useEffect(() => {
    setNote("");
  }, [approvalId]);

  const isManagerRole = !!user && (MANAGER_ROLES as readonly string[]).includes(user.role);
  const myRoleOnProject = memberships?.find((m) => m.user_id === user?.id)?.role_on_project;
  const canManage = isManagerRole || (!!myRoleOnProject && (MANAGER_ROLES as readonly string[]).includes(myRoleOnProject));
  const isReviewer = !!approval && approval.assigned_reviewer_id === user?.id;
  const isRequester = !!approval && approval.requested_by_user_id === user?.id;
  const canDecide = isReviewer || canManage;
  const canCancel = isRequester || canManage;

  const nextStatuses = approval ? APPROVAL_TRANSITIONS[approval.status] ?? [] : [];

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ["approval-detail", approvalId] });
    qc.invalidateQueries({ queryKey: ["approval-history", approvalId] });
    qc.invalidateQueries({ queryKey: ["approvals-list"] });
    qc.invalidateQueries({ queryKey: ["approvals-summary"] });
  };

  const onActionError = (err: unknown) => {
    if (isConflict(err)) {
      toast({ title: "This approval changed", description: apiErrorDetail(err, "Reload and try again."), variant: "destructive" });
      invalidateAll();
    } else {
      toast({ title: "Action failed", description: apiErrorDetail(err), variant: "destructive" });
    }
  };

  const commonMutationOpts = {
    onSuccess: (updated: { status: string }) => {
      invalidateAll();
      toast({ title: `Status: ${updated.status}`, variant: "success" });
      setNote("");
    },
    onError: onActionError,
  };

  const startReview = useStartApprovalReview({ mutation: commonMutationOpts });
  const approve = useApproveApproval({ mutation: commonMutationOpts });
  const reject = useRejectApproval({ mutation: commonMutationOpts });
  const returnForChanges = useReturnApproval({ mutation: commonMutationOpts });
  const cancel = useCancelApproval({ mutation: commonMutationOpts });
  const assignReviewer = useAssignApprovalReviewer({
    mutation: {
      onSuccess: () => {
        invalidateAll();
        toast({ title: "Reviewer updated", variant: "success" });
      },
      onError: onActionError,
    },
  });

  const anyPending = startReview.isPending || approve.isPending || reject.isPending || returnForChanges.isPending || cancel.isPending;

  const expected_updated_at = approval?.updated_at;

  const reviewerCandidates = useMemo(
    () => (memberships ?? []).filter((m) => m.is_active && m.user_id !== approval?.assigned_reviewer_id),
    [memberships, approval?.assigned_reviewer_id]
  );

  return (
    <Sheet open={open} onOpenChange={(next) => !next && onClose()}>
      <SheetContent className="w-full sm:max-w-xl overflow-y-auto">
        {approvalLoading || !approval ? (
          <div className="space-y-3 mt-6">
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-24 w-full" />
          </div>
        ) : (
          <>
            <SheetHeader>
              <div className="flex items-center gap-2 flex-wrap">
                <SheetTitle>{entityLabel(approval.entity_type)} #{approval.entity_id}</SheetTitle>
                <span className={`badge ${approvalStatusBadgeClass(approval.status)}`}>{approval.status}</span>
                <span className="badge badge-neutral capitalize">{approval.risk_level} risk</span>
              </div>
              <SheetDescription>
                Approval request #{approval.id} · requested by {resolveUserName(approval.requested_by_user_id) ?? "—"}
              </SheetDescription>
            </SheetHeader>

            {/* Source entity context — clearly separate from the approval's own status */}
            <div className="mt-4 rounded-lg border border-border bg-muted/30 p-3 text-sm">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1.5">Source record</p>
              {isPurchaseRequest && sourcePr ? (
                <div className="flex items-center justify-between gap-2">
                  <span>{sourcePr.request_no}</span>
                  <span className={`badge ${genericStatusBadgeClass(sourcePr.status)}`}>{sourcePr.status}</span>
                </div>
              ) : isClaim && sourceClaim ? (
                <div className="flex items-center justify-between gap-2">
                  <span>{sourceClaim.claim_number} · {sourceClaim.claim_type}</span>
                  <span className={`badge ${genericStatusBadgeClass(sourceClaim.status)}`}>{sourceClaim.status}</span>
                </div>
              ) : (
                <p className="text-muted-foreground">
                  {entityLabel(approval.entity_type)} #{approval.entity_id}
                  {approval.target_version != null && ` · version ${approval.target_version}`}
                </p>
              )}
              {(approval.entity_type === "change_order" || approval.entity_type === "claim") && (
                <p className="text-[11px] text-muted-foreground mt-2">
                  Approving this request records a decision only — it does not change the {approval.entity_type === "change_order" ? "change order's value" : "claim's settlement"}.
                </p>
              )}
            </div>

            <div className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Reviewer</span>
                <span>{resolveUserName(approval.assigned_reviewer_id) ?? "Unassigned"}</span>
              </div>
              {approval.due_at && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Due</span>
                  <span>{new Date(approval.due_at).toLocaleString()}</span>
                </div>
              )}
              {approval.review_note && (
                <div>
                  <span className="text-muted-foreground">Latest note</span>
                  <p className="mt-1 rounded-md bg-muted/50 p-2 text-foreground/90">{approval.review_note}</p>
                </div>
              )}
            </div>

            {/* Reviewer assignment — manager authority only */}
            {canManage && !["Approved", "Rejected", "Cancelled"].includes(approval.status) && (
              <div className="mt-4 border-t border-border pt-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
                  {approval.assigned_reviewer_id ? "Reassign reviewer" : "Assign reviewer"}
                </p>
                {reviewerCandidates.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No other project members available to assign.</p>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {reviewerCandidates.map((m) => (
                      <Button
                        key={m.id}
                        variant="outline"
                        size="sm"
                        disabled={assignReviewer.isPending}
                        onClick={() =>
                          assignReviewer.mutate({
                            approvalId: approval.id,
                            data: { reviewer_user_id: m.user_id, expected_updated_at },
                          })
                        }
                      >
                        {resolveUserName(m.user_id)} <span className="text-muted-foreground ms-1">({m.role_on_project})</span>
                      </Button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Lifecycle actions */}
            {(canDecide || canCancel) && nextStatuses.length > 0 && (
              <div className="mt-4 border-t border-border pt-3 space-y-3">
                <div>
                  <Label htmlFor="approval-note" className="text-xs text-muted-foreground">
                    Note (required to reject or return)
                  </Label>
                  <Textarea
                    id="approval-note"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Add context for your decision…"
                    className="mt-1"
                    rows={2}
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  {canDecide && nextStatuses.includes("Under Review") && (
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={anyPending}
                      onClick={() => startReview.mutate({ approvalId: approval.id, data: { review_note: note || undefined, expected_updated_at } })}
                    >
                      Start review
                    </Button>
                  )}
                  {canDecide && nextStatuses.includes("Approved") && (
                    <Button
                      size="sm"
                      disabled={anyPending}
                      onClick={() => approve.mutate({ approvalId: approval.id, data: { review_note: note || undefined, expected_updated_at } })}
                    >
                      Approve
                    </Button>
                  )}
                  {canDecide && nextStatuses.includes("Returned") && (
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={anyPending || !note.trim()}
                      title={!note.trim() ? "A note is required to return this request" : undefined}
                      onClick={() => returnForChanges.mutate({ approvalId: approval.id, data: { review_note: note, expected_updated_at } })}
                    >
                      Return for changes
                    </Button>
                  )}
                  {canDecide && nextStatuses.includes("Rejected") && (
                    <Button
                      variant="destructive"
                      size="sm"
                      disabled={anyPending || !note.trim()}
                      title={!note.trim() ? "A note is required to reject this request" : undefined}
                      onClick={() => reject.mutate({ approvalId: approval.id, data: { review_note: note, expected_updated_at } })}
                    >
                      Reject
                    </Button>
                  )}
                  {canCancel && nextStatuses.includes("Cancelled") && (
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={anyPending}
                      onClick={() => cancel.mutate({ approvalId: approval.id, data: { review_note: note || undefined, expected_updated_at } })}
                    >
                      Cancel request
                    </Button>
                  )}
                </div>
              </div>
            )}

            {/* History */}
            <div className="mt-6 border-t border-border pt-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">History</p>
              {!history?.length ? (
                <p className="text-xs text-muted-foreground">No history yet.</p>
              ) : (
                <ol className="space-y-2">
                  {history.map((h) => (
                    <li key={h.id} className="text-xs">
                      <span className="text-foreground">
                        {h.previous_status ? `${h.previous_status} → ${h.new_status}` : `Created (${h.new_status})`}
                      </span>
                      <span className="text-muted-foreground">
                        {" "}
                        · {resolveUserName(h.actor_user_id) ?? "System"} · {new Date(h.created_at).toLocaleString()}
                      </span>
                      {h.note && <p className="text-muted-foreground mt-0.5 ps-3 border-s border-border">{h.note}</p>}
                    </li>
                  ))}
                </ol>
              )}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
