import { useState } from "react";
import { useListSuppliers } from "@workspace/api-client-react";
import { useTranslation } from "react-i18next";
import { Skeleton } from "@/components/ui/skeleton";
import { Truck } from "lucide-react";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { SearchInput } from "@/components/search-input";
import { FilterSelect } from "@/components/filter-select";

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
    return <ErrorState title="Failed to load suppliers" />;
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
    <WorkspaceLayout
        title={t("Suppliers")}
        subtitle={`${suppliers?.length ?? 0} registered · ${activeCount} active`}
        backLabel="Back to Operations"
        backHref="/operations"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Operations", href: "/operations" },
          { label: "Suppliers" },
        ]}
      >
      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <SearchInput value={search} onChange={setSearch} placeholder={t("Search suppliers...")} testId="search-suppliers" />
        <FilterSelect className="min-w-40" value={categoryFilter} onChange={setCategoryFilter} testId="filter-category">
          <option value="all">{t("All Categories")}</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </FilterSelect>
        <FilterSelect className="min-w-40" value={statusFilter} onChange={setStatusFilter} testId="filter-status">
          <option value="all">{t("All Statuses")}</option>
          {statuses.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </FilterSelect>
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
    </WorkspaceLayout>
  );
}
