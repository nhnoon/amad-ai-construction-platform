import { useState } from "react";
import { ChevronDown, ChevronUp, AlertTriangle, FileText, Gavel, ListChecks, Target } from "lucide-react";
import type { KnowledgeItem } from "@/lib/mockCrossProjectLearning";
import { CATEGORY_META, SOURCE_TYPE_META, RISK_BADGE, OUTCOME_BADGE, confidenceTone, formatDate } from "./shared";

// One shared card for a KnowledgeItem — used by Search Results, the
// Knowledge Timeline, and Similar Cases inside the drawer. `compact` drops
// the summary/expand affordance for list contexts that just need a row.
// `similarity` overlays a match-score badge when rendered inside a
// Similar Cases list.

export function KnowledgeItemCard({
  item,
  onSelect,
  compact = false,
  similarity,
}: {
  item: KnowledgeItem;
  onSelect: (item: KnowledgeItem) => void;
  compact?: boolean;
  similarity?: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const catMeta = CATEGORY_META[item.category];
  const CatIcon = catMeta.icon;
  const sourceMeta = SOURCE_TYPE_META[item.sourceType];

  return (
    <div className="panel panel-body space-y-2.5">
      <div className="flex items-start justify-between gap-2">
        <button type="button" onClick={() => onSelect(item)} className="flex items-start gap-2.5 min-w-0 text-start hover:opacity-80 transition-opacity">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
            <CatIcon className="w-4 h-4 text-primary" />
          </div>
          <div className="min-w-0">
            <h4 className="font-semibold text-foreground text-sm leading-snug">{item.title}</h4>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              {item.projectCode} &middot; {item.category} &middot; {sourceMeta.label} &middot; {formatDate(item.date)}
            </p>
          </div>
        </button>
        <div className="text-end shrink-0 space-y-1">
          {similarity !== undefined && (
            <p className="text-xs font-bold text-primary tabular-nums">{similarity}% match</p>
          )}
          <p className={`text-[11px] font-semibold tabular-nums ${confidenceTone(item.confidence)}`}>{item.confidence}% confidence</p>
        </div>
      </div>

      {!compact && <p className="text-sm text-muted-foreground leading-relaxed line-clamp-2">{item.summary}</p>}

      <div className="flex flex-wrap items-center gap-1.5">
        <span className={`badge ${RISK_BADGE[item.riskLevel]} text-[10px]`}>{item.riskLevel} risk</span>
        <span className={`badge ${OUTCOME_BADGE[item.outcome]} text-[10px]`}>{item.outcome}</span>
        {item.supplierName && <span className="text-[10px] text-muted-foreground">{item.supplierName}</span>}
      </div>

      {!compact && (
        <button type="button" onClick={() => setExpanded((e) => !e)} className="flex items-center gap-1.5 text-xs font-medium text-primary hover:text-primary/80 transition-colors">
          {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          {expanded ? "Hide related items" : "Related risks, documents, decisions & actions"}
        </button>
      )}

      {!compact && expanded && (
        <div className="space-y-2 pt-1 border-t border-border/50 text-xs">
          <div className="flex items-start gap-1.5"><AlertTriangle className="w-3 h-3 text-muted-foreground shrink-0 mt-0.5" /><span className="text-muted-foreground">{item.relatedRisks.join(", ")}</span></div>
          <div className="flex items-start gap-1.5"><FileText className="w-3 h-3 text-muted-foreground shrink-0 mt-0.5" /><span className="text-muted-foreground">{item.citations.map((c) => c.label).join(", ")}</span></div>
          <div className="flex items-start gap-1.5"><Gavel className="w-3 h-3 text-muted-foreground shrink-0 mt-0.5" /><span className="text-muted-foreground">{item.relatedDecisions.join("; ")}</span></div>
          <div className="flex items-start gap-1.5"><ListChecks className="w-3 h-3 text-muted-foreground shrink-0 mt-0.5" /><span className="text-muted-foreground">{item.relatedActions.join("; ")}</span></div>
          <div className="flex items-start gap-1.5 rounded-lg bg-primary/5 border border-primary/10 px-2.5 py-2">
            <Target className="w-3 h-3 text-primary shrink-0 mt-0.5" />
            <span className="text-foreground">{item.recommendation}</span>
          </div>
        </div>
      )}
    </div>
  );
}
