import { useMemo } from "react";
import type { KnowledgeItem } from "@/lib/mockCrossProjectLearning";
import { EmptyState } from "@/components/ui/empty-state";
import { History } from "lucide-react";
import { KnowledgeItemCard } from "./KnowledgeItemCard";

// Timeline View — chronological knowledge history, grouped by month, same
// grouped-timeline shape used across the other AI Center workspaces
// (Project Memory's MemoryTimeline, Predictive Intelligence's
// PredictionTimeline) so this reads as one consistent pattern.

export function KnowledgeTimeline({ items, onSelect }: { items: KnowledgeItem[]; onSelect: (item: KnowledgeItem) => void }) {
  const groups = useMemo(() => {
    const map = new Map<string, KnowledgeItem[]>();
    for (const item of items) {
      const label = new Date(item.date).toLocaleDateString(undefined, { year: "numeric", month: "long" });
      const list = map.get(label) ?? [];
      list.push(item);
      map.set(label, list);
    }
    return Array.from(map.entries());
  }, [items]);

  if (items.length === 0) {
    return <EmptyState icon={History} title="No knowledge items match the current filters" />;
  }

  return (
    <div className="space-y-6">
      {groups.map(([label, monthItems]) => (
        <div key={label} className="relative ps-6 border-s-2 border-border">
          <div className="absolute -start-[7px] top-0.5 w-3 h-3 rounded-full bg-primary" />
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
            {label} <span className="normal-case font-normal">&middot; {monthItems.length} item{monthItems.length === 1 ? "" : "s"}</span>
          </p>
          <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
            {monthItems.map((item) => <KnowledgeItemCard key={item.id} item={item} onSelect={onSelect} compact />)}
          </div>
        </div>
      ))}
    </div>
  );
}
