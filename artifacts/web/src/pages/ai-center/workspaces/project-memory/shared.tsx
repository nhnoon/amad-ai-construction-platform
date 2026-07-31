import {
  FileText, ClipboardList, CalendarDays, FileSignature, Scale, Gavel,
  AlertTriangle, ListChecks, FileCheck2, FlaskConical, type LucideIcon,
} from "lucide-react";
import type { MemorySourceType, MemoryStatus, RiskLevel } from "@/lib/mockProjectMemory";

// Shared display constants for the Project Memory workspace — one place
// mapping the 9 source types / risk levels / statuses to icon, label, and
// color, so the timeline, cards, graph, stats, and drawer all agree on how
// each item type looks instead of drifting per-file.

export const SOURCE_META: Record<MemorySourceType, { label: string; icon: LucideIcon; color: string }> = {
  document:    { label: "Document",    icon: FileText,       color: "#64748b" },
  site_report: { label: "Site Report", icon: ClipboardList,  color: "#0ea5e9" },
  meeting:     { label: "Meeting",     icon: CalendarDays,   color: "#8b5cf6" },
  contract:    { label: "Contract",    icon: FileSignature,  color: "#f97316" },
  claim:       { label: "Claim",       icon: Scale,          color: "#ec4899" },
  decision:    { label: "Decision",    icon: Gavel,          color: "#14b8a6" },
  risk:        { label: "Risk",        icon: AlertTriangle,  color: "#ef4444" },
  action:      { label: "Action",      icon: ListChecks,     color: "#22c55e" },
  approval:    { label: "Approval",    icon: FileCheck2,     color: "#eab308" },
};

export const SOURCE_TYPE_ORDER: MemorySourceType[] = [
  "document", "site_report", "meeting", "contract", "claim", "decision", "risk", "action", "approval",
];

export const RISK_TONE: Record<RiskLevel, string> = {
  critical: "text-rose-700 border-rose-500/40 bg-rose-500/10 dark:text-rose-400",
  high:     "text-red-600 border-red-500/30 bg-red-500/10 dark:text-red-400",
  medium:   "text-amber-600 border-amber-500/30 bg-amber-500/10 dark:text-amber-400",
  low:      "text-slate-600 border-slate-400/30 bg-slate-400/10 dark:text-slate-400",
};

export const STATUS_BADGE: Record<MemoryStatus, string> = {
  Open:      "badge-warning",
  Pending:   "badge-info",
  Approved:  "badge-success",
  Rejected:  "badge-danger",
  Resolved:  "badge-success",
  Completed: "badge-neutral",
};

export const CHART_TOOLTIP_STYLE = {
  backgroundColor: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "0.5rem",
  fontSize: "12px",
  color: "hsl(var(--foreground))",
};

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

// Deliberately loud and consistent everywhere it's used — every panel that
// shows synthetic content carries this, so nothing here can be mistaken for
// a live AI output or real platform data (see constraint in the Project
// Memory build brief: never present demo content as live AI output).
export function DemoDataBadge({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center gap-1 rounded-full border border-dashed border-violet-400/60 bg-violet-500/10 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-violet-600 dark:text-violet-400 ${className}`}
      title="Illustrative demo content for the Project Memory concept — not live data or a real AI output"
    >
      <FlaskConical className="w-3 h-3" />
      Demo Data
    </span>
  );
}
