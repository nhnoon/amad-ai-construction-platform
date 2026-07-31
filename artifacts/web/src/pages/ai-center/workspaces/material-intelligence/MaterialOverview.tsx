import { Boxes, AlertOctagon, TrendingUp, Wallet, PackageX, Clock3 } from "lucide-react";
import { StatTile } from "@/components/stat-tile";
import type { MaterialIntelligenceSnapshot } from "@/lib/mockMaterialIntelligence";
import { formatSar } from "./shared";

// Executive Material Overview — the six headline KPIs the spec calls out
// by name, first thing on the page.

export function MaterialOverview({ stats }: { stats: MaterialIntelligenceSnapshot["portfolioStats"] }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
      <StatTile icon={Boxes} label="Materials Monitored" value={stats.materialsMonitored} tone="neutral" />
      <StatTile icon={AlertOctagon} label="High-Risk Materials" value={stats.highRiskCount} tone={stats.highRiskCount > 0 ? "warning" : "success"} />
      <StatTile icon={TrendingUp} label="Avg Price Change" value={`${stats.avgPriceChange30d > 0 ? "+" : ""}${stats.avgPriceChange30d}%`} tone={stats.avgPriceChange30d > 3 ? "warning" : "neutral"} />
      <StatTile icon={Wallet} label="Portfolio Cost Exposure" value={formatSar(stats.totalExposureSar)} tone={stats.totalExposureSar > 0 ? "warning" : "success"} />
      <StatTile icon={PackageX} label="Supply Shortage Alerts" value={stats.shortageAlertCount} tone={stats.shortageAlertCount > 0 ? "danger" : "success"} />
      <StatTile icon={Clock3} label="Long Lead-Time Materials" value={stats.longLeadTimeCount} tone={stats.longLeadTimeCount > 0 ? "warning" : "success"} />
    </div>
  );
}
