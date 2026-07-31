import {
  ResponsiveContainer, PieChart, Pie, Cell, Tooltip,
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { BarChart2, HeartPulse, LayoutGrid, PieChart as PieChartIcon, TrendingUp } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { ACCENT, GLASS, GLASS_HEADER, CHART_TOOLTIP_STYLE, EXEC_SEV_COLOR, IconChip } from "./shared";
import type { RiskCategory } from "../../lib/useExecutive";
import type { PortfolioTrendPoint } from "../../lib/useExecutive";

const AXIS_TICK = { fontSize: 10, fill: "hsl(var(--muted-foreground))" };

// ── Portfolio Health — the only donut on the page ───────────────────────────

export function PortfolioHealthDonut({
  data, isLoading,
}: { data: { name: string; value: number; color: string }[]; isLoading?: boolean }) {
  if (isLoading) return <Skeleton className={`${GLASS} h-full min-h-[280px] w-full`} />;
  const total = data.reduce((s, d) => s + d.value, 0);

  return (
    <div className={`${GLASS} h-full`}>
      <div className={GLASS_HEADER}>
        <IconChip icon={HeartPulse} />
        <div>
          <span className="text-sm font-bold text-foreground block">Portfolio Health</span>
          <span className="text-[11px] text-muted-foreground">Projects scored by health level</span>
        </div>
      </div>
      {total === 0 ? (
        <ChartEmptyState icon={PieChartIcon} message="No scored projects yet" />
      ) : (
        <div className="relative p-4 flex items-center gap-4">
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
              <span className="text-[10px] text-muted-foreground mt-0.5">scored</span>
            </div>
          </div>
          <div className="flex-1 space-y-2.5 min-w-0">
            {data.map((d) => (
              <div key={d.name} className="flex items-center justify-between gap-2 text-xs">
                <span className="flex items-center gap-1.5 text-muted-foreground truncate">
                  <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
                  {d.name}
                </span>
                <span className="font-semibold text-foreground tabular-nums shrink-0">{d.value}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Project Status — a real bar chart, not a donut, so the two side-by-side
// don't compete visually for the same "circular chart" reading. ────────────

export function ProjectStatusChart({
  data, isLoading,
}: { data: { name: string; value: number; color: string }[]; isLoading?: boolean }) {
  if (isLoading) return <Skeleton className={`${GLASS} h-full min-h-[280px] w-full`} />;
  const total = data.reduce((s, d) => s + d.value, 0);

  return (
    <div className={`${GLASS} h-full`}>
      <div className={GLASS_HEADER}>
        <IconChip icon={LayoutGrid} />
        <div>
          <span className="text-sm font-bold text-foreground block">Project Status</span>
          <span className="text-[11px] text-muted-foreground">Portfolio breakdown by status</span>
        </div>
      </div>
      {total === 0 ? (
        <ChartEmptyState icon={LayoutGrid} message="No projects in the portfolio yet" />
      ) : (
        <div className="p-4 h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
              <XAxis dataKey="name" tick={AXIS_TICK} axisLine={false} tickLine={false} />
              <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} allowDecimals={false} width={28} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} cursor={{ fill: "hsl(var(--muted))", opacity: 0.4 }} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]} isAnimationActive={false}>
                {data.map((d, i) => <Cell key={i} fill={d.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

// ── Biggest Risks — horizontal bar chart, severity color retained
//    intentionally, this is the one place color-coding IS the information ──

export function BiggestRisksBarChart({
  data, isLoading,
}: { data?: RiskCategory[]; isLoading?: boolean }) {
  if (isLoading) return <Skeleton className={`${GLASS} h-full min-h-[280px] w-full`} />;
  const risks = (data ?? []).slice(0, 5);

  return (
    <div className={`${GLASS} h-full`}>
      <div className={GLASS_HEADER}>
        <IconChip icon={BarChart2} />
        <div>
          <span className="text-sm font-bold text-foreground block">Biggest Risks</span>
          <span className="text-[11px] text-muted-foreground">Top risk categories across the portfolio</span>
        </div>
      </div>
      {risks.length === 0 ? (
        <ChartEmptyState icon={BarChart2} message="No risks currently flagged" />
      ) : (
        <div className="p-4 h-[200px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={risks} layout="vertical" margin={{ top: 0, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--border))" />
              <XAxis type="number" tick={AXIS_TICK} axisLine={false} tickLine={false} allowDecimals={false} />
              <YAxis type="category" dataKey="label" width={88} tick={AXIS_TICK} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} cursor={{ fill: "hsl(var(--muted))", opacity: 0.4 }} />
              <Bar dataKey="count" radius={[0, 6, 6, 0]} isAnimationActive={false}>
                {risks.map((r, i) => <Cell key={i} fill={EXEC_SEV_COLOR[r.severity] ?? "#6b7280"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

// ── Portfolio Trend — daily score history. Only exists from whichever day
// the backend first recorded a snapshot (see backend/app/api/v1/
// executive.py) — no backfilled/fabricated history, so a fresh install
// shows the empty state below instead of a chart with one lonely dot. ─────

export function PortfolioTrendChart({
  points, isLoading,
}: { points?: PortfolioTrendPoint[]; isLoading?: boolean }) {
  if (isLoading) return <Skeleton className={`${GLASS} h-full min-h-[260px] w-full`} />;
  const data = points ?? [];

  return (
    <div className={GLASS}>
      <div className={GLASS_HEADER}>
        <IconChip icon={TrendingUp} />
        <div>
          <span className="text-sm font-bold text-foreground block">Portfolio Trend</span>
          <span className="text-[11px] text-muted-foreground">Daily portfolio score since tracking began</span>
        </div>
      </div>
      {data.length < 2 ? (
        <ChartEmptyState icon={TrendingUp} message="Trend builds up day by day — check back tomorrow" />
      ) : (
        <div className="p-4 h-[220px]">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 8, right: 16, left: -16, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
              <XAxis
                dataKey="date" tick={AXIS_TICK} axisLine={false} tickLine={false}
                tickFormatter={(d: string) => new Date(d).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
              />
              <YAxis domain={[0, 100]} tick={AXIS_TICK} axisLine={false} tickLine={false} width={28} />
              <Tooltip
                contentStyle={CHART_TOOLTIP_STYLE}
                labelFormatter={(d: string) => new Date(d).toLocaleDateString()}
              />
              <Line type="monotone" dataKey="score" stroke={ACCENT} strokeWidth={2.5} dot={{ r: 3, fill: ACCENT }} isAnimationActive={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

// ── Shared chart empty state ────────────────────────────────────────────────

function ChartEmptyState({ icon: Icon, message }: { icon: typeof HeartPulse; message: string }) {
  return (
    <div className="relative p-4 min-h-[130px] flex flex-col items-center justify-center text-center gap-2">
      <Icon className="w-8 h-8 text-muted-foreground/30" />
      <p className="text-xs text-muted-foreground">{message}</p>
    </div>
  );
}
