import { useMemo, useState, useEffect } from "react";
import { useListProjects } from "@workspace/api-client-react";
import { Link } from "wouter";
import { useTranslation } from "react-i18next";
import {
  CloudSun, AlertOctagon, ChevronRight, FileStack, AlertTriangle, Activity,
  ClipboardCheck, ClipboardList, ShieldAlert, Folder, Building2, ListChecks,
  Clock, Sparkles, Info,
} from "lucide-react";
import { getToken } from "@/lib/auth";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { FilterSelect } from "@/components/filter-select";
import { StatTile } from "@/components/stat-tile";
import { WorkspaceQuickLink } from "@/components/WorkspaceQuickLink";
import { AIActionPanel } from "@/components/AIActionPanel";

// ── Site Reports — daily operational workspace (Phase 2) ───────────────────
// Every number and list on this page comes from the existing project-scoped
// GET .../site-reports/cards response (report_id, project_id, project_name,
// report_date, engineer, weather, work_progress, risk_indicator,
// safety_indicator, quality_indicator) — the only bulk site-report read the
// backend exposes today. "Today's Site Status" and "Needs Attention" are
// derived client-side from those same fields, not a second endpoint.
// Workforce count, equipment issues, and a report review/approval workflow
// are NOT columns anywhere in the backend (see backend/app/models/site.py
// and schemas/site.py) — rather than fabricate them, this page says so
// explicitly wherever the spec calls for them.

const WEATHER_BADGE: Record<string, string> = {
  Clear: "badge-success",
  Windy: "badge-warning",
  Hot: "badge-warning",
  Humid: "badge-info",
  Dusty: "badge-warning",
  "Light Rain": "badge-info",
};

// Same Low/Medium/High/Critical → badge-tone mapping already used across the
// app for severity labels (e.g. ai-center/workspaces/*/shared.tsx).
const SEVERITY_BADGE: Record<string, string> = {
  Low: "badge-success",
  Medium: "badge-info",
  High: "badge-warning",
  Critical: "badge-danger",
};
const SEVERITY_RANK: Record<string, number> = { Low: 0, Medium: 1, High: 2, Critical: 3 };
const CONDITION_LABEL: Record<string, string> = {
  Low: "Stable",
  Medium: "Fair",
  High: "Needs Attention",
  Critical: "Critical",
};

type ReportCard = {
  report_id: number;
  project_id: number;
  project_name: string;
  report_date: string;
  engineer?: string | null;
  weather: string;
  work_progress: string;
  risk_indicator: string;
  safety_indicator: string;
  quality_indicator: string;
};

function worstIndicator(card: ReportCard): string {
  return [card.risk_indicator, card.safety_indicator, card.quality_indicator].reduce(
    (worst, v) => ((SEVERITY_RANK[v] ?? 0) > (SEVERITY_RANK[worst] ?? 0) ? v : worst),
    "Low",
  );
}

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

const RECENT_PREVIEW_COUNT = 6;

export default function SiteReports() {
  const { t } = useTranslation();
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [cards, setCards] = useState<ReportCard[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);
  const [showAllReports, setShowAllReports] = useState(false);

  const { data: projects } = useListProjects({ limit: 60 });

  useEffect(() => {
    if (projects && projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  useEffect(() => {
    let mounted = true;
    const loadCards = async () => {
      if (!selectedProjectId) return;
      setIsLoading(true);
      setIsError(false);
      setShowAllReports(false);
      try {
        const token = getToken();
        const response = await fetch(`/api/v1/projects/${selectedProjectId}/site-reports/cards?limit=50`, {
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });
        if (!response.ok) {
          throw new Error("Failed to load report cards");
        }
        const data = await response.json();
        if (mounted) {
          setCards(data);
        }
      } catch {
        if (mounted) {
          setIsError(true);
          setCards([]);
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    loadCards();
    return () => {
      mounted = false;
    };
  }, [selectedProjectId]);

  const selectedProject = projects?.find((p) => p.id === selectedProjectId);

  const today = todayStr();
  const reportsToday = useMemo(() => (cards ?? []).filter((c) => c.report_date === today), [cards, today]);
  const flaggedCards = useMemo(
    () =>
      (cards ?? [])
        .map((c) => ({ card: c, severity: worstIndicator(c) }))
        .filter((x) => x.severity === "High" || x.severity === "Critical")
        .sort((a, b) => SEVERITY_RANK[b.severity] - SEVERITY_RANK[a.severity])
        .slice(0, 8),
    [cards],
  );
  const latestCard = cards && cards.length > 0 ? cards[0] : null;
  const latestWeatherCard = reportsToday[0] ?? latestCard;
  const overallSeverity = latestCard ? worstIndicator(latestCard) : null;
  const visibleCards = showAllReports ? cards ?? [] : (cards ?? []).slice(0, RECENT_PREVIEW_COUNT);

  return (
    <WorkspaceLayout
      title={t("Site Reports")}
      subtitle={`${
        selectedProject
          ? `${selectedProject.project_code} — ${selectedProject.project_name}`
          : "Select a project to begin"
      }${cards ? ` · ${cards.length} reports` : ""}`}
      backLabel="Back to Operations"
      backHref="/operations"
      breadcrumbs={[
        { label: "Dashboard", href: "/" },
        { label: "Operations", href: "/operations" },
        { label: "Site Reports" },
      ]}
      toolbar={
        <FilterSelect
          className="min-w-52"
          value={String(selectedProjectId ?? "")}
          onChange={(v) => setSelectedProjectId(Number(v))}
          testId="project-selector"
        >
          <option value="" disabled>{t("Select Project")}</option>
          {projects?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.project_code} — {p.project_name}
            </option>
          ))}
        </FilterSelect>
      }
    >
      {!selectedProjectId ? (
        <div className="panel">
          <EmptyState icon={CloudSun} title={t("Select a project to view data")} />
        </div>
      ) : isLoading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
          </div>
          <Skeleton className="h-40 w-full rounded-xl" />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => <Skeleton key={i} className="h-44 w-full rounded-xl" />)}
          </div>
        </div>
      ) : isError ? (
        <div className="panel">
          <div className="text-center py-10">
            <div className="flex flex-col items-center gap-1 text-muted-foreground">
              <AlertOctagon className="w-6 h-6 text-destructive opacity-60" />
              <span className="text-sm">Failed to load site reports</span>
            </div>
          </div>
        </div>
      ) : !cards?.length ? (
        <div className="panel">
          <EmptyState
            icon={FileStack}
            title="No site reports yet"
            description="Site reports for this project will appear here once submitted."
          />
        </div>
      ) : (
        <div className="space-y-6">
          {/* 1 — Today's Site Status ─────────────────────────────────── */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Clock className="w-4 h-4 text-muted-foreground shrink-0" />
              <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Today's Site Status
              </h2>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <StatTile
                icon={FileStack}
                label="Reports Today"
                value={reportsToday.length}
                description={today}
                tone={reportsToday.length > 0 ? "success" : "neutral"}
              />
              <StatTile
                icon={AlertTriangle}
                label="High-Risk Reports"
                value={flaggedCards.length}
                description="High/Critical, recent reports"
                tone={flaggedCards.length > 0 ? "danger" : "success"}
              />
              <StatTile
                icon={CloudSun}
                label="Weather"
                value={latestWeatherCard?.weather ?? "—"}
                description={reportsToday.length > 0 ? "Today" : `Latest — ${latestWeatherCard?.report_date ?? "n/a"}`}
                tone="neutral"
              />
              <StatTile
                icon={Activity}
                label="Overall Site Condition"
                value={overallSeverity ? CONDITION_LABEL[overallSeverity] : "—"}
                description={latestCard ? `From ${latestCard.report_date}` : undefined}
                tone={
                  overallSeverity === "Critical" || overallSeverity === "High"
                    ? "danger"
                    : overallSeverity === "Medium"
                      ? "warning"
                      : "success"
                }
              />
            </div>
            <p className="text-[11px] text-muted-foreground mt-2 flex items-start gap-1.5">
              <Info className="w-3 h-3 shrink-0 mt-0.5" />
              Workforce count and equipment issues aren't tracked as structured fields in the backend yet — they
              only appear as free text inside individual reports, so they can't be shown as reliable site-wide
              numbers here.
            </p>
          </div>

          {/* 2 — Needs Attention ─────────────────────────────────────── */}
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
                Needs Attention
              </span>
              {flaggedCards.length > 0 && <span className="badge badge-warning text-[10px]">{flaggedCards.length}</span>}
            </div>
            <div className="panel-body p-2">
              {flaggedCards.length === 0 ? (
                <p className="text-xs text-muted-foreground py-2 px-1.5">
                  No reports currently flag a high or critical risk, safety, or quality signal.
                </p>
              ) : (
                <div className="space-y-px">
                  {flaggedCards.map(({ card, severity }) => (
                    <Link
                      key={card.report_id}
                      href={`/projects/${card.project_id}/site-reports/${card.report_id}`}
                      className="grid grid-cols-[auto_1fr_auto] items-center gap-2 px-2 py-2 rounded-lg hover:bg-muted/50 transition-colors"
                    >
                      <span className={`badge ${SEVERITY_BADGE[severity]} text-[10px]`}>{severity}</span>
                      <span className="min-w-0">
                        <p className="text-xs font-semibold text-foreground truncate leading-tight">
                          {card.project_name} · {card.report_date}
                        </p>
                        <p className="text-[10.5px] text-muted-foreground truncate leading-tight mt-0.5">
                          Risk: {card.risk_indicator} · Safety: {card.safety_indicator} · Quality: {card.quality_indicator}
                        </p>
                      </span>
                      <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0" />
                    </Link>
                  ))}
                </div>
              )}
              <p className="text-[11px] text-muted-foreground mt-1 px-1.5 flex items-start gap-1.5">
                <Info className="w-3 h-3 shrink-0 mt-0.5" />
                A report review/approval workflow isn't tracked in the backend, so "awaiting review" can't be
                shown as a real status here.
              </p>
            </div>
          </div>

          {/* 3 — Recent Reports (primary content) ────────────────────── */}
          <div id="recent-reports">
            <div className="flex items-center justify-between gap-3 mb-3">
              <div className="flex items-center gap-2">
                <FileStack className="w-4 h-4 text-muted-foreground shrink-0" />
                <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  Recent Reports
                </h2>
              </div>
              {(cards?.length ?? 0) > RECENT_PREVIEW_COUNT && (
                <button
                  type="button"
                  onClick={() => setShowAllReports((v) => !v)}
                  className="text-xs font-medium text-primary hover:underline"
                >
                  {showAllReports ? "Show recent only" : `Show all ${cards?.length}`}
                </button>
              )}
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3" data-testid="site-reports-cards">
              {visibleCards.map((card) => {
                const severity = worstIndicator(card);
                const needsFollowUp = severity === "High" || severity === "Critical";
                return (
                  <article key={card.report_id} className="panel p-4 flex flex-col">
                    <div className="mb-2 flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-foreground truncate">{card.project_name}</p>
                        <p className="text-[11px] text-muted-foreground">{card.report_date}</p>
                      </div>
                      <span className={`badge ${SEVERITY_BADGE[card.risk_indicator] ?? "badge-neutral"} shrink-0`}>
                        {card.risk_indicator} Risk
                      </span>
                    </div>

                    <p className="text-xs text-muted-foreground mb-2">
                      <span className="font-semibold text-foreground">Engineer:</span> {card.engineer || "Not assigned"}
                    </p>

                    <p className="text-xs text-muted-foreground line-clamp-2 mb-3 flex-1">{card.work_progress}</p>

                    <div className="flex flex-wrap items-center gap-1.5 mb-3">
                      <span className={`badge ${WEATHER_BADGE[card.weather] ?? "badge-neutral"} text-[10px]`}>{card.weather}</span>
                      <span className={`badge ${SEVERITY_BADGE[card.safety_indicator] ?? "badge-neutral"} text-[10px]`}>
                        Safety: {card.safety_indicator}
                      </span>
                      <span className={`badge ${SEVERITY_BADGE[card.quality_indicator] ?? "badge-neutral"} text-[10px]`}>
                        Quality: {card.quality_indicator}
                      </span>
                      {needsFollowUp && <span className="badge badge-danger text-[10px]">Needs Follow-up</span>}
                    </div>

                    <Link
                      href={`/projects/${card.project_id}/site-reports/${card.report_id}`}
                      className="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline mt-auto"
                    >
                      Open Report
                      <ChevronRight className="w-3.5 h-3.5" />
                    </Link>
                  </article>
                );
              })}
            </div>
          </div>

          {/* 4 — Report Timeline ──────────────────────────────────────── */}
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" /> Report Timeline
              </span>
            </div>
            <div className="panel-body p-3 space-y-1">
              {cards.slice(0, 10).map((card) => {
                const severity = worstIndicator(card);
                return (
                  <Link
                    key={card.report_id}
                    href={`/projects/${card.project_id}/site-reports/${card.report_id}`}
                    className="flex items-center gap-3 py-2 px-2 -mx-2 rounded-lg hover:bg-muted/50 transition-colors"
                  >
                    <span
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{
                        backgroundColor:
                          severity === "Critical" ? "#dc2626" : severity === "High" ? "#d97706" : severity === "Medium" ? "#2563eb" : "#16a34a",
                      }}
                    />
                    <span className="text-xs font-medium text-foreground shrink-0 tabular-nums w-24">{card.report_date}</span>
                    <span className="text-xs text-muted-foreground truncate flex-1 min-w-0">{card.work_progress}</span>
                    <span className={`badge ${SEVERITY_BADGE[severity]} text-[9px] shrink-0`}>{severity}</span>
                  </Link>
                );
              })}
            </div>
          </div>

          {/* 5 — Quick Actions ────────────────────────────────────────── */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <ListChecks className="w-4 h-4 text-muted-foreground shrink-0" />
              <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Quick Actions</h2>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
              <div className="panel p-2.5 flex flex-col gap-1.5 opacity-60 cursor-not-allowed" title="Not available yet — no backend endpoint exists to create a site report.">
                <div className="flex items-center justify-between">
                  <div className="w-6 h-6 rounded-md flex items-center justify-center shrink-0 bg-muted text-muted-foreground">
                    <ClipboardCheck className="w-3.5 h-3.5" />
                  </div>
                </div>
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold text-foreground truncate leading-tight">Submit New Report</p>
                  <p className="text-[9px] text-muted-foreground truncate mt-0.5">Not available yet</p>
                </div>
              </div>
              <button type="button" onClick={() => { setShowAllReports(true); document.getElementById("recent-reports")?.scrollIntoView({ behavior: "smooth" }); }} className="text-start">
                <div className="panel p-2.5 flex flex-col gap-1.5 hover:border-primary/30 hover:-translate-y-0.5 transition-all duration-150">
                  <div className="w-6 h-6 rounded-md flex items-center justify-center shrink-0 bg-muted text-sky-600 dark:text-sky-400">
                    <FileStack className="w-3.5 h-3.5" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-[11px] font-semibold text-foreground truncate leading-tight">View All Reports</p>
                    <p className="text-[9px] text-muted-foreground truncate mt-0.5">{cards.length} total</p>
                  </div>
                </div>
              </button>
              <WorkspaceQuickLink icon={Building2} title="Project" meta="Project overview" href={`/projects/${selectedProjectId}`} accent="text-sky-600 dark:text-sky-400" variant="card" />
              <WorkspaceQuickLink icon={ShieldAlert} title="Safety" meta="Events & NCRs" href="/safety" accent="text-rose-600 dark:text-rose-400" variant="card" />
              <WorkspaceQuickLink icon={Folder} title="Documents" meta="Document library" href="/documents" accent="text-violet-600 dark:text-violet-400" variant="card" />
              <WorkspaceQuickLink icon={ClipboardList} title="AI Analysis" meta="Site Report Intelligence" href="/ai-center/site-reports" accent="text-accent" variant="card" />
            </div>
          </div>

          {/* 6 — AI Assistance ────────────────────────────────────────── */}
          {selectedProject && (
            <div className="panel">
              <div className="panel-header">
                <span className="panel-title flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-primary" /> AI Assistance
                </span>
              </div>
              <div className="panel-body p-4">
                <AIActionPanel
                  entityKind="project"
                  projectId={selectedProject.id}
                  projectCode={selectedProject.project_code}
                  projectName={selectedProject.project_name}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </WorkspaceLayout>
  );
}
