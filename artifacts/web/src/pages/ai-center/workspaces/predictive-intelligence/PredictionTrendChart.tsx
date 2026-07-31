import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";
import { CHART_TOOLTIP_STYLE } from "./shared";

const AXIS_TICK = { fontSize: 10, fill: "hsl(var(--muted-foreground))" };

export interface TrendSeries {
  key: string;
  label: string;
  color: string;
}

// Generic multi-line trend chart — reused for the portfolio-wide 6-category
// trend and for a single project's "overall" trend line, so there is one
// chart implementation instead of two near-identical ones.

export function PredictionTrendChart({
  data,
  series,
}: {
  data: Record<string, number | string>[];
  series: TrendSeries[];
}) {
  return (
    <div className="h-[260px]">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
          <XAxis dataKey="weekLabel" tick={AXIS_TICK} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 100]} tick={AXIS_TICK} axisLine={false} tickLine={false} width={28} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(value: number) => [`${value}%`, ""]} />
          {series.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
          {series.map((s) => (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label}
              stroke={s.color}
              strokeWidth={2.25}
              dot={false}
              isAnimationActive={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
