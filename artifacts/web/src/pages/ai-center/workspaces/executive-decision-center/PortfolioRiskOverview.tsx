import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from "recharts";
import { CHART_TOOLTIP_STYLE } from "./shared";

// Executive Decision Center Integration — previously took a `{band,
// count}[]` distribution computed from this page's own synthetic
// per-project risk score (Low/Medium/High/Critical bands unrelated to any
// other page's vocabulary). Now takes pre-colored `{name,value,color}[]`
// chart data — the caller (index.tsx) passes the exact same
// Excellent/Good/At Risk/Critical breakdown, from the same useExecutive()
// counts, that Dashboard's Portfolio Health donut already renders. Same
// donut-with-legend shape used elsewhere in the app so this reads as one
// consistent chart language across AMAD.

export function PortfolioRiskOverview({ data }: { data: { name: string; value: number; color: string }[] }) {
  const total = data.reduce((s, d) => s + d.value, 0);

  if (total === 0) return <p className="text-xs text-muted-foreground text-center py-8">No projects to distribute.</p>;

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
          <span className="text-[10px] text-muted-foreground mt-0.5">projects</span>
        </div>
      </div>
      <div className="flex-1 space-y-2 min-w-0">
        {data.map((d) => (
          <div key={d.name} className="flex items-center justify-between gap-2 text-xs">
            <span className="flex items-center gap-1.5 text-muted-foreground truncate"><span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: d.color }} /> {d.name}</span>
            <span className="font-semibold text-foreground tabular-nums shrink-0">{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
