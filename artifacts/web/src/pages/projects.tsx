import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useListProjects, useListProjectHealthScores } from "@workspace/api-client-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Link } from "wouter";
import { Search, ChevronRight, AlertOctagon } from "lucide-react";
import { PageContextHeader } from "@/components/page-context-header";

const STATUS_BADGE: Record<string, string> = {
  Active:      "badge-success",
  Delayed:     "badge-danger",
  Completed:   "badge-info",
  Suspended:   "badge-neutral",
  Planning:    "badge-purple",
  "On Hold":   "badge-warning",
};

const HEALTH_COLOR: Record<string, { bar: string; text: string }> = {
  "Excellent": { bar: "#22c55e", text: "#16a34a" },
  "Good":      { bar: "#3b82f6", text: "#2563eb" },
  "At Risk":   { bar: "#f59e0b", text: "#d97706" },
  "Critical":  { bar: "#ef4444", text: "#dc2626" },
};

function HealthBadge({ score, level }: { score: number; level: string }) {
  const colors = HEALTH_COLOR[level] ?? { bar: "#94a3b8", text: "#64748b" };
  return (
    <div className="flex items-center gap-2 min-w-[90px]">
      <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${score}%`, backgroundColor: colors.bar }}
        />
      </div>
      <span className="text-xs font-semibold tabular-nums" style={{ color: colors.text }}>
        {score}
      </span>
    </div>
  );
}

function getStatusBadge(status: string) {
  return STATUS_BADGE[status] ?? "badge-neutral";
}

export default function Projects() {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useListProjects({ limit: 100 });
  const { data: healthData } = useListProjectHealthScores();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const healthMap = new Map(
    (healthData ?? []).map((h) => [h.project_id, h])
  );

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="space-y-1">
          <Skeleton className="h-8 w-40" />
          <Skeleton className="h-4 w-32" />
        </div>
        <div className="flex gap-3">
          <Skeleton className="h-10 w-72" />
          <Skeleton className="h-10 w-40" />
        </div>
        <Skeleton className="h-[480px] w-full rounded-xl" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="panel panel-body flex items-center justify-center h-48">
        <div className="text-center text-muted-foreground">
          <AlertOctagon className="w-8 h-8 mx-auto mb-2 text-destructive opacity-60" />
          <p className="text-sm font-medium">Failed to load projects</p>
          <p className="text-xs mt-1">Check your connection or permissions and try again.</p>
        </div>
      </div>
    );
  }

  const allStatuses = Array.from(new Set(data?.map((p) => p.status) ?? [])).sort();

  const filtered = data?.filter((p) => {
    const matchSearch =
      p.project_name.toLowerCase().includes(search.toLowerCase()) ||
      p.project_code.toLowerCase().includes(search.toLowerCase()) ||
      (p.client_name ?? "").toLowerCase().includes(search.toLowerCase()) ||
      (p.city ?? "").toLowerCase().includes(search.toLowerCase());
    const matchStatus = statusFilter === "all" || p.status === statusFilter;
    return matchSearch && matchStatus;
  });

  return (
    <div className="space-y-6">
      <PageContextHeader
        title={t("Projects")}
        subtitle={`${data?.length ?? 0} total · ${filtered?.length ?? 0} shown`}
        backLabel="Back to Operations"
        backHref="/operations"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Operations", href: "/operations" },
          { label: "Projects" },
        ]}
      />

      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-52 max-w-sm">
          <Search className="absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
          <Input
            placeholder={t("Search projects...")}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="ps-9 h-10"
            data-testid="search-projects"
          />
        </div>
        <select
          className="border rounded-lg px-3 py-2 text-sm h-10 bg-background text-foreground"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          data-testid="filter-status"
        >
          <option value="all">{t("All Statuses")}</option>
          {allStatuses.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      <div className="panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="data-table" data-testid="projects-table">
            <thead>
              <tr>
                <th>{t("Code")}</th>
                <th className="min-w-[200px]">Project Name</th>
                <th>{t("City")}</th>
                <th>{t("Client")}</th>
                <th>{t("Status")}</th>
                <th className="min-w-[130px]">{t("Health")}</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filtered?.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center h-24 text-muted-foreground">
                    {t("No data")}
                  </td>
                </tr>
              ) : (
                filtered?.map((project) => {
                  const health = healthMap.get(project.id);
                  return (
                    <tr key={project.id}>
                      <td>
                        <Link
                          href={`/projects/${project.id}`}
                          className="font-semibold text-primary hover:text-accent transition-colors text-sm"
                          data-testid={`project-link-${project.id}`}
                        >
                          {project.project_code}
                        </Link>
                      </td>
                      <td className="font-medium">{project.project_name}</td>
                      <td className="text-muted-foreground">{project.city}</td>
                      <td className="text-muted-foreground">{project.client_name}</td>
                      <td>
                        <span className={`badge ${getStatusBadge(project.status)}`}>
                          {project.status}
                        </span>
                      </td>
                      <td>
                        {health ? (
                          <HealthBadge score={health.score} level={health.level} />
                        ) : (
                          <span className="text-muted-foreground text-xs">—</span>
                        )}
                      </td>
                      <td className="text-end">
                        <Link
                          href={`/projects/${project.id}`}
                          className="text-muted-foreground hover:text-foreground transition-colors"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </Link>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
