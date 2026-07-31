import { useMemo, useState } from "react";
import { Boxes } from "lucide-react";
import type { MaterialProfile, PriceTrend, ProjectRef, RiskLevel, SupplyStatus } from "@/lib/mockMaterialIntelligence";
import { EmptyState } from "@/components/ui/empty-state";
import { SearchInput } from "@/components/search-input";
import { FilterSelect } from "@/components/filter-select";
import { RISK_BADGE, SUPPLY_STATUS_BADGE, trendTone, formatPrice, formatPct } from "./shared";

const RISK_LEVELS: (RiskLevel | "all")[] = ["all", "Low", "Medium", "High", "Critical"];
const TRENDS: (PriceTrend | "all")[] = ["all", "Rising", "Stable", "Falling"];
const SUPPLY_STATUSES: (SupplyStatus | "all")[] = ["all", "Available", "Constrained", "Shortage"];

// Material Market Watch / Directory — search + filters (category, risk
// level, price trend, supply status, region, project exposure, supplier)
// over every monitored material. Row click opens the detail drawer;
// checkbox column feeds Material Comparison.

export function MaterialDirectory({
  materials,
  allProjects,
  compareIds,
  onToggleCompare,
  onSelectMaterial,
}: {
  materials: MaterialProfile[];
  allProjects: ProjectRef[];
  compareIds: Set<string>;
  onToggleCompare: (id: string) => void;
  onSelectMaterial: (material: MaterialProfile) => void;
}) {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [riskLevel, setRiskLevel] = useState<RiskLevel | "all">("all");
  const [trend, setTrend] = useState<PriceTrend | "all">("all");
  const [supplyStatus, setSupplyStatus] = useState<SupplyStatus | "all">("all");
  const [region, setRegion] = useState("all");
  const [projectCode, setProjectCode] = useState("all");
  const [supplierName, setSupplierName] = useState("all");

  const categories = useMemo(() => Array.from(new Set(materials.map((m) => m.category))).sort(), [materials]);
  const regions = useMemo(() => Array.from(new Set(materials.map((m) => m.region))).sort(), [materials]);
  const supplierNames = useMemo(() => Array.from(new Set(materials.flatMap((m) => m.suppliers.map((s) => s.name)))).sort(), [materials]);

  const filtered = materials.filter((m) => {
    if (category !== "all" && m.category !== category) return false;
    if (riskLevel !== "all" && m.riskLevel !== riskLevel) return false;
    if (trend !== "all" && m.priceTrend !== trend) return false;
    if (supplyStatus !== "all" && m.supplyStatus !== supplyStatus) return false;
    if (region !== "all" && m.region !== region) return false;
    if (projectCode !== "all" && !m.affectedProjects.some((p) => p.projectCode === projectCode)) return false;
    if (supplierName !== "all" && !m.suppliers.some((s) => s.name === supplierName)) return false;
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      if (!(m.name.toLowerCase().includes(q) || m.category.toLowerCase().includes(q))) return false;
    }
    return true;
  });

  const filtersActive = !!search || category !== "all" || riskLevel !== "all" || trend !== "all" || supplyStatus !== "all" || region !== "all" || projectCode !== "all" || supplierName !== "all";
  const clearFilters = () => {
    setSearch(""); setCategory("all"); setRiskLevel("all"); setTrend("all"); setSupplyStatus("all"); setRegion("all"); setProjectCode("all"); setSupplierName("all");
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <SearchInput value={search} onChange={setSearch} placeholder="Search materials by name or category..." testId="input-material-search" />
        <FilterSelect value={category} onChange={setCategory} className="w-44" ariaLabel="Material category">
          <option value="all">All categories</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </FilterSelect>
        <FilterSelect value={riskLevel} onChange={(v) => setRiskLevel(v as typeof riskLevel)} className="w-36" ariaLabel="Risk level">
          {RISK_LEVELS.map((r) => <option key={r} value={r}>{r === "all" ? "All risk levels" : `${r} risk`}</option>)}
        </FilterSelect>
        <FilterSelect value={trend} onChange={(v) => setTrend(v as typeof trend)} className="w-36" ariaLabel="Price trend">
          {TRENDS.map((t) => <option key={t} value={t}>{t === "all" ? "All trends" : t}</option>)}
        </FilterSelect>
        <FilterSelect value={supplyStatus} onChange={(v) => setSupplyStatus(v as typeof supplyStatus)} className="w-40" ariaLabel="Supply status">
          {SUPPLY_STATUSES.map((s) => <option key={s} value={s}>{s === "all" ? "All supply statuses" : s}</option>)}
        </FilterSelect>
        <FilterSelect value={region} onChange={setRegion} className="w-36" ariaLabel="Region">
          <option value="all">All regions</option>
          {regions.map((r) => <option key={r} value={r}>{r}</option>)}
        </FilterSelect>
        <FilterSelect value={projectCode} onChange={setProjectCode} className="w-48" ariaLabel="Project exposure">
          <option value="all">All projects</option>
          {allProjects.map((p) => <option key={p.projectId} value={p.projectCode}>{p.projectCode} — {p.projectName}</option>)}
        </FilterSelect>
        <FilterSelect value={supplierName} onChange={setSupplierName} className="w-44" ariaLabel="Supplier">
          <option value="all">All suppliers</option>
          {supplierNames.map((s) => <option key={s} value={s}>{s}</option>)}
        </FilterSelect>
        {filtersActive && <button onClick={clearFilters} className="text-xs text-primary hover:underline shrink-0">Clear filters</button>}
      </div>

      <div className="panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="data-table" data-testid="material-directory-table">
            <thead>
              <tr>
                <th className="w-10">Compare</th>
                <th className="min-w-[170px]">Material</th>
                <th>Category</th>
                <th>Price</th>
                <th>Unit</th>
                <th>30d</th>
                <th>90d</th>
                <th>Volatility</th>
                <th>Supply</th>
                <th>Lead Time</th>
                <th>Projects</th>
                <th>Primary Supplier</th>
                <th>Risk</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={13}>
                    <EmptyState icon={Boxes} title="No materials match the current filters" action={
                      <button onClick={clearFilters} className="text-xs font-medium text-primary hover:underline">Clear filters</button>
                    } />
                  </td>
                </tr>
              ) : (
                filtered.map((m) => (
                  <tr key={m.id} className="cursor-pointer" onClick={() => onSelectMaterial(m)} data-testid={`row-material-${m.id}`}>
                    <td onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={compareIds.has(m.id)}
                        onChange={() => onToggleCompare(m.id)}
                        disabled={!compareIds.has(m.id) && compareIds.size >= 3}
                        aria-label={`Compare ${m.name}`}
                        className="w-3.5 h-3.5 accent-primary"
                      />
                    </td>
                    <td className="text-sm font-semibold text-foreground">{m.name}</td>
                    <td className="text-muted-foreground text-sm">{m.category}</td>
                    <td className="text-sm tabular-nums">{formatPrice(m.currentPrice)}</td>
                    <td className="text-muted-foreground text-xs">/{m.unit}</td>
                    <td className={`text-sm font-medium tabular-nums ${trendTone(m.change30dPct > 0 ? "Rising" : m.change30dPct < 0 ? "Falling" : "Stable")}`}>{formatPct(m.change30dPct)}</td>
                    <td className={`text-sm font-medium tabular-nums ${trendTone(m.change90dPct > 0 ? "Rising" : m.change90dPct < 0 ? "Falling" : "Stable")}`}>{formatPct(m.change90dPct)}</td>
                    <td className="text-sm tabular-nums">{m.volatility}</td>
                    <td><span className={`badge ${SUPPLY_STATUS_BADGE[m.supplyStatus]} text-[10px]`}>{m.supplyStatus}</span></td>
                    <td className="text-sm tabular-nums">{m.avgLeadTimeDays}d</td>
                    <td className="text-sm text-muted-foreground">{m.affectedProjects.length}</td>
                    <td className="text-xs text-muted-foreground truncate max-w-[140px]">{m.suppliers[0]?.name ?? "—"}</td>
                    <td><span className={`badge ${RISK_BADGE[m.riskLevel]} text-[10px]`}>{m.riskLevel}</span></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      <p className="text-[11px] text-muted-foreground">{filtered.length} of {materials.length} materials &middot; select up to 3 to compare</p>
    </div>
  );
}
