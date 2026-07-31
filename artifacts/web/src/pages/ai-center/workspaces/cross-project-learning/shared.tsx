import {
  BookOpen, Scale, FileSignature, CalendarDays, ClipboardList, ShieldAlert, ClipboardCheck,
  ShoppingCart, CalendarClock, Wallet, Truck, Gavel, FileText, AlertTriangle, ListChecks, FlaskConical,
  type LucideIcon,
} from "lucide-react";
import type {
  Department, KnowledgeCategory, Outcome, RiskLevel, SourceType,
} from "@/lib/mockCrossProjectLearning";

// Shared display constants for the Cross-Project Learning workspace — one
// place mapping the 11 knowledge categories / 7 source types / risk
// levels / outcomes to icon, label, and color so search results, the
// drawer, the timeline, and the knowledge graph all agree.

export const CATEGORY_META: Record<KnowledgeCategory, { icon: LucideIcon }> = {
  "Lessons Learned": { icon: BookOpen },
  Claims: { icon: Scale },
  Contracts: { icon: FileSignature },
  Meetings: { icon: CalendarDays },
  "Site Reports": { icon: ClipboardList },
  Safety: { icon: ShieldAlert },
  Quality: { icon: ClipboardCheck },
  Procurement: { icon: ShoppingCart },
  Schedule: { icon: CalendarClock },
  Cost: { icon: Wallet },
  Suppliers: { icon: Truck },
};

export const CATEGORY_ORDER: KnowledgeCategory[] = [
  "Lessons Learned", "Claims", "Contracts", "Meetings", "Site Reports",
  "Safety", "Quality", "Procurement", "Schedule", "Cost", "Suppliers",
];

export const SOURCE_TYPE_META: Record<SourceType, { label: string; icon: LucideIcon; color: string }> = {
  meeting:  { label: "Meeting",  icon: CalendarDays,  color: "#8b5cf6" },
  document: { label: "Document", icon: FileText,      color: "#64748b" },
  claim:    { label: "Claim",    icon: Scale,          color: "#ec4899" },
  contract: { label: "Contract", icon: FileSignature, color: "#f97316" },
  decision: { label: "Decision", icon: Gavel,          color: "#14b8a6" },
  risk:     { label: "Risk",     icon: AlertTriangle,  color: "#ef4444" },
  action:   { label: "Action",   icon: ListChecks,     color: "#22c55e" },
};

export const SOURCE_TYPE_ORDER: SourceType[] = ["meeting", "document", "claim", "contract", "decision", "risk", "action"];

export const DEPARTMENTS: Department[] = ["Engineering", "Procurement", "Site Operations", "Commercial", "Safety", "Quality", "Executive"];

export const RISK_BADGE: Record<RiskLevel, string> = {
  Low: "badge-success", Medium: "badge-info", High: "badge-warning", Critical: "badge-danger",
};

export const OUTCOME_BADGE: Record<Outcome, string> = {
  Successful: "badge-success", Partial: "badge-warning", Unsuccessful: "badge-danger",
};

export function confidenceTone(confidence: number): string {
  if (confidence >= 75) return "text-emerald-600 dark:text-emerald-400";
  if (confidence >= 50) return "text-amber-600 dark:text-amber-400";
  return "text-muted-foreground";
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

// Deliberately loud and consistent everywhere it's used — this workspace
// never presents keyword-matched demo retrieval as real semantic/vector
// search or a live AI output (build constraint: no live AI, no
// embeddings, no vector database).
export function DemoDataBadge({ label = "Demo Data — Illustrative Knowledge Retrieval", className = "" }: { label?: string; className?: string }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded-full border border-dashed border-violet-400/60 bg-violet-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-violet-600 dark:text-violet-400 ${className}`}
      title="Illustrative demo knowledge retrieval — keyword-matched, not real semantic or vector search"
    >
      <FlaskConical className="w-3 h-3" />
      {label}
    </span>
  );
}

// ── Recent / saved searches — genuinely functional client-side
// preferences (same tradeoff already made for pinned memories in
// ai-center/memoryTaxonomy.ts): stored in localStorage, scoped per
// browser, not backed by a real endpoint. ────────────────────────────────

const RECENT_KEY = "amad_cpl_recent_searches";
const SAVED_KEY = "amad_cpl_saved_searches";
const MAX_RECENT = 8;

function readList(key: string): string[] {
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as string[]) : [];
  } catch {
    return [];
  }
}
function writeList(key: string, list: string[]): void {
  try { window.localStorage.setItem(key, JSON.stringify(list)); } catch { /* private browsing / quota — no-op */ }
}

export function getRecentSearches(): string[] { return readList(RECENT_KEY); }
export function addRecentSearch(query: string): string[] {
  const q = query.trim();
  if (!q) return getRecentSearches();
  const next = [q, ...getRecentSearches().filter((s) => s.toLowerCase() !== q.toLowerCase())].slice(0, MAX_RECENT);
  writeList(RECENT_KEY, next);
  return next;
}

export function getSavedSearches(): string[] { return readList(SAVED_KEY); }
export function toggleSavedSearch(query: string): string[] {
  const q = query.trim();
  if (!q) return getSavedSearches();
  const current = getSavedSearches();
  const next = current.some((s) => s.toLowerCase() === q.toLowerCase())
    ? current.filter((s) => s.toLowerCase() !== q.toLowerCase())
    : [q, ...current];
  writeList(SAVED_KEY, next);
  return next;
}
