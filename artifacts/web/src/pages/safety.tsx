import { useMemo, useState, useEffect } from "react";
import {
  useListProjects,
  useListProjectSafetyEvents,
  useListProjectNcrs,
} from "@workspace/api-client-react";
import { Link } from "wouter";
import { useTranslation } from "react-i18next";
import {
  ShieldAlert, AlertOctagon, AlertTriangle, ClipboardCheck, Activity,
  FileStack, Clock, Sparkles, Info, Building2, ListChecks,
} from "lucide-react";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { PageTabs } from "@/components/page-tabs";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { FilterSelect } from "@/components/filter-select";
import { StatTile } from "@/components/stat-tile";
import { WorkspaceQuickLink } from "@/components/WorkspaceQuickLink";
import { InsightPanel } from "@/components/InsightPanel";
import { AIActionPanel } from "@/components/AIActionPanel";

// ── Safety — operational safety workspace (Phase 2) ─────────────────────────
// Every number and card here comes straight from the existing project-scoped
// GET .../safety-events and GET .../ncrs lists — the only safety/quality
// reads the backend exposes (see backend/app/api/v1/safety.py). There is no
// portfolio-wide safety feed, no subcontractor/supplier name resolution on
// either record (both are raw foreign keys — see schemas/safety.py), no
// investigation/assignee/resolution-owner field on either table, and no
// POST endpoint to log a new event or NCR, and no per-record detail route.
// Rather than invent any of that, this page says so wherever the design
// calls for it instead of rendering a fabricated value or a dead link.

type Tab = "events" | "ncrs";

const SEVERITY_BADGE: Record<string, string> = {
  Low: "badge-success",
  Medium: "badge-warning",
  High: "badge-danger",
  Critical: "badge-danger",
};

const NCR_STATUS_BADGE: Record<string, string> = {
  Open: "badge-danger",
  Closed: "badge-success",
  "Under Corrective Action": "badge-warning",
  "In Progress": "badge-warning",
};

function isHighSeverity(severity: string): boolean {
  return severity === "High" || severity === "Critical";
}
function isOpenNcr(status: string): boolean {
  return status !== "Closed";
}
function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

const RECENT_PREVIEW_COUNT = 6;

export default function Safety() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>("events");
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [showAllEvents, setShowAllEvents] = useState(false);
  const [showAllNcrs, setShowAllNcrs] = useState(false);

  const { data: projects } = useListProjects({ limit: 60 });

  useEffect(() => {
    if (projects && projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  const { data: events, isLoading: eventsLoading, isError: eventsError } = useListProjectSafetyEvents(
    selectedProjectId ?? 0,
    { limit: 50 },
    { query: { enabled: !!selectedProjectId, queryKey: ["safety-events", selectedProjectId] } }
  );

  const { data: ncrs, isLoading: ncrsLoading, isError: ncrsError } = useListProjectNcrs(
    selectedProjectId ?? 0,
    { limit: 50 },
    { query: { enabled: !!selectedProjectId, queryKey: ["ncrs", selectedProjectId] } }
  );

  const selectedProject = projects?.find((p) => p.id === selectedProjectId);
  const isLoading = eventsLoading || ncrsLoading;
  const isError = eventsError || ncrsError;

  const today = todayStr();
  const highSeverityEvents = useMemo(
    () => (events ?? []).filter((e) => isHighSeverity(e.severity)).sort((a, b) => b.event_date.localeCompare(a.event_date)),
    [events],
  );
  const openNcrs = useMemo(
    () => (ncrs ?? []).filter((n) => isOpenNcr(n.status)).sort((a, b) => b.issue_date.localeCompare(a.issue_date)),
    [ncrs],
  );
  const loggedToday = useMemo(
    () =>
      (events ?? []).filter((e) => e.event_date === today).length +
      (ncrs ?? []).filter((n) => n.issue_date === today).length,
    [events, ncrs, today],
  );
  const condition: "Stable" | "Monitor" | "Needs Action" =
    highSeverityEvents.length > 0 ? "Needs Action" : openNcrs.length > 0 ? "Monitor" : "Stable";
  const conditionTone = condition === "Needs Action" ? "danger" : condition === "Monitor" ? "warning" : "success";

  // Needs Attention — high-severity events + open NCRs, the only two real
  // "requires action" signals the backend exposes for this project.
  const attentionItems = useMemo(
    () =>
      [
        ...highSeverityEvents.map((e) => ({
          id: `safety-${e.id}`, date: e.event_date, label: `${e.severity} severity safety event`,
          detail: e.description, tone: "badge-danger" as const, icon: ShieldAlert,
        })),
        ...openNcrs.map((n) => ({
          id: `ncr-${n.id}`, date: n.issue_date, label: `Open NCR — ${n.ncr_type}`,
          detail: n.description, tone: "badge-warning" as const, icon: ClipboardCheck,
        })),
      ].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 8),
    [highSeverityEvents, openNcrs],
  );

  const timelineItems = useMemo(
    () =>
      [
        ...(events ?? []).map((e) => ({
          id: `safety-${e.id}`, date: e.event_date, type: "Safety Event" as const,
          label: e.description, tone: SEVERITY_BADGE[e.severity] ?? "badge-neutral", tag: e.severity,
        })),
        ...(ncrs ?? []).map((n) => ({
          id: `ncr-${n.id}`, date: n.issue_date, type: "NCR" as const,
          label: n.description, tone: NCR_STATUS_BADGE[n.status] ?? "badge-neutral", tag: n.status,
        })),
      ].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 10),
    [events, ncrs],
  );

  const visibleEvents = showAllEvents ? events ?? [] : (events ?? []).slice(0, RECENT_PREVIEW_COUNT);
  const visibleNcrs = showAllNcrs ? ncrs ?? [] : (ncrs ?? []).slice(0, RECENT_PREVIEW_COUNT);

  return (
    <WorkspaceLayout
      title={t("Safety")}
      subtitle={`${
        selectedProject ? `${selectedProject.project_code} — ${selectedProject.project_name}` : "Select a project to begin"
      }${events ? ` · ${events.length} ${t("Safety Events")}` : ""}${ncrs ? ` · ${ncrs.length} NCRs` : ""}`}
      backLabel="Back to Operations"
      backHref="/operations"
      breadcrumbs={[
        { label: "Dashboard", href: "/" },
        { label: "Operations", href: "/operations" },
        { label: t("Safety") },
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
          <EmptyState icon={ShieldAlert} title={t("Select a project to view data")} />
        </div>
      ) : isLoading ? (
        <div className="space-y-6">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
          </div>
          <Skeleton className="h-40 w-full rounded-xl" />
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => <Skeleton key={i} className="h-40 w-full rounded-xl" />)}
          </div>
        </div>
      ) : isError ? (
        <div className="panel">
          <div className="text-center py-10">
            <div className="flex flex-col items-center gap-1 text-muted-foreground">
              <AlertOctagon className="w-6 h-6 text-destructive opacity-60" />
              <span className="text-sm">Failed to load safety data</span>
            </div>
          </div>
        </div>
      ) : !events?.length && !ncrs?.length ? (
        <div className="panel">
          <EmptyState
            icon={ShieldAlert}
            title="No safety data yet"
            description="Safety events and NCRs for this project will appear here once logged."
          />
        </div>
      ) : (
        <div className="space-y-6">
          {/* 1 — Current Safety Status ────────────────────────────────── */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Clock className="w-4 h-4 text-muted-foreground shrink-0" />
              <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Current Safety Status
              </h2>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <StatTile
                icon={ClipboardCheck}
                label="Open NCRs"
                value={openNcrs.length}
                description="Not yet closed"
                tone={openNcrs.length > 0 ? "warning" : "success"}
              />
              <StatTile
                icon={ShieldAlert}
                label="High-Severity Events"
                value={highSeverityEvents.length}
                description="High/Critical severity"
                tone={highSeverityEvents.length > 0 ? "danger" : "success"}
              />
              <StatTile
                icon={FileStack}
                label="Logged Today"
                value={loggedToday}
                description={today}
                tone={loggedToday > 0 ? "neutral" : "neutral"}
              />
              <StatTile
                icon={Activity}
                label="Overall Safety Condition"
                value={condition}
                description={`${events?.length ?? 0} events · ${ncrs?.length ?? 0} NCRs total`}
                tone={conditionTone}
              />
            </div>
            <p className="text-[11px] text-muted-foreground mt-2 flex items-start gap-1.5">
              <Info className="w-3 h-3 shrink-0 mt-0.5" />
              Workforce/incident counts beyond safety events and NCRs (e.g. near-misses, toolbox-talk attendance)
              aren't tracked in the backend, so they aren't shown here.
            </p>
          </div>

          {/* 2 — Needs Attention ─────────────────────────────────────── */}
          <InsightPanel
            icon={AlertTriangle}
            title="Needs Attention"
            variant="brief"
            badge={
              attentionItems.length === 0
                ? <span className="badge badge-success text-[9px]">All Clear</span>
                : <span className="badge badge-warning text-[9px]">{attentionItems.length}</span>
            }
          >
            {attentionItems.length === 0 ? (
              <p className="text-[13px] text-muted-foreground leading-normal">
                No high-severity safety events or open NCRs for this project right now.
              </p>
            ) : (
              <div className="space-y-1">
                {attentionItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <div key={item.id} className="flex items-start gap-2.5 px-2 py-1.5 rounded-md text-sm text-foreground">
                      <Icon className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
                      <span className="flex-1 min-w-0">
                        <span className="flex items-center gap-2">
                          <span className={`badge ${item.tone} text-[9px] shrink-0`}>{item.label}</span>
                          <span className="text-[11px] text-muted-foreground shrink-0">{item.date}</span>
                        </span>
                        <span className="block text-xs text-muted-foreground truncate mt-0.5">{item.detail}</span>
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
            <p className="text-[10.5px] text-muted-foreground/70 mt-2 pt-2 border-t border-border/50">
              Investigation status, assigned owner, and resolution deadline aren't tracked fields on safety events
              or NCRs yet — this list can only show that something is open, not who is handling it or by when.
            </p>
          </InsightPanel>

          {/* 3 — Recent Events / NCRs (primary content) ───────────────── */}
          <div id="recent-safety">
            <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-muted-foreground shrink-0" />
                <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Recent</h2>
              </div>
              <PageTabs<Tab>
                tabs={[
                  { id: "events", label: t("Safety Events"), count: events?.length },
                  { id: "ncrs", label: t("NCRs"), count: ncrs?.length },
                ]}
                value={tab}
                onChange={setTab}
              />
            </div>

            {tab === "events" ? (
              !events?.length ? (
                <div className="panel">
                  <EmptyState icon={ShieldAlert} title="No safety events logged" description="Safety events for this project will appear here." />
                </div>
              ) : (
                <>
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3" data-testid="safety-events-cards">
                    {visibleEvents.map((e) => (
                      <article key={e.id} className="panel p-4 flex flex-col">
                        <div className="mb-2 flex items-start justify-between gap-2">
                          <span className={`badge ${SEVERITY_BADGE[e.severity] ?? "badge-neutral"} shrink-0`}>{e.severity}</span>
                          <span className="text-[11px] text-muted-foreground">{e.event_date}</span>
                        </div>
                        <p className="text-xs text-foreground line-clamp-3 mb-2">{e.description}</p>
                        <p className="text-xs text-muted-foreground line-clamp-2 mt-auto pt-2 border-t border-border/50">
                          <span className="font-semibold text-foreground">Corrective action:</span> {e.corrective_action}
                        </p>
                      </article>
                    ))}
                  </div>
                  {events.length > RECENT_PREVIEW_COUNT && (
                    <button type="button" onClick={() => setShowAllEvents((v) => !v)} className="text-xs font-medium text-primary hover:underline mt-3">
                      {showAllEvents ? "Show recent only" : `Show all ${events.length}`}
                    </button>
                  )}
                </>
              )
            ) : !ncrs?.length ? (
              <div className="panel">
                <EmptyState icon={ClipboardCheck} title="No NCRs logged" description="Non-conformance reports for this project will appear here." />
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3" data-testid="ncrs-cards">
                  {visibleNcrs.map((n) => (
                    <article key={n.id} className="panel p-4 flex flex-col">
                      <div className="mb-2 flex items-start justify-between gap-2">
                        <span className={`badge ${NCR_STATUS_BADGE[n.status] ?? "badge-neutral"} shrink-0`}>{n.status}</span>
                        <span className="text-[11px] text-muted-foreground">{n.issue_date}</span>
                      </div>
                      <p className="text-[11px] font-semibold text-foreground mb-1">{n.ncr_type}</p>
                      <p className="text-xs text-muted-foreground line-clamp-3 mb-2">{n.description}</p>
                      <p className="text-xs text-muted-foreground line-clamp-2 mt-auto pt-2 border-t border-border/50">
                        <span className="font-semibold text-foreground">Root cause:</span> {n.root_cause}
                      </p>
                    </article>
                  ))}
                </div>
                {ncrs.length > RECENT_PREVIEW_COUNT && (
                  <button type="button" onClick={() => setShowAllNcrs((v) => !v)} className="text-xs font-medium text-primary hover:underline mt-3">
                    {showAllNcrs ? "Show recent only" : `Show all ${ncrs.length}`}
                  </button>
                )}
              </>
            )}
          </div>

          {/* 4 — Timeline ─────────────────────────────────────────────── */}
          <div className="panel">
            <div className="panel-header">
              <span className="panel-title flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5" /> Safety Timeline
              </span>
            </div>
            <div className="panel-body p-3 space-y-1">
              {timelineItems.length === 0 ? (
                <p className="text-xs text-muted-foreground py-2 px-1.5">No safety events or NCRs recorded yet.</p>
              ) : (
                timelineItems.map((item) => (
                  <div key={item.id} className="flex items-center gap-3 py-2 px-2 -mx-2 rounded-lg">
                    <span
                      className="w-2 h-2 rounded-full shrink-0"
                      style={{
                        backgroundColor:
                          item.tone === "badge-danger" ? "#dc2626" : item.tone === "badge-warning" ? "#d97706" : "#16a34a",
                      }}
                    />
                    <span className="text-xs font-medium text-foreground shrink-0 tabular-nums w-24">{item.date}</span>
                    <span className="badge badge-neutral text-[9px] shrink-0">{item.type}</span>
                    <span className="text-xs text-muted-foreground truncate flex-1 min-w-0">{item.label}</span>
                    <span className={`badge ${item.tone} text-[9px] shrink-0`}>{item.tag}</span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* 5 — Quick Actions ────────────────────────────────────────── */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <ListChecks className="w-4 h-4 text-muted-foreground shrink-0" />
              <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Quick Actions</h2>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
              <div className="panel p-2.5 flex flex-col gap-1.5 opacity-60 cursor-not-allowed" title="Not available yet — no backend endpoint exists to log a safety event.">
                <div className="w-6 h-6 rounded-md flex items-center justify-center shrink-0 bg-muted text-muted-foreground">
                  <ShieldAlert className="w-3.5 h-3.5" />
                </div>
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold text-foreground truncate leading-tight">Report Safety Event</p>
                  <p className="text-[9px] text-muted-foreground truncate mt-0.5">Not available yet</p>
                </div>
              </div>
              <div className="panel p-2.5 flex flex-col gap-1.5 opacity-60 cursor-not-allowed" title="Not available yet — no backend endpoint exists to file an NCR.">
                <div className="w-6 h-6 rounded-md flex items-center justify-center shrink-0 bg-muted text-muted-foreground">
                  <ClipboardCheck className="w-3.5 h-3.5" />
                </div>
                <div className="min-w-0">
                  <p className="text-[11px] font-semibold text-foreground truncate leading-tight">File NCR</p>
                  <p className="text-[9px] text-muted-foreground truncate mt-0.5">Not available yet</p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => {
                  setShowAllEvents(true);
                  setShowAllNcrs(true);
                  document.getElementById("recent-safety")?.scrollIntoView({ behavior: "smooth" });
                }}
                className="text-start"
              >
                <div className="panel p-2.5 flex flex-col gap-1.5 hover:border-primary/30 hover:-translate-y-0.5 transition-all duration-150">
                  <div className="w-6 h-6 rounded-md flex items-center justify-center shrink-0 bg-muted text-sky-600 dark:text-sky-400">
                    <FileStack className="w-3.5 h-3.5" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-[11px] font-semibold text-foreground truncate leading-tight">View All</p>
                    <p className="text-[9px] text-muted-foreground truncate mt-0.5">
                      {(events?.length ?? 0) + (ncrs?.length ?? 0)} total
                    </p>
                  </div>
                </div>
              </button>
              <WorkspaceQuickLink icon={Building2} title="Project" meta="Project overview" href={`/projects/${selectedProjectId}`} accent="text-sky-600 dark:text-sky-400" variant="card" />
              <WorkspaceQuickLink icon={FileStack} title="Site Reports" meta="Daily site reports" href="/site-reports" accent="text-emerald-600 dark:text-emerald-400" variant="card" />
              <WorkspaceQuickLink icon={Sparkles} title="AI Analysis" meta="Project Intelligence" href="/ai-center/projects" accent="text-accent" variant="card" />
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
