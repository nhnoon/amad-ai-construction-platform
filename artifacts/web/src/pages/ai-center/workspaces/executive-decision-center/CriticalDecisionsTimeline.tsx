import { Link } from "wouter";
import { CalendarClock } from "lucide-react";
import type { CriticalTimelineEvent } from "@/lib/mockExecutiveDecisionCenter";
import { EmptyState } from "@/components/ui/empty-state";
import { MODULE_META, RISK_BADGE, formatDate, formatRelativeDays } from "./shared";

// Critical Decisions Timeline — every decision deadline and risk
// checkpoint, in date order, so leadership can see what's converging on
// the same week before it becomes a crunch.

export function CriticalDecisionsTimeline({ events, referenceIso }: { events: CriticalTimelineEvent[]; referenceIso: string }) {
  if (events.length === 0) {
    return <EmptyState icon={CalendarClock} title="Nothing time-sensitive right now" />;
  }

  return (
    <div className="relative ps-6 border-s-2 border-border space-y-3">
      {events.slice(0, 14).map((event) => {
        const meta = MODULE_META[event.module];
        const Icon = meta.icon;
        return (
          <div key={event.id} className="relative">
            <div className="absolute -start-[31px] top-0.5 w-3 h-3 rounded-full" style={{ backgroundColor: meta.color }} />
            <div className="rounded-lg border border-border/60 p-3 space-y-1">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-1.5">
                  <Icon className="w-3.5 h-3.5" style={{ color: meta.color }} />
                  <span className="text-xs font-semibold text-foreground">{event.module}</span>
                  <span className={`badge ${RISK_BADGE[event.severity]} text-[10px]`}>{event.severity}</span>
                </div>
                <span className="text-[11px] text-muted-foreground">{formatRelativeDays(event.date, referenceIso)} &middot; {formatDate(event.date)}</span>
              </div>
              <p className="text-sm text-foreground">{event.title}</p>
              {event.projectCode && <Link href={`/projects/${event.projectId}`} className="text-[11px] text-primary hover:underline">{event.projectCode}</Link>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
