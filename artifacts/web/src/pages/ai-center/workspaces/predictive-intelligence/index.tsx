import { useMemo, useState } from "react";
import { useLocation, useSearch } from "wouter";
import { useListProjects } from "@workspace/api-client-react";
import {
  Brain, RotateCcw, Gauge, AlertTriangle, LineChart as LineChartIcon,
  GitCompare, Table2, Flame, CalendarClock, TrendingUp as TrendingUpIcon, History as HistoryIcon,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { StatTile } from "@/components/stat-tile";
import { SearchInput } from "@/components/search-input";
import { FilterSelect } from "@/components/filter-select";
import { FilterChip } from "@/components/filter-chip";
import { useRegisterCurrentEntity } from "@/context/CurrentEntityContext";
import { usePredictiveIntelligence } from "@/lib/usePredictiveIntelligence";
import type { CategoryPrediction, ConfidenceLevel, PredictionCategory } from "@/lib/mockPredictiveIntelligence";
import {
  CATEGORY_META, CATEGORY_ORDER, BAND_BADGE, BAND_COLOR, DemoDataBadge,
} from "./shared";
import { PredictionCard } from "./PredictionCard";
import { PredictionTrendChart, type TrendSeries } from "./PredictionTrendChart";
import { HighRiskProjectsTable } from "./HighRiskProjectsTable";
import { ScenarioComparison } from "./ScenarioComparison";
import { PortfolioHeatMap } from "./PortfolioHeatMap";
import { PredictionTimeline } from "./PredictionTimeline";
import { EmergingRisks } from "./EmergingRisks";
import { PredictionHistory } from "./PredictionHistory";
import { AIRecommendationPanel } from "./AIRecommendationPanel";

// ── Predictive Construction Intelligence workspace ──────────────────────
// "What is likely to happen next?" — an executive forecast center covering
// delay, budget overrun, cash flow, claim, safety, and schedule risk across
// the portfolio (or a single selected project). The project list is real
// (useListProjects, same endpoint every other project picker in the app
// uses); every forecast number is local demo data (see
// lib/mockPredictiveIntelligence.ts + lib/usePredictiveIntelligence.ts)
// until a real forecasting backend exists — every prediction surface below
// is labeled Demo Data / Illustrative Forecast, never presented as live.

const CONFIDENCE_FILTERS: (ConfidenceLevel | "all")[] = ["all", "high", "medium", "low"];

function ForecastGauge({ score, band }: { score: number; band: string }) {
  const color = BAND_COLOR[band as keyof typeof BAND_COLOR] ?? "#6b7280";
  return (
    <div className="relative w-20 h-20 shrink-0">
      <svg viewBox="0 0 64 64" className="w-20 h-20 -rotate-90">
        <circle cx="32" cy="32" r="26" fill="none" stroke="currentColor" strokeWidth="6" className="text-muted opacity-20" />
        <circle
          cx="32" cy="32" r="26" fill="none" strokeWidth="6"
          strokeDasharray={`${(score / 100) * 163.4} 163.4`} strokeLinecap="round"
          style={{ stroke: color, transition: "stroke-dasharray 0.6s ease" }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-base font-bold tabular-nums" style={{ color }}>{score}</span>
      </div>
    </div>
  );
}

function PredictiveIntelligenceSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-6 gap-2.5">
        {[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}
      </div>
      <Skeleton className="h-64 w-full rounded-xl" />
      <Skeleton className="h-72 w-full rounded-xl" />
    </div>
  );
}

function SectionTitle({ icon: Icon, children }: { icon: typeof Gauge; children: React.ReactNode }) {
  return (
    <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
      <Icon className="w-4 h-4 text-primary" /> {children}
    </h3>
  );
}

export default function PredictiveIntelligence() {
  const [, setLocation] = useLocation();
  const search = useSearch();
  const { data: projects, isLoading: projectsLoading, isError: projectsError, refetch: refetchProjects } = useListProjects({ limit: 100 });

  const scopeParam = new URLSearchParams(search).get("project"); // null / "" => portfolio
  const scope = scopeParam ?? "portfolio";

  const setScope = (next: string) => {
    setLocation(next === "portfolio" ? "/ai-center/predictive-intelligence" : `/ai-center/predictive-intelligence?project=${encodeURIComponent(next)}`);
  };

  const { data: snapshot, isLoading, isError, refetch, isRefetching } = usePredictiveIntelligence(projects);

  const selectedProject = useMemo(
    () => (scope === "portfolio" ? null : snapshot?.projects.find((p) => p.projectCode === scope) ?? null),
    [scope, snapshot],
  );

  useRegisterCurrentEntity(
    selectedProject ? { kind: "project", code: selectedProject.projectCode, label: selectedProject.projectName, projectId: selectedProject.projectId } : null,
  );

  // ── Filters ──────────────────────────────────────────────────────────
  const [globalSearch, setGlobalSearch] = useState("");
  const [activeCategories, setActiveCategories] = useState<Set<PredictionCategory>>(new Set());
  const [confidence, setConfidence] = useState<ConfidenceLevel | "all">("all");

  const toggleCategory = (c: PredictionCategory) => {
    setActiveCategories((prev) => {
      const next = new Set(prev);
      next.has(c) ? next.delete(c) : next.add(c);
      return next;
    });
  };
  const clearFilters = () => { setGlobalSearch(""); setActiveCategories(new Set()); setConfidence("all"); };
  const filtersActive = !!globalSearch || activeCategories.size > 0 || confidence !== "all";
  const categoriesForColumns = Array.from(activeCategories);

  const matchesSearch = (code: string, name: string) => {
    if (!globalSearch.trim()) return true;
    const q = globalSearch.trim().toLowerCase();
    return code.toLowerCase().includes(q) || name.toLowerCase().includes(q);
  };

  // ── Scope-derived data ───────────────────────────────────────────────
  const cardsData: CategoryPrediction[] = useMemo(() => {
    if (!snapshot) return [];
    const source = selectedProject ? selectedProject.categories : snapshot.categoryPredictions;
    return CATEGORY_ORDER
      .map((c) => source[c])
      .filter((p) => activeCategories.size === 0 || activeCategories.has(p.category))
      .filter((p) => confidence === "all" || p.confidence === confidence);
  }, [snapshot, selectedProject, activeCategories, confidence]);

  const trendSeries: TrendSeries[] = selectedProject
    ? [{ key: "overall", label: `${selectedProject.projectCode} overall`, color: "#6366f1" }]
    : CATEGORY_ORDER.filter((c) => activeCategories.size === 0 || activeCategories.has(c))
        .map((c) => ({ key: c, label: CATEGORY_META[c].label, color: CATEGORY_META[c].color }));
  const trendData = selectedProject ? selectedProject.trend : (snapshot?.trend ?? []);

  const scenarios = selectedProject ? selectedProject.scenarios : (snapshot?.scenarios ?? []);

  const timelineEvents = useMemo(() => {
    if (!snapshot) return [];
    const events = selectedProject
      ? selectedProject.timeline
      : snapshot.projects.flatMap((p) => p.timeline).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
    return events
      .filter((e) => activeCategories.size === 0 || activeCategories.has(e.category))
      .filter((e) => matchesSearch(e.projectCode, e.projectName))
      .slice(0, 14);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snapshot, selectedProject, activeCategories, globalSearch]);

  const filteredProjects = useMemo(() => {
    if (!snapshot) return [];
    return snapshot.projects.filter((p) => matchesSearch(p.projectCode, p.projectName));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snapshot, globalSearch]);

  const filteredEmergingRisks = useMemo(() => {
    if (!snapshot) return [];
    return snapshot.emergingRisks
      .filter((r) => activeCategories.size === 0 || activeCategories.has(r.category))
      .filter((r) => matchesSearch(r.projectCode, r.projectName));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snapshot, activeCategories, globalSearch]);

  const filteredHistory = useMemo(() => {
    if (!snapshot) return [];
    return snapshot.predictionHistory
      .filter((h) => activeCategories.size === 0 || activeCategories.has(h.category))
      .filter((h) => matchesSearch(h.projectCode, h.projectName));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [snapshot, activeCategories, globalSearch]);

  const aiPanel = useMemo(() => {
    if (!snapshot) return null;
    if (!selectedProject) return snapshot.aiRecommendations;
    const topCategory = CATEGORY_ORDER.reduce((a, b) =>
      selectedProject.categories[a].probability >= selectedProject.categories[b].probability ? a : b);
    const top = selectedProject.categories[topCategory];
    return {
      headline: `${selectedProject.projectCode} is forecast ${selectedProject.overallBand.toLowerCase()} risk overall, led by ${CATEGORY_META[topCategory].label.toLowerCase()} at ${top.probability}%.`,
      keyFindings: [
        `${CATEGORY_META[topCategory].label} is this project's highest-probability forecast at ${top.probability}% (${top.confidence} confidence).`,
        ...top.contributingFactors.slice(0, 2),
      ],
      recommendations: top.recommendedActions,
    };
  }, [snapshot, selectedProject]);

  // ── Top-level states ─────────────────────────────────────────────────

  if (projectsLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-full max-w-md rounded-lg" />
        <PredictiveIntelligenceSkeleton />
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
    return <EmptyState icon={Brain} title="No projects yet" description="Predictive Intelligence needs at least one project to forecast against." />;
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-lg font-semibold text-foreground">Predictive Construction Intelligence</h2>
            <DemoDataBadge />
          </div>
          <p className="text-sm text-muted-foreground max-w-2xl">
            Answers <span className="italic">"what is likely to happen next?"</span> — delay, budget overrun, cash
            flow, claim, safety, and schedule risk, forecast across the portfolio or a single project.
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

      {/* Project selector */}
      <div className="panel panel-body flex flex-wrap items-center gap-3">
        <label className="text-xs font-semibold uppercase tracking-wide text-muted-foreground shrink-0">Scope</label>
        <FilterSelect
          className="min-w-64 flex-1"
          value={scope}
          onChange={setScope}
          ariaLabel="Select portfolio or project"
          testId="select-predictive-scope"
        >
          <option value="portfolio">Portfolio — all {projects.length} projects</option>
          {projects.map((p) => (
            <option key={p.id} value={p.project_code}>{p.project_code} — {p.project_name}</option>
          ))}
        </FilterSelect>
        {selectedProject && <span className="badge badge-neutral shrink-0">{selectedProject.status}</span>}
      </div>

      {isLoading || !snapshot ? (
        isError ? (
          <ErrorState title="Unable to load predictions" description="Something went wrong generating the forecast." action={
            <button className="text-xs font-medium text-primary hover:underline" onClick={() => refetch()}>Retry</button>
          } />
        ) : (
          <PredictiveIntelligenceSkeleton />
        )
      ) : (
        <>
          {/* Search + filters */}
          <div className="panel panel-body space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <SearchInput
                value={globalSearch}
                onChange={setGlobalSearch}
                placeholder="Search projects by name or code..."
                testId="input-predictive-search"
              />
              {filtersActive && (
                <button onClick={clearFilters} className="text-xs text-primary hover:underline shrink-0">Clear filters</button>
              )}
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1.5">Prediction Category</p>
              <div className="flex flex-wrap gap-1.5">
                {CATEGORY_ORDER.map((c) => (
                  <FilterChip key={c} active={activeCategories.has(c)} onClick={() => toggleCategory(c)} icon={CATEGORY_META[c].icon}>
                    {CATEGORY_META[c].label}
                  </FilterChip>
                ))}
              </div>
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1.5">Confidence Level</p>
              <div className="flex flex-wrap gap-1.5">
                {CONFIDENCE_FILTERS.map((c) => (
                  <FilterChip key={c} active={confidence === c} onClick={() => setConfidence(confidence === c ? "all" : c)}>
                    {c === "all" ? "All confidence levels" : `${c.charAt(0).toUpperCase()}${c.slice(1)}`}
                  </FilterChip>
                ))}
              </div>
            </div>
          </div>

          {/* Executive Prediction Summary + Overall Portfolio Forecast */}
          <div className="space-y-3">
            <SectionTitle icon={Gauge}>Executive Prediction Summary</SectionTitle>
            <div className="panel panel-body flex flex-wrap items-center gap-5">
              <ForecastGauge score={snapshot.overallForecast.score} band={snapshot.overallForecast.band} />
              <div className="flex-1 min-w-[240px] space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className={`badge ${BAND_BADGE[snapshot.overallForecast.band]}`}>{snapshot.overallForecast.band} portfolio risk</span>
                  <span className="text-xs text-muted-foreground">Overall Portfolio Forecast &middot; {snapshot.overallForecast.score}/100</span>
                </div>
                <p className="text-sm text-foreground leading-relaxed">{snapshot.overallForecast.narrative}</p>
              </div>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
              <StatTile icon={AlertTriangle} label="Elevated / Critical" value={snapshot.projects.filter((p) => p.overallBand === "Critical" || p.overallBand === "Elevated").length} tone="warning" />
              <StatTile icon={Flame} label="Emerging Risks" value={snapshot.emergingRisks.length} tone={snapshot.emergingRisks.length > 0 ? "warning" : "success"} />
              <StatTile icon={HistoryIcon} label="Predictions Tracked" value={snapshot.predictionHistory.length} tone="neutral" />
              <StatTile icon={TrendingUpIcon} label="Projects Forecast" value={snapshot.projects.length} tone="neutral" />
            </div>
          </div>

          {/* Prediction cards */}
          <div className="space-y-3">
            <SectionTitle icon={Gauge}>
              {selectedProject ? `Prediction Cards — ${selectedProject.projectCode}` : "Prediction Cards — Portfolio"}
            </SectionTitle>
            {cardsData.length === 0 ? (
              <div className="panel"><EmptyState icon={Gauge} title="No predictions match the current filters" action={
                <button onClick={clearFilters} className="text-xs font-medium text-primary hover:underline">Clear filters</button>
              } /></div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {cardsData.map((p) => <PredictionCard key={p.category} prediction={p} />)}
              </div>
            )}
          </div>

          {/* Trend chart */}
          <div className="panel">
            <div className="panel-header">
              <div className="flex items-center gap-2">
                <LineChartIcon className="w-4 h-4 text-primary" />
                <span className="panel-title">Prediction Trend</span>
              </div>
              <span className="text-[11px] text-muted-foreground">10-week forecast history</span>
            </div>
            <div className="panel-body">
              {trendSeries.length === 0 ? (
                <EmptyState icon={LineChartIcon} title="No categories selected" description="Choose at least one prediction category to see its trend." />
              ) : (
                <PredictionTrendChart data={trendData} series={trendSeries} />
              )}
            </div>
          </div>

          {/* Scenario comparison */}
          <div className="panel panel-body space-y-3">
            <SectionTitle icon={GitCompare}>Scenario Comparison — "What if..."</SectionTitle>
            <ScenarioComparison scenarios={scenarios} contextLabel={selectedProject ? `${selectedProject.projectCode} — ${selectedProject.projectName}` : "the full portfolio"} />
          </div>

          {/* High risk projects table */}
          <div className="panel">
            <div className="panel-header">
              <div className="flex items-center gap-2">
                <Table2 className="w-4 h-4 text-primary" />
                <span className="panel-title">High Risk Projects</span>
              </div>
              <span className="text-[11px] text-muted-foreground">{filteredProjects.length} of {snapshot.projects.length} projects</span>
            </div>
            <div className="panel-body">
              <HighRiskProjectsTable
                projects={filteredProjects}
                activeCategories={categoriesForColumns}
                selectedProjectCode={selectedProject?.projectCode ?? null}
                onSelectProject={setScope}
              />
            </div>
          </div>

          {/* Portfolio heat map */}
          <div className="panel">
            <div className="panel-header">
              <div className="flex items-center gap-2">
                <Flame className="w-4 h-4 text-primary" />
                <span className="panel-title">Portfolio Heat Map</span>
              </div>
            </div>
            <div className="panel-body">
              <PortfolioHeatMap
                projects={filteredProjects}
                activeCategories={categoriesForColumns}
                selectedProjectCode={selectedProject?.projectCode ?? null}
                onSelectProject={setScope}
              />
            </div>
          </div>

          {/* Project prediction timeline */}
          <div className="space-y-3">
            <SectionTitle icon={CalendarClock}>
              {selectedProject ? `Project Prediction Timeline — ${selectedProject.projectCode}` : "Project Prediction Timeline — Portfolio"}
            </SectionTitle>
            <PredictionTimeline events={timelineEvents} referenceIso={snapshot.generatedAt} showProject={!selectedProject} />
          </div>

          {/* Top emerging risks */}
          <div className="space-y-3">
            <SectionTitle icon={Flame}>Top Emerging Risks</SectionTitle>
            <EmergingRisks risks={filteredEmergingRisks} />
          </div>

          {/* AI recommendation panel */}
          {aiPanel && (
            <AIRecommendationPanel headline={aiPanel.headline} keyFindings={aiPanel.keyFindings} recommendations={aiPanel.recommendations} />
          )}

          {/* Prediction history */}
          <div className="space-y-3">
            <SectionTitle icon={HistoryIcon}>Prediction History</SectionTitle>
            <PredictionHistory entries={filteredHistory} />
          </div>

          <p className="text-[11px] text-muted-foreground text-center">
            Forecast generated {new Date(snapshot.generatedAt).toLocaleString()} &middot; Demo Data / Illustrative Forecast &middot; not a live AI prediction.
          </p>
        </>
      )}
    </div>
  );
}
