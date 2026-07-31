import { Link } from "wouter";
import { Clock3 } from "lucide-react";
import type { PriorityItem, Urgency } from "@/lib/mockExecutiveDecisionCenter";
import { EmptyState } from "@/components/ui/empty-state";
import { MODULE_META } from "./shared";

const URGENCY_TONE: Record<Urgency, string> = {
  Today: "text-red-600 dark:text-red-400",
  "This Week": "text-amber-600 dark:text-amber-400",
  "This Month": "text-muted-foreground",
};

// Today's Priorities — the short, ranked "what needs my attention today"
// list. Deliberately terse (title + one line), each linking straight into
// the source module for the full picture.

export function TodaysPriorities({ items }: { items: PriorityItem[] }) {
  if (items.length === 0) {
    return <EmptyState icon={Clock3} title="Nothing urgent today" description="No priority items are flagged for today." />;
  }

  return (
    <div className="space-y-2">
      {items.map((item) => {
        const meta = MODULE_META[item.module];
        const Icon = meta.icon;
        return (
          <Link key={item.id} href={item.href} className="rounded-lg border border-border/60 p-3 flex items-start gap-3 hover:border-primary/30 transition-colors">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5" style={{ backgroundColor: `${meta.color}1a` }}>
              <Icon className="w-4 h-4" style={{ color: meta.color }} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-foreground truncate">{item.title}</p>
                <span className={`text-[11px] font-bold uppercase tracking-wide shrink-0 ${URGENCY_TONE[item.urgency]}`}>{item.urgency}</span>
              </div>
              <p className="text-xs text-muted-foreground line-clamp-1">{item.description}</p>
              <p className="text-[10px] text-muted-foreground mt-0.5">{item.module}{item.projectCode ? ` · ${item.projectCode}` : ""}</p>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
