import { useState } from "react";
import { useListSuppliers, useListProjects } from "@workspace/api-client-react";
import { RotateCcw, Truck, AlertOctagon, Flame, CalendarClock, GitCompare, PieChart as PieChartIcon } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { useSupplierRisk } from "@/lib/useSupplierRisk";
import type { SupplierProfile } from "@/lib/mockSupplierRisk";
import { DemoDataBadge } from "./shared";
import { SupplierHealthOverview } from "./SupplierHealthOverview";
import { TopHighRiskSuppliers } from "./TopHighRiskSuppliers";
import { SupplierDirectory } from "./SupplierDirectory";
import { SupplierDetailDrawer } from "./SupplierDetailDrawer";
import { PortfolioDistribution } from "./PortfolioDistribution";
import { RiskTimeline } from "./RiskTimeline";
import { SupplierComparison } from "./SupplierComparison";
import { AIInsightsPanel } from "./AIInsightsPanel";

// ── Supplier Risk Intelligence workspace ────────────────────────────────
// "Which suppliers represent the greatest operational risk?" — the
// central place to evaluate suppliers across every project. Supplier and
// project identity is real (useListSuppliers / useListProjects, the same
// endpoints suppliers.tsx and every project picker already use); every
// score, trend, issue, and AI insight layered on top is local demo data
// (see lib/mockSupplierRisk.ts + lib/useSupplierRisk.ts) until a real
// supplier-scoring backend exists — every surface below is labeled
// Demo Data / Illustrative Analysis, never presented as live.

function SectionTitle({ icon: Icon, children }: { icon: typeof Truck; children: React.ReactNode }) {
  return (
    <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5">
      <Icon className="w-4 h-4 text-primary" /> {children}
    </h3>
  );
}

function SupplierRiskSkeleton() {
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

export default function SupplierRiskIntelligence() {
  const { data: suppliers, isLoading: suppliersLoading, isError: suppliersError, refetch: refetchSuppliers } = useListSuppliers({ limit: 100 });
  const { data: projects } = useListProjects({ limit: 100 });

  const { data: snapshot, isLoading, isError, refetch, isRefetching } = useSupplierRisk(suppliers, projects);

  const [selectedSupplier, setSelectedSupplier] = useState<SupplierProfile | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [compareIds, setCompareIds] = useState<Set<number>>(new Set());

  const handleSelectSupplier = (supplier: SupplierProfile) => {
    setSelectedSupplier(supplier);
    setDrawerOpen(true);
  };

  const toggleCompare = (id: number) => {
    setCompareIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < 3) next.add(id);
      return next;
    });
  };

  if (suppliersLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-9 w-full max-w-md rounded-lg" />
        <SupplierRiskSkeleton />
      </div>
    );
  }

  if (suppliersError) {
    return (
      <ErrorState title="Unable to load suppliers" description="Check your connection and try again." action={
        <button className="text-xs font-medium text-primary hover:underline" onClick={() => refetchSuppliers()}>Retry</button>
      } />
    );
  }

  if (!suppliers?.length) {
    return <EmptyState icon={Truck} title="No suppliers yet" description="Supplier Risk Intelligence needs at least one registered supplier to evaluate." />;
  }

  const allProjectRefs = (projects ?? []).map((p) => ({ projectId: p.id, projectCode: p.project_code, projectName: p.project_name }));
  const comparedSuppliers = snapshot ? snapshot.suppliers.filter((s) => compareIds.has(s.id)) : [];
  const topRiskAlternatives = snapshot?.topHighRiskSuppliers[0]?.aiInsights.suggestedAlternatives ?? [];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <h2 className="text-lg font-semibold text-foreground">Supplier Risk Intelligence</h2>
            <DemoDataBadge />
          </div>
          <p className="text-sm text-muted-foreground max-w-2xl">
            Answers <span className="italic">"which suppliers represent the greatest operational risk?"</span> —
            delivery, quality, contract compliance, and financial stability across every registered supplier.
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
          <ErrorState title="Unable to load supplier risk analysis" description="Something went wrong generating the analysis." action={
            <button className="text-xs font-medium text-primary hover:underline" onClick={() => refetch()}>Retry</button>
          } />
        ) : (
          <SupplierRiskSkeleton />
        )
      ) : (
        <>
          {/* Executive Summary + Supplier Health Score */}
          <SupplierHealthOverview stats={snapshot.portfolioStats} summary={snapshot.executiveSummary} />

          {/* Top High Risk Suppliers */}
          <div className="space-y-3">
            <SectionTitle icon={AlertOctagon}>Top High Risk Suppliers</SectionTitle>
            <TopHighRiskSuppliers suppliers={snapshot.topHighRiskSuppliers} onSelect={handleSelectSupplier} />
          </div>

          {/* Portfolio distribution + risk timeline */}
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="panel panel-body space-y-3">
              <SectionTitle icon={PieChartIcon}>Portfolio Distribution</SectionTitle>
              <PortfolioDistribution distribution={snapshot.portfolioStats.riskDistribution} />
            </div>
            <div className="space-y-3">
              <SectionTitle icon={CalendarClock}>Risk Timeline</SectionTitle>
              <RiskTimeline events={snapshot.riskTimeline} referenceIso={snapshot.generatedAt} />
            </div>
          </div>

          {/* AI Insights Panel */}
          <AIInsightsPanel
            headline={snapshot.aiPortfolioInsights.headline}
            topRisks={snapshot.aiPortfolioInsights.topRisks}
            recommendedActions={snapshot.aiPortfolioInsights.recommendedActions}
            procurementObservations={snapshot.aiPortfolioInsights.procurementObservations}
            exampleAlternatives={topRiskAlternatives}
          />

          {/* Supplier comparison */}
          <div className="panel panel-body space-y-3">
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <SectionTitle icon={GitCompare}>Supplier Comparison</SectionTitle>
              {comparedSuppliers.length > 0 && (
                <button onClick={() => setCompareIds(new Set())} className="text-xs text-primary hover:underline">Clear comparison</button>
              )}
            </div>
            <SupplierComparison suppliers={comparedSuppliers} onRemove={toggleCompare} />
          </div>

          {/* Supplier directory */}
          <div className="space-y-3">
            <SectionTitle icon={Truck}>Supplier Directory</SectionTitle>
            <SupplierDirectory
              suppliers={snapshot.suppliers}
              allProjects={allProjectRefs}
              compareIds={compareIds}
              onToggleCompare={toggleCompare}
              onSelectSupplier={handleSelectSupplier}
            />
          </div>

          <p className="text-[11px] text-muted-foreground text-center">
            Analysis generated {new Date(snapshot.generatedAt).toLocaleString()} &middot; Demo Data / Illustrative Analysis &middot; not live AI.
          </p>
        </>
      )}

      <SupplierDetailDrawer supplier={selectedSupplier} open={drawerOpen} onOpenChange={setDrawerOpen} />
    </div>
  );
}
