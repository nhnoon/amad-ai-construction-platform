import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useListProjects, useListProjectHealthScores } from "@workspace/api-client-react";
import { Skeleton } from "@/components/ui/skeleton";
import { Link } from "wouter";
import { ChevronRight, FolderKanban } from "lucide-react";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { SearchInput } from "@/components/search-input";
import { FilterSelect } from "@/components/filter-select";
import { FilterChip } from "@/components/filter-chip";

// ── AMAD v2 — Projects (operational workspace) ──────────────────────────────
// Not a project directory — the workspace a PM opens to see, at a glance,
// which of their projects need attention right now. Two changes from the
// previous table-only version: (1) projects are sorted by priority by
// default (Delayed status and Critical/At Risk health first, not id/
// alphabetical order), so "which projects need attention" doesn't require
// scanning the whole list; (2) rows became cards — a bigger click target
// into Project Detail, and room for status + health to read as a single
// glance instead of two narrow table cells. Same status vocabulary, same
// health scores, same two hooks (useListProjects, useListProjectHealthScores)
// as before — no new backend calls, no per-project N+1 requests.

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
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${score}%`, backgroundColor: colors.bar }}
        />
      </div>
      <span className="text-xs font-semibold tabular-nums shrink-0" style={{ color: colors.text }}>
        {score}
      </span>
    </div>
  );
}

function getStatusBadge(status: string) {
  return STATUS_BADGE[status] ?? "badge-neutral";
}

// A project needs attention if it's formally Delayed, or its health has
// crossed into At Risk/Critical — the same two real signals (status,
// health level) the rest of the app already treats as the "attention"
// threshold (e.g. Dashboard's Needs Attention, Operations Overview's
// Projects Behind Schedule).
function needsAttention(status: string, level?: string): boolean {
  return status === "Delayed" || level === "Critical" || level === "At Risk";
}

// Sort worst-first: Delayed status, then Critical, then At Risk health,
// then everything else by health score ascending (lower score = worse),
// with unscored projects last. This is what makes "which projects need
// attention" answerable without reading the whole list top to bottom.
function priorityRank(status: string, level?: string): number {
  if (status === "Delayed") return 0;
  if (level === "Critical") return 1;
  if (level === "At Risk") return 2;
  if (status === "On Hold" || status === "Suspended") return 3;
  return 4;
}

export default function Projects() {
  const { t } = useTranslation();
  const { data, isLoading, isError, refetch } = useListProjects({ limit: 100 });
  const { data: healthData } = useListProjectHealthScores();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [attentionOnly, setAttentionOnly] = useState(false);

  const healthMap = useMemo(
    () => new Map((healthData ?? []).map((h) => [h.project_id, h])),
    [healthData],
  );

  const allStatuses = useMemo(() => Array.from(new Set(data?.map((p) => p.status) ?? [])).sort(), [data]);

  const attentionCount = useMemo(
    () => (data ?? []).filter((p) => needsAttention(p.status, healthMap.get(p.id)?.level)).length,
    [data, healthMap],
  );

  const filtered = useMemo(() => {
    return (data ?? [])
      .filter((p) => {
        const matchSearch =
          p.project_name.toLowerCase().includes(search.toLowerCase()) ||
          p.project_code.toLowerCase().includes(search.toLowerCase()) ||
          (p.client_name ?? "").toLowerCase().includes(search.toLowerCase()) ||
          (p.city ?? "").toLowerCase().includes(search.toLowerCase());
        const matchStatus = statusFilter === "all" || p.status === statusFilter;
        const health = healthMap.get(p.id);
        const matchAttention = !attentionOnly || needsAttention(p.status, health?.level);
        return matchSearch && matchStatus && matchAttention;
      })
      .sort((a, b) => {
        const ha = healthMap.get(a.id), hb = healthMap.get(b.id);
        const rankDiff = priorityRank(a.status, ha?.level) - priorityRank(b.status, hb?.level);
        if (rankDiff !== 0) return rankDiff;
        const scoreDiff = (ha?.score ?? 100) - (hb?.score ?? 100);
        if (scoreDiff !== 0) return scoreDiff;
        return a.project_code.localeCompare(b.project_code);
      });
  }, [data, search, statusFilter, attentionOnly, healthMap]);

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
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2.5">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <ErrorState title="Failed to load projects" action={
        <button className="text-xs font-medium text-primary hover:underline" onClick={() => refetch()}>Retry</button>
      } />
    );
  }

  return (
    <WorkspaceLayout
        title={t("Projects")}
        subtitle={`${data?.length ?? 0} total · ${filtered.length} shown`}
        backLabel="Back to Operations"
        backHref="/operations"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Operations", href: "/operations" },
          { label: "Projects" },
        ]}
        toolbar={
          <>
            <SearchInput value={search} onChange={setSearch} placeholder={t("Search projects...")} testId="search-projects" />
            <FilterSelect
              className="min-w-40"
              value={statusFilter}
              onChange={setStatusFilter}
              testId="filter-status"
            >
              <option value="all">{t("All Statuses")}</option>
              {allStatuses.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </FilterSelect>
          </>
        }
      >

      {/* Quick triage — sorted-list scanability is the default; this chip
          lets a PM collapse straight to only what needs a decision. */}
      <div className="flex flex-wrap items-center gap-2">
        <FilterChip active={!attentionOnly} onClick={() => setAttentionOnly(false)}>
          All Projects ({data?.length ?? 0})
        </FilterChip>
        <FilterChip active={attentionOnly} onClick={() => setAttentionOnly(true)} tone="amber">
          Needs Attention ({attentionCount})
        </FilterChip>
      </div>

      {filtered.length === 0 ? (
        <div className="panel">
          <EmptyState
            icon={FolderKanban}
            title={search || statusFilter !== "all" || attentionOnly ? "No projects match your filters" : "No projects yet"}
            description={
              search || statusFilter !== "all" || attentionOnly
                ? "Try adjusting your search, status, or attention filter."
                : "Projects will appear here once they're added to the portfolio."
            }
          />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2.5" data-testid="projects-grid">
          {filtered.map((project) => {
            const health = healthMap.get(project.id);
            const attention = needsAttention(project.status, health?.level);
            return (
              <Link
                key={project.id}
                href={`/projects/${project.id}`}
                data-testid={`project-link-${project.id}`}
                className={`panel p-3 flex flex-col gap-2 hover:border-primary/30 hover:-translate-y-0.5 transition-all duration-150 group ${attention ? "border-s-2 border-s-red-500" : ""}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-semibold text-foreground truncate">{project.project_code}</p>
                    <p className="text-xs text-muted-foreground truncate">{project.project_name}</p>
                  </div>
                  <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/40 shrink-0 mt-0.5 group-hover:translate-x-0.5 group-hover:text-primary transition-all" />
                </div>

                <div className="flex items-center gap-2 flex-wrap">
                  <span className={`badge ${getStatusBadge(project.status)} text-[10px]`}>{project.status}</span>
                  <span className="text-[11px] text-muted-foreground truncate">
                    {project.city || "—"}{project.client_name ? ` · ${project.client_name}` : ""}
                  </span>
                </div>

                {health ? (
                  <HealthBadge score={health.score} level={health.level} />
                ) : (
                  <span className="text-[10px] text-muted-foreground">No health score yet</span>
                )}
              </Link>
            );
          })}
        </div>
      )}
    </WorkspaceLayout>
  );
}
