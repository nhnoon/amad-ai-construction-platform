import { useMemo, useState } from "react";
import { Link } from "wouter";
import {
  Sparkles, Target, FileSearch, GitCompare, Link2, ExternalLink,
  AlertTriangle, Gavel, ListChecks, CheckCircle2, XCircle,
} from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { EmptyState } from "@/components/ui/empty-state";
import { PageTabs } from "@/components/page-tabs";
import { findSimilarCases, type CitationKind, type KnowledgeItem } from "@/lib/mockCrossProjectLearning";
import {
  CATEGORY_META, SOURCE_TYPE_META, RISK_BADGE, OUTCOME_BADGE, DemoDataBadge,
  confidenceTone, formatDate,
} from "./shared";
import { KnowledgeItemCard } from "./KnowledgeItemCard";

type DrawerTab = "overview" | "timeline" | "similar" | "ai";

const CITATION_GROUP_LABEL: Record<CitationKind, string> = {
  document: "Documents", meeting: "Meetings", approval: "Approvals", claim: "Claims",
};

export function KnowledgeDetailDrawer({
  item,
  allItems,
  open,
  onOpenChange,
  onSelectItem,
}: {
  item: KnowledgeItem | null;
  allItems: KnowledgeItem[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelectItem: (item: KnowledgeItem) => void;
}) {
  const [tab, setTab] = useState<DrawerTab>("overview");
  const [compareIds, setCompareIds] = useState<Set<string>>(new Set());

  const similar = useMemo(() => (item ? findSimilarCases(allItems, item) : []), [item, allItems]);
  const connectedEvents = useMemo(
    () => (item ? item.connectedIds.map((id) => allItems.find((i) => i.id === id)).filter((i): i is KnowledgeItem => !!i) : []),
    [item, allItems],
  );

  if (!item) return null;
  const catMeta = CATEGORY_META[item.category];
  const CatIcon = catMeta.icon;
  const sourceMeta = SOURCE_TYPE_META[item.sourceType];

  const citationGroups = new Map<CitationKind, string[]>();
  for (const c of item.citations) citationGroups.set(c.kind, [...(citationGroups.get(c.kind) ?? []), c.label]);

  const compareItems = [item, ...Array.from(compareIds).map((id) => allItems.find((i) => i.id === id)).filter((i): i is KnowledgeItem => !!i)];
  const toggleCompare = (id: string) => setCompareIds((prev) => {
    const next = new Set(prev);
    if (next.has(id)) next.delete(id);
    else if (next.size < 2) next.add(id);
    return next;
  });

  const successfulSolutions = Array.from(new Set(similar.filter((s) => s.item.outcome === "Successful").map((s) => s.item.resolution)));
  const failedSolutions = Array.from(new Set(similar.filter((s) => s.item.outcome === "Unsuccessful").map((s) => s.item.resolution)));
  const commonIssues = Array.from(new Set([item, ...similar.slice(0, 5).map((s) => s.item)].flatMap((i) => i.tags)))
    .filter((tag) => [item, ...similar.map((s) => s.item)].filter((i) => i.tags.includes(tag)).length >= 2);

  return (
    <Sheet open={open} onOpenChange={(o) => { onOpenChange(o); if (!o) { setTab("overview"); setCompareIds(new Set()); } }}>
      <SheetContent className="w-full sm:max-w-xl overflow-y-auto">
        <SheetHeader className="text-start space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`badge ${RISK_BADGE[item.riskLevel]}`}>{item.riskLevel} risk</span>
            <span className={`badge ${OUTCOME_BADGE[item.outcome]}`}>{item.outcome}</span>
            <DemoDataBadge />
          </div>
          <div className="flex items-start gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 mt-0.5"><CatIcon className="w-4 h-4 text-primary" /></div>
            <SheetTitle className="text-lg leading-snug">{item.title}</SheetTitle>
          </div>
          <SheetDescription className="text-xs">
            <Link href={`/projects/${item.projectId}`} className="text-primary hover:underline">{item.projectCode} — {item.projectName}</Link>
            {" "}&middot; {item.category} &middot; {sourceMeta.label} &middot; {formatDate(item.date)}
            {" "}&middot; <span className={confidenceTone(item.confidence)}>{item.confidence}% confidence</span>
          </SheetDescription>
        </SheetHeader>

        <div className="mt-4">
          <PageTabs<DrawerTab>
            tabs={[
              { id: "overview", label: "Overview" },
              { id: "timeline", label: "Timeline & Connections", count: connectedEvents.length },
              { id: "similar", label: "Similar Cases", count: similar.length },
              { id: "ai", label: "AI Insights" },
            ]}
            value={tab}
            onChange={setTab}
          />
        </div>

        <div className="mt-4 space-y-5">
          {tab === "overview" && (
            <>
              <p className="text-sm text-foreground leading-relaxed">{item.summary}</p>
              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><AlertTriangle className="w-3 h-3" /> Root Cause</p>
                <p className="text-sm text-foreground/90 rounded-lg border border-border/60 px-3 py-2">{item.rootCause}</p>
              </div>
              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Gavel className="w-3 h-3" /> Resolution</p>
                <p className="text-sm text-foreground/90 rounded-lg border border-border/60 px-3 py-2">{item.resolution}</p>
              </div>
              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><FileSearch className="w-3 h-3" /> Evidence</p>
                <ul className="space-y-1">
                  {item.evidence.map((e, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/50" /> {e}</li>
                  ))}
                </ul>
              </div>
              <div className="rounded-lg bg-primary/5 border border-primary/10 px-3 py-2.5 space-y-1">
                <p className="text-[11px] font-bold uppercase tracking-wider text-primary flex items-center gap-1.5"><Target className="w-3 h-3" /> Recommendation</p>
                <p className="text-sm text-foreground">{item.recommendation}</p>
              </div>
              <div className="grid grid-cols-1 gap-2 text-xs">
                <p className="text-muted-foreground"><span className="font-semibold text-foreground">Related risks:</span> {item.relatedRisks.join(", ")}</p>
                <p className="text-muted-foreground"><span className="font-semibold text-foreground">Related decisions:</span> {item.relatedDecisions.join("; ")}</p>
                <p className="text-muted-foreground"><span className="font-semibold text-foreground">Related actions:</span> {item.relatedActions.join("; ")}</p>
              </div>
            </>
          )}

          {tab === "timeline" && (
            <>
              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Timeline</p>
                <div className="relative ps-5 border-s-2 border-border space-y-3">
                  {item.timeline.map((t, i) => (
                    <div key={i} className="relative">
                      <div className="absolute -start-[25px] top-0.5 w-2.5 h-2.5 rounded-full bg-primary" />
                      <p className="text-xs text-muted-foreground">{formatDate(t.date)}</p>
                      <p className="text-sm text-foreground">{t.label}</p>
                    </div>
                  ))}
                </div>
              </div>

              {Array.from(citationGroups.entries()).map(([kind, labels]) => (
                <div key={kind} className="space-y-1">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">{CITATION_GROUP_LABEL[kind]}</p>
                  <div className="flex flex-wrap gap-1.5">
                    {labels.map((l, i) => <span key={i} className="text-[11px] rounded-full bg-muted px-2.5 py-1 text-muted-foreground">{l}</span>)}
                  </div>
                </div>
              ))}

              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Link2 className="w-3 h-3" /> Connected Events ({connectedEvents.length})</p>
                {connectedEvents.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No connected events for this case.</p>
                ) : (
                  <div className="space-y-2">
                    {connectedEvents.map((e) => <KnowledgeItemCard key={e.id} item={e} onSelect={onSelectItem} compact />)}
                  </div>
                )}
              </div>
            </>
          )}

          {tab === "similar" && (
            <>
              {similar.length === 0 ? (
                <EmptyState icon={GitCompare} title="No similar cases found" description="No other knowledge item shares enough in common with this one." />
              ) : (
                <>
                  <div className="space-y-1.5">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Similar Cases &middot; check up to 2 to compare</p>
                    <div className="space-y-2">
                      {similar.slice(0, 8).map((s) => (
                        <div key={s.item.id} className="flex items-start gap-2">
                          <input
                            type="checkbox"
                            className="w-3.5 h-3.5 accent-primary mt-3"
                            checked={compareIds.has(s.item.id)}
                            onChange={() => toggleCompare(s.item.id)}
                            disabled={!compareIds.has(s.item.id) && compareIds.size >= 2}
                            aria-label={`Compare with ${s.item.title}`}
                          />
                          <div className="flex-1 min-w-0">
                            <KnowledgeItemCard item={s.item} onSelect={onSelectItem} compact similarity={s.score} />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {commonIssues.length > 0 && (
                    <div className="space-y-1.5">
                      <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Common Issues</p>
                      <div className="flex flex-wrap gap-1.5">{commonIssues.map((t) => <span key={t} className="text-[11px] rounded-full bg-muted px-2.5 py-1 text-muted-foreground">#{t}</span>)}</div>
                    </div>
                  )}

                  <div className="grid grid-cols-1 gap-3">
                    <div className="space-y-1.5">
                      <p className="text-[11px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5"><CheckCircle2 className="w-3 h-3" /> Successful Solutions</p>
                      {successfulSolutions.length === 0 ? <p className="text-xs text-muted-foreground">None recorded among similar cases.</p> : (
                        <ul className="space-y-1">{successfulSolutions.map((s, i) => <li key={i} className="text-xs text-foreground/90 rounded-lg border border-emerald-500/20 bg-emerald-500/5 px-2.5 py-1.5">{s}</li>)}</ul>
                      )}
                    </div>
                    <div className="space-y-1.5">
                      <p className="text-[11px] font-bold uppercase tracking-wider text-red-600 dark:text-red-400 flex items-center gap-1.5"><XCircle className="w-3 h-3" /> Failed Solutions</p>
                      {failedSolutions.length === 0 ? <p className="text-xs text-muted-foreground">None recorded among similar cases.</p> : (
                        <ul className="space-y-1">{failedSolutions.map((s, i) => <li key={i} className="text-xs text-foreground/90 rounded-lg border border-red-500/20 bg-red-500/5 px-2.5 py-1.5">{s}</li>)}</ul>
                      )}
                    </div>
                  </div>

                  {compareIds.size > 0 && (
                    <div className="space-y-1.5">
                      <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><GitCompare className="w-3 h-3" /> Comparison View</p>
                      <div className="overflow-x-auto">
                        <table className="data-table" data-testid="knowledge-comparison-table">
                          <thead>
                            <tr><th>Field</th>{compareItems.map((c) => <th key={c.id} className="min-w-[140px] normal-case">{c.projectCode}</th>)}</tr>
                          </thead>
                          <tbody>
                            <tr><td className="text-muted-foreground font-medium">Outcome</td>{compareItems.map((c) => <td key={c.id}><span className={`badge ${OUTCOME_BADGE[c.outcome]} text-[10px]`}>{c.outcome}</span></td>)}</tr>
                            <tr><td className="text-muted-foreground font-medium">Confidence</td>{compareItems.map((c) => <td key={c.id} className="text-sm tabular-nums">{c.confidence}%</td>)}</tr>
                            <tr><td className="text-muted-foreground font-medium">Risk Level</td>{compareItems.map((c) => <td key={c.id}><span className={`badge ${RISK_BADGE[c.riskLevel]} text-[10px]`}>{c.riskLevel}</span></td>)}</tr>
                            <tr><td className="text-muted-foreground font-medium">Root Cause</td>{compareItems.map((c) => <td key={c.id} className="text-xs max-w-[200px]">{c.rootCause}</td>)}</tr>
                            <tr><td className="text-muted-foreground font-medium">Resolution</td>{compareItems.map((c) => <td key={c.id} className="text-xs max-w-[200px]">{c.resolution}</td>)}</tr>
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </>
              )}
            </>
          )}

          {tab === "ai" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <p className="text-sm font-bold text-foreground flex items-center gap-1.5"><Sparkles className="w-4 h-4 text-primary" /> AI Recommendation Panel</p>
                <DemoDataBadge />
              </div>
              <p className="text-xs text-muted-foreground -mt-2">
                Illustrative of the synthesis Hermes would generate once grounded in real cross-project memory — not a live AI call.
              </p>
              <p className="text-sm text-foreground leading-relaxed">
                {similar.length > 0
                  ? `This issue has occurred ${similar.filter((s) => s.item.templateId === item.templateId).length + 1} time${similar.filter((s) => s.item.templateId === item.templateId).length === 0 ? "" : "s"} across ${new Set([item, ...similar.map((s) => s.item)].map((i) => i.projectCode)).size} project${new Set([item, ...similar.map((s) => s.item)].map((i) => i.projectCode)).size === 1 ? "" : "s"}. ${successfulSolutions.length > 0 ? "A successful resolution pattern already exists — reuse it before improvising a new one." : "No confirmed successful resolution exists yet for this issue."}`
                  : "This appears to be an isolated case with no similar precedent found yet."}
              </p>
              <div className="rounded-lg bg-primary/5 border border-primary/10 px-3 py-2.5 space-y-1">
                <p className="text-[11px] font-bold uppercase tracking-wider text-primary">Recommended Action</p>
                <p className="text-sm text-foreground">{item.recommendation}</p>
              </div>
              <Link href={`/projects/${item.projectId}`} className="inline-flex items-center gap-1 text-xs text-primary hover:underline">
                View project <ExternalLink className="w-3 h-3" />
              </Link>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
