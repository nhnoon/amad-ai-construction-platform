import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from "recharts";
import type { SupplierRiskSnapshot } from "@/lib/mockSupplierRisk";
import { BAND_COLOR, CHART_TOOLTIP_STYLE } from "./shared";

// Portfolio Distribution — how many suppliers fall into each risk band,
// same donut-with-legend shape as the Dashboard's Portfolio Health chart
// so this reads as a native AMAD chart, not a bolted-on widget.

export function PortfolioDistribution({ distribution }: { distribution: SupplierRiskSnapshot["portfolioStats"]["riskDistribution"] }) {
  const data = distribution.map((d) => ({ name: d.band, value: d.count, color: BAND_COLOR[d.band] }));
  const total = data.reduce((s, d) => s + d.value, 0);

  if (total === 0) {
    return <p className="text-xs text-muted-foreground text-center py-8">No suppliers to distribute.</p>;
  }

  return (
    <div className="flex items-center gap-4">
      <div className="relative h-32 w-32 shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={40} outerRadius={58} paddingAngle={3} strokeWidth={0} isAnimationActive={false}>
              {data.map((d, i) => <Cell key={i} fill={d.color} />)}
            </Pie>
            <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-black text-foreground leading-none tabular-nums">{total}</span>
          <span className="text-[10px] text-muted-foreground mt-0.5">suppliers</span>
        </div>
      </div>
      <div className="flex-1 space-y-2 min-w-0">
        {data.map((d) => (
          <div key={d.name} className="flex items-center justify-between gap-2 text-xs">
            <span className="flex items-center gap-1.5 text-muted-foreground truncate">
              <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: d.color }} /> {d.name}
            </span>
            <span className="font-semibold text-foreground tabular-nums shrink-0">{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
