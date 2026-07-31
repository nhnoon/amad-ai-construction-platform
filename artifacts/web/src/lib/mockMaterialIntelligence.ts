// ─────────────────────────────────────────────────────────────────────────
// MOCK / DEMO DATA — Material Intelligence
//
// Everything in this file is synthetic and deterministic. Nothing here
// calls a model, an external market-data API, or a network. It exists so
// the Material Intelligence workspace
// (pages/ai-center/workspaces/material-intelligence/) can be reviewed as a
// complete, investor-ready experience before a real material-pricing
// backend or market-data integration exists. Project and supplier identity
// (which projects/suppliers exist) is real; every price, trend, forecast,
// alert, and AI insight layered on top is not — none of it should ever be
// read as a real market price.
//
// To wire this up later: implement a real material-pricing endpoint (or an
// external market-data integration) that returns a
// `MaterialIntelligenceSnapshot`-shaped payload and replace the body of
// `loadMaterialIntelligence` in lib/useMaterialIntelligence.ts with a
// `fetch`/`useQuery` call. No component under
// pages/ai-center/workspaces/material-intelligence/ needs to change — they
// only ever consume that hook's `data`/`isLoading`/`isError`.
// ─────────────────────────────────────────────────────────────────────────

export type RiskLevel = "Low" | "Medium" | "High" | "Critical";
export type PriceTrend = "Rising" | "Falling" | "Stable";
export type SupplyStatus = "Available" | "Constrained" | "Shortage";
export type LeadTimeTrend = "Increasing" | "Stable" | "Decreasing";
export type ProcurementStatus = "Not Started" | "In Progress" | "Locked" | "Completed";
export type AlertType =
  | "price_increase" | "delivery_delay" | "shortage" | "lead_time_increase"
  | "supplier_dependency" | "contract_expiry" | "unapproved_substitute";
export type OpportunityType =
  | "buy_early" | "lock_contract" | "consolidate_demand" | "switch_supplier"
  | "use_alternative" | "renegotiate_schedule" | "transfer_stock";

export interface PricePoint { period: string; price: number; }
export interface ForecastRange { best: number; expected: number; worst: number; }

export interface ProjectRef { projectId: number; projectCode: string; projectName: string; }

export interface MaterialProjectExposure {
  projectId: number;
  projectCode: string;
  projectName: string;
  plannedQuantity: number;
  baselineCost: number;
  currentCost: number;
  estimatedIncrease: number;
  exposureLevel: RiskLevel;
  procurementStatus: ProcurementStatus;
}

export interface MaterialSupplierShare {
  supplierId: number;
  name: string;
  shareOfSupplyPct: number;
}

export interface RiskBreakdownItem { label: string; score: number; }

export interface MaterialAIInsights {
  topRisks: string[];
  recommendedActions: string[];
  suggestedAlternatives: string[];
}

export interface MaterialProfile {
  id: string;
  name: string;
  category: string;
  unit: string;
  currentPrice: number;
  change30dPct: number;
  change90dPct: number;
  volatility: number; // 0-100
  priceTrend: PriceTrend;
  supplyStatus: SupplyStatus;
  avgLeadTimeDays: number;
  leadTimeTrend: LeadTimeTrend;
  riskLevel: RiskLevel;
  region: string;
  priceHistory: PricePoint[];
  forecast: ForecastRange;
  suppliers: MaterialSupplierShare[];
  affectedProjects: MaterialProjectExposure[];
  supplyRisks: { id: string; title: string; severity: RiskLevel; description: string }[];
  procurementIssues: { id: string; title: string; status: string; date: string }[];
  alternatives: { name: string; note: string }[];
  riskBreakdown: RiskBreakdownItem[];
  aiInsights: MaterialAIInsights;
  lastUpdated: string;
  source: string;
}

export interface CategorySummary {
  category: string;
  materialCount: number;
  avgChange30d: number;
  riskLevel: RiskLevel;
}

export interface SupplyChainAlert {
  id: string;
  type: AlertType;
  severity: RiskLevel;
  materialId: string;
  materialName: string;
  title: string;
  affectedProjects: ProjectRef[];
  estimatedImpactSar: number;
  recommendedAction: string;
  date: string;
  status: "Open" | "Acknowledged" | "Resolved";
}

export interface ProcurementOpportunity {
  id: string;
  type: OpportunityType;
  materialId: string;
  materialName: string;
  title: string;
  description: string;
  estimatedSavingSar: number;
  projects: string[];
  priority: "High" | "Medium" | "Low";
}

export interface MaterialRiskHeatRow {
  materialId: string;
  materialName: string;
  priceRisk: number;
  supplyRisk: number;
  leadTimeRisk: number;
  supplierConcentration: number;
  projectExposure: number;
}

export interface MaterialIntelligenceSnapshot {
  generatedAt: string;
  materials: MaterialProfile[];
  portfolioStats: {
    materialsMonitored: number;
    highRiskCount: number;
    avgPriceChange30d: number;
    totalExposureSar: number;
    shortageAlertCount: number;
    longLeadTimeCount: number;
  };
  categorySummaries: CategorySummary[];
  portfolioPriceTrend: { period: string; index: number }[];
  exposureRows: (MaterialProjectExposure & { materialId: string; materialName: string })[];
  riskHeatRows: MaterialRiskHeatRow[];
  alerts: SupplyChainAlert[];
  opportunities: ProcurementOpportunity[];
  aiPortfolioInsights: {
    headline: string;
    topRisks: string[];
    highestCostExposure: string[];
    emergingShortages: string[];
    recommendations: string[];
    suggestedAlternatives: string[];
    attentionProjects: { projectCode: string; projectName: string; reason: string }[];
  };
}

// ── Deterministic PRNG ──────────────────────────────────────────────────

function hashString(input: string): number {
  let h = 2166136261;
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function mulberry32(seed: number): () => number {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function pick<T>(rand: () => number, arr: T[]): T {
  return arr[Math.floor(rand() * arr.length)];
}
function pickN<T>(rand: () => number, arr: T[], n: number): T[] {
  const pool = [...arr];
  const out: T[] = [];
  for (let i = 0; i < n && pool.length > 0; i++) out.push(pool.splice(Math.floor(rand() * pool.length), 1)[0]);
  return out;
}

function bandFor(riskScore: number): RiskLevel {
  if (riskScore >= 75) return "Critical";
  if (riskScore >= 55) return "High";
  if (riskScore >= 30) return "Medium";
  return "Low";
}

function isoDaysAgo(days: number, referenceMs: number): string {
  return new Date(referenceMs - days * 86_400_000).toISOString();
}

function monthLabel(monthsAgo: number, referenceMs: number): string {
  const d = new Date(referenceMs);
  d.setUTCMonth(d.getUTCMonth() - monthsAgo);
  return d.toLocaleDateString(undefined, { month: "short", year: "2-digit" });
}

// ── Material catalog — the 15 suggested construction materials ─────────

interface MaterialSeed {
  id: string;
  name: string;
  category: string;
  unit: string;
  basePrice: number;
  region: string;
}

const MATERIAL_CATALOG: MaterialSeed[] = [
  { id: "ready-mix-concrete", name: "Ready-Mix Concrete", category: "Concrete & Cement", unit: "m³", basePrice: 280, region: "Central" },
  { id: "reinforcement-steel", name: "Reinforcement Steel", category: "Metals", unit: "ton", basePrice: 3200, region: "Eastern" },
  { id: "structural-steel", name: "Structural Steel", category: "Metals", unit: "ton", basePrice: 3600, region: "Eastern" },
  { id: "cement", name: "Cement", category: "Concrete & Cement", unit: "ton", basePrice: 260, region: "Central" },
  { id: "copper", name: "Copper", category: "Metals", unit: "ton", basePrice: 38_000, region: "Western" },
  { id: "aluminum", name: "Aluminum", category: "Metals", unit: "ton", basePrice: 9800, region: "Eastern" },
  { id: "electrical-cables", name: "Electrical Cables", category: "Electrical", unit: "meter", basePrice: 14, region: "Central" },
  { id: "glass", name: "Glass", category: "Finishes", unit: "m²", basePrice: 180, region: "Western" },
  { id: "timber", name: "Timber", category: "Finishes", unit: "m³", basePrice: 950, region: "Western" },
  { id: "gypsum-board", name: "Gypsum Board", category: "Finishes", unit: "sheet", basePrice: 32, region: "Central" },
  { id: "insulation", name: "Insulation", category: "Finishes", unit: "m²", basePrice: 45, region: "Central" },
  { id: "diesel", name: "Diesel", category: "Fuel & Bitumen", unit: "liter", basePrice: 0.55, region: "Eastern" },
  { id: "asphalt", name: "Asphalt", category: "Fuel & Bitumen", unit: "ton", basePrice: 420, region: "Eastern" },
  { id: "pvc-pipes", name: "PVC Pipes", category: "Piping", unit: "meter", basePrice: 22, region: "Central" },
  { id: "hvac-equipment", name: "HVAC Equipment", category: "Mechanical", unit: "unit", basePrice: 45_000, region: "Western" },
];

const SUPPLY_RISK_POOL: Record<string, string[]> = {
  "Concrete & Cement": ["Regional batching plant capacity constrained", "Cement clinker import dependency", "Peak-season demand outpacing supply"],
  Metals: ["Import tariff exposure on raw billet", "Global commodity price volatility", "Limited domestic mill capacity for this grade"],
  Electrical: ["Copper content drives cost volatility", "Single approved manufacturer for this spec"],
  Finishes: ["Import lead time from overseas manufacturer", "Limited local fabrication capacity"],
  "Fuel & Bitumen": ["Regional refinery output variability", "Transport cost sensitivity to fuel price itself"],
  Piping: ["Resin feedstock price exposure", "Import dependency for specialty fittings"],
  Mechanical: ["Long manufacturing lead time overseas", "Limited number of approved equipment brands"],
};

const PROCUREMENT_ISSUE_POOL = [
  "Purchase order pending supplier confirmation", "Delivery schedule not yet finalized for next phase",
  "Price validity on current quote expiring soon", "Quality certification pending for latest batch",
];

const ALTERNATIVE_POOL: Record<string, { name: string; note: string }[]> = {
  "Ready-Mix Concrete": [{ name: "Site-batched concrete", note: "Viable for smaller pours where batching plant access is constrained" }],
  "Reinforcement Steel": [{ name: "Fiber-reinforced polymer rebar", note: "Approved alternative for select non-structural applications" }],
  "Structural Steel": [{ name: "Precast concrete structural elements", note: "Alternative for select framing applications, subject to design review" }],
  Cement: [{ name: "Blended cement (fly ash)", note: "Lower-cost alternative meeting the same strength class" }],
  Copper: [{ name: "Aluminum conductor cable", note: "Approved substitute for select low-voltage runs" }],
  Aluminum: [{ name: "Galvanized steel framing", note: "Alternative for select cladding support applications" }],
  "Electrical Cables": [{ name: "Aluminum-core cable", note: "Cost-effective alternative for larger cross-sections" }],
  Glass: [{ name: "Locally fabricated glazing", note: "Shorter lead time, subject to spec approval" }],
  Timber: [{ name: "Engineered wood products", note: "More consistent supply than solid timber imports" }],
  "Gypsum Board": [{ name: "Fiber cement board", note: "Alternative for wet-area applications" }],
  Insulation: [{ name: "Mineral wool insulation", note: "Locally available alternative with comparable R-value" }],
  Diesel: [{ name: "Grid power connection", note: "Where available, reduces generator fuel dependency" }],
  Asphalt: [{ name: "Concrete paving", note: "Alternative for select access road applications" }],
  "PVC Pipes": [{ name: "HDPE piping", note: "Approved alternative with comparable cost profile" }],
  "HVAC Equipment": [{ name: "Locally assembled HVAC units", note: "Shorter lead time than imported equipment" }],
};

const TOP_RISK_TEMPLATES = (name: string, category: string) => [
  `${name} price has moved sharply over the last 90 days`,
  `Supply for ${name} is constrained relative to portfolio demand`,
  `Lead times for ${name} have lengthened, pressuring downstream schedules`,
  `${category} category shows concentrated exposure to a small supplier base`,
];

const RECOMMENDED_ACTION_TEMPLATES = (name: string) => [
  `Lock current pricing for ${name} on committed scope before the next review cycle`,
  `Qualify an additional supplier for ${name} to reduce concentration risk`,
  `Consolidate ${name} demand across projects into a single bulk order`,
  `Reassess the ${name} order schedule against the current lead-time trend`,
];

function buildPriceHistory(rand: () => number, basePrice: number, referenceMs: number): PricePoint[] {
  const points: PricePoint[] = [];
  let price = basePrice * (0.85 + rand() * 0.1);
  for (let m = 11; m >= 0; m--) {
    price = Math.max(basePrice * 0.6, price * (1 + (rand() * 0.1 - 0.045)));
    points.push({ period: monthLabel(m, referenceMs), price: Math.round(price * 100) / 100 });
  }
  points[points.length - 1] = { ...points[points.length - 1], price: Math.round(basePrice * 100) / 100 };
  return points;
}

/** Pure function — same suppliers + projects always produce the same
 * snapshot. Called by lib/useMaterialIntelligence.ts, the only place this
 * touches React. */
export function generateMaterialIntelligence(
  suppliers: { id: number; supplier_name: string; category: string | null }[],
  projects: { id: number; project_code: string; project_name: string }[],
  referenceMs: number = Date.UTC(2026, 6, 28),
): MaterialIntelligenceSnapshot {
  const materials: MaterialProfile[] = MATERIAL_CATALOG.map((seed) => {
    const rand = mulberry32(hashString(`material::${seed.id}`));

    const history = buildPriceHistory(rand, seed.basePrice, referenceMs);
    const currentPrice = history[history.length - 1].price;
    const price30dAgo = history[history.length - 2]?.price ?? currentPrice;
    const price90dAgo = history[history.length - 4]?.price ?? currentPrice;
    const change30dPct = Math.round(((currentPrice - price30dAgo) / price30dAgo) * 1000) / 10;
    const change90dPct = Math.round(((currentPrice - price90dAgo) / price90dAgo) * 1000) / 10;

    const volatility = Math.round(20 + rand() * 70);
    const priceTrend: PriceTrend = change30dPct > 2 ? "Rising" : change30dPct < -2 ? "Falling" : "Stable";
    const supplyStatus: SupplyStatus = rand() > 0.8 ? "Shortage" : rand() > 0.55 ? "Constrained" : "Available";
    const avgLeadTimeDays = Math.round(7 + rand() * 75);
    const leadTimeTrend: LeadTimeTrend = rand() > 0.6 ? "Increasing" : rand() > 0.3 ? "Stable" : "Decreasing";

    const priceRisk = Math.max(0, Math.min(100, Math.round(50 + change90dPct * 2 + volatility * 0.2)));
    const supplyRisk = supplyStatus === "Shortage" ? 80 + Math.round(rand() * 18) : supplyStatus === "Constrained" ? 45 + Math.round(rand() * 25) : Math.round(rand() * 30);
    const leadTimeRisk = Math.min(100, Math.round((avgLeadTimeDays / 90) * 100));

    // Suppliers — matched to real suppliers in the same category where
    // possible, generic fallback names otherwise so every material still
    // shows a plausible supplier base.
    const categorySuppliers = suppliers.filter((s) => (s.category ?? "").toLowerCase().includes(seed.category.split(" ")[0].toLowerCase()));
    const supplierPool = categorySuppliers.length > 0 ? categorySuppliers : suppliers;
    const chosenSuppliers = pickN(rand, supplierPool, Math.min(supplierPool.length, 2 + Math.floor(rand() * 2)));
    let remaining = 100;
    const supplierShares: MaterialSupplierShare[] = chosenSuppliers.map((s, i) => {
      const share = i === chosenSuppliers.length - 1 ? remaining : Math.min(remaining - (chosenSuppliers.length - i - 1) * 5, Math.round(15 + rand() * 40));
      remaining -= share;
      return { supplierId: s.id, name: s.supplier_name, shareOfSupplyPct: Math.max(5, share) };
    });
    const topShare = supplierShares[0]?.shareOfSupplyPct ?? 0;
    const supplierConcentration = Math.min(100, Math.round(topShare * 1.15));

    const affectedProjectRefs = projects.length
      ? pickN(rand, projects, Math.min(projects.length, 1 + Math.floor(rand() * 4)))
      : [];
    const affectedProjects: MaterialProjectExposure[] = affectedProjectRefs.map((p) => {
      const plannedQuantity = Math.round((50 + rand() * 950) * (seed.unit === "unit" ? 0.05 : 1));
      const baselinePrice = price90dAgo;
      const baselineCost = Math.round(plannedQuantity * baselinePrice);
      const currentCost = Math.round(plannedQuantity * currentPrice);
      const estimatedIncrease = currentCost - baselineCost;
      const exposureLevel = bandFor(Math.max(0, Math.min(100, 50 + (estimatedIncrease / Math.max(1, baselineCost)) * 200)));
      return {
        projectId: p.id,
        projectCode: p.project_code,
        projectName: p.project_name,
        plannedQuantity,
        baselineCost,
        currentCost,
        estimatedIncrease,
        exposureLevel,
        procurementStatus: pick(rand, ["Not Started", "In Progress", "Locked", "Completed"] as ProcurementStatus[]),
      };
    });

    const projectExposureScore = Math.min(100, affectedProjects.length * 16 + (affectedProjects.some((p) => p.exposureLevel === "Critical" || p.exposureLevel === "High") ? 20 : 0));

    const overallRiskScore = Math.round(priceRisk * 0.3 + supplyRisk * 0.25 + leadTimeRisk * 0.2 + supplierConcentration * 0.15 + projectExposureScore * 0.1);
    const riskLevel = bandFor(overallRiskScore);

    const supplyRisks = pickN(rand, SUPPLY_RISK_POOL[seed.category] ?? SUPPLY_RISK_POOL.Metals, 1 + Math.floor(rand() * 2)).map((title, i) => ({
      id: `${seed.id}-sr-${i}`, title, severity: bandFor(Math.round(30 + rand() * 65)), description: `Assessed against ${seed.name.toLowerCase()} demand across the current project portfolio.`,
    }));

    const procurementIssues = pickN(rand, PROCUREMENT_ISSUE_POOL, Math.floor(rand() * 3)).map((title, i) => ({
      id: `${seed.id}-pi-${i}`, title, status: pick(rand, ["Open", "In Progress", "Resolved"]), date: isoDaysAgo(Math.floor(rand() * 45), referenceMs),
    }));

    const forecastDrift = 0.03 + rand() * 0.12;
    const forecast: ForecastRange = {
      best: Math.round(currentPrice * (1 - forecastDrift * 0.6) * 100) / 100,
      expected: Math.round(currentPrice * (1 + forecastDrift * 0.3) * 100) / 100,
      worst: Math.round(currentPrice * (1 + forecastDrift * 1.6) * 100) / 100,
    };

    return {
      id: seed.id,
      name: seed.name,
      category: seed.category,
      unit: seed.unit,
      currentPrice,
      change30dPct,
      change90dPct,
      volatility,
      priceTrend,
      supplyStatus,
      avgLeadTimeDays,
      leadTimeTrend,
      riskLevel,
      region: seed.region,
      priceHistory: history,
      forecast,
      suppliers: supplierShares,
      affectedProjects,
      supplyRisks,
      procurementIssues,
      alternatives: ALTERNATIVE_POOL[seed.name] ?? [],
      riskBreakdown: [
        { label: "Price Risk", score: priceRisk },
        { label: "Supply Risk", score: supplyRisk },
        { label: "Lead-Time Risk", score: leadTimeRisk },
        { label: "Supplier Concentration", score: supplierConcentration },
        { label: "Project Exposure", score: projectExposureScore },
      ],
      aiInsights: {
        topRisks: pickN(rand, TOP_RISK_TEMPLATES(seed.name, seed.category), 2),
        recommendedActions: pickN(rand, RECOMMENDED_ACTION_TEMPLATES(seed.name), 2),
        suggestedAlternatives: (ALTERNATIVE_POOL[seed.name] ?? []).map((a) => a.name),
      },
      lastUpdated: isoDaysAgo(Math.floor(rand() * 5), referenceMs),
      source: "Illustrative Market Panel — Demo Data",
    };
  });

  // ── Portfolio rollups ────────────────────────────────────────────────
  const n = materials.length || 1;
  const highRiskCount = materials.filter((m) => m.riskLevel === "High" || m.riskLevel === "Critical").length;
  const avgPriceChange30d = Math.round((materials.reduce((s, m) => s + m.change30dPct, 0) / n) * 10) / 10;
  const totalExposureSar = materials.reduce((s, m) => s + m.affectedProjects.reduce((s2, p) => s2 + p.estimatedIncrease, 0), 0);
  const shortageAlertCount = materials.filter((m) => m.supplyStatus === "Shortage").length;
  const longLeadTimeCount = materials.filter((m) => m.avgLeadTimeDays >= 45).length;

  const categoryNames = Array.from(new Set(materials.map((m) => m.category)));
  const categorySummaries: CategorySummary[] = categoryNames.map((category) => {
    const inCategory = materials.filter((m) => m.category === category);
    const avgChange30d = Math.round((inCategory.reduce((s, m) => s + m.change30dPct, 0) / inCategory.length) * 10) / 10;
    const riskiest = inCategory.reduce((a, b) => (a.riskLevel === "Critical" || (a.riskLevel === "High" && b.riskLevel !== "Critical") ? a : b));
    return { category, materialCount: inCategory.length, avgChange30d, riskLevel: riskiest.riskLevel };
  });

  // Synthetic portfolio price index — base 100 at the earliest period,
  // weighted equally across every monitored material.
  const periods = materials[0]?.priceHistory.map((p) => p.period) ?? [];
  const portfolioPriceTrend = periods.map((period, i) => {
    const avgRatio = materials.reduce((s, m) => s + m.priceHistory[i].price / m.priceHistory[0].price, 0) / n;
    return { period, index: Math.round(avgRatio * 1000) / 10 };
  });

  const exposureRows = materials.flatMap((m) => m.affectedProjects.map((p) => ({ ...p, materialId: m.id, materialName: m.name })));

  const riskHeatRows: MaterialRiskHeatRow[] = materials.map((m) => ({
    materialId: m.id,
    materialName: m.name,
    priceRisk: m.riskBreakdown[0].score,
    supplyRisk: m.riskBreakdown[1].score,
    leadTimeRisk: m.riskBreakdown[2].score,
    supplierConcentration: m.riskBreakdown[3].score,
    projectExposure: m.riskBreakdown[4].score,
  }));

  // ── Supply chain alerts — realistic named scenarios from the spec ─────
  const alertRand = mulberry32(hashString("material-alerts"));
  const findMaterial = (id: string) => materials.find((m) => m.id === id)!;
  const alertTemplates: { type: AlertType; materialId: string; title: string; action: string }[] = [
    { type: "price_increase", materialId: "reinforcement-steel", title: "Reinforcement steel price increase detected", action: "Lock pricing on committed scope before the next quote cycle" },
    { type: "delivery_delay", materialId: "cement", title: "Cement delivery delay reported by primary supplier", action: "Confirm buffer stock and expedite the next scheduled order" },
    { type: "shortage", materialId: "copper", title: "Copper shortage affecting electrical procurement", action: "Evaluate aluminum-core cable as an approved substitute" },
    { type: "lead_time_increase", materialId: "hvac-equipment", title: "Imported HVAC equipment lead time has increased", action: "Reassess order dates against the updated manufacturer lead time" },
    { type: "supplier_dependency", materialId: "structural-steel", title: "Supplier dependency risk — concentrated structural steel supply", action: "Qualify a second structural steel supplier this quarter" },
    { type: "contract_expiry", materialId: "asphalt", title: "Material supply contract nearing expiry", action: "Begin renewal negotiations ahead of the expiry date" },
    { type: "unapproved_substitute", materialId: "pvc-pipes", title: "Unapproved substitute material flagged on site", action: "Confirm specification compliance before further installation" },
  ];
  const alerts: SupplyChainAlert[] = alertTemplates.map((tpl, i) => {
    const material = findMaterial(tpl.materialId);
    const affected = material.affectedProjects.slice(0, 2).map((p) => ({ projectId: p.projectId, projectCode: p.projectCode, projectName: p.projectName }));
    return {
      id: `alert-${i}`,
      type: tpl.type,
      severity: material.riskLevel,
      materialId: material.id,
      materialName: material.name,
      title: tpl.title,
      affectedProjects: affected,
      estimatedImpactSar: Math.round((5_000 + alertRand() * 480_000) / 500) * 500,
      recommendedAction: tpl.action,
      date: isoDaysAgo(Math.floor(alertRand() * 21), referenceMs),
      status: pick(alertRand, ["Open", "Acknowledged", "Resolved"]),
    };
  });

  // ── Procurement opportunities ──────────────────────────────────────────
  const oppRand = mulberry32(hashString("material-opportunities"));
  const opportunityTemplates: { type: OpportunityType; materialId: string; title: string; description: string }[] = [
    { type: "buy_early", materialId: "reinforcement-steel", title: "Buy early — reinforcement steel", description: "Forecast shows further increases; locking volume now avoids the projected rise." },
    { type: "lock_contract", materialId: "cement", title: "Lock contract price — cement", description: "Current supplier offer is below the 90-day forecast expected price." },
    { type: "consolidate_demand", materialId: "electrical-cables", title: "Consolidate demand — electrical cables", description: "Multiple projects are ordering separately; a combined order improves unit pricing." },
    { type: "switch_supplier", materialId: "copper", title: "Switch supplier — copper", description: "An alternate supplier offers comparable lead time at a lower current price." },
    { type: "use_alternative", materialId: "structural-steel", title: "Use approved alternative — structural steel", description: "Precast alternative is viable for select scope, reducing steel exposure." },
    { type: "renegotiate_schedule", materialId: "hvac-equipment", title: "Renegotiate delivery schedule — HVAC equipment", description: "Shifting delivery earlier avoids the manufacturer's forecast lead-time increase." },
    { type: "transfer_stock", materialId: "gypsum-board", title: "Transfer stock between projects — gypsum board", description: "One project is overstocked while another has an open shortfall." },
  ];
  const opportunities: ProcurementOpportunity[] = opportunityTemplates.map((tpl, i) => {
    const material = findMaterial(tpl.materialId);
    return {
      id: `opportunity-${i}`,
      type: tpl.type,
      materialId: material.id,
      materialName: material.name,
      title: tpl.title,
      description: tpl.description,
      estimatedSavingSar: Math.round((8_000 + oppRand() * 320_000) / 500) * 500,
      projects: material.affectedProjects.slice(0, 3).map((p) => p.projectCode),
      priority: pick(oppRand, ["High", "Medium", "Low"]),
    };
  });

  const topRiskMaterials = [...materials].sort((a, b) =>
    (b.riskBreakdown.reduce((s, r) => s + r.score, 0)) - (a.riskBreakdown.reduce((s, r) => s + r.score, 0)),
  ).slice(0, 5);
  const topExposureMaterials = [...materials].sort((a, b) =>
    b.affectedProjects.reduce((s, p) => s + p.estimatedIncrease, 0) - a.affectedProjects.reduce((s, p) => s + p.estimatedIncrease, 0),
  ).slice(0, 3);
  const shortageMaterials = materials.filter((m) => m.supplyStatus === "Shortage" || m.leadTimeTrend === "Increasing").slice(0, 3);

  const attentionProjectsMap = new Map<string, { projectCode: string; projectName: string; reason: string }>();
  for (const m of topRiskMaterials.slice(0, 3)) {
    for (const p of m.affectedProjects) {
      if (p.exposureLevel === "Critical" || p.exposureLevel === "High") {
        if (!attentionProjectsMap.has(p.projectCode)) {
          attentionProjectsMap.set(p.projectCode, { projectCode: p.projectCode, projectName: p.projectName, reason: `${m.name} cost exposure` });
        }
      }
    }
  }

  return {
    generatedAt: new Date(referenceMs).toISOString(),
    materials,
    portfolioStats: { materialsMonitored: materials.length, highRiskCount, avgPriceChange30d, totalExposureSar, shortageAlertCount, longLeadTimeCount },
    categorySummaries,
    portfolioPriceTrend,
    exposureRows,
    riskHeatRows,
    alerts,
    opportunities,
    aiPortfolioInsights: {
      headline: `${highRiskCount} of ${materials.length} monitored materials carry High or Critical risk, with average 30-day price movement of ${avgPriceChange30d >= 0 ? "+" : ""}${avgPriceChange30d}% across the portfolio.`,
      topRisks: topRiskMaterials.slice(0, 3).map((m) => `${m.name}: ${m.aiInsights.topRisks[0]}`),
      highestCostExposure: topExposureMaterials.map((m) => `${m.name} — SAR ${Math.round(m.affectedProjects.reduce((s, p) => s + p.estimatedIncrease, 0)).toLocaleString()} estimated increase across ${m.affectedProjects.length} project${m.affectedProjects.length === 1 ? "" : "s"}`),
      emergingShortages: shortageMaterials.map((m) => `${m.name} — ${m.supplyStatus.toLowerCase()}, lead time ${m.leadTimeTrend.toLowerCase()}`),
      recommendations: [
        "Prioritize price locks for the top 3 highest cost-exposure materials this cycle",
        "Qualify backup suppliers for materials with supplier concentration above 60%",
        "Review procurement opportunities below before the next purchasing cycle",
      ],
      suggestedAlternatives: topRiskMaterials.flatMap((m) => m.aiInsights.suggestedAlternatives.slice(0, 1)).slice(0, 3),
      attentionProjects: Array.from(attentionProjectsMap.values()).slice(0, 5),
    },
  };
}
