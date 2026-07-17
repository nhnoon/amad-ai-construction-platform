import { useEffect, useState } from "react";
import {
  useGetProject, useGetProjectHealth, useListProjectMeetings, useListProjectDecisions,
  useListProjectNcrs, useListProjectSafetyEvents, useListPurchaseOrders, useListSuppliers,
} from "@workspace/api-client-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useParams, useSearch, Link } from "wouter";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft, MapPin, Building2, Calendar, DollarSign, Hash, Tag, AlertOctagon,
  HeartPulse, ClipboardList, CalendarDays, FileSignature, Folder, Truck, ShieldAlert,
  Sparkles, ChevronRight, ExternalLink,
} from "lucide-react";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import CopilotPage from "@/pages/copilot";
import MemoryCenter from "@/pages/ai-center/MemoryCenter";
import { bucketFor } from "@/pages/ai-center/memoryTaxonomy";
import { getMemory, listDocuments } from "@/lib/aiCenterClient";
import { useExecutive } from "@/lib/useExecutive";
import { getToken } from "@/lib/auth";

const STATUS_BADGE: Record<string, string> = {
  Active:    "badge-success",
  Delayed:   "badge-danger",
  Completed: "badge-info",
  Suspended: "badge-neutral",
  Planning:  "badge-purple",
  "On Hold": "badge-warning",
};

const LEVEL_CONFIG: Record<string, { color: string; bg: string; border: string; label: string }> = {
  "Excellent": { color: "#16a34a", bg: "rgba(22,163,74,0.08)", border: "rgba(22,163,74,0.25)", label: "Excellent" },
  "Good": { color: "#2563eb", bg: "rgba(37,99,235,0.08)", border: "rgba(37,99,235,0.25)", label: "Good" },
  "At Risk": { color: "#d97706", bg: "rgba(217,119,6,0.08)", border: "rgba(217,119,6,0.25)", label: "At Risk" },
  "Critical": { color: "#dc2626", bg: "rgba(220,38,38,0.08)", border: "rgba(220,38,38,0.25)", label: "Critical" },
};

function DetailRow({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value?: string | number | null }) {
  if (!value && value !== 0) return null;
  return (
    <div className="flex items-start gap-3 py-3 border-b border-border last:border-0">
      <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center shrink-0 mt-0.5">
        <Icon className="w-4 h-4 text-muted-foreground" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-0.5">{label}</p>
        <p className="text-sm font-semibold text-foreground leading-snug">{value}</p>
      </div>
    </div>
  );
}

function formatBudget(v?: number | null) {
  if (v == null) return null;
  if (v >= 1_000_000_000) return `SAR ${(v / 1_000_000_000).toFixed(2)}B`;
  if (v >= 1_000_000) return `SAR ${(v / 1_000_000).toFixed(1)}M`;
  return `SAR ${v.toLocaleString()}`;
}

// ── Health Score tab ──────────────────────────────────────────────────────
function HealthScorePanel({ projectId }: { projectId: number }) {
  const { data: health, isLoading } = useGetProjectHealth(projectId, {
    query: { enabled: !!projectId, queryKey: ["project-health", projectId] },
  });

  if (isLoading) {
    return (
      <div className="panel">
        <div className="panel-body space-y-3">
          <Skeleton className="h-16 w-full rounded-xl" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      </div>
    );
  }

  if (!health) return <EmptyState icon={HeartPulse} title="Health score not available" />;

  const cfg = LEVEL_CONFIG[health.level] ?? LEVEL_CONFIG["Good"];

  return (
    <div className="panel">
      <div className="panel-body space-y-4">
        <div className="rounded-xl px-5 py-4 flex items-center gap-4" style={{ backgroundColor: cfg.bg, border: `1px solid ${cfg.border}` }}>
          <div className="relative w-16 h-16 shrink-0">
            <svg viewBox="0 0 64 64" className="w-16 h-16 -rotate-90">
              <circle cx="32" cy="32" r="26" fill="none" stroke="currentColor" strokeWidth="6" className="text-muted opacity-20" />
              <circle cx="32" cy="32" r="26" fill="none" strokeWidth="6"
                strokeDasharray={`${(health.score / 100) * 163.4} 163.4`} strokeLinecap="round"
                style={{ stroke: cfg.color, transition: "stroke-dasharray 0.6s ease" }} />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-sm font-bold tabular-nums" style={{ color: cfg.color }}>{health.score}</span>
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-0.5">Health Level</p>
            <p className="text-xl font-bold" style={{ color: cfg.color }}>{health.level}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{health.score}/100 health score</p>
          </div>
        </div>

        <div className="space-y-1.5">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Score</span>
            <span className="font-semibold" style={{ color: cfg.color }}>{health.score}/100</span>
          </div>
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div className="h-full rounded-full transition-all duration-700" style={{ width: `${health.score}%`, backgroundColor: cfg.color }} />
          </div>
        </div>

        {(health.schedule_penalty > 0 || health.safety_penalty > 0 || health.ncr_penalty > 0 || health.procurement_penalty > 0 || health.risk_penalty > 0) && (
          <div className="space-y-1.5">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Score Breakdown</p>
            {[
              { label: "Schedule", penalty: health.schedule_penalty },
              { label: "Safety Events", penalty: health.safety_penalty },
              { label: "Open NCRs", penalty: health.ncr_penalty },
              { label: "Late POs", penalty: health.procurement_penalty },
              { label: "Project Risks", penalty: health.risk_penalty },
            ].filter((f) => f.penalty > 0).map((f) => (
              <div key={f.label} className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">{f.label}</span>
                <span className="text-destructive font-semibold">−{f.penalty.toFixed(1)}</span>
              </div>
            ))}
          </div>
        )}

        {health.reasons.length > 0 ? (
          <div className="space-y-1.5">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Key Issues</p>
            <ul className="space-y-1">
              {health.reasons.map((reason, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-foreground">
                  <span className="mt-0.5 shrink-0" style={{ color: cfg.color }}>•</span>
                  <span>{reason}</span>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">✓ No issues detected — project is on track</p>
        )}
      </div>
    </div>
  );
}

// ── Meetings tab ──────────────────────────────────────────────────────────
function MeetingsTab({ projectId }: { projectId: number }) {
  const { data: meetings, isLoading } = useListProjectMeetings(projectId, { limit: 10 }, { query: { queryKey: ["pw-meetings", projectId] } });
  const { data: decisions } = useListProjectDecisions(projectId, { limit: 5 }, { query: { queryKey: ["pw-decisions", projectId] } });

  if (isLoading) return <div className="space-y-2">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}</div>;
  if (!meetings?.length) return <EmptyState icon={CalendarDays} title="No meetings yet" action={<Link href="/meetings" className="text-sm text-primary hover:underline">Create one in Meetings</Link>} />;

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        {meetings.map((m) => (
          <Link key={m.id} href={`/meetings/${m.project_id}/${m.id}`} className="flex items-center justify-between gap-3 rounded-xl border border-border bg-card p-3 hover:border-primary/30 transition-colors group">
            <div className="min-w-0">
              <p className="text-sm font-medium text-foreground truncate">{m.title}</p>
              <p className="text-xs text-muted-foreground">{m.meeting_date} &middot; {m.meeting_type}</p>
            </div>
            <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0 group-hover:translate-x-0.5 transition-transform" />
          </Link>
        ))}
      </div>
      {!!decisions?.length && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Recent Decisions</p>
          <div className="space-y-2">
            {decisions.map((d) => (
              <div key={d.id} className="rounded-lg border border-border/60 p-2.5 text-sm text-foreground">
                {d.decision_text}
                <p className="text-xs text-muted-foreground mt-0.5">{d.decision_date} &middot; {d.owner}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Site Reports tab ──────────────────────────────────────────────────────
function SiteReportsTab({ projectId }: { projectId: number }) {
  const { data: cards, isLoading } = useQuery({
    queryKey: ["pw-site-reports", projectId],
    queryFn: async () => {
      const token = getToken();
      const resp = await fetch(`/api/v1/projects/${projectId}/site-reports/cards?limit=8`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      return resp.ok ? resp.json() : [];
    },
  });

  if (isLoading) return <div className="grid gap-3 sm:grid-cols-2">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}</div>;
  if (!cards?.length) return <EmptyState icon={ClipboardList} title="No site reports yet" />;

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {cards.map((c: { report_id: number; report_date: string; risk_indicator: string }) => (
        <Link key={c.report_id} href={`/projects/${projectId}/site-reports/${c.report_id}`} className="flex items-center justify-between gap-2 rounded-xl border border-border bg-card p-3.5 hover:border-primary/30 transition-colors group">
          <div>
            <p className="text-sm font-medium text-foreground">{c.report_date}</p>
            <p className="text-xs text-muted-foreground">Risk: {c.risk_indicator}</p>
          </div>
          <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
        </Link>
      ))}
    </div>
  );
}

// ── Contracts + Documents tabs ────────────────────────────────────────────
function ContractsTab({ projectCode }: { projectCode: string }) {
  const { data } = useQuery({ queryKey: ["ai-center-memory"], queryFn: getMemory });
  const contracts = (data?.structured_memories ?? []).filter((m) => bucketFor(m.source, m.category) === "contract" && m.project_code === projectCode);

  if (!contracts.length) return <EmptyState icon={FileSignature} title="No contract extractions for this project yet" action={<Link href="/documents" className="text-sm text-primary hover:underline">Analyze a contract in Documents</Link>} />;

  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {contracts.map((c) => (
        <div key={c.id} className="rounded-xl border border-border bg-card p-4 space-y-1.5">
          <h4 className="font-semibold text-sm text-foreground">{c.title}</h4>
          <p className="text-sm text-muted-foreground line-clamp-3">{c.summary}</p>
        </div>
      ))}
    </div>
  );
}

function DocumentsTab({ projectId }: { projectId: number }) {
  const { data: documents, isLoading } = useQuery({
    queryKey: ["pw-documents", projectId],
    queryFn: () => listDocuments({ scope: "project", projectId, limit: 30 }),
  });

  if (isLoading) return <div className="space-y-2">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}</div>;
  if (!documents?.length) return <EmptyState icon={Folder} title="No documents for this project yet" action={<Link href="/documents" className="text-sm text-primary hover:underline">Upload in Documents</Link>} />;

  return (
    <div className="space-y-2">
      {documents.map((d) => (
        <div key={d.id} className="flex items-center justify-between gap-3 rounded-lg border border-border/60 p-3">
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground truncate">{d.title}</p>
            <p className="text-xs text-muted-foreground">{d.doc_type} &middot; {d.doc_date}</p>
          </div>
        </div>
      ))}
      <Link href="/documents" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline pt-1">
        Open Documents workspace <ExternalLink className="w-3 h-3" />
      </Link>
    </div>
  );
}

// ── Suppliers tab ─────────────────────────────────────────────────────────
function SuppliersTab({ projectId }: { projectId: number }) {
  const { data: orders, isLoading } = useListPurchaseOrders({ project_id: projectId, limit: 20 }, { query: { queryKey: ["pw-pos", projectId] } });
  const { data: suppliers } = useListSuppliers({ limit: 100 }, { query: { queryKey: ["pw-suppliers"] } });
  const supplierName = (id: number) => suppliers?.find((s) => s.id === id)?.supplier_name ?? `Supplier #${id}`;

  if (isLoading) return <div className="space-y-2">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-14 w-full rounded-lg" />)}</div>;
  if (!orders?.length) return <EmptyState icon={Truck} title="No purchase orders for this project yet" action={<Link href="/procurement" className="text-sm text-primary hover:underline">View Procurement</Link>} />;

  return (
    <div className="space-y-2">
      {orders.map((po) => (
        <div key={po.id} className="flex items-center justify-between gap-3 rounded-lg border border-border/60 p-3">
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground truncate">{supplierName(po.supplier_id)}</p>
            <p className="text-xs text-muted-foreground">{po.po_number} &middot; {po.status}</p>
          </div>
          {po.is_late && <span className="badge badge-danger shrink-0">Late {po.delay_days}d</span>}
        </div>
      ))}
    </div>
  );
}

// ── Risks tab ──────────────────────────────────────────────────────────────
function RisksTab({ projectId }: { projectId: number }) {
  const { data: ncrs, isLoading: ncrsLoading } = useListProjectNcrs(projectId, { limit: 10 }, { query: { queryKey: ["pw-ncrs", projectId] } });
  const { data: safety, isLoading: safetyLoading } = useListProjectSafetyEvents(projectId, { limit: 10 }, { query: { queryKey: ["pw-safety", projectId] } });

  if (ncrsLoading || safetyLoading) return <div className="space-y-2">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-16 w-full rounded-xl" />)}</div>;

  const openNcrs = (ncrs ?? []).filter((n) => n.status !== "Closed");

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Open NCRs</p>
        {!openNcrs.length ? <EmptyState icon={ShieldAlert} title="No open NCRs" /> : (
          <div className="space-y-2">
            {openNcrs.map((n) => (
              <div key={n.id} className="rounded-lg border border-border/60 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="badge badge-warning">{n.ncr_type}</span>
                  <span className="text-xs text-muted-foreground">{n.issue_date}</span>
                </div>
                <p className="text-sm text-foreground mt-1.5">{n.description}</p>
              </div>
            ))}
          </div>
        )}
      </div>
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Safety Events</p>
        {!safety?.length ? <EmptyState icon={AlertOctagon} title="No safety events" /> : (
          <div className="space-y-2">
            {safety.map((s) => (
              <div key={s.id} className="rounded-lg border border-border/60 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="badge badge-danger">{s.severity}</span>
                  <span className="text-xs text-muted-foreground">{s.event_date}</span>
                </div>
                <p className="text-sm text-foreground mt-1.5">{s.description}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── AI Summary tab ─────────────────────────────────────────────────────────
function AiSummaryTab({ projectId }: { projectId: number }) {
  const { data: exec, isLoading } = useExecutive();
  if (isLoading) return <Skeleton className="h-40 w-full rounded-xl" />;

  const brief = [...(exec?.top_priorities ?? []), ...(exec?.attention_required ?? []), ...(exec?.best_projects ?? [])]
    .find((b) => b.project_id === projectId);

  if (!brief) {
    return (
      <EmptyState
        icon={Sparkles}
        title="Not currently flagged in executive intelligence"
        description="That usually means nothing urgent stands out for this project — ask Hermes directly for a fresh read."
      />
    );
  }

  const cfg = LEVEL_CONFIG[brief.level] ?? LEVEL_CONFIG["Good"];
  return (
    <div className="rounded-xl p-5 space-y-3" style={{ backgroundColor: cfg.bg, border: `1px solid ${cfg.border}` }}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: cfg.color }}>{brief.level}</p>
        <p className="text-2xl font-bold tabular-nums" style={{ color: cfg.color }}>{brief.score}/100</p>
      </div>
      <p className="text-sm text-foreground">{brief.primary_reason}</p>
      <Link href="/ai-center/executive" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
        View in Executive Intelligence <ExternalLink className="w-3 h-3" />
      </Link>
    </div>
  );
}

export default function ProjectDetail() {
  const { t } = useTranslation();
  const params = useParams();
  const search = useSearch();
  const id = parseInt(params.id || "0", 10);
  const { data: project, isLoading, isError } = useGetProject(id, { query: { enabled: !!id, queryKey: ["project", id] } });

  const initialTab = new URLSearchParams(search).get("tab") ?? "overview";
  const [tab, setTab] = useState(initialTab);
  useEffect(() => { setTab(new URLSearchParams(search).get("tab") ?? "overview"); }, [search]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-5 w-32" />
        <div className="space-y-2">
          <Skeleton className="h-9 w-2/3" />
          <Skeleton className="h-5 w-32" />
        </div>
        <Skeleton className="h-10 w-full rounded-lg" />
        <Skeleton className="h-80 rounded-xl" />
      </div>
    );
  }

  if (isError || !project) {
    return (
      <div className="space-y-4">
        <Link href="/projects" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4" />{t("Back to Projects")}
        </Link>
        <div className="panel panel-body flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground">
          <AlertOctagon className="w-8 h-8 text-destructive opacity-60" />
          <p className="text-sm font-medium">{isError ? "Failed to load project" : "Project not found."}</p>
        </div>
      </div>
    );
  }

  const statusBadge = STATUS_BADGE[project.status] ?? "badge-neutral";

  return (
    <div className="space-y-6">
      <Link href="/projects" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ArrowLeft className="w-4 h-4" />
        {t("Back to Projects")}
      </Link>

      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span className="text-xs font-mono font-semibold text-muted-foreground bg-muted px-2.5 py-1 rounded-lg">{project.project_code}</span>
            <span className={`badge ${statusBadge}`}>{project.status}</span>
          </div>
          <h1 className="text-2xl font-bold text-foreground leading-tight">{project.project_name}</h1>
        </div>
      </div>

      {project.status === "Delayed" && (
        <div className="rounded-xl border border-red-200 bg-red-50 dark:border-red-900/30 dark:bg-red-900/10 px-5 py-4 flex items-start gap-3">
          <span className="text-red-500 text-lg leading-none mt-0.5">⚠</span>
          <div>
            <p className="text-sm font-semibold text-red-700 dark:text-red-400">Project is behind schedule</p>
            <p className="text-xs text-red-600/70 dark:text-red-400/70 mt-0.5">This project has been flagged as delayed. Review site reports and procurement records for bottlenecks.</p>
          </div>
        </div>
      )}

      <Tabs value={tab} onValueChange={setTab} className="space-y-4">
        <TabsList className="flex-wrap h-auto">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="health">Health Score</TabsTrigger>
          <TabsTrigger value="meetings">Meetings</TabsTrigger>
          <TabsTrigger value="site-reports">Site Reports</TabsTrigger>
          <TabsTrigger value="contracts">Contracts</TabsTrigger>
          <TabsTrigger value="documents">Documents</TabsTrigger>
          <TabsTrigger value="suppliers">Suppliers</TabsTrigger>
          <TabsTrigger value="risks">Risks</TabsTrigger>
          <TabsTrigger value="memory">Memory</TabsTrigger>
          <TabsTrigger value="ai-summary">AI Summary</TabsTrigger>
          <TabsTrigger value="ask-hermes" className="gap-1"><Sparkles className="w-3.5 h-3.5" />Ask Hermes</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="panel">
              <div className="panel-header"><span className="panel-title">{t("Project Details")}</span></div>
              <div className="panel-body space-y-0 divide-y divide-border">
                <DetailRow icon={Hash} label={t("Code")} value={project.project_code} />
                <DetailRow icon={Tag} label={t("Project Type")} value={project.project_type} />
                <DetailRow icon={Building2} label={t("Client")} value={project.client_name} />
                <DetailRow icon={MapPin} label={t("City")} value={project.city} />
              </div>
            </div>
            <div className="panel">
              <div className="panel-header"><span className="panel-title">Timeline & Financials</span></div>
              <div className="panel-body space-y-0 divide-y divide-border">
                <DetailRow icon={Calendar} label={t("Start Date")} value={project.start_date} />
                <DetailRow icon={Calendar} label={t("Planned Finish")} value={project.planned_finish} />
                {project.actual_finish && <DetailRow icon={Calendar} label={t("Actual Finish")} value={project.actual_finish} />}
                <DetailRow icon={DollarSign} label={t("Budget")} value={formatBudget(project.budget)} />
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="health"><ErrorBoundary><HealthScorePanel projectId={id} /></ErrorBoundary></TabsContent>
        <TabsContent value="meetings"><ErrorBoundary><MeetingsTab projectId={id} /></ErrorBoundary></TabsContent>
        <TabsContent value="site-reports"><ErrorBoundary><SiteReportsTab projectId={id} /></ErrorBoundary></TabsContent>
        <TabsContent value="contracts"><ErrorBoundary><ContractsTab projectCode={project.project_code} /></ErrorBoundary></TabsContent>
        <TabsContent value="documents"><ErrorBoundary><DocumentsTab projectId={id} /></ErrorBoundary></TabsContent>
        <TabsContent value="suppliers"><ErrorBoundary><SuppliersTab projectId={id} /></ErrorBoundary></TabsContent>
        <TabsContent value="risks"><ErrorBoundary><RisksTab projectId={id} /></ErrorBoundary></TabsContent>
        <TabsContent value="memory"><ErrorBoundary><MemoryCenter projectCodeFilter={project.project_code} /></ErrorBoundary></TabsContent>
        <TabsContent value="ai-summary"><ErrorBoundary><AiSummaryTab projectId={id} /></ErrorBoundary></TabsContent>
        <TabsContent value="ask-hermes">
          <ErrorBoundary>
            <div className="rounded-xl border border-border overflow-hidden">
              <CopilotPage compact projectId={id} projectLabel={`${project.project_code} — ${project.project_name}`} />
            </div>
          </ErrorBoundary>
        </TabsContent>
      </Tabs>
    </div>
  );
}
