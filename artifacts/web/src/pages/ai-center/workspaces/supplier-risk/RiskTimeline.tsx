import { AlertTriangle, FileSignature, CalendarClock } from "lucide-react";
import type { SupplierRiskSnapshot } from "@/lib/mockSupplierRisk";
import { EmptyState } from "@/components/ui/empty-state";
import { BAND_BADGE, formatDate, formatRelativeDays } from "./shared";

// Risk Timeline — open supplier issues and upcoming contract expirations,
// merged into one chronological view so nothing time-sensitive gets missed
// by only looking at the directory table.

export function RiskTimeline({
  events,
  referenceIso,
}: {
  events: SupplierRiskSnapshot["riskTimeline"];
  referenceIso: string;
}) {
  if (events.length === 0) {
    return <EmptyState icon={CalendarClock} title="Nothing time-sensitive right now" description="No open issues or near-term contract expirations." />;
  }

  return (
    <div className="relative ps-6 border-s-2 border-border space-y-3">
      {events.slice(0, 16).map((event) => {
        const Icon = event.type === "issue" ? AlertTriangle : FileSignature;
        const dotColor = event.type === "issue" ? "#dc2626" : "#f59e0b";
        return (
          <div key={event.id} className="relative">
            <div className="absolute -start-[31px] top-0.5 w-3 h-3 rounded-full" style={{ backgroundColor: dotColor }} />
            <div className="panel panel-body space-y-1">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-1.5">
                  <Icon className="w-3.5 h-3.5" style={{ color: dotColor }} />
                  <span className="text-xs font-semibold text-foreground">{event.type === "issue" ? "Open Issue" : "Contract Expiring"}</span>
                  <span className={`badge ${BAND_BADGE[event.severity]} text-[10px]`}>{event.severity}</span>
                </div>
                <span className="text-[11px] text-muted-foreground">{formatRelativeDays(event.date, referenceIso)} &middot; {formatDate(event.date)}</span>
              </div>
              <p className="text-sm text-foreground">{event.title}</p>
              <p className="text-[11px] text-muted-foreground">{event.supplierName}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
