import { useListProjects } from "@workspace/api-client-react";
import { Link } from "wouter";
import { Building2, ChevronRight, HeartPulse } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { useExecutive } from "@/lib/useExecutive";

const STATUS_BADGE: Record<string, string> = {
  Active: "badge-success", Delayed: "badge-danger", Completed: "badge-info",
  Suspended: "badge-neutral", Planning: "badge-purple", "On Hold": "badge-warning",
};

const LEVEL_TONE: Record<string, string> = {
  Excellent: "text-emerald-600 dark:text-emerald-400",
  Good: "text-blue-600 dark:text-blue-400",
  "At Risk": "text-amber-600 dark:text-amber-400",
  Critical: "text-rose-600 dark:text-rose-400",
};

// Project Intelligence workspace — a portfolio-wide entry point into each
// project's AI workspace (Project tab on /projects/:id). Health/level for
// the projects Executive Intelligence already ranks (top_priorities +
// attention_required + best_projects) is shown inline without any new
// per-project fetch; projects outside that ranked set still show their
// plain status — no N+1 health calls, no fabricated scores.
export default function ProjectIntelligence() {
  const { data: projects, isLoading } = useListProjects({ limit: 100 });
  const { data: exec } = useExecutive();

  const briefByProjectId = new Map<number, { score: number; level: string; primary_reason: string }>();
  for (const brief of [...(exec?.top_priorities ?? []), ...(exec?.attention_required ?? []), ...(exec?.best_projects ?? [])]) {
    briefByProjectId.set(brief.project_id, brief);
  }

  if (isLoading) {
    return (
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}
      </div>
    );
  }

  if (!projects?.length) {
    return <EmptyState icon={Building2} title="No projects yet" description="Projects will appear here once created." />;
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-semibold text-foreground">Project Intelligence</h2>
        <p className="text-sm text-muted-foreground">
          {projects.length} projects &middot; open any project's AI workspace for health score, AI summary, and Ask Hermes.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {projects.map((p) => {
          const brief = briefByProjectId.get(p.id);
          return (
            <Link
              key={p.id}
              href={`/projects/${p.id}?tab=ai-summary`}
              className="rounded-xl border border-border bg-card p-4 space-y-2 hover:border-primary/30 transition-colors group"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-xs font-mono text-muted-foreground">{p.project_code}</p>
                  <h4 className="font-semibold text-sm text-foreground truncate">{p.project_name}</h4>
                </div>
                <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0 group-hover:translate-x-0.5 transition-transform" />
              </div>
              <span className={`badge ${STATUS_BADGE[p.status] ?? "badge-neutral"}`}>{p.status}</span>
              {brief && (
                <div className="flex items-center gap-1.5 pt-1 text-xs">
                  <HeartPulse className={`w-3.5 h-3.5 ${LEVEL_TONE[brief.level] ?? "text-muted-foreground"}`} />
                  <span className={`font-semibold ${LEVEL_TONE[brief.level] ?? "text-foreground"}`}>{brief.score}/100</span>
                  <span className="text-muted-foreground truncate">&middot; {brief.primary_reason}</span>
                </div>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
