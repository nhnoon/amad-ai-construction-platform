import { Link } from "wouter";
import { AlertOctagon, ChevronRight } from "lucide-react";
import type { ProjectBrief } from "@/lib/useExecutive";
import { EmptyState } from "@/components/ui/empty-state";

// Executive Decision Center Integration — this used to rank the top 6
// projects by this page's own synthetic per-project risk score, each with
// 2-3 fabricated "reasons" drawn from a canned pool
// (lib/mockExecutiveDecisionCenter.ts's `reasonPool`). It now renders
// `exec.attention_required` directly — the exact same real, already-ranked
// list Dashboard's "Needs Attention" panel and Executive Intelligence's
// "Critical Projects" panel already show, each with its own real
// `primary_reason` from the backend instead of a fabricated one.

const LEVEL_BADGE: Record<string, string> = {
  Excellent: "badge-success", Good: "badge-success", "At Risk": "badge-warning", Critical: "badge-danger",
};

export function AttentionProjects({ projects }: { projects: ProjectBrief[] }) {
  if (projects.length === 0) {
    return <EmptyState icon={AlertOctagon} title="No projects need immediate attention" description="Every project is currently within acceptable risk levels." />;
  }

  return (
    <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
      {projects.map((p, rank) => (
        <Link key={p.project_id} href={`/projects/${p.project_id}`} className="rounded-lg border border-border/60 p-3 space-y-2 hover:border-primary/30 hover:-translate-y-0.5 transition-all duration-150 group">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2 min-w-0">
              <span className="w-5 h-5 rounded-full bg-muted flex items-center justify-center text-[10px] font-bold text-muted-foreground shrink-0">{rank + 1}</span>
              <div className="min-w-0">
                <p className="text-sm font-semibold text-foreground truncate">{p.project_code}</p>
                <p className="text-[11px] text-muted-foreground truncate">{p.project_name}</p>
              </div>
            </div>
            <ChevronRight className="w-3.5 h-3.5 text-muted-foreground shrink-0 group-hover:translate-x-0.5 transition-transform" />
          </div>
          <div className="flex items-center gap-2">
            <span className={`badge ${LEVEL_BADGE[p.level] ?? "badge-neutral"} text-[10px]`}>{p.level}</span>
            <span className="text-xs font-bold text-foreground tabular-nums">{p.score}/100</span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">{p.primary_reason}</p>
        </Link>
      ))}
    </div>
  );
}
