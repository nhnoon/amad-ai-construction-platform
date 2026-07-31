import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";
import { CHART_TOOLTIP_STYLE } from "./shared";

const AXIS_TICK = { fontSize: 10, fill: "hsl(var(--muted-foreground))" };

export interface PriceSeries {
  key: string;
  label: string;
  color: string;
}

// Generic multi-line price/index chart — reused for the portfolio index,
// a category's materials, a single material's raw price, and the material
// comparison overlay, so there's one chart implementation instead of four
// near-identical ones.

export function PriceTrendChart({
  data,
  series,
  valueSuffix = "",
  height = 260,
}: {
  data: Record<string, number | string>[];
  series: PriceSeries[];
  valueSuffix?: string;
  height?: number;
}) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, left: -12, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
          <XAxis dataKey="period" tick={AXIS_TICK} axisLine={false} tickLine={false} />
          <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={40} />
          <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(value: number) => [`${value}${valueSuffix}`, ""]} />
          {series.length > 1 && <Legend wrapperStyle={{ fontSize: 11 }} />}
          {series.map((s) => (
            <Line key={s.key} type="monotone" dataKey={s.key} name={s.label} stroke={s.color} strokeWidth={2.25} dot={false} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
