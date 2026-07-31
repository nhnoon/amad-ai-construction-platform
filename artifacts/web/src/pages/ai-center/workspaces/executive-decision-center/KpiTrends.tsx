import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";
import type { KpiTrendPoint } from "@/lib/mockExecutiveDecisionCenter";
import { CHART_TOOLTIP_STYLE } from "./shared";

const AXIS_TICK = { fontSize: 10, fill: "hsl(var(--muted-foreground))" };

// KPI Trends — portfolio health, decision backlog, and critical alerts
// over the last 8 weeks, same recharts + tooltip conventions used across
// every other AI Center workspace.

export function KpiTrends({ data }: { data: KpiTrendPoint[] }) {
  return (
    <div className="h-[240px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
          <XAxis dataKey="period" tick={AXIS_TICK} axisLine={false} tickLine={false} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={28} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Line type="monotone" dataKey="portfolioHealth" name="Portfolio Health" stroke="#16a34a" strokeWidth={2.25} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="decisionBacklog" name="Decision Backlog" stroke="#eab308" strokeWidth={2.25} dot={false} isAnimationActive={false} />
          <Line type="monotone" dataKey="criticalAlerts" name="Critical Alerts" stroke="#dc2626" strokeWidth={2.25} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
