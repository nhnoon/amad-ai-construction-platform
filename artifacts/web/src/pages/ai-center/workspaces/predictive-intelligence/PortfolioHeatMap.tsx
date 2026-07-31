import { Flame } from "lucide-react";
import type { PredictionCategory, ProjectPrediction } from "@/lib/mockPredictiveIntelligence";
import { EmptyState } from "@/components/ui/empty-state";
import { CATEGORY_META, CATEGORY_ORDER, heatColor } from "./shared";

// Portfolio Heat Map — every project x every forecast category, colored by
// predicted probability (green -> amber -> red). Answers "where across the
// whole portfolio is risk concentrated" in one glance, independent of
// which single project is currently selected elsewhere on the page.

export function PortfolioHeatMap({
  projects,
  activeCategories,
  selectedProjectCode,
  onSelectProject,
}: {
  projects: ProjectPrediction[];
  activeCategories: PredictionCategory[];
  selectedProjectCode: string | null;
  onSelectProject: (code: string) => void;
}) {
  const categories = activeCategories.length > 0 ? activeCategories : CATEGORY_ORDER;

  if (projects.length === 0) {
    return <EmptyState icon={Flame} title="No projects match the current filters" />;
  }

  return (
    <div className="overflow-x-auto">
      <div className="min-w-[560px]">
        <div className="grid gap-1" style={{ gridTemplateColumns: `160px repeat(${categories.length}, 1fr)` }}>
          <div />
          {categories.map((c) => {
            const Icon = CATEGORY_META[c].icon;
            return (
              <div key={c} className="flex flex-col items-center gap-1 px-1 pb-1.5">
                <Icon className="w-3.5 h-3.5 text-muted-foreground" />
                <span className="text-[10px] text-muted-foreground text-center leading-tight">{CATEGORY_META[c].label}</span>
              </div>
            );
          })}

          {projects.map((p) => (
            <div key={p.projectCode} className="contents">
              <button
                type="button"
                onClick={() => onSelectProject(p.projectCode)}
                className={`text-start px-2 py-1.5 rounded-md text-xs font-medium truncate transition-colors ${
                  selectedProjectCode === p.projectCode ? "bg-primary/10 text-primary" : "text-foreground hover:bg-muted/50"
                }`}
                title={`${p.projectCode} — ${p.projectName}`}
              >
                {p.projectCode}
              </button>
              {categories.map((c) => {
                const value = p.categories[c].probability;
                const color = heatColor(value);
                return (
                  <button
                    key={c}
                    type="button"
                    onClick={() => onSelectProject(p.projectCode)}
                    className="rounded-md m-0.5 flex items-center justify-center text-[11px] font-semibold tabular-nums text-white transition-transform hover:scale-[1.04]"
                    style={{ backgroundColor: color, minHeight: 30 }}
                    title={`${p.projectCode} · ${CATEGORY_META[c].label}: ${value}%`}
                  >
                    {value}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>
      <div className="flex items-center gap-2 justify-end mt-3 text-[10px] text-muted-foreground">
        <span>Low</span>
        <div className="h-2 w-32 rounded-full" style={{ background: "linear-gradient(90deg, hsl(142,72%,42%), hsl(45,72%,42%), hsl(0,72%,42%))" }} />
        <span>Critical</span>
      </div>
    </div>
  );
}
