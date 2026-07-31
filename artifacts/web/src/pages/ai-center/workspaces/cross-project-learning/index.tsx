import { useMemo, useState } from "react";
import { useListProjects, useListSuppliers } from "@workspace/api-client-react";
import {
  RotateCcw, BookOpen, Search as SearchIcon, Network, Sparkles, History,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useCrossProjectLearning } from "@/lib/useCrossProjectLearning";
import { searchKnowledge, type KnowledgeItem } from "@/lib/mockCrossProjectLearning";
import { DemoDataBadge } from "./shared";
import { ExecutiveLearningSummary } from "./ExecutiveLearningSummary";
import { KnowledgeSearchBar } from "./KnowledgeSearchBar";
import { FilterBar, DEFAULT_FILTERS, type KnowledgeFilters } from "./FilterBar";
import { KnowledgeItemCard } from "./KnowledgeItemCard";
import { KnowledgeGraph } from "./KnowledgeGraph";
import { KnowledgeTimeline } from "./KnowledgeTimeline";
import { ExecutiveInsights } from "./ExecutiveInsights";
import { KnowledgeDetailDrawer } from "./KnowledgeDetailDrawer";

// ── Cross-Project Learning workspace ────────────────────────────────────
// Answers: has this happened before, what worked, and what should we do
// now. Project and supplier identity is real (useListProjects /
// useListSuppliers, the same endpoints every other picker in the app
// uses); every knowledge item, similarity score, and AI insight is local
// demo data (see lib/mockCrossProjectLearning.ts +
// lib/useCrossProjectLearning.ts) until a real knowledge-retrieval
// backend exists — every surface below is labeled Demo Data / Illustrative
// Knowledge Retrieval, never presented as real semantic/vector search.

function SectionTitle({ icon: Icon, children }: { icon: typeof BookOpen; children: React.ReactNode }) {
  return (
    <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
      <Icon className="w-4 h-4 text-primary" /> {children}
    </h3>
  );
}

function CrossProjectLearningSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
        {[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
      </div>
      <Skeleton className="h-40 w-full rounded-xl" />
      <Skeleton className="h-72 w-full rounded-xl" />
    </div>
  );
}

export default function CrossProjectLearning() {
  const { data: projects, isLoading: projectsLoading, isError: projectsError, refetch: refetchProjects } = useListProjects({ limit: 100 });
  const { data: suppliers } = useListSuppliers({ limit: 100 });

  const { data: snapshot, isLoading, isError, refetch, isRefetching } = useCrossProjectLearning(projects, suppliers);

  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState<KnowledgeFilters>(DEFAULT_FILTERS);
  const [selectedItem, setSelectedItem] = useState<KnowledgeItem | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const handleSelect = (item: KnowledgeItem) => { setSelectedItem(item); setDrawerOpen(true); };
  const handleFiltersChange = (patch: Partial<KnowledgeFilters>) => setFilters((prev) => ({ ...prev, ...patch }));
  const clearFilters = () => setFilters(DEFAULT_FILTERS);

  const filteredItems = useMemo(() => {
    if (!snapshot) return [];
    const now = new Date(snapshot.generatedAt).getTime();
    const cutoff = filters.dateRange === "all" ? null : now - Number(filters.dateRange) * 86_400_000;
    return snapshot.items.filter((item) => {
      if (filters.category !== "all" && item.category !== filters.category) return false;
      if (filters.project !== "all" && item.projectCode !== filters.project) return false;
      if (filters.source !== "all" && item.sourceType !== filters.source) return false;
      if (filters.riskLevel !== "all" && item.riskLevel !== filters.riskLevel) return false;
      if (filters.department !== "all" && item.department !== filters.department) return false;
      if (filters.supplier !== "all" && item.supplierName !== filters.supplier) return false;
      if (filters.material !== "all" && item.materialName !== filters.material) return false;
      if (cutoff !== null && new Date(item.date).getTime() < cutoff) return false;
      return true;
    });
  }, [snapshot, filters]);

  const searchResults = useMemo(() => searchKnowledge(filteredItems, query), [filteredItems, query]);
  const filtersActive = Object.entries(filters).some(([k, v]) => v !== DEFAULT_FILTERS[k as keyof KnowledgeFilters]);

  if (projectsLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-full max-w-md rounded-lg" />
        <CrossProjectLearningSkeleton />
      </div>
    );
  }

  if (projectsError) {
    return (
      <ErrorState title="Unable to load projects" description="Check your connection and try again." action={
        <button className="text-xs font-medium text-primary hover:underline" onClick={() => refetchProjects()}>Retry</button>
      } />
    );
  }

  if (!projects?.length) {
    return <EmptyState icon={BookOpen} title="No projects yet" description="Cross-Project Learning needs at least one project to draw organizational knowledge from." />;
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-lg font-semibold text-foreground">Cross-Project Learning</h2>
            <DemoDataBadge />
          </div>
          <p className="text-sm text-muted-foreground max-w-2xl">
            <span className="italic">"Has this happened before? What worked? What should we do now?"</span> — search
            organizational knowledge across every project and discover reusable experience.
          </p>
        </div>
        <button
          onClick={() => refetch()}
          disabled={isRefetching}
          className="inline-flex items-center gap-1.5 h-9 px-3 rounded-lg border border-border text-xs font-medium text-muted-foreground hover:text-foreground hover:border-primary/40 transition-colors shrink-0"
        >
          <RotateCcw className={`w-3.5 h-3.5 ${isRefetching ? "animate-spin" : ""}`} />
          Refresh
        </button>
      </div>

      {isLoading || !snapshot ? (
        isError ? (
          <ErrorState title="Unable to load cross-project knowledge" description="Something went wrong generating the analysis." action={
            <button className="text-xs font-medium text-primary hover:underline" onClick={() => refetch()}>Retry</button>
          } />
        ) : (
          <CrossProjectLearningSkeleton />
        )
      ) : snapshot.items.length === 0 ? (
        <EmptyState icon={BookOpen} title="No knowledge captured yet" description="Once projects accumulate history, reusable knowledge will appear here." />
      ) : (
        <>
          {/* Executive Learning Summary */}
          <div className="space-y-3">
            <SectionTitle icon={BookOpen}>Executive Learning Summary</SectionTitle>
            <ExecutiveLearningSummary stats={snapshot.stats} />
          </div>

          {/* Knowledge search */}
          <div className="panel panel-body">
            <SectionTitle icon={SearchIcon}>Knowledge Search</SectionTitle>
            <div className="mt-3">
              <KnowledgeSearchBar value={query} onChange={setQuery} />
            </div>
          </div>

          {/* Knowledge categories + filters */}
          <div className="panel panel-body">
            <FilterBar
              items={snapshot.items}
              categoryCounts={snapshot.categoryCounts}
              allProjects={projects.map((p) => ({ projectId: p.id, projectCode: p.project_code, projectName: p.project_name }))}
              filters={filters}
              onChange={handleFiltersChange}
              onClear={clearFilters}
            />
          </div>

          {/* Search results */}
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <SectionTitle icon={SearchIcon}>Search Results</SectionTitle>
              <span className="text-xs text-muted-foreground">{searchResults.length} of {snapshot.items.length} items{query || filtersActive ? " (filtered)" : ""}</span>
            </div>
            {searchResults.length === 0 ? (
              <div className="panel">
                <EmptyState icon={SearchIcon} title="No knowledge matches your search" description="Try a different term, or clear the active filters." action={
                  <button onClick={() => { setQuery(""); clearFilters(); }} className="text-xs font-medium text-primary hover:underline">Clear search & filters</button>
                } />
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
                {searchResults.slice(0, 12).map((item) => <KnowledgeItemCard key={item.id} item={item} onSelect={handleSelect} />)}
              </div>
            )}
          </div>

          {/* Knowledge graph */}
          <div className="panel">
            <div className="panel-header">
              <div className="flex items-center gap-2"><Network className="w-4 h-4 text-primary" /><span className="panel-title">Knowledge Graph</span></div>
              <span className="text-[11px] text-muted-foreground">{filteredItems.length} knowledge items</span>
            </div>
            <div className="panel-body">
              <KnowledgeGraph items={filteredItems} selectedId={selectedItem?.id ?? null} onSelectCase={handleSelect} />
            </div>
          </div>

          {/* Executive insights */}
          <ExecutiveInsights insights={snapshot.executiveInsights} />

          {/* Timeline view */}
          <div className="space-y-3">
            <SectionTitle icon={History}>Timeline View</SectionTitle>
            <KnowledgeTimeline items={filteredItems} onSelect={handleSelect} />
          </div>

          <p className="text-[11px] text-muted-foreground text-center flex items-center justify-center gap-1.5">
            <Sparkles className="w-3 h-3" /> Generated {new Date(snapshot.generatedAt).toLocaleString()} &middot; Demo Data / Illustrative Knowledge Retrieval &middot; not live AI, not real semantic search.
          </p>
        </>
      )}

      <KnowledgeDetailDrawer
        item={selectedItem}
        allItems={snapshot?.items ?? []}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        onSelectItem={handleSelect}
      />
    </div>
  );
}
