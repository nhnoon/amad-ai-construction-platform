import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from "recharts";
import { BarChart2, HeartPulse, LayoutGrid, PieChart as PieChartIcon } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { GLASS, GLASS_HEADER, CHART_TOOLTIP_STYLE, EXEC_SEV_COLOR, IconChip } from "./shared";
import type { ExecutiveIntelligence } from "../../lib/useExecutive";

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
        <div className="relative p-5 flex items-center gap-5">
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
              <span className="text-[9px] text-muted-foreground mt-0.5">scored</span>
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

// ── Project Status — premium status cards, deliberately NOT a donut ────────

export function ProjectStatusCard({
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
        <div className="relative p-5 grid grid-cols-2 gap-3">
          {data.map((d) => {
            const pct = Math.round((d.value / total) * 100);
            return (
              <div
                key={d.name}
                className="rounded-2xl border border-border/50 dark:border-white/[0.05] bg-muted/30 dark:bg-white/[0.02] p-4"
              >
                <div className="flex items-center gap-2 mb-2.5">
                  <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: d.color }} />
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground truncate">{d.name}</span>
                </div>
                <div className="flex items-baseline gap-1.5">
                  <span className="text-2xl font-bold text-foreground tabular-nums leading-none">{d.value}</span>
                  <span className="text-[10px] text-muted-foreground">{pct}%</span>
                </div>
                <div className="h-1 rounded-full bg-muted/60 dark:bg-white/[0.06] overflow-hidden mt-2.5">
                  <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: d.color }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Biggest Risks — sparkline-style bars, severity color retained
//    intentionally, this is the one place color-coding IS the information ──

export function BiggestRisksCard({ data, isLoading }: { data?: ExecutiveIntelligence; isLoading: boolean }) {
  if (isLoading) return <Skeleton className={`${GLASS} h-full min-h-[280px] w-full`} />;
  const risks = data?.biggest_risks.slice(0, 5) ?? [];
  const max = Math.max(...risks.map((r) => r.count), 1);

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
        <div className="relative p-5 space-y-4">
          {risks.map((r) => {
            const color = EXEC_SEV_COLOR[r.severity] ?? "#6b7280";
            const pct = (r.count / max) * 100;
            return (
              <div key={r.category}>
                <div className="flex items-center justify-between text-xs mb-1.5">
                  <span className="text-muted-foreground truncate">{r.label}</span>
                  <span className="font-bold text-foreground tabular-nums shrink-0 ml-2">{r.count}</span>
                </div>
                <div className="h-1.5 rounded-full bg-muted/50 dark:bg-white/[0.05] overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Shared chart empty state ────────────────────────────────────────────────

function ChartEmptyState({ icon: Icon, message }: { icon: typeof BarChart2; message: string }) {
  return (
    <div className="relative p-5 min-h-[200px] flex flex-col items-center justify-center text-center gap-2">
      <Icon className="w-8 h-8 text-muted-foreground/30" />
      <p className="text-xs text-muted-foreground">{message}</p>
    </div>
  );
}
