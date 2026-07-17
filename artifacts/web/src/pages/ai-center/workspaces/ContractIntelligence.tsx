import { useQuery } from "@tanstack/react-query";
import { Link } from "wouter";
import { FileSignature, ExternalLink } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import { getMemory } from "@/lib/aiCenterClient";
import { bucketFor } from "../memoryTaxonomy";

// Contract Intelligence workspace — every completed contract extraction is
// already written to structured memory (app/ai/contract_extraction.py's
// writer, source="contract"); this reuses that same data rather than
// adding a new bulk contract-listing endpoint. Full document + extraction
// detail (fields, risks, obligations) stays on the Documents page.
export default function ContractIntelligence() {
  const { data, isLoading } = useQuery({ queryKey: ["ai-center-memory"], queryFn: getMemory });

  const contracts = (data?.structured_memories ?? []).filter(
    (m) => bucketFor(m.source, m.category) === "contract",
  );

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Contract Intelligence</h2>
          <p className="text-sm text-muted-foreground">Completed contract extractions — value, obligations, and flagged risks.</p>
        </div>
        <Link href="/documents" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline whitespace-nowrap">
          Open Documents <ExternalLink className="w-3 h-3" />
        </Link>
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}
        </div>
      ) : !contracts.length ? (
        <EmptyState
          icon={FileSignature}
          title="No contract extractions yet"
          description="Run contract analysis on an uploaded document (Documents workspace) to populate this view."
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {contracts.map((c) => (
            <div key={c.id} className="rounded-xl border border-border bg-card p-4 space-y-2">
              <div className="flex items-start gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                  <FileSignature className="w-4 h-4 text-primary" />
                </div>
                <div className="min-w-0">
                  <h4 className="font-semibold text-sm text-foreground truncate">{c.title}</h4>
                  <p className="text-[11px] text-muted-foreground">
                    {new Date(c.created_at).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
                  </p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground line-clamp-3">{c.summary}</p>
              <div className="flex flex-wrap gap-1.5">
                {c.project_code && <Badge variant="outline" className="text-[10px]">{c.project_code}</Badge>}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
