import { useMemo, useState } from "react";
import { useListSuppliers, useListProjects } from "@workspace/api-client-react";
import {
  RotateCcw, Boxes, LineChart as LineChartIcon, Flame, Wallet, Bell, ShoppingCart,
  GitCompare, FlaskConical, Info,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { FilterSelect } from "@/components/filter-select";
import { useMaterialIntelligence } from "@/lib/useMaterialIntelligence";
import type { MaterialProfile } from "@/lib/mockMaterialIntelligence";
import { DemoDataBadge, formatPct } from "./shared";
import { MaterialOverview } from "./MaterialOverview";
import { PriceTrendChart, type PriceSeries } from "./PriceTrendChart";
import { MaterialDirectory } from "./MaterialDirectory";
import { MaterialDetailDrawer } from "./MaterialDetailDrawer";
import { PortfolioExposureTable } from "./PortfolioExposureTable";
import { MaterialRiskHeatMap } from "./MaterialRiskHeatMap";
import { SupplyChainAlerts } from "./SupplyChainAlerts";
import { ProcurementOpportunities } from "./ProcurementOpportunities";
import { ScenarioAnalysis } from "./ScenarioAnalysis";
import { MaterialComparison } from "./MaterialComparison";
import { AIInsightsPanel } from "./AIInsightsPanel";

// ── Material Intelligence workspace ─────────────────────────────────────
// Answers: which materials are becoming more expensive, which projects are
// exposed, which materials carry the greatest cost/supply risk, and what
// procurement should do about it. Project and supplier identity is real
// (useListProjects / useListSuppliers, the same endpoints every other
// picker in the app uses); every price, trend, forecast, alert, and AI
// insight layered on top is local demo data (see
// lib/mockMaterialIntelligence.ts + lib/useMaterialIntelligence.ts) until
// a real pricing/market-data integration exists — every surface below is
// labeled Demo Data / Illustrative Market Analysis, never presented as a
// real price or live AI output.

type TrendScope = "portfolio" | "category" | "material";

function SectionTitle({ icon: Icon, children }: { icon: typeof Boxes; children: React.ReactNode }) {
  return (
    <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
      <Icon className="w-4 h-4 text-primary" /> {children}
    </h3>
  );
}

function MaterialIntelligenceSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-6 gap-2.5">
        {[0, 1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className="h-24 w-full rounded-xl" />)}
      </div>
      <Skeleton className="h-64 w-full rounded-xl" />
      <Skeleton className="h-72 w-full rounded-xl" />
    </div>
  );
}

export default function MaterialIntelligence() {
  const { data: suppliers, isLoading: suppliersLoading } = useListSuppliers({ limit: 100 });
  const { data: projects, isLoading: projectsLoading, isError: projectsError, refetch: refetchProjects } = useListProjects({ limit: 100 });

  const { data: snapshot, isLoading, isError, refetch, isRefetching } = useMaterialIntelligence(suppliers, projects);

  const [selectedMaterial, setSelectedMaterial] = useState<MaterialProfile | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [compareIds, setCompareIds] = useState<Set<string>>(new Set());

  const [trendScope, setTrendScope] = useState<TrendScope>("portfolio");
  const [trendCategory, setTrendCategory] = useState<string>("");
  const [trendMaterialId, setTrendMaterialId] = useState<string>("");

  const handleSelectMaterial = (material: MaterialProfile) => {
    setSelectedMaterial(material);
    setDrawerOpen(true);
  };

  const toggleCompare = (id: string) => {
    setCompareIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < 3) next.add(id);
      return next;
    });
  };

  const trend = useMemo(() => {
    if (!snapshot) return { data: [] as Record<string, number | string>[], series: [] as PriceSeries[], suffix: "" };
    if (trendScope === "material") {
      const material = snapshot.materials.find((m) => m.id === trendMaterialId) ?? snapshot.materials[0];
      if (!material) return { data: [], series: [], suffix: "" };
      return {
        data: material.priceHistory.map((p) => ({ period: p.period, price: p.price })),
        series: [{ key: "price", label: material.name, color: "#0ea5e9" }],
        suffix: ` SAR/${material.unit}`,
      };
    }
    if (trendScope === "category") {
      const category = trendCategory || snapshot.categorySummaries[0]?.category;
      const inCategory = snapshot.materials.filter((m) => m.category === category);
      const periods = inCategory[0]?.priceHistory.map((p) => p.period) ?? [];
      const data = periods.map((period, i) => {
        const avg = inCategory.reduce((s, m) => s + m.priceHistory[i].price / m.priceHistory[0].price, 0) / (inCategory.length || 1);
        return { period, index: Math.round(avg * 1000) / 10 };
      });
      return { data, series: [{ key: "index", label: `${category} index`, color: "#f59e0b" }], suffix: " idx" };
    }
    return {
      data: snapshot.portfolioPriceTrend.map((p) => ({ period: p.period, index: p.index })),
      series: [{ key: "index", label: "Portfolio Index", color: "#6366f1" }],
      suffix: " idx",
    };
  }, [snapshot, trendScope, trendCategory, trendMaterialId]);

  if (projectsLoading || suppliersLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-full max-w-md rounded-lg" />
        <MaterialIntelligenceSkeleton />
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

  const comparedMaterials = snapshot ? snapshot.materials.filter((m) => compareIds.has(m.id)) : [];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-lg font-semibold text-foreground">Material Intelligence</h2>
            <DemoDataBadge />
          </div>
          <p className="text-sm text-muted-foreground max-w-2xl">
            Which materials are becoming more expensive, which projects are exposed to price increases, which
            materials carry the greatest cost and supply risk, and what procurement should consider next.
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
          <ErrorState title="Unable to load material intelligence" description="Something went wrong generating the analysis." action={
            <button className="text-xs font-medium text-primary hover:underline" onClick={() => refetch()}>Retry</button>
          } />
        ) : (
          <MaterialIntelligenceSkeleton />
        )
      ) : snapshot.materials.length === 0 ? (
        <EmptyState icon={Boxes} title="No materials monitored" description="No material catalog data is available yet." />
      ) : (
        <>
          {/* Executive Material Overview */}
          <div className="space-y-3">
            <SectionTitle icon={Boxes}>Executive Material Overview</SectionTitle>
            <MaterialOverview stats={snapshot.portfolioStats} />
          </div>

          {/* Price Trend Analysis */}
          <div className="panel">
            <div className="panel-header flex-wrap gap-2">
              <div className="flex items-center gap-2">
                <LineChartIcon className="w-4 h-4 text-primary" />
                <span className="panel-title">Price Trend Analysis</span>
              </div>
              <div className="flex items-center gap-2">
                <FilterSelect value={trendScope} onChange={(v) => setTrendScope(v as TrendScope)} className="w-40" ariaLabel="Trend scope">
                  <option value="portfolio">Portfolio</option>
                  <option value="category">Category</option>
                  <option value="material">Individual Material</option>
                </FilterSelect>
                {trendScope === "category" && (
                  <FilterSelect value={trendCategory || snapshot.categorySummaries[0]?.category} onChange={setTrendCategory} className="w-44" ariaLabel="Category">
                    {snapshot.categorySummaries.map((c) => <option key={c.category} value={c.category}>{c.category}</option>)}
                  </FilterSelect>
                )}
                {trendScope === "material" && (
                  <FilterSelect value={trendMaterialId || snapshot.materials[0]?.id} onChange={setTrendMaterialId} className="w-48" ariaLabel="Material">
                    {snapshot.materials.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
                  </FilterSelect>
                )}
              </div>
            </div>
            <div className="panel-body space-y-3">
              <PriceTrendChart data={trend.data} series={trend.series} valueSuffix={trend.suffix} />
              <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground border-t border-border/50 pt-3">
                <Info className="w-3.5 h-3.5 shrink-0" />
                <span>Portfolio 30-day change: <strong className="text-foreground">{formatPct(snapshot.portfolioStats.avgPriceChange30d)}</strong></span>
                <span>&middot;</span>
                <span>{snapshot.categorySummaries.length} categories tracked</span>
              </div>
            </div>
          </div>

          {/* Risk heat map */}
          <div className="panel">
            <div className="panel-header">
              <div className="flex items-center gap-2">
                <Flame className="w-4 h-4 text-primary" />
                <span className="panel-title">Material Risk Heat Map</span>
              </div>
            </div>
            <div className="panel-body">
              <MaterialRiskHeatMap
                rows={snapshot.riskHeatRows}
                onSelectMaterial={(id) => {
                  const m = snapshot.materials.find((mm) => mm.id === id);
                  if (m) handleSelectMaterial(m);
                }}
              />
            </div>
          </div>

          {/* Portfolio cost exposure */}
          <div className="space-y-3">
            <SectionTitle icon={Wallet}>Portfolio Cost Exposure</SectionTitle>
            <PortfolioExposureTable rows={snapshot.exposureRows} />
          </div>

          {/* Supply chain alerts */}
          <div className="space-y-3">
            <SectionTitle icon={Bell}>Supply Chain Alerts</SectionTitle>
            <SupplyChainAlerts alerts={snapshot.alerts} />
          </div>

          {/* Procurement opportunities */}
          <div className="space-y-3">
            <SectionTitle icon={ShoppingCart}>Procurement Opportunities</SectionTitle>
            <ProcurementOpportunities opportunities={snapshot.opportunities} />
          </div>

          {/* Scenario analysis */}
          <div className="space-y-3">
            <SectionTitle icon={FlaskConical}>Scenario Analysis</SectionTitle>
            <ScenarioAnalysis materials={snapshot.materials} />
          </div>

          {/* AI insights panel */}
          <AIInsightsPanel insights={snapshot.aiPortfolioInsights} />

          {/* Material comparison */}
          <div className="panel panel-body space-y-3">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <SectionTitle icon={GitCompare}>Material Comparison</SectionTitle>
              {comparedMaterials.length > 0 && (
                <button onClick={() => setCompareIds(new Set())} className="text-xs text-primary hover:underline">Clear comparison</button>
              )}
            </div>
            <MaterialComparison materials={comparedMaterials} onRemove={toggleCompare} />
          </div>

          {/* Material directory / market watch */}
          <div className="space-y-3">
            <SectionTitle icon={Boxes}>Material Market Watch</SectionTitle>
            <MaterialDirectory
              materials={snapshot.materials}
              allProjects={(projects ?? []).map((p) => ({ projectId: p.id, projectCode: p.project_code, projectName: p.project_name }))}
              compareIds={compareIds}
              onToggleCompare={toggleCompare}
              onSelectMaterial={handleSelectMaterial}
            />
          </div>

          <p className="text-[11px] text-muted-foreground text-center">
            Analysis generated {new Date(snapshot.generatedAt).toLocaleString()} &middot; Demo Data / Illustrative Market Analysis &middot; not live AI, not real market prices.
          </p>
        </>
      )}

      <MaterialDetailDrawer material={selectedMaterial} open={drawerOpen} onOpenChange={setDrawerOpen} />
    </div>
  );
}
