import { useMemo, useState } from "react";
import { Truck } from "lucide-react";
import type { ProjectRef, RiskBand, SupplierProfile } from "@/lib/mockSupplierRisk";
import { EmptyState } from "@/components/ui/empty-state";
import { SearchInput } from "@/components/search-input";
import { FilterSelect } from "@/components/filter-select";
import { BAND_BADGE, CONTRACT_STATUS_BADGE, heatColor } from "./shared";

const RISK_LEVELS: (RiskBand | "all")[] = ["all", "Low", "Medium", "High", "Critical"];

// Supplier Directory — search + filters (projects served, risk level,
// material category, region, contract status) over every supplier, with
// an optional compare checkbox. This is the one place suppliers are
// browsed rather than ranked — Top High Risk Suppliers stays unfiltered
// on purpose so this panel's filters don't silently hide it.

export function SupplierDirectory({
  suppliers,
  allProjects,
  compareIds,
  onToggleCompare,
  onSelectSupplier,
}: {
  suppliers: SupplierProfile[];
  allProjects: ProjectRef[];
  compareIds: Set<number>;
  onToggleCompare: (id: number) => void;
  onSelectSupplier: (supplier: SupplierProfile) => void;
}) {
  const [search, setSearch] = useState("");
  const [riskLevel, setRiskLevel] = useState<RiskBand | "all">("all");
  const [category, setCategory] = useState("all");
  const [region, setRegion] = useState("all");
  const [contractStatus, setContractStatus] = useState("all");
  const [projectCode, setProjectCode] = useState("all");

  const categories = useMemo(() => Array.from(new Set(suppliers.map((s) => s.category))).sort(), [suppliers]);
  const regions = useMemo(() => Array.from(new Set(suppliers.map((s) => s.region))).sort(), [suppliers]);
  const contractStatuses = useMemo(() => Array.from(new Set(suppliers.map((s) => s.contractStatus))).sort(), [suppliers]);

  const filtered = suppliers.filter((s) => {
    if (riskLevel !== "all" && s.riskBand !== riskLevel) return false;
    if (category !== "all" && s.category !== category) return false;
    if (region !== "all" && s.region !== region) return false;
    if (contractStatus !== "all" && s.contractStatus !== contractStatus) return false;
    if (projectCode !== "all" && !s.projectsServed.some((p) => p.projectCode === projectCode)) return false;
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      if (!(s.name.toLowerCase().includes(q) || s.category.toLowerCase().includes(q) || s.city.toLowerCase().includes(q))) return false;
    }
    return true;
  });

  const filtersActive = !!search || riskLevel !== "all" || category !== "all" || region !== "all" || contractStatus !== "all" || projectCode !== "all";
  const clearFilters = () => { setSearch(""); setRiskLevel("all"); setCategory("all"); setRegion("all"); setContractStatus("all"); setProjectCode("all"); };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <SearchInput value={search} onChange={setSearch} placeholder="Search suppliers by name, category, or city..." testId="input-supplier-search" />
        <FilterSelect value={riskLevel} onChange={(v) => setRiskLevel(v as typeof riskLevel)} className="w-36" ariaLabel="Risk level">
          {RISK_LEVELS.map((r) => <option key={r} value={r}>{r === "all" ? "All risk levels" : `${r} risk`}</option>)}
        </FilterSelect>
        <FilterSelect value={category} onChange={setCategory} className="w-44" ariaLabel="Material category">
          <option value="all">All categories</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </FilterSelect>
        <FilterSelect value={region} onChange={setRegion} className="w-36" ariaLabel="Region">
          <option value="all">All regions</option>
          {regions.map((r) => <option key={r} value={r}>{r}</option>)}
        </FilterSelect>
        <FilterSelect value={contractStatus} onChange={setContractStatus} className="w-44" ariaLabel="Contract status">
          <option value="all">All contract statuses</option>
          {contractStatuses.map((c) => <option key={c} value={c}>{c}</option>)}
        </FilterSelect>
        <FilterSelect value={projectCode} onChange={setProjectCode} className="w-48" ariaLabel="Project served">
          <option value="all">All projects served</option>
          {allProjects.map((p) => <option key={p.projectId} value={p.projectCode}>{p.projectCode} — {p.projectName}</option>)}
        </FilterSelect>
        {filtersActive && <button onClick={clearFilters} className="text-xs text-primary hover:underline shrink-0">Clear filters</button>}
      </div>

      <div className="panel overflow-hidden">
        <div className="overflow-x-auto">
          <table className="data-table" data-testid="supplier-directory-table">
            <thead>
              <tr>
                <th className="w-10">Compare</th>
                <th className="min-w-[180px]">Supplier</th>
                <th>Category</th>
                <th>Region</th>
                <th>Risk</th>
                <th>Delivery</th>
                <th>Quality</th>
                <th>Contract</th>
                <th>Projects</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={9}>
                    <EmptyState icon={Truck} title="No suppliers match the current filters" action={
                      <button onClick={clearFilters} className="text-xs font-medium text-primary hover:underline">Clear filters</button>
                    } />
                  </td>
                </tr>
              ) : (
                filtered.map((s) => (
                  <tr key={s.id} className="cursor-pointer" onClick={() => onSelectSupplier(s)} data-testid={`row-supplier-${s.id}`}>
                    <td onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={compareIds.has(s.id)}
                        onChange={() => onToggleCompare(s.id)}
                        disabled={!compareIds.has(s.id) && compareIds.size >= 3}
                        aria-label={`Compare ${s.name}`}
                        className="w-3.5 h-3.5 accent-primary"
                      />
                    </td>
                    <td>
                      <p className="text-sm font-semibold text-foreground">{s.name}</p>
                      <p className="text-xs text-muted-foreground">{s.city}</p>
                    </td>
                    <td className="text-muted-foreground text-sm">{s.category}</td>
                    <td className="text-muted-foreground text-sm">{s.region}</td>
                    <td>
                      <div className="flex items-center gap-1.5">
                        <span className={`badge ${BAND_BADGE[s.riskBand]} text-[10px]`}>{s.riskBand}</span>
                        <span className="text-xs font-semibold tabular-nums" style={{ color: heatColor(s.overallRiskScore) }}>{s.overallRiskScore}</span>
                      </div>
                    </td>
                    <td className="text-sm tabular-nums">{s.deliveryPerformance}%</td>
                    <td className="text-sm tabular-nums">{s.qualityScore}%</td>
                    <td><span className={`badge ${CONTRACT_STATUS_BADGE[s.contractStatus]} text-[10px]`}>{s.contractStatus}</span></td>
                    <td className="text-sm text-muted-foreground">{s.projectsServed.length}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      <p className="text-[11px] text-muted-foreground">{filtered.length} of {suppliers.length} suppliers &middot; select up to 3 to compare</p>
    </div>
  );
}
