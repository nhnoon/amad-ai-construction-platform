import { Link } from "wouter";
import { ExternalLink, Link2, Tag, User, Calendar } from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import type { MemoryItem } from "@/lib/mockProjectMemory";
import { SOURCE_META, RISK_TONE, STATUS_BADGE, DemoDataBadge, formatDateTime } from "./shared";

// Detail drawer for a single memory item — the "zoom in" counterpart to the
// timeline/cards/graph, all of which only show a summary. Also renders the
// item's Connected Events (its related items) so a user can walk the same
// storyline the relationship graph draws, without leaving the drawer.

export function MemoryDetailDrawer({
  item,
  allItems,
  open,
  onOpenChange,
  onSelectRelated,
}: {
  item: MemoryItem | null;
  allItems: MemoryItem[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectRelated: (item: MemoryItem) => void;
}) {
  if (!item) return null;
  const meta = SOURCE_META[item.sourceType];
  const Icon = meta.icon;
  const related = item.relatedIds
    .map((id) => allItems.find((i) => i.id === id))
    .filter((i): i is MemoryItem => !!i);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader className="text-start space-y-3">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`badge ${STATUS_BADGE[item.status]}`}>{item.status}</span>
            <span className="rounded-full border px-2 py-0.5 text-[10px] font-medium border-border text-muted-foreground">
              {item.category}
            </span>
            {item.riskLevel && (
              <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${RISK_TONE[item.riskLevel]}`}>
                {item.riskLevel} risk
              </span>
            )}
            <DemoDataBadge />
          </div>
          <div className="flex items-start gap-2.5">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5" style={{ backgroundColor: `${meta.color}1a` }}>
              <Icon className="w-4 h-4" style={{ color: meta.color }} />
            </div>
            <SheetTitle className="text-lg leading-snug">{item.title}</SheetTitle>
          </div>
          <SheetDescription className="text-sm text-foreground/80 leading-relaxed">
            {item.detail}
          </SheetDescription>
        </SheetHeader>

        <div className="mt-5 space-y-5">
          {/* Meta row */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Calendar className="w-3.5 h-3.5" /> {formatDateTime(item.date)}
            </div>
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <User className="w-3.5 h-3.5" /> {item.author}
            </div>
          </div>

          {/* Tags */}
          {item.tags.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Tag className="w-3 h-3" /> Tags
              </p>
              <div className="flex flex-wrap gap-1.5">
                {item.tags.map((t) => (
                  <span key={t} className="text-[10px] rounded-full bg-muted px-2 py-0.5 text-muted-foreground">#{t}</span>
                ))}
              </div>
            </div>
          )}

          {/* Source citations */}
          {item.citations.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Source References</p>
              <ul className="space-y-1.5">
                {item.citations.map((c, i) => (
                  <li key={i} className="rounded-lg border border-border/60 bg-muted/30 px-3 py-2 text-xs flex items-center justify-between gap-2">
                    <span className="text-foreground/80">{c.label}</span>
                    {c.href ? (
                      <Link href={c.href} className="inline-flex items-center gap-1 text-primary hover:underline shrink-0">
                        Open <ExternalLink className="w-3 h-3" />
                      </Link>
                    ) : (
                      <span className="text-muted-foreground shrink-0">{SOURCE_META[c.sourceType].label}</span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Connected events */}
          {related.length > 0 && (
            <div className="space-y-1.5">
              <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                <Link2 className="w-3 h-3" /> Connected Events ({related.length})
              </p>
              <ul className="space-y-1.5">
                {related.map((r) => {
                  const rMeta = SOURCE_META[r.sourceType];
                  const RIcon = rMeta.icon;
                  return (
                    <li key={r.id}>
                      <button
                        type="button"
                        onClick={() => onSelectRelated(r)}
                        className="w-full flex items-start gap-2.5 rounded-lg border border-border/60 hover:border-primary/40 hover:bg-muted/30 transition-colors px-3 py-2 text-start"
                      >
                        <div className="w-6 h-6 rounded-md flex items-center justify-center shrink-0 mt-0.5" style={{ backgroundColor: `${rMeta.color}1a` }}>
                          <RIcon className="w-3.5 h-3.5" style={{ color: rMeta.color }} />
                        </div>
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-foreground truncate">{r.title}</p>
                          <p className="text-[10px] text-muted-foreground">{rMeta.label} &middot; {formatDateTime(r.date)}</p>
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
