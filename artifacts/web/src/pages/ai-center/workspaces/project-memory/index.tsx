import { useEffect, useMemo, useState } from "react";
import { useLocation, useSearch } from "wouter";
import { useListProjects } from "@workspace/api-client-react";
import {
  Brain, Sparkles, ListChecks, Target, RotateCcw, Gavel, FileCheck2,
  ClipboardList, FolderOpen, Network, History as HistoryIcon, ArrowRight,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { StatTile } from "@/components/stat-tile";
import { SearchInput } from "@/components/search-input";
import { FilterSelect } from "@/components/filter-select";
import { FilterChip } from "@/components/filter-chip";
import { useRegisterCurrentEntity } from "@/context/CurrentEntityContext";
import { useProjectMemory } from "@/lib/useProjectMemory";
import type {
  MemoryCategory, MemoryItem, MemorySourceType, RiskLevel,
} from "@/lib/mockProjectMemory";
import { SOURCE_META, SOURCE_TYPE_ORDER, RISK_TONE, STATUS_BADGE, DemoDataBadge, formatDate } from "./shared";
import { MemoryItemCard } from "./MemoryItemCard";
import { MemoryTimeline } from "./MemoryTimeline";
import { MemoryGraph } from "./MemoryGraph";
import { MemoryDetailDrawer } from "./MemoryDetailDrawer";
import { StatsPanel } from "./StatsPanel";

// ── Project Memory workspace ────────────────────────────────────────────
// One connected view of everything captured about a project — documents,
// site reports, meetings, contracts, claims, decisions, risks, actions,
// and approvals — unified into a single searchable timeline, relationship
// graph, and AI-style summary. The project list is real (useListProjects,
// the same endpoint every other project picker in the app uses); the
// memory content itself is local demo data (see lib/mockProjectMemory.ts +
// lib/useProjectMemory.ts) until a backend "project memory" endpoint
// exists — every demo surface below is labeled, never presented as live.

const RISK_FILTERS: (RiskLevel | "all")[] = ["all", "critical", "high", "medium", "low"];
const DATE_FILTERS = [
  { value: "all", label: "All time" },
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
  { value: "90", label: "Last 90 days" },
] as const;

function WorkflowStrip() {
  const steps = ["Capture", "Understand", "Connect", "Detect", "Decide"];
  return (
    <div className="flex flex-wrap items-center gap-1.5 text-[11px] font-medium text-muted-foreground">
      {steps.map((step, i) => (
        <span key={step} className="flex items-center gap-1.5">
          <span className="rounded-full bg-muted px-2.5 py-1 text-foreground/80">{step}</span>
          {i < steps.length - 1 && <ArrowRight className="w-3 h-3 text-muted-foreground/50" />}
        </span>
      ))}
    </div>
  );
}

function ProjectMemorySkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
        {[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}
      </div>
      <Skeleton className="h-32 w-full rounded-xl" />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}
      </div>
    </div>
  );
}

export default function ProjectMemory() {
  const [, setLocation] = useLocation();
  const search = useSearch();
  const { data: projects, isLoading: projectsLoading, isError: projectsError, refetch: refetchProjects } = useListProjects({ limit: 100 });

  const projectCodeParam = new URLSearchParams(search).get("project");
  const selectedProject = useMemo(() => {
    if (!projects?.length) return null;
    return (projectCodeParam && projects.find((p) => p.project_code === projectCodeParam)) || projects[0];
  }, [projects, projectCodeParam]);

  const setSelectedProjectCode = (code: string) => {
    setLocation(`/ai-center/project-memory?project=${encodeURIComponent(code)}`);
  };

  useRegisterCurrentEntity(
    selectedProject
      ? { kind: "project", code: selectedProject.project_code, label: selectedProject.project_name, projectId: selectedProject.id }
      : null,
  );

  const { data: snapshot, isLoading, isError, refetch, isRefetching } = useProjectMemory(
    selectedProject ? { project_code: selectedProject.project_code, project_name: selectedProject.project_name } : null,
  );

  // ── Filters ──────────────────────────────────────────────────────────
  const [globalSearch, setGlobalSearch] = useState("");
  const [sourceTypes, setSourceTypes] = useState<Set<MemorySourceType>>(new Set());
  const [category, setCategory] = useState<MemoryCategory | "all">("all");
  const [riskLevel, setRiskLevel] = useState<RiskLevel | "all">("all");
  const [author, setAuthor] = useState<string>("all");
  const [dateRange, setDateRange] = useState<(typeof DATE_FILTERS)[number]["value"]>("all");

  const [selectedItem, setSelectedItem] = useState<MemoryItem | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  // Reset filters when the selected project changes so counts/filters from
  // one project's memory don't linger and silently hide another's.
  useEffect(() => {
    setGlobalSearch(""); setSourceTypes(new Set()); setCategory("all");
    setRiskLevel("all"); setAuthor("all"); setDateRange("all");
    setSelectedItem(null); setDrawerOpen(false);
  }, [selectedProject?.project_code]);

  const handleSelect = (item: MemoryItem) => {
    setSelectedItem(item);
    setDrawerOpen(true);
  };

  const handleSelectRelated = (item: MemoryItem) => {
    setSelectedItem(item);
    // stays open — jump straight to the related item's own details
  };

  const allItems = snapshot?.items ?? [];

  const filteredItems = useMemo(() => {
    const now = snapshot ? new Date(snapshot.generatedAt).getTime() : Date.now();
    const cutoff = dateRange === "all" ? null : now - Number(dateRange) * 86_400_000;
    const q = globalSearch.trim().toLowerCase();
    return allItems.filter((item) => {
      if (sourceTypes.size > 0 && !sourceTypes.has(item.sourceType)) return false;
      if (category !== "all" && item.category !== category) return false;
      if (riskLevel !== "all" && item.riskLevel !== riskLevel) return false;
      if (author !== "all" && item.author !== author) return false;
      if (cutoff !== null && new Date(item.date).getTime() < cutoff) return false;
      if (q) {
        const hay = `${item.title} ${item.summary} ${item.tags.join(" ")} ${item.author}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [allItems, sourceTypes, category, riskLevel, author, dateRange, globalSearch, snapshot]);

  const toggleSourceType = (type: MemorySourceType) => {
    setSourceTypes((prev) => {
      const next = new Set(prev);
      next.has(type) ? next.delete(type) : next.add(type);
      return next;
    });
  };

  const clearFilters = () => {
    setGlobalSearch(""); setSourceTypes(new Set()); setCategory("all"); setRiskLevel("all"); setAuthor("all"); setDateRange("all");
  };
  const filtersActive = !!globalSearch || sourceTypes.size > 0 || category !== "all" || riskLevel !== "all" || author !== "all" || dateRange !== "all";

  // Default focus item once data loads: the most recent high/critical risk
  // item if one exists, else the most recent item overall.
  useEffect(() => {
    if (!snapshot || selectedItem) return;
    const risky = snapshot.items.find((i) => i.riskLevel === "critical" || i.riskLevel === "high");
    setSelectedItem(risky ?? snapshot.items[0] ?? null);
  }, [snapshot, selectedItem]);

  const decisions = allItems.filter((i) => i.sourceType === "decision");
  const openActions = allItems.filter((i) => i.sourceType === "action" && i.status === "Open");
  const pendingApprovals = allItems.filter((i) => i.sourceType === "approval" && i.status === "Pending");
  const documentItems = allItems.filter((i) => i.sourceType === "document");
  const allCitations = useMemo(() => {
    const seen = new Map<string, { label: string; sourceType: MemorySourceType; href?: string }>();
    for (const item of allItems) for (const c of item.citations) if (!seen.has(c.label)) seen.set(c.label, c);
    return Array.from(seen.values());
  }, [allItems]);

  const connectedToSelected = useMemo(() => {
    if (!selectedItem) return [];
    return selectedItem.relatedIds.map((id) => allItems.find((i) => i.id === id)).filter((i): i is MemoryItem => !!i);
  }, [selectedItem, allItems]);

  // ── Top-level states ─────────────────────────────────────────────────

  if (projectsLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-full max-w-md rounded-lg" />
        <ProjectMemorySkeleton />
      </div>
    );
  }

  if (projectsError) {
    return <ErrorState title="Unable to load projects" description="Check your connection and try again." action={
      <button className="text-xs font-medium text-primary hover:underline" onClick={() => refetchProjects()}>Retry</button>
    } />;
  }

  if (!projects?.length || !selectedProject) {
    return <EmptyState icon={Brain} title="No projects yet" description="Project Memory needs at least one project to organize knowledge around." />;
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-lg font-semibold text-foreground">Project Memory</h2>
            <DemoDataBadge />
          </div>
          <p className="text-sm text-muted-foreground max-w-2xl">
            One connected view of everything captured about a project — documents, site reports, meetings,
            contracts, claims, decisions, risks, actions, and approvals — in a single searchable timeline.
          </p>
          <WorkflowStrip />
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

      {/* Project selector */}
      <div className="panel panel-body flex flex-wrap items-center gap-3">
        <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground shrink-0">Project</label>
        <FilterSelect
          className="min-w-64 flex-1"
          value={String(selectedProject.id)}
          onChange={(v) => {
            const p = projects.find((pr) => String(pr.id) === v);
            if (p) setSelectedProjectCode(p.project_code);
          }}
          ariaLabel="Select project"
          testId="select-project-memory-project"
        >
          {projects.map((p) => (
            <option key={p.id} value={p.id}>{p.project_code} — {p.project_name}</option>
          ))}
        </FilterSelect>
        <span className="badge badge-neutral shrink-0">{selectedProject.status}</span>
      </div>

      {isLoading ? (
        <ProjectMemorySkeleton />
      ) : isError || !snapshot ? (
        <ErrorState title="Unable to load project memory" description="Something went wrong generating this project's memory view." action={
          <button className="text-xs font-medium text-primary hover:underline" onClick={() => refetch()}>Retry</button>
        } />
      ) : (
        <>
          {/* Global search + filters */}
          <div className="panel panel-body space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <SearchInput
                value={globalSearch}
                onChange={setGlobalSearch}
                placeholder="Search all project memory — titles, summaries, tags, authors..."
                testId="input-project-memory-search"
              />
              <FilterSelect value={dateRange} onChange={(v) => setDateRange(v as typeof dateRange)} className="w-40" ariaLabel="Date range">
                {DATE_FILTERS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
              </FilterSelect>
              <FilterSelect value={category} onChange={(v) => setCategory(v as typeof category)} className="w-40" ariaLabel="Category">
                <option value="all">All categories</option>
                {(Object.keys(snapshot.stats.byCategory) as MemoryCategory[]).map((c) => <option key={c} value={c}>{c}</option>)}
              </FilterSelect>
              <FilterSelect value={author} onChange={setAuthor} className="w-44" ariaLabel="Author">
                <option value="all">All authors</option>
                {snapshot.authors.map((a) => <option key={a} value={a}>{a}</option>)}
              </FilterSelect>
              {filtersActive && (
                <button onClick={clearFilters} className="text-xs text-primary hover:underline shrink-0">Clear filters</button>
              )}
            </div>

            <div>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1.5">Source Type</p>
              <div className="flex flex-wrap gap-1.5">
                {SOURCE_TYPE_ORDER.map((type) => (
                  <FilterChip key={type} active={sourceTypes.has(type)} onClick={() => toggleSourceType(type)} icon={SOURCE_META[type].icon}>
                    {SOURCE_META[type].label} ({snapshot.stats.bySourceType[type] ?? 0})
                  </FilterChip>
                ))}
              </div>
            </div>

            <div>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1.5">Risk Level</p>
              <div className="flex flex-wrap gap-1.5">
                {RISK_FILTERS.map((r) => (
                  <FilterChip key={r} active={riskLevel === r} onClick={() => setRiskLevel(riskLevel === r ? "all" : r)} tone={r === "critical" || r === "high" ? "amber" : "default"}>
                    {r === "all" ? "All risk levels" : `${r.charAt(0).toUpperCase()}${r.slice(1)} (${snapshot.stats.byRiskLevel[r]})`}
                  </FilterChip>
                ))}
              </div>
            </div>
          </div>

          {/* Executive Project Summary */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5"><ClipboardList className="w-4 h-4 text-primary" /> Executive Project Summary</h3>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
              <StatTile icon={Brain} label="Memory Items" value={snapshot.stats.total} tone="neutral" />
              <StatTile icon={SOURCE_META.risk.icon} label="Open Risks" value={snapshot.stats.openRisks} tone={snapshot.stats.openRisks > 0 ? "warning" : "success"} />
              <StatTile icon={SOURCE_META.approval.icon} label="Pending Approvals" value={snapshot.stats.pendingApprovals} tone={snapshot.stats.pendingApprovals > 0 ? "warning" : "success"} />
              <StatTile icon={ListChecks} label="Open Actions" value={snapshot.stats.openActions} tone={snapshot.stats.openActions > 0 ? "warning" : "success"} />
              <StatTile icon={Gavel} label="Decisions Logged" value={snapshot.stats.decisionsLogged} tone="neutral" />
            </div>
            <div className="panel panel-body space-y-2">
              <p className="text-sm text-foreground leading-relaxed">{snapshot.executiveSummary.headline}</p>
              <ul className="space-y-1">
                {snapshot.executiveSummary.bullets.map((b, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary" /> {b}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* AI-generated-style summary panel */}
          <div className="panel panel-body space-y-4">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5"><Sparkles className="w-4 h-4 text-primary" /> AI Memory Summary</h3>
              <DemoDataBadge />
            </div>
            <p className="text-xs text-muted-foreground -mt-2">
              Illustrative of the summary Hermes would generate once grounded in this project's real memory — not a live AI call.
            </p>
            <div className="space-y-1.5">
              <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Key Findings</p>
              <ul className="space-y-1">
                {snapshot.aiSummary.keyFindings.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-foreground">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary" /> {f}
                  </li>
                ))}
              </ul>
            </div>
            <div className="space-y-1.5">
              <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Target className="w-3 h-3" /> Recommendations</p>
              <ul className="space-y-1">
                {snapshot.aiSummary.recommendations.map((r, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-foreground">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary" /> {r}
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* Memory statistics + knowledge categories */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5"><HistoryIcon className="w-4 h-4 text-primary" /> Memory Statistics &amp; Knowledge Categories</h3>
            <StatsPanel stats={snapshot.stats} activeCategory={category} onCategoryClick={setCategory} />
          </div>

          {/* Relationship graph */}
          <div className="panel">
            <div className="panel-header">
              <div className="flex items-center gap-2">
                <Network className="w-4 h-4 text-primary" />
                <span className="panel-title">Memory Relationship Graph</span>
              </div>
              <span className="text-[11px] text-muted-foreground">{allItems.length} items &middot; {allItems.reduce((n, i) => n + i.relatedIds.length, 0)} links</span>
            </div>
            <div className="panel-body">
              <MemoryGraph items={allItems} selectedId={selectedItem?.id ?? null} onSelect={handleSelect} />
            </div>
          </div>

          {/* Connected events for the currently focused item */}
          {selectedItem && (
            <div className="panel panel-body space-y-2.5">
              <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                Connected Events &middot; focused on "{selectedItem.title}"
              </p>
              {connectedToSelected.length === 0 ? (
                <p className="text-xs text-muted-foreground">No connected items for this entry.</p>
              ) : (
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {connectedToSelected.map((item) => (
                    <MemoryItemCard key={item.id} item={item} onSelect={handleSelect} compact />
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Unified chronological timeline + recent cards */}
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <h3 className="text-sm font-bold text-foreground">Recent Knowledge</h3>
              <span className="text-xs text-muted-foreground">{filteredItems.length} of {allItems.length} items{filtersActive ? " (filtered)" : ""}</span>
            </div>
            {filteredItems.length === 0 ? (
              <div className="panel">
                <EmptyState icon={Brain} title="No memory items match your filters" description="Try a different search term, date range, or clear the active filters." action={
                  <button onClick={clearFilters} className="text-xs font-medium text-primary hover:underline">Clear filters</button>
                } />
              </div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {filteredItems.slice(0, 6).map((item) => (
                  <MemoryItemCard key={item.id} item={item} onSelect={handleSelect} />
                ))}
              </div>
            )}
          </div>

          <div className="space-y-3">
            <h3 className="text-sm font-bold text-foreground">Full Timeline</h3>
            {filteredItems.length === 0 ? null : <MemoryTimeline items={filteredItems} onSelect={handleSelect} />}
          </div>

          {/* Important decisions */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5"><Gavel className="w-4 h-4 text-primary" /> Important Decisions</h3>
            {decisions.length === 0 ? (
              <div className="panel"><EmptyState icon={Gavel} title="No decisions logged yet" /></div>
            ) : (
              <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                {decisions.map((item) => <MemoryItemCard key={item.id} item={item} onSelect={handleSelect} compact />)}
              </div>
            )}
          </div>

          {/* Open actions & pending approvals */}
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-2.5">
              <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5"><ListChecks className="w-4 h-4 text-primary" /> Open Actions ({openActions.length})</h3>
              {openActions.length === 0 ? (
                <div className="panel"><EmptyState icon={ListChecks} title="No open actions" description="Everything raised so far has been completed." /></div>
              ) : (
                <div className="space-y-2">
                  {openActions.map((item) => <MemoryItemCard key={item.id} item={item} onSelect={handleSelect} compact />)}
                </div>
              )}
            </div>
            <div className="space-y-2.5">
              <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5"><FileCheck2 className="w-4 h-4 text-primary" /> Pending Approvals ({pendingApprovals.length})</h3>
              {pendingApprovals.length === 0 ? (
                <div className="panel"><EmptyState icon={FileCheck2} title="Nothing pending" description="No approvals are currently awaiting a decision." /></div>
              ) : (
                <div className="space-y-2">
                  {pendingApprovals.map((item) => <MemoryItemCard key={item.id} item={item} onSelect={handleSelect} compact />)}
                </div>
              )}
            </div>
          </div>

          {/* Related documents & source references */}
          <div className="panel">
            <div className="panel-header">
              <div className="flex items-center gap-2">
                <FolderOpen className="w-4 h-4 text-primary" />
                <span className="panel-title">Related Documents &amp; Source References</span>
              </div>
            </div>
            <div className="panel-body space-y-4">
              {documentItems.length > 0 && (
                <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
                  {documentItems.map((item) => <MemoryItemCard key={item.id} item={item} onSelect={handleSelect} compact />)}
                </div>
              )}
              <div>
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-1.5">All Source References ({allCitations.length})</p>
                <div className="flex flex-wrap gap-1.5">
                  {allCitations.map((c) => (
                    <span key={c.label} className="inline-flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-[11px] text-muted-foreground">
                      {c.label}
                    </span>
                  ))}
                </div>
              </div>
              <p className="text-[11px] text-muted-foreground">
                Last generated {formatDate(snapshot.generatedAt)} for {snapshot.projectName}.
              </p>
            </div>
          </div>
        </>
      )}

      <MemoryDetailDrawer
        item={selectedItem}
        allItems={allItems}
        open={drawerOpen}
        onOpenChange={setDrawerOpen}
        onSelectRelated={handleSelectRelated}
      />
    </div>
  );
}
