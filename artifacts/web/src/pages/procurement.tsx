import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  useListPurchaseRequests,
  useListPurchaseOrders,
  useUpdatePurchaseRequest,
  useAssignPurchaseRequest,
  useUnassignPurchaseRequest,
} from "@workspace/api-client-react";
import { useTranslation } from "react-i18next";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Search, Info, ClipboardList, Truck } from "lucide-react";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { PageTabs } from "@/components/page-tabs";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { TableSkeletonRows } from "@/components/ui/table-skeleton";
import { OwnershipControl } from "@/components/ownership-control";
import { StatusTransitionControl } from "@/components/status-transition-control";
import { useToast } from "@/hooks/use-toast";
import { makeConflictAwareErrorHandler } from "@/lib/mutationFeedback";

type Tab = "requests" | "orders";

// Purchase request status is now rendered via StatusTransitionControl
// (Sprint 6 Phase F), which sources its badge coloring from
// lib/entityLinks.ts::genericStatusBadgeClass — prStatusBadge was this
// page's own local copy of that mapping and is no longer needed.

function poStatusBadge(status: string) {
  const m: Record<string, string> = {
    Delivered:           "badge-success",
    Approved:            "badge-info",
    Pending:             "badge-warning",
    Cancelled:           "badge-neutral",
    "Partially Delivered":"badge-purple",
  };
  return m[status] ?? "badge-neutral";
}

const PAGE_LIMIT = 100;

export default function Procurement() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("requests");
  const [search, setSearch] = useState("");

  const { data: prs, isLoading: prsLoading, isError: prsError } = useListPurchaseRequests(
    { limit: PAGE_LIMIT },
    { query: { queryKey: ["purchase-requests-list"] } }
  );
  const { data: pos, isLoading: posLoading, isError: posError } = useListPurchaseOrders({ limit: PAGE_LIMIT });

  const onMutationError = makeConflictAwareErrorHandler(toast, qc, [["purchase-requests-list"]]);
  const onMutationSuccess = (label: string) => () => {
    toast({ title: label, variant: "success" });
    qc.invalidateQueries({ queryKey: ["purchase-requests-list"] });
  };
  const updatePr = useUpdatePurchaseRequest({ mutation: { onSuccess: onMutationSuccess("Purchase request updated"), onError: onMutationError } });
  const assignPr = useAssignPurchaseRequest({ mutation: { onSuccess: onMutationSuccess("Owner updated"), onError: onMutationError } });
  const unassignPr = useUnassignPurchaseRequest({ mutation: { onSuccess: onMutationSuccess("Unassigned"), onError: onMutationError } });

  const filteredPrs = prs?.filter(
    (pr) =>
      pr.request_no.toLowerCase().includes(search.toLowerCase()) ||
      (pr.material_category ?? "").toLowerCase().includes(search.toLowerCase()) ||
      pr.status.toLowerCase().includes(search.toLowerCase())
  );

  const filteredPos = pos?.filter(
    (po) =>
      po.po_number.toLowerCase().includes(search.toLowerCase()) ||
      po.status.toLowerCase().includes(search.toLowerCase())
  );

  const lateCount = pos?.filter((po) => po.is_late).length ?? 0;
  const isLoading = tab === "requests" ? prsLoading : posLoading;
  const isError   = tab === "requests" ? prsError   : posError;

  return (
    <WorkspaceLayout
        title={t("Procurement")}
        subtitle={`${prs ? `${prs.length.toLocaleString()} ${t("Purchase Requests")} loaded` : "—"}${pos ? ` · ${pos.length.toLocaleString()} ${t("Purchase Orders")} loaded` : ""}`}
        backLabel="Back to Operations"
        backHref="/operations"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Operations", href: "/operations" },
          { label: t("Procurement") },
        ]}
        toolbar={lateCount > 0 ? <span className="badge badge-danger">{lateCount} late</span> : undefined}
      >

      {/* Pagination notice */}
      <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/40 px-4 py-3 text-xs text-muted-foreground">
        <Info className="w-4 h-4 shrink-0 mt-0.5 text-accent" />
        <span>
          Displaying the {PAGE_LIMIT} most recent records per tab. Use the search box or project filters
          to narrow results. Total database: ~3,000 purchase requests · ~2,550 purchase orders.
        </span>
      </div>

      {/* Tabs + search */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <PageTabs
          tabs={[
            { id: "requests", label: t("Purchase Requests"), count: prs?.length },
            { id: "orders", label: t("Purchase Orders"), count: pos?.length },
          ]}
          value={tab}
          onChange={(id) => { setTab(id); setSearch(""); }}
        />
        <div className="relative">
          <Search className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
          <Input
            placeholder="Search…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="ps-9 h-9 w-64"
          />
        </div>
      </div>

      {/* Error state */}
      {isError && <ErrorState title="Failed to load procurement data" />}

      {/* Purchase Requests table */}
      {!isError && tab === "requests" && (
        <div className="panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table" data-testid="purchase-requests-table">
              <thead>
                <tr>
                  <th>{t("Request No")}</th>
                  <th>{t("Category")}</th>
                  <th>{t("Specification")}</th>
                  <th>{t("Status")}</th>
                  <th>{t("Owner")}</th>
                  <th>{t("Delivery Date")}</th>
                  <th>{t("Issue Date")}</th>
                </tr>
              </thead>
              <tbody>
                {prsLoading ? (
                  <TableSkeletonRows rows={6} cols={7} />
                ) : !filteredPrs?.length ? (
                  <tr>
                    <td colSpan={7}>
                      <EmptyState
                        icon={ClipboardList}
                        title={search ? "No purchase requests match your search" : "No purchase requests yet"}
                        description={search ? "Try a different search term." : "Purchase requests will appear here once submitted."}
                      />
                    </td>
                  </tr>
                ) : (
                  filteredPrs.map((pr) => (
                    <tr key={pr.id}>
                      <td className="font-semibold text-sm">{pr.request_no}</td>
                      <td>{pr.material_category ?? "—"}</td>
                      <td className="max-w-xs truncate text-muted-foreground text-xs">
                        {pr.specification ?? "—"}
                      </td>
                      <td>
                        <StatusTransitionControl
                          entity="purchase_request"
                          entityLabel="purchase request"
                          currentStatus={pr.status}
                          disabled={updatePr.isPending}
                          onTransition={(target, closeOutValue) =>
                            updatePr.mutate({
                              requestId: pr.id,
                              data: { status: target, rework_reason: closeOutValue, expected_updated_at: pr.updated_at ?? undefined },
                            })
                          }
                        />
                      </td>
                      <td>
                        <OwnershipControl
                          projectId={pr.project_id}
                          ownerId={pr.owner_id}
                          disabled={assignPr.isPending || unassignPr.isPending}
                          onAssign={(userId) =>
                            assignPr.mutate({ requestId: pr.id, data: { user_id: userId, expected_updated_at: pr.updated_at ?? undefined } })
                          }
                          onUnassign={() => unassignPr.mutate({ requestId: pr.id, data: { expected_updated_at: pr.updated_at ?? undefined } })}
                        />
                      </td>
                      <td className="text-muted-foreground text-sm whitespace-nowrap">{pr.required_delivery_date ?? "—"}</td>
                      <td className="text-muted-foreground text-sm whitespace-nowrap">{pr.created_at}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Purchase Orders table */}
      {!isError && tab === "orders" && (
        <div className="panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table" data-testid="purchase-orders-table">
              <thead>
                <tr>
                  <th>{t("PO Number")}</th>
                  <th>{t("Status")}</th>
                  <th>{t("Issue Date")}</th>
                  <th>{t("Delivery Date")}</th>
                  <th>{t("Late")}</th>
                  <th>{t("Delay Days")}</th>
                </tr>
              </thead>
              <tbody>
                {posLoading ? (
                  <TableSkeletonRows rows={6} cols={6} />
                ) : !filteredPos?.length ? (
                  <tr>
                    <td colSpan={6}>
                      <EmptyState
                        icon={Truck}
                        title={search ? "No purchase orders match your search" : "No purchase orders yet"}
                        description={search ? "Try a different search term." : "Purchase orders will appear here once issued."}
                      />
                    </td>
                  </tr>
                ) : (
                  filteredPos.map((po) => (
                    <tr key={po.id} className={po.is_late ? "bg-red-50/50 dark:bg-red-900/5" : ""}>
                      <td className="font-semibold text-sm">{po.po_number}</td>
                      <td><span className={`badge ${poStatusBadge(po.status)}`}>{po.status}</span></td>
                      <td className="text-muted-foreground text-sm whitespace-nowrap">{po.issue_date}</td>
                      <td className="text-muted-foreground text-sm whitespace-nowrap">{po.promised_delivery}</td>
                      <td>
                        {po.is_late ? (
                          <span className="badge badge-danger">{t("Yes")}</span>
                        ) : (
                          <span className="badge badge-success">{t("No")}</span>
                        )}
                      </td>
                      <td className="text-muted-foreground text-sm">
                        {po.delay_days ? (
                          <span className="font-medium text-red-600 dark:text-red-400">
                            {po.delay_days}d
                          </span>
                        ) : "—"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </WorkspaceLayout>
  );
}
