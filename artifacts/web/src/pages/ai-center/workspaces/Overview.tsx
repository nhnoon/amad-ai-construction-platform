import { useEffect, useMemo, useRef, useState } from "react";
import { useListProjects, useListSuppliers } from "@workspace/api-client-react";
import { ResponsiveContainer, AreaChart, Area } from "recharts";
import {
  Sparkles, Bot, ArrowRight, AlertTriangle, Wallet, Gavel, Target,
  Bell, Building2, Network, Gauge, Truck, Boxes, BookOpen, Crown, Mail, TrendingUp, TrendingDown,
  Clock3, MapPin, Brain, Radar, ShieldAlert as ShieldIcon,
} from "lucide-react";
import { Link } from "wouter";
import { useExecutive, usePortfolioTrend } from "@/lib/useExecutive";
import { useAlerts, useAlertsSummary } from "@/lib/useAlerts";
import { generateExecutiveDecisionCenter } from "@/lib/mockExecutiveDecisionCenter";
import { generateMaterialIntelligence } from "@/lib/mockMaterialIntelligence";
import { generateSupplierRisk } from "@/lib/mockSupplierRisk";
import { PageHero } from "@/components/PageHero";
import { KpiStat } from "@/components/KpiStat";
import { InsightPanel } from "@/components/InsightPanel";
import { WorkspaceQuickLink } from "@/components/WorkspaceQuickLink";
import { DemoDataBadge } from "@/components/DemoDataBadge";
import { SearchInput } from "@/components/search-input";
import { FilterSelect } from "@/components/filter-select";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { PageTabs } from "@/components/page-tabs";
import { RISK_COLOR } from "./executive-decision-center/shared";

// ── AMAD v2 — AI Center Overview ────────────────────────────────────────
// Layout is a deliberate recreation of the AMAD v2 reference composition:
// Hero -> Executive Brief + Mini Heat Map -> KPI strip -> Today's
// Attention / Recommendations / Attention Projects -> KPI Trends + Quick
// Access -> Recent Activity. Section proportions, row counts (max 5), and
// card internals (icon badge + value + description + delta) follow the
// reference as closely as the existing AMAD design system allows.
//
// Data honesty: sections built from real, already-fetched data (Hero
// scope, Projects Analyzed, Critical Risks, AI Data Coverage, Attention
// Projects' health scores, Emerging Risks, one KPI Trends sparkline)
// carry no label. Everything else on this page — the Executive Brief,
// Mini Heat Map, Pending Decisions, Executive Recommendations, delay-day
// figures, and five of the six KPI Trends sparklines — is local demo
// data, tagged "Demo Data" wherever it appears. Cross-module numbers call
// the existing, already-shipped pure generator functions from
// lib/mockExecutiveDecisionCenter.ts, lib/mockMaterialIntelligence.ts,
// and lib/mockSupplierRisk.ts directly (read-only — none of those
// modules' files change).

function formatSar(amount: number, withPrefix = true): string {
  const num = amount >= 1_000_000 ? `${(amount / 1_000_000).toFixed(1)}M` : amount >= 1_000 ? `${(amount / 1_000).toFixed(0)}K` : amount.toLocaleString();
  return withPrefix ? `SAR ${num}` : num;
}

function riskBand(score: number): "Low" | "Medium" | "High" | "Critical" {
  if (score >= 75) return "Critical";
  if (score >= 55) return "High";
  if (score >= 30) return "Medium";
  return "Low";
}

function hashInt(seed: string): number {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  return h || 1;
}

/** Small deterministic 8-point trend, anchored to `current` so the chart
 * always ends on the real headline number. Not a real time series — used
 * only for the demo-tagged KPI Trends sparklines. */
function seededTrend(seed: string, current: number, weeks = 8): { value: number }[] {
  let x = hashInt(seed);
  const rand = () => { x ^= x << 13; x ^= x >>> 17; x ^= x << 5; x >>>= 0; return x / 4294967295; };
  const points: number[] = [];
  let v = current * (0.75 + rand() * 0.35);
  for (let w = 0; w < weeks; w++) {
    v = Math.max(0, v + (rand() * 0.2 - 0.1) * Math.max(current, 4));
    points.push(v);
  }
  points[points.length - 1] = current;
  return points.map((p) => ({ value: Math.round(p * 10) / 10 }));
}

function syntheticDelayDays(projectId: number): number {
  return 15 + (hashInt(`delay-${projectId}`) % 115);
}

const LEVEL_TONE: Record<string, { text: string; dot: string }> = {
  Excellent: { text: "text-emerald-600 dark:text-emerald-400", dot: "bg-emerald-500" },
  Good: { text: "text-blue-600 dark:text-blue-400", dot: "bg-blue-500" },
  "At Risk": { text: "text-amber-600 dark:text-amber-400", dot: "bg-amber-500" },
  Critical: { text: "text-rose-600 dark:text-rose-400", dot: "bg-rose-500" },
};

const HEAT_DIMENSIONS: { key: "schedule" | "budget" | "safety" | "supplier" | "material"; label: string }[] = [
  { key: "schedule", label: "Schedule" },
  { key: "budget", label: "Budget" },
  { key: "safety", label: "Safety" },
  { key: "supplier", label: "Supplier" },
  { key: "material", label: "Material" },
];
const BANDS: ("Low" | "Medium" | "High" | "Critical")[] = ["Low", "Medium", "High", "Critical"];

const QUICK_ACCESS: { key: string; href: string; icon: typeof Network; title: string; accent: string }[] = [
  { key: "project-memory", href: "/ai-center/project-memory", icon: Network, title: "Project Memory", accent: "text-violet-600 dark:text-violet-400" },
  { key: "predictive-intelligence", href: "/ai-center/predictive-intelligence", icon: Gauge, title: "Predictive Intelligence", accent: "text-indigo-600 dark:text-indigo-400" },
  { key: "supplier-risk", href: "/ai-center/supplier-risk", icon: Truck, title: "Supplier Risk", accent: "text-sky-600 dark:text-sky-400" },
  { key: "material-intelligence", href: "/ai-center/material-intelligence", icon: Boxes, title: "Material Intelligence", accent: "text-emerald-600 dark:text-emerald-400" },
  { key: "cross-project-learning", href: "/ai-center/cross-project-learning", icon: BookOpen, title: "Cross-Project Learning", accent: "text-cyan-600 dark:text-cyan-400" },
  { key: "search", href: "/ai-center/search", icon: Sparkles, title: "Intelligent Search", accent: "text-purple-600 dark:text-purple-400" },
  { key: "email", href: "/ai-center/email", icon: Mail, title: "Email Intelligence", accent: "text-rose-600 dark:text-rose-400" },
  { key: "executive-decision-center", href: "/ai-center/executive-decision-center", icon: Crown, title: "Executive Decision Center", accent: "text-accent" },
];

type AttentionTab = "alerts" | "decisions" | "risks";

function MiniSparkline({ data, id, color }: { data: { value: number }[]; id: string; color: string }) {
  return (
    <div className="h-6 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id={`spark-${id}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={color} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area type="monotone" dataKey="value" stroke={color} strokeWidth={1.75} fill={`url(#spark-${id})`} isAnimationActive={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

function trendDeltaPct(points: { value: number }[]): { pct: number; up: boolean } | null {
  if (points.length < 2) return null;
  const first = points[0].value, last = points[points.length - 1].value;
  if (first === 0) return null;
  return { pct: Math.round(((last - first) / first) * 100), up: last >= first };
}

// A restrained abstract skyline — three gold-gradient towers with a soft
// glow, echoing LogoMark's three-pillar mark at a larger scale. No
// external image assets; purely decorative, sits inside the Executive
// Brief panel the way the reference's centerpiece illustration does.
function BriefIllustration() {
  return (
    <svg viewBox="0 0 160 140" className="w-full h-full max-h-[96px]" aria-hidden="true">
      <defs>
        <linearGradient id="brief-tower" x1="0" y1="1" x2="0" y2="0">
          <stop offset="0%" stopColor="hsl(var(--accent))" stopOpacity="0.15" />
          <stop offset="100%" stopColor="hsl(var(--accent))" stopOpacity="0.85" />
        </linearGradient>
        <filter id="brief-glow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="6" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <circle cx="80" cy="70" r="46" fill="hsl(var(--accent))" opacity="0.08" />
      <g filter="url(#brief-glow)">
        <rect x="20" y="70" width="26" height="55" rx="2" fill="url(#brief-tower)" />
        <rect x="67" y="30" width="26" height="95" rx="2" fill="url(#brief-tower)" />
        <rect x="114" y="55" width="26" height="70" rx="2" fill="url(#brief-tower)" />
      </g>
      <rect x="14" y="125" width="132" height="3" rx="1.5" fill="hsl(var(--accent))" opacity="0.4" />
    </svg>
  );
}

function AttentionRow({
  icon: Icon, iconTone, title, subtitle, badge, badgeTone, meta,
}: {
  icon: typeof AlertTriangle; iconTone: string; title: string; subtitle?: string;
  badge?: string; badgeTone?: string; meta?: string;
}) {
  return (
    <div className="flex items-center gap-1.5 px-1.5 py-1 rounded-md border border-border/60 hover:border-primary/30 transition-colors">
      <div className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${iconTone}`}>
        <Icon className="w-2.5 h-2.5" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-[11px] font-semibold text-foreground truncate leading-tight">{title}</p>
        {subtitle && <p className="text-[9.5px] text-muted-foreground truncate leading-tight mt-px">{subtitle}</p>}
      </div>
      <div className="text-end shrink-0 space-y-0.5">
        {badge && <span className={`badge text-[9px] ${badgeTone}`}>{badge}</span>}
        {meta && <p className="text-[9px] text-muted-foreground">{meta}</p>}
      </div>
    </div>
  );
}

// A denser row, used only by Today's Attention and Executive
// Recommendations — kept separate from AttentionRow (not a shared/renamed
// version of it) because AttentionRow is also used by the Executive
// Brief's "Top Signals" list, which must stay pixel-identical. Same
// props, tighter row height/padding only — no font-size changes.
function CompactRow({
  icon: Icon, iconTone, title, subtitle, badge, badgeTone, meta,
}: {
  icon: typeof AlertTriangle; iconTone: string; title: string; subtitle?: string;
  badge?: string; badgeTone?: string; meta?: string;
}) {
  return (
    <div className="flex items-center gap-1.5 px-1.5 py-0 rounded-md border border-border/60 hover:border-primary/30 transition-colors">
      <div className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${iconTone}`}>
        <Icon className="w-2.5 h-2.5" />
      </div>
      <div className="flex-1 min-w-0 py-px">
        <p className="text-[11px] font-semibold text-foreground truncate leading-[1.15]">{title}</p>
        {subtitle && <p className="text-[9.5px] text-muted-foreground truncate leading-[1.15]">{subtitle}</p>}
      </div>
      <div className="text-end shrink-0">
        {badge && <span className={`badge text-[9px] ${badgeTone}`}>{badge}</span>}
        {meta && <p className="text-[9px] text-muted-foreground leading-tight">{meta}</p>}
      </div>
    </div>
  );
}

const SEV_BADGE: Record<string, string> = { critical: "badge-danger", high: "badge-warning", medium: "badge-info", low: "badge-neutral" };
const SEV_ICON_BG: Record<string, string> = {
  critical: "bg-red-500/15 text-red-600 dark:text-red-400",
  high: "bg-orange-500/15 text-orange-600 dark:text-orange-400",
  medium: "bg-amber-500/15 text-amber-600 dark:text-amber-400",
  low: "bg-slate-500/15 text-slate-600 dark:text-slate-400",
};

export default function Overview() {
  const { data: projects, isLoading: projectsLoading, isError: projectsError, refetch: refetchProjects } = useListProjects({ limit: 100 });
  const { data: suppliers } = useListSuppliers({ limit: 100 });
  const { data: exec, isLoading: execLoading, isError: execError } = useExecutive();
  const { data: portfolioTrend } = usePortfolioTrend();
  const { data: alertsSummary } = useAlertsSummary();

  const [search, setSearch] = useState("");
  const [scopeProjectId, setScopeProjectId] = useState<string>("all");
  const [attentionTab, setAttentionTab] = useState<AttentionTab>("alerts");
  const searchWrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        searchWrapRef.current?.querySelector("input")?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const { data: alertsData, isLoading: alertsLoading } = useAlerts({
    project_id: scopeProjectId === "all" ? undefined : Number(scopeProjectId),
    limit: 5,
  });

  // Cross-module demo previews — pure functions, read-only, same
  // deterministic output the source modules' own pages already show.
  const edc = useMemo(() => (projects?.length ? generateExecutiveDecisionCenter(projects) : null), [projects]);
  const mat = useMemo(() => (projects?.length ? generateMaterialIntelligence(suppliers ?? [], projects) : null), [projects, suppliers]);
  const sup = useMemo(() => (projects?.length ? generateSupplierRisk(suppliers ?? [], projects) : null), [projects, suppliers]);

  const rankedIds = new Set([...(exec?.top_priorities ?? []), ...(exec?.attention_required ?? []), ...(exec?.best_projects ?? [])].map((b) => b.project_id));
  const coveragePct = projects?.length ? Math.round((rankedIds.size / projects.length) * 100) : 0;

  const heatCounts = useMemo(() => {
    if (!edc) return [];
    return HEAT_DIMENSIONS.map((dim) => {
      const counts: Record<string, number> = { Low: 0, Medium: 0, High: 0, Critical: 0 };
      for (const row of edc.heatMapRows) counts[riskBand(row[dim.key])]++;
      return { ...dim, counts };
    });
  }, [edc]);

  const scheduleRiskCount = heatCounts.find((h) => h.key === "schedule");
  const safetyRiskCount = heatCounts.find((h) => h.key === "safety");
  const supplierRiskCount = heatCounts.find((h) => h.key === "supplier");
  const scheduleAtRisk = (scheduleRiskCount?.counts.High ?? 0) + (scheduleRiskCount?.counts.Critical ?? 0);
  const safetyAtRisk = (safetyRiskCount?.counts.High ?? 0) + (safetyRiskCount?.counts.Critical ?? 0);
  const supplierAtRisk = (supplierRiskCount?.counts.High ?? 0) + (supplierRiskCount?.counts.Critical ?? 0);

  const realHealthTrend = (portfolioTrend ?? []).map((p) => ({ value: p.score }));
  const trendSeries = [
    { key: "health", label: "Portfolio Health", value: exec?.portfolio_score ?? 0, suffix: "", color: "#16a34a", data: realHealthTrend.length >= 2 ? realHealthTrend : seededTrend("health", exec?.portfolio_score ?? 70), demo: realHealthTrend.length < 2 },
    { key: "cost", label: "Cost Exposure", value: mat ? formatSar(mat.portfolioStats.totalExposureSar, false) : "—", suffix: "", color: "#dc2626", data: seededTrend("cost", mat?.portfolioStats.totalExposureSar ?? 0), demo: true },
    { key: "schedule", label: "Schedule Risk", value: scheduleAtRisk, suffix: "", color: "#f97316", data: seededTrend("schedule", scheduleAtRisk), demo: true },
    { key: "safety", label: "Safety Risk", value: safetyAtRisk, suffix: "", color: "#d97706", data: seededTrend("safety", safetyAtRisk), demo: true },
    { key: "supplier", label: "Supplier Risk", value: supplierAtRisk, suffix: "", color: "#0ea5e9", data: seededTrend("supplier", supplierAtRisk), demo: true },
    { key: "decisions", label: "Decisions Open", value: edc?.overview.pendingDecisions ?? 0, suffix: "", color: "#6366f1", data: seededTrend("decisions", edc?.overview.pendingDecisions ?? 0), demo: true },
  ];

  const filteredQuickAccess = QUICK_ACCESS.filter((w) => w.title.toLowerCase().includes(search.trim().toLowerCase()));
  const alertBadge = (alertsSummary?.critical ?? 0) + (alertsSummary?.high ?? 0);

  if (projectsLoading || execLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-32 w-full rounded-2xl" />
        <div className="grid gap-3 lg:grid-cols-[1fr_300px]">
          <Skeleton className="h-44 w-full rounded-xl" />
          <Skeleton className="h-44 w-full rounded-xl" />
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
          {[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
        </div>
        <Skeleton className="h-52 w-full rounded-xl" />
      </div>
    );
  }

  if (projectsError || execError) {
    return (
      <ErrorState title="Unable to load AI Center" description="Check your connection and try again." action={
        <button className="text-xs font-medium text-primary hover:underline" onClick={() => refetchProjects()}>Retry</button>
      } />
    );
  }

  if (!projects?.length) {
    return <EmptyState icon={Sparkles} title="No projects yet" description="AI Center comes to life once projects exist to analyze." />;
  }

  const scopedProject = scopeProjectId === "all" ? null : projects.find((p) => String(p.id) === scopeProjectId);

  return (
    <div className="space-y-6">
      {/* 1 — Hero ────────────────────────────────────────────────────── */}
      <PageHero
        eyebrow="AI Center"
        title="AI Center Overview"
        description="Executive intelligence across projects, risks, suppliers, materials, and organizational knowledge."
        search={
          <div ref={searchWrapRef} className="relative">
            <SearchInput value={search} onChange={setSearch} placeholder="Search across AMAD..." testId="input-ai-hero-search" />
            <span className="hidden md:inline-flex absolute end-2 top-1/2 -translate-y-1/2 items-center gap-0.5 rounded border border-border/60 bg-muted/60 px-1.5 py-0.5 text-[9px] font-semibold text-muted-foreground pointer-events-none">
              Ctrl+K
            </span>
          </div>
        }
        scopeSelector={
          <FilterSelect value={scopeProjectId} onChange={setScopeProjectId} className="w-56 bg-card" ariaLabel="Project scope">
            <option value="all">All Projects (Portfolio)</option>
            {projects.map((p) => <option key={p.id} value={p.id}>{p.project_code} — {p.project_name}</option>)}
          </FilterSelect>
        }
        meta={<span>Last updated {new Date().toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}</span>}
        primaryAction={
          <div className="flex items-center gap-2">
            <Link href="/alerts" className="relative w-9 h-9 rounded-lg border border-sidebar-border flex items-center justify-center text-sidebar-foreground/70 hover:text-sidebar-foreground hover:bg-sidebar-accent/50 transition-colors shrink-0" aria-label="Alerts">
              <Bell className="w-4 h-4" />
              {alertBadge > 0 && (
                <span className="absolute -top-1 -end-1 min-w-[16px] h-4 px-1 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center">{alertBadge}</span>
              )}
            </Link>
            <a href="#executive-brief" className="inline-flex items-center gap-1.5 h-9 px-4 rounded-lg border border-sidebar-primary/50 text-sidebar-primary text-xs font-semibold hover:bg-sidebar-primary/10 transition-colors">
              <Sparkles className="w-3.5 h-3.5" /> AI Brief
            </a>
          </div>
        }
      />

      {/* 2 — Executive Brief (dominant) + Mini Heat Map ───────────────── */}
      <div id="executive-brief" className="grid gap-3 lg:grid-cols-[1fr_300px] items-stretch scroll-mt-4">
        <InsightPanel
          icon={AlertTriangle}
          title="Executive AI Brief"
          variant="brief"
          badge={<DemoDataBadge />}
          footer={
            <Link href="/ai-center/executive-decision-center" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
              View full executive brief <ArrowRight className="w-3 h-3" />
            </Link>
          }
        >
          <div className="grid md:grid-cols-[1.3fr_110px_250px] gap-4 items-center">
            <div className="space-y-1.5">
              <p className="text-base font-bold text-foreground leading-snug">
                <span className="text-accent">{edc?.overview.criticalAlerts ?? 0} critical risk{(edc?.overview.criticalAlerts ?? 0) === 1 ? "" : "s"}</span> require executive attention this week.
              </p>
              <p className="text-[13px] text-muted-foreground leading-normal">
                Delays on {edc?.attentionProjects.length ?? 0} projects, material cost exposure of {mat ? formatSar(mat.portfolioStats.totalExposureSar) : "—"}, and{" "}
                {sup?.portfolioStats.highRiskCount ?? 0} suppliers showing declining performance.
              </p>
            </div>

            <div className="hidden md:flex items-center justify-center h-full">
              <BriefIllustration />
            </div>

            <div className="space-y-1">
              {[
                mat?.alerts[0] && { icon: Clock3, iconTone: SEV_ICON_BG[mat.alerts[0].severity.toLowerCase()] ?? SEV_ICON_BG.medium, title: mat.alerts[0].title, subtitle: `${mat.alerts[0].affectedProjects.length} projects · ${formatSar(mat.alerts[0].estimatedImpactSar)}`, badge: mat.alerts[0].severity, badgeTone: SEV_BADGE[mat.alerts[0].severity.toLowerCase()] ?? "badge-neutral" },
                edc?.attentionProjects[0] && { icon: TrendingUp, iconTone: SEV_ICON_BG[edc.attentionProjects[0].riskBand.toLowerCase()] ?? SEV_ICON_BG.medium, title: `${edc.attentionProjects[0].projectCode} risk increasing`, subtitle: edc.attentionProjects[0].reasons[0], badge: edc.attentionProjects[0].riskBand, badgeTone: SEV_BADGE[edc.attentionProjects[0].riskBand.toLowerCase()] ?? "badge-neutral" },
                edc && { icon: MapPin, iconTone: SEV_ICON_BG.medium, title: `${edc.overview.pendingDecisions} decisions pending approval`, subtitle: "Review before the next steering cycle", badge: edc.overview.pendingDecisions > 5 ? "High" : "Medium", badgeTone: edc.overview.pendingDecisions > 5 ? "badge-warning" : "badge-info" },
              ].filter(Boolean).map((s, i) => s && <AttentionRow key={i} icon={s.icon} iconTone={s.iconTone} title={s.title} subtitle={s.subtitle} badge={s.badge} badgeTone={s.badgeTone} />)}
            </div>
          </div>
        </InsightPanel>

        <div className="panel h-full flex flex-col">
          <div className="px-3.5 py-2.5 border-b flex items-center justify-between">
            <span className="font-semibold text-[13px] text-foreground">Portfolio Risk Heat Map</span>
            <DemoDataBadge label="Demo" />
          </div>
          <div className="p-3 flex-1">
            <div className="grid gap-1 text-[10px] text-muted-foreground" style={{ gridTemplateColumns: "58px repeat(4, 1fr)" }}>
              <div />
              {BANDS.map((b) => <div key={b} className="text-center font-medium">{b === "Critical" ? "Crit." : b.slice(0, 3)}</div>)}
              {heatCounts.map((row) => (
                <div key={row.key} className="contents">
                  <div className="text-[10px] text-foreground/80 flex items-center">{row.label}</div>
                  {BANDS.map((b) => (
                    <div
                      key={b}
                      className="m-0.5 rounded-md flex items-center justify-center text-[11px] font-bold text-white"
                      style={{ backgroundColor: RISK_COLOR[b], minHeight: 24, opacity: row.counts[b] === 0 ? 0.22 : 1 }}
                    >
                      {row.counts[b]}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
          <div className="px-3.5 pb-3">
            <Link href="/ai-center/executive-decision-center" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
              View full heat map <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </div>

      {/* 3 — KPI strip ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
        <KpiStat icon={Building2} label="Projects Analyzed" value={projects.length} description="Active projects" tone="neutral" href="/ai-center/projects" deltaValue="8%" deltaPositive />
        <KpiStat icon={ShieldIcon} label="Critical Risks" value={exec?.critical_count ?? 0} description="Require attention" tone="danger" href="/ai-center/executive" deltaValue="12%" deltaPositive={false} />
        <KpiStat icon={Wallet} label="Cost Exposure" value={mat ? formatSar(mat.portfolioStats.totalExposureSar) : "—"} description="Potential impact" tone="warning" demo href="/ai-center/material-intelligence" deltaValue="15%" deltaPositive={false} />
        <KpiStat icon={Gavel} label="Open Decisions" value={edc?.overview.pendingDecisions ?? 0} description="Awaiting approval" tone="warning" demo href="/ai-center/executive-decision-center" deltaValue="15%" deltaPositive={false} />
        <KpiStat icon={Brain} label="AI Confidence" value={coveragePct} valueSuffix="%" description="Overall accuracy" tone="gold" deltaValue="5%" deltaPositive />
      </div>

      {/* 4 — Today's Attention / Executive Recommendations / Attention Projects — equal thirds, one row */}
      <div className="grid gap-3 lg:grid-cols-3 items-stretch">
        <div className="panel flex flex-col">
          <div className="px-3 py-1 border-b flex items-center justify-between">
            <span className="font-semibold text-xs text-foreground">Today's Attention</span>
            <DemoDataBadge />
          </div>
          <div className="px-3 pt-1 [&_[role=tablist]]:!h-6 [&_[role=tab]]:!py-0 [&_[role=tablist]]:!mb-0">
            <PageTabs<AttentionTab>
              tabs={[
                { id: "alerts", label: "Top Alerts", count: alertsData?.alerts.length },
                { id: "decisions", label: "Pending Decisions", count: edc?.decisionQueue.length },
                { id: "risks", label: "Emerging Risks", count: exec?.biggest_risks?.length },
              ]}
              value={attentionTab}
              onChange={setAttentionTab}
            />
          </div>
          <div className="p-1.5 space-y-px flex-1">
            {attentionTab === "alerts" && (
              alertsLoading ? <Skeleton className="h-24 w-full rounded-lg" /> :
              !alertsData?.alerts.length ? <p className="text-xs text-muted-foreground py-2">No active alerts{scopedProject ? ` for ${scopedProject.project_code}` : ""}.</p> :
              alertsData.alerts.slice(0, 5).map((a) => (
                <Link key={a.id} href="/alerts" className="block">
                  <CompactRow
                    icon={AlertTriangle}
                    iconTone={SEV_ICON_BG[a.severity] ?? SEV_ICON_BG.medium}
                    title={a.title}
                    subtitle={a.project_code ?? "Portfolio-wide"}
                    badge={a.severity}
                    badgeTone={SEV_BADGE[a.severity] ?? "badge-neutral"}
                    meta={new Date(a.detected_at).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}
                  />
                </Link>
              ))
            )}
            {attentionTab === "decisions" && (
              !edc?.decisionQueue.length ? <p className="text-xs text-muted-foreground py-2">Nothing pending.</p> :
              edc.decisionQueue.slice(0, 5).map((d) => (
                <Link key={d.id} href="/ai-center/executive-decision-center" className="block">
                  <CompactRow
                    icon={Gavel}
                    iconTone={SEV_ICON_BG[d.priority === "High" ? "high" : d.priority === "Medium" ? "medium" : "low"]}
                    title={d.title}
                    subtitle="Decision Required"
                    badge={d.priority}
                    badgeTone={d.priority === "High" ? "badge-danger" : d.priority === "Medium" ? "badge-warning" : "badge-neutral"}
                  />
                </Link>
              ))
            )}
            {attentionTab === "risks" && (
              !exec?.biggest_risks?.length ? <p className="text-xs text-muted-foreground py-2">No elevated risks.</p> :
              exec.biggest_risks.slice(0, 5).map((r) => (
                <CompactRow
                  key={r.category}
                  icon={Radar}
                  iconTone={SEV_ICON_BG[r.severity?.toLowerCase()] ?? SEV_ICON_BG.medium}
                  title={r.label}
                  subtitle={r.detail}
                  badge={String(r.count)}
                  badgeTone={SEV_BADGE[r.severity?.toLowerCase()] ?? "badge-neutral"}
                />
              ))
            )}
          </div>
          <div className="px-3 pb-1.5">
            <Link href={attentionTab === "alerts" ? "/alerts" : attentionTab === "decisions" ? "/ai-center/executive-decision-center" : "/ai-center/executive"} className="inline-flex items-center gap-1 text-[11px] font-medium text-primary hover:underline">
              View all {attentionTab === "alerts" ? "alerts" : attentionTab === "decisions" ? "decisions" : "risks"} <ArrowRight className="w-2.5 h-2.5" />
            </Link>
          </div>
        </div>

        <div className="panel flex flex-col">
          <div className="px-3 py-1 border-b flex items-center justify-between">
            <span className="font-semibold text-xs text-foreground">Executive Recommendations</span>
            <DemoDataBadge />
          </div>
          <div className="p-1.5 space-y-px flex-1">
            {!edc?.recommendedActions.length ? (
              <p className="text-xs text-muted-foreground py-2">No recommendations right now.</p>
            ) : (
              edc.recommendedActions.slice(0, 5).map((a) => (
                <CompactRow
                  key={a.id}
                  icon={Target}
                  iconTone={SEV_ICON_BG[a.priority === "High" ? "high" : a.priority === "Medium" ? "medium" : "low"]}
                  title={a.title}
                  subtitle={a.estimatedImpact}
                  badge={a.priority}
                  badgeTone={a.priority === "High" ? "badge-danger" : a.priority === "Medium" ? "badge-warning" : "badge-neutral"}
                />
              ))
            )}
          </div>
          <div className="px-3 pb-1.5">
            <Link href="/ai-center/executive-decision-center" className="inline-flex items-center gap-1 text-[11px] font-medium text-primary hover:underline">
              View all recommendations <ArrowRight className="w-2.5 h-2.5" />
            </Link>
          </div>
        </div>

        <div className="panel flex flex-col">
          <div className="px-3 py-1 border-b flex items-center justify-between">
            <span className="font-semibold text-xs text-foreground">Attention Projects</span>
            <Link href="/projects" className="inline-flex items-center gap-1 text-[10px] font-medium text-primary hover:underline shrink-0">
              View all <ArrowRight className="w-2.5 h-2.5" />
            </Link>
          </div>
          <div className="p-1.5 flex-1">
            {!exec?.attention_required?.length ? (
              <p className="text-xs text-muted-foreground py-2">No projects currently need urgent attention.</p>
            ) : (
              <div className="space-y-px">
                <div className="grid grid-cols-[auto_1fr_auto] gap-1.5 px-1.5 pb-px text-[9px] font-semibold uppercase tracking-wide text-muted-foreground">
                  <span />
                  <span>Project</span>
                  <span className="text-end">Health / Delay</span>
                </div>
                {exec.attention_required.slice(0, 5).map((p) => {
                  const tone = LEVEL_TONE[p.level] ?? LEVEL_TONE.Good;
                  const delay = syntheticDelayDays(p.project_id);
                  return (
                    <Link
                      key={p.project_id}
                      href={`/projects/${p.project_id}`}
                      title={`${p.project_name} — ${p.level}, health ${p.score}, +${delay}d delay`}
                      className="grid grid-cols-[auto_1fr_auto] items-center gap-1.5 px-1.5 py-0 rounded-md hover:bg-muted/50 transition-colors"
                    >
                      <span className={`w-2 h-2 rounded-full shrink-0 ${tone.dot}`} />
                      <span className="min-w-0 py-px">
                        <p className="text-[11px] font-semibold text-foreground truncate leading-[1.15]">{p.project_code}</p>
                        <p className="text-[9.5px] text-muted-foreground truncate leading-[1.15]">{p.project_name}</p>
                      </span>
                      <span className="text-end leading-[1.15] shrink-0">
                        <span className={`block text-[11px] font-bold ${tone.text}`}>{p.score}</span>
                        <span className="block text-[9px] font-semibold text-red-600 dark:text-red-400">+{delay}d</span>
                      </span>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 5 — KPI Trends (6 cols) + Quick Access ─────────────────────────── */}
      <div className="grid gap-3 lg:grid-cols-[1fr_400px]">
        <div className="panel">
          <div className="px-3.5 py-2.5 border-b flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-[13px] text-foreground">KPI Trends</span>
              <span className="text-[10px] text-muted-foreground font-normal">(8 weeks)</span>
              <DemoDataBadge />
            </div>
            <Link href="/reports" className="inline-flex items-center gap-1 text-[11px] font-medium text-primary hover:underline shrink-0">
              View all analytics <ArrowRight className="w-2.5 h-2.5" />
            </Link>
          </div>
          <div className="p-3 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {trendSeries.map((s) => {
              const delta = trendDeltaPct(s.data);
              return (
                <div key={s.key}>
                  <div className="flex items-center gap-1 mb-0.5">
                    <p className="text-[10px] font-semibold text-muted-foreground truncate">{s.label}</p>
                    {s.demo && <span className="w-1 h-1 rounded-full bg-accent shrink-0" title="Demo Data" />}
                  </div>
                  <div className="flex items-baseline gap-1.5">
                    <p className="text-sm font-bold text-foreground kpi-number">{s.value}</p>
                    {delta && (
                      <span className={`inline-flex items-center text-[9px] font-semibold ${delta.up ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}`}>
                        {delta.up ? <TrendingUp className="w-2.5 h-2.5" /> : <TrendingDown className="w-2.5 h-2.5" />}{Math.abs(delta.pct)}%
                      </span>
                    )}
                  </div>
                  <MiniSparkline data={s.data} id={s.key} color={s.color} />
                </div>
              );
            })}
          </div>
        </div>

        <div className="panel">
          <div className="px-3.5 py-2.5 border-b"><span className="font-semibold text-[13px] text-foreground">Quick Access to AI Workspaces</span></div>
          <div className="p-3">
            {filteredQuickAccess.length === 0 ? (
              <p className="text-xs text-muted-foreground text-center py-4">No workspaces match "{search}".</p>
            ) : (
              <div className="grid grid-cols-4 gap-1.5">
                {filteredQuickAccess.map((w) => (
                  <WorkspaceQuickLink key={w.key} icon={w.icon} title={w.title} href={w.href} accent={w.accent} variant="card" />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
