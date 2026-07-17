import {
  Building2, CalendarDays, Gavel, ShieldAlert, FileSignature, Truck, ClipboardList, StickyNote,
  type LucideIcon,
} from "lucide-react";
import type { StructuredMemory } from "@/lib/aiCenterClient";

// Product UX Phase 1 — the 8 display categories the Memory Center groups,
// searches, and filters by. Existing automatic writers (meeting/site_report/
// contract/supplier/executive_summary) and the "Add Memory" form's own
// category choice (app/ai/memory_records.py::USER_MEMORY_CATEGORIES) both
// map onto this one fixed taxonomy so filtering/grouping behaves the same
// regardless of how a memory was created. Pure display-layer mapping — the
// backend keeps storing its own (source, category) pair unchanged.

export type MemoryBucket =
  | "project" | "meeting" | "decision" | "risk"
  | "contract" | "supplier" | "site_report" | "personal";

export const BUCKET_META: Record<MemoryBucket, { label: string; icon: LucideIcon }> = {
  project:     { label: "Project",        icon: Building2 },
  meeting:     { label: "Meeting",        icon: CalendarDays },
  decision:    { label: "Decision",       icon: Gavel },
  risk:        { label: "Risk",           icon: ShieldAlert },
  contract:    { label: "Contract",       icon: FileSignature },
  supplier:    { label: "Supplier",       icon: Truck },
  site_report: { label: "Site Report",    icon: ClipboardList },
  personal:    { label: "Personal Notes", icon: StickyNote },
};

export const BUCKET_ORDER: MemoryBucket[] = [
  "project", "meeting", "decision", "risk", "contract", "supplier", "site_report", "personal",
];

export function bucketFor(source: string, category: string): MemoryBucket {
  switch (source) {
    case "meeting": return "meeting";
    case "site_report": return "site_report";
    case "contract": return "contract";
    case "supplier": return "supplier";
    case "executive_summary": return "project";
    case "user":
      switch (category) {
        case "project_note": return "project";
        case "meeting_note": return "meeting";
        case "decision_note": return "decision";
        case "risk_note": return "risk";
        case "contract_note": return "contract";
        case "supplier_note": return "supplier";
        case "site_report_note": return "site_report";
        default: return "personal"; // personal_note + legacy user_note
      }
    default: return "personal";
  }
}

export const PRIORITY_TONE: Record<string, string> = {
  High:   "text-rose-600 border-rose-500/30 bg-rose-500/10 dark:text-rose-400",
  Medium: "text-amber-600 border-amber-500/30 bg-amber-500/10 dark:text-amber-400",
  Low:    "text-slate-600 border-slate-400/30 bg-slate-400/10 dark:text-slate-400",
};

export function matchesSearch(item: StructuredMemory, query: string): boolean {
  if (!query.trim()) return true;
  const q = query.trim().toLowerCase();
  return (
    item.title.toLowerCase().includes(q) ||
    item.summary.toLowerCase().includes(q) ||
    (item.project_code ?? "").toLowerCase().includes(q) ||
    item.keywords.some((k) => k.toLowerCase().includes(q))
  );
}
