import { useEffect, useRef, useState } from "react";
import {
  X, Sparkles, Send, Paperclip, Mic, Plus, ArrowLeft,
  AlertTriangle, Target, Gauge, Activity, Building2, Clock, Package, FileText, ShieldAlert,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useGetDashboardSummary } from "@workspace/api-client-react";
import { cn } from "@/lib/utils";
import { useExecutive, type ExecutiveIntelligence } from "../lib/useExecutive";

// ── AMAD AI Copilot — frontend shell ─────────────────────────────────────────
// No AI provider, no backend changes. All four quick-action chips read the
// same existing live hooks the Dashboard already uses (useExecutive →
// /api/v1/executive, useGetDashboardSummary → /api/v1/dashboard/summary),
// with a 3s client-side timeout so a response can never hang forever.
// Manual typed messages get an honest guided reply pointing at the chips
// above — never a loading state, never fabricated data.
//
// The "streaming" effect below is purely a client-side reveal animation over
// text that is already fully loaded — it does not simulate typing an
// in-progress response, and it always finishes within ~1.5s (bounded).

type ChatRole = "user" | "assistant-guide" | "assistant-insight";
type InsightType = "portfolio" | "critical-projects" | "procurement-risks" | "safety-overview";

interface CopilotMessage {
  id: string;
  role: ChatRole;
  text?: string; // user text, or the guided reply for assistant-guide
  insightType?: InsightType; // set for assistant-insight
  createdAt: number;
}

const SUGGESTIONS = ["Show critical projects", "Portfolio summary", "Procurement risks", "Safety overview"];

const CHIP_INSIGHT_MAP: Record<string, InsightType> = {
  "Show critical projects": "critical-projects",
  "Portfolio summary": "portfolio",
  "Procurement risks": "procurement-risks",
  "Safety overview": "safety-overview",
};

const UNAVAILABLE = "Unavailable from current database.";
const DATA_TIMEOUT_MS = 3000;

const GUIDED_REPLY_TEXT =
  "I can currently answer portfolio summary, critical projects, procurement risks, and safety overview using live AMAD data. Choose one of the quick actions above.";

function fieldText(value: number | string | undefined | null): string {
  return value === undefined || value === null || value === "" ? UNAVAILABLE : String(value);
}

function plural(n: number | undefined, word: string): string {
  return n === 1 ? word : `${word}s`;
}

function isAre(n: number | undefined): string {
  return n === 1 ? "is" : "are";
}

function hasHave(n: number | undefined): string {
  return n === 1 ? "has" : "have";
}

function capitalize(s: string): string {
  return s.length ? s[0].toUpperCase() + s.slice(1) : s;
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// Deterministic, category-mapped recommendation — not fabricated data, just a
// fixed phrase keyed to a risk category already computed by the live backend.
const RISK_ACTION_MAP: Record<string, string> = {
  procurement: "prioritize procurement recovery and executive review for critical projects",
  safety: "commission an immediate safety audit and executive review for critical projects",
  quality: "prioritize NCR closure and executive review for critical projects",
  schedule: "convene a schedule recovery review and executive review for critical projects",
  health: "schedule an emergency portfolio health review for critical projects",
};

type DashboardSummaryData = {
  delayed_projects?: number;
  late_purchase_orders?: number;
  open_purchase_requests?: number;
  total_purchase_orders?: number;
  total_purchase_requests?: number;
  high_severity_events?: number;
  total_safety_events?: number;
  open_ncrs?: number;
  total_ncrs?: number;
};

function findRisk(execData: ExecutiveIntelligence | undefined, category: string) {
  return execData?.biggest_risks?.find((r) => r.category === category);
}

interface InsightView {
  title: string;
  riskSectionLabel: string;
  overview: string;
  keyFindings: string[];
  riskText: string;
  recommendedAction: string;
  metrics: { icon: React.ElementType; label: string; value: string }[];
}

// Builds the full narrative + metrics for one insight type from the live
// query results already fetched for the panel — no new data, no fabrication.
function buildInsight(
  type: InsightType,
  execData: ExecutiveIntelligence | undefined,
  execIsError: boolean,
  summaryData: DashboardSummaryData | undefined,
  summaryIsError: boolean
): InsightView {
  if (type === "critical-projects") {
    const risk = findRisk(execData, "health");
    const criticalCount = execData?.critical_count;
    const atRiskCount = execData?.at_risk_count;
    const topCritical = (execData?.attention_required ?? []).slice(0, 3);
    return {
      title: "Critical Projects Analysis",
      riskSectionLabel: "Risk Interpretation",
      overview: execIsError
        ? UNAVAILABLE
        : `${fieldText(criticalCount)} ${plural(criticalCount, "project")} ${isAre(criticalCount)} currently in critical health condition, out of ${fieldText(execData?.total_projects)} total projects in the portfolio.`,
      keyFindings: execIsError
        ? [UNAVAILABLE]
        : topCritical.length > 0
          ? topCritical.map((p) => `${p.project_code} — ${p.project_name} (score ${p.score}/100): ${p.primary_reason}`)
          : ["No critical or at-risk projects at this time."],
      riskText: execIsError || !risk ? UNAVAILABLE : `${capitalize(risk.detail)}.`,
      recommendedAction: execIsError || !risk ? UNAVAILABLE : `${capitalize(RISK_ACTION_MAP.health)}.`,
      metrics: [
        { icon: AlertTriangle, label: "Critical", value: execIsError ? UNAVAILABLE : fieldText(criticalCount) },
        { icon: Activity, label: "At Risk", value: execIsError ? UNAVAILABLE : fieldText(atRiskCount) },
        { icon: Building2, label: "Total Projects", value: execIsError ? UNAVAILABLE : fieldText(execData?.total_projects) },
        { icon: Gauge, label: "Portfolio Score", value: execIsError ? UNAVAILABLE : fieldText(execData?.portfolio_score) },
        { icon: Activity, label: "Status", value: execIsError ? UNAVAILABLE : fieldText(execData?.portfolio_status) },
      ],
    };
  }

  if (type === "procurement-risks") {
    const risk = findRisk(execData, "procurement");
    return {
      title: "Procurement Risk Analysis",
      riskSectionLabel: "Risk Interpretation",
      overview: summaryIsError
        ? UNAVAILABLE
        : `${fieldText(summaryData?.late_purchase_orders)} ${plural(summaryData?.late_purchase_orders, "purchase order")} ${isAre(summaryData?.late_purchase_orders)} currently late, and ${fieldText(summaryData?.open_purchase_requests)} ${plural(summaryData?.open_purchase_requests, "purchase request")} ${isAre(summaryData?.open_purchase_requests)} open across the portfolio.`,
      keyFindings: summaryIsError
        ? [UNAVAILABLE]
        : [
            `${fieldText(summaryData?.late_purchase_orders)} of ${fieldText(summaryData?.total_purchase_orders)} purchase orders are late`,
            `${fieldText(summaryData?.open_purchase_requests)} of ${fieldText(summaryData?.total_purchase_requests)} purchase requests are open or pending`,
            risk ? `Procurement risk severity: ${capitalize(risk.severity)}` : UNAVAILABLE,
          ],
      riskText: execIsError || !risk ? UNAVAILABLE : `${capitalize(risk.detail)}.`,
      recommendedAction: execIsError || !risk ? UNAVAILABLE : `${capitalize(RISK_ACTION_MAP.procurement)}.`,
      metrics: [
        { icon: Package, label: "Late POs", value: summaryIsError ? UNAVAILABLE : fieldText(summaryData?.late_purchase_orders) },
        { icon: FileText, label: "Open PRs", value: summaryIsError ? UNAVAILABLE : fieldText(summaryData?.open_purchase_requests) },
        { icon: Package, label: "Total POs", value: summaryIsError ? UNAVAILABLE : fieldText(summaryData?.total_purchase_orders) },
        { icon: FileText, label: "Total PRs", value: summaryIsError ? UNAVAILABLE : fieldText(summaryData?.total_purchase_requests) },
        { icon: AlertTriangle, label: "Severity", value: risk ? capitalize(risk.severity) : UNAVAILABLE },
      ],
    };
  }

  if (type === "safety-overview") {
    const risk = findRisk(execData, "safety");
    return {
      title: "Safety & Risk Overview",
      riskSectionLabel: "Risk Interpretation",
      overview: summaryIsError
        ? UNAVAILABLE
        : `${fieldText(summaryData?.high_severity_events)} high or critical severity safety ${plural(summaryData?.high_severity_events, "event")} ${hasHave(summaryData?.high_severity_events)} been recorded, out of ${fieldText(summaryData?.total_safety_events)} total safety events across the portfolio.`,
      keyFindings: summaryIsError
        ? [UNAVAILABLE]
        : [
            `${fieldText(summaryData?.high_severity_events)} high/critical severity safety events requiring investigation`,
            `${fieldText(summaryData?.open_ncrs)} of ${fieldText(summaryData?.total_ncrs)} non-conformance reports remain open`,
            risk ? `Safety risk severity: ${capitalize(risk.severity)}` : UNAVAILABLE,
          ],
      riskText: execIsError || !risk ? UNAVAILABLE : `${capitalize(risk.detail)}.`,
      recommendedAction: execIsError || !risk ? UNAVAILABLE : `${capitalize(RISK_ACTION_MAP.safety)}.`,
      metrics: [
        { icon: ShieldAlert, label: "High Severity", value: summaryIsError ? UNAVAILABLE : fieldText(summaryData?.high_severity_events) },
        { icon: Activity, label: "Total Events", value: summaryIsError ? UNAVAILABLE : fieldText(summaryData?.total_safety_events) },
        { icon: AlertTriangle, label: "Open NCRs", value: summaryIsError ? UNAVAILABLE : fieldText(summaryData?.open_ncrs) },
        { icon: FileText, label: "Total NCRs", value: summaryIsError ? UNAVAILABLE : fieldText(summaryData?.total_ncrs) },
        { icon: AlertTriangle, label: "Severity", value: risk ? capitalize(risk.severity) : UNAVAILABLE },
      ],
    };
  }

  // portfolio (default)
  const mainRisk = execData?.biggest_risks?.[0];
  const criticalCount = execData?.critical_count;
  const delayedCount = summaryData?.delayed_projects;
  return {
    title: "Portfolio Executive Summary",
    riskSectionLabel: "Primary Risk",
    overview: execIsError
      ? UNAVAILABLE
      : `The portfolio is currently ${fieldText(execData?.portfolio_status)} with an average health score of ${fieldText(execData?.portfolio_score)}/100. ${fieldText(criticalCount)} ${plural(criticalCount, "project")} require executive attention, and ${
          summaryIsError ? UNAVAILABLE : `${delayedCount} ${plural(delayedCount, "project")} are delayed`
        }.`,
    keyFindings: execIsError
      ? [UNAVAILABLE]
      : [
          `Portfolio score is ${fieldText(execData?.portfolio_score)}/100 (${fieldText(execData?.portfolio_status)})`,
          `${fieldText(criticalCount)} ${plural(criticalCount, "project")} in critical health condition`,
          summaryIsError ? UNAVAILABLE : `${delayedCount} ${plural(delayedCount, "project")} behind schedule`,
        ],
    riskText:
      execIsError || !mainRisk ? UNAVAILABLE : `The primary risk driver is ${mainRisk.label.toLowerCase()}, with ${mainRisk.detail}.`,
    recommendedAction:
      execIsError || !mainRisk
        ? UNAVAILABLE
        : `${capitalize(RISK_ACTION_MAP[mainRisk.category] ?? "review portfolio risk drivers and prioritize executive attention")}.`,
    metrics: [
      { icon: Gauge, label: "Portfolio Score", value: execIsError ? UNAVAILABLE : fieldText(execData?.portfolio_score) },
      { icon: Activity, label: "Status", value: execIsError ? UNAVAILABLE : fieldText(execData?.portfolio_status) },
      { icon: Building2, label: "Projects", value: execIsError ? UNAVAILABLE : fieldText(execData?.total_projects) },
      { icon: AlertTriangle, label: "Critical", value: execIsError ? UNAVAILABLE : fieldText(execData?.critical_count) },
      { icon: Clock, label: "Delayed", value: summaryIsError ? UNAVAILABLE : fieldText(summaryData?.delayed_projects) },
    ],
  };
}

// Reveals `totalSteps` sections one at a time over `stepDelayMs` apart —
// bounded (never infinite), starts as soon as `active` is true.
function useProgressiveReveal(totalSteps: number, active: boolean, stepDelayMs = 320): number {
  const [revealed, setRevealed] = useState(active ? 1 : 0);
  useEffect(() => {
    if (!active) return;
    setRevealed(1);
    let step = 1;
    let timer: number | undefined;
    const advance = () => {
      step += 1;
      setRevealed(step);
      if (step < totalSteps) {
        timer = window.setTimeout(advance, stepDelayMs);
      }
    };
    timer = window.setTimeout(advance, stepDelayMs);
    return () => {
      if (timer) window.clearTimeout(timer);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);
  return revealed;
}

function IconChip({ icon: Icon, className = "h-7 w-7" }: { icon: React.ElementType; className?: string }) {
  return (
    <div
      className={`flex shrink-0 items-center justify-center rounded-lg ${className}`}
      style={{ backgroundColor: "#eab30817", boxShadow: "0 0 0 1px #eab30830" }}
    >
      <Icon className="h-3.5 w-3.5" style={{ color: "#eab308" }} />
    </div>
  );
}

function MetricMiniCard({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3 transition-all duration-200 hover:border-white/20 hover:bg-white/[0.08] hover:-translate-y-0.5">
      <div className="flex items-center gap-2 mb-2">
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md" style={{ backgroundColor: "#eab30817" }}>
          <Icon className="h-3.5 w-3.5" style={{ color: "#eab308" }} />
        </div>
        <span className="text-[9px] font-semibold uppercase tracking-wider text-white/40 truncate">{label}</span>
      </div>
      <p className="text-lg font-bold text-white leading-none truncate">{value}</p>
    </div>
  );
}

// Executive-formatted, streamed-in insight response. All values come
// straight from the props (the same live query results the Dashboard uses)
// — nothing here is fabricated, only the presentation is enhanced.
function InsightContent({
  insightType,
  execData,
  execIsError,
  summaryData,
  summaryIsError,
}: {
  insightType: InsightType;
  execData?: ExecutiveIntelligence;
  execIsError: boolean;
  summaryData?: DashboardSummaryData;
  summaryIsError: boolean;
}) {
  const revealed = useProgressiveReveal(5, true, 320);
  const view = buildInsight(insightType, execData, execIsError, summaryData, summaryIsError);

  return (
    <div className="max-w-[92%] rounded-2xl rounded-bl-sm border border-white/10 bg-white/[0.06] px-4 py-4">
      <div className="flex items-center gap-2 mb-2">
        <span
          className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider"
          style={{ backgroundColor: "#16a34a1A", color: "#16a34a" }}
        >
          <span className="h-1.5 w-1.5 rounded-full bg-current" />
          Live AMAD Analysis
        </span>
      </div>
      <h3 className="text-base font-bold text-white mb-3">{view.title}</h3>

      <div className="space-y-4">
        {revealed >= 1 && (
          <div className="animate-in fade-in-0 slide-in-from-bottom-1 duration-300 space-y-1.5">
            <p className="text-[10px] font-bold uppercase tracking-wider text-white/40">Overview</p>
            <p className="text-sm text-white/85 leading-relaxed">{view.overview}</p>
          </div>
        )}

        {revealed >= 2 && (
          <div className="animate-in fade-in-0 slide-in-from-bottom-1 duration-300 space-y-1.5">
            <p className="text-[10px] font-bold uppercase tracking-wider text-white/40">Key Findings</p>
            <ul className="space-y-1 text-sm text-white/80">
              {view.keyFindings.map((f, i) => (
                <li key={i}>• {f}</li>
              ))}
            </ul>
          </div>
        )}

        {revealed >= 3 && (
          <div className="animate-in fade-in-0 slide-in-from-bottom-1 duration-300">
            <p className="text-[10px] font-bold uppercase tracking-wider text-white/40 mb-1.5">{view.riskSectionLabel}</p>
            <div className="flex gap-2.5 rounded-xl border-l-4 border-amber-500/60 bg-amber-500/[0.08] px-3.5 py-3">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-400" />
              <p className="text-sm text-amber-100/90 leading-relaxed">{view.riskText}</p>
            </div>
          </div>
        )}

        {revealed >= 4 && (
          <div className="animate-in fade-in-0 slide-in-from-bottom-1 duration-300">
            <p className="text-[10px] font-bold uppercase tracking-wider text-white/40 mb-1.5">Recommended Action</p>
            <div
              className="flex gap-2.5 rounded-xl border px-3.5 py-3"
              style={{ borderColor: "#eab30840", backgroundColor: "#eab30812" }}
            >
              <Target className="h-4 w-4 shrink-0 mt-0.5" style={{ color: "#eab308" }} />
              <div>
                <p className="text-[10px] font-bold uppercase tracking-wide mb-0.5" style={{ color: "#eab308" }}>
                  Executive Recommendation
                </p>
                <p className="text-sm text-white/90 leading-relaxed">{view.recommendedAction}</p>
              </div>
            </div>
          </div>
        )}

        {revealed >= 5 && (
          <div className="animate-in fade-in-0 slide-in-from-bottom-1 duration-300 grid grid-cols-2 gap-2.5">
            {view.metrics.map((m) => (
              <MetricMiniCard key={m.label} icon={m.icon} label={m.label} value={m.value} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface AIDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AIDrawer({ isOpen, onClose }: AIDrawerProps) {
  const { t } = useTranslation();
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [input, setInput] = useState("");
  const [dataTimedOut, setDataTimedOut] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dataTimeoutRef = useRef<number | null>(null);

  // Only fetch while the panel is open — reuses the exact same hooks/queries
  // the Dashboard already relies on, so no new endpoint or query is added.
  const { data: execData, isLoading: execLoading, isError: execIsError } = useExecutive(isOpen);
  const {
    data: summaryData,
    isLoading: summaryLoading,
    isError: summaryIsError,
  } = useGetDashboardSummary({ query: { enabled: isOpen, queryKey: ["/api/v1/dashboard/summary"] } });

  const dataLoading = execLoading || summaryLoading;

  // Lock page scroll while open — dashboard stays visible (blurred) behind it,
  // it just shouldn't scroll underneath the panel.
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  // ESC closes the panel — never trap the user inside it.
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Autofocus the composer when the panel opens.
  useEffect(() => {
    if (isOpen) textareaRef.current?.focus();
  }, [isOpen]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, dataLoading, dataTimedOut]);

  // Once the live-data query actually settles (success or error), the 3s
  // "taking longer than expected" timeout is moot — clear it so a late
  // response is never overridden by a stale timeout message.
  useEffect(() => {
    if (!dataLoading && dataTimeoutRef.current) {
      window.clearTimeout(dataTimeoutRef.current);
      dataTimeoutRef.current = null;
    }
  }, [dataLoading]);

  // Clear any pending timeout on unmount.
  useEffect(() => {
    return () => {
      if (dataTimeoutRef.current) window.clearTimeout(dataTimeoutRef.current);
    };
  }, []);

  const startNewChat = () => {
    setMessages([]);
    setInput("");
    setDataTimedOut(false);
    if (dataTimeoutRef.current) {
      window.clearTimeout(dataTimeoutRef.current);
      dataTimeoutRef.current = null;
    }
    textareaRef.current?.focus();
  };

  const sendGuidedReply = (text: string) => {
    const content = text.trim();
    if (!content) return;
    const now = Date.now();
    setMessages((prev) => [
      ...prev,
      { id: `u-${now}`, role: "user", text: content, createdAt: now },
      { id: `a-${now}`, role: "assistant-guide", text: GUIDED_REPLY_TEXT, createdAt: now },
    ]);
    setInput("");
    textareaRef.current?.focus();
  };

  const askInsight = (chip: string, type: InsightType) => {
    setDataTimedOut(false);
    if (dataTimeoutRef.current) window.clearTimeout(dataTimeoutRef.current);
    dataTimeoutRef.current = window.setTimeout(() => {
      setDataTimedOut(true);
    }, DATA_TIMEOUT_MS);

    const now = Date.now();
    setMessages((prev) => [
      ...prev,
      { id: `u-${now}`, role: "user", text: chip, createdAt: now },
      { id: `a-${now}`, role: "assistant-insight", insightType: type, createdAt: now },
    ]);
  };

  const handleChipClick = (chip: string) => {
    askInsight(chip, CHIP_INSIGHT_MAP[chip]);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendGuidedReply(input);
    }
  };

  if (!isOpen) return null;

  const showDataTimeoutMessage = dataLoading && dataTimedOut;

  return (
    <>
      {/* Soft dark backdrop — dashboard stays visible behind it, just dimmed
          and slightly blurred. Clicking it closes the panel. */}
      <div
        className="fixed inset-0 z-45 bg-black/45 backdrop-blur-[3px] transition-opacity duration-300"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Copilot panel — dark premium glass, slides in from the right */}
      <div
        className={cn(
          "fixed inset-y-0 end-0 z-50 flex flex-col",
          "w-full sm:w-[420px]",
          "bg-[#0b1220]/95 dark:bg-[#080e1c]/95 backdrop-blur-2xl",
          "border-s border-white/10",
          "shadow-[0_0_0_1px_rgba(255,255,255,0.04)_inset,-24px_0_60px_-20px_rgba(0,0,0,0.6)]",
          "transition-transform duration-300 ease-out",
          isOpen ? "translate-x-0" : "translate-x-full"
        )}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="AMAD AI Copilot"
      >
        {/* ── Header ─────────────────────────────────────────────────── */}
        <div className="shrink-0 border-b border-white/10 px-5 py-4 flex items-center justify-between gap-2">
          <div className="flex items-center gap-3 min-w-0">
            <IconChip icon={Sparkles} className="h-10 w-10 rounded-xl" />
            <div className="min-w-0">
              <h2 className="text-sm font-bold text-white truncate">{t("AMAD AI Copilot")}</h2>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-60" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
                </span>
                <span className="text-[11px] font-medium text-emerald-400/90">{t("Online")}</span>
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={startNewChat}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-white/70 hover:text-white hover:bg-white/10 transition-colors"
              aria-label={t("New chat")}
              title={t("New chat")}
            >
              <Plus className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{t("New chat")}</span>
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg text-white/50 hover:text-white hover:bg-white/10 transition-colors"
              aria-label={t("Close")}
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* ── Conversation area ─────────────────────────────────────── */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-6 space-y-5">
          {messages.length === 0 ? (
            <div className="space-y-6">
              <div className="space-y-2">
                <IconChip icon={Sparkles} className="h-11 w-11 rounded-2xl" />
                <h3 className="text-lg font-semibold text-white mt-3">{t("Welcome to AMAD AI")}</h3>
                <p className="text-sm text-white/60 leading-relaxed">
                  {t(
                    "I can help you understand projects, risks, procurement, safety, reports and portfolio performance."
                  )}
                </p>
              </div>

              <div className="grid grid-cols-1 gap-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => handleChipClick(s)}
                    className="text-start rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-white/80 hover:bg-white/[0.07] hover:border-white/20 transition-colors"
                  >
                    {t(s)}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              <button
                onClick={startNewChat}
                className="flex items-center gap-1.5 text-xs font-medium text-white/50 hover:text-white transition-colors"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                {t("Back to home")}
              </button>

              {messages.map((m) => {
                if (m.role === "user") {
                  return (
                    <div key={m.id} className="flex flex-col items-end animate-in fade-in-0 slide-in-from-bottom-1 duration-300">
                      <div
                        className="max-w-[85%] rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm text-[#1a1400] shadow-sm"
                        style={{ backgroundColor: "#eab308" }}
                      >
                        {m.text}
                      </div>
                      <span className="text-[10px] text-white/30 mt-1 me-1">{formatTime(m.createdAt)}</span>
                    </div>
                  );
                }

                if (m.role === "assistant-insight" && m.insightType) {
                  return (
                    <div key={m.id} className="flex items-end gap-2 animate-in fade-in-0 slide-in-from-bottom-1 duration-300">
                      <IconChip icon={Sparkles} />
                      <div className="flex flex-col items-start min-w-0">
                        {dataLoading ? (
                          showDataTimeoutMessage ? (
                            <div className="max-w-[92%] rounded-2xl rounded-bl-sm border border-amber-500/20 bg-amber-500/[0.08] px-4 py-3">
                              <p className="text-sm text-amber-200/90 leading-relaxed">
                                {t("Live AMAD data is taking longer than expected. Please try again.")}
                              </p>
                            </div>
                          ) : (
                            <div className="rounded-2xl rounded-bl-sm border border-white/10 bg-white/[0.06] px-4 py-3">
                              <p className="text-sm text-white/60">{t("Loading live portfolio data…")}</p>
                            </div>
                          )
                        ) : (
                          <InsightContent
                            insightType={m.insightType}
                            execData={execData}
                            execIsError={execIsError}
                            summaryData={summaryData}
                            summaryIsError={summaryIsError}
                          />
                        )}
                        <span className="text-[10px] text-white/30 mt-1 ms-1">{formatTime(m.createdAt)}</span>
                      </div>
                    </div>
                  );
                }

                // assistant-guide — immediate, honest guided reply.
                // Never a loading state: this is static text, shown the
                // instant the message is created.
                return (
                  <div key={m.id} className="flex items-end gap-2 animate-in fade-in-0 slide-in-from-bottom-1 duration-300">
                    <IconChip icon={Sparkles} />
                    <div className="flex flex-col items-start min-w-0">
                      <div className="max-w-[85%] rounded-2xl rounded-bl-sm border border-white/10 bg-white/[0.06] px-4 py-2.5">
                        <p className="text-sm text-white/80 leading-relaxed">{m.text}</p>
                      </div>
                      <span className="text-[10px] text-white/30 mt-1 ms-1">{formatTime(m.createdAt)}</span>
                    </div>
                  </div>
                );
              })}
            </>
          )}
        </div>

        {/* ── Bottom composer ───────────────────────────────────────── */}
        <div className="shrink-0 border-t border-white/10 p-4">
          <div className="flex items-end gap-2 rounded-2xl border border-white/10 bg-white/[0.04] px-3 py-2 focus-within:border-white/25 transition-colors">
            <button
              type="button"
              disabled
              aria-label={t("Attach file (coming soon)")}
              className="shrink-0 p-2 rounded-lg text-white/25 cursor-not-allowed"
            >
              <Paperclip className="w-4 h-4" />
            </button>

            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t("Ask AMAD AI anything…")}
              rows={1}
              className="flex-1 resize-none bg-transparent text-sm text-white placeholder:text-white/35 focus:outline-none py-1.5 max-h-24"
            />

            <button
              type="button"
              disabled
              aria-label={t("Voice input (coming soon)")}
              className="shrink-0 p-2 rounded-lg text-white/25 cursor-not-allowed"
            >
              <Mic className="w-4 h-4" />
            </button>

            <button
              type="button"
              onClick={() => sendGuidedReply(input)}
              disabled={!input.trim()}
              aria-label={t("Send")}
              className={cn(
                "shrink-0 flex h-8 w-8 items-center justify-center rounded-xl transition-all",
                input.trim() ? "hover:opacity-90" : "opacity-30 cursor-not-allowed"
              )}
              style={{ backgroundColor: "#eab308", color: "#1a1400" }}
            >
              <Send className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
