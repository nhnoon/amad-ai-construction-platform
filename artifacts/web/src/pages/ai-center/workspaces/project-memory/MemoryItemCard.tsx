import type { MemoryItem } from "@/lib/mockProjectMemory";
import { SOURCE_META, RISK_TONE, STATUS_BADGE, formatDate } from "./shared";

// One shared row/card for a MemoryItem — used by the Recent Knowledge
// Cards grid, the Decisions section, the Open Actions & Approvals lists,
// and the chronological timeline (via `compact`). Keeping this in one
// component means every surface that shows a memory item agrees on layout
// instead of four near-identical hand-rolled cards.

export function MemoryItemCard({
  item,
  onSelect,
  compact = false,
}: {
  item: MemoryItem;
  onSelect: (item: MemoryItem) => void;
  compact?: boolean;
}) {
  const meta = SOURCE_META[item.sourceType];
  const Icon = meta.icon;

  return (
    <button
      type="button"
      onClick={() => onSelect(item)}
      className={`panel panel-body w-full text-start space-y-2 hover:border-primary/30 hover:-translate-y-0.5 transition-all duration-150 ${compact ? "py-2.5" : ""}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2.5 min-w-0">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
            style={{ backgroundColor: `${meta.color}1a` }}
          >
            <Icon className="w-4 h-4" style={{ color: meta.color }} />
          </div>
          <div className="min-w-0">
            <h4 className="font-semibold text-foreground text-sm leading-snug line-clamp-2">{item.title}</h4>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {meta.label} &middot; {formatDate(item.date)} &middot; {item.author}
            </p>
          </div>
        </div>
        <span className={`badge ${STATUS_BADGE[item.status]} text-[10px] shrink-0`}>{item.status}</span>
      </div>

      {!compact && (
        <p className="text-sm text-muted-foreground leading-relaxed line-clamp-2">{item.summary}</p>
      )}

      <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
        <span className="rounded-full border px-2 py-0.5 text-[10px] font-medium border-border text-muted-foreground">
          {item.category}
        </span>
        {item.riskLevel && (
          <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${RISK_TONE[item.riskLevel]}`}>
            {item.riskLevel} risk
          </span>
        )}
        {item.citations.length > 0 && (
          <span className="text-[10px] text-muted-foreground">
            {item.citations.length} source{item.citations.length === 1 ? "" : "s"}
          </span>
        )}
      </div>
    </button>
  );
}
