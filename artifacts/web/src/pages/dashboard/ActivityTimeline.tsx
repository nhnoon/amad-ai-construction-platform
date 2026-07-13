import { Link } from "wouter";
import { Clock, FileText } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { GLASS, GLASS_HEADER, IconChip, formatRelativeTime } from "./shared";
import type { DocumentStub } from "../../lib/aiCenterClient";

// Recent document activity, sorted newest-first. This is the one event type
// available portfolio-wide from an existing endpoint (listDocuments) without
// per-project N+1 calls — meetings, decisions and site reports only expose
// project-scoped list hooks today, so a true cross-entity activity log isn't
// buildable from existing data without a new backend aggregation endpoint
// (out of scope for this phase; see final report).

export function ActivityTimeline({
  documents, isLoading,
}: { documents?: DocumentStub[]; isLoading: boolean }) {
  const recent = [...(documents ?? [])]
    .sort((a, b) => new Date(b.doc_date).getTime() - new Date(a.doc_date).getTime())
    .slice(0, 6);

  return (
    <div className={`${GLASS} h-full`}>
      <div className={GLASS_HEADER}>
        <IconChip icon={Clock} />
        <div>
          <span className="text-sm font-bold text-foreground block">Recent Activity</span>
          <span className="text-[11px] text-muted-foreground">Latest documents added to the library</span>
        </div>
      </div>

      {isLoading ? (
        <div className="p-5 space-y-3">
          {[1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-12 w-full rounded-xl" />)}
        </div>
      ) : recent.length === 0 ? (
        <div className="p-5 min-h-[180px] flex flex-col items-center justify-center text-center gap-2">
          <FileText className="w-8 h-8 text-muted-foreground/30" />
          <p className="text-xs text-muted-foreground">No recent document activity</p>
        </div>
      ) : (
        <div className="p-5 space-y-1">
          {recent.map((doc) => (
            <div
              key={doc.id}
              className="flex items-center gap-3 py-2 px-2 -mx-2 rounded-xl transition-colors hover:bg-muted/40 dark:hover:bg-white/[0.03]"
            >
              <div className="w-8 h-8 rounded-lg bg-muted/50 dark:bg-white/[0.05] flex items-center justify-center shrink-0">
                <FileText className="w-3.5 h-3.5 text-muted-foreground" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-foreground truncate">{doc.title}</p>
                <p className="text-[10px] text-muted-foreground truncate">
                  {doc.project_id == null ? "General Library" : "Project document"} · {doc.doc_type}
                </p>
              </div>
              <span className="text-[10px] text-muted-foreground shrink-0 tabular-nums">
                {formatRelativeTime(doc.doc_date)}
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="px-5 py-3 border-t border-border/60 dark:border-white/[0.05]">
        <Link href="/documents" className="text-xs font-medium text-primary hover:underline">
          View all documents →
        </Link>
      </div>
    </div>
  );
}
