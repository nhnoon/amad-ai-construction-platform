import { useEffect, useState } from "react";
import { Link } from "wouter";
import { cn } from "@/lib/utils";
import type { CopilotCitation } from "@/lib/copilotClient";

// Shared premium UI pieces for AI agent answers (Executive Copilot,
// Procurement Agent, Meeting Agent) — presentation only. No new data is
// fetched or invented here; every value rendered comes from the existing
// CopilotQueryResponse fields (confidence, citations) already returned by
// the backend. Used by both AIDrawer.tsx and pages/meeting-detail.tsx so
// the same visual language doesn't get duplicated/diverge between them.

// ── 1. AI Thinking Progress ─────────────────────────────────────────────
// Purely a client-side reveal animation over a fixed step sequence — it
// does not change how long the real request takes. Steps advance on a
// fixed schedule and then HOLD at the final step (with a pulsing dot)
// until the real response replaces this component; the actual wait time
// is whatever the network call takes, never artificially extended.
const THINKING_STEPS_EN = [
  "Understanding your request",
  "Retrieving live AMAD data",
  "Validating evidence",
  "Preparing executive analysis",
];
const THINKING_STEPS_AR = [
  "فهم طلبك",
  "جلب بيانات آماد المباشرة",
  "التحقق من الأدلة",
  "إعداد التحليل التنفيذي",
];
const THINKING_STEP_DELAY_MS = 650;

export function AiThinkingProgress({ ar }: { ar: boolean }) {
  const steps = ar ? THINKING_STEPS_AR : THINKING_STEPS_EN;
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    setActiveIndex(0);
    const timers = steps.slice(1).map((_, i) =>
      window.setTimeout(() => setActiveIndex(i + 1), (i + 1) * THINKING_STEP_DELAY_MS)
    );
    return () => timers.forEach((id) => window.clearTimeout(id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      className={cn("rounded-2xl rounded-bl-sm border border-white/10 bg-white/[0.06] px-4 py-3 space-y-1.5 min-w-[230px]")}
      dir={ar ? "rtl" : "ltr"}
    >
      {steps.map((label, i) => {
        const done = i < activeIndex;
        const active = i === activeIndex;
        return (
          <div
            key={label}
            className={cn("flex items-center gap-2 text-xs animate-in fade-in-0 duration-300", ar && "flex-row-reverse text-right")}
          >
            <span
              className={cn(
                "flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border text-[9px] transition-colors duration-300",
                done
                  ? "border-emerald-500/50 bg-emerald-500/20 text-emerald-400"
                  : active
                    ? "border-amber-400/60"
                    : "border-white/15"
              )}
            >
              {done ? "✓" : active ? <span className="h-1.5 w-1.5 rounded-full bg-amber-300 animate-pulse" /> : null}
            </span>
            <span className={cn(done ? "text-white/70" : active ? "text-white/90 font-medium" : "text-white/25")}>
              {label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

// ── 2. Executive Confidence ─────────────────────────────────────────────
// The backend only ever returns a 4-level confidence enum (none/low/medium
// /high — see CopilotPipeline._compute_confidence). There is no numeric
// score. The percentages below are a fixed, deterministic presentation of
// that same enum (not a new metric) so the bar has something honest to
// fill — never a fabricated precise measurement.
const CONFIDENCE_PRESENTATION: Record<
  string,
  { pct: number; textClass: string; barClass: string; labelEn: string; labelAr: string }
> = {
  high:   { pct: 92, textClass: "text-emerald-400", barClass: "bg-emerald-500", labelEn: "High",   labelAr: "عالية" },
  medium: { pct: 65, textClass: "text-amber-400",   barClass: "bg-amber-500",   labelEn: "Medium", labelAr: "متوسطة" },
  low:    { pct: 35, textClass: "text-orange-400",  barClass: "bg-orange-500",  labelEn: "Low",    labelAr: "منخفضة" },
  none:   { pct: 10, textClass: "text-white/40",    barClass: "bg-white/20",    labelEn: "None",   labelAr: "لا توجد" },
};

export function ConfidenceMeter({ confidence, ar }: { confidence: string; ar: boolean }) {
  const p = CONFIDENCE_PRESENTATION[confidence] ?? CONFIDENCE_PRESENTATION.none;
  return (
    <div className={cn("flex items-center gap-1.5 shrink-0", ar && "flex-row-reverse")} title={ar ? "الثقة" : "Confidence"}>
      <span className={cn("text-[10px] font-bold uppercase tracking-wide", p.textClass)}>
        {ar ? p.labelAr : p.labelEn}
      </span>
      <div className="h-1.5 w-10 rounded-full bg-white/10 overflow-hidden">
        <div className={cn("h-full rounded-full transition-all duration-700 ease-out", p.barClass)} style={{ width: `${p.pct}%` }} />
      </div>
      <span className="text-[10px] text-white/40 tabular-nums">{p.pct}%</span>
    </div>
  );
}

// ── 3. Sources — grouped, expandable cards ──────────────────────────────
// Exported so other surfaces with a different visual theme than this dark
// panel (e.g. pages/meeting-detail.tsx, which uses the app's light/dark
// design tokens rather than this fixed dark-glass palette) can group
// citations the same way without a second copy of the label map drifting.
export const SOURCE_TYPE_LABELS: Record<string, { en: string; ar: string }> = {
  project:              { en: "Projects",           ar: "المشاريع" },
  purchase_order:       { en: "Purchase Orders",    ar: "أوامر الشراء" },
  purchase_request:     { en: "Purchase Requests",  ar: "طلبات الشراء" },
  supplier:             { en: "Suppliers",          ar: "الموردون" },
  safety:               { en: "Safety Events",      ar: "أحداث السلامة" },
  ncr:                  { en: "NCRs",                ar: "تقارير عدم المطابقة" },
  site_report:          { en: "Site Reports",       ar: "تقارير الموقع" },
  meeting:              { en: "Meetings",           ar: "الاجتماعات" },
  project_decision:     { en: "Decisions",          ar: "القرارات" },
  meeting_action_item:  { en: "Action Items",       ar: "بنود العمل" },
  meeting_attendee:     { en: "Attendees",          ar: "الحضور" },
};

export function prettifySourceType(type: string): string {
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function SourcesGrouped({ citations, ar }: { citations: CopilotCitation[]; ar: boolean }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  if (!citations.length) return null;

  const groups = new Map<string, CopilotCitation[]>();
  for (const c of citations) {
    const key = c.source_type || "other";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(c);
  }

  const toggle = (key: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <div className="space-y-1.5">
      <p className="text-[10px] font-bold uppercase tracking-wider text-white/40">{ar ? "المصادر" : "Sources"}</p>
      <div className="grid grid-cols-2 gap-1.5">
        {Array.from(groups.entries()).map(([type, items]) => {
          const label = SOURCE_TYPE_LABELS[type]
            ? (ar ? SOURCE_TYPE_LABELS[type].ar : SOURCE_TYPE_LABELS[type].en)
            : prettifySourceType(type);
          const isOpen = expanded.has(type);
          return (
            <div key={type} className="rounded-lg border border-white/10 bg-white/[0.03] overflow-hidden min-w-0">
              <button
                type="button"
                onClick={() => toggle(type)}
                className={cn(
                  "w-full flex items-center justify-between gap-1.5 px-2.5 py-2 text-start hover:bg-white/[0.05] transition-colors",
                  ar && "flex-row-reverse text-end"
                )}
              >
                <span className="text-xs font-medium text-white/80 truncate">{label}</span>
                <span className="text-[10px] text-white/40 shrink-0">
                  {items.length} {ar ? "سجل" : items.length === 1 ? "record" : "records"}
                </span>
              </button>
              {isOpen && (
                <ul className={cn("px-2.5 pb-2 space-y-1 text-[11px] text-white/60", ar && "text-end")}>
                  {items.map((c) => {
                    const href = (c.ui_metadata as Record<string, unknown> | undefined)?.href as string | undefined;
                    return (
                      <li key={c.id} className="truncate">
                        {href ? (
                          <Link href={href} className="hover:underline">{c.label}</Link>
                        ) : (
                          c.label
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── 4. Executive Status Badges ──────────────────────────────────────────
// Purely presentational color mapping over whatever status/level string
// the backend already returns (Excellent/Good/At Risk/Critical for health,
// Active/Delayed/Completed for projects, etc.) — values are never renamed.
const STATUS_TONE: Record<string, string> = {
  excellent:  "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  good:       "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  healthy:    "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  active:     "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  "on track": "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  completed:  "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  approved:   "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  delivered:  "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  watch:      "bg-amber-500/15 text-amber-400 border-amber-500/30",
  medium:     "bg-amber-500/15 text-amber-400 border-amber-500/30",
  pending:    "bg-amber-500/15 text-amber-400 border-amber-500/30",
  "under review": "bg-amber-500/15 text-amber-400 border-amber-500/30",
  "at risk":  "bg-orange-500/15 text-orange-400 border-orange-500/30",
  delayed:    "bg-orange-500/15 text-orange-400 border-orange-500/30",
  "on hold":  "bg-orange-500/15 text-orange-400 border-orange-500/30",
  critical:   "bg-red-500/15 text-red-400 border-red-500/30",
  overdue:    "bg-red-500/15 text-red-400 border-red-500/30",
  cancelled:  "bg-white/10 text-white/50 border-white/15",
};

export function StatusBadge({ status }: { status?: string | null }) {
  if (!status) return null;
  const tone = STATUS_TONE[status.toLowerCase()] ?? "bg-white/10 text-white/60 border-white/15";
  return (
    <span className={cn("inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold whitespace-nowrap shrink-0", tone)}>
      {status}
    </span>
  );
}

// ── 5. Executive Quick Actions ──────────────────────────────────────────
export const QUICK_ACTIONS: { en: string; ar: string }[] = [
  { en: "Executive Summary", ar: "ملخص تنفيذي" },
  { en: "Identify Risks", ar: "تحديد المخاطر" },
  { en: "Recommendations", ar: "التوصيات" },
  { en: "Generate Report", ar: "إنشاء تقرير" },
  { en: "Export Summary", ar: "تصدير الملخص" },
];

export function ExecutiveQuickActions({
  ar,
  onSelect,
}: {
  ar: boolean;
  onSelect: (text: string) => void;
}) {
  return (
    <div
      className="flex flex-wrap gap-1.5 px-5 py-2.5 border-b border-white/10 shrink-0"
      dir={ar ? "rtl" : "ltr"}
    >
      {QUICK_ACTIONS.map((action) => (
        <button
          key={action.en}
          onClick={() => onSelect(ar ? action.ar : action.en)}
          className="rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1 text-xs text-white/70 hover:bg-white/10 hover:border-white/20 transition-colors whitespace-nowrap"
        >
          {ar ? action.ar : action.en}
        </button>
      ))}
    </div>
  );
}
