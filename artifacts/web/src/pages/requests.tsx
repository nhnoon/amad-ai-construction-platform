import { useEffect, useState } from "react";
import { useSearch } from "wouter";
import { useTranslation } from "react-i18next";
import { FileCheck2 } from "lucide-react";
import { useGetApprovalsSummary, useListApprovals } from "@workspace/api-client-react";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { FilterChip } from "@/components/filter-chip";
import { FilterSelect } from "@/components/filter-select";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { TableSkeletonRows } from "@/components/ui/table-skeleton";
import { ApprovalDetailSheet } from "@/components/approval-detail-sheet";
import { useUserDirectory } from "@/lib/useUserDirectory";
import { entityLabel } from "@/lib/entityLinks";

const STATUSES = ["Pending", "Under Review", "Returned", "Approved", "Rejected", "Cancelled"];
const ENTITY_TYPES = ["purchase_request", "change_order", "claim", "document"];

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

const PAGE_LIMIT = 100;

export default function Requests() {
  const { t } = useTranslation();
  const search = useSearch();
  const { resolveUserName } = useUserDirectory();

  const [assignedToMe, setAssignedToMe] = useState(false);
  const [requestedByMe, setRequestedByMe] = useState(false);
  const [status, setStatus] = useState<string>("all");
  const [entityType, setEntityType] = useState<string>("all");
  const [overdue, setOverdue] = useState(false);
  const [dueSoon, setDueSoon] = useState(false);
  const [selectedId, setSelectedId] = useState<number | null>(null);

  useEffect(() => {
    const openId = new URLSearchParams(search).get("open");
    if (openId) setSelectedId(Number(openId));
  }, [search]);

  const { data: summary } = useGetApprovalsSummary({ query: { queryKey: ["approvals-summary"] } });

  const { data: approvals, isLoading, isError } = useListApprovals(
    {
      assigned_to_me: assignedToMe,
      requested_by_me: requestedByMe,
      status: status === "all" ? undefined : status,
      entity_type: entityType === "all" ? undefined : entityType,
      overdue,
      due_soon: dueSoon,
      limit: PAGE_LIMIT,
    },
    { query: { queryKey: ["approvals-list", assignedToMe, requestedByMe, status, entityType, overdue, dueSoon] } }
  );

  return (
    <WorkspaceLayout
      title={t("Requests & Approvals")}
      subtitle="Approval requests for purchase requests, change orders, claims, and documents"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Requests & Approvals" }]}
      toolbar={
        summary ? (
          <div className="flex items-center gap-2 text-xs">
            {summary.overdue_count > 0 && <span className="badge badge-danger">{summary.overdue_count} overdue</span>}
            {summary.due_soon_count > 0 && <span className="badge badge-warning">{summary.due_soon_count} due soon</span>}
          </div>
        ) : undefined
      }
    >
      <div className="flex flex-wrap items-center gap-2">
        <FilterChip active={assignedToMe} onClick={() => setAssignedToMe((v) => !v)}>
          {t("Assigned to me")}
        </FilterChip>
        <FilterChip active={requestedByMe} onClick={() => setRequestedByMe((v) => !v)}>
          {t("Requested by me")}
        </FilterChip>
        <FilterChip active={overdue} onClick={() => setOverdue((v) => !v)} tone="amber">
          {t("Overdue")}
        </FilterChip>
        <FilterChip active={dueSoon} onClick={() => setDueSoon((v) => !v)}>
          {t("Due soon")}
        </FilterChip>
        <FilterSelect value={status} onChange={setStatus} ariaLabel="Status">
          <option value="all">{t("All statuses")}</option>
          {STATUSES.map((s) => (
            <option key={s} value={s}>
              {t(s)}
            </option>
          ))}
        </FilterSelect>
        <FilterSelect value={entityType} onChange={setEntityType} ariaLabel="Entity type" className="ms-auto">
          <option value="all">{t("All types")}</option>
          {ENTITY_TYPES.map((e) => (
            <option key={e} value={e}>
              {t(entityLabel(e))}
            </option>
          ))}
        </FilterSelect>
      </div>

      {isError && <ErrorState title="Failed to load approvals" />}

      {!isError && (
        <div className="panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table" data-testid="approvals-table">
              <thead>
                <tr>
                  <th>{t("Record")}</th>
                  <th>{t("Status")}</th>
                  <th>{t("Risk")}</th>
                  <th>{t("Reviewer")}</th>
                  <th>{t("Requested by")}</th>
                  <th>{t("Due")}</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <TableSkeletonRows rows={8} cols={6} />
                ) : !approvals?.length ? (
                  <tr>
                    <td colSpan={6}>
                      <EmptyState
                        icon={FileCheck2}
                        title="No approval requests"
                        description="Approval requests created from purchase requests, change orders, claims, and documents will show up here."
                      />
                    </td>
                  </tr>
                ) : (
                  approvals.map((a) => (
                    <tr
                      key={a.id}
                      className="cursor-pointer hover:bg-muted/40"
                      onClick={() => setSelectedId(a.id)}
                      data-testid={`approval-row-${a.id}`}
                    >
                      <td className="text-sm font-medium">
                        {entityLabel(a.entity_type)} #{a.entity_id}
                      </td>
                      <td>
                        <span className={`badge ${approvalStatusBadgeClass(a.status)}`}>{a.status}</span>
                      </td>
                      <td className="text-muted-foreground text-sm capitalize">{a.risk_level}</td>
                      <td className="text-muted-foreground text-sm">{resolveUserName(a.assigned_reviewer_id) ?? "—"}</td>
                      <td className="text-muted-foreground text-sm">{resolveUserName(a.requested_by_user_id) ?? "—"}</td>
                      <td className="text-muted-foreground text-sm whitespace-nowrap">
                        {a.due_at ? new Date(a.due_at).toLocaleDateString() : "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <ApprovalDetailSheet approvalId={selectedId} onClose={() => setSelectedId(null)} />
    </WorkspaceLayout>
  );
}
