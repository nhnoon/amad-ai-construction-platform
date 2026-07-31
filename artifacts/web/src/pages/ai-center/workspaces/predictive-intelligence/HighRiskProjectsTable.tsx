import { AlertTriangle } from "lucide-react";
import type { ProjectPrediction } from "@/lib/mockPredictiveIntelligence";
import { EmptyState } from "@/components/ui/empty-state";
import { CATEGORY_META, CATEGORY_ORDER, BAND_BADGE, heatColor } from "./shared";
import type { PredictionCategory } from "@/lib/mockPredictiveIntelligence";

// High Risk Projects table — every project ranked by overall predicted
// risk (highest first), with a per-category probability breakdown so an
// executive can see at a glance *which* forecast is driving each project's
// ranking. Clicking a row scopes the rest of the page to that project.

export function HighRiskProjectsTable({
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
  const sorted = [...projects].sort((a, b) => b.overallProbability - a.overallProbability);

  if (sorted.length === 0) {
    return <EmptyState icon={AlertTriangle} title="No projects match the current filters" />;
  }

  return (
    <div className="overflow-x-auto">
      <table className="data-table" data-testid="high-risk-projects-table">
        <thead>
          <tr>
            <th>Project</th>
            <th>Status</th>
            <th>Overall</th>
            {categories.map((c) => <th key={c} className="text-center">{CATEGORY_META[c].label}</th>)}
          </tr>
        </thead>
        <tbody>
          {sorted.map((p) => (
            <tr
              key={p.projectCode}
              onClick={() => onSelectProject(p.projectCode)}
              className={`cursor-pointer ${selectedProjectCode === p.projectCode ? "bg-primary/5" : ""}`}
              data-testid={`row-prediction-${p.projectCode}`}
            >
              <td>
                <p className="text-sm font-medium text-foreground">{p.projectCode}</p>
                <p className="text-xs text-muted-foreground truncate max-w-[220px]">{p.projectName}</p>
              </td>
              <td><span className="text-xs text-muted-foreground">{p.status}</span></td>
              <td>
                <div className="flex items-center gap-2">
                  <span className={`badge ${BAND_BADGE[p.overallBand]} text-[10px]`}>{p.overallBand}</span>
                  <span className="text-xs font-semibold tabular-nums" style={{ color: heatColor(p.overallProbability) }}>{p.overallProbability}%</span>
                </div>
              </td>
              {categories.map((c) => {
                const value = p.categories[c].probability;
                return (
                  <td key={c} className="text-center">
                    <span
                      className="inline-flex items-center justify-center min-w-[38px] rounded-md px-1.5 py-0.5 text-[11px] font-semibold tabular-nums"
                      style={{ backgroundColor: `${heatColor(value)}22`, color: heatColor(value) }}
                    >
                      {value}%
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
