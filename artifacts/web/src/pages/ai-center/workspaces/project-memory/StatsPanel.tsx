import {
  ResponsiveContainer, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip,
  AreaChart, Area,
} from "recharts";
import { BarChart2, Activity, LayoutGrid } from "lucide-react";
import type { MemoryCategory, ProjectMemoryStats } from "@/lib/mockProjectMemory";
import { SOURCE_META, SOURCE_TYPE_ORDER, CHART_TOOLTIP_STYLE } from "./shared";

const AXIS_TICK = { fontSize: 10, fill: "hsl(var(--muted-foreground))" };

// Memory Statistics + Knowledge Categories — the "how much do we know, and
// about what" view of the project. Same recharts + `.panel` conventions as
// dashboard/Charts.tsx (ResponsiveContainer, CHART_TOOLTIP_STYLE, no chart
// animation) so this reads as native to the rest of AMAD, not a bolted-on
// widget.

export function StatsPanel({
  stats,
  activeCategory,
  onCategoryClick,
}: {
  stats: ProjectMemoryStats;
  activeCategory: MemoryCategory | "all";
  onCategoryClick: (category: MemoryCategory | "all") => void;
}) {
  const bySourceData = SOURCE_TYPE_ORDER
    .map((type) => ({ type, label: SOURCE_META[type].label, value: stats.bySourceType[type] ?? 0, color: SOURCE_META[type].color }))
    .filter((d) => d.value > 0);

  const categories = Object.entries(stats.byCategory) as [MemoryCategory, number][];

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {/* By source type */}
      <div className="panel h-full">
        <div className="panel-header">
          <div className="flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-primary" />
            <span className="panel-title">Memory by Source Type</span>
          </div>
        </div>
        <div className="p-4 h-[220px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={bySourceData} layout="vertical" margin={{ top: 0, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--border))" />
              <XAxis type="number" tick={AXIS_TICK} axisLine={false} tickLine={false} allowDecimals={false} />
              <YAxis type="category" dataKey="label" width={84} tick={AXIS_TICK} axisLine={false} tickLine={false} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} cursor={{ fill: "hsl(var(--muted))", opacity: 0.4 }} />
              <Bar dataKey="value" radius={[0, 6, 6, 0]} isAnimationActive={false}>
                {bySourceData.map((d) => <Cell key={d.type} fill={d.color} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Activity over time */}
      <div className="panel h-full">
        <div className="panel-header">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary" />
            <span className="panel-title">Memory Activity</span>
          </div>
          <span className="text-[11px] text-muted-foreground">Items captured per week</span>
        </div>
        <div className="p-4 h-[220px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={stats.activityByWeek} margin={{ top: 8, right: 16, left: -16, bottom: 0 }}>
              <defs>
                <linearGradient id="pm-activity-fill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.35} />
                  <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
              <XAxis dataKey="weekLabel" tick={AXIS_TICK} axisLine={false} tickLine={false} />
              <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={24} allowDecimals={false} />
              <Tooltip contentStyle={CHART_TOOLTIP_STYLE} />
              <Area type="monotone" dataKey="count" stroke="hsl(var(--primary))" strokeWidth={2.5} fill="url(#pm-activity-fill)" isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Knowledge categories */}
      <div className="panel lg:col-span-2">
        <div className="panel-header">
          <div className="flex items-center gap-2">
            <LayoutGrid className="w-4 h-4 text-primary" />
            <span className="panel-title">Knowledge Categories</span>
          </div>
        </div>
        <div className="panel-body">
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
            <button
              type="button"
              onClick={() => onCategoryClick("all")}
              className={`rounded-lg border px-3 py-2.5 text-center transition-colors ${
                activeCategory === "all" ? "border-primary bg-primary/10" : "border-border hover:border-primary/40"
              }`}
            >
              <p className="text-lg font-bold text-foreground leading-none">{stats.total}</p>
              <p className="text-[10px] text-muted-foreground mt-1">All</p>
            </button>
            {categories.map(([category, count]) => (
              <button
                key={category}
                type="button"
                onClick={() => onCategoryClick(category)}
                className={`rounded-lg border px-3 py-2.5 text-center transition-colors ${
                  activeCategory === category ? "border-primary bg-primary/10" : "border-border hover:border-primary/40"
                }`}
              >
                <p className="text-lg font-bold text-foreground leading-none">{count}</p>
                <p className="text-[10px] text-muted-foreground mt-1">{category}</p>
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
