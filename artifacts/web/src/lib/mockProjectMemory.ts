// ─────────────────────────────────────────────────────────────────────────
// MOCK / DEMO DATA — Project Memory
//
// This file is the ONLY place synthetic Project Memory content is defined.
// Nothing here talks to the network. It exists so the Project Memory
// workspace (pages/ai-center/workspaces/project-memory/) can be reviewed as
// a complete, investor-ready experience before a backend "project memory"
// endpoint exists.
//
// To wire this up to a real backend later: implement an endpoint that
// returns a `ProjectMemorySnapshot` shape (or adjust the shape to match
// whatever it returns) and replace the body of `generateProjectMemorySnapshot`
// in lib/useProjectMemory.ts with a `fetch`/`useQuery` call — no component
// in project-memory/ needs to change, they only consume the hook.
// ─────────────────────────────────────────────────────────────────────────

export type MemorySourceType =
  | "document"
  | "site_report"
  | "meeting"
  | "contract"
  | "claim"
  | "decision"
  | "risk"
  | "action"
  | "approval";

export type MemoryCategory =
  | "Schedule"
  | "Procurement"
  | "Safety"
  | "Quality"
  | "Commercial"
  | "Contract"
  | "Governance";

export type RiskLevel = "low" | "medium" | "high" | "critical";

export type MemoryStatus =
  | "Open"
  | "Pending"
  | "Approved"
  | "Rejected"
  | "Resolved"
  | "Completed";

export interface MemoryCitation {
  label: string;
  sourceType: MemorySourceType;
  /** Real, existing route this citation points into — always a general
   * section page (e.g. /site-reports), never a fabricated deep link to a
   * specific record ID that doesn't exist in the backend. */
  href?: string;
}

export interface MemoryItem {
  id: string;
  projectCode: string;
  sourceType: MemorySourceType;
  category: MemoryCategory;
  title: string;
  summary: string;
  detail: string;
  author: string;
  date: string; // ISO date
  riskLevel?: RiskLevel;
  status: MemoryStatus;
  tags: string[];
  citations: MemoryCitation[];
  /** IDs of other MemoryItems this one is meaningfully connected to
   * (same storyline — capture → understand → connect → detect → decide). */
  relatedIds: string[];
  storyline: string;
}

export interface ProjectMemoryStats {
  total: number;
  bySourceType: Record<MemorySourceType, number>;
  byCategory: Record<MemoryCategory, number>;
  byRiskLevel: Record<RiskLevel, number>;
  openActions: number;
  pendingApprovals: number;
  openRisks: number;
  decisionsLogged: number;
  oldestDate: string;
  newestDate: string;
  activityByWeek: { weekLabel: string; count: number }[];
}

export interface ProjectMemorySnapshot {
  projectCode: string;
  projectName: string;
  generatedAt: string;
  items: MemoryItem[];
  stats: ProjectMemoryStats;
  authors: string[];
  executiveSummary: {
    headline: string;
    bullets: string[];
  };
  aiSummary: {
    keyFindings: string[];
    recommendations: string[];
  };
}

// ── Deterministic PRNG — same project always renders the same demo dataset
// (stable across re-renders / re-mounts), different projects render visibly
// different data, without any project-specific data actually existing. ────

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

const AUTHORS = [
  "Sara Al-Qahtani", "Omar Al-Harbi", "Fahad Al-Otaibi", "Lina Abdullah",
  "Yousef Al-Rashid", "Noura Al-Dossari", "Khalid Al-Ghamdi", "Maha Al-Zahrani",
];

const SOURCE_ROUTE: Record<MemorySourceType, string | undefined> = {
  document: "/documents",
  site_report: "/site-reports",
  meeting: "/meetings",
  contract: "/ai-center/contracts",
  claim: "/claims",
  approval: "/requests",
  risk: "/risks",
  action: "/tasks",
  decision: undefined,
};

function cite(label: string, sourceType: MemorySourceType): MemoryCitation {
  return { label, sourceType, href: SOURCE_ROUTE[sourceType] };
}

// ── Storyline templates ─────────────────────────────────────────────────
// Five short narratives, each walking Capture -> Understand -> Connect ->
// Detect -> Decide across a handful of linked items, so the timeline and
// relationship graph show a coherent story rather than disconnected rows.
// `dayOffset` is days-ago from "now" at generation time; jittered per
// project by the PRNG so the same storyline lands on different dates for
// different projects.

interface ItemTemplate {
  id: string;
  storyline: string;
  sourceType: MemorySourceType;
  category: MemoryCategory;
  title: string;
  summary: string;
  detail: string;
  dayOffset: number;
  riskLevel?: RiskLevel;
  status: MemoryStatus;
  tags: string[];
  citations: MemoryCitation[];
  relatedIds: string[];
}

const TEMPLATES: ItemTemplate[] = [
  // Storyline A — Concrete delivery delay
  {
    id: "a1", storyline: "Concrete Delivery Delay", sourceType: "site_report", category: "Schedule",
    title: "Concrete delivery delayed 2 days — Zone C foundations",
    summary: "Ready-mix concrete pour for Zone C foundations postponed after the supplier reported a batching plant breakdown.",
    detail: "Site team logged a 2-day slip on the Zone C foundation pour. Supplier confirmed a batching plant mechanical failure with no firm restart date at time of reporting. Formwork and rebar were already complete and standing idle.",
    dayOffset: 21, riskLevel: "high", status: "Open",
    tags: ["concrete", "foundations", "zone-c"],
    citations: [cite("Daily Site Report", "site_report")],
    relatedIds: ["a2", "a3"],
  },
  {
    id: "a2", storyline: "Concrete Delivery Delay", sourceType: "risk", category: "Procurement",
    title: "Supplier delay risk — ready-mix concrete supplier",
    summary: "Single-source dependency on the ready-mix supplier flagged as a schedule risk following the Zone C delay.",
    detail: "The project has no qualified backup ready-mix supplier within economical hauling distance. A repeat plant failure would directly threaten the Zone D and Zone E pour dates downstream.",
    dayOffset: 20, riskLevel: "high", status: "Open",
    tags: ["supplier", "concrete", "single-source"],
    citations: [cite("Risk Register", "risk"), cite("Daily Site Report", "site_report")],
    relatedIds: ["a1", "a3", "a4"],
  },
  {
    id: "a3", storyline: "Concrete Delivery Delay", sourceType: "meeting", category: "Schedule",
    title: "Weekly progress meeting — resequencing discussion",
    summary: "Project team discussed resequencing Zone C behind Zone B to absorb the concrete delay without slipping the milestone date.",
    detail: "Site engineering proposed swapping the Zone B and Zone C pour order since Zone B rebar is ready. Procurement to source a qualified backup supplier in parallel.",
    dayOffset: 19, status: "Completed",
    tags: ["progress-meeting", "resequencing"],
    citations: [cite("Weekly Progress Meeting", "meeting")],
    relatedIds: ["a1", "a2", "a4"],
  },
  {
    id: "a4", storyline: "Concrete Delivery Delay", sourceType: "decision", category: "Schedule",
    title: "Decision: resequence Zone C pour after Zone B",
    summary: "Approved swapping the Zone B and Zone C foundation pour order to protect the overall milestone date.",
    detail: "Decision recorded in the weekly progress meeting minutes. Site engineering to update the master schedule; procurement to report backup supplier options within 5 working days.",
    dayOffset: 19, status: "Approved",
    tags: ["decision", "resequencing"],
    citations: [cite("Weekly Progress Meeting", "meeting")],
    relatedIds: ["a3", "a5"],
  },
  {
    id: "a5", storyline: "Concrete Delivery Delay", sourceType: "action", category: "Procurement",
    title: "Action: qualify a backup ready-mix supplier",
    summary: "Procurement to identify and qualify a second ready-mix supplier to remove the single-source schedule risk.",
    detail: "Open action assigned to procurement following the resequencing decision. Target: two qualified backup suppliers with signed rate agreements.",
    dayOffset: 18, status: "Open",
    tags: ["procurement", "backup-supplier"],
    citations: [cite("Risk Register", "risk")],
    relatedIds: ["a2", "a4"],
  },

  // Storyline B — Drawing revision
  {
    id: "b1", storyline: "Drawing Revision", sourceType: "document", category: "Quality",
    title: "Structural drawing Rev C uploaded — Level 3 slab",
    summary: "Revised Level 3 slab reinforcement drawing uploaded to the document center following the design team's clash review.",
    detail: "Rev C resolves a reinforcement clash with the MEP riser at gridline D4, flagged during the BIM coordination pass.",
    dayOffset: 34, status: "Pending",
    tags: ["drawing", "structural", "level-3"],
    citations: [cite("Document Center", "document")],
    relatedIds: ["b2"],
  },
  {
    id: "b2", storyline: "Drawing Revision", sourceType: "decision", category: "Quality",
    title: "Approved drawing revision — Level 3 slab reinforcement",
    summary: "Design manager approved Rev C for construction after site engineering confirmed no impact to the current pour sequence.",
    detail: "Approval recorded with a note that the previous Rev B copies on site must be superseded before the Level 3 pour.",
    dayOffset: 32, status: "Approved",
    tags: ["approval", "drawing", "structural"],
    citations: [cite("Document Center", "document")],
    relatedIds: ["b1", "b3"],
  },
  {
    id: "b3", storyline: "Drawing Revision", sourceType: "action", category: "Quality",
    title: "Action: issue Rev C to site team, withdraw Rev B",
    summary: "Document controller to distribute the approved revision and formally withdraw the superseded copy from site.",
    detail: "Standard document-control action following a drawing approval — confirms only the current revision is in circulation on site.",
    dayOffset: 31, status: "Completed",
    tags: ["document-control"],
    citations: [cite("Document Center", "document")],
    relatedIds: ["b2"],
  },

  // Storyline C — Variation order, contract risk, payment, claim
  {
    id: "c1", storyline: "Variation & Payment", sourceType: "approval", category: "Commercial",
    title: "Pending variation order — additional excavation works",
    summary: "Variation order for unforeseen rock excavation at the basement level awaiting client approval.",
    detail: "Geotechnical conditions differed from the tender borehole data. Variation order quantifies the additional excavation and disposal cost, submitted for client sign-off.",
    dayOffset: 14, riskLevel: "medium", status: "Pending",
    tags: ["variation-order", "excavation"],
    citations: [cite("Requests & Approvals", "approval")],
    relatedIds: ["c2", "c4"],
  },
  {
    id: "c2", storyline: "Variation & Payment", sourceType: "contract", category: "Contract",
    title: "Contract clause risk — liquidated damages exposure reviewed",
    summary: "Commercial team reviewed the liquidated damages clause against the cumulative schedule slip from the concrete and excavation delays.",
    detail: "Clause 14.2 caps liquidated damages at 10% of contract value. Current cumulative slip is within the notice period allowed for an extension-of-time claim, but requires formal notice within 28 days.",
    dayOffset: 13, riskLevel: "high", status: "Open",
    tags: ["contract", "liquidated-damages", "eot"],
    citations: [cite("Contract Intelligence", "contract")],
    relatedIds: ["c1", "c4"],
  },
  {
    id: "c3", storyline: "Variation & Payment", sourceType: "approval", category: "Commercial",
    title: "Interim Payment Certificate #7 approved",
    summary: "Monthly interim payment certificate approved by the client's quantity surveyor for works completed through the current period.",
    detail: "IPC #7 approved at the assessed value after minor quantity adjustments to the substructure line items.",
    dayOffset: 9, status: "Approved",
    tags: ["payment", "ipc"],
    citations: [cite("Requests & Approvals", "approval")],
    relatedIds: [],
  },
  {
    id: "c4", storyline: "Variation & Payment", sourceType: "claim", category: "Commercial",
    title: "Extended site overhead claim submitted",
    summary: "Claim submitted for extended site overheads arising from the excavation-related schedule impact.",
    detail: "Claim references the differing site conditions and the pending variation order as supporting grounds, filed within the contractual notice period.",
    dayOffset: 8, riskLevel: "medium", status: "Pending",
    tags: ["claim", "site-overheads"],
    citations: [cite("Claims", "claim"), cite("Contract Intelligence", "contract")],
    relatedIds: ["c1", "c2"],
  },

  // Storyline D — Site safety
  {
    id: "d1", storyline: "Site Safety", sourceType: "site_report", category: "Safety",
    title: "Safety observation — missing guardrails, Zone A scaffold",
    summary: "Site safety walk identified missing edge protection on the Zone A scaffold third lift.",
    detail: "HSE officer stopped work on the affected bay pending guardrail installation. No injuries reported.",
    dayOffset: 6, riskLevel: "high", status: "Open",
    tags: ["safety", "scaffold", "edge-protection"],
    citations: [cite("Daily Site Report", "site_report")],
    relatedIds: ["d2", "d3"],
  },
  {
    id: "d2", storyline: "Site Safety", sourceType: "action", category: "Safety",
    title: "Corrective action — install guardrails and re-inspect",
    summary: "Guardrails installed on the affected scaffold bay and the area re-inspected and cleared for work.",
    detail: "Corrective action closed out same day. Scaffold inspection tag renewed and photographed for the safety file.",
    dayOffset: 5, status: "Completed",
    tags: ["corrective-action", "scaffold"],
    citations: [cite("Daily Site Report", "site_report")],
    relatedIds: ["d1"],
  },
  {
    id: "d3", storyline: "Site Safety", sourceType: "meeting", category: "Safety",
    title: "Toolbox talk — working at height refresher",
    summary: "HSE-led toolbox talk on working-at-height requirements delivered to all scaffold and roofing crews.",
    detail: "Refresher triggered directly by the Zone A guardrail observation, attended by 24 site personnel.",
    dayOffset: 4, status: "Completed",
    tags: ["toolbox-talk", "training"],
    citations: [cite("Meetings", "meeting")],
    relatedIds: ["d1", "d2"],
  },

  // Storyline E — Subcontractor / governance
  {
    id: "e1", storyline: "Subcontractor & Governance", sourceType: "contract", category: "Contract",
    title: "Subcontractor agreement amendment — MEP scope",
    summary: "MEP subcontract amended to add chilled-water piping scope previously carried as a provisional sum.",
    detail: "Amendment converts the provisional sum to a firm price after the MEP subcontractor's detailed quotation was reviewed and negotiated down 6%.",
    dayOffset: 27, status: "Approved",
    tags: ["subcontract", "mep"],
    citations: [cite("Contract Intelligence", "contract")],
    relatedIds: ["e2", "e3"],
  },
  {
    id: "e2", storyline: "Subcontractor & Governance", sourceType: "decision", category: "Governance",
    title: "Executive decision — budget reallocation for MEP scope",
    summary: "Project steering committee approved reallocating contingency budget to cover the firmed-up MEP scope.",
    detail: "Reallocation keeps the project within the approved total budget envelope; contingency drawdown now at 34%.",
    dayOffset: 26, status: "Approved",
    tags: ["budget", "governance"],
    citations: [cite("Executive Intelligence", "contract")],
    relatedIds: ["e1", "e3"],
  },
  {
    id: "e3", storyline: "Subcontractor & Governance", sourceType: "approval", category: "Commercial",
    title: "Payment approval — MEP mobilization advance",
    summary: "Mobilization advance for the amended MEP scope approved for release against the subcontractor's bank guarantee.",
    detail: "Standard 10% mobilization advance, secured by an on-demand bank guarantee lodged prior to release.",
    dayOffset: 24, status: "Approved",
    tags: ["payment", "mobilization"],
    citations: [cite("Requests & Approvals", "approval")],
    relatedIds: ["e1", "e2"],
  },

  // Standalone items — variety without forcing every row into a storyline
  {
    id: "f1", storyline: "General", sourceType: "document", category: "Schedule",
    title: "As-built survey — Zone B foundations",
    summary: "Topographic as-built survey filed for the completed Zone B foundation works.",
    detail: "Survey confirms as-built levels within tolerance across all Zone B foundation pads.",
    dayOffset: 40, status: "Completed",
    tags: ["survey", "as-built"],
    citations: [cite("Document Center", "document")],
    relatedIds: [],
  },
  {
    id: "f2", storyline: "General", sourceType: "meeting", category: "Governance",
    title: "Monthly client progress review",
    summary: "Monthly steering meeting with the client covering progress, cost, and risk status.",
    detail: "Client acknowledged the Zone C resequencing plan and requested weekly updates until concrete supply is stabilized.",
    dayOffset: 17, status: "Completed",
    tags: ["client-review"],
    citations: [cite("Meetings", "meeting")],
    relatedIds: ["a3", "a4"],
  },
  {
    id: "f3", storyline: "General", sourceType: "risk", category: "Schedule",
    title: "Weather risk — rainy season schedule impact",
    summary: "Seasonal rainfall forecast flagged as a schedule risk to external works planned for the coming six weeks.",
    detail: "Historical weather data suggests 8-10 lost working days across the forecast window; contingency already reflected in the master schedule float.",
    dayOffset: 3, riskLevel: "medium", status: "Open",
    tags: ["weather", "external-works"],
    citations: [cite("Risk Register", "risk")],
    relatedIds: [],
  },
  {
    id: "f4", storyline: "General", sourceType: "site_report", category: "Schedule",
    title: "Daily progress report — Zone D formwork",
    summary: "Zone D formwork progressing on schedule, 60% complete for the level 2 slab.",
    detail: "No blockers reported. Rebar delivery for the remaining 40% confirmed for next week.",
    dayOffset: 1, riskLevel: "low", status: "Open",
    tags: ["formwork", "zone-d"],
    citations: [cite("Daily Site Report", "site_report")],
    relatedIds: [],
  },
];

const CATEGORIES: MemoryCategory[] = [
  "Schedule", "Procurement", "Safety", "Quality", "Commercial", "Contract", "Governance",
];

function isoDaysAgo(days: number, referenceMs: number): string {
  const d = new Date(referenceMs - days * 86_400_000);
  return d.toISOString();
}

function weekLabel(date: Date): string {
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

/** Pure function — same input always produces the same output. Called by
 * lib/useProjectMemory.ts, which is the only place this touches React. */
export function generateProjectMemorySnapshot(
  project: { project_code: string; project_name: string },
  referenceMs: number = Date.UTC(2026, 6, 28), // fixed "today" so the demo dataset never drifts
): ProjectMemorySnapshot {
  const rand = mulberry32(hashString(project.project_code));
  const dateJitterDays = Math.floor(rand() * 5); // small per-project date shift

  const items: MemoryItem[] = TEMPLATES.map((tpl) => {
    const author = AUTHORS[Math.floor(rand() * AUTHORS.length)];
    return {
      id: tpl.id,
      projectCode: project.project_code,
      sourceType: tpl.sourceType,
      category: tpl.category,
      title: tpl.title,
      summary: tpl.summary,
      detail: tpl.detail,
      author,
      date: isoDaysAgo(tpl.dayOffset + dateJitterDays, referenceMs),
      riskLevel: tpl.riskLevel,
      status: tpl.status,
      tags: tpl.tags,
      citations: tpl.citations,
      relatedIds: tpl.relatedIds,
      storyline: tpl.storyline,
    };
  }).sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

  const bySourceType = {} as Record<MemorySourceType, number>;
  const byCategory = {} as Record<MemoryCategory, number>;
  const byRiskLevel: Record<RiskLevel, number> = { low: 0, medium: 0, high: 0, critical: 0 };

  for (const item of items) {
    bySourceType[item.sourceType] = (bySourceType[item.sourceType] ?? 0) + 1;
    byCategory[item.category] = (byCategory[item.category] ?? 0) + 1;
    if (item.riskLevel) byRiskLevel[item.riskLevel] += 1;
  }
  for (const c of CATEGORIES) byCategory[c] = byCategory[c] ?? 0;

  const openActions = items.filter((i) => i.sourceType === "action" && i.status === "Open").length;
  const pendingApprovals = items.filter((i) => i.sourceType === "approval" && i.status === "Pending").length;
  const openRisks = items.filter((i) => i.sourceType === "risk" && i.status === "Open").length;
  const decisionsLogged = items.filter((i) => i.sourceType === "decision").length;

  // 6-week activity bucket, most recent week last
  const weeks: { weekLabel: string; count: number }[] = [];
  for (let w = 5; w >= 0; w--) {
    const weekStart = referenceMs - w * 7 * 86_400_000;
    const weekEnd = weekStart + 7 * 86_400_000;
    const count = items.filter((i) => {
      const t = new Date(i.date).getTime();
      return t >= weekStart && t < weekEnd;
    }).length;
    weeks.push({ weekLabel: weekLabel(new Date(weekStart)), count });
  }

  const highRiskCount = byRiskLevel.high + byRiskLevel.critical;

  return {
    projectCode: project.project_code,
    projectName: project.project_name,
    generatedAt: new Date(referenceMs).toISOString(),
    items,
    authors: AUTHORS,
    stats: {
      total: items.length,
      bySourceType,
      byCategory,
      byRiskLevel,
      openActions,
      pendingApprovals,
      openRisks,
      decisionsLogged,
      oldestDate: items[items.length - 1]?.date ?? new Date(referenceMs).toISOString(),
      newestDate: items[0]?.date ?? new Date(referenceMs).toISOString(),
      activityByWeek: weeks,
    },
    executiveSummary: {
      headline: `${project.project_name} has ${items.length} captured knowledge items across ${Object.keys(bySourceType).length} sources, with ${openRisks} open risk${openRisks === 1 ? "" : "s"} and ${pendingApprovals} approval${pendingApprovals === 1 ? "" : "s"} awaiting a decision.`,
      bullets: [
        `${highRiskCount} item${highRiskCount === 1 ? "" : "s"} flagged high or critical risk, concentrated in ${byCategory.Procurement > byCategory.Contract ? "procurement and schedule" : "contract and commercial"} categories.`,
        `${decisionsLogged} decisions logged and traceable back to the meeting or report that prompted them.`,
        `${openActions} action${openActions === 1 ? "" : "s"} still open against ${items.filter((i) => i.sourceType === "action").length} raised overall.`,
        `Most recent activity: "${items[0]?.title}" (${new Date(items[0]?.date ?? referenceMs).toLocaleDateString()}).`,
      ],
    },
    aiSummary: {
      keyFindings: [
        `Concrete supply is a single-source dependency — the Zone C delay traces to one supplier with no qualified backup, currently tracked as an open procurement risk.`,
        `The excavation variation order and the extended-overheads claim share the same root cause (differing site conditions) and reference the same contract clause review.`,
        `Safety corrective actions on this project close quickly — the Zone A guardrail issue was resolved same-day and reinforced with a toolbox talk within 48 hours.`,
      ],
      recommendations: [
        `Qualify a second ready-mix supplier before the Zone D pour to remove the single-source schedule risk.`,
        `File the extension-of-time notice for the cumulative delay within the contractual window referenced in the clause review.`,
        `Track the pending variation order and payment certificate together — both feed the same cash-flow forecast line.`,
      ],
    },
  };
}
