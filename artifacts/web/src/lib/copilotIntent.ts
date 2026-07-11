// ── AMAD Copilot — deterministic Intent Engine ──────────────────────────────
// No LLM, no ML, no network calls. Pure keyword/phrase matching over the raw
// user message, so the same question phrased different ways ("Portfolio
// summary" / "Summarize portfolio" / "How is the portfolio?") resolves to the
// same intent. Rules are ordered most-specific-first — the first rule whose
// pattern matches wins.

export type IntentKey =
  | "portfolio-summary"
  | "critical-projects"
  | "delayed-projects"
  | "project-health"
  | "procurement-risks"
  | "safety-overview"
  | "project-status"
  | "upcoming-meetings"
  | "open-claims"
  | "rfis"
  | "change-orders"
  | "documents";

interface IntentRule {
  intent: IntentKey;
  patterns: RegExp[];
}

const INTENT_RULES: IntentRule[] = [
  { intent: "rfis", patterns: [/\brfis?\b/i, /request(s)?\s+for\s+information/i] },
  { intent: "change-orders", patterns: [/change\s*orders?/i] },
  { intent: "open-claims", patterns: [/\bclaims?\b/i] },
  { intent: "upcoming-meetings", patterns: [/\bmeetings?\b/i] },
  { intent: "documents", patterns: [/\bdocuments?\b/i, /\bdocs?\b/i, /\bpaperwork\b/i] },
  {
    intent: "project-status",
    patterns: [
      /\bstatus\s+of\b/i,
      /\bproject\s+status\b/i,
      /\bstatus\s+for\b/i,
      /\bupdate\s+on\b/i,
      /\bhow\s+is\s+(project|prj)\b/i,
    ],
  },
  {
    intent: "procurement-risks",
    patterns: [/\bprocurement\b/i, /purchase\s+orders?/i, /purchase\s+requests?/i, /\blate\s+pos?\b/i, /supply\s+chain/i, /مخاطر المشتريات/],
  },
  {
    intent: "safety-overview",
    patterns: [/\bsafety\b/i, /\bncrs?\b/i, /non-?conformance/i, /\bincidents?\b/i, /نظرة عامة على السلامة|مخاطر السلامة/],
  },
  {
    intent: "delayed-projects",
    patterns: [/\bdelayed\b/i, /behind\s+schedule/i, /late\s+projects?\b/i, /\boverdue\b/i],
  },
  {
    intent: "critical-projects",
    patterns: [
      /critical\s+projects?/i,
      /show\s+critical/i,
      /which\s+projects?\s+are\s+critical/i,
      /worst\s+projects?/i,
      /projects?\s+at\s+risk/i,
      /المشاريع الحرجة|مشاريع حرجة/,
    ],
  },
  {
    intent: "project-health",
    patterns: [/project\s+health/i, /health\s+score/i, /health\s+breakdown/i, /how\s+healthy/i, /health\s+distribution/i],
  },
  {
    intent: "portfolio-summary",
    patterns: [
      /\bportfolio\b/i,
      /\boverall\b/i,
      /\bsummarize\b/i,
      /how\s+is\s+(the\s+)?(company|business)\b/i,
      /ملخص المحفظة|المحفظة/,
    ],
  },
];

export function detectIntent(rawMessage: string): IntentKey | null {
  const message = rawMessage.trim();
  if (!message) return null;
  for (const rule of INTENT_RULES) {
    if (rule.patterns.some((p) => p.test(message))) return rule.intent;
  }
  return null;
}

export const UNSUPPORTED_INTENT_REPLY = `I couldn't identify the requested construction topic.

Try asking about:
• Portfolio
• Projects
• Procurement
• Safety
• Meetings
• Claims`;

export function projectReferenceHint(topic: string): string {
  return `Please include a project code or name to check its ${topic} — for example: "${topic} for PRJ-0057".`;
}

export interface ProjectRef {
  id: number;
  project_code: string;
  project_name: string;
}

const PROJECT_CODE_PATTERN = /[A-Za-z]{2,6}-\d{2,6}/;

// Deterministic project lookup: exact project-code match first (e.g.
// "PRJ-0057"), then longest substring match against a known project name.
export function findProjectMatch<T extends ProjectRef>(rawMessage: string, projects: T[] | undefined): T | undefined {
  if (!projects?.length) return undefined;

  const codeMatch = rawMessage.match(PROJECT_CODE_PATTERN);
  if (codeMatch) {
    const byCode = projects.find((p) => p.project_code.toLowerCase() === codeMatch[0].toLowerCase());
    if (byCode) return byCode;
  }

  const lower = rawMessage.toLowerCase();
  let best: T | undefined;
  let bestLen = 0;
  for (const p of projects) {
    const name = p.project_name.toLowerCase();
    if (name.length >= 4 && lower.includes(name) && name.length > bestLen) {
      best = p;
      bestLen = name.length;
    }
  }
  return best;
}
