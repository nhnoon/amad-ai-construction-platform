import { useEffect, useState } from "react";
import {
  useListProjects, useListProjectMeetings, useListProjectDecisions,
} from "@workspace/api-client-react";
import { Link } from "wouter";
import { CalendarDays, ChevronRight, ExternalLink, Gavel } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";

const TYPE_BADGE: Record<string, string> = {
  Weekly: "badge-info", Technical: "badge-purple", Safety: "badge-warning", Commercial: "badge-gold",
};

// Meeting Intelligence workspace — recent meetings + decisions for a
// project, both reused from the same generated hooks meetings.tsx already
// uses. Full CRUD (create meeting, action items) stays at /meetings; this
// is the AI-angle summary + entry point.
export default function MeetingIntelligence() {
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const { data: projects } = useListProjects({ limit: 60 });

  useEffect(() => {
    if (projects && projects.length > 0 && !selectedProjectId) setSelectedProjectId(projects[0].id);
  }, [projects, selectedProjectId]);

  const { data: meetings, isLoading: meetingsLoading } = useListProjectMeetings(
    selectedProjectId ?? 0, { limit: 6 },
    { query: { enabled: !!selectedProjectId, queryKey: ["ai-center-meetings", selectedProjectId] } },
  );
  const { data: decisions, isLoading: decisionsLoading } = useListProjectDecisions(
    selectedProjectId ?? 0, { limit: 5 },
    { query: { enabled: !!selectedProjectId, queryKey: ["ai-center-decisions", selectedProjectId] } },
  );

  const isLoading = meetingsLoading || decisionsLoading;

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Meeting Intelligence</h2>
          <p className="text-sm text-muted-foreground">Recent meetings, extracted decisions, and action items per project.</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={selectedProjectId ? String(selectedProjectId) : ""} onValueChange={(v) => setSelectedProjectId(Number(v))}>
            <SelectTrigger className="w-64 h-9"><SelectValue placeholder="Select project" /></SelectTrigger>
            <SelectContent>
              {projects?.map((p) => (
                <SelectItem key={p.id} value={String(p.id)}>{p.project_code} — {p.project_name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Link href="/meetings" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline whitespace-nowrap">
            All meetings <ExternalLink className="w-3 h-3" />
          </Link>
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Recent Meetings</p>
            {!meetings?.length ? (
              <EmptyState icon={CalendarDays} title="No meetings yet" />
            ) : (
              meetings.map((m) => (
                <Link
                  key={m.id}
                  href={`/meetings/${m.project_id}/${m.id}`}
                  className="flex items-center justify-between gap-3 rounded-xl border border-border bg-card p-3 hover:border-primary/30 transition-colors group"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">{m.title}</p>
                    <p className="text-xs text-muted-foreground">{m.meeting_date}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`badge ${TYPE_BADGE[m.meeting_type] ?? "badge-neutral"}`}>{m.meeting_type}</span>
                    <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:translate-x-0.5 transition-transform" />
                  </div>
                </Link>
              ))
            )}
          </div>

          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Recent Decisions</p>
            {!decisions?.length ? (
              <EmptyState icon={Gavel} title="No decisions logged" />
            ) : (
              decisions.map((d) => (
                <div key={d.id} className="rounded-xl border border-border bg-card p-3">
                  <p className="text-sm text-foreground">{d.decision_text}</p>
                  <p className="text-xs text-muted-foreground mt-1">{d.decision_date} &middot; {d.owner}</p>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
