import { Sparkles, ListChecks, FileSearch, Target, BookOpen, ChevronDown, ChevronUp, Brain } from "lucide-react";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import type { CopilotQueryResponse, CopilotCitation } from "@/lib/copilotClient";
import { SOURCE_TYPE_LABELS, prettifySourceType } from "@/components/ai-answer-ui";
import { getMemory } from "@/lib/aiCenterClient";

// Phase 2 §6 — every Hermes response follows the same professional shape:
// Executive Summary / Key Findings / Evidence / Recommendations / Sources,
// instead of a long conversational paragraph. Reuses fields the backend
// already returns (answer/short_summary, key_findings, citations incl.
// evidence_snippet, follow_up_suggestions) — no new backend field, no new
// endpoint. Light-theme counterpart to AIDrawer's dark-glass AiAnswerCard
// (kept separate rather than shared, since the two surfaces have different
// visual languages — see AIDrawer.tsx for that one).

function Section({ icon: Icon, title, children }: { icon: React.ElementType; title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5">
        <Icon className="h-3.5 w-3.5 text-primary" />
        <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">{title}</p>
      </div>
      {children}
    </div>
  );
}

function EvidenceList({ citations }: { citations: CopilotCitation[] }) {
  const withSnippet = citations.filter((c) => c.evidence_snippet);
  if (!withSnippet.length) return null;
  return (
    <ul className="space-y-1.5">
      {withSnippet.slice(0, 4).map((c) => (
        <li key={c.id} className="rounded-lg border border-border/60 bg-muted/30 px-3 py-2 text-xs text-foreground/80 leading-relaxed">
          <span className="font-mono text-[10px] text-primary/80 me-1.5">{c.label}</span>
          {c.evidence_snippet}
        </li>
      ))}
    </ul>
  );
}

function SourcesList({ citations }: { citations: CopilotCitation[] }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  if (!citations.length) return null;
  const groups = new Map<string, CopilotCitation[]>();
  for (const c of citations) {
    const key = c.source_type || "other";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(c);
  }
  const toggle = (key: string) => setExpanded((prev) => {
    const next = new Set(prev);
    next.has(key) ? next.delete(key) : next.add(key);
    return next;
  });
  return (
    <div className="grid grid-cols-2 gap-1.5">
      {Array.from(groups.entries()).map(([type, items]) => {
        const label = SOURCE_TYPE_LABELS[type]?.en ?? prettifySourceType(type);
        const isOpen = expanded.has(type);
        return (
          <div key={type} className="rounded-lg border border-border/60 overflow-hidden">
            <button
              type="button"
              onClick={() => toggle(type)}
              className="w-full flex items-center justify-between gap-1.5 px-2.5 py-1.5 text-start hover:bg-muted/40 transition-colors"
            >
              <span className="text-xs font-medium text-foreground truncate">{label}</span>
              <span className="flex items-center gap-1 text-[10px] text-muted-foreground shrink-0">
                {items.length}
                {isOpen ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              </span>
            </button>
            {isOpen && (
              <ul className="px-2.5 pb-2 space-y-1 text-[11px] text-muted-foreground">
                {items.map((c) => {
                  const href = (c.ui_metadata as Record<string, unknown> | undefined)?.href as string | undefined;
                  return (
                    <li key={c.id} className="truncate">
                      {href ? <Link href={href} className="hover:underline text-primary">{c.label}</Link> : c.label}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        );
      })}
    </div>
  );
}

// Knowledge Panel — Related Memories (Phase 2 §9). The backend's citations
// array doesn't include memory-sourced items (structured memory is
// injected into the Hermes prompt as a labeled text block, not as
// individual Citation rows — see app/ai/memory_records.py), so this
// queries the same GET /api/v1/ai/memory endpoint the Memory Center uses
// and matches client-side against the entity codes this answer already
// cites — real, already-fetched data, no fabrication, no backend change.
function RelatedMemories({ citations }: { citations: CopilotCitation[] }) {
  const { data } = useQuery({ queryKey: ["ai-center-memory"], queryFn: getMemory });
  const codes = new Set(citations.map((c) => c.source_id).filter(Boolean));
  const related = (data?.structured_memories ?? []).filter((m) =>
    (m.citation && codes.has(m.citation)) || m.keywords.some((k) => codes.has(k)),
  ).slice(0, 3);
  if (!related.length) return null;
  return (
    <Section icon={Brain} title="Related Memories">
      <ul className="space-y-1.5">
        {related.map((m) => (
          <li key={m.id} className="rounded-lg border border-border/60 bg-violet-500/[0.04] px-3 py-2">
            <p className="text-xs font-medium text-foreground">{m.title}</p>
            <p className="text-[11px] text-muted-foreground line-clamp-1">{m.summary}</p>
          </li>
        ))}
      </ul>
    </Section>
  );
}

export function AIAnswerStructured({ response, title }: { response: CopilotQueryResponse; title?: string }) {
  const summary = response.short_summary || response.answer;
  const recommendations = response.follow_up_suggestions ?? [];
  return (
    <div className="panel panel-body space-y-4">
      {title && <p className="text-sm font-semibold text-foreground">{title}</p>}

      <Section icon={Sparkles} title="Executive Summary">
        <p className="text-sm text-foreground leading-relaxed">{summary}</p>
      </Section>

      {!!response.key_findings?.length && (
        <Section icon={ListChecks} title="Key Findings">
          <ul className="space-y-1">
            {response.key_findings.map((f, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-foreground">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary" />
                {f}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {response.citations.some((c) => c.evidence_snippet) && (
        <Section icon={FileSearch} title="Evidence">
          <EvidenceList citations={response.citations} />
        </Section>
      )}

      <RelatedMemories citations={response.citations} />

      {recommendations.length > 0 && (
        <Section icon={Target} title="Recommendations">
          <ul className="space-y-1">
            {recommendations.slice(0, 3).map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-foreground">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary" />
                {r}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {response.citations.length > 0 && (
        <Section icon={BookOpen} title="Sources">
          <SourcesList citations={response.citations} />
        </Section>
      )}
    </div>
  );
}
