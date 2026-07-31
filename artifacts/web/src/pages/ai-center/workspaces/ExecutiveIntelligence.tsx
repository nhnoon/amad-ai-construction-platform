import { Link } from "wouter";
import {
  Sparkles, AlertOctagon, Radar, ShoppingCart, Gavel, Target, ExternalLink, ArrowRight,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { PageHero } from "@/components/PageHero";
import { InsightPanel } from "@/components/InsightPanel";
import { useExecutive } from "@/lib/useExecutive";
import { useExecutiveWeeklyReport } from "@/lib/useReports";

// ── AMAD v2 — Executive Intelligence ────────────────────────────────────────
// Same executive tier as Dashboard, Reports, and AI Center Overview — this
// workspace now renders its own PageHero (see the "executive" special-case
// in ../index.tsx, mirroring the one Overview already has) instead of the
// generic 16-workspace WorkspaceLayout shell, and its content follows the
// same What's happening / Why / What next reading order those three pages
// already established. No new data: still the exact same useExecutive() +
// useExecutiveWeeklyReport() calls this workspace has always made — this is
// AI Center's own entry point into that real data, not a rebuild of either
// page. "Recent Decisions" stays an honest redirect: there's no
// portfolio-wide decisions endpoint, so it points to Meeting Intelligence
// per-project instead of faking an aggregate feed.

const SEVERITY_TONE: Record<string, string> = {
  critical: "badge-danger", high: "badge-danger", medium: "badge-warning",
  warning: "badge-warning", low: "badge-info", info: "badge-info",
};

// Duplicated from dashboard/shared.tsx's EXEC_LEVEL_CFG and reports.tsx's
// LEVEL_CFG (this is the fourth independent copy of the same Excellent/
// Good/At Risk/Critical → color mapping across the app — see the migration
// report for this page; a strong candidate for a shared constant, not
// something this page-scoped pass introduces new risk by touching.
const LEVEL_DOT_COLOR: Record<string, string> = {
  Excellent: "#16a34a",
  Good: "#2563eb",
  "At Risk": "#d97706",
  Critical: "#dc2626",
};

// Phase 2 §4 — every insight card names its confidence. These figures are
// deterministic aggregations straight off live records (open POs, NCRs,
// safety events…), not an LLM's probabilistic guess — so confidence here
// means "how directly this number traces to the database," not a model's
// self-reported certainty. Always High for that reason; shown so it's
// never left implicit, per the ticket's own requirement.
function ConfidenceTag() {
  return (
    <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-600 dark:text-emerald-400" title="Computed directly from live database records, not an AI estimate">
      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
      High confidence · live records
    </span>
  );
}

// Secondary-panel header — AMAD v2's shared `.panel-header` bar (border-b,
// icon + title + optional subtitle/action) instead of the small uppercase
// label previously embedded inside `.panel-body` with no separator. Same
// shape as Reports' PanelHeader (icon/title/subtitle/color props) — a
// second independent implementation of the same pattern, also flagged in
// the migration report.
function SectionShell({ icon: Icon, title, subtitle, color = "text-primary", action, children }: {
  icon: typeof Sparkles; title: string; subtitle?: string; color?: string; action?: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <section className="panel">
      <div className="panel-header">
        <span className="flex items-center gap-2 min-w-0">
          <Icon className={`w-4 h-4 shrink-0 ${color}`} />
          <span className="panel-title truncate">{title}</span>
        </span>
        {action ?? (subtitle ? <span className="text-[10px] text-muted-foreground shrink-0">{subtitle}</span> : null)}
      </div>
      <div className="panel-body space-y-3">{children}</div>
    </section>
  );
}

// Stabilization pass — the four executive pages (Dashboard, Reports,
// Executive Intelligence, Executive Decision Center) previously had no
// link to one another anywhere; a user had to already know all four
// existed and go back to the sidebar every time. This wayfinding strip
// makes them read as one connected suite. Defined identically (and
// intentionally duplicated, not extracted — out of scope for this pass)
// in all four pages; a real candidate for a shared primitive later.
const EXECUTIVE_SUITE_LINKS: { key: string; label: string; href: string }[] = [
  { key: "dashboard", label: "Dashboard", href: "/" },
  { key: "reports", label: "Reports", href: "/reports" },
  { key: "executive-intelligence", label: "Executive Intelligence", href: "/ai-center/executive" },
  { key: "decision-center", label: "Decision Center", href: "/ai-center/executive-decision-center" },
];

function ExecutiveSuiteNav({ current }: { current: string }) {
  return (
    <nav aria-label="Executive Suite" className="flex flex-wrap items-center gap-1.5">
      <span className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground me-0.5">Executive Suite</span>
      {EXECUTIVE_SUITE_LINKS.map((p) => p.key === current ? (
        <span key={p.key} className="badge badge-brand text-[11px] cursor-default" aria-current="page">{p.label}</span>
      ) : (
        <Link key={p.key} href={p.href} className="badge badge-neutral text-[11px] hover:bg-muted transition-colors">{p.label}</Link>
      ))}
    </nav>
  );
}

export default function ExecutiveIntelligence() {
  const { data: exec, isLoading: execLoading, isError: execError, refetch: refetchExec } = useExecutive();
  const { data: report, isLoading: reportLoading, isError: reportError, refetch: refetchReport } = useExecutiveWeeklyReport();

  if (execLoading || reportLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-32 w-full rounded-2xl" />
        <div className="grid gap-3 lg:grid-cols-[1fr_340px] items-stretch">
          <Skeleton className="h-40 w-full rounded-xl" />
          <Skeleton className="h-40 w-full rounded-xl" />
        </div>
        <div className="grid gap-4 lg:grid-cols-2">
          {[0, 1].map((i) => <Skeleton key={i} className="h-44 w-full rounded-xl" />)}
        </div>
        <Skeleton className="h-40 w-full rounded-xl" />
        <Skeleton className="h-40 w-full rounded-xl" />
      </div>
    );
  }

  // Stabilization fix — this was the one page in the executive suite with
  // no error state (isError was never destructured, so a failed request
  // silently fell through to placeholder copy instead of telling the
  // user anything failed). Same ErrorState + retry pattern as Dashboard,
  // Reports, and Executive Decision Center.
  if (execError || reportError) {
    return (
      <ErrorState
        title="Unable to load executive intelligence"
        description="Check your connection and try refreshing."
        action={
          <button
            className="text-xs font-medium text-primary hover:underline"
            onClick={() => { refetchExec(); refetchReport(); }}
          >
            Retry
          </button>
        }
      />
    );
  }

  const attentionProjects = exec?.attention_required.slice(0, 5) ?? [];

  return (
    <div className="space-y-6">
      {/* 1 — Hero ────────────────────────────────────────────────────── */}
      <PageHero
        eyebrow="AI Center"
        title="Executive Intelligence"
        description="Portfolio-wide AI insight — critical projects, risks, and suggested actions."
        meta={<span>Last updated {new Date().toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}</span>}
        primaryAction={
          <Link
            href="/reports"
            className="inline-flex items-center gap-1.5 h-9 px-4 rounded-lg border border-sidebar-primary/50 text-sidebar-primary text-xs font-semibold hover:bg-sidebar-primary/10 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" /> Full Weekly Report
          </Link>
        }
      />

      <ExecutiveSuiteNav current="executive-intelligence" />

      {/* 2 — What's happening: AI Brief + Critical Projects ──────────── */}
      <div className="grid gap-3 lg:grid-cols-[1fr_340px] items-stretch">
        <InsightPanel icon={Sparkles} title="Today's AI Insights" variant="brief">
          <p className="text-[13px] text-muted-foreground leading-normal">
            {exec?.executive_summary ?? "No summary available yet."}
          </p>
          {exec && (
            <div className="flex items-center gap-4 mt-2 pt-2 border-t border-border/50 text-xs text-muted-foreground">
              <span>Portfolio score: <strong className="text-foreground">{exec.portfolio_score}/100</strong></span>
              <span>Status: <strong className="text-foreground">{exec.portfolio_status}</strong></span>
            </div>
          )}
        </InsightPanel>

        <div className="panel h-full flex flex-col">
          <div className="px-3.5 py-2.5 border-b flex items-center justify-between">
            <span className="font-semibold text-[13px] text-foreground flex items-center gap-1.5">
              <AlertOctagon className="w-3.5 h-3.5 text-red-600 dark:text-red-400" /> Critical Projects
            </span>
            {attentionProjects.length > 0 && <span className="badge badge-danger text-[9px]">{attentionProjects.length}</span>}
          </div>
          <div className="p-1.5 flex-1">
            {attentionProjects.length === 0 ? (
              <p className="text-xs text-muted-foreground py-2 px-1.5">Nothing needs immediate attention right now.</p>
            ) : (
              <div className="space-y-px">
                {attentionProjects.map((p) => {
                  const color = LEVEL_DOT_COLOR[p.level] ?? LEVEL_DOT_COLOR.Good;
                  return (
                    <Link
                      key={p.project_id}
                      href={`/projects/${p.project_id}`}
                      title={`${p.project_name} — ${p.level}, score ${p.score}. ${p.primary_reason}`}
                      className="grid grid-cols-[auto_1fr_auto] items-center gap-1.5 px-1.5 py-1 rounded-md hover:bg-muted/50 transition-colors"
                    >
                      <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: color }} />
                      <span className="min-w-0">
                        <p className="text-[11px] font-semibold text-foreground truncate leading-tight">{p.project_code}</p>
                        <p className="text-[9.5px] text-muted-foreground truncate leading-tight mt-px">{p.primary_reason}</p>
                      </span>
                      <span className="text-end text-[11px] font-bold shrink-0" style={{ color }}>{p.score}</span>
                    </Link>
                  );
                })}
              </div>
            )}
          </div>
          <div className="px-3.5 pb-3">
            <Link href="/projects" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
              View all projects <ArrowRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </div>

      {/* 3 — Why it's happening: Top Risks + Procurement Issues ───────── */}
      <div className="grid gap-4 lg:grid-cols-2">
        <SectionShell icon={Radar} title="Top Risks" color="text-rose-500">
          {!exec?.biggest_risks?.length ? (
            <EmptyState icon={Radar} title="No elevated risks" />
          ) : (
            <div className="space-y-2">
              {exec.biggest_risks.map((r) => (
                <div key={r.category} className="rounded-lg border border-border/60 p-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium text-foreground">{r.label}</p>
                    <span className={`badge ${SEVERITY_TONE[r.severity?.toLowerCase()] ?? "badge-neutral"}`}>{r.count}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">{r.detail}</p>
                  <div className="mt-1.5"><ConfidenceTag /></div>
                </div>
              ))}
            </div>
          )}
        </SectionShell>

        <SectionShell icon={ShoppingCart} title="Procurement Issues" color="text-blue-500">
          {!report?.procurement_blockers?.length ? (
            <EmptyState icon={ShoppingCart} title="No procurement blockers" />
          ) : (
            <div className="space-y-2">
              {report.procurement_blockers.map((b) => (
                <div key={b.label} className="rounded-lg border border-border/60 p-2.5">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-sm font-medium text-foreground">{b.label}</p>
                    <span className={`badge ${SEVERITY_TONE[b.severity?.toLowerCase()] ?? "badge-neutral"}`}>{b.count}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">{b.detail}</p>
                  <div className="mt-1.5"><ConfidenceTag /></div>
                </div>
              ))}
            </div>
          )}
        </SectionShell>
      </div>

      {/* 4 — What leadership should do next: Suggested Actions ────────── */}
      {report?.recommended_actions?.length ? (
        <InsightPanel
          icon={Target}
          title="Suggested Actions"
          variant="decision"
          badge={<span className="text-[10px] text-muted-foreground">{report.recommended_actions.length} actions</span>}
        >
          {/* Stabilization fix — this is the exact same report.recommended_actions
              list Reports' own "Recommended Executive Actions" section shows;
              said explicitly rather than letting two pages present identical
              data as if each generated it independently. */}
          <p className="text-[11px] text-muted-foreground -mt-1 mb-1">
            Same recommendations as this week's <Link href="/reports" className="text-primary hover:underline">Executive Report</Link> — shown here for quick reference.
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {report.recommended_actions.map((a) => (
              <div key={`${a.priority}-${a.area}`} className="rounded-lg border border-border/60 p-3">
                <span className="text-xs font-semibold text-primary">#{a.priority} &middot; {a.area}</span>
                <p className="text-sm text-foreground mt-1">{a.action}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{a.rationale}</p>
                <div className="mt-1.5"><ConfidenceTag /></div>
              </div>
            ))}
          </div>
        </InsightPanel>
      ) : (
        <SectionShell icon={Target} title="Suggested Actions">
          <EmptyState icon={Target} title="No suggested actions right now" />
        </SectionShell>
      )}

      {/* 5 — Recent Decisions (honest redirect, lowest priority) ──────── */}
      <SectionShell
        icon={Gavel} title="Recent Decisions" color="text-muted-foreground"
        action={<Link href="/ai-center/meetings" className="text-xs text-primary hover:underline shrink-0">Browse by project</Link>}
      >
        <EmptyState
          icon={Gavel}
          title="Decisions are tracked per project"
          description="There's no portfolio-wide decision feed yet — open Meeting Intelligence and pick a project to see its decision log."
        />
      </SectionShell>
    </div>
  );
}
