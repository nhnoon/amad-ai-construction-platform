import { useState } from "react";
import { useListSuppliers } from "@workspace/api-client-react";
import { useTranslation } from "react-i18next";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Search, AlertOctagon, Truck } from "lucide-react";
import { PageContextHeader } from "@/components/page-context-header";
import { EmptyState } from "@/components/ui/empty-state";

function statusBadge(status: string) {
  const m: Record<string, string> = {
    Active:    "badge-success",
    Inactive:  "badge-neutral",
    Suspended: "badge-danger",
  };
  return m[status] ?? "badge-neutral";
}

export default function Suppliers() {
  const { t } = useTranslation();
  const { data: suppliers, isLoading, isError } = useListSuppliers({ limit: 100 });
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="space-y-1">
          <Skeleton className="h-8 w-40" />
          <Skeleton className="h-4 w-32" />
        </div>
        <div className="flex gap-3">
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-10 w-40" />
          <Skeleton className="h-10 w-40" />
        </div>
        <Skeleton className="h-[420px] w-full rounded-xl" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="panel panel-body flex items-center justify-center h-48">
        <div className="text-center text-muted-foreground">
          <AlertOctagon className="w-8 h-8 mx-auto mb-2 text-destructive opacity-60" />
          <p className="text-sm font-medium">Failed to load suppliers</p>
          <p className="text-xs mt-1">Check your connection or permissions and try again.</p>
        </div>
      </div>
    );
  }

  const categories = Array.from(new Set(suppliers?.map((s) => s.category).filter(Boolean) ?? [])).sort();
  const statuses = Array.from(new Set(suppliers?.map((s) => s.status) ?? [])).sort();

  const filtered = suppliers?.filter((s) => {
    const matchSearch =
      s.supplier_name.toLowerCase().includes(search.toLowerCase()) ||
      (s.city ?? "").toLowerCase().includes(search.toLowerCase()) ||
      (s.category ?? "").toLowerCase().includes(search.toLowerCase());
    const matchCat = categoryFilter === "all" || s.category === categoryFilter;
    const matchStatus = statusFilter === "all" || s.status === statusFilter;
    return matchSearch && matchCat && matchStatus;
  });

  const activeCount = suppliers?.filter((s) => s.status === "Active").length ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageContextHeader
        title={t("Suppliers")}
        subtitle={`${suppliers?.length ?? 0} registered · ${activeCount} active`}
        backLabel="Back to Operations"
        backHref="/operations"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Operations", href: "/operations" },
          { label: "Suppliers" },
        ]}
      />

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-52 max-w-sm">
          <Search className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
          <Input
            placeholder={t("Search suppliers...")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="ps-9 h-10"
            data-testid="search-suppliers"
          />
        </div>
        <select
          className="border rounded-lg px-3 py-2 text-sm h-10 bg-background text-foreground"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          data-testid="filter-category"
        >
          <option value="all">{t("All Categories")}</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <select
          className="border rounded-lg px-3 py-2 text-sm h-10 bg-background text-foreground"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          data-testid="filter-status"
        >
          <option value="all">{t("All Statuses")}</option>
          {statuses.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="data-table" data-testid="suppliers-table">
            <thead>
              <tr>
                <th>#</th>
                <th className="min-w-[200px]">{t("Name")}</th>
                <th>{t("Category")}</th>
                <th>{t("City")}</th>
                <th>{t("Status")}</th>
              </tr>
            </thead>
            <tbody>
              {!filtered?.length ? (
                <tr>
                  <td colSpan={5}>
                    <EmptyState
                      icon={Truck}
                      title={search || categoryFilter !== "all" || statusFilter !== "all" ? "No suppliers match your filters" : "No suppliers yet"}
                      description={
                        search || categoryFilter !== "all" || statusFilter !== "all"
                          ? "Try adjusting your search or filters."
                          : "Registered suppliers will appear here."
                      }
                    />
                  </td>
                </tr>
              ) : (
                filtered.map((s) => (
                  <tr key={s.id}>
                    <td className="text-muted-foreground text-sm font-mono">{s.id}</td>
                    <td className="font-semibold">{s.supplier_name}</td>
                    <td className="text-muted-foreground">{s.category}</td>
                    <td className="text-muted-foreground">{s.city}</td>
                    <td>
                      <span className={`badge ${statusBadge(s.status)}`}>{s.status}</span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
