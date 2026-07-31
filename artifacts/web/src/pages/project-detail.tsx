import { useEffect, useMemo, useState } from "react";
import {
  useGetProject, useGetProjectHealth, useListProjectMeetings, useListProjectDecisions,
  useListProjectNcrs, useListProjectSafetyEvents, useListPurchaseOrders, useListSuppliers,
} from "@workspace/api-client-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BackButton } from "@/components/back-button";
import { useParams, useSearch, Link } from "wouter";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import {
  Calendar, DollarSign, Hash, Tag, AlertOctagon,
  HeartPulse, ClipboardList, CalendarDays, FileSignature, Folder, Truck, ShieldAlert,
  Sparkles, ChevronRight, ExternalLink, AlertTriangle, Brain, HelpCircle,
} from "lucide-react";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import CopilotPage from "@/pages/copilot";
import MemoryCenter from "@/pages/ai-center/MemoryCenter";
import { bucketFor } from "@/pages/ai-center/memoryTaxonomy";
import { getMemory, listDocuments } from "@/lib/aiCenterClient";
import { useExecutive } from "@/lib/useExecutive";
import { getToken } from "@/lib/auth";
import { useRegisterCurrentEntity } from "@/context/CurrentEntityContext";
import { CurrentlyAnalyzing } from "@/components/CurrentlyAnalyzing";
import { AIActionPanel } from "@/components/AIActionPanel";
import { StatTile } from "@/components/stat-tile";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { WorkspaceQuickLink } from "@/components/WorkspaceQuickLink";
import { InsightPanel } from "@/components/InsightPanel";
import { FilterChip } from "@/components/filter-chip";

// ── AMAD v2 — Project Detail (operational command center) ──────────────────
// The page a PM spends most of the day on for one project. Two changes
// from the previous version: (1) a persistent hero row (health, schedule
// progress, last activity, client + primary quick actions) now sits above
// the tabs, visible no matter which tab is open — previously health/risk
// context only existed inside the Overview tab; (2) the Overview tab leads
// with "Needs Attention" (the same InsightPanel "brief" pattern used
// across Dashboard/Operations/Executive Suite) instead of three redundant
// health buttons, followed by real Recent Activity and Open Issues
// previews. Every field still comes from the exact hooks + queryKeys the
// sibling tabs already used — no new endpoints, no second health score,
// no fabricated RFI/approval data (neither exists as a project-scoped
// entity yet; see the report for exactly what's honestly omitted instead).

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

const LEVEL_BADGE: Record<string, string> = {
  Excellent: "badge-success", Good: "badge-info", "At Risk": "badge-warning", Critical: "badge-danger",
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

function formatShortDate(iso?: string): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

// Honest, computed proxy for "Progress" — the Project schema has no work-
// completion percentage, only start_date/planned_finish. This is time
// elapsed against the planned schedule, not construction progress, and is
// labeled as such everywhere it's shown rather than implied to be more
// than it is.
function scheduleElapsedPct(start?: string, finish?: string): number | null {
  if (!start || !finish) return null;
  const startMs = new Date(start).getTime(), finishMs = new Date(finish).getTime();
  if (!(finishMs > startMs) || Number.isNaN(startMs)) return null;
  const pct = ((Date.now() - startMs) / (finishMs - startMs)) * 100;
  return Math.max(0, Math.min(100, Math.round(pct)));
}

// ── Shared project-event builder ────────────────────────────────────────
// Used by both the Overview tab's "Recent Activity" preview and the full
// Timeline tab — one place that merges meetings, site reports, documents,
// open risks, decisions, and memories into a dated feed, instead of two
// independent copies of the same merge/sort logic.
type TimelineEventType = "meeting" | "site_report" | "contract" | "document" | "risk" | "memory" | "decision";
interface TimelineEvent { date: string; type: TimelineEventType; title: string; href?: string }

const TIMELINE_TYPE_META: Record<TimelineEventType, { label: string; icon: React.ElementType; tone: string }> = {
  meeting:     { label: "Meeting Created",   icon: CalendarDays,   tone: "text-sky-600 dark:text-sky-400" },
  site_report: { label: "Site Report Added", icon: ClipboardList,  tone: "text-amber-600 dark:text-amber-400" },
  contract:    { label: "Contract Uploaded", icon: FileSignature,  tone: "text-rose-600 dark:text-rose-400" },
  document:    { label: "Document Added",    icon: Folder,         tone: "text-slate-600 dark:text-slate-400" },
  risk:        { label: "Risk Increased",    icon: AlertTriangle,  tone: "text-red-600 dark:text-red-400" },
  memory:      { label: "Memory Saved",      icon: Brain,          tone: "text-violet-600 dark:text-violet-400" },
  decision:    { label: "Decision Recorded", icon: Hash,           tone: "text-emerald-600 dark:text-emerald-400" },
};

function buildProjectEvents(params: {
  projectId: number;
  projectCode: string;
  meetings?: { id: number; project_id: number; meeting_date: string; title: string }[];
  siteReportCards?: { report_id: number; report_date: string }[];
  documents?: { id: number; title: string; doc_date: string; doc_type?: string | null }[];
  ncrs?: { status: string; issue_date: string; ncr_type: string }[];
  safety?: { severity: string; event_date: string; description: string }[];
  decisions?: { decision_date: string; decision_text: string }[];
  memories?: { project_code: string | null; created_at: string; title: string }[];
}): TimelineEvent[] {
  const { projectId, projectCode, meetings, siteReportCards, documents, ncrs, safety, decisions, memories } = params;
  return [
    ...(meetings ?? []).map((m): TimelineEvent => ({ date: m.meeting_date, type: "meeting", title: m.title, href: `/meetings/${projectId}/${m.id}` })),
    ...(siteReportCards ?? []).map((c): TimelineEvent => ({ date: c.report_date, type: "site_report", title: `Site Report — ${c.report_date}`, href: `/projects/${projectId}/site-reports/${c.report_id}` })),
    ...(documents ?? []).map((d): TimelineEvent => ({ date: d.doc_date, type: d.doc_type?.toLowerCase().includes("contract") ? "contract" : "document", title: d.title })),
    ...(ncrs ?? []).filter((n) => n.status !== "Closed").map((n): TimelineEvent => ({ date: n.issue_date, type: "risk", title: `NCR — ${n.ncr_type}` })),
    ...(safety ?? []).filter((s) => s.severity === "high" || s.severity === "critical").map((s): TimelineEvent => ({ date: s.event_date, type: "risk", title: `Safety — ${s.description}` })),
    ...(decisions ?? []).map((d): TimelineEvent => ({ date: d.decision_date, type: "decision", title: d.decision_text })),
    ...(memories ?? []).filter((m) => m.project_code === projectCode).map((m): TimelineEvent => ({ date: m.created_at.slice(0, 10), type: "memory", title: m.title })),
  ].sort((a, b) => b.date.localeCompare(a.date));
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
          <Link key={m.id} href={`/meetings/${m.project_id}/${m.id}`} className="panel flex items-center justify-between gap-3 p-3 hover:border-primary/30 transition-colors group">
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
        <Link key={c.report_id} href={`/projects/${projectId}/site-reports/${c.report_id}`} className="panel flex items-center justify-between gap-2 p-3.5 hover:border-primary/30 transition-colors group">
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
        <div key={c.id} className="panel panel-body space-y-1.5">
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

// ── Procurement (purchase orders) tab — labeled to match the app's own
// "Procurement" naming (previously "Suppliers"); content unchanged. ──────
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

// ── Safety & NCRs tab (previously "Risks"; content unchanged) ────────────
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

// ── Timeline tab ────────────────────────────────────────────────────────
function TimelineTab({ project, projectId }: { project: { project_code: string }; projectId: number }) {
  const [typeFilter, setTypeFilter] = useState<TimelineEventType | "all">("all");
  const { data: meetings, isLoading: meetingsLoading } = useListProjectMeetings(projectId, { limit: 20 }, { query: { queryKey: ["pw-meetings", projectId] } });
  const { data: decisions } = useListProjectDecisions(projectId, { limit: 20 }, { query: { queryKey: ["pw-decisions-tl", projectId] } });
  const { data: ncrs } = useListProjectNcrs(projectId, { limit: 20 }, { query: { queryKey: ["pw-ncrs", projectId] } });
  const { data: safety } = useListProjectSafetyEvents(projectId, { limit: 20 }, { query: { queryKey: ["pw-safety", projectId] } });
  const { data: siteReportCards, isLoading: srLoading } = useQuery({
    queryKey: ["pw-site-reports", projectId],
    queryFn: async () => {
      const token = getToken();
      const resp = await fetch(`/api/v1/projects/${projectId}/site-reports/cards?limit=20`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      return resp.ok ? resp.json() : [];
    },
  });
  const { data: documents } = useQuery({ queryKey: ["pw-documents", projectId], queryFn: () => listDocuments({ scope: "project", projectId, limit: 30 }) });
  const { data: memory } = useQuery({ queryKey: ["ai-center-memory"], queryFn: getMemory });

  const isLoading = meetingsLoading || srLoading;

  const events = buildProjectEvents({
    projectId, projectCode: project.project_code,
    meetings, siteReportCards, documents, ncrs, safety, decisions,
    memories: memory?.structured_memories,
  });

  const filtered = typeFilter === "all" ? events : events.filter((e) => e.type === typeFilter);
  const presentTypes = Array.from(new Set(events.map((e) => e.type)));

  if (isLoading) return <div className="space-y-2">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-14 w-full rounded-lg" />)}</div>;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-1.5">
        <FilterChip active={typeFilter === "all"} onClick={() => setTypeFilter("all")}>
          All ({events.length})
        </FilterChip>
        {presentTypes.map((type) => {
          const meta = TIMELINE_TYPE_META[type];
          const count = events.filter((e) => e.type === type).length;
          return (
            <FilterChip
              key={type}
              active={typeFilter === type}
              onClick={() => setTypeFilter(typeFilter === type ? "all" : type)}
              icon={meta.icon}
            >
              {meta.label} ({count})
            </FilterChip>
          );
        })}
      </div>

      {!filtered.length ? (
        <EmptyState icon={CalendarDays} title="No timeline events yet" description="Meetings, site reports, documents, risks, decisions, and memories for this project will appear here as they happen." />
      ) : (
        <div className="relative ps-6 border-s-2 border-border space-y-3">
          {filtered.map((e, i) => {
            const meta = TIMELINE_TYPE_META[e.type];
            const Icon = meta.icon;
            const content = (
              <div className="flex items-start gap-3 rounded-lg border border-border/60 bg-card px-3 py-2.5 hover:border-primary/30 transition-colors">
                <Icon className={`w-4 h-4 mt-0.5 shrink-0 ${meta.tone}`} />
                <div className="min-w-0 flex-1">
                  <p className="text-sm text-foreground truncate">{e.title}</p>
                  <p className="text-xs text-muted-foreground">{meta.label} &middot; {e.date}</p>
                </div>
              </div>
            );
            return (
              <div key={`${e.type}-${i}-${e.date}`} className="relative">
                <div className="absolute -start-[31px] top-3 w-2.5 h-2.5 rounded-full bg-primary" />
                {e.href ? <Link href={e.href}>{content}</Link> : content}
              </div>
            );
          })}
        </div>
      )}
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

// ── Overview tab ────────────────────────────────────────────────────────
// Leads with "Needs Attention" (real signals only — delayed status,
// critical/at-risk health, open NCRs, high-severity safety events, late
// purchase orders), then AI assistance, then real Recent Activity and
// Open Issues previews (both reuse data the sibling tabs already fetch),
// then the remaining-tabs quick-nav grid, then supporting project detail.
// Health/status context that's now in the persistent hero above the tabs
// (health score, schedule progress) isn't repeated here.
function OverviewTab({ project, projectId, health, onNavigate }: {
  project: {
    project_code: string; project_name: string; project_type?: string | null;
    client_name?: string | null; city?: string | null; start_date?: string | null;
    planned_finish?: string | null; budget?: number | null; status: string;
  };
  projectId: number;
  health?: { level: string; score: number; reasons: string[] };
  onNavigate: (tab: string) => void;
}) {
  const { data: meetings } = useListProjectMeetings(projectId, { limit: 10 }, { query: { queryKey: ["pw-meetings", projectId] } });
  const { data: ncrs } = useListProjectNcrs(projectId, { limit: 10 }, { query: { queryKey: ["pw-ncrs", projectId] } });
  const { data: safety } = useListProjectSafetyEvents(projectId, { limit: 10 }, { query: { queryKey: ["pw-safety", projectId] } });
  const { data: siteReportCards } = useQuery({
    queryKey: ["pw-site-reports", projectId],
    queryFn: async () => {
      const token = getToken();
      const resp = await fetch(`/api/v1/projects/${projectId}/site-reports/cards?limit=8`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      return resp.ok ? resp.json() : [];
    },
  });
  const { data: documents } = useQuery({ queryKey: ["pw-documents", projectId], queryFn: () => listDocuments({ scope: "project", projectId, limit: 30 }) });
  const { data: orders } = useListPurchaseOrders({ project_id: projectId, limit: 20 }, { query: { queryKey: ["pw-pos", projectId] } });
  const { data: memory } = useQuery({ queryKey: ["ai-center-memory"], queryFn: getMemory });
  const { data: exec } = useExecutive();

  const openNcrs = (ncrs ?? []).filter((n) => n.status !== "Closed");
  const highSeveritySafety = (safety ?? []).filter((s) => s.severity === "high" || s.severity === "critical");
  const lateOrders = (orders ?? []).filter((o) => o.is_late);
  const contracts = (memory?.structured_memories ?? []).filter((m) => bucketFor(m.source, m.category) === "contract" && m.project_code === project.project_code);
  const projectMemories = (memory?.structured_memories ?? []).filter((m) => m.project_code === project.project_code)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

  const brief = [...(exec?.top_priorities ?? []), ...(exec?.attention_required ?? []), ...(exec?.best_projects ?? [])]
    .find((b) => b.project_id === projectId);

  // Needs Attention — every item traces to a real, already-fetched
  // signal. Open RFIs and pending approvals are not shown: neither exists
  // as a project-scoped entity in the current schema (RFIs are a
  // portfolio-wide keyword view over decisions/documents; there is no
  // approvals/decision-queue table at all) — named honestly below instead
  // of being faked as a zero count.
  type AttentionItem = { id: string; label: string; tab: string; icon: React.ElementType };
  const attentionItems: AttentionItem[] = [];
  if (project.status === "Delayed") attentionItems.push({ id: "delayed", label: "Project is behind schedule", tab: "site-reports", icon: AlertTriangle });
  if (health && (health.level === "Critical" || health.level === "At Risk")) {
    attentionItems.push({ id: "health", label: `Health is ${health.level} (${health.score}/100)`, tab: "health", icon: HeartPulse });
  }
  if (openNcrs.length > 0) attentionItems.push({ id: "ncrs", label: `${openNcrs.length} open NCR${openNcrs.length === 1 ? "" : "s"}`, tab: "risks", icon: ShieldAlert });
  if (highSeveritySafety.length > 0) attentionItems.push({ id: "safety", label: `${highSeveritySafety.length} high-severity safety event${highSeveritySafety.length === 1 ? "" : "s"}`, tab: "risks", icon: AlertOctagon });
  if (lateOrders.length > 0) attentionItems.push({ id: "pos", label: `${lateOrders.length} late purchase order${lateOrders.length === 1 ? "" : "s"}`, tab: "suppliers", icon: Truck });

  const recentEvents = buildProjectEvents({
    projectId, projectCode: project.project_code,
    meetings, siteReportCards, documents, ncrs, safety, memories: memory?.structured_memories,
  }).slice(0, 5);

  const openIssues = [
    ...openNcrs.map((n) => ({ id: `ncr-${n.id}`, label: n.ncr_type, detail: n.description, date: n.issue_date, tone: "badge-warning" })),
    ...highSeveritySafety.map((s) => ({ id: `safety-${s.id}`, label: s.severity, detail: s.description, date: s.event_date, tone: "badge-danger" })),
  ].sort((a, b) => b.date.localeCompare(a.date)).slice(0, 4);

  return (
    <div className="space-y-5">
      {/* Needs Attention */}
      <InsightPanel
        icon={AlertTriangle}
        title="Needs Attention"
        variant="brief"
        badge={attentionItems.length === 0 ? <span className="badge badge-success text-[9px]">All Clear</span> : <span className="badge badge-warning text-[9px]">{attentionItems.length}</span>}
      >
        {attentionItems.length === 0 ? (
          <p className="text-[13px] text-muted-foreground leading-normal">No delayed status, critical health, open NCRs, high-severity safety events, or late orders — this project is on track.</p>
        ) : (
          <div className="space-y-1">
            {attentionItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onNavigate(item.tab)}
                  className="w-full flex items-center gap-2.5 px-2 py-1.5 rounded-md text-sm text-foreground hover:bg-muted/50 transition-colors group text-start"
                >
                  <Icon className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                  <span className="flex-1">{item.label}</span>
                  <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/40 group-hover:text-primary transition-colors" />
                </button>
              );
            })}
          </div>
        )}
        <p className="text-[10.5px] text-muted-foreground/70 mt-2 pt-2 border-t border-border/50">
          RFI and approval tracking aren't project-scoped yet — see the portfolio-wide <Link href="/rfis" className="text-primary hover:underline">RFIs</Link> page.
        </p>
      </InsightPanel>

      {/* AI assistance — reuses the existing brief + action panel, nothing new */}
      <div className="panel panel-body">
        <div className="flex items-center gap-2 mb-2"><Sparkles className="w-4 h-4 text-primary" /><span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">AI Executive Summary</span></div>
        <p className="text-sm text-foreground leading-relaxed">
          {brief?.primary_reason ?? (health?.reasons?.[0] ?? "No issues detected — project is on track.")}
        </p>
      </div>
      <AIActionPanel entityKind="project" projectId={projectId} projectCode={project.project_code} projectName={project.project_name} />

      {/* Recent Activity + Open Issues */}
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="panel h-full flex flex-col">
          <div className="px-3.5 py-2.5 border-b flex items-center justify-between">
            <span className="font-semibold text-[13px] text-foreground">Recent Activity</span>
            <button onClick={() => onNavigate("timeline")} className="text-[11px] text-primary hover:underline shrink-0">Full timeline →</button>
          </div>
          <div className="p-1.5 flex-1">
            {recentEvents.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2 px-1.5">No recorded activity for this project yet.</p>
            ) : (
              <div className="space-y-px">
                {recentEvents.map((e, i) => {
                  const meta = TIMELINE_TYPE_META[e.type];
                  const Icon = meta.icon;
                  return (
                    <div key={`${e.type}-${i}`} className="flex items-center gap-2.5 px-1.5 py-1.5">
                      <Icon className={`w-3.5 h-3.5 shrink-0 ${meta.tone}`} />
                      <span className="flex-1 min-w-0 text-[12px] text-foreground truncate">{e.title}</span>
                      <span className="text-[10px] text-muted-foreground shrink-0">{formatShortDate(e.date)}</span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        <div className="panel h-full flex flex-col">
          <div className="px-3.5 py-2.5 border-b flex items-center justify-between">
            <span className="font-semibold text-[13px] text-foreground">Open Issues</span>
            <button onClick={() => onNavigate("risks")} className="text-[11px] text-primary hover:underline shrink-0">View all →</button>
          </div>
          <div className="p-1.5 flex-1">
            {openIssues.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2 px-1.5">No open NCRs or high-severity safety events.</p>
            ) : (
              <div className="space-y-1">
                {openIssues.map((issue) => (
                  <div key={issue.id} className="rounded-md px-1.5 py-1.5 hover:bg-muted/50 transition-colors">
                    <div className="flex items-center gap-1.5">
                      <span className={`badge ${issue.tone} text-[9px]`}>{issue.label}</span>
                      <span className="text-[10px] text-muted-foreground ms-auto">{formatShortDate(issue.date)}</span>
                    </div>
                    <p className="text-[11px] text-foreground truncate mt-0.5">{issue.detail}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Operational Modules — everything not already one click away from
          the hero above (Documents/Site Reports/Procurement/Safety &
          NCRs/RFIs). Reuses StatTile's existing onClick tab-switch mode —
          the same one-click-nav mechanism this page already established. */}
      <div>
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">More for This Project</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <StatTile icon={HeartPulse} label="Health Score" value={health?.score ?? "—"} onClick={() => onNavigate("health")} />
          <StatTile icon={CalendarDays} label="Meetings" value={meetings?.length ?? 0} onClick={() => onNavigate("meetings")} />
          <StatTile icon={FileSignature} label="Contracts" value={contracts.length} onClick={() => onNavigate("contracts")} />
          <StatTile icon={Brain} label="Memory" value={projectMemories.length} onClick={() => onNavigate("memory")} />
          <StatTile icon={Sparkles} label="Ask Hermes" description="Chat about this project" onClick={() => onNavigate("ask-hermes")} />
        </div>
      </div>

      {/* Memory Timeline snippet */}
      {projectMemories.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Memory Timeline</p>
            <button onClick={() => onNavigate("memory")} className="text-xs text-primary hover:underline">View all →</button>
          </div>
          <div className="space-y-1.5">
            {projectMemories.slice(0, 4).map((m) => (
              <div key={m.id} className="flex items-center gap-3 rounded-lg border border-border/60 bg-card px-3 py-2">
                <span className="text-xs text-muted-foreground shrink-0 w-20 tabular-nums">{new Date(m.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</span>
                <span className="text-sm text-foreground truncate flex-1">{m.title}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Supporting project detail — code/client/city already live in the
          hero above, so this only carries what isn't shown there yet. */}
      <div className="panel">
        <div className="panel-header"><span className="panel-title">Project Details</span></div>
        <div className="panel-body space-y-0 divide-y divide-border">
          <DetailRow icon={Tag} label="Project Type" value={project.project_type} />
          <DetailRow icon={Calendar} label="Start Date" value={project.start_date} />
          <DetailRow icon={Calendar} label="Planned Finish" value={project.planned_finish} />
          <DetailRow icon={DollarSign} label="Budget" value={formatBudget(project.budget)} />
        </div>
      </div>
    </div>
  );
}

export default function ProjectDetail() {
  const { t } = useTranslation();
  const params = useParams();
  const search = useSearch();
  const id = parseInt(params.id || "0", 10);
  const { data: project, isLoading, isError } = useGetProject(id, { query: { enabled: !!id, queryKey: ["project", id] } });

  useRegisterCurrentEntity(
    project ? { kind: "project", code: project.project_code, label: project.project_name, projectId: id } : null,
  );

  const initialTab = new URLSearchParams(search).get("tab") ?? "overview";
  const [tab, setTab] = useState(initialTab);
  useEffect(() => { setTab(new URLSearchParams(search).get("tab") ?? "overview"); }, [search]);

  // Hero data — health (shared with the Health Score tab's exact queryKey,
  // never a second score) + the real dates behind "Schedule" and "Last
  // Activity". Lightweight, already-established hooks; React Query dedupes
  // against the Overview/Timeline tabs' identical queryKeys once visited.
  const { data: health } = useGetProjectHealth(id, { query: { enabled: !!id, queryKey: ["project-health", id] } });
  const { data: heroMeetings } = useListProjectMeetings(id, { limit: 10 }, { query: { queryKey: ["pw-meetings", id], enabled: !!id } });
  const { data: heroSiteReports } = useQuery({
    queryKey: ["pw-site-reports", id],
    queryFn: async () => {
      const token = getToken();
      const resp = await fetch(`/api/v1/projects/${id}/site-reports/cards?limit=8`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
      return resp.ok ? resp.json() : [];
    },
    enabled: !!id,
  });
  const { data: heroDocuments } = useQuery({
    queryKey: ["pw-documents", id],
    queryFn: () => listDocuments({ scope: "project", projectId: id, limit: 30 }),
    enabled: !!id,
  });

  const lastActivityDate = useMemo(() => {
    const dates = [
      ...(heroMeetings ?? []).map((m) => m.meeting_date),
      ...(heroSiteReports ?? []).map((c: { report_date: string }) => c.report_date),
      ...(heroDocuments ?? []).map((d) => d.doc_date),
    ].filter(Boolean).sort();
    return dates[dates.length - 1];
  }, [heroMeetings, heroSiteReports, heroDocuments]);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-5 w-32" />
        <div className="space-y-2">
          <Skeleton className="h-9 w-2/3" />
          <Skeleton className="h-5 w-32" />
        </div>
        <Skeleton className="h-16 w-full rounded-xl" />
        <Skeleton className="h-10 w-full rounded-lg" />
        <Skeleton className="h-80 rounded-xl" />
      </div>
    );
  }

  if (isError || !project) {
    return (
      <div className="space-y-4">
        <BackButton to="/projects" label="Back to Projects" />
        <div className="panel panel-body flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground">
          <AlertOctagon className="w-8 h-8 text-destructive opacity-60" />
          <p className="text-sm font-medium">{isError ? "Failed to load project" : "Project not found."}</p>
        </div>
      </div>
    );
  }

  const statusBadge = STATUS_BADGE[project.status] ?? "badge-neutral";
  const healthCfg = health ? (LEVEL_CONFIG[health.level] ?? LEVEL_CONFIG["Good"]) : null;
  const scheduleElapsed = scheduleElapsedPct(project.start_date, project.planned_finish);

  return (
    <WorkspaceLayout
        title={project.project_name}
        subtitle={[project.project_type, project.client_name, project.city].filter(Boolean).join(" · ") || "Project workspace"}
        backLabel="Back to Projects"
        backHref="/projects"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Operations", href: "/operations" },
          { label: "Projects", href: "/projects" },
          { label: project.project_name },
        ]}
        badge={
          <>
            <span className="text-xs font-mono font-semibold text-muted-foreground bg-muted px-2.5 py-1 rounded-lg">{project.project_code}</span>
            <span className={`badge ${statusBadge}`}>{project.status}</span>
          </>
        }
      >

      <CurrentlyAnalyzing />

      {/* Project Hero — persistent across every tab: health, schedule
          progress, last activity, client, and the fastest paths into
          Documents/Site Reports/Procurement/Safety & NCRs/RFIs. */}
      <div className="panel panel-body">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Health</span>
            {health ? (
              <>
                <span className={`badge ${LEVEL_BADGE[health.level] ?? "badge-neutral"} text-[10px]`}>{health.level}</span>
                <span className="text-xs font-semibold tabular-nums" style={{ color: healthCfg?.color }}>{health.score}/100</span>
              </>
            ) : <span className="text-xs text-muted-foreground">—</span>}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Schedule</span>
            <span className="text-xs font-semibold text-foreground tabular-nums">{scheduleElapsed != null ? `${scheduleElapsed}% elapsed` : "—"}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Last Activity</span>
            <span className="text-xs font-semibold text-foreground">{lastActivityDate ? formatShortDate(lastActivityDate) : "No activity recorded"}</span>
          </div>
          {project.client_name && (
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">Client</span>
              <span className="text-xs font-semibold text-foreground">{project.client_name}</span>
            </div>
          )}
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 mt-3 pt-3 border-t border-border/50">
          <WorkspaceQuickLink icon={Folder} title="Documents" href={`/projects/${id}?tab=documents`} variant="card" />
          <WorkspaceQuickLink icon={ClipboardList} title="Site Reports" href={`/projects/${id}?tab=site-reports`} variant="card" />
          <WorkspaceQuickLink icon={Truck} title="Procurement" href={`/projects/${id}?tab=suppliers`} variant="card" />
          <WorkspaceQuickLink icon={ShieldAlert} title="Safety & NCRs" href={`/projects/${id}?tab=risks`} variant="card" />
          <WorkspaceQuickLink icon={HelpCircle} title="RFIs" meta="Portfolio-wide" href="/rfis" variant="card" />
        </div>
      </div>

      {project.status === "Delayed" && (
        <div className="rounded-xl border border-red-200 bg-red-50 dark:border-red-900/30 dark:bg-red-900/10 px-5 py-3 flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
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
          <TabsTrigger value="suppliers">Procurement</TabsTrigger>
          <TabsTrigger value="risks">Safety &amp; NCRs</TabsTrigger>
          <TabsTrigger value="timeline">Timeline</TabsTrigger>
          <TabsTrigger value="memory">Memory</TabsTrigger>
          <TabsTrigger value="ai-summary">AI Summary</TabsTrigger>
          <TabsTrigger value="ask-hermes" className="gap-1"><Sparkles className="w-3.5 h-3.5" />Ask Hermes</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <ErrorBoundary><OverviewTab project={project} projectId={id} health={health} onNavigate={setTab} /></ErrorBoundary>
        </TabsContent>

        <TabsContent value="health"><ErrorBoundary><HealthScorePanel projectId={id} /></ErrorBoundary></TabsContent>
        <TabsContent value="meetings"><ErrorBoundary><MeetingsTab projectId={id} /></ErrorBoundary></TabsContent>
        <TabsContent value="site-reports"><ErrorBoundary><SiteReportsTab projectId={id} /></ErrorBoundary></TabsContent>
        <TabsContent value="contracts"><ErrorBoundary><ContractsTab projectCode={project.project_code} /></ErrorBoundary></TabsContent>
        <TabsContent value="documents"><ErrorBoundary><DocumentsTab projectId={id} /></ErrorBoundary></TabsContent>
        <TabsContent value="suppliers"><ErrorBoundary><SuppliersTab projectId={id} /></ErrorBoundary></TabsContent>
        <TabsContent value="risks"><ErrorBoundary><RisksTab projectId={id} /></ErrorBoundary></TabsContent>
        <TabsContent value="timeline"><ErrorBoundary><TimelineTab project={project} projectId={id} /></ErrorBoundary></TabsContent>
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
    </WorkspaceLayout>
  );
}
