import { CalendarClock } from "lucide-react";
import { Link } from "wouter";
import type { TimelineEvent } from "@/lib/mockPredictiveIntelligence";
import { EmptyState } from "@/components/ui/empty-state";
import { CATEGORY_META, BAND_BADGE, formatDate, formatRelativeDays } from "./shared";

// Project Prediction Timeline — forward-looking, not historical: the next
// dated moments the model expects each category's risk to peak. Shared by
// both the portfolio view (merged across projects) and a single project's
// own view (already pre-filtered by the caller).

export function PredictionTimeline({
  events,
  referenceIso,
  showProject = true,
}: {
  events: TimelineEvent[];
  referenceIso: string;
  showProject?: boolean;
}) {
  if (events.length === 0) {
    return <EmptyState icon={CalendarClock} title="No upcoming risk events forecast" description="Nothing is predicted to peak in the current window." />;
  }

  return (
    <div className="relative ps-6 border-s-2 border-border space-y-4">
      {events.map((event) => {
        const meta = CATEGORY_META[event.category];
        const Icon = meta.icon;
        return (
          <div key={event.id} className="relative">
            <div className="absolute -start-[31px] top-0.5 w-3 h-3 rounded-full" style={{ backgroundColor: meta.color }} />
            <div className="panel panel-body space-y-1.5">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-1.5">
                  <Icon className="w-3.5 h-3.5" style={{ color: meta.color }} />
                  <span className="text-xs font-semibold text-foreground">{meta.label}</span>
                  <span className={`badge ${BAND_BADGE[event.severity]} text-[10px]`}>{event.severity}</span>
                </div>
                <span className="text-[11px] text-muted-foreground">{formatRelativeDays(event.date, referenceIso)} &middot; {formatDate(event.date)}</span>
              </div>
              <p className="text-sm text-foreground leading-relaxed">{event.description}</p>
              {showProject && (
                <Link href={`/projects/${event.projectId}`} className="text-[11px] text-primary hover:underline">
                  {event.projectCode} &middot; {event.projectName}
                </Link>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
