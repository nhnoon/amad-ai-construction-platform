// ─────────────────────────────────────────────────────────────────────────
// MOCK / DEMO DATA — Cross-Project Learning
//
// Everything in this file is synthetic and deterministic. Nothing here
// performs real semantic search, embeddings, or vector retrieval. It
// exists so the Cross-Project Learning workspace
// (pages/ai-center/workspaces/cross-project-learning/) can be reviewed as
// a complete, investor-ready experience before a real knowledge-retrieval
// backend exists. Project and supplier identity (which projects/suppliers
// exist) is real; every knowledge item, similarity score, and AI insight
// layered on top is not — every retrieval on this page is keyword-based
// demo matching, not real semantic/vector search.
//
// To wire this up later: implement a real knowledge-retrieval endpoint
// (vector search / embeddings / Hermes memory / a knowledge graph store)
// that returns a `CrossProjectLearningSnapshot`-shaped payload (or a
// search-specific response) and replace the body of
// `loadCrossProjectLearning` in lib/useCrossProjectLearning.ts with a
// `fetch`/`useQuery` call. No component under
// pages/ai-center/workspaces/cross-project-learning/ needs to change —
// they only ever consume that hook's `data`/`isLoading`/`isError`, plus
// the pure `searchKnowledge`/`similarityScore` helpers below, which are
// themselves the natural seam to swap for a real semantic search call.
// ─────────────────────────────────────────────────────────────────────────

export type SourceType = "meeting" | "document" | "claim" | "contract" | "decision" | "risk" | "action";
export type KnowledgeCategory =
  | "Lessons Learned" | "Claims" | "Contracts" | "Meetings" | "Site Reports"
  | "Safety" | "Quality" | "Procurement" | "Schedule" | "Cost" | "Suppliers";
export type Outcome = "Successful" | "Partial" | "Unsuccessful";
export type RiskLevel = "Low" | "Medium" | "High" | "Critical";
export type Department = "Engineering" | "Procurement" | "Site Operations" | "Commercial" | "Safety" | "Quality" | "Executive";
export type CitationKind = "document" | "meeting" | "approval" | "claim";

export interface Citation { label: string; kind: CitationKind; }

export interface KnowledgeItem {
  id: string;
  templateId: string; // groups cross-project recurrences of "the same lesson"
  projectId: number;
  projectCode: string;
  projectName: string;
  title: string;
  summary: string;
  category: KnowledgeCategory;
  sourceType: SourceType;
  date: string;
  confidence: number; // 0-100
  riskLevel: RiskLevel;
  department: Department;
  supplierName?: string;
  materialName?: string;
  tags: string[];
  rootCause: string;
  resolution: string;
  outcome: Outcome;
  evidence: string[];
  relatedRisks: string[];
  relatedDecisions: string[];
  relatedActions: string[];
  citations: Citation[];
  recommendation: string;
  connectedIds: string[];
  timeline: { date: string; label: string }[];
}

export interface RecurringProblem { templateId: string; title: string; occurrences: number; projects: string[]; }
export interface FrequencyItem { name: string; count: number; }

export interface CrossProjectLearningSnapshot {
  generatedAt: string;
  items: KnowledgeItem[];
  categoryCounts: Record<KnowledgeCategory, number>;
  stats: {
    totalKnowledgeItems: number;
    projectsRepresented: number;
    recurringPatternCount: number;
    successfulResolutionPct: number;
    avgConfidence: number;
  };
  executiveInsights: {
    topRecurringProblems: RecurringProblem[];
    mostSuccessfulActions: string[];
    mostCommonCauses: string[];
    frequentSuppliers: FrequencyItem[];
    frequentMaterials: FrequencyItem[];
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
function pick<T>(rand: () => number, arr: T[]): T { return arr[Math.floor(rand() * arr.length)]; }
function pickN<T>(rand: () => number, arr: T[], n: number): T[] {
  const pool = [...arr];
  const out: T[] = [];
  for (let i = 0; i < n && pool.length > 0; i++) out.push(pool.splice(Math.floor(rand() * pool.length), 1)[0]);
  return out;
}
function isoDaysAgo(days: number, referenceMs: number): string {
  return new Date(referenceMs - days * 86_400_000).toISOString();
}

const MATERIAL_POOL = ["Reinforcement Steel", "Ready-Mix Concrete", "Copper Cable", "HVAC Equipment", "Timber", "Cement", "PVC Piping"];

// ── Case templates — the recurring organizational lessons. Each template
// is instantiated once per matched project below, so the same issue
// genuinely recurs across different projects rather than being faked by
// fuzzy matching after the fact. ──────────────────────────────────────

interface ItemTemplate {
  id: string;
  title: string;
  summary: string;
  category: KnowledgeCategory;
  sourceType: SourceType;
  department: Department;
  tags: string[];
  rootCause: string;
  resolution: string;
  recommendation: string;
  material?: string;
  supplierCategoryHint?: string;
  riskLevel: RiskLevel;
  dayOffsetBase: number;
}

const TEMPLATES: ItemTemplate[] = [
  {
    id: "rebar-delivery-delay", title: "Recurring reinforcement steel delivery delays",
    summary: "A single-source rebar supplier repeatedly missed delivery windows, forcing resequencing of foundation pours.",
    category: "Procurement", sourceType: "claim", department: "Procurement",
    tags: ["rebar", "delivery-delay", "single-source", "foundations"],
    rootCause: "Sole-sourced reinforcement steel supplier with no qualified backup and limited buffer stock held on site.",
    resolution: "Qualified a second reinforcement steel supplier and required a minimum on-site buffer for critical-path pours.",
    recommendation: "Qualify at least one backup rebar supplier before mobilizing foundation works on future projects.",
    material: "Reinforcement Steel", supplierCategoryHint: "steel", riskLevel: "High", dayOffsetBase: 210,
  },
  {
    id: "concrete-slump-rejection", title: "Concrete batch rejected for slump test failure",
    summary: "Ready-mix concrete delivered outside the approved slump range was rejected on site, delaying the pour.",
    category: "Quality", sourceType: "document", department: "Quality",
    tags: ["concrete", "quality", "slump-test", "batching"],
    rootCause: "Batching plant inconsistency during high-demand periods led to water content drifting outside spec.",
    resolution: "Added a mandatory slump test checkpoint at the truck gate before any pour is accepted.",
    recommendation: "Require a gate-side slump test on every ready-mix delivery for structural pours.",
    material: "Ready-Mix Concrete", supplierCategoryHint: "concrete", riskLevel: "Medium", dayOffsetBase: 160,
  },
  {
    id: "scaffold-safety-nonconformance", title: "Recurring scaffold edge-protection non-conformance",
    summary: "Multiple site safety walks identified missing or incomplete guardrails on scaffold lifts above the second level.",
    category: "Safety", sourceType: "risk", department: "Safety",
    tags: ["safety", "scaffold", "edge-protection", "working-at-height"],
    rootCause: "Subcontractor scaffold crews were not re-inspecting guardrails after each lift extension.",
    resolution: "Introduced a mandatory scaffold hand-over inspection with sign-off before each lift is used.",
    recommendation: "Require a documented scaffold hand-over inspection at every lift change, not just initial erection.",
    riskLevel: "High", dayOffsetBase: 95,
  },
  {
    id: "eot-differing-conditions", title: "Extension-of-time claim succeeded on differing site conditions",
    summary: "An extension-of-time claim was approved after geotechnical conditions differed materially from tender borehole data.",
    category: "Claims", sourceType: "claim", department: "Commercial",
    tags: ["eot-claim", "differing-conditions", "geotechnical"],
    rootCause: "Tender-stage borehole data did not capture localized rock conditions encountered during excavation.",
    resolution: "Filed formal notice within the contractual window with photographic and survey evidence, claim approved in full.",
    recommendation: "File differing-conditions notices within the contractual window immediately evidence is available — do not wait for full quantification.",
    riskLevel: "Medium", dayOffsetBase: 260,
  },
  {
    id: "variation-order-approval-delay", title: "Variation order approvals delayed by client review cycle",
    summary: "Client-side variation order approvals routinely took over 30 days, stalling downstream procurement decisions.",
    category: "Cost", sourceType: "decision", department: "Commercial",
    tags: ["variation-order", "approval-delay", "cash-flow"],
    rootCause: "Client's internal approval chain required multiple sign-offs with no defined turnaround SLA.",
    resolution: "Negotiated a 10-business-day variation order response SLA into the next contract amendment.",
    recommendation: "Negotiate a defined variation-order approval SLA at contract award, not after delays begin.",
    riskLevel: "Medium", dayOffsetBase: 130,
  },
  {
    id: "mep-scope-gap-rework", title: "MEP subcontract scope gap caused rework",
    summary: "An ambiguous MEP subcontract scope boundary led to duplicated and missed work between two subcontractors.",
    category: "Contracts", sourceType: "contract", department: "Engineering",
    tags: ["mep", "scope-gap", "subcontract", "rework"],
    rootCause: "Subcontract scope schedules did not clearly allocate interface responsibility at the ceiling void.",
    resolution: "Reworked the disputed interface at contractor cost, then issued a scope-boundary addendum for the remaining subcontracts.",
    recommendation: "Explicitly allocate interface responsibility for every MEP subcontract boundary before award, not after a clash is found.",
    riskLevel: "High", dayOffsetBase: 175,
  },
  {
    id: "copper-price-spike", title: "Early bulk purchase avoided copper price spike exposure",
    summary: "Procurement locked in copper cable pricing ahead of a forecast market increase, avoiding a significant cost overrun.",
    category: "Cost", sourceType: "decision", department: "Procurement",
    tags: ["copper", "price-spike", "bulk-purchase", "cost-avoidance"],
    rootCause: "Global copper price volatility was flagged early by the supplier as a near-term risk.",
    resolution: "Consolidated demand across active projects and locked pricing with a single bulk purchase order.",
    recommendation: "When a supplier flags near-term commodity volatility, evaluate a consolidated bulk purchase before the price moves.",
    material: "Copper Cable", supplierCategoryHint: "electrical", riskLevel: "Low", dayOffsetBase: 70,
  },
  {
    id: "progress-meeting-cadence", title: "Weekly progress meeting cadence improved schedule adherence",
    summary: "Moving from bi-weekly to weekly progress meetings measurably reduced schedule slippage on critical-path activities.",
    category: "Schedule", sourceType: "meeting", department: "Site Operations",
    tags: ["progress-meeting", "cadence", "schedule-adherence"],
    rootCause: "Bi-weekly reporting meant emerging delays were surfaced too late to recover within the same period.",
    resolution: "Switched to a weekly critical-path review with the same attendee list and a standing action log.",
    recommendation: "Default to weekly (not bi-weekly) progress meetings once a project enters its critical structural phase.",
    riskLevel: "Low", dayOffsetBase: 300,
  },
  {
    id: "hvac-lead-time-underestimate", title: "Imported HVAC equipment lead time underestimated at tender",
    summary: "Tender-stage lead time assumptions for imported HVAC equipment proved optimistic, compressing the MEP fit-out schedule.",
    category: "Procurement", sourceType: "claim", department: "Procurement",
    tags: ["hvac", "lead-time", "import", "mep"],
    rootCause: "Tender schedule used the manufacturer's catalog lead time rather than the actual quoted lead time including customs clearance.",
    resolution: "Re-sequenced MEP fit-out around confirmed delivery and added a schedule contingency for future imported equipment.",
    recommendation: "Confirm actual quoted lead time (including customs) for imported equipment before finalizing the tender schedule, not the catalog figure.",
    material: "HVAC Equipment", supplierCategoryHint: "mechanical", riskLevel: "Medium", dayOffsetBase: 110,
  },
  {
    id: "payment-cert-standardization", title: "Standardized documentation reduced payment certificate disputes",
    summary: "Introducing a standard supporting-documentation checklist reduced disputed line items on interim payment certificates.",
    category: "Cost", sourceType: "decision", department: "Commercial",
    tags: ["payment-certificate", "documentation", "dispute-reduction"],
    rootCause: "Payment applications were submitted with inconsistent supporting evidence, prompting repeated client queries.",
    resolution: "Adopted a standard IPC supporting-documentation checklist across all active projects.",
    recommendation: "Use a standard payment-certificate documentation checklist from project kickoff, not after disputes start.",
    riskLevel: "Low", dayOffsetBase: 190,
  },
  {
    id: "timber-moisture-nonconformance", title: "Timber moisture non-conformance traced to single supplier",
    summary: "Recurring timber moisture-content failures were traced back to inadequate storage at one supplier's yard.",
    category: "Quality", sourceType: "risk", department: "Quality",
    tags: ["timber", "moisture", "quality", "storage"],
    rootCause: "Supplier stored timber in an uncovered yard, allowing moisture content to exceed the approved threshold.",
    resolution: "Switched to a supplier with covered, climate-controlled storage and added moisture testing on receipt.",
    recommendation: "Verify a timber supplier's storage conditions during qualification, not only their mill certification.",
    material: "Timber", supplierCategoryHint: "timber", riskLevel: "Medium", dayOffsetBase: 145,
  },
  {
    id: "structural-clash-claim", title: "Structural design clash led to rework and claim exposure",
    summary: "A late-discovered structural steel clash with MEP risers required rework and exposed the project to a subcontractor claim.",
    category: "Quality", sourceType: "claim", department: "Engineering",
    tags: ["structural-steel", "design-clash", "rework", "claim"],
    rootCause: "BIM coordination review was completed after steel fabrication had already started.",
    resolution: "Absorbed the rework cost and moved BIM clash coordination to before fabrication release on subsequent packages.",
    recommendation: "Complete BIM clash coordination before releasing structural steel for fabrication, not in parallel with it.",
    material: "Reinforcement Steel", supplierCategoryHint: "steel", riskLevel: "Critical", dayOffsetBase: 240,
  },
];

const CONFIDENCE_BASE = 62;

function outcomeFor(rand: () => number): Outcome {
  const r = rand();
  if (r < 0.55) return "Successful";
  if (r < 0.85) return "Partial";
  return "Unsuccessful";
}

function citationsFor(rand: () => number, tpl: ItemTemplate): Citation[] {
  const pool: Citation[] = [
    { label: "Site Report", kind: "document" }, { label: "Weekly Progress Meeting", kind: "meeting" },
    { label: "Change Order Approval", kind: "approval" }, { label: "Claim Record", kind: "claim" },
    { label: "Contract Amendment", kind: "document" }, { label: "Payment Certificate", kind: "approval" },
  ];
  return pickN(rand, pool, 2 + Math.floor(rand() * 2));
}

/** Pure function — same suppliers + projects always produce the same
 * snapshot. Called by lib/useCrossProjectLearning.ts, the only place this
 * touches React. */
export function generateCrossProjectLearning(
  projects: { id: number; project_code: string; project_name: string }[],
  suppliers: { id: number; supplier_name: string; category: string | null }[],
  referenceMs: number = Date.UTC(2026, 6, 28),
): CrossProjectLearningSnapshot {
  if (projects.length === 0) {
    return {
      generatedAt: new Date(referenceMs).toISOString(),
      items: [],
      categoryCounts: {} as Record<KnowledgeCategory, number>,
      stats: { totalKnowledgeItems: 0, projectsRepresented: 0, recurringPatternCount: 0, successfulResolutionPct: 0, avgConfidence: 0 },
      executiveInsights: { topRecurringProblems: [], mostSuccessfulActions: [], mostCommonCauses: [], frequentSuppliers: [], frequentMaterials: [] },
    };
  }

  const items: KnowledgeItem[] = [];

  for (const tpl of TEMPLATES) {
    const rand = mulberry32(hashString(`cpl::${tpl.id}`));
    const occurrenceCount = Math.min(projects.length, 2 + Math.floor(rand() * 3));
    const matchedProjects = pickN(rand, projects, occurrenceCount);

    const supplierPool = tpl.supplierCategoryHint
      ? suppliers.filter((s) => (s.category ?? "").toLowerCase().includes(tpl.supplierCategoryHint!))
      : [];
    const templateIds: string[] = [];

    matchedProjects.forEach((project, i) => {
      const itemRand = mulberry32(hashString(`cpl::${tpl.id}::${project.id}`));
      const id = `${tpl.id}-${project.id}`;
      templateIds.push(id);
      const supplier = supplierPool.length > 0 ? pick(itemRand, supplierPool) : undefined;
      items.push({
        id,
        templateId: tpl.id,
        projectId: project.id,
        projectCode: project.project_code,
        projectName: project.project_name,
        title: tpl.title,
        summary: tpl.summary,
        category: tpl.category,
        sourceType: tpl.sourceType,
        date: isoDaysAgo(tpl.dayOffsetBase + i * 18 + Math.floor(itemRand() * 12), referenceMs),
        confidence: Math.min(98, Math.max(40, Math.round(CONFIDENCE_BASE + itemRand() * 30))),
        riskLevel: tpl.riskLevel,
        department: tpl.department,
        supplierName: supplier?.supplier_name,
        materialName: tpl.material ?? (rand() > 0.7 ? pick(itemRand, MATERIAL_POOL) : undefined),
        tags: tpl.tags,
        rootCause: tpl.rootCause,
        resolution: tpl.resolution,
        outcome: outcomeFor(itemRand),
        evidence: [
          `${tpl.sourceType === "meeting" ? "Meeting minutes" : tpl.sourceType === "claim" ? "Claim file" : tpl.sourceType === "contract" ? "Contract record" : tpl.sourceType === "risk" ? "Risk register entry" : tpl.sourceType === "decision" ? "Decision log" : "Site record"} for ${project.project_code} confirms the timeline below.`,
          `Referenced in ${1 + Math.floor(itemRand() * 3)} follow-up report${itemRand() > 0.5 ? "s" : ""}.`,
        ],
        relatedRisks: [`${tpl.category} risk — ${tpl.tags[0]}`],
        relatedDecisions: [`Decision: ${tpl.resolution.slice(0, 60)}${tpl.resolution.length > 60 ? "…" : ""}`],
        relatedActions: [`Action: ${tpl.recommendation.slice(0, 60)}${tpl.recommendation.length > 60 ? "…" : ""}`],
        citations: citationsFor(itemRand, tpl),
        recommendation: tpl.recommendation,
        connectedIds: [], // filled below once every occurrence's id is known
        timeline: [
          { date: isoDaysAgo(tpl.dayOffsetBase + i * 18 + 6, referenceMs), label: "Issue identified and logged" },
          { date: isoDaysAgo(tpl.dayOffsetBase + i * 18 + 2, referenceMs), label: "Root cause investigation completed" },
          { date: isoDaysAgo(tpl.dayOffsetBase + i * 18 - 4, referenceMs), label: "Resolution implemented" },
        ],
      });
    });

    // Every occurrence of the same template is connected to every other
    // occurrence — this is the concrete, honest basis for "has this
    // happened before" rather than a fuzzy-matched illusion of one.
    for (const item of items.filter((it) => it.templateId === tpl.id)) {
      item.connectedIds = templateIds.filter((otherId) => otherId !== item.id);
    }
  }

  items.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

  const categoryCounts = {} as Record<KnowledgeCategory, number>;
  for (const item of items) categoryCounts[item.category] = (categoryCounts[item.category] ?? 0) + 1;

  const projectsRepresented = new Set(items.map((i) => i.projectCode)).size;
  const successfulCount = items.filter((i) => i.outcome === "Successful").length;
  const recurringPatternCount = TEMPLATES.filter((tpl) => items.filter((i) => i.templateId === tpl.id).length >= 2).length;

  const topRecurringProblems: RecurringProblem[] = TEMPLATES
    .map((tpl) => {
      const occurrences = items.filter((i) => i.templateId === tpl.id);
      return { templateId: tpl.id, title: tpl.title, occurrences: occurrences.length, projects: occurrences.map((o) => o.projectCode) };
    })
    .filter((r) => r.occurrences >= 2)
    .sort((a, b) => b.occurrences - a.occurrences)
    .slice(0, 6);

  const mostSuccessfulActions = Array.from(new Set(items.filter((i) => i.outcome === "Successful").map((i) => i.resolution))).slice(0, 6);
  const mostCommonCauses = Array.from(new Set(items.map((i) => i.rootCause))).slice(0, 6);

  const supplierFreq = new Map<string, number>();
  for (const item of items) if (item.supplierName) supplierFreq.set(item.supplierName, (supplierFreq.get(item.supplierName) ?? 0) + 1);
  const frequentSuppliers: FrequencyItem[] = Array.from(supplierFreq.entries()).map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count).slice(0, 6);

  const materialFreq = new Map<string, number>();
  for (const item of items) if (item.materialName) materialFreq.set(item.materialName, (materialFreq.get(item.materialName) ?? 0) + 1);
  const frequentMaterials: FrequencyItem[] = Array.from(materialFreq.entries()).map(([name, count]) => ({ name, count })).sort((a, b) => b.count - a.count).slice(0, 6);

  return {
    generatedAt: new Date(referenceMs).toISOString(),
    items,
    categoryCounts,
    stats: {
      totalKnowledgeItems: items.length,
      projectsRepresented,
      recurringPatternCount,
      successfulResolutionPct: items.length ? Math.round((successfulCount / items.length) * 100) : 0,
      avgConfidence: items.length ? Math.round(items.reduce((s, i) => s + i.confidence, 0) / items.length) : 0,
    },
    executiveInsights: { topRecurringProblems, mostSuccessfulActions, mostCommonCauses, frequentSuppliers, frequentMaterials },
  };
}

// ── Search + similarity — the pure-function seam a real semantic/vector
// search implementation would replace. Deliberately simple keyword
// matching so it is never mistaken for real retrieval. ──────────────────

export function searchKnowledge(items: KnowledgeItem[], query: string): KnowledgeItem[] {
  const q = query.trim().toLowerCase();
  if (!q) return items;
  const terms = q.split(/\s+/).filter(Boolean);
  return items
    .map((item) => {
      const haystack = `${item.title} ${item.summary} ${item.rootCause} ${item.resolution} ${item.recommendation} ${item.tags.join(" ")} ${item.projectCode} ${item.projectName}`.toLowerCase();
      const matches = terms.filter((t) => haystack.includes(t)).length;
      return { item, matches };
    })
    .filter((r) => r.matches > 0)
    .sort((a, b) => b.matches - a.matches)
    .map((r) => r.item);
}

export function similarityScore(a: KnowledgeItem, b: KnowledgeItem): number {
  if (a.id === b.id) return 0;
  let score = 0;
  if (a.templateId === b.templateId) score += 55;
  score += a.tags.filter((t) => b.tags.includes(t)).length * 12;
  if (a.category === b.category) score += 15;
  if (a.supplierName && a.supplierName === b.supplierName) score += 10;
  if (a.materialName && a.materialName === b.materialName) score += 10;
  if (a.department === b.department) score += 5;
  return Math.min(99, score);
}

export function findSimilarCases(items: KnowledgeItem[], target: KnowledgeItem, minScore = 20): { item: KnowledgeItem; score: number }[] {
  return items
    .filter((i) => i.id !== target.id)
    .map((item) => ({ item, score: similarityScore(target, item) }))
    .filter((r) => r.score >= minScore)
    .sort((a, b) => b.score - a.score);
}

export const SUGGESTED_SEARCHES: string[] = TEMPLATES.slice(0, 6).map((t) => t.tags[0].replace(/-/g, " "));
