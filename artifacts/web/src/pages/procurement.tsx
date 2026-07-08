import { useState } from "react";
import { useListPurchaseRequests, useListPurchaseOrders } from "@workspace/api-client-react";
import { useTranslation } from "react-i18next";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Search, AlertOctagon, Info } from "lucide-react";

type Tab = "requests" | "orders";

function prStatusBadge(status: string) {
  const m: Record<string, string> = {
    Approved:                "badge-success",
    "Converted to PO":       "badge-info",
    "Under Review":          "badge-warning",
    "Pending Clarification": "badge-warning",
    "Needs Rework":          "badge-danger",
    "Returned to Requester": "badge-neutral",
  };
  return m[status] ?? "badge-neutral";
}

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
  const [tab, setTab] = useState<Tab>("requests");
  const [search, setSearch] = useState("");

  const { data: prs, isLoading: prsLoading, isError: prsError } = useListPurchaseRequests({ limit: PAGE_LIMIT });
  const { data: pos, isLoading: posLoading, isError: posError } = useListPurchaseOrders({ limit: PAGE_LIMIT });

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
    <div className="space-y-6">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("Procurement")}</h1>
          <p className="page-subtitle">
            {prs ? `${prs.length.toLocaleString()} ${t("Purchase Requests")} loaded` : "—"}
            {pos ? ` · ${pos.length.toLocaleString()} ${t("Purchase Orders")} loaded` : ""}
            {lateCount > 0 && (
              <span className="ms-2 badge badge-danger">{lateCount} late</span>
            )}
          </p>
        </div>
      </div>

      {/* Pagination notice */}
      <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/40 px-4 py-3 text-xs text-muted-foreground">
        <Info className="w-4 h-4 shrink-0 mt-0.5 text-accent" />
        <span>
          Displaying the {PAGE_LIMIT} most recent records per tab. Use the search box or project filters
          to narrow results. Total database: ~3,000 purchase requests · ~2,550 purchase orders.
        </span>
      </div>

      {/* Tabs + search */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-0">
        <div className="flex gap-0">
          {(["requests", "orders"] as Tab[]).map((id) => (
            <button
              key={id}
              onClick={() => { setTab(id); setSearch(""); }}
              data-testid={`tab-${id}`}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
                tab === id
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              }`}
            >
              {id === "requests" ? t("Purchase Requests") : t("Purchase Orders")}
              <span className="ms-2 text-xs text-muted-foreground">
                {id === "requests" ? (prs?.length ?? "…") : (pos?.length ?? "…")}
              </span>
            </button>
          ))}
        </div>
        <div className="relative mb-px">
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
      {isError && (
        <div className="panel panel-body flex items-center justify-center h-36">
          <div className="text-center text-muted-foreground">
            <AlertOctagon className="w-7 h-7 mx-auto mb-2 text-destructive opacity-60" />
            <p className="text-sm font-medium">Failed to load procurement data</p>
            <p className="text-xs mt-1">Check your connection or permissions and try again.</p>
          </div>
        </div>
      )}

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
                  <th>{t("Delivery Date")}</th>
                  <th>{t("Issue Date")}</th>
                </tr>
              </thead>
              <tbody>
                {prsLoading ? (
                  <tr><td colSpan={6} className="text-center py-10 text-muted-foreground">{t("Loading...")}</td></tr>
                ) : !filteredPrs?.length ? (
                  <tr><td colSpan={6} className="text-center py-10 text-muted-foreground">{t("No data")}</td></tr>
                ) : (
                  filteredPrs.map((pr) => (
                    <tr key={pr.id}>
                      <td className="font-semibold text-sm">{pr.request_no}</td>
                      <td>{pr.material_category ?? "—"}</td>
                      <td className="max-w-xs truncate text-muted-foreground text-xs">
                        {pr.specification ?? "—"}
                      </td>
                      <td><span className={`badge ${prStatusBadge(pr.status)}`}>{pr.status}</span></td>
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
                  <tr><td colSpan={6} className="text-center py-10 text-muted-foreground">{t("Loading...")}</td></tr>
                ) : !filteredPos?.length ? (
                  <tr><td colSpan={6} className="text-center py-10 text-muted-foreground">{t("No data")}</td></tr>
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
    </div>
  );
}
