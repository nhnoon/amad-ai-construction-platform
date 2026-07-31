// ─────────────────────────────────────────────────────────────────────────
// MOCK / DEMO DATA — Predictive Construction Intelligence
//
// Everything in this file is synthetic and deterministic. Nothing here
// calls a model or a network. It exists so the Predictive Intelligence
// workspace (pages/ai-center/workspaces/predictive-intelligence/) can be
// reviewed as a complete, investor-ready experience before a real
// forecasting backend exists.
//
// To wire this up later: implement a real prediction endpoint (or model)
// that returns a `PredictivePortfolioSnapshot`-shaped payload and replace
// the body of `loadPredictiveIntelligence` in lib/usePredictiveIntelligence.ts
// with a `fetch`/`useQuery` call. No component in
// pages/ai-center/workspaces/predictive-intelligence/ needs to change —
// they only ever consume that hook's `data`/`isLoading`/`isError`.
// ─────────────────────────────────────────────────────────────────────────

export type PredictionCategory =
  | "delay" | "budget_overrun" | "cash_flow" | "claim" | "safety" | "schedule";

export type ConfidenceLevel = "low" | "medium" | "high";
export type ForecastTrend = "up" | "down" | "flat";
export type ScenarioCase = "best" | "expected" | "worst";
export type RiskBand = "Low" | "Moderate" | "Elevated" | "Critical";
export type PredictionOutcome = "occurred" | "avoided" | "pending";

export interface CategoryPrediction {
  category: PredictionCategory;
  probability: number; // 0-100
  confidence: ConfidenceLevel;
  trend: ForecastTrend;
  trendDeltaPts: number; // change vs 4 weeks ago, can be negative
  contributingFactors: string[];
  recommendedActions: string[];
}

export interface ScenarioOutcome {
  case: ScenarioCase;
  completionDateOffsetDays: number; // vs current planned finish, +late / -early
  budgetVariancePct: number; // + over budget
  riskScore: number; // 0-100, lower is better
  narrative: string;
}

export interface TimelineEvent {
  id: string;
  projectId: number;
  projectCode: string;
  projectName: string;
  date: string; // ISO, in the future relative to generatedAt
  category: PredictionCategory;
  severity: RiskBand;
  description: string;
}

export interface EmergingRisk {
  id: string;
  projectId: number;
  projectCode: string;
  projectName: string;
  category: PredictionCategory;
  probability: number;
  deltaPts: number; // week-over-week increase
  description: string;
}

export interface PredictionHistoryEntry {
  id: string;
  date: string; // ISO, in the past
  projectId: number;
  projectCode: string;
  projectName: string;
  category: PredictionCategory;
  predictedBand: RiskBand;
  predictedProbability: number;
  outcome: PredictionOutcome;
  note: string;
}

export interface ProjectPrediction {
  projectId: number;
  projectCode: string;
  projectName: string;
  status: string;
  categories: Record<PredictionCategory, CategoryPrediction>;
  overallProbability: number; // 0-100 aggregate across categories
  overallBand: RiskBand;
  scenarios: ScenarioOutcome[];
  timeline: TimelineEvent[];
  trend: { weekLabel: string; overall: number }[];
}

export interface PredictivePortfolioSnapshot {
  generatedAt: string;
  projects: ProjectPrediction[];
  categoryPredictions: Record<PredictionCategory, CategoryPrediction>;
  overallForecast: { score: number; band: RiskBand; narrative: string };
  trend: { weekLabel: string; delay: number; budget_overrun: number; cash_flow: number; claim: number; safety: number; schedule: number }[];
  scenarios: ScenarioOutcome[];
  emergingRisks: EmergingRisk[];
  predictionHistory: PredictionHistoryEntry[];
  aiRecommendations: { headline: string; keyFindings: string[]; recommendations: string[] };
}

// ── Deterministic PRNG — identical inputs always render identical demo
// output; different projects/categories look visibly different. ──────────

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
    const idx = Math.floor(rand() * pool.length);
    out.push(pool.splice(idx, 1)[0]);
  }
  return out;
}

export const CATEGORY_ORDER: PredictionCategory[] = [
  "delay", "budget_overrun", "cash_flow", "claim", "safety", "schedule",
];

export const CATEGORY_LABEL: Record<PredictionCategory, string> = {
  delay: "Project Delay",
  budget_overrun: "Budget Overrun",
  cash_flow: "Cash Flow Risk",
  claim: "Claim Probability",
  safety: "Safety Risk",
  schedule: "Schedule Risk",
};

const FACTOR_POOL: Record<PredictionCategory, string[]> = {
  delay: [
    "Concrete supplier single-source dependency", "Adverse weather forecast for the coming weeks",
    "Permit or inspection approval pending", "Subcontractor mobilization behind schedule",
    "Design revision awaiting approval", "Long-lead equipment delivery uncertain",
  ],
  budget_overrun: [
    "Material price escalation (steel / rebar / cement)", "Unapproved variation orders accumulating",
    "Provisional sums trending above original estimate", "Currency exchange exposure on imported materials",
    "Overtime and acceleration labor costs rising", "Rework cost from quality non-conformances",
  ],
  cash_flow: [
    "Client interim payment certificate delayed", "High retention held against completed milestones",
    "Subcontractor advance payments outstanding", "Slow variation order approvals delaying billing",
    "Extended payment terms from client", "Front-loaded procurement outpacing certified progress",
  ],
  claim: [
    "Differing site conditions identified", "Cumulative delay approaching contractual notice threshold",
    "Scope ambiguity in contract documents", "Unresolved RFIs affecting the critical path",
    "Client-directed changes without formal instruction", "Latent condition discovered during excavation",
  ],
  safety: [
    "Incident rate trending above portfolio average", "Overdue safety inspections",
    "New subcontractor with limited safety track record", "High-risk activity phase underway (height / excavation / lifting)",
    "Reduced safety staffing on night shift", "Heat stress risk during peak summer months",
  ],
  schedule: [
    "Critical path activities behind baseline", "Float consumption above threshold on key chains",
    "Resequencing risk from an upstream delay", "Long-lead item delivery uncertainty",
    "Interface dependency with a parallel contractor", "Design coordination clashes still open",
  ],
};

const ACTION_POOL: Record<PredictionCategory, string[]> = {
  delay: [
    "Qualify a backup supplier for the at-risk material", "Escalate permit follow-up with the issuing authority",
    "Add a resequencing buffer to the master schedule", "Formalize the subcontractor mobilization recovery plan",
  ],
  budget_overrun: [
    "Lock remaining material pricing with forward contracts", "Tighten the variation-order approval workflow",
    "Reforecast cost-to-complete this reporting period", "Review provisional sums against latest market quotes",
  ],
  cash_flow: [
    "Escalate the outstanding payment certificate with the client", "Negotiate reduced retention on completed milestones",
    "Accelerate variation-order sign-off to unlock billing", "Review subcontractor payment terms against project cash-in timing",
  ],
  claim: [
    "File the extension-of-time notice within the contractual window", "Compile the differing-conditions evidence package",
    "Request formal written instruction for directed changes", "Engage the commercial team for an early claim assessment",
  ],
  safety: [
    "Increase inspection frequency for the high-risk activity", "Refresh toolbox talks for the affected crews",
    "Audit the subcontractor's safety induction records", "Add supervisory coverage to the night shift",
  ],
  schedule: [
    "Rebaseline the critical path with a recovery plan", "Expedite procurement of the long-lead item",
    "Add schedule float to the interface milestone", "Convene a recovery-schedule workshop with subcontractors",
  ],
};

function confidenceFor(rand: () => number): ConfidenceLevel {
  const r = rand();
  if (r < 0.45) return "high";
  if (r < 0.8) return "medium";
  return "low";
}

function bandFor(probability: number): RiskBand {
  if (probability >= 75) return "Critical";
  if (probability >= 55) return "Elevated";
  if (probability >= 30) return "Moderate";
  return "Low";
}

function isoDaysFromNow(days: number, referenceMs: number): string {
  return new Date(referenceMs + days * 86_400_000).toISOString();
}

function isoDaysAgo(days: number, referenceMs: number): string {
  return new Date(referenceMs - days * 86_400_000).toISOString();
}

function weekLabelFromOffset(weeksAgo: number, referenceMs: number): string {
  return new Date(referenceMs - weeksAgo * 7 * 86_400_000).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function buildTrend(rand: () => number, baseProbability: number, referenceMs: number): { weekLabel: string; value: number }[] {
  const points: { weekLabel: string; value: number }[] = [];
  let value = Math.max(5, Math.min(95, baseProbability - (rand() * 20 - 10)));
  for (let w = 9; w >= 0; w--) {
    value = Math.max(5, Math.min(95, value + (rand() * 14 - 7)));
    points.push({ weekLabel: weekLabelFromOffset(w, referenceMs), value: Math.round(value) });
  }
  // Force the final point toward the intended current baseProbability so the
  // chart's "now" reading matches the prediction cards above it.
  points[points.length - 1] = { weekLabel: points[points.length - 1].weekLabel, value: Math.round(baseProbability) };
  return points;
}

function buildScenarios(rand: () => number, expectedProbability: number, expectedBudgetVariance: number): ScenarioOutcome[] {
  const bestShift = 14 + Math.round(rand() * 8);
  const worstShift = 14 + Math.round(rand() * 12);
  return [
    {
      case: "best",
      completionDateOffsetDays: -Math.round(6 + rand() * 8),
      budgetVariancePct: Math.max(0, Math.round((expectedBudgetVariance - bestShift * 0.3) * 10) / 10),
      riskScore: Math.max(5, Math.round(expectedProbability - bestShift)),
      narrative: "Mitigation actions land on time, backup suppliers qualify, and no new risks emerge.",
    },
    {
      case: "expected",
      completionDateOffsetDays: Math.round(rand() * 6),
      budgetVariancePct: Math.round(expectedBudgetVariance * 10) / 10,
      riskScore: Math.round(expectedProbability),
      narrative: "Current trajectory continues — open risks are managed but not fully resolved.",
    },
    {
      case: "worst",
      completionDateOffsetDays: Math.round(18 + worstShift),
      budgetVariancePct: Math.round((expectedBudgetVariance + worstShift * 0.35) * 10) / 10,
      riskScore: Math.min(97, Math.round(expectedProbability + worstShift)),
      narrative: "Top contributing factors compound — supplier delay, weather, and claim exposure all land together.",
    },
  ];
}

/** Pure function — same project list always produces the same snapshot.
 * Called by lib/usePredictiveIntelligence.ts, the only place this touches
 * React. */
export function generatePredictiveIntelligence(
  projects: { id: number; project_code: string; project_name: string; status: string }[],
  referenceMs: number = Date.UTC(2026, 6, 28),
): PredictivePortfolioSnapshot {
  const projectPredictions: ProjectPrediction[] = projects.map((project) => {
    const categories = {} as Record<PredictionCategory, CategoryPrediction>;
    let probabilitySum = 0;

    for (const category of CATEGORY_ORDER) {
      const rand = mulberry32(hashString(`${project.project_code}::${category}`));
      const probability = Math.round(15 + rand() * 75);
      probabilitySum += probability;
      categories[category] = {
        category,
        probability,
        confidence: confidenceFor(rand),
        trend: probability > 55 ? (rand() > 0.3 ? "up" : "flat") : (rand() > 0.6 ? "down" : "flat"),
        trendDeltaPts: Math.round((rand() * 24 - 8)),
        contributingFactors: pickN(rand, FACTOR_POOL[category], 2 + Math.floor(rand() * 2)),
        recommendedActions: pickN(rand, ACTION_POOL[category], 1 + Math.floor(rand() * 2)),
      };
    }

    const overallProbability = Math.round(probabilitySum / CATEGORY_ORDER.length);
    const projectRand = mulberry32(hashString(`${project.project_code}::overall`));

    const timeline: TimelineEvent[] = pickN(projectRand, CATEGORY_ORDER, 3).map((category, i) => {
      const factor = pick(projectRand, FACTOR_POOL[category]);
      const days = 5 + i * 9 + Math.floor(projectRand() * 6);
      return {
        id: `${project.project_code}-tl-${category}-${i}`,
        projectId: project.id,
        projectCode: project.project_code,
        projectName: project.project_name,
        date: isoDaysFromNow(days, referenceMs),
        category,
        severity: bandFor(categories[category].probability),
        description: `${CATEGORY_LABEL[category]} risk expected to peak — ${factor.toLowerCase()}.`,
      };
    }).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

    return {
      projectId: project.id,
      projectCode: project.project_code,
      projectName: project.project_name,
      status: project.status,
      categories,
      overallProbability,
      overallBand: bandFor(overallProbability),
      scenarios: buildScenarios(projectRand, overallProbability, Math.round(2 + projectRand() * 10)),
      timeline,
      trend: buildTrend(mulberry32(hashString(`${project.project_code}::trend`)), overallProbability, referenceMs)
        .map((p) => ({ weekLabel: p.weekLabel, overall: p.value })),
    };
  });

  // ── Portfolio-level rollups ──────────────────────────────────────────
  const categoryPredictions = {} as Record<PredictionCategory, CategoryPrediction>;
  for (const category of CATEGORY_ORDER) {
    const rand = mulberry32(hashString(`PORTFOLIO::${category}`));
    const values = projectPredictions.map((p) => p.categories[category].probability);
    const probability = values.length ? Math.round(values.reduce((a, b) => a + b, 0) / values.length) : 0;
    const deltaValues = projectPredictions.map((p) => p.categories[category].trendDeltaPts);
    const trendDeltaPts = deltaValues.length ? Math.round(deltaValues.reduce((a, b) => a + b, 0) / deltaValues.length) : 0;
    categoryPredictions[category] = {
      category,
      probability,
      confidence: confidenceFor(rand),
      trend: trendDeltaPts > 3 ? "up" : trendDeltaPts < -3 ? "down" : "flat",
      trendDeltaPts,
      contributingFactors: pickN(rand, FACTOR_POOL[category], 3),
      recommendedActions: pickN(rand, ACTION_POOL[category], 2),
    };
  }

  const portfolioTrendSeries = buildTrend(mulberry32(hashString("PORTFOLIO::overall::trend")), 0, referenceMs);
  const trend = portfolioTrendSeries.map((point, i) => ({
    weekLabel: point.weekLabel,
    delay: buildTrend(mulberry32(hashString(`PORTFOLIO::delay::${i}`)), categoryPredictions.delay.probability, referenceMs)[i]?.value ?? categoryPredictions.delay.probability,
    budget_overrun: buildTrend(mulberry32(hashString(`PORTFOLIO::budget_overrun::${i}`)), categoryPredictions.budget_overrun.probability, referenceMs)[i]?.value ?? categoryPredictions.budget_overrun.probability,
    cash_flow: buildTrend(mulberry32(hashString(`PORTFOLIO::cash_flow::${i}`)), categoryPredictions.cash_flow.probability, referenceMs)[i]?.value ?? categoryPredictions.cash_flow.probability,
    claim: buildTrend(mulberry32(hashString(`PORTFOLIO::claim::${i}`)), categoryPredictions.claim.probability, referenceMs)[i]?.value ?? categoryPredictions.claim.probability,
    safety: buildTrend(mulberry32(hashString(`PORTFOLIO::safety::${i}`)), categoryPredictions.safety.probability, referenceMs)[i]?.value ?? categoryPredictions.safety.probability,
    schedule: buildTrend(mulberry32(hashString(`PORTFOLIO::schedule::${i}`)), categoryPredictions.schedule.probability, referenceMs)[i]?.value ?? categoryPredictions.schedule.probability,
  }));

  const portfolioAvgProbability = CATEGORY_ORDER.reduce((s, c) => s + categoryPredictions[c].probability, 0) / CATEGORY_ORDER.length;
  const forecastScore = Math.round(100 - portfolioAvgProbability);
  const forecastBand = bandFor(Math.round(portfolioAvgProbability));

  const scenarios = buildScenarios(
    mulberry32(hashString("PORTFOLIO::scenarios")),
    Math.round(portfolioAvgProbability),
    Math.round(3 + mulberry32(hashString("PORTFOLIO::budget"))() * 8),
  );

  // Emerging risks — biggest week-over-week increases across every
  // project x category combination.
  const emergingRisks: EmergingRisk[] = projectPredictions
    .flatMap((p) => CATEGORY_ORDER.map((category) => ({ project: p, category, pred: p.categories[category] })))
    .filter((x) => x.pred.trendDeltaPts > 8)
    .sort((a, b) => b.pred.trendDeltaPts - a.pred.trendDeltaPts)
    .slice(0, 10)
    .map((x, i) => ({
      id: `emerging-${i}`,
      projectId: x.project.projectId,
      projectCode: x.project.projectCode,
      projectName: x.project.projectName,
      category: x.category,
      probability: x.pred.probability,
      deltaPts: x.pred.trendDeltaPts,
      description: x.pred.contributingFactors[0] ?? `${CATEGORY_LABEL[x.category]} trending up this week.`,
    }));

  // Prediction history — a track record of past forecasts vs what
  // happened, so the page can answer "were we right before."
  const historyRand = mulberry32(hashString("PORTFOLIO::history"));
  const historyCandidates = projectPredictions.flatMap((p) => CATEGORY_ORDER.map((category) => ({ p, category })));
  const historyPicks = pickN(historyRand, historyCandidates, Math.min(14, historyCandidates.length));
  const predictionHistory: PredictionHistoryEntry[] = historyPicks.map((pick_, i) => {
    const rand = mulberry32(hashString(`history-${pick_.p.projectCode}-${pick_.category}-${i}`));
    const predictedProbability = Math.round(30 + rand() * 65);
    const predictedBand = bandFor(predictedProbability);
    const outcomeRoll = rand();
    const outcome: PredictionOutcome =
      predictedProbability >= 60 ? (outcomeRoll < 0.72 ? "occurred" : outcomeRoll < 0.92 ? "avoided" : "pending")
      : (outcomeRoll < 0.35 ? "occurred" : outcomeRoll < 0.85 ? "avoided" : "pending");
    const daysAgo = 7 + Math.floor(rand() * 45);
    const noteByOutcome: Record<PredictionOutcome, string> = {
      occurred: `Outcome confirmed via ${pick_.category === "safety" ? "site report" : pick_.category === "claim" ? "claim log" : "project record"} within the forecast window.`,
      avoided: "Recommended mitigation was applied in time — risk did not materialize.",
      pending: "Forecast window still open — outcome not yet confirmed.",
    };
    return {
      id: `history-${i}`,
      date: isoDaysAgo(daysAgo, referenceMs),
      projectId: pick_.p.projectId,
      projectCode: pick_.p.projectCode,
      projectName: pick_.p.projectName,
      category: pick_.category,
      predictedBand,
      predictedProbability,
      outcome,
      note: noteByOutcome[outcome],
    };
  }).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

  const highRiskCount = projectPredictions.filter((p) => p.overallBand === "Critical" || p.overallBand === "Elevated").length;
  const topCategory = CATEGORY_ORDER.reduce((a, b) => (categoryPredictions[a].probability >= categoryPredictions[b].probability ? a : b));

  return {
    generatedAt: new Date(referenceMs).toISOString(),
    projects: projectPredictions,
    categoryPredictions,
    overallForecast: {
      score: forecastScore,
      band: forecastBand,
      narrative: `${highRiskCount} of ${projectPredictions.length} project${projectPredictions.length === 1 ? "" : "s"} are forecast Elevated or Critical risk over the next 30 days, led by ${CATEGORY_LABEL[topCategory].toLowerCase()} at a ${categoryPredictions[topCategory].probability}% portfolio-wide probability.`,
    },
    trend,
    scenarios,
    emergingRisks,
    predictionHistory,
    aiRecommendations: {
      headline: `Portfolio forecast is ${forecastBand} risk over the next 30 days, primarily driven by ${CATEGORY_LABEL[topCategory].toLowerCase()} exposure.`,
      keyFindings: [
        `${CATEGORY_LABEL[topCategory]} carries the highest portfolio-wide probability at ${categoryPredictions[topCategory].probability}%, up ${Math.max(0, categoryPredictions[topCategory].trendDeltaPts)} points over the last 4 weeks.`,
        `${highRiskCount} project${highRiskCount === 1 ? "" : "s"} sit in the Elevated or Critical band and warrant executive attention this cycle.`,
        `${emergingRisks.length} risk signal${emergingRisks.length === 1 ? "" : "s"} increased sharply week-over-week — see Top Emerging Risks below.`,
      ],
      recommendations: [
        ...categoryPredictions[topCategory].recommendedActions,
        "Review the Scenario Comparison panel before the next steering committee to align on a mitigation posture.",
      ],
    },
  };
}
