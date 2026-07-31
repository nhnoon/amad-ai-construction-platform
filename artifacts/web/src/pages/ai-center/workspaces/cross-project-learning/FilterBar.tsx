import { useMemo } from "react";
import type { KnowledgeCategory, KnowledgeItem, RiskLevel } from "@/lib/mockCrossProjectLearning";
import { FilterSelect } from "@/components/filter-select";
import { CATEGORY_META, CATEGORY_ORDER, SOURCE_TYPE_META, SOURCE_TYPE_ORDER, DEPARTMENTS } from "./shared";

export interface KnowledgeFilters {
  category: KnowledgeCategory | "all";
  project: string; // project code
  source: string; // SourceType
  dateRange: "all" | "30" | "90" | "365";
  riskLevel: RiskLevel | "all";
  department: string;
  supplier: string;
  material: string;
}

export const DEFAULT_FILTERS: KnowledgeFilters = {
  category: "all", project: "all", source: "all", dateRange: "all",
  riskLevel: "all", department: "all", supplier: "all", material: "all",
};

const DATE_OPTIONS = [
  { value: "all", label: "All time" }, { value: "30", label: "Last 30 days" },
  { value: "90", label: "Last 90 days" }, { value: "365", label: "Last 12 months" },
];

// Knowledge Categories tile grid + the full filter row (project, source,
// date, risk level, department, supplier, material). Category is
// selected via the tiles (same "clickable count tile" pattern used by
// Project Memory's Knowledge Categories), so there's no redundant
// category dropdown alongside it.

export function FilterBar({
  items,
  categoryCounts,
  allProjects,
  filters,
  onChange,
  onClear,
}: {
  items: KnowledgeItem[];
  categoryCounts: Partial<Record<KnowledgeCategory, number>>;
  allProjects: { projectId: number; projectCode: string; projectName: string }[];
  filters: KnowledgeFilters;
  onChange: (patch: Partial<KnowledgeFilters>) => void;
  onClear: () => void;
}) {
  const supplierNames = useMemo(() => Array.from(new Set(items.map((i) => i.supplierName).filter(Boolean))).sort() as string[], [items]);
  const materialNames = useMemo(() => Array.from(new Set(items.map((i) => i.materialName).filter(Boolean))).sort() as string[], [items]);

  const filtersActive = Object.entries(filters).some(([k, v]) => v !== DEFAULT_FILTERS[k as keyof KnowledgeFilters]);

  return (
    <div className="space-y-3">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground mb-1.5">Knowledge Categories</p>
        <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-2">
          <button
            type="button"
            onClick={() => onChange({ category: "all" })}
            className={`rounded-lg border px-3 py-2.5 text-center transition-colors ${filters.category === "all" ? "border-primary bg-primary/10" : "border-border hover:border-primary/40"}`}
          >
            <p className="text-lg font-bold text-foreground leading-none">{items.length}</p>
            <p className="text-[10px] text-muted-foreground mt-1">All</p>
          </button>
          {CATEGORY_ORDER.filter((c) => (categoryCounts[c] ?? 0) > 0).map((c) => {
            const Icon = CATEGORY_META[c].icon;
            return (
              <button
                key={c}
                type="button"
                onClick={() => onChange({ category: filters.category === c ? "all" : c })}
                className={`rounded-lg border px-3 py-2.5 text-center transition-colors ${filters.category === c ? "border-primary bg-primary/10" : "border-border hover:border-primary/40"}`}
              >
                <Icon className="w-3.5 h-3.5 mx-auto text-muted-foreground mb-1" />
                <p className="text-sm font-bold text-foreground leading-none">{categoryCounts[c] ?? 0}</p>
                <p className="text-[10px] text-muted-foreground mt-1 truncate">{c}</p>
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <FilterSelect value={filters.project} onChange={(v) => onChange({ project: v })} className="w-48" ariaLabel="Project">
          <option value="all">All projects</option>
          {allProjects.map((p) => <option key={p.projectId} value={p.projectCode}>{p.projectCode} — {p.projectName}</option>)}
        </FilterSelect>
        <FilterSelect value={filters.source} onChange={(v) => onChange({ source: v })} className="w-36" ariaLabel="Source type">
          <option value="all">All sources</option>
          {SOURCE_TYPE_ORDER.map((s) => <option key={s} value={s}>{SOURCE_TYPE_META[s].label}</option>)}
        </FilterSelect>
        <FilterSelect value={filters.dateRange} onChange={(v) => onChange({ dateRange: v as KnowledgeFilters["dateRange"] })} className="w-36" ariaLabel="Date range">
          {DATE_OPTIONS.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
        </FilterSelect>
        <FilterSelect value={filters.riskLevel} onChange={(v) => onChange({ riskLevel: v as KnowledgeFilters["riskLevel"] })} className="w-36" ariaLabel="Risk level">
          <option value="all">All risk levels</option>
          {(["Low", "Medium", "High", "Critical"] as RiskLevel[]).map((r) => <option key={r} value={r}>{r}</option>)}
        </FilterSelect>
        <FilterSelect value={filters.department} onChange={(v) => onChange({ department: v })} className="w-40" ariaLabel="Department">
          <option value="all">All departments</option>
          {DEPARTMENTS.map((d) => <option key={d} value={d}>{d}</option>)}
        </FilterSelect>
        <FilterSelect value={filters.supplier} onChange={(v) => onChange({ supplier: v })} className="w-44" ariaLabel="Supplier">
          <option value="all">All suppliers</option>
          {supplierNames.map((s) => <option key={s} value={s}>{s}</option>)}
        </FilterSelect>
        <FilterSelect value={filters.material} onChange={(v) => onChange({ material: v })} className="w-44" ariaLabel="Material">
          <option value="all">All materials</option>
          {materialNames.map((m) => <option key={m} value={m}>{m}</option>)}
        </FilterSelect>
        {filtersActive && <button onClick={onClear} className="text-xs text-primary hover:underline shrink-0">Clear filters</button>}
      </div>
    </div>
  );
}
