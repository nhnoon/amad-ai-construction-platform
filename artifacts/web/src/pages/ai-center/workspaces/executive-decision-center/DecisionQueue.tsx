import { useState } from "react";
import { Link } from "wouter";
import { CheckCircle2, Gavel } from "lucide-react";
import type { DecisionQueueItem, DecisionStatus } from "@/lib/mockExecutiveDecisionCenter";
import { EmptyState } from "@/components/ui/empty-state";
import { MODULE_META, PRIORITY_BADGE, formatDate, formatRelativeDays } from "./shared";

const STATUS_BADGE: Record<DecisionStatus, string> = {
  Overdue: "badge-danger", Pending: "badge-warning", Scheduled: "badge-info",
};

// Executive Decision Queue — every decision awaiting executive sign-off,
// with priority, due date, requester, and estimated impact. "Acknowledge"
// is a session-local UI affordance (not persisted) so the queue feels
// like a working list, not a static report — it does not call a backend.

export function DecisionQueue({ items, referenceIso }: { items: DecisionQueueItem[]; referenceIso: string }) {
  const [acknowledged, setAcknowledged] = useState<Set<string>>(new Set());
  const toggleAck = (id: string) => setAcknowledged((prev) => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });

  if (items.length === 0) {
    return <EmptyState icon={Gavel} title="No decisions pending" description="Nothing is currently awaiting executive sign-off." />;
  }

  return (
    <div className="space-y-2">
      {items.map((item) => {
        const meta = MODULE_META[item.module];
        const Icon = meta.icon;
        const isAck = acknowledged.has(item.id);
        return (
          <div key={item.id} className={`rounded-lg border border-border/60 p-3 space-y-2 ${isAck ? "opacity-60" : ""}`}>
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-start gap-2.5 min-w-0">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5" style={{ backgroundColor: `${meta.color}1a` }}>
                  <Icon className="w-4 h-4" style={{ color: meta.color }} />
                </div>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-foreground">{item.title}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{item.description}</p>
                </div>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                <span className={`badge ${PRIORITY_BADGE[item.priority]} text-[10px]`}>{item.priority}</span>
                <span className={`badge ${STATUS_BADGE[item.status]} text-[10px]`}>{item.status}</span>
              </div>
            </div>
            <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground">
              <span>Requested by {item.requestedBy} &middot; {item.estimatedImpact}</span>
              <span>{formatRelativeDays(item.dueDate, referenceIso)} &middot; {formatDate(item.dueDate)}</span>
            </div>
            <div className="flex items-center justify-between gap-2 pt-1 border-t border-border/50">
              <Link href={item.href} className="text-xs text-primary hover:underline">{item.module}</Link>
              <button
                type="button"
                onClick={() => toggleAck(item.id)}
                className={`inline-flex items-center gap-1.5 text-xs font-medium transition-colors ${isAck ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground hover:text-foreground"}`}
              >
                <CheckCircle2 className={`w-3.5 h-3.5 ${isAck ? "fill-current" : ""}`} />
                {isAck ? "Acknowledged" : "Acknowledge"}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
