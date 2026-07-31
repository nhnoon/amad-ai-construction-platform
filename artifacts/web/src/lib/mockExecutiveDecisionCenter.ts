// ─────────────────────────────────────────────────────────────────────────
// MOCK / DEMO DATA — Executive Decision Center
//
// Everything in this file is synthetic and deterministic. Nothing here
// calls a model or a network, and nothing here imports from the other AI
// Center workspaces' mock data files — this module is intentionally
// isolated, exactly like Project Memory, Predictive Intelligence,
// Supplier Risk Intelligence, Material Intelligence, and Cross-Project
// Learning each are from one another. The "Cross-module Highlights"
// section below illustrates what a real aggregation of those five
// modules would summarize — it does not actually read their data.
//
// To wire this up later: implement a real executive-aggregation endpoint
// (or a backend job that rolls up the five source modules once they are
// real) that returns an `ExecutiveDecisionSnapshot`-shaped payload and
// replace the body of `loadExecutiveDecisionCenter` in
// lib/useExecutiveDecisionCenter.ts with a `fetch`/`useQuery` call — or,
// once each source module has a real backend, aggregate their real hooks
// directly. No component under
// pages/ai-center/workspaces/executive-decision-center/ needs to change —
// they only ever consume that hook's `data`/`isLoading`/`isError`.
// ─────────────────────────────────────────────────────────────────────────

export type RiskBand = "Low" | "Medium" | "High" | "Critical";
export type Urgency = "Today" | "This Week" | "This Month";
export type Priority = "High" | "Medium" | "Low";
export type DecisionStatus = "Pending" | "Overdue" | "Scheduled";

export type SourceModule =
  | "Project Memory" | "Predictive Intelligence" | "Supplier Risk Intelligence"
  | "Material Intelligence" | "Cross-Project Learning" | "Executive Intelligence";

export interface PriorityItem {
  id: string;
  title: string;
  description: string;
  urgency: Urgency;
  module: SourceModule;
  projectId?: number;
  projectCode?: string;
  href: string;
}

export interface DecisionQueueItem {
  id: string;
  title: string;
  description: string;
  priority: Priority;
  status: DecisionStatus;
  dueDate: string;
  module: SourceModule;
  projectId?: number;
  projectCode?: string;
  requestedBy: string;
  estimatedImpact: string;
  href: string;
}

export interface ModuleHighlight {
  module: SourceModule;
  headline: string;
  metric: string;
  metricLabel: string;
  href: string;
}

export interface CriticalTimelineEvent {
  id: string;
  date: string;
  title: string;
  module: SourceModule;
  severity: RiskBand;
  projectId?: number;
  projectCode?: string;
}

export interface HeatMapRow {
  projectId: number;
  projectCode: string;
  projectName: string;
  schedule: number;
  budget: number;
  safety: number;
  supplier: number;
  material: number;
}

export interface AttentionProject {
  projectId: number;
  projectCode: string;
  projectName: string;
  riskBand: RiskBand;
  reasons: string[];
}

export interface RecommendedAction {
  id: string;
  title: string;
  description: string;
  priority: Priority;
  module: SourceModule;
  estimatedImpact: string;
}

export interface KpiTrendPoint {
  period: string;
  portfolioHealth: number;
  decisionBacklog: number;
  criticalAlerts: number;
}

export interface ExecutiveDecisionSnapshot {
  generatedAt: string;
  overview: {
    portfolioHealthScore: number;
    portfolioHealthBand: RiskBand;
    activeProjects: number;
    criticalAlerts: number;
    highRiskItems: number;
    pendingDecisions: number;
  };
  todaysPriorities: PriorityItem[];
  decisionQueue: DecisionQueueItem[];
  portfolioRisk: { band: RiskBand; count: number }[];
  aiExecutiveBrief: { headline: string; keyPoints: string[]; recommendations: string[] };
  moduleHighlights: ModuleHighlight[];
  criticalTimeline: CriticalTimelineEvent[];
  heatMapRows: HeatMapRow[];
  attentionProjects: AttentionProject[];
  recommendedActions: RecommendedAction[];
  kpiTrend: KpiTrendPoint[];
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
function pick<T>(rand: () => number, arr: T[]): T { return arr[Math.floor(rand() * arr.length)]; }
function pickN<T>(rand: () => number, arr: T[], n: number): T[] {
  const pool = [...arr];
  const out: T[] = [];
  for (let i = 0; i < n && pool.length > 0; i++) out.push(pool.splice(Math.floor(rand() * pool.length), 1)[0]);
  return out;
}
function bandFor(score: number): RiskBand {
  if (score >= 75) return "Critical";
  if (score >= 55) return "High";
  if (score >= 30) return "Medium";
  return "Low";
}
function isoDaysAgo(days: number, referenceMs: number): string { return new Date(referenceMs - days * 86_400_000).toISOString(); }
function isoDaysFromNow(days: number, referenceMs: number): string { return new Date(referenceMs + days * 86_400_000).toISOString(); }
function weekLabel(weeksAgo: number, referenceMs: number): string {
  return new Date(referenceMs - weeksAgo * 7 * 86_400_000).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

const MODULE_ROUTE: Record<SourceModule, string> = {
  "Project Memory": "/ai-center/project-memory",
  "Predictive Intelligence": "/ai-center/predictive-intelligence",
  "Supplier Risk Intelligence": "/ai-center/supplier-risk",
  "Material Intelligence": "/ai-center/material-intelligence",
  "Cross-Project Learning": "/ai-center/cross-project-learning",
  "Executive Intelligence": "/ai-center/executive",
};

const SOURCE_MODULES: SourceModule[] = [
  "Project Memory", "Predictive Intelligence", "Supplier Risk Intelligence", "Material Intelligence", "Cross-Project Learning",
];

const PRIORITY_TEMPLATES: { title: string; description: string; module: SourceModule; urgency: Urgency }[] = [
  { title: "Approve reinforcement steel price lock", description: "Forecast shows a further increase within 30 days — locking now avoids the projected overrun.", module: "Predictive Intelligence", urgency: "Today" },
  { title: "Review high-risk supplier performance", description: "A key supplier has crossed into Critical risk on delivery and quality metrics.", module: "Supplier Risk Intelligence", urgency: "Today" },
  { title: "Sign off on extension-of-time notice", description: "Contractual notice window closes this week — commercial team needs executive approval to file.", module: "Cross-Project Learning", urgency: "This Week" },
  { title: "Confirm copper cable bulk purchase", description: "Consolidating demand across projects before the forecast price spike requires budget approval.", module: "Material Intelligence", urgency: "Today" },
  { title: "Review recurring scaffold safety non-conformance", description: "The same safety issue has now recurred on a third project — a portfolio-wide directive may be warranted.", module: "Cross-Project Learning", urgency: "This Week" },
  { title: "Approve backup supplier qualification budget", description: "Reducing supplier concentration risk requires funding a qualification audit.", module: "Supplier Risk Intelligence", urgency: "This Month" },
];

const DECISION_TEMPLATES: { title: string; description: string; module: SourceModule; priority: Priority; requestedBy: string; estimatedImpact: string }[] = [
  { title: "Approve variation order — additional excavation works", description: "Client-directed additional excavation scope requires budget sign-off before work proceeds.", module: "Cross-Project Learning", priority: "High", requestedBy: "Commercial Director", estimatedImpact: "SAR 480K exposure" },
  { title: "Approve supplier switch — ready-mix concrete", description: "Recommended switch to a lower-risk supplier following repeated quality non-conformances.", module: "Supplier Risk Intelligence", priority: "High", requestedBy: "Procurement Lead", estimatedImpact: "Reduces quality risk 2 bands" },
  { title: "Approve early material purchase — HVAC equipment", description: "Locking pricing and delivery slot now avoids the forecast lead-time increase.", module: "Material Intelligence", priority: "Medium", requestedBy: "Procurement Lead", estimatedImpact: "SAR 210K avoided cost" },
  { title: "Approve schedule recovery plan", description: "Resequencing plan requires executive sign-off to reallocate crew across two projects.", module: "Predictive Intelligence", priority: "High", requestedBy: "Site Operations Director", estimatedImpact: "Protects milestone date" },
  { title: "Approve contract renewal — structural steel supplier", description: "Existing contract expires within 45 days; renewal terms are ready for review.", module: "Supplier Risk Intelligence", priority: "Medium", requestedBy: "Commercial Director", estimatedImpact: "Avoids supply gap" },
  { title: "Approve knowledge-share directive across projects", description: "A successful mitigation from one project should be mandated across two others facing the same issue.", module: "Cross-Project Learning", priority: "Low", requestedBy: "Quality Director", estimatedImpact: "Portfolio-wide risk reduction" },
];

const ACTION_TEMPLATES: { title: string; description: string; module: SourceModule; priority: Priority; estimatedImpact: string }[] = [
  { title: "Convene a portfolio risk review this week", description: "Three projects have crossed into Elevated or Critical risk since last cycle.", module: "Predictive Intelligence", priority: "High", estimatedImpact: "Early intervention window" },
  { title: "Qualify backup suppliers for concentrated categories", description: "Two material categories are single-sourced above the recommended concentration threshold.", module: "Supplier Risk Intelligence", priority: "High", estimatedImpact: "Reduces supply risk" },
  { title: "Mandate the standard payment-certificate checklist portfolio-wide", description: "The checklist reduced disputes wherever it was adopted — extend it to remaining projects.", module: "Cross-Project Learning", priority: "Medium", estimatedImpact: "Fewer payment disputes" },
  { title: "Lock pricing on the top 3 cost-exposure materials", description: "Forecast shows continued upward pressure on the highest-exposure material categories.", module: "Material Intelligence", priority: "High", estimatedImpact: "Avoided cost increase" },
  { title: "Review the Project Memory timeline for the two flagged projects", description: "Both projects show a cluster of open risks and pending approvals in the same period.", module: "Project Memory", priority: "Medium", estimatedImpact: "Faster decision cycle" },
];

/** Pure function — same project list always produces the same snapshot.
 * Called by lib/useExecutiveDecisionCenter.ts, the only place this
 * touches React. */
export function generateExecutiveDecisionCenter(
  projects: { id: number; project_code: string; project_name: string; status: string }[],
  referenceMs: number = Date.UTC(2026, 6, 28),
): ExecutiveDecisionSnapshot {
  if (projects.length === 0) {
    return {
      generatedAt: new Date(referenceMs).toISOString(),
      overview: { portfolioHealthScore: 0, portfolioHealthBand: "Low", activeProjects: 0, criticalAlerts: 0, highRiskItems: 0, pendingDecisions: 0 },
      todaysPriorities: [], decisionQueue: [], portfolioRisk: [], moduleHighlights: [], criticalTimeline: [],
      heatMapRows: [], attentionProjects: [], recommendedActions: [], kpiTrend: [],
      aiExecutiveBrief: { headline: "No active projects to summarize.", keyPoints: [], recommendations: [] },
    };
  }

  const rand = mulberry32(hashString("executive-decision-center"));

  // ── Per-project risk profile (drives heat map + attention list + risk chart)
  const projectRisk = projects.map((p) => {
    const pRand = mulberry32(hashString(`edc::${p.id}`));
    const schedule = Math.round(15 + pRand() * 80);
    const budget = Math.round(15 + pRand() * 80);
    const safety = Math.round(10 + pRand() * 70);
    const supplier = Math.round(10 + pRand() * 75);
    const material = Math.round(10 + pRand() * 75);
    const overall = Math.round((schedule + budget + safety + supplier + material) / 5);
    return { project: p, schedule, budget, safety, supplier, material, overall, band: bandFor(overall) };
  });

  const portfolioHealthScore = Math.round(100 - projectRisk.reduce((s, p) => s + p.overall, 0) / projectRisk.length);
  const portfolioHealthBand = bandFor(100 - portfolioHealthScore);
  const highRiskProjects = projectRisk.filter((p) => p.band === "High" || p.band === "Critical");

  // ── Today's priorities ──────────────────────────────────────────────
  const priorityCount = Math.min(PRIORITY_TEMPLATES.length, 4 + Math.floor(rand() * 3));
  const todaysPriorities: PriorityItem[] = pickN(rand, PRIORITY_TEMPLATES, priorityCount).map((tpl, i) => {
    const project = pick(rand, projects);
    return {
      id: `priority-${i}`, title: tpl.title, description: tpl.description, urgency: tpl.urgency, module: tpl.module,
      projectId: project.id, projectCode: project.project_code, href: MODULE_ROUTE[tpl.module],
    };
  });

  // ── Decision queue ───────────────────────────────────────────────────
  const decisionQueue: DecisionQueueItem[] = DECISION_TEMPLATES.map((tpl, i) => {
    const dRand = mulberry32(hashString(`edc-decision-${i}`));
    const project = pick(dRand, projects);
    const dueOffset = Math.floor(dRand() * 14) - 3;
    const status: DecisionStatus = dueOffset < 0 ? "Overdue" : dueOffset <= 3 ? "Pending" : "Scheduled";
    return {
      id: `decision-${i}`, title: tpl.title, description: tpl.description, priority: tpl.priority, status,
      dueDate: isoDaysFromNow(dueOffset, referenceMs), module: tpl.module, projectId: project.id, projectCode: project.project_code,
      requestedBy: tpl.requestedBy, estimatedImpact: tpl.estimatedImpact, href: MODULE_ROUTE[tpl.module],
    };
  });

  // ── Portfolio risk distribution ─────────────────────────────────────
  const portfolioRisk = (["Low", "Medium", "High", "Critical"] as RiskBand[]).map((band) => ({
    band, count: projectRisk.filter((p) => p.band === band).length,
  }));

  // ── Module highlights (cross-module summary) ────────────────────────
  const highlightRand = mulberry32(hashString("edc-highlights"));
  const moduleHighlights: ModuleHighlight[] = SOURCE_MODULES.map((module) => {
    const project = pick(highlightRand, projects);
    const templates: Record<SourceModule, { headline: string; metric: string; metricLabel: string }> = {
      "Project Memory": { headline: `${project.project_code} has ${3 + Math.floor(highlightRand() * 8)} open risks and pending approvals worth reviewing this cycle.`, metric: String(3 + Math.floor(highlightRand() * 8)), metricLabel: "open items" },
      "Predictive Intelligence": { headline: `Portfolio delay risk is trending up — ${1 + Math.floor(highlightRand() * 3)} projects forecast Elevated risk within 30 days.`, metric: `${1 + Math.floor(highlightRand() * 3)}`, metricLabel: "projects at risk" },
      "Supplier Risk Intelligence": { headline: `${1 + Math.floor(highlightRand() * 3)} suppliers now carry High or Critical risk across delivery and quality.`, metric: `${1 + Math.floor(highlightRand() * 3)}`, metricLabel: "high-risk suppliers" },
      "Material Intelligence": { headline: `Reinforcement steel and copper together account for the largest share of portfolio cost exposure this cycle.`, metric: `SAR ${(200 + highlightRand() * 600).toFixed(0)}K`, metricLabel: "cost exposure" },
      "Cross-Project Learning": { headline: `${2 + Math.floor(highlightRand() * 4)} issues have now recurred across more than one project — reusable mitigations exist for most of them.`, metric: `${2 + Math.floor(highlightRand() * 4)}`, metricLabel: "recurring patterns" },
      "Executive Intelligence": { headline: "Portfolio-wide AI insight, grounded in live records.", metric: "—", metricLabel: "" },
    };
    const t = templates[module];
    return { module, headline: t.headline, metric: t.metric, metricLabel: t.metricLabel, href: MODULE_ROUTE[module] };
  });

  // ── Critical decisions timeline ──────────────────────────────────────
  const timelineRand = mulberry32(hashString("edc-timeline"));
  const criticalTimeline: CriticalTimelineEvent[] = decisionQueue
    .map((d, i) => ({
      id: `tl-${i}`, date: d.dueDate, title: d.title, module: d.module, severity: d.priority === "High" ? "Critical" as RiskBand : d.priority === "Medium" ? "High" as RiskBand : "Medium" as RiskBand,
      projectId: d.projectId, projectCode: d.projectCode,
    }))
    .concat(highRiskProjects.slice(0, 3).map((p, i) => ({
      id: `tl-risk-${i}`, date: isoDaysFromNow(2 + Math.floor(timelineRand() * 10), referenceMs),
      title: `${p.project.project_code} risk review checkpoint`, module: "Predictive Intelligence" as SourceModule,
      severity: p.band, projectId: p.project.id, projectCode: p.project.project_code,
    })))
    .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  // ── Heat map ─────────────────────────────────────────────────────────
  const heatMapRows: HeatMapRow[] = projectRisk.map((p) => ({
    projectId: p.project.id, projectCode: p.project.project_code, projectName: p.project.project_name,
    schedule: p.schedule, budget: p.budget, safety: p.safety, supplier: p.supplier, material: p.material,
  }));

  // ── Attention projects ──────────────────────────────────────────────
  const reasonPool = [
    "Predicted delay risk trending upward", "High-risk supplier dependency on critical path",
    "Material cost exposure above portfolio average", "Recurring issue flagged by Cross-Project Learning",
    "Multiple pending executive decisions outstanding", "Safety risk score above acceptable threshold",
  ];
  const attentionProjects: AttentionProject[] = highRiskProjects
    .sort((a, b) => b.overall - a.overall)
    .slice(0, 6)
    .map((p) => {
      const aRand = mulberry32(hashString(`edc-attention-${p.project.id}`));
      return { projectId: p.project.id, projectCode: p.project.project_code, projectName: p.project.project_name, riskBand: p.band, reasons: pickN(aRand, reasonPool, 2 + Math.floor(aRand() * 2)) };
    });

  // ── Recommended actions ─────────────────────────────────────────────
  const recommendedActions: RecommendedAction[] = ACTION_TEMPLATES.map((tpl, i) => ({ id: `action-${i}`, ...tpl }));

  // ── KPI trend (8-week) ────────────────────────────────────────────────
  const trendRand = mulberry32(hashString("edc-kpi-trend"));
  let health = portfolioHealthScore, backlog = decisionQueue.length, alerts = highRiskProjects.length;
  const kpiTrend: KpiTrendPoint[] = [];
  for (let w = 7; w >= 0; w--) {
    health = Math.max(20, Math.min(95, health + (trendRand() * 8 - 4)));
    backlog = Math.max(0, Math.round(backlog + (trendRand() * 3 - 1.4)));
    alerts = Math.max(0, Math.round(alerts + (trendRand() * 2 - 1)));
    kpiTrend.push({ period: weekLabel(w, referenceMs), portfolioHealth: Math.round(health), decisionBacklog: backlog, criticalAlerts: alerts });
  }
  kpiTrend[kpiTrend.length - 1] = { ...kpiTrend[kpiTrend.length - 1], portfolioHealth: portfolioHealthScore, decisionBacklog: decisionQueue.length, criticalAlerts: highRiskProjects.length };

  const topAttention = attentionProjects[0];
  const overdueCount = decisionQueue.filter((d) => d.status === "Overdue").length;

  return {
    generatedAt: new Date(referenceMs).toISOString(),
    overview: {
      portfolioHealthScore, portfolioHealthBand,
      activeProjects: projects.filter((p) => p.status === "Active").length || projects.length,
      criticalAlerts: highRiskProjects.filter((p) => p.band === "Critical").length,
      highRiskItems: highRiskProjects.length,
      pendingDecisions: decisionQueue.filter((d) => d.status !== "Scheduled").length,
    },
    todaysPriorities,
    decisionQueue,
    portfolioRisk,
    aiExecutiveBrief: {
      headline: `Portfolio health is ${portfolioHealthBand === "Low" ? "strong" : portfolioHealthBand === "Medium" ? "stable with pockets of risk" : "under pressure"} at ${portfolioHealthScore}/100, with ${decisionQueue.length} decisions awaiting executive sign-off${overdueCount > 0 ? `, ${overdueCount} of them overdue` : ""}.`,
      keyPoints: [
        topAttention ? `${topAttention.projectCode} needs the most attention right now — ${topAttention.reasons[0].toLowerCase()}.` : "No project currently stands out as higher risk than the rest.",
        `${highRiskProjects.length} of ${projects.length} projects carry High or Critical risk across schedule, budget, safety, supplier, or material dimensions.`,
        `Cross-Project Learning shows recurring patterns with known mitigations — several open decisions could reuse a solution that already worked elsewhere.`,
      ],
      recommendations: [
        overdueCount > 0 ? `Clear the ${overdueCount} overdue decision${overdueCount === 1 ? "" : "s"} in the queue first — they are blocking downstream work.` : "Review the decision queue in priority order this week.",
        "Focus the next steering review on the projects flagged in the Executive Heat Map.",
        "Use Cross-Project Learning's recommended resolutions before approving new mitigation spend.",
      ],
    },
    moduleHighlights,
    criticalTimeline,
    heatMapRows,
    attentionProjects,
    recommendedActions,
    kpiTrend,
  };
}
