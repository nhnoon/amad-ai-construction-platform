import { Link } from "wouter";
import {
  Sparkles, AlertOctagon, Radar, ShoppingCart, Gavel, Target, ExternalLink, ArrowRight,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { useExecutive } from "@/lib/useExecutive";
import { useExecutiveWeeklyReport } from "@/lib/useReports";

const SEVERITY_TONE: Record<string, string> = {
  critical: "badge-danger", high: "badge-danger", medium: "badge-warning",
  warning: "badge-warning", low: "badge-info", info: "badge-info",
};

function SectionShell({ icon: Icon, title, action, children }: {
  icon: typeof Sparkles; title: string; action?: React.ReactNode; children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border bg-card p-4 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-primary" />
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h3>
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

// Executive Intelligence workspace — reuses the exact same endpoints the
// Executive Dashboard (/) and Executive Weekly Report (/reports) already
// call; this is the AI Center's own entry point into the same real data,
// not a rebuild of either page. "Recent Decisions" is honestly scoped:
// there's no portfolio-wide decisions endpoint yet, so it links to Meeting
// Intelligence per-project rather than faking an aggregate feed.
export default function ExecutiveIntelligence() {
  const { data: exec, isLoading: execLoading } = useExecutive();
  const { data: report, isLoading: reportLoading } = useExecutiveWeeklyReport();

  if (execLoading || reportLoading) {
    return (
      <div className="grid gap-4 lg:grid-cols-2">
        {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-40 w-full rounded-xl" />)}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Executive Intelligence</h2>
          <p className="text-sm text-muted-foreground">Portfolio-wide AI insight — critical projects, risks, and suggested actions.</p>
        </div>
        <Link href="/reports" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline whitespace-nowrap">
          Full Weekly Report <ExternalLink className="w-3 h-3" />
        </Link>
      </div>

      <SectionShell icon={Sparkles} title="Today's AI Insights">
        <p className="text-sm text-foreground leading-relaxed">{exec?.executive_summary ?? "No summary available yet."}</p>
        {exec && (
          <div className="flex items-center gap-4 pt-1 text-xs text-muted-foreground">
            <span>Portfolio score: <strong className="text-foreground">{exec.portfolio_score}/100</strong></span>
            <span>Status: <strong className="text-foreground">{exec.portfolio_status}</strong></span>
          </div>
        )}
      </SectionShell>

      <div className="grid gap-4 lg:grid-cols-2">
        <SectionShell icon={AlertOctagon} title="Critical Projects">
          {!exec?.attention_required?.length ? (
            <EmptyState icon={AlertOctagon} title="No critical projects" description="Nothing needs immediate attention right now." />
          ) : (
            <div className="space-y-2">
              {exec.attention_required.map((p) => (
                <Link key={p.project_id} href={`/projects/${p.project_id}`} className="flex items-center justify-between gap-2 rounded-lg border border-border/60 p-2.5 hover:border-primary/30 transition-colors group">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">{p.project_code} — {p.project_name}</p>
                    <p className="text-xs text-muted-foreground truncate">{p.primary_reason}</p>
                  </div>
                  <ArrowRight className="w-3.5 h-3.5 text-muted-foreground shrink-0 group-hover:translate-x-0.5 transition-transform" />
                </Link>
              ))}
            </div>
          )}
        </SectionShell>

        <SectionShell icon={Radar} title="Top Risks">
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
                </div>
              ))}
            </div>
          )}
        </SectionShell>

        <SectionShell icon={ShoppingCart} title="Procurement Issues">
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
                </div>
              ))}
            </div>
          )}
        </SectionShell>

        <SectionShell
          icon={Gavel} title="Recent Decisions"
          action={<Link href="/ai-center/meetings" className="text-xs text-primary hover:underline">Browse by project</Link>}
        >
          <EmptyState
            icon={Gavel}
            title="Decisions are tracked per project"
            description="There's no portfolio-wide decision feed yet — open Meeting Intelligence and pick a project to see its decision log."
          />
        </SectionShell>
      </div>

      <SectionShell icon={Target} title="Suggested Actions">
        {!report?.recommended_actions?.length ? (
          <EmptyState icon={Target} title="No suggested actions right now" />
        ) : (
          <div className="grid gap-2 sm:grid-cols-2">
            {report.recommended_actions.map((a) => (
              <div key={`${a.priority}-${a.area}`} className="rounded-lg border border-border/60 p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-primary">#{a.priority} &middot; {a.area}</span>
                </div>
                <p className="text-sm text-foreground mt-1">{a.action}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{a.rationale}</p>
              </div>
            ))}
          </div>
        )}
      </SectionShell>
    </div>
  );
}
