// ─────────────────────────────────────────────────────────────────────────
// MOCK / DEMO DATA — Supplier Risk Intelligence
//
// Everything in this file is synthetic and deterministic. Nothing here
// calls a model or a network. It exists so the Supplier Risk Intelligence
// workspace (pages/ai-center/workspaces/supplier-risk/) can be reviewed as
// a complete, investor-ready experience before a real supplier-scoring
// backend exists. Supplier and project identity (name, category, city,
// which projects exist) is real — every score, trend, issue, and AI
// insight layered on top of that identity is not.
//
// To wire this up later: implement a real supplier-scoring endpoint that
// returns a `SupplierRiskSnapshot`-shaped payload and replace the body of
// `loadSupplierRisk` in lib/useSupplierRisk.ts with a `fetch`/`useQuery`
// call. No component under pages/ai-center/workspaces/supplier-risk/ needs
// to change — they only ever consume that hook's `data`/`isLoading`/`isError`.
// ─────────────────────────────────────────────────────────────────────────

export type RiskBand = "Low" | "Medium" | "High" | "Critical";
export type ContractStatus = "Active" | "Expiring Soon" | "Under Negotiation" | "Expired";
export type IssueStatus = "Open" | "In Progress" | "Resolved";
export type ClaimStatus = "Pending" | "Approved" | "Rejected" | "Resolved";

export interface SupplierIssue {
  id: string;
  title: string;
  severity: RiskBand;
  status: IssueStatus;
  date: string;
}

export interface CorrectiveAction {
  id: string;
  title: string;
  status: "Open" | "Completed";
  date: string;
}

export interface SupplierClaim {
  id: string;
  title: string;
  amount: number;
  status: ClaimStatus;
  date: string;
}

export interface SupplierContract {
  id: string;
  title: string;
  value: number;
  status: ContractStatus;
  expiryDate: string;
}

export interface DeliveryRecord {
  id: string;
  date: string;
  orderRef: string;
  description: string;
  onTime: boolean;
  daysLate: number;
}

export interface PerformancePoint {
  weekLabel: string;
  delivery: number;      // 0-100
  quality: number;       // 0-100
  responseTimeHours: number;
  compliance: number;    // 0-100
}

export interface RiskBreakdownItem {
  label: string;
  score: number; // 0-100 contribution, higher = riskier
}

export interface ProjectRef {
  projectId: number;
  projectCode: string;
  projectName: string;
}

export interface SupplierAIInsights {
  topRisks: string[];
  recommendedActions: string[];
  suggestedAlternatives: { supplierId: number; name: string; riskScore: number }[];
  procurementObservations: string[];
}

export interface SupplierProfile {
  id: number;
  name: string;
  category: string;
  city: string;
  region: string;
  status: string; // real supplier status (Active/Inactive/Suspended)
  contractStatus: ContractStatus;
  contractExpiryDate: string;
  overallRiskScore: number; // 0-100, higher = riskier
  riskBand: RiskBand;
  deliveryPerformance: number; // 0-100, higher = better
  qualityScore: number; // 0-100, higher = better
  contractCompliance: number; // 0-100, higher = better
  financialStability: number; // 0-100, higher = better
  projectsServed: ProjectRef[];
  contracts: SupplierContract[];
  openIssues: SupplierIssue[];
  correctiveActions: CorrectiveAction[];
  claims: SupplierClaim[];
  paymentStatus: { onTimePct: number; averageDelayDays: number; outstandingAmountSar: number };
  deliveryHistory: DeliveryRecord[];
  performanceTrend: PerformancePoint[];
  riskBreakdown: RiskBreakdownItem[];
  aiInsights: SupplierAIInsights;
}

export interface SupplierRiskSnapshot {
  generatedAt: string;
  suppliers: SupplierProfile[];
  portfolioStats: {
    overallRiskScore: number;
    avgDeliveryPerformance: number;
    avgQualityScore: number;
    avgContractCompliance: number;
    avgFinancialStability: number;
    highRiskCount: number;
    riskDistribution: { band: RiskBand; count: number }[];
  };
  executiveSummary: { headline: string; bullets: string[] };
  topHighRiskSuppliers: SupplierProfile[];
  riskTimeline: {
    id: string; supplierId: number; supplierName: string; date: string;
    type: "issue" | "contract_expiry"; title: string; severity: RiskBand;
  }[];
  aiPortfolioInsights: { headline: string; topRisks: string[]; recommendedActions: string[]; procurementObservations: string[] };
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
  for (let i = 0; i < n && pool.length > 0; i++) {
    out.push(pool.splice(Math.floor(rand() * pool.length), 1)[0]);
  }
  return out;
}

const REGION_BY_CITY: Record<string, string> = {
  "Riyadh": "Central", "Al Kharj": "Central", "Qassim": "Central",
  "Jeddah": "Western", "Makkah": "Western", "Madinah": "Western", "Taif": "Western", "Rabigh": "Western",
  "Dammam": "Eastern", "Khobar": "Eastern", "Al Khobar": "Eastern", "Dhahran": "Eastern", "Jubail": "Eastern", "Ahsa": "Eastern",
  "Abha": "Southern", "Jazan": "Southern", "Najran": "Southern",
  "Tabuk": "Northern", "Hail": "Northern", "Al Jouf": "Northern",
};

function regionForCity(city: string | null | undefined): string {
  if (!city) return "Other";
  return REGION_BY_CITY[city] ?? "Other";
}

function bandFor(riskScore: number): RiskBand {
  if (riskScore >= 75) return "Critical";
  if (riskScore >= 55) return "High";
  if (riskScore >= 30) return "Medium";
  return "Low";
}

function isoDaysAgo(days: number, referenceMs: number): string {
  return new Date(referenceMs - days * 86_400_000).toISOString();
}
function isoDaysFromNow(days: number, referenceMs: number): string {
  return new Date(referenceMs + days * 86_400_000).toISOString();
}
function weekLabel(weeksAgo: number, referenceMs: number): string {
  return new Date(referenceMs - weeksAgo * 7 * 86_400_000).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

const ISSUE_POOL = [
  "Late delivery on critical-path rebar order", "Damaged materials received on last shipment",
  "Incomplete delivery documentation flagged by site QA", "Quality non-conformance on last batch inspection",
  "Delivery schedule not confirmed for upcoming milestone", "Invoice discrepancy against purchase order",
];
const ACTION_POOL = [
  "Supplier performance review scheduled with account manager", "Corrective action plan requested and under review",
  "Inspection sampling rate increased for incoming deliveries", "Delivery penalty clause added to next PO",
  "Root-cause analysis completed for the last non-conformance",
];
const CLAIM_POOL = [
  "Claim for short-delivered quantity on structural steel order", "Dispute over material specification compliance",
  "Claim for delivery delay liquidated damages", "Warranty claim for defective MEP components",
];
const TOP_RISK_POOL = [
  "Repeated late deliveries on critical-path materials over the last quarter",
  "Quality non-conformances trending above the acceptable threshold",
  "One or more corrective actions remain open past their target date",
  "Contract is expiring within 60 days with no renewal in progress",
  "An outstanding claim disputes delivered quantities or specification",
  "Financial stability indicators show working-capital strain",
  "This supplier is the sole qualified source for a critical material category",
  "Response time to RFQs and site RFIs has slowed over the last quarter",
];
const RECOMMENDED_ACTION_POOL = [
  "Schedule a supplier performance review with the account manager",
  "Request an updated financial statement and bank reference",
  "Begin qualifying a backup supplier in the same category",
  "Escalate the open corrective action to the supplier's management",
  "Start contract renewal negotiations ahead of the expiry window",
  "Tighten delivery penalty clauses in the next contract cycle",
  "Increase inspection sampling on incoming deliveries",
];
const OBSERVATION_POOL = [
  "Pricing remains competitive despite recent delivery slippage",
  "Two active projects currently depend on this supplier for the same material",
  "Supplier has historically responded well to corrective action requests",
  "The last claim against this supplier was resolved without recurrence",
  "Performance is notably stronger on smaller-scope orders",
  "This supplier's delivery performance has improved over the last quarter",
];

export const RISK_BREAKDOWN_LABELS = [
  "Delivery Risk", "Quality Risk", "Compliance Risk", "Financial Risk", "Claims & Issues Risk",
];

function buildPerformanceTrend(rand: () => number, delivery: number, quality: number, compliance: number, referenceMs: number): PerformancePoint[] {
  const points: PerformancePoint[] = [];
  let d = delivery, q = quality, c = compliance, r = 12 + rand() * 24;
  for (let w = 9; w >= 0; w--) {
    d = Math.max(10, Math.min(99, d + (rand() * 12 - 6)));
    q = Math.max(10, Math.min(99, q + (rand() * 10 - 5)));
    c = Math.max(10, Math.min(99, c + (rand() * 8 - 4)));
    r = Math.max(2, Math.min(96, r + (rand() * 10 - 5)));
    points.push({ weekLabel: weekLabel(w, referenceMs), delivery: Math.round(d), quality: Math.round(q), responseTimeHours: Math.round(r), compliance: Math.round(c) });
  }
  // pin the final point to the supplier's current headline numbers
  const last = points[points.length - 1];
  points[points.length - 1] = { ...last, delivery: Math.round(delivery), quality: Math.round(quality), compliance: Math.round(compliance) };
  return points;
}

/** Pure function — same suppliers + projects always produce the same
 * snapshot. Called by lib/useSupplierRisk.ts, the only place this touches
 * React. */
export function generateSupplierRisk(
  suppliers: { id: number; supplier_name: string; category: string | null; city: string | null; status: string }[],
  projects: { id: number; project_code: string; project_name: string }[],
  referenceMs: number = Date.UTC(2026, 6, 28),
): SupplierRiskSnapshot {
  const profiles: SupplierProfile[] = suppliers.map((supplier) => {
    const rand = mulberry32(hashString(`supplier::${supplier.id}::${supplier.supplier_name}`));

    const deliveryPerformance = Math.round(35 + rand() * 63);
    const qualityScore = Math.round(35 + rand() * 63);
    const contractCompliance = Math.round(35 + rand() * 63);
    const financialStability = Math.round(30 + rand() * 68);
    const overallRiskScore = Math.round(
      100 - (deliveryPerformance * 0.3 + qualityScore * 0.25 + contractCompliance * 0.25 + financialStability * 0.2),
    );
    const riskBand = bandFor(overallRiskScore);

    const projectsServed = projects.length
      ? pickN(rand, projects, Math.min(projects.length, 1 + Math.floor(rand() * 4)))
          .map((p) => ({ projectId: p.id, projectCode: p.project_code, projectName: p.project_name }))
      : [];

    const contracts: SupplierContract[] = projectsServed.slice(0, 3).map((p, i) => {
      const expiryDays = Math.floor(rand() * 220) - 30;
      const status: ContractStatus = expiryDays < 0 ? "Expired" : expiryDays < 45 ? "Expiring Soon" : rand() > 0.85 ? "Under Negotiation" : "Active";
      return {
        id: `${supplier.id}-ct-${i}`,
        title: `${supplier.category ?? "Supply"} Agreement — ${p.projectCode}`,
        value: Math.round((150_000 + rand() * 4_500_000) / 1000) * 1000,
        status,
        expiryDate: isoDaysFromNow(expiryDays, referenceMs),
      };
    });
    const primaryContractStatus: ContractStatus = contracts[0]?.status ?? (rand() > 0.7 ? "Expiring Soon" : "Active");
    const primaryExpiry = contracts[0]?.expiryDate ?? isoDaysFromNow(Math.floor(rand() * 180), referenceMs);

    const openIssues: SupplierIssue[] = pickN(rand, ISSUE_POOL, Math.floor(rand() * 4)).map((title, i) => ({
      id: `${supplier.id}-is-${i}`,
      title,
      severity: bandFor(Math.round(20 + rand() * 75)),
      status: pick(rand, ["Open", "In Progress", "Resolved"] as IssueStatus[]),
      date: isoDaysAgo(Math.floor(rand() * 60), referenceMs),
    }));

    const correctiveActions: CorrectiveAction[] = pickN(rand, ACTION_POOL, Math.floor(rand() * 3)).map((title, i) => ({
      id: `${supplier.id}-ca-${i}`,
      title,
      status: rand() > 0.4 ? "Completed" : "Open",
      date: isoDaysAgo(Math.floor(rand() * 90), referenceMs),
    }));

    const claims: SupplierClaim[] = pickN(rand, CLAIM_POOL, Math.floor(rand() * 3)).map((title, i) => ({
      id: `${supplier.id}-cl-${i}`,
      title,
      amount: Math.round((20_000 + rand() * 380_000) / 500) * 500,
      status: pick(rand, ["Pending", "Approved", "Rejected", "Resolved"] as ClaimStatus[]),
      date: isoDaysAgo(Math.floor(rand() * 120), referenceMs),
    }));

    const deliveryHistory: DeliveryRecord[] = Array.from({ length: 8 }, (_, i) => {
      const onTime = rand() > (overallRiskScore / 140);
      return {
        id: `${supplier.id}-dh-${i}`,
        date: isoDaysAgo(i * 12 + Math.floor(rand() * 5), referenceMs),
        orderRef: `PO-${2000 + supplier.id * 7 + i}`,
        description: `${supplier.category ?? "Material"} delivery`,
        onTime,
        daysLate: onTime ? 0 : 1 + Math.floor(rand() * 9),
      };
    });

    const performanceTrend = buildPerformanceTrend(rand, deliveryPerformance, qualityScore, contractCompliance, referenceMs);

    const riskBreakdown: RiskBreakdownItem[] = [
      { label: "Delivery Risk", score: 100 - deliveryPerformance },
      { label: "Quality Risk", score: 100 - qualityScore },
      { label: "Compliance Risk", score: 100 - contractCompliance },
      { label: "Financial Risk", score: 100 - financialStability },
      { label: "Claims & Issues Risk", score: Math.min(100, openIssues.length * 18 + claims.length * 12) },
    ];

    return {
      id: supplier.id,
      name: supplier.supplier_name,
      category: supplier.category ?? "General",
      city: supplier.city ?? "Unknown",
      region: regionForCity(supplier.city),
      status: supplier.status,
      contractStatus: primaryContractStatus,
      contractExpiryDate: primaryExpiry,
      overallRiskScore,
      riskBand,
      deliveryPerformance,
      qualityScore,
      contractCompliance,
      financialStability,
      projectsServed,
      contracts,
      openIssues,
      correctiveActions,
      claims,
      paymentStatus: {
        onTimePct: Math.round(50 + rand() * 48),
        averageDelayDays: Math.round(rand() * 18),
        outstandingAmountSar: Math.round((rand() * 850_000) / 1000) * 1000,
      },
      deliveryHistory,
      performanceTrend,
      riskBreakdown,
      // aiInsights filled in a second pass below, once every supplier's
      // score is known (so "suggested alternatives" can reference a real,
      // lower-risk supplier in the same category).
      aiInsights: { topRisks: [], recommendedActions: [], suggestedAlternatives: [], procurementObservations: [] },
    };
  });

  // ── Second pass: AI insights per supplier, incl. cross-supplier
  // alternatives — needs every profile's score, hence a second pass. ─────
  for (const profile of profiles) {
    const rand = mulberry32(hashString(`supplier-ai::${profile.id}`));
    const alternatives = profiles
      .filter((p) => p.id !== profile.id && p.category === profile.category && p.overallRiskScore < profile.overallRiskScore - 8)
      .sort((a, b) => a.overallRiskScore - b.overallRiskScore)
      .slice(0, 2)
      .map((p) => ({ supplierId: p.id, name: p.name, riskScore: p.overallRiskScore }));

    profile.aiInsights = {
      topRisks: pickN(rand, TOP_RISK_POOL, 2 + Math.floor(rand() * 2)),
      recommendedActions: pickN(rand, RECOMMENDED_ACTION_POOL, 2 + Math.floor(rand() * 2)),
      suggestedAlternatives: alternatives,
      procurementObservations: pickN(rand, OBSERVATION_POOL, 1 + Math.floor(rand() * 2)),
    };
  }

  // ── Portfolio rollups ────────────────────────────────────────────────
  const n = profiles.length || 1;
  const avg = (fn: (p: SupplierProfile) => number) => Math.round(profiles.reduce((s, p) => s + fn(p), 0) / n);
  const riskDistribution: { band: RiskBand; count: number }[] = (["Low", "Medium", "High", "Critical"] as RiskBand[])
    .map((band) => ({ band, count: profiles.filter((p) => p.riskBand === band).length }));

  const topHighRiskSuppliers = [...profiles].sort((a, b) => b.overallRiskScore - a.overallRiskScore).slice(0, 8);
  const highRiskCount = profiles.filter((p) => p.riskBand === "Critical" || p.riskBand === "High").length;

  const riskTimeline = [
    ...profiles.flatMap((p) => p.openIssues.filter((i) => i.status !== "Resolved").map((issue) => ({
      id: `tl-issue-${issue.id}`,
      supplierId: p.id,
      supplierName: p.name,
      date: issue.date,
      type: "issue" as const,
      title: issue.title,
      severity: issue.severity,
    }))),
    ...profiles
      .filter((p) => {
        const days = (new Date(p.contractExpiryDate).getTime() - referenceMs) / 86_400_000;
        return days >= 0 && days <= 90;
      })
      .map((p) => ({
        id: `tl-expiry-${p.id}`,
        supplierId: p.id,
        supplierName: p.name,
        date: p.contractExpiryDate,
        type: "contract_expiry" as const,
        title: `Contract expires — ${p.category} agreement`,
        severity: bandFor(p.overallRiskScore),
      })),
  ].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  const overallRiskScore = avg((p) => p.overallRiskScore);
  const topRiskSupplier = topHighRiskSuppliers[0];

  return {
    generatedAt: new Date(referenceMs).toISOString(),
    suppliers: profiles,
    portfolioStats: {
      overallRiskScore,
      avgDeliveryPerformance: avg((p) => p.deliveryPerformance),
      avgQualityScore: avg((p) => p.qualityScore),
      avgContractCompliance: avg((p) => p.contractCompliance),
      avgFinancialStability: avg((p) => p.financialStability),
      highRiskCount,
      riskDistribution,
    },
    executiveSummary: {
      headline: `${highRiskCount} of ${profiles.length} supplier${profiles.length === 1 ? "" : "s"} carry High or Critical risk, with an average portfolio risk score of ${overallRiskScore}/100.`,
      bullets: [
        topRiskSupplier
          ? `${topRiskSupplier.name} is the highest-risk supplier at ${topRiskSupplier.overallRiskScore}/100, serving ${topRiskSupplier.projectsServed.length} project${topRiskSupplier.projectsServed.length === 1 ? "" : "s"}.`
          : "No suppliers currently registered.",
        `${profiles.filter((p) => p.contractStatus === "Expiring Soon").length} supplier contract${profiles.filter((p) => p.contractStatus === "Expiring Soon").length === 1 ? "" : "s"} are expiring within 60 days.`,
        `${profiles.reduce((s, p) => s + p.openIssues.filter((i) => i.status !== "Resolved").length, 0)} open supplier issues across the portfolio.`,
        `${profiles.reduce((s, p) => s + p.claims.filter((c) => c.status === "Pending").length, 0)} pending supplier claims awaiting resolution.`,
      ],
    },
    topHighRiskSuppliers,
    riskTimeline,
    aiPortfolioInsights: {
      headline: `Supplier portfolio risk is trending ${overallRiskScore >= 55 ? "elevated" : "manageable"}, concentrated in ${topRiskSupplier?.category.toLowerCase() ?? "a small number of"} suppliers.`,
      topRisks: topHighRiskSuppliers.slice(0, 3).flatMap((p) => p.aiInsights.topRisks.slice(0, 1)),
      recommendedActions: [
        "Prioritize performance reviews for the top 3 high-risk suppliers this cycle",
        "Begin renewal conversations for all contracts expiring within 60 days",
        "Qualify at least one backup supplier per single-sourced material category",
      ],
      procurementObservations: pickN(mulberry32(hashString("portfolio-observations")), OBSERVATION_POOL, 3),
    },
  };
}
