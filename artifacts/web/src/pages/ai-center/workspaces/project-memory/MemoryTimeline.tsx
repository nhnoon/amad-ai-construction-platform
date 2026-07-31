import { useMemo } from "react";
import type { MemoryItem } from "@/lib/mockProjectMemory";
import { MemoryItemCard } from "./MemoryItemCard";

// Unified chronological memory timeline — groups already-filtered/sorted
// items by day, same grouped-timeline shape as MemoryCenter's own timeline
// view (ai-center/MemoryCenter.tsx), reused here because it's the right
// visual for "everything that happened, in order" across a mixed set of
// source types.

export function MemoryTimeline({
  items,
  onSelect,
}: {
  items: MemoryItem[];
  onSelect: (item: MemoryItem) => void;
}) {
  const groups = useMemo(() => {
    const map = new Map<string, MemoryItem[]>();
    for (const item of items) {
      const label = new Date(item.date).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
      const list = map.get(label) ?? [];
      list.push(item);
      map.set(label, list);
    }
    return Array.from(map.entries());
  }, [items]);

  return (
    <div className="space-y-6">
      {groups.map(([dateLabel, dayItems]) => (
        <div key={dateLabel} className="relative ps-6 border-s-2 border-border">
          <div className="absolute -start-[7px] top-0.5 w-3 h-3 rounded-full bg-primary" />
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-3">
            {dateLabel} <span className="normal-case font-normal">&middot; {dayItems.length} item{dayItems.length === 1 ? "" : "s"}</span>
          </p>
          <div className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-3">
            {dayItems.map((item) => (
              <MemoryItemCard key={item.id} item={item} onSelect={onSelect} compact />
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
