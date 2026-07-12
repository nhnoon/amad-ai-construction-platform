import { useEffect, useRef, useState } from "react";
import { useLocation, Link } from "wouter";
import {
  X, Sparkles, Send, Paperclip, Mic, Plus, ArrowLeft, RefreshCw,
  AlertTriangle, Target, Gauge, Activity, Building2, Clock, Package, FileText, ShieldAlert,
  PauseCircle, CheckCircle2, ThumbsUp, XCircle, DollarSign, Calendar, BarChart3,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import {
  useGetDashboardSummary,
  useListProjects,
  useListProjectHealthScores,
  useListProjectMeetings,
  useListPurchaseRequests,
  useListPurchaseOrders,
  useListProjectSafetyEvents,
  useListProjectSiteReports,
  getListProjectsQueryKey,
  getListProjectHealthScoresQueryKey,
  getListProjectMeetingsQueryKey,
  getListPurchaseRequestsQueryKey,
  getListPurchaseOrdersQueryKey,
  getListProjectSafetyEventsQueryKey,
  getListProjectSiteReportsQueryKey,
} from "@workspace/api-client-react";
import { cn } from "@/lib/utils";
import { useExecutive, type ExecutiveIntelligence } from "../lib/useExecutive";
import { useExecutiveWeeklyReport } from "../lib/useReports";
import { detectIntent, findProjectMatch } from "../lib/copilotIntent";
import { postCopilotQuery, postProcurementAgent, postMeetingAgent, CopilotApiError, isArabicText, type CopilotQueryResponse, type CopilotRenderBlock } from "../lib/copilotClient";
import {
  useCopilotClaims,
  useCopilotChangeOrders,
  useCopilotDocuments,
  useCopilotCorrespondence,
  useCopilotSiteReportAnalysis,
  useCopilotPortfolioClaims,
  isRfiLike,
  type ClaimRecord,
  type ChangeOrderRecord,
  type DocumentRecord,
  type CorrespondenceRecord,
} from "../lib/copilotData";
import {
  resolvePageContext,
  isPageAwareQuery,
  CONTEXT_LABEL,
  INSUFFICIENT_DATA_REPLY,
  type PageContext,
} from "../lib/copilotContext";

// ── AMAD AI Copilot — Executive Analyst reasoning layer ─────────────────────
// No AI provider, no backend changes, no new endpoints. A deterministic
// Intent Engine (lib/copilotIntent.ts) resolves fixed-topic questions; a
// second deterministic layer (lib/copilotContext.ts) resolves page-aware
// questions against the current wouter route. This file turns the fetched
// values into an executive read: rank what matters, drop what doesn't, and
// always close with the "so what" — never a raw metric dump.
//
// The "streaming" effect below is purely a client-side reveal animation over
// text that is already fully loaded — it does not simulate typing an
// in-progress response, and it always finishes within ~2s (bounded).

type ChatRole = "user" | "assistant-guide" | "assistant-insight" | "assistant-record" | "assistant-context" | "assistant-ai";

type InsightType =
  | "portfolio-summary"
  | "critical-projects"
  | "delayed-projects"
  | "project-health"
  | "procurement-risks"
  | "safety-overview"
  | "project-status";

type RecordKind = "meetings" | "claims" | "change-orders" | "rfis" | "documents";

interface CopilotMessage {
  id: string;
  role: ChatRole;
  text?: string; // user text, or the assistant-guide reply
  insightType?: InsightType; // for assistant-insight
  targetProjectId?: number; // for assistant-insight "project-status"
  recordKind?: RecordKind; // for assistant-record
  projectId?: number; // for assistant-record
  projectLabel?: string; // for assistant-record
  pageContext?: PageContext; // for assistant-context — frozen at creation time
  aiQuestion?: string; // for assistant-ai — original question, needed for Retry
  agentKind?: "procurement" | "meeting"; // for assistant-ai — set when this came from a dedicated agent endpoint, not the free-text pipeline; tells Retry which agent endpoint to call
  aiResponse?: CopilotQueryResponse; // for assistant-ai — set once the real pipeline answers
  aiError?: string; // for assistant-ai — set if the real pipeline call failed
  isFallback?: boolean; // marks a deterministic message shown because the AI call failed
  createdAt: number;
}

const SUGGESTIONS = ["Show critical projects", "Portfolio summary", "Procurement risks", "Safety overview"];
const PAGE_AWARE_CHIP = "Summarize this page";

const UNAVAILABLE = "Unavailable from current database."; // per-field fallback (metrics grid)
const NO_LIVE_DATA = "Live data for this analysis is currently unavailable."; // whole-analysis fallback
const DATA_TIMEOUT_MS = 3000;
const CLAIMS_AGGREGATE_TIMEOUT_MS = 10000; // fans out one request per project — needs more bounded time than a single fetch
const COPILOT_TIMEOUT_MS = 50000; // real LLM/network round-trip needs more headroom than the deterministic paths, but is still strictly bounded — widened further after observing ~25s live response times when the panel's background data hooks are still in flight

const CONFIDENCE_LABEL_AR: Record<string, string> = { none: "لا توجد", low: "منخفضة", medium: "متوسطة", high: "عالية" };

const RECORD_KIND_BY_INTENT: Partial<Record<string, RecordKind>> = {
  "upcoming-meetings": "meetings",
  "open-claims": "claims",
  rfis: "rfis",
  "change-orders": "change-orders",
  documents: "documents",
};

const RECORD_TOPIC_LABEL: Record<RecordKind, string> = {
  meetings: "meetings",
  claims: "claims",
  "change-orders": "change orders",
  rfis: "RFIs",
  documents: "documents",
};

function fieldText(value: number | string | undefined | null): string {
  return value === undefined || value === null || value === "" ? UNAVAILABLE : String(value);
}

function plural(n: number | undefined, word: string): string {
  return n === 1 ? word : `${word}s`;
}

function isAre(n: number | undefined): string {
  return n === 1 ? "is" : "are";
}

function capitalize(s: string): string {
  return s.length ? s[0].toUpperCase() + s.slice(1) : s;
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function pct(n: number | undefined, total: number | undefined): number | undefined {
  if (n == null || !total) return undefined;
  return Math.round((n / total) * 100);
}

// Keeps only the findings worth a reader's attention (max 3) — this is the
// "ignore insignificant information" step of the reasoning pipeline.
function significantFindings(...candidates: (string | null | undefined | false)[]): string[] {
  return candidates.filter((c): c is string => !!c).slice(0, 3);
}

function findingsOrFallback(...candidates: (string | null | undefined | false)[]): string[] {
  const found = significantFindings(...candidates);
  return found.length ? found : ["No material findings beyond standard performance indicators."];
}

function severityTier(severity: string | undefined): "high" | "medium" | "low" {
  if (severity === "critical" || severity === "high") return "high";
  if (severity === "medium") return "medium";
  return "low";
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

// What a given risk category typically means for the business — used to
// answer "so what" without inventing project-specific facts.
const BUSINESS_IMPACT_MAP: Record<string, string> = {
  procurement: "Continued procurement delays increase the risk of schedule slippage and cost escalation from expedited sourcing or alternate suppliers.",
  safety: "Unresolved high-severity safety events carry regulatory, legal, and reputational exposure, and may trigger corrective-action mandates.",
  quality: "Open non-conformances typically drive rework costs and can cascade into schedule delays if not closed before dependent activities begin.",
  schedule: "Extended delays commonly translate into liquidated-damages exposure, client dissatisfaction, and compounding procurement and labor costs.",
  health: "A concentration of critical and at-risk projects strains executive attention and increases the likelihood of missed portfolio-level commitments.",
};

const PENALTY_LABEL: Record<string, string> = {
  schedule: "schedule delays",
  safety: "safety incidents",
  quality: "quality non-conformances",
  procurement: "procurement delays",
};
const PENALTY_LABEL_AR: Record<string, string> = {
  schedule: "تأخيرات الجدول الزمني",
  safety: "حوادث السلامة",
  quality: "حالات عدم مطابقة الجودة",
  procurement: "تأخيرات المشتريات",
};

type DashboardSummaryData = {
  delayed_projects?: number;
  on_hold_projects?: number;
  late_purchase_orders?: number;
  open_purchase_requests?: number;
  total_purchase_orders?: number;
  total_purchase_requests?: number;
  high_severity_events?: number;
  total_safety_events?: number;
  open_ncrs?: number;
  total_ncrs?: number;
  total_meetings?: number;
  total_decisions?: number;
  total_site_reports?: number;
};

type ProjectRecord = {
  id: number;
  project_code: string;
  project_name: string;
  status: string;
  city?: string;
  planned_finish?: string;
  budget?: number;
};

type HealthScoreRecord = {
  project_id: number;
  project_code: string;
  project_name: string;
  status: string;
  score: number;
  level: string;
  reasons: string[];
  schedule_penalty: number;
  safety_penalty: number;
  ncr_penalty: number;
  procurement_penalty: number;
  risk_penalty: number;
};

type MeetingRecord = {
  id: number;
  project_id: number;
  meeting_date: string;
  title: string;
  meeting_type: string;
};

type PurchaseRequestRecord = { id: number; project_id: number; status: string };
type PurchaseOrderRecord = { id: number; project_id: number; status: string; is_late: boolean };
type SafetyEventRecord = { id: number; project_id: number; severity: string };
type SiteReportRecord = { id: number; project_id: number; report_date: string };

function findRisk(execData: ExecutiveIntelligence | undefined, category: string) {
  return execData?.biggest_risks?.find((r) => r.category === category);
}

interface InsightContext {
  execData?: ExecutiveIntelligence;
  execIsError: boolean;
  summaryData?: DashboardSummaryData;
  summaryIsError: boolean;
  projectsData?: ProjectRecord[];
  projectsIsError: boolean;
  targetProject?: ProjectRecord;
  targetHealthScore?: HealthScoreRecord;
}

// Executive Summary / Key Findings / Primary Risks / Business Impact /
// Executive Recommendation — the fixed shape every analytical response uses.
interface InsightView {
  title: string;
  executiveSummary: string;
  keyFindings: string[];
  primaryRisks: string;
  businessImpact: string;
  recommendedAction: string;
  metrics: { icon: React.ElementType; label: string; value: string }[];
}

const NO_DATA_VIEW = (title: string): InsightView => ({
  title,
  executiveSummary: NO_LIVE_DATA,
  keyFindings: [NO_LIVE_DATA],
  primaryRisks: NO_LIVE_DATA,
  businessImpact: NO_LIVE_DATA,
  recommendedAction: NO_LIVE_DATA,
  metrics: [],
});

// Builds the executive narrative for one insight type from the live query
// results already fetched for the panel — ranked, filtered, interpreted.
// No new data, no fabrication: every sentence traces back to a real field.
const SEVERITY_LABEL_AR: Record<string, string> = { critical: "حرجة", high: "عالية", medium: "متوسطة", low: "منخفضة" };
const HEALTH_LEVEL_LABEL_AR: Record<string, string> = { excellent: "ممتازة", good: "جيدة", "at risk": "في خطر", critical: "حرجة" };
const PROJECT_STATUS_LABEL_AR: Record<string, string> = {
  active: "نشط",
  delayed: "متأخر",
  completed: "مكتمل",
  suspended: "معلّق",
  planning: "قيد التخطيط",
  "on hold": "متوقف مؤقتاً",
};

function buildInsight(type: InsightType, ctx: InsightContext, isAr: boolean): InsightView {
  const { execData, execIsError, summaryData, summaryIsError, projectsData, projectsIsError } = ctx;

  if (type === "critical-projects") {
    if (execIsError) return NO_DATA_VIEW("Critical Projects Analysis");
    const risk = findRisk(execData, "health");
    const criticalCount = execData?.critical_count ?? 0;
    const atRiskCount = execData?.at_risk_count ?? 0;
    const total = execData?.total_projects;
    const topCritical = (execData?.attention_required ?? []).slice(0, 3);
    const worst = topCritical[0];
    const criticalPct = pct(criticalCount, total);

    return {
      title: isAr ? "تحليل المشاريع الحرجة" : "Critical Projects Analysis",
      executiveSummary: isAr
        ? criticalCount > 0
          ? `من أصل ${fieldText(total)} مشروعاً في المحفظة، هناك ${criticalCount} مشروعاً${criticalPct != null ? ` (${criticalPct}%)` : ""} في حالة صحية حرجة حالياً.${worst ? ` الحالة الأكثر إلحاحاً هي ${worst.project_code} — ${worst.project_name}.` : ""}`
          : "لا توجد مشاريع في حالة حرجة حالياً — تبقى أضعف المشاريع أداءً ضمن مستوى الخطر المتوسط فقط."
        : criticalCount > 0
          ? `${criticalCount} of ${fieldText(total)} projects${criticalPct != null ? ` (${criticalPct}%)` : ""} are in critical health condition.${worst ? ` The most severe case is ${worst.project_code} — ${worst.project_name}.` : ""}`
          : "No projects are currently in critical health condition — the portfolio's weakest performers remain at the at-risk tier.",
      keyFindings: findingsOrFallback(
        worst && `${worst.project_code}: ${worst.primary_reason}`,
        topCritical[1] && `${topCritical[1].project_code}: ${topCritical[1].primary_reason}`,
        atRiskCount > 0 &&
          (isAr
            ? `${atRiskCount} مشروعاً إضافياً معرض لخطر التصعيد إلى الحالة الحرجة`
            : `${atRiskCount} additional ${plural(atRiskCount, "project")} at risk of escalating to critical`)
      ),
      primaryRisks: risk ? `${capitalize(risk.detail)}.` : "No dominant risk category identified.",
      businessImpact: BUSINESS_IMPACT_MAP.health,
      recommendedAction: criticalCount > 0 ? `${capitalize(RISK_ACTION_MAP.health)}.` : "Continue standard portfolio monitoring.",
      metrics: [
        { icon: AlertTriangle, label: "Critical", value: String(criticalCount) },
        { icon: Activity, label: "At Risk", value: String(atRiskCount) },
        { icon: Building2, label: "Total Projects", value: fieldText(total) },
        { icon: Gauge, label: "Portfolio Score", value: fieldText(execData?.portfolio_score) },
        { icon: Activity, label: "Status", value: fieldText(execData?.portfolio_status) },
      ],
    };
  }

  if (type === "delayed-projects") {
    if (summaryIsError) return NO_DATA_VIEW(isAr ? "تحليل المشاريع المتأخرة" : "Delayed Projects Analysis");
    const risk = findRisk(execData, "schedule");
    const delayedCount = summaryData?.delayed_projects ?? 0;
    const onHold = summaryData?.on_hold_projects ?? 0;
    const total = execData?.total_projects;
    const delayedList = (projectsData ?? []).filter((p) => p.status === "Delayed").slice(0, 3);
    const delayedPct = pct(delayedCount, total);

    return {
      title: isAr ? "تحليل المشاريع المتأخرة" : "Delayed Projects Analysis",
      executiveSummary: isAr
        ? delayedCount > 0
          ? `تشير بيانات AMAD الحالية إلى أن ${delayedCount} من أصل ${fieldText(total)} مشروعاً${delayedPct != null ? ` (${delayedPct}%)` : ""} متأخرة حالياً.${delayedList[0] ? ` ويُعد مشروع ${delayedList[0].project_code} — ${delayedList[0].project_name} من أكثر المشاريع تأثراً.` : ""}`
          : "لا توجد مشاريع متأخرة حالياً — أداء الجدول الزمني عبر المحفظة مستقر."
        : delayedCount > 0
          ? `${delayedCount} of ${fieldText(total)} projects${delayedPct != null ? ` (${delayedPct}%)` : ""} are currently delayed.${delayedList[0] ? ` ${delayedList[0].project_code} — ${delayedList[0].project_name} is among the most affected.` : ""}`
          : "No projects are currently delayed — schedule performance across the portfolio is stable.",
      keyFindings: projectsIsError
        ? [NO_LIVE_DATA]
        : findingsOrFallback(
            delayedList[1] && `${delayedList[1].project_code} — ${delayedList[1].project_name}`,
            delayedList[2] && `${delayedList[2].project_code} — ${delayedList[2].project_name}`,
            onHold > 0 && (isAr ? `${onHold} مشروعاً إضافياً متوقف مؤقتاً` : `${onHold} additional ${plural(onHold, "project")} on hold`)
          ),
      primaryRisks: risk ? `${capitalize(risk.detail)}.` : "No dominant schedule risk identified.",
      businessImpact: BUSINESS_IMPACT_MAP.schedule,
      recommendedAction: delayedCount > 0 ? `${capitalize(RISK_ACTION_MAP.schedule)}.` : "Continue standard schedule monitoring.",
      metrics: [
        { icon: Clock, label: "Delayed", value: String(delayedCount) },
        { icon: PauseCircle, label: "On Hold", value: String(onHold) },
        { icon: Building2, label: "Total Projects", value: fieldText(total) },
        { icon: Gauge, label: "Portfolio Score", value: fieldText(execData?.portfolio_score) },
        { icon: Activity, label: "Status", value: fieldText(execData?.portfolio_status) },
      ],
    };
  }

  if (type === "project-health") {
    if (execIsError) return NO_DATA_VIEW(isAr ? "توزيع صحة المشاريع" : "Project Health Breakdown");
    const excellent = execData?.excellent_count ?? 0;
    const good = execData?.good_count ?? 0;
    const atRisk = execData?.at_risk_count ?? 0;
    const critical = execData?.critical_count ?? 0;
    const risk = findRisk(execData, "health");
    const negative = atRisk + critical;
    const positive = excellent + good;

    return {
      title: isAr ? "توزيع صحة المشاريع" : "Project Health Breakdown",
      executiveSummary: isAr
        ? negative > positive
          ? `تُظهر بيانات المحفظة الحالية ميلاً سلبياً في توزيع الصحة — إذ يُظهر ${negative} من أصل ${fieldText(execData?.total_projects)} مشروعاً مؤشرات مخاطر مرتفعة.`
          : critical > 0
            ? `المحفظة في حالة جيدة إجمالاً، مع وجود ${critical} مشروعاً يتطلب تدخلاً مركزاً.`
            : "المحفظة في حالة صحية قوية، ولا توجد مشاريع مصنّفة حالياً كحرجة."
        : negative > positive
          ? `The portfolio's health distribution skews negative — ${negative} of ${fieldText(execData?.total_projects)} projects show elevated risk indicators.`
          : critical > 0
            ? `The portfolio is largely healthy, with ${critical} ${plural(critical, "project")} requiring focused intervention.`
            : "The portfolio is in strong health, with no projects currently flagged as critical.",
      keyFindings: isAr
        ? findingsOrFallback(
            critical > 0 && `${critical} مشروعاً حرجاً`,
            atRisk > 0 && `${atRisk} مشروعاً في دائرة الخطر`,
            negative === 0 && `${positive} مشروعاً بتصنيف جيد أو ممتاز`
          )
        : findingsOrFallback(
            critical > 0 && `${critical} ${plural(critical, "project")} critical`,
            atRisk > 0 && `${atRisk} ${plural(atRisk, "project")} at risk`,
            negative === 0 && `${positive} ${plural(positive, "project")} rated good or excellent`
          ),
      primaryRisks: risk ? `${capitalize(risk.detail)}.` : "No dominant risk category identified.",
      businessImpact: BUSINESS_IMPACT_MAP.health,
      recommendedAction: critical > 0 ? `${capitalize(RISK_ACTION_MAP.health)}.` : "Continue standard portfolio monitoring.",
      metrics: [
        { icon: CheckCircle2, label: "Excellent", value: String(excellent) },
        { icon: ThumbsUp, label: "Good", value: String(good) },
        { icon: AlertTriangle, label: "At Risk", value: String(atRisk) },
        { icon: XCircle, label: "Critical", value: String(critical) },
        { icon: Gauge, label: "Portfolio Score", value: fieldText(execData?.portfolio_score) },
      ],
    };
  }

  if (type === "procurement-risks") {
    if (summaryIsError) return NO_DATA_VIEW("Procurement Risk Analysis");
    const risk = findRisk(execData, "procurement");
    const tier = severityTier(risk?.severity);
    const late = summaryData?.late_purchase_orders;
    const totalPOs = summaryData?.total_purchase_orders;
    const openPRs = summaryData?.open_purchase_requests ?? 0;
    const totalPRs = summaryData?.total_purchase_requests;

    return {
      title: isAr ? "تحليل مخاطر المشتريات" : "Procurement Risk Analysis",
      executiveSummary: isAr
        ? tier === "high"
          ? `تُعد المشتريات أبرز المخاطر التشغيلية في المحفظة حالياً؛ إذ يوجد ${fieldText(late)} من أصل ${fieldText(totalPOs)} أمر شراء متأخر، ما يهدد مباشرة جداول التسليم في المشاريع المتأثرة.`
          : tier === "medium"
            ? `تُظهر بيانات المشتريات مخاطر ناشئة — ${fieldText(late)} من أصل ${fieldText(totalPOs)} أمر شراء متأخر حالياً.`
            : `أداء المشتريات ضمن النطاق التشغيلي الطبيعي، حيث يوجد ${fieldText(late)} من أصل ${fieldText(totalPOs)} أمر شراء متأخر.`
        : tier === "high"
          ? `Procurement is the leading operational risk in the portfolio. ${fieldText(late)} of ${fieldText(totalPOs)} purchase orders are late, directly threatening delivery schedules on affected projects.`
          : tier === "medium"
            ? `Procurement shows emerging risk — ${fieldText(late)} of ${fieldText(totalPOs)} purchase orders are currently late.`
            : `Procurement performance is within normal operating range, with ${fieldText(late)} of ${fieldText(totalPOs)} purchase orders late.`,
      keyFindings: findingsOrFallback(
        openPRs > 0 &&
          (isAr
            ? `${openPRs} من أصل ${fieldText(totalPRs)} طلب شراء لا يزال مفتوحاً أو قيد المراجعة`
            : `${openPRs} of ${fieldText(totalPRs)} purchase requests remain open or pending review`),
        risk &&
          (isAr
            ? `تُصنَّف حدة مخاطر المشتريات بأنها ${SEVERITY_LABEL_AR[risk.severity] ?? risk.severity}`
            : `Procurement risk severity rated ${capitalize(risk.severity)}`)
      ),
      primaryRisks: risk ? `${capitalize(risk.detail)}.` : "No dominant procurement risk identified.",
      businessImpact: BUSINESS_IMPACT_MAP.procurement,
      recommendedAction:
        tier === "high"
          ? `${capitalize(RISK_ACTION_MAP.procurement)}.`
          : tier === "medium"
            ? "Monitor late purchase orders closely and escalate if the trend continues."
            : "Continue routine procurement monitoring; no escalation required.",
      metrics: [
        { icon: Package, label: "Late POs", value: fieldText(late) },
        { icon: FileText, label: "Open PRs", value: String(openPRs) },
        { icon: Package, label: "Total POs", value: fieldText(totalPOs) },
        { icon: FileText, label: "Total PRs", value: fieldText(totalPRs) },
        { icon: AlertTriangle, label: "Severity", value: risk ? capitalize(risk.severity) : UNAVAILABLE },
      ],
    };
  }

  if (type === "safety-overview") {
    if (summaryIsError) return NO_DATA_VIEW("Safety & Risk Overview");
    const risk = findRisk(execData, "safety");
    const tier = severityTier(risk?.severity);
    const highSev = summaryData?.high_severity_events;
    const totalEvents = summaryData?.total_safety_events;
    const openNCRs = summaryData?.open_ncrs ?? 0;
    const totalNCRs = summaryData?.total_ncrs;

    return {
      title: isAr ? "نظرة عامة على السلامة والمخاطر" : "Safety & Risk Overview",
      executiveSummary: isAr
        ? tier === "high"
          ? `تُعد السلامة أكثر المخاطر إلحاحاً في المحفظة حالياً؛ إذ تم تسجيل ${fieldText(highSev)} حدثاً عالي أو حرج الخطورة، ما يشير إلى تعرض غير معالَج عبر المواقع النشطة.`
          : tier === "medium"
            ? `تُظهر بيانات السلامة مخاطر متوسطة — ${fieldText(highSev)} حدثاً عالي/حرج الخطورة مسجلاً.`
            : `أداء السلامة مستقر، بواقع ${fieldText(highSev)} حدثاً عالي/حرج الخطورة من أصل ${fieldText(totalEvents)} حدثاً إجمالياً.`
        : tier === "high"
          ? `Safety is the most pressing risk in the portfolio. ${fieldText(highSev)} high or critical severity events have been recorded, indicating unresolved exposure across active sites.`
          : tier === "medium"
            ? `Safety shows moderate risk — ${fieldText(highSev)} high/critical severity events on record.`
            : `Safety performance is stable, with ${fieldText(highSev)} high/critical severity events out of ${fieldText(totalEvents)} total.`,
      keyFindings: findingsOrFallback(
        openNCRs > 0 &&
          (isAr
            ? `${openNCRs} من أصل ${fieldText(totalNCRs)} تقرير عدم مطابقة لا يزال مفتوحاً`
            : `${openNCRs} of ${fieldText(totalNCRs)} non-conformance reports remain open`),
        risk &&
          (isAr
            ? `تُصنَّف حدة مخاطر السلامة بأنها ${SEVERITY_LABEL_AR[risk.severity] ?? risk.severity}`
            : `Safety risk severity rated ${capitalize(risk.severity)}`)
      ),
      primaryRisks: risk ? `${capitalize(risk.detail)}.` : "No dominant safety risk identified.",
      businessImpact: BUSINESS_IMPACT_MAP.safety,
      recommendedAction:
        tier === "high"
          ? `${capitalize(RISK_ACTION_MAP.safety)}.`
          : tier === "medium"
            ? "Monitor open safety events closely and verify corrective actions are on track."
            : "Continue routine safety monitoring; no escalation required.",
      metrics: [
        { icon: ShieldAlert, label: "High Severity", value: fieldText(highSev) },
        { icon: Activity, label: "Total Events", value: fieldText(totalEvents) },
        { icon: AlertTriangle, label: "Open NCRs", value: String(openNCRs) },
        { icon: FileText, label: "Total NCRs", value: fieldText(totalNCRs) },
        { icon: AlertTriangle, label: "Severity", value: risk ? capitalize(risk.severity) : UNAVAILABLE },
      ],
    };
  }

  if (type === "project-status") {
    const project = ctx.targetProject;
    const hs = ctx.targetHealthScore;
    if (!project) return NO_DATA_VIEW(isAr ? "حالة المشروع" : "Project Status");

    const penalties = hs
      ? [
          { key: "schedule", value: hs.schedule_penalty },
          { key: "safety", value: hs.safety_penalty },
          { key: "quality", value: hs.ncr_penalty },
          { key: "procurement", value: hs.procurement_penalty },
        ]
      : [];
    const topPenalty = penalties.length ? penalties.reduce((a, b) => (b.value > a.value ? b : a)) : undefined;
    const hasRisk = !!hs && (hs.level === "Critical" || hs.level === "At Risk");
    const statusAr = PROJECT_STATUS_LABEL_AR[project.status?.toLowerCase() ?? ""] ?? project.status;
    const levelAr = hs ? (HEALTH_LEVEL_LABEL_AR[hs.level.toLowerCase()] ?? hs.level) : undefined;

    return {
      title: isAr ? `حالة المشروع — ${project.project_code}` : `Project Status — ${project.project_code}`,
      executiveSummary: isAr
        ? !hs
          ? `${project.project_code} — ${project.project_name} حالته الحالية "${fieldText(statusAr)}". بيانات الصحة غير متوفرة حالياً.`
          : `${project.project_code} — ${project.project_name} حالته "${fieldText(statusAr)}" وتصنيفه الصحي "${levelAr}" (${hs.score}/100).${hasRisk ? " يتطلب هذا المشروع اهتماماً تنفيذياً." : ""}`
        : !hs
          ? `${project.project_code} — ${project.project_name} is currently ${fieldText(project.status)}. Health data is currently unavailable.`
          : `${project.project_code} — ${project.project_name} is ${fieldText(project.status)} and rated ${hs.level.toLowerCase()} (${hs.score}/100).${hasRisk ? " This project requires executive attention." : ""}`,
      keyFindings: isAr
        ? findingsOrFallback(
            project.city && `الموقع: ${project.city}`,
            project.planned_finish && `تاريخ الإنجاز المخطط: ${project.planned_finish}`,
            project.budget != null && `الميزانية: ${project.budget.toLocaleString()}`
          )
        : findingsOrFallback(
            project.city && `Location: ${project.city}`,
            project.planned_finish && `Planned finish: ${project.planned_finish}`,
            project.budget != null && `Budget: ${project.budget.toLocaleString()}`
          ),
      primaryRisks: !hs
        ? NO_LIVE_DATA
        : hasRisk && hs.reasons?.[0]
          ? `${capitalize(hs.reasons[0])}.`
          : "No significant risk indicators identified for this project.",
      businessImpact: !hs
        ? NO_LIVE_DATA
        : hasRisk && topPenalty
          ? (BUSINESS_IMPACT_MAP[topPenalty.key] ?? "Continued underperformance may affect delivery timelines or cost.")
          : "No material business impact identified at this time.",
      recommendedAction: !hs
        ? NO_LIVE_DATA
        : hasRisk && topPenalty && topPenalty.value > 0
          ? `${capitalize(RISK_ACTION_MAP[topPenalty.key])}.`
          : "Continue standard monitoring; no immediate action required.",
      metrics: [
        { icon: Gauge, label: "Score", value: hs ? String(hs.score) : UNAVAILABLE },
        { icon: Activity, label: "Level", value: hs ? hs.level : UNAVAILABLE },
        { icon: Building2, label: "Status", value: fieldText(project.status) },
        { icon: DollarSign, label: "Budget", value: project.budget != null ? project.budget.toLocaleString() : UNAVAILABLE },
        { icon: Calendar, label: "Planned Finish", value: project.planned_finish ?? UNAVAILABLE },
      ],
    };
  }

  // portfolio-summary (default)
  if (execIsError) return NO_DATA_VIEW("Portfolio Executive Summary");
  const mainRisk = execData?.biggest_risks?.[0];
  const criticalCount = execData?.critical_count ?? 0;
  const delayedCount = summaryData?.delayed_projects;
  const total = execData?.total_projects;

  return {
    title: isAr ? "الملخص التنفيذي للمحفظة" : "Portfolio Executive Summary",
    executiveSummary: isAr
      ? criticalCount > 0
        ? `يبلغ متوسط درجة الصحة للمحفظة ${fieldText(execData?.portfolio_score)}/100 عبر ${fieldText(total)} مشروعاً. بصرف النظر عن الحجم، هناك ${criticalCount} مشروعاً في حالة حرجة تستوجب تدخلاً تنفيذياً مباشراً.`
        : `يبلغ متوسط درجة الصحة للمحفظة ${fieldText(execData?.portfolio_score)}/100 عبر ${fieldText(total)} مشروعاً، دون وجود مشاريع في حالة حرجة حالياً.`
      : criticalCount > 0
        ? `The portfolio is averaging a health score of ${fieldText(execData?.portfolio_score)}/100 across ${fieldText(total)} projects. Volume aside, ${criticalCount} ${plural(criticalCount, "project")} ${isAre(criticalCount)} in critical condition and require direct executive intervention.`
        : `The portfolio is averaging a health score of ${fieldText(execData?.portfolio_score)}/100 across ${fieldText(total)} projects, with no projects currently in critical condition.`,
    keyFindings: findingsOrFallback(
      mainRisk &&
        (isAr
          ? `أبرز فئة مخاطر: ${mainRisk.label} (${SEVERITY_LABEL_AR[mainRisk.severity] ?? mainRisk.severity})`
          : `Leading risk category: ${mainRisk.label} (${capitalize(mainRisk.severity)})`),
      !summaryIsError &&
        (delayedCount ?? 0) > 0 &&
        (isAr ? `${delayedCount} مشروعاً متأخراً عن الجدول الزمني` : `${delayedCount} ${plural(delayedCount, "project")} behind schedule`),
      execData?.attention_required?.[0] &&
        (isAr
          ? `الأكثر إلحاحاً: ${execData.attention_required[0].project_code} — ${execData.attention_required[0].primary_reason}`
          : `Most urgent: ${execData.attention_required[0].project_code} — ${execData.attention_required[0].primary_reason}`)
    ),
    primaryRisks: mainRisk ? `${capitalize(mainRisk.label)} is the greatest exposure — ${mainRisk.detail}.` : "No dominant risk category identified.",
    businessImpact: mainRisk
      ? (BUSINESS_IMPACT_MAP[mainRisk.category] ?? "Continued underperformance in this area may affect portfolio delivery commitments.")
      : NO_LIVE_DATA,
    recommendedAction: mainRisk
      ? `${capitalize(RISK_ACTION_MAP[mainRisk.category] ?? "review portfolio risk drivers and prioritize executive attention")}.`
      : "Continue standard portfolio monitoring.",
    metrics: [
      { icon: Gauge, label: "Portfolio Score", value: fieldText(execData?.portfolio_score) },
      { icon: Activity, label: "Status", value: fieldText(execData?.portfolio_status) },
      { icon: Building2, label: "Projects", value: fieldText(total) },
      { icon: AlertTriangle, label: "Critical", value: String(criticalCount) },
      { icon: Clock, label: "Delayed", value: summaryIsError ? UNAVAILABLE : fieldText(delayedCount) },
    ],
  };
}

// Financial-exposure / legal-risk read on a claims register — shared by the
// per-project chat lookup and the portfolio-wide "Claims" page context.
// `projectsData` is only needed to resolve project codes across a
// multi-project (portfolio) scope; omit it for a single-project scope.
function buildClaimsInsightView(
  rows: ClaimRecord[],
  scopeLabel: string,
  hasError: boolean,
  projectsData?: ProjectRecord[],
  isAr = false
): InsightView {
  if (hasError) return NO_DATA_VIEW("Claims Analysis");

  const totalAmount = rows.reduce((s, r) => s + r.amount, 0);
  const open = rows.filter((r) => r.status === "Open").length;
  const highest = [...rows].sort((a, b) => b.amount - a.amount)[0];
  const highestCode = highest && projectsData ? projectsData.find((p) => p.id === highest.project_id)?.project_code : undefined;

  const byProject = new Map<number, number>();
  rows.forEach((r) => byProject.set(r.project_id, (byProject.get(r.project_id) ?? 0) + 1));
  const distinctProjects = byProject.size;
  const topRepeat = distinctProjects > 1 ? [...byProject.entries()].sort((a, b) => b[1] - a[1])[0] : undefined;
  const repeatedProjectCode = topRepeat && topRepeat[1] >= 2 && projectsData ? projectsData.find((p) => p.id === topRepeat[0])?.project_code : undefined;

  const avgAmount = rows.length ? totalAmount / rows.length : 0;
  const isHighExposure = !!highest && highest.amount > avgAmount * 2;
  const scopeLabelAr = scopeLabel === "the portfolio" ? "المحفظة" : scopeLabel;

  return {
    title: isAr ? "تحليل المطالبات" : "Claims Analysis",
    executiveSummary: isAr
      ? rows.length === 0
        ? `لا توجد مطالبات مسجلة حالياً لـ ${scopeLabelAr}.`
        : `يبلغ إجمالي التعرض المالي للمطالبات في ${scopeLabelAr} ${totalAmount.toLocaleString()} عبر ${rows.length} مطالبة. ${isHighExposure ? "يتركز التعرض في عدد محدود من المطالبات عالية القيمة وليس موزعاً بالتساوي." : "التعرض موزع بشكل عام وليس مركّزاً."}`
      : rows.length === 0
        ? `No claims are currently on record for ${scopeLabel}.`
        : `${scopeLabel === "the portfolio" ? "The portfolio" : scopeLabel} carries ${totalAmount.toLocaleString()} in total claim exposure across ${rows.length} ${plural(rows.length, "claim")}. ${isHighExposure ? "Exposure is concentrated in a small number of high-value claims rather than spread evenly." : "Exposure is broadly distributed rather than concentrated."}`,
    keyFindings: findingsOrFallback(
      highest &&
        (isAr
          ? `أعلى تعرض: ${highest.claim_number}${highestCode ? ` (${highestCode})` : ""} — ${highest.claim_type}, ${highest.amount.toLocaleString()}`
          : `Highest exposure: ${highest.claim_number}${highestCode ? ` (${highestCode})` : ""} — ${highest.claim_type}, ${highest.amount.toLocaleString()}`),
      repeatedProjectCode &&
        (isAr
          ? `${repeatedProjectCode} لديه ${topRepeat![1]} مطالبات متكررة — نمط يستحق المتابعة`
          : `${repeatedProjectCode} has ${topRepeat![1]} recurring claims — a pattern worth investigating`),
      open > 0 && (isAr ? `${open} مطالبة لا تزال مفتوحة` : `${open} ${plural(open, "claim")} still open`)
    ),
    primaryRisks: highest
      ? `Financial exposure is led by ${highest.claim_type.toLowerCase()} claims${highestCode ? ` on ${highestCode}` : ""}, valued at ${highest.amount.toLocaleString()}.`
      : "No material claims exposure identified.",
    businessImpact: isHighExposure
      ? "Concentrated high-value claims carry meaningful legal and financial risk and may affect project margins or trigger dispute-resolution proceedings."
      : "Current claims exposure is distributed and does not indicate an emerging systemic issue.",
    recommendedAction:
      open > 0
        ? "Review open claims with legal and commercial teams, prioritizing the highest-value exposures."
        : "No open claims currently require action.",
    metrics: [
      { icon: FileText, label: "Total Claims", value: String(rows.length) },
      { icon: AlertTriangle, label: "Open", value: String(open) },
      { icon: DollarSign, label: "Total Value", value: totalAmount.toLocaleString() },
      { icon: Target, label: "Highest Claim", value: highest ? highest.amount.toLocaleString() : UNAVAILABLE },
    ],
  };
}

interface RecordView {
  title: string;
  overview: string;
  lines: string[];
}

function buildRecordView(
  kind: Exclude<RecordKind, "claims">,
  projectLabel: string,
  hasError: boolean,
  data: {
    meetings?: MeetingRecord[];
    changeOrders?: ChangeOrderRecord[];
    documents?: DocumentRecord[];
    correspondence?: CorrespondenceRecord[];
  }
): RecordView {
  if (kind === "meetings") {
    const todayStr = new Date().toISOString().slice(0, 10);
    const upcoming = (data.meetings ?? [])
      .filter((m) => m.meeting_date >= todayStr)
      .sort((a, b) => a.meeting_date.localeCompare(b.meeting_date))
      .slice(0, 5);
    return {
      title: `Upcoming Meetings — ${projectLabel}`,
      overview: hasError
        ? UNAVAILABLE
        : `${upcoming.length} upcoming ${plural(upcoming.length, "meeting")} scheduled for ${projectLabel}.`,
      lines: hasError
        ? [UNAVAILABLE]
        : upcoming.length
          ? upcoming.map((m) => `${m.title} — ${m.meeting_type}, ${m.meeting_date}`)
          : ["No upcoming meetings scheduled."],
    };
  }

  if (kind === "change-orders") {
    const rows = data.changeOrders ?? [];
    const totalValue = rows.reduce((sum, r) => sum + r.value, 0);
    const top = [...rows].sort((a, b) => b.value - a.value).slice(0, 5);
    return {
      title: `Change Orders — ${projectLabel}`,
      overview: hasError
        ? UNAVAILABLE
        : `${rows.length} change ${plural(rows.length, "order")} on record for ${projectLabel}, combined value ${totalValue.toLocaleString()}.`,
      lines: hasError
        ? [UNAVAILABLE]
        : top.length
          ? top.map((r) => `${r.co_number} — ${r.description} (${r.status}): ${r.value.toLocaleString()}`)
          : ["No change orders on record for this project."],
    };
  }

  if (kind === "rfis") {
    const docs = (data.documents ?? []).filter((d) => isRfiLike(d.doc_type) || isRfiLike(d.title));
    const corr = (data.correspondence ?? []).filter((c) => isRfiLike(c.related_record_type) || isRfiLike(c.subject));
    const merged = [
      ...docs.map((d) => ({ label: `${d.title} (Document)`, date: d.doc_date })),
      ...corr.map((c) => ({ label: `${c.subject} (Correspondence)`, date: c.sent_date })),
    ]
      .sort((a, b) => b.date.localeCompare(a.date))
      .slice(0, 5);
    return {
      title: `RFIs — ${projectLabel}`,
      overview: hasError
        ? UNAVAILABLE
        : `${docs.length} RFI-related document(s) and ${corr.length} RFI-related correspondence record(s) found for ${projectLabel}.`,
      lines: hasError
        ? [UNAVAILABLE]
        : merged.length
          ? merged.map((m) => `${m.label} — ${m.date}`)
          : ["No RFI-related records found for this project."],
    };
  }

  // documents
  const rows = [...(data.documents ?? [])].sort((a, b) => b.doc_date.localeCompare(a.doc_date)).slice(0, 5);
  return {
    title: `Documents — ${projectLabel}`,
    overview: hasError ? UNAVAILABLE : `${(data.documents ?? []).length} document(s) on record for ${projectLabel}.`,
    lines: hasError
      ? [UNAVAILABLE]
      : rows.length
        ? rows.map((d) => `${d.title} (${d.doc_type}) — ${d.doc_date}`)
        : ["No documents on record for this project."],
  };
}

// Starts (or clears) a bounded countdown whenever `isActive` is true — the
// "taking longer than expected" signal is honest and always fires within
// `ms`, never left hanging.
function useBoundedTimeout(isActive: boolean, ms: number): boolean {
  const [timedOut, setTimedOut] = useState(false);
  useEffect(() => {
    if (!isActive) {
      setTimedOut(false);
      return;
    }
    const t = window.setTimeout(() => setTimedOut(true), ms);
    return () => window.clearTimeout(t);
  }, [isActive, ms]);
  return timedOut;
}

// Reveals `totalSteps` sections one at a time over `stepDelayMs` apart —
// bounded (never infinite), (re)starts whenever `active` flips to true.
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

// `t()` on any string not in the dictionary returns it unchanged — so this
// is safe to call on metric values that are numbers, project codes, or
// dynamically-composed sentences (they simply pass through untranslated),
// while exact-match constants (statuses, "Unavailable...", etc.) do get
// translated.
function MetricMiniCard({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  const { t } = useTranslation();
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.04] p-3 transition-all duration-200 hover:border-white/20 hover:bg-white/[0.08] hover:-translate-y-0.5">
      <div className="flex items-center gap-2 mb-2">
        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md" style={{ backgroundColor: "#eab30817" }}>
          <Icon className="h-3.5 w-3.5" style={{ color: "#eab308" }} />
        </div>
        <span className="text-[9px] font-semibold uppercase tracking-wider text-white/40 truncate">{t(label)}</span>
      </div>
      <p className="text-lg font-bold text-white leading-none truncate">{t(value)}</p>
    </div>
  );
}

function LiveBadge() {
  const { t } = useTranslation();
  return (
    <div className="flex items-center gap-2 mb-2">
      <span
        className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider"
        style={{ backgroundColor: "#16a34a1A", color: "#16a34a" }}
      >
        <span className="h-1.5 w-1.5 rounded-full bg-current" />
        {t("Live AMAD Analysis")}
      </span>
    </div>
  );
}

// Shared premium 6-section card shell (Executive Summary / Key Findings /
// Primary Risks / Business Impact / Executive Recommendation / Metrics).
// Every text field is run through t() — dynamic, data-interpolated sentences
// pass through unchanged (no matching key), while fixed constants and
// section labels translate to Arabic when Arabic is the active language.
function InsightCard({ view, revealed }: { view: InsightView; revealed: number }) {
  const { t } = useTranslation();
  return (
    <div className="max-w-[92%] rounded-2xl rounded-bl-sm border border-white/10 bg-white/[0.06] px-4 py-4">
      <LiveBadge />
      <h3 className="text-base font-bold text-white mb-3">{view.title}</h3>

      <div className="space-y-4">
        {revealed >= 1 && (
          <div className="animate-in fade-in-0 slide-in-from-bottom-1 duration-300 space-y-1.5">
            <p className="text-[10px] font-bold uppercase tracking-wider text-white/40">{t("Executive Summary")}</p>
            <p className="text-sm text-white/85 leading-relaxed">{t(view.executiveSummary)}</p>
          </div>
        )}

        {revealed >= 2 && (
          <div className="animate-in fade-in-0 slide-in-from-bottom-1 duration-300 space-y-1.5">
            <p className="text-[10px] font-bold uppercase tracking-wider text-white/40">{t("Key Findings")}</p>
            <ul className="space-y-1 text-sm text-white/80">
              {view.keyFindings.map((f, i) => (
                <li key={i}>• {t(f)}</li>
              ))}
            </ul>
          </div>
        )}

        {revealed >= 3 && (
          <div className="animate-in fade-in-0 slide-in-from-bottom-1 duration-300">
            <p className="text-[10px] font-bold uppercase tracking-wider text-white/40 mb-1.5">{t("Primary Risks")}</p>
            <div className="flex gap-2.5 rounded-xl border-l-4 border-amber-500/60 bg-amber-500/[0.08] px-3.5 py-3">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-amber-400" />
              <p className="text-sm text-amber-100/90 leading-relaxed">{t(view.primaryRisks)}</p>
            </div>
          </div>
        )}

        {revealed >= 4 && (
          <div className="animate-in fade-in-0 slide-in-from-bottom-1 duration-300">
            <p className="text-[10px] font-bold uppercase tracking-wider text-white/40 mb-1.5">{t("Business Impact")}</p>
            <div className="flex gap-2.5 rounded-xl border border-white/10 bg-white/[0.03] px-3.5 py-3">
              <BarChart3 className="h-4 w-4 shrink-0 mt-0.5 text-white/50" />
              <p className="text-sm text-white/80 leading-relaxed">{t(view.businessImpact)}</p>
            </div>
          </div>
        )}

        {revealed >= 5 && (
          <div className="animate-in fade-in-0 slide-in-from-bottom-1 duration-300">
            <p className="text-[10px] font-bold uppercase tracking-wider text-white/40 mb-1.5">{t("Executive Recommendation")}</p>
            <div
              className="flex gap-2.5 rounded-xl border px-3.5 py-3"
              style={{ borderColor: "#eab30840", backgroundColor: "#eab30812" }}
            >
              <Target className="h-4 w-4 shrink-0 mt-0.5" style={{ color: "#eab308" }} />
              <p className="text-sm text-white/90 leading-relaxed">{t(view.recommendedAction)}</p>
            </div>
          </div>
        )}

        {revealed >= 6 && view.metrics.length > 0 && (
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

// Shared lightweight 2-section card shell (Overview + a plain records list)
// — used for the purely informational per-project lookups (meetings/change
// orders/RFIs/documents) that don't call for risk-analyst framing.
function RecordCard({ view, revealed }: { view: RecordView; revealed: number }) {
  const { t } = useTranslation();
  return (
    <div className="max-w-[92%] rounded-2xl rounded-bl-sm border border-white/10 bg-white/[0.06] px-4 py-4">
      <LiveBadge />
      <h3 className="text-base font-bold text-white mb-3">{view.title}</h3>
      <div className="space-y-4">
        {revealed >= 1 && (
          <div className="animate-in fade-in-0 slide-in-from-bottom-1 duration-300 space-y-1.5">
            <p className="text-[10px] font-bold uppercase tracking-wider text-white/40">{t("Overview")}</p>
            <p className="text-sm text-white/85 leading-relaxed">{t(view.overview)}</p>
          </div>
        )}
        {revealed >= 2 && (
          <div className="animate-in fade-in-0 slide-in-from-bottom-1 duration-300 space-y-1.5">
            <p className="text-[10px] font-bold uppercase tracking-wider text-white/40">{t("Records")}</p>
            <ul className="space-y-1 text-sm text-white/80">
              {view.lines.map((l, i) => (
                <li key={i}>• {t(l)}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function LoadingBubble({ topic, timedOut }: { topic: string; timedOut: boolean }) {
  const { t } = useTranslation();
  return timedOut ? (
    <div className="max-w-[92%] rounded-2xl rounded-bl-sm border border-amber-500/20 bg-amber-500/[0.08] px-4 py-3">
      <p className="text-sm text-amber-200/90 leading-relaxed">
        {t("Live AMAD data is taking longer than expected. Please try again.")}
      </p>
    </div>
  ) : (
    <div className="rounded-2xl rounded-bl-sm border border-white/10 bg-white/[0.06] px-4 py-3">
      <p className="text-sm text-white/60">{t("Loading live {{topic}} data…", { topic: t(topic) })}</p>
    </div>
  );
}

function FallbackLabel() {
  const { t } = useTranslation();
  return (
    <p className="text-[10px] font-medium text-amber-400/70 mb-1.5">
      {t("Deterministic data — AI is currently unavailable")}
    </p>
  );
}

function AiPendingBubble() {
  const { t } = useTranslation();
  return (
    <div className="rounded-2xl rounded-bl-sm border border-white/10 bg-white/[0.06] px-4 py-3">
      <p className="text-sm text-white/60">{t("Thinking…")}</p>
    </div>
  );
}

function AiErrorBubble({ message, onRetry }: { message: string; onRetry: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="max-w-[92%] rounded-2xl rounded-bl-sm border border-red-500/20 bg-red-500/[0.08] px-4 py-3 space-y-2">
      <p className="text-sm text-red-200/90 leading-relaxed">{t(message)}</p>
      <button
        onClick={onRetry}
        className="inline-flex items-center gap-1.5 rounded-lg border border-white/15 px-2.5 py-1 text-xs font-medium text-white/80 hover:bg-white/10 transition-colors"
      >
        <RefreshCw className="h-3 w-3" />
        {t("Retry")}
      </button>
    </div>
  );
}

function BlockLabel({ children }: { children: React.ReactNode }) {
  return <p className="text-[10px] font-bold uppercase tracking-wider text-white/40 mb-1.5">{children}</p>;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyBlock = Record<string, any>;

function ProjectMiniRow({ p }: { p: AnyBlock }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-semibold text-white truncate">
          {p.code} — {p.name}
        </span>
        {p.score != null && <span className="text-xs text-white/60 shrink-0">{p.score}/100</span>}
      </div>
      <p className="text-xs text-white/50 mt-0.5 truncate">{[p.status, p.city, p.budget_fmt].filter(Boolean).join(" · ")}</p>
    </div>
  );
}

// Renders one of the backend's typed render_blocks (project_card,
// project_list, comparison, safety_summary, ncr_summary, risk_summary,
// health_list, health_card) — real structured data straight from
// backend/app/ai/render_blocks.py, not re-derived or fabricated here.
function RenderBlockItem({ block, ar }: { block: CopilotRenderBlock; ar: boolean }) {
  const b = block as AnyBlock;

  if (b.type === "project_card") {
    return (
      <div>
        {b.highlight && <BlockLabel>{ar ? b.highlight.label_ar : b.highlight.label_en}</BlockLabel>}
        <ProjectMiniRow p={b.project} />
        {b.runner_up && (
          <p className="text-xs text-white/40 mt-1">
            {ar ? "الأقرب: " : "Runner-up: "}
            {b.runner_up.code} — {b.runner_up.name} ({b.runner_up.budget_fmt ?? "—"})
          </p>
        )}
      </div>
    );
  }

  if (b.type === "project_list") {
    return (
      <div className="space-y-2">
        <BlockLabel>
          {ar ? b.filter_label_ar : b.filter_label_en} · {b.total}
        </BlockLabel>
        <div className="space-y-1.5">
          {(b.projects ?? []).slice(0, 6).map((p: AnyBlock, i: number) => (
            <ProjectMiniRow key={i} p={p} />
          ))}
        </div>
      </div>
    );
  }

  if (b.type === "comparison") {
    const [pa, pb] = b.projects ?? [];
    return (
      <div className="space-y-2">
        <BlockLabel>{ar ? "مقارنة" : "Comparison"}</BlockLabel>
        <div className="rounded-lg border border-white/10 overflow-hidden overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-white/[0.04] text-white/50">
                <th className="text-start px-2 py-1.5 font-medium"> </th>
                <th className="text-start px-2 py-1.5 font-medium">{pa?.code}</th>
                <th className="text-start px-2 py-1.5 font-medium">{pb?.code}</th>
              </tr>
            </thead>
            <tbody>
              {(b.metrics ?? []).map((m: AnyBlock, i: number) => (
                <tr key={i} className="border-t border-white/10">
                  <td className="px-2 py-1.5 text-white/50 whitespace-nowrap">{ar ? m.label_ar : m.label_en}</td>
                  <td className={cn("px-2 py-1.5", m.winner === "a" ? "text-emerald-400 font-semibold" : "text-white/80")}>{m.a}</td>
                  <td className={cn("px-2 py-1.5", m.winner === "b" ? "text-emerald-400 font-semibold" : "text-white/80")}>{m.b}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (b.type === "safety_summary") {
    return (
      <div className="space-y-1.5">
        <BlockLabel>{ar ? "ملخص السلامة" : "Safety Summary"}</BlockLabel>
        <p className="text-sm text-white/80">
          {b.total} {ar ? "حدث" : "events"} — {b.high} {ar ? "عالية الخطورة" : "high severity"}
        </p>
        <ul className="space-y-1 text-sm text-white/70">
          {(b.notable ?? []).map((n: AnyBlock, i: number) => (
            <li key={i}>
              • {n.code}: {n.description} ({n.severity})
            </li>
          ))}
        </ul>
      </div>
    );
  }

  if (b.type === "ncr_summary") {
    return (
      <div className="space-y-1.5">
        <BlockLabel>{ar ? "ملخص عدم المطابقة" : "NCR Summary"}</BlockLabel>
        <p className="text-sm text-white/80">
          {b.total} {ar ? "إجمالي" : "total"} — {b.under_corrective_action} {ar ? "تحت الإجراء التصحيحي" : "under corrective action"}
        </p>
        <ul className="space-y-1 text-sm text-white/70">
          {(b.items ?? []).map((it: AnyBlock, i: number) => (
            <li key={i}>
              • {it.code}: {it.type} ({it.status})
            </li>
          ))}
        </ul>
      </div>
    );
  }

  if (b.type === "risk_summary") {
    return (
      <div className="space-y-3">
        {(b.categories ?? []).map((cat: AnyBlock, i: number) => (
          <div key={i} className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2.5">
            <p className="text-sm font-semibold text-white">
              {cat.emoji} {ar ? cat.title_ar : cat.title_en}
            </p>
            {(ar ? cat.subtitle_ar : cat.subtitle_en) && <p className="text-xs text-white/50 mb-1">{ar ? cat.subtitle_ar : cat.subtitle_en}</p>}
            <ul className="space-y-0.5 text-xs text-white/70">
              {(cat.items ?? []).map((it: AnyBlock, j: number) => (
                <li key={j}>• {it.text ?? it.code}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    );
  }

  if (b.type === "health_list") {
    return (
      <div className="space-y-1.5">
        {(b.items ?? []).slice(0, 6).map((it: AnyBlock, i: number) => (
          <div key={i} className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2">
            <div className="flex items-center justify-between gap-2">
              <Link href={it.href} className="text-sm font-semibold text-white hover:underline truncate">
                {it.code} — {it.name}
              </Link>
              <span className="text-xs text-white/60 shrink-0">
                {it.score}/100 ({it.level})
              </span>
            </div>
            {it.reasons?.[0] && <p className="text-xs text-white/50 mt-0.5">{it.reasons[0]}</p>}
          </div>
        ))}
      </div>
    );
  }

  if (b.type === "health_card") {
    return (
      <div className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2.5">
        <div className="flex items-center justify-between gap-2">
          <Link href={b.href} className="text-sm font-semibold text-white hover:underline truncate">
            {b.code} — {b.name}
          </Link>
          <span className="text-xs text-white/60 shrink-0">
            {b.score}/100 ({b.level})
          </span>
        </div>
        {b.reasons?.[0] && <p className="text-xs text-white/50 mt-1">{b.reasons[0]}</p>}
      </div>
    );
  }

  return null;
}

function RenderBlocks({ blocks, ar }: { blocks: CopilotRenderBlock[]; ar: boolean }) {
  const visible = blocks.filter((b) => (b as AnyBlock).type !== "citations");
  if (!visible.length) return null;
  return (
    <div className="space-y-3">
      {visible.map((b, i) => (
        <RenderBlockItem key={i} block={b} ar={ar} />
      ))}
    </div>
  );
}

// Real AI-pipeline answer — grounded in live retrieval, RBAC-scoped and
// citation-backed server-side (backend/app/ai/pipeline.py). Renders
// right-to-left automatically when the backend replied in Arabic.
//
// Language is detected from the ORIGINAL QUESTION first, not just the
// answer: answers that embed several English citation codes (correctly
// left untranslated — project codes, PO/SE/NCR numbers) can dilute the
// answer's own Arabic-character ratio below the detection threshold even
// though the question — and the intended reading direction — was Arabic.
function AiAnswerCard({
  response,
  question,
  onFollowUp,
}: {
  response: CopilotQueryResponse;
  question?: string;
  onFollowUp: (text: string) => void;
}) {
  const ar = isArabicText(question) || isArabicText(response.answer);
  return (
    <div className="max-w-[92%] rounded-2xl rounded-bl-sm border border-white/10 bg-white/[0.06] px-4 py-4">
      <div className="flex items-center justify-between mb-2 gap-2">
        <LiveBadge />
        <span className="text-[10px] font-medium text-white/40 uppercase tracking-wide shrink-0">
          {ar ? `الثقة: ${CONFIDENCE_LABEL_AR[response.confidence] ?? response.confidence}` : `Confidence: ${capitalize(response.confidence)}`}
        </span>
      </div>

      {response.clarification_required ? (
        <div className="space-y-2" dir={ar ? "rtl" : "ltr"}>
          <p className={cn("text-sm text-white/85 leading-relaxed", ar && "text-right")}>{response.clarification_question}</p>
          {!!response.clarification_options?.length && (
            <div className="flex flex-wrap gap-1.5">
              {response.clarification_options.map((opt) => (
                <button
                  key={opt}
                  onClick={() => onFollowUp(opt)}
                  className="rounded-lg border border-white/15 px-2.5 py-1 text-xs text-white/80 hover:bg-white/10 transition-colors"
                >
                  {opt}
                </button>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-3" dir={ar ? "rtl" : "ltr"}>
          <p className={cn("text-sm text-white/85 leading-relaxed", ar && "text-right")}>{response.answer}</p>

          {!!response.render_blocks?.length && <RenderBlocks blocks={response.render_blocks} ar={ar} />}

          {!!response.key_findings?.length && (
            <div className="space-y-1">
              <p className="text-[10px] font-bold uppercase tracking-wider text-white/40">{ar ? "أبرز النتائج" : "Key Findings"}</p>
              <ul className={cn("space-y-1 text-sm text-white/80", ar && "text-right")}>
                {response.key_findings.map((f, i) => (
                  <li key={i}>• {f}</li>
                ))}
              </ul>
            </div>
          )}

          {!!response.citations?.length && (
            <div className="space-y-1">
              <p className="text-[10px] font-bold uppercase tracking-wider text-white/40">{ar ? "المصادر" : "Sources"}</p>
              <ul className={cn("space-y-1 text-xs text-white/60", ar && "text-right")}>
                {response.citations.map((c) => {
                  const href = (c.ui_metadata as AnyBlock | undefined)?.href;
                  return (
                    <li key={c.id}>
                      •{" "}
                      {href ? (
                        <Link href={href} className="text-white/70 hover:underline">
                          {c.label}
                        </Link>
                      ) : (
                        c.label
                      )}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {!!response.follow_up_suggestions?.length && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {response.follow_up_suggestions.map((s) => (
                <button
                  key={s}
                  onClick={() => onFollowUp(s)}
                  className="rounded-lg border border-white/10 bg-white/[0.03] px-2.5 py-1 text-xs text-white/70 hover:bg-white/10 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Executive-formatted, streamed-in insight response for the fixed-topic
// Intent Engine. All values come straight from the props (the same live
// query results the Dashboard uses) — nothing here is fabricated.
function InsightContent({ insightType, ctx }: { insightType: InsightType; ctx: InsightContext }) {
  const { i18n } = useTranslation();
  const revealed = useProgressiveReveal(6, true, 320);
  const view = buildInsight(insightType, ctx, !!i18n.language?.startsWith("ar"));
  return <InsightCard view={view} revealed={revealed} />;
}

// Project-scoped record response. Each instance owns its own live query —
// mounted once per chat message — so multiple record questions never race
// each other's state. Claims gets the full executive-analyst treatment
// (financial exposure / legal risk); the rest stay purely informational.
function RecordInsightContent({
  recordKind,
  projectId,
  projectLabel,
}: {
  recordKind: RecordKind;
  projectId: number;
  projectLabel: string;
}) {
  const { i18n } = useTranslation();
  const isAr = !!i18n.language?.startsWith("ar");
  const meetingsParams = { limit: 50 };
  const meetings = useListProjectMeetings(projectId, meetingsParams, {
    query: {
      enabled: recordKind === "meetings",
      queryKey: getListProjectMeetingsQueryKey(projectId, meetingsParams),
    },
  });
  const claims = useCopilotClaims(projectId, recordKind === "claims");
  const changeOrders = useCopilotChangeOrders(projectId, recordKind === "change-orders");
  const documents = useCopilotDocuments(projectId, recordKind === "documents" || recordKind === "rfis");
  const correspondence = useCopilotCorrespondence(projectId, recordKind === "rfis");

  const isLoading =
    (recordKind === "meetings" && meetings.isLoading) ||
    (recordKind === "claims" && claims.isLoading) ||
    (recordKind === "change-orders" && changeOrders.isLoading) ||
    (recordKind === "documents" && documents.isLoading) ||
    (recordKind === "rfis" && (documents.isLoading || correspondence.isLoading));

  const isError =
    (recordKind === "meetings" && meetings.isError) ||
    (recordKind === "claims" && claims.isError) ||
    (recordKind === "change-orders" && changeOrders.isError) ||
    (recordKind === "documents" && documents.isError) ||
    (recordKind === "rfis" && (documents.isError || correspondence.isError));

  const timedOut = useBoundedTimeout(isLoading, DATA_TIMEOUT_MS);
  const stepCount = recordKind === "claims" ? 6 : 2;
  const revealed = useProgressiveReveal(stepCount, !isLoading, 320);

  if (isLoading) return <LoadingBubble topic={RECORD_TOPIC_LABEL[recordKind]} timedOut={timedOut} />;

  if (recordKind === "claims") {
    return <InsightCard view={buildClaimsInsightView(claims.data ?? [], projectLabel, isError, undefined, isAr)} revealed={revealed} />;
  }

  const view = buildRecordView(recordKind, projectLabel, isError, {
    meetings: meetings.data,
    changeOrders: changeOrders.data,
    documents: documents.data,
    correspondence: correspondence.data,
  });

  return <RecordCard view={view} revealed={revealed} />;
}

interface PageDataProps {
  execData?: ExecutiveIntelligence;
  execLoading: boolean;
  execIsError: boolean;
  summaryData?: DashboardSummaryData;
  summaryLoading: boolean;
  summaryIsError: boolean;
  projectsData?: ProjectRecord[];
  projectsLoading: boolean;
  projectsIsError: boolean;
  healthScoresData?: HealthScoreRecord[];
  healthScoresLoading: boolean;
}

// Answers page-aware questions ("Summarize this page") using whichever real
// data source exists for the current route. Each instance owns any bespoke
// per-context fetch it needs (project-detail / site-report-detail / claims
// portfolio aggregate / reports) — mounted once per chat message, exactly
// like RecordInsightContent above.
function ContextSummaryContent({ pageContext, data }: { pageContext: PageContext; data: PageDataProps }) {
  const { t, i18n } = useTranslation();
  const isAr = !!i18n.language?.startsWith("ar");
  const kind = pageContext.kind;
  const {
    execData, execLoading, execIsError,
    summaryData, summaryLoading, summaryIsError,
    projectsData, projectsLoading, projectsIsError,
    healthScoresData, healthScoresLoading,
  } = data;

  const projectDetailId = kind === "project-detail" ? pageContext.projectId : undefined;
  const prParams = { project_id: projectDetailId, limit: 100 };
  const poParams = { project_id: projectDetailId, limit: 100 };
  const safetyParams = { limit: 100 };
  const siteReportParams = { limit: 100 };

  const prs = useListPurchaseRequests(prParams, {
    query: { enabled: !!projectDetailId, queryKey: getListPurchaseRequestsQueryKey(prParams) },
  });
  const pos = useListPurchaseOrders(poParams, {
    query: { enabled: !!projectDetailId, queryKey: getListPurchaseOrdersQueryKey(poParams) },
  });
  const safetyEvents = useListProjectSafetyEvents(projectDetailId ?? 0, safetyParams, {
    query: {
      enabled: !!projectDetailId,
      queryKey: getListProjectSafetyEventsQueryKey(projectDetailId ?? 0, safetyParams),
    },
  });
  const siteReports = useListProjectSiteReports(projectDetailId ?? 0, siteReportParams, {
    query: {
      enabled: !!projectDetailId,
      queryKey: getListProjectSiteReportsQueryKey(projectDetailId ?? 0, siteReportParams),
    },
  });
  const projectClaims = useCopilotClaims(projectDetailId, kind === "project-detail");
  const projectMeetingsParams = { limit: 50 };
  const projectMeetings = useListProjectMeetings(projectDetailId ?? 0, projectMeetingsParams, {
    query: {
      enabled: kind === "project-detail" && !!projectDetailId,
      queryKey: getListProjectMeetingsQueryKey(projectDetailId ?? 0, projectMeetingsParams),
    },
  });

  const analysis = useCopilotSiteReportAnalysis(
    kind === "site-report-detail" ? pageContext.projectId : undefined,
    kind === "site-report-detail" ? pageContext.reportId : undefined,
    kind === "site-report-detail"
  );

  const portfolioProjectIds = projectsData?.map((p) => p.id);
  const portfolioClaims = useCopilotPortfolioClaims(portfolioProjectIds, kind === "claims");

  const weeklyReport = useExecutiveWeeklyReport(kind === "reports");

  const sharedLoading = execLoading || summaryLoading || projectsLoading || healthScoresLoading;

  const isLoading =
    (["dashboard", "projects", "procurement", "meetings", "site-reports"].includes(kind) && sharedLoading) ||
    (kind === "project-detail" &&
      (sharedLoading ||
        prs.isLoading ||
        pos.isLoading ||
        safetyEvents.isLoading ||
        siteReports.isLoading ||
        projectClaims.isLoading ||
        projectMeetings.isLoading)) ||
    (kind === "site-report-detail" && analysis.isLoading) ||
    (kind === "claims" && (projectsLoading || portfolioClaims.isLoading)) ||
    (kind === "reports" && weeklyReport.isLoading);

  const isError =
    (kind === "project-detail" && (execIsError || projectsIsError || prs.isError || pos.isError || safetyEvents.isError || siteReports.isError || projectClaims.isError)) ||
    (kind === "site-report-detail" && analysis.isError) ||
    (kind === "claims" && (projectsIsError || portfolioClaims.isError)) ||
    (kind === "reports" && weeklyReport.isError);

  // The claims aggregate fans out one request per portfolio project (not a
  // single fetch), so it's given a longer — but still strictly bounded —
  // timeout budget than every other context, which only ever fires one or
  // two requests.
  const contextTimeoutMs = kind === "claims" ? CLAIMS_AGGREGATE_TIMEOUT_MS : DATA_TIMEOUT_MS;
  const timedOut = useBoundedTimeout(isLoading, contextTimeoutMs);
  const isThinCard = kind === "meetings" || kind === "site-reports";
  const revealed = useProgressiveReveal(isThinCard ? 2 : 6, !isLoading, 320);

  if (kind === "rfis" || kind === "change-orders" || kind === "documents" || kind === "other") {
    return (
      <div className="max-w-[85%] rounded-2xl rounded-bl-sm border border-white/10 bg-white/[0.06] px-4 py-2.5">
        <p className="text-sm text-white/80 leading-relaxed">{t(INSUFFICIENT_DATA_REPLY)}</p>
      </div>
    );
  }

  if (isLoading) return <LoadingBubble topic={CONTEXT_LABEL[kind] || "page"} timedOut={timedOut} />;

  if (kind === "dashboard") {
    return (
      <InsightCard
        view={buildInsight("portfolio-summary", { execData, execIsError, summaryData, summaryIsError, projectsData, projectsIsError }, isAr)}
        revealed={revealed}
      />
    );
  }
  if (kind === "projects") {
    return (
      <InsightCard
        view={buildInsight("project-health", { execData, execIsError, summaryData, summaryIsError, projectsData, projectsIsError }, isAr)}
        revealed={revealed}
      />
    );
  }
  if (kind === "procurement") {
    return (
      <InsightCard
        view={buildInsight("procurement-risks", { execData, execIsError, summaryData, summaryIsError, projectsData, projectsIsError }, isAr)}
        revealed={revealed}
      />
    );
  }

  if (kind === "meetings") {
    return (
      <RecordCard
        view={{
          title: isAr ? "نظرة عامة على الاجتماعات" : "Meetings Overview",
          overview: summaryIsError
            ? UNAVAILABLE
            : isAr
              ? `تشير سجلات AMAD إلى ${fieldText(summaryData?.total_meetings)} اجتماعاً و${fieldText(summaryData?.total_decisions)} قراراً مسجلاً عبر المحفظة.`
              : `${fieldText(summaryData?.total_meetings)} meetings and ${fieldText(summaryData?.total_decisions)} decisions on record across the portfolio.`,
          lines: summaryIsError
            ? [UNAVAILABLE]
            : isAr
              ? [
                  `${fieldText(summaryData?.total_meetings)} إجمالي الاجتماعات`,
                  `${fieldText(summaryData?.total_decisions)} إجمالي القرارات`,
                ]
              : [
                  `${fieldText(summaryData?.total_meetings)} total meetings`,
                  `${fieldText(summaryData?.total_decisions)} total decisions`,
                ],
        }}
        revealed={revealed}
      />
    );
  }

  if (kind === "site-reports") {
    // Per the reasoning pipeline, report volume is not the signal — safety
    // and quality risk categories (already computed live, portfolio-wide)
    // stand in for "recurring observations" since no per-report trend
    // aggregate exists without a new endpoint.
    const safetyRisk = findRisk(execData, "safety");
    const qualityRisk = findRisk(execData, "quality");
    const safetyTier = severityTier(safetyRisk?.severity);
    return (
      <InsightCard
        view={
          execIsError
            ? NO_DATA_VIEW(isAr ? "تحليل مخاطر التقارير الميدانية" : "Site Reports — Operational Risk Analysis")
            : {
                title: isAr ? "تحليل مخاطر التقارير الميدانية" : "Site Reports — Operational Risk Analysis",
                executiveSummary: isAr
                  ? safetyTier === "high"
                    ? `تشير أنشطة الموقع إلى وجود مخاوف سلامة حقيقية حالياً — ${safetyRisk!.detail}.`
                    : "لا تُظهر أنشطة التقارير الميدانية أي مخاوف سلامة أو جودة بارزة على مستوى المحفظة حالياً."
                  : safetyTier === "high"
                    ? `Site activity indicates a live safety concern — ${safetyRisk!.detail}.`
                    : "Site reporting activity shows no dominant safety or quality concern at the portfolio level currently.",
                keyFindings: isAr
                  ? findingsOrFallback(
                      safetyRisk && safetyRisk.count > 0 && `السلامة: ${safetyRisk.detail}`,
                      qualityRisk && qualityRisk.count > 0 && `الجودة: ${qualityRisk.detail}`,
                      summaryData?.total_site_reports != null &&
                        `${summaryData.total_site_reports} تقريراً ميدانياً مسجلاً (مؤشر حجم داعم، وليس المؤشر الأساسي)`
                    )
                  : findingsOrFallback(
                      safetyRisk && safetyRisk.count > 0 && `Safety: ${safetyRisk.detail}`,
                      qualityRisk && qualityRisk.count > 0 && `Quality: ${qualityRisk.detail}`,
                      summaryData?.total_site_reports != null &&
                        `${summaryData.total_site_reports} site reports on record (supporting volume, not the primary signal)`
                    ),
                primaryRisks: safetyRisk ? `${capitalize(safetyRisk.detail)}.` : "No dominant safety risk identified.",
                businessImpact: BUSINESS_IMPACT_MAP.safety,
                recommendedAction:
                  safetyTier === "high"
                    ? `${capitalize(RISK_ACTION_MAP.safety)}.`
                    : "Continue routine site inspection cadence; no escalation required.",
                metrics: [
                  { icon: ShieldAlert, label: "High Severity", value: summaryIsError ? UNAVAILABLE : fieldText(summaryData?.high_severity_events) },
                  { icon: AlertTriangle, label: "Open NCRs", value: summaryIsError ? UNAVAILABLE : fieldText(summaryData?.open_ncrs) },
                  { icon: FileText, label: "Total Reports", value: summaryIsError ? UNAVAILABLE : fieldText(summaryData?.total_site_reports) },
                ],
              }
        }
        revealed={revealed}
      />
    );
  }

  if (kind === "reports") {
    const report = weeklyReport.data;
    const topAction = report?.recommended_actions?.[0];
    const topRisk = report?.biggest_risks?.[0];
    const view: InsightView =
      isError || !report
        ? NO_DATA_VIEW(isAr ? "التقرير التنفيذي الأسبوعي — تحليل" : "Executive Weekly Report — Analysis")
        : {
            title: isAr ? "التقرير التنفيذي الأسبوعي — تحليل" : "Executive Weekly Report — Analysis",
            executiveSummary: report.portfolio_summary,
            keyFindings: isAr
              ? findingsOrFallback(
                  report.critical_alerts.length > 0 && `${report.critical_alerts.length} تنبيهاً حرجاً مسجلاً خلال هذه الفترة`,
                  report.procurement_blockers.length > 0 && `${report.procurement_blockers.length} عائقاً في المشتريات تم رصده`,
                  topAction && `الأولوية القصوى: ${topAction.area}`
                )
              : findingsOrFallback(
                  report.critical_alerts.length > 0 && `${report.critical_alerts.length} critical ${plural(report.critical_alerts.length, "alert")} logged this period`,
                  report.procurement_blockers.length > 0 && `${report.procurement_blockers.length} procurement ${plural(report.procurement_blockers.length, "blocker")} identified`,
                  topAction && `Top priority: ${topAction.area}`
                ),
            primaryRisks: topRisk ? `${capitalize(topRisk.detail)}.` : "No dominant risk category identified.",
            businessImpact: topRisk
              ? (BUSINESS_IMPACT_MAP[topRisk.category] ?? "Continued underperformance in this area may affect portfolio delivery commitments.")
              : NO_LIVE_DATA,
            recommendedAction: topAction ? `${topAction.action}.` : "Continue standard portfolio monitoring.",
            metrics: [
              { icon: Gauge, label: "Portfolio Score", value: fieldText(report.portfolio_score) },
              { icon: Activity, label: "Status", value: fieldText(report.portfolio_status) },
              { icon: AlertTriangle, label: "Critical Alerts", value: fieldText(report.critical_alerts.length) },
              { icon: Package, label: "Procurement Blockers", value: fieldText(report.procurement_blockers.length) },
              { icon: Building2, label: "Total Projects", value: fieldText(report.health_distribution.total) },
            ],
          };
    return <InsightCard view={view} revealed={revealed} />;
  }

  if (kind === "claims") {
    return <InsightCard view={buildClaimsInsightView(portfolioClaims.data ?? [], "the portfolio", isError, projectsData, isAr)} revealed={revealed} />;
  }

  if (kind === "site-report-detail") {
    const a = analysis.data;
    const view: InsightView =
      isError || !a
        ? NO_DATA_VIEW(isAr ? "تحليل مخاطر التقرير الميداني" : "Site Report Risk Analysis")
        : {
            title: isAr ? "تحليل مخاطر التقرير الميداني" : "Site Report Risk Analysis",
            executiveSummary: a.executive_summary,
            keyFindings: findingsOrFallback(
              a.progress_assessment,
              a.delay_analysis && !/no explicit/i.test(a.delay_analysis) ? a.delay_analysis : null,
              a.safety_findings[0]
            ),
            primaryRisks: a.risk_analysis || (isAr ? "لا توجد مخاطر جوهرية مرصودة في هذا التقرير." : "No significant risks identified in this report."),
            businessImpact: a.escalation_required
              ? isAr
                ? "يتطلب هذا التقرير تصعيداً — قد تؤثر البنود غير المحلولة على الجدول الزمني أو الامتثال للسلامة أو العلاقة مع العميل إن لم تُعالج فوراً."
                : "This report requires escalation — unresolved items may affect schedule, safety compliance, or client relations if not addressed promptly."
              : isAr
                ? "النتائج ضمن النطاق التشغيلي الطبيعي ولا تتطلب تصعيداً في الوقت الحالي."
                : "Findings are within normal operating parameters and do not currently require escalation.",
            recommendedAction: a.recommended_actions[0] ?? (isAr ? "لا يوجد إجراء محدد موصى به." : "No specific action recommended."),
            metrics: [
              { icon: Target, label: isAr ? "الأولوية" : "Priority", value: a.priority_level },
              { icon: AlertTriangle, label: isAr ? "التصعيد" : "Escalation", value: a.escalation_required ? (isAr ? "مطلوب" : "Required") : (isAr ? "غير مطلوب" : "Not Required") },
              { icon: Gauge, label: isAr ? "الثقة" : "Confidence", value: fieldText(a.confidence_score) },
            ],
          };
    return <InsightCard view={view} revealed={revealed} />;
  }

  // project-detail
  const project = projectsData?.find((p) => p.id === projectDetailId);
  const hs = healthScoresData?.find((h) => h.project_id === projectDetailId);
  if (!project) {
    return <InsightCard view={NO_DATA_VIEW(isAr ? "النظرة التنفيذية للمشروع" : "Project Executive Overview")} revealed={revealed} />;
  }
  const prRows: PurchaseRequestRecord[] = prs.data ?? [];
  const poRows: PurchaseOrderRecord[] = pos.data ?? [];
  const safetyRows: SafetyEventRecord[] = safetyEvents.data ?? [];
  const siteReportRows: SiteReportRecord[] = siteReports.data ?? [];
  const claimsRows = projectClaims.data ?? [];
  const meetingsRows = projectMeetings.data ?? [];
  const OPEN_PR_STATUSES = new Set(["Pending Clarification", "Under Review", "Needs Rework", "Returned to Requester"]);
  const latePOs = poRows.filter((p) => p.is_late).length;
  const openPRs = prRows.filter((p) => OPEN_PR_STATUSES.has(p.status)).length;
  const highSeverity = safetyRows.filter((e) => e.severity === "High" || e.severity === "Critical").length;
  const hasRisk = !!hs && (hs.level === "Critical" || hs.level === "At Risk");
  const penalties = hs
    ? [
        { key: "schedule", value: hs.schedule_penalty },
        { key: "safety", value: hs.safety_penalty },
        { key: "quality", value: hs.ncr_penalty },
        { key: "procurement", value: hs.procurement_penalty },
      ]
    : [];
  const topPenalty = penalties.length ? penalties.reduce((a, b) => (b.value > a.value ? b : a)) : undefined;
  const statusAr = PROJECT_STATUS_LABEL_AR[project.status?.toLowerCase() ?? ""] ?? project.status;
  const levelAr = hs ? (HEALTH_LEVEL_LABEL_AR[hs.level.toLowerCase()] ?? hs.level) : undefined;
  const view: InsightView = {
    title: isAr ? `النظرة التنفيذية — ${project.project_code}` : `Executive Overview — ${project.project_code}`,
    executiveSummary: isAr
      ? !hs
        ? `${project.project_code} — ${project.project_name} حالته "${statusAr}". بيانات الصحة غير متوفرة حالياً.`
        : `${project.project_code} — ${project.project_name} حالته "${statusAr}" وتصنيفه الصحي "${levelAr}" (${hs.score}/100).${hasRisk && topPenalty ? ` والمحرك الرئيسي لذلك هو ${PENALTY_LABEL_AR[topPenalty.key]}.` : ""}`
      : !hs
        ? `${project.project_code} — ${project.project_name} is ${project.status}. Health data is currently unavailable.`
        : `${project.project_code} — ${project.project_name} is ${project.status} and rated ${hs.level.toLowerCase()} (${hs.score}/100).${hasRisk && topPenalty ? ` The primary driver is ${PENALTY_LABEL[topPenalty.key]}.` : ""}`,
    keyFindings: isAr
      ? findingsOrFallback(
          latePOs > 0 && `${latePOs} أمر شراء متأخر`,
          highSeverity > 0 && `${highSeverity} حدث سلامة بدرجة عالية/حرجة`,
          claimsRows.length > 0 && `${claimsRows.length} مطالبة مسجلة`
        )
      : findingsOrFallback(
          latePOs > 0 && `${latePOs} late purchase ${plural(latePOs, "order")}`,
          highSeverity > 0 && `${highSeverity} high/critical severity safety ${plural(highSeverity, "event")}`,
          claimsRows.length > 0 && `${claimsRows.length} ${plural(claimsRows.length, "claim")} on record`
        ),
    primaryRisks: !hs
      ? NO_LIVE_DATA
      : hasRisk && hs.reasons?.[0]
        ? `${capitalize(hs.reasons[0])}.`
        : "No significant risk indicators identified for this project.",
    businessImpact: !hs
      ? NO_LIVE_DATA
      : hasRisk && topPenalty
        ? (BUSINESS_IMPACT_MAP[topPenalty.key] ?? "Continued underperformance may affect delivery timelines or cost.")
        : "No material business impact identified at this time.",
    recommendedAction: !hs
      ? NO_LIVE_DATA
      : hasRisk && topPenalty && topPenalty.value > 0
        ? `${capitalize(RISK_ACTION_MAP[topPenalty.key])}.`
        : "Continue standard monitoring; no immediate action required.",
    metrics: [
      { icon: Gauge, label: "Score", value: hs ? String(hs.score) : UNAVAILABLE },
      { icon: Activity, label: "Level", value: hs ? hs.level : UNAVAILABLE },
      { icon: Building2, label: "Status", value: fieldText(project.status) },
      { icon: Package, label: "Late POs", value: String(latePOs) },
      { icon: ShieldAlert, label: "High-Sev Safety", value: String(highSeverity) },
    ],
  };
  return <InsightCard view={view} revealed={revealed} />;
}

interface AIDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AIDrawer({ isOpen, onClose }: AIDrawerProps) {
  const { t, i18n } = useTranslation();
  const isRTL = i18n.language?.startsWith("ar");
  const [location] = useLocation();
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  // Ref, not state — read/written across async calls only, never rendered.
  const conversationIdRef = useRef<number | null>(null);
  // Which backend path typed messages go through. "procurement" pins EVERY
  // message (not just the initial click) to POST /ai/agents/procurement, and
  // "meeting" pins every message to POST /ai/agents/meeting — never the
  // general /copilot/query — so a question can never fall through the
  // keyword router into execute_multi_domain_plan() and pull in unrelated
  // domain evidence. Switching agents always starts a fresh conversation
  // (see startNewChat / handleProcurementAgentClick / handleMeetingAgentClick)
  // so citations from one agent's chat never leak into another's.
  const [activeAgent, setActiveAgent] = useState<"general" | "procurement" | "meeting">("general");

  const pageContext = resolvePageContext(location);

  // Portfolio-wide reference data — fetched once while the panel is open,
  // reused by every insight so no intent needs its own duplicate fetch.
  const { data: execData, isLoading: execLoading, isError: execIsError } = useExecutive(isOpen);
  const {
    data: summaryData,
    isLoading: summaryLoading,
    isError: summaryIsError,
  } = useGetDashboardSummary({ query: { enabled: isOpen, queryKey: ["/api/v1/dashboard/summary"] } });
  const projectsParams = { limit: 100 }; // backend caps limit at 100 (Query(..., le=100))
  const {
    data: projectsData,
    isLoading: projectsLoading,
    isError: projectsIsError,
  } = useListProjects(projectsParams, {
    query: { enabled: isOpen, queryKey: getListProjectsQueryKey(projectsParams) },
  });
  const { data: healthScoresData, isLoading: healthScoresLoading } = useListProjectHealthScores({
    query: { enabled: isOpen, queryKey: getListProjectHealthScoresQueryKey() },
  });

  const dataLoading = execLoading || summaryLoading || projectsLoading || healthScoresLoading;
  const dataTimedOut = useBoundedTimeout(dataLoading, DATA_TIMEOUT_MS);

  const resolvedContextProject =
    pageContext.kind === "project-detail" || pageContext.kind === "site-report-detail"
      ? projectsData?.find((p) => p.id === pageContext.projectId)
      : undefined;
  const contextLabel =
    pageContext.kind === "other"
      ? null
      : pageContext.kind === "project-detail"
        ? (resolvedContextProject?.project_code ?? t("Project"))
        : pageContext.kind === "site-report-detail"
          ? `${resolvedContextProject?.project_code ?? t("Project")} · ${t("Report #{{id}}", { id: pageContext.reportId })}`
          : t(CONTEXT_LABEL[pageContext.kind]);

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

  const startNewChat = () => {
    setMessages([]);
    setInput("");
    conversationIdRef.current = null;
    setActiveAgent("general");
    textareaRef.current?.focus();
  };

  // Translated at creation time (this closure has `t` in scope) so the
  // guide message is stored already in the active UI language.
  const translatedProjectHint = (topic: string) =>
    t('Please include a project code or name to check its {{topic}} — for example: "{{topic}} for PRJ-0057".', {
      topic: t(topic),
    });

  // Deterministic fallback ONLY — used when the real AI pipeline call fails.
  // Same pattern-matching used in earlier phases, now a safety net rather
  // than the primary path, so a real backend outage never means silence.
  const resolveDeterministicFallback = (content: string): Omit<CopilotMessage, "id" | "createdAt"> | null => {
    if (isPageAwareQuery(content)) {
      return { role: "assistant-context", pageContext };
    }

    const intent = detectIntent(content);
    if (!intent) return null;

    const recordKind = RECORD_KIND_BY_INTENT[intent];
    if (recordKind) {
      const project = findProjectMatch(content, projectsData);
      if (!project) return { role: "assistant-guide", text: translatedProjectHint(RECORD_TOPIC_LABEL[recordKind]) };
      return {
        role: "assistant-record",
        recordKind,
        projectId: project.id,
        projectLabel: `${project.project_code} — ${project.project_name}`,
      };
    }

    if (intent === "project-status") {
      const project = findProjectMatch(content, projectsData);
      if (!project) return { role: "assistant-guide", text: translatedProjectHint("status") };
      return { role: "assistant-insight", insightType: "project-status", targetProjectId: project.id };
    }

    return { role: "assistant-insight", insightType: intent as InsightType };
  };

  // Backend intent routing (backend/app/ai/intent.py) matches plain Arabic
  // keyword substrings — not touched here. A couple of natural, colloquial
  // Arabic phrasings used in executive demos don't literally contain any of
  // its keywords, so the backend can't route them. This appends the
  // matching canonical keyword phrase to the OUTGOING request only (never
  // shown to the user, never affects the displayed question) so the
  // existing routing logic resolves the correct domain. No backend file is
  // modified — this is purely a client-side request-shaping aid.
  const ROUTING_HINTS_AR: { pattern: RegExp; hint: string }[] = [
    { pattern: /تنصح|ماذا توصي/, hint: "ملخص تنفيذي" },
    { pattern: /أخطر[\s\S]{0,20}(مشاريع|مشروع)/, hint: "مشاريع حرجة" },
  ];
  const withRoutingHint = (question: string): string => {
    const hit = ROUTING_HINTS_AR.find((r) => r.pattern.test(question));
    return hit ? `${question} — ${hit.hint}` : question;
  };

  // The one real request path: every message (typed or a quick-action chip)
  // goes to the existing backend AI Copilot pipeline (RBAC-scoped retrieval,
  // grounding, citations, bilingual EN/AR — see backend/app/ai/pipeline.py).
  // No new template logic is added here. On failure, a deterministic
  // fallback is appended when one applies — clearly labeled as such.
  const runCopilotQuery = async (question: string, assistantId: string) => {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), COPILOT_TIMEOUT_MS);
    const projectIdHint =
      pageContext.kind === "project-detail" || pageContext.kind === "site-report-detail" ? pageContext.projectId : undefined;

    try {
      const res = await postCopilotQuery(
        { question: withRoutingHint(question), conversation_id: conversationIdRef.current ?? undefined, project_id: projectIdHint },
        controller.signal
      );
      window.clearTimeout(timeoutId);
      conversationIdRef.current = res.conversation_id;
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, aiResponse: res, aiError: undefined } : m)));
    } catch (err) {
      window.clearTimeout(timeoutId);
      const isAbort = err instanceof DOMException && err.name === "AbortError";
      const message = isAbort
        ? "The AI service is taking longer than expected. Please try again."
        : err instanceof CopilotApiError
          ? err.status === 429
            ? "Too many requests — please wait a moment and try again."
            : err.message
          : "The AI service is currently unavailable.";

      setMessages((prev) => {
        const withError = prev.map((m) => (m.id === assistantId ? { ...m, aiError: message } : m));
        const fallback = resolveDeterministicFallback(question);
        if (!fallback) return withError;
        const fbNow = Date.now();
        return [...withError, { id: `fb-${fbNow}`, createdAt: fbNow, isFallback: true, ...fallback }];
      });
    }
  };

  // Procurement Intelligence Agent — a fixed-scope specialist call (no
  // free-text question), hitting the existing backend AI pipeline's own
  // agent endpoint (RBAC-scoped retrieval, grounding, citations, bilingual
  // EN/AR — see backend/app/ai/pipeline.py:execute_procurement_agent). Same
  // response shape as the regular Copilot query, so it renders through the
  // same AiAnswerCard below.
  const runProcurementAgent = async (assistantId: string, question?: string) => {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), COPILOT_TIMEOUT_MS);
    const projectIdHint =
      pageContext.kind === "project-detail" || pageContext.kind === "site-report-detail" ? pageContext.projectId : undefined;

    try {
      const res = await postProcurementAgent(
        {
          conversation_id: conversationIdRef.current ?? undefined,
          project_id: projectIdHint,
          language: isRTL ? "ar" : "en",
          ...(question ? { question } : {}),
        },
        controller.signal
      );
      window.clearTimeout(timeoutId);
      conversationIdRef.current = res.conversation_id;
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, aiResponse: res, aiError: undefined } : m)));
    } catch (err) {
      window.clearTimeout(timeoutId);
      const isAbort = err instanceof DOMException && err.name === "AbortError";
      const message = isAbort
        ? "The AI service is taking longer than expected. Please try again."
        : err instanceof CopilotApiError
          ? err.status === 429
            ? "Too many requests — please wait a moment and try again."
            : err.message
          : "The AI service is currently unavailable.";
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, aiError: message } : m)));
    }
  };

  // Meeting Intelligence Agent — portfolio-wide meetings/decisions status
  // summary by default (no meeting_id), hitting the existing backend AI
  // pipeline's own agent endpoint (RBAC-scoped retrieval, grounding,
  // citations, bilingual EN/AR, deterministic fallback on provider failure —
  // see backend/app/ai/pipeline.py:execute_meeting_agent). Same response
  // shape as the regular Copilot query, so it renders through the same
  // AiAnswerCard below.
  const runMeetingAgent = async (assistantId: string, question?: string) => {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), COPILOT_TIMEOUT_MS);
    const projectIdHint =
      pageContext.kind === "project-detail" || pageContext.kind === "site-report-detail" ? pageContext.projectId : undefined;

    try {
      const res = await postMeetingAgent(
        {
          conversation_id: conversationIdRef.current ?? undefined,
          project_id: projectIdHint,
          language: isRTL ? "ar" : "en",
          ...(question ? { question } : {}),
        },
        controller.signal
      );
      window.clearTimeout(timeoutId);
      conversationIdRef.current = res.conversation_id;
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, aiResponse: res, aiError: undefined } : m)));
    } catch (err) {
      window.clearTimeout(timeoutId);
      const isAbort = err instanceof DOMException && err.name === "AbortError";
      const message = isAbort
        ? "The AI service is taking longer than expected. Please try again."
        : err instanceof CopilotApiError
          ? err.status === 429
            ? "Too many requests — please wait a moment and try again."
            : err.message
          : "The AI service is currently unavailable.";
      setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, aiError: message } : m)));
    }
  };

  const handleProcurementAgentClick = () => {
    // Isolate the conversation: an agent chat must never inherit
    // messages/citations from a general Copilot conversation, and vice versa.
    const now = Date.now();
    const assistantMsgId = `a-${now}`;
    const label = t("Run Procurement Agent");
    conversationIdRef.current = null;
    setActiveAgent("procurement");
    setMessages([
      { id: `u-${now}`, role: "user", text: label, createdAt: now },
      { id: assistantMsgId, role: "assistant-ai", aiQuestion: label, agentKind: "procurement", createdAt: now },
    ]);
    void runProcurementAgent(assistantMsgId);
  };

  const handleMeetingAgentClick = () => {
    // Isolate the conversation: an agent chat must never inherit
    // messages/citations from a general Copilot or Procurement Agent conversation.
    const now = Date.now();
    const assistantMsgId = `a-${now}`;
    const label = t("Run Meeting Agent");
    conversationIdRef.current = null;
    setActiveAgent("meeting");
    setMessages([
      { id: `u-${now}`, role: "user", text: label, createdAt: now },
      { id: assistantMsgId, role: "assistant-ai", aiQuestion: label, agentKind: "meeting", createdAt: now },
    ]);
    void runMeetingAgent(assistantMsgId);
  };

  const handleRetry = (messageId: string, question: string, agentKind?: "procurement" | "meeting") => {
    setMessages((prev) => prev.map((m) => (m.id === messageId ? { ...m, aiError: undefined, aiResponse: undefined } : m)));
    if (agentKind === "procurement") {
      // question is the fixed label on the initial click, or the user's own
      // typed text for later turns — only pass it through in the latter case.
      void runProcurementAgent(messageId, question === t("Run Procurement Agent") ? undefined : question);
    } else if (agentKind === "meeting") {
      void runMeetingAgent(messageId, question === t("Run Meeting Agent") ? undefined : question);
    } else {
      void runCopilotQuery(question, messageId);
    }
  };

  // Every user message (typed or a suggestion chip) goes through the same
  // real AI pipeline — no client-side template engine decides the answer.
  // The one exception: "summarize this page" has no page identity in its
  // own text ("this page" is meaningless to the backend without it), which
  // was observed to send the real pipeline into a pronoun-clarification
  // loop. The page's live data is already loaded client-side (the same
  // existing deterministic context-summary view used as the AI-failure
  // fallback), so that view is used directly — instant, grounded in real
  // data, no backend round-trip needed for this one query shape.
  const handleUserMessage = (rawText: string) => {
    const content = rawText.trim();
    if (!content) return;
    const now = Date.now();
    const assistantMsgId = `a-${now}`;

    // While Procurement Agent or Meeting Agent is active, EVERY message —
    // typed or chip — goes to that agent's dedicated endpoint, never
    // /copilot/query. This is the fix for the routing bug: a typed question
    // that missed the general pipeline's keyword router used to fall into
    // intent="unknown" → execute_multi_domain_plan(), pulling in unrelated
    // domain evidence. The dedicated agent endpoints never run intent
    // routing or that multi-domain fallback, so it can't happen here
    // regardless of wording.
    if (activeAgent === "procurement" || activeAgent === "meeting") {
      const agentKind = activeAgent;
      setMessages((prev) => [
        ...prev,
        { id: `u-${now}`, role: "user", text: content, createdAt: now },
        { id: assistantMsgId, role: "assistant-ai", aiQuestion: content, agentKind, createdAt: now },
      ]);
      setInput("");
      textareaRef.current?.focus();
      if (agentKind === "procurement") {
        void runProcurementAgent(assistantMsgId, content);
      } else {
        void runMeetingAgent(assistantMsgId, content);
      }
      return;
    }

    if (isPageAwareQuery(content)) {
      setMessages((prev) => [
        ...prev,
        { id: `u-${now}`, role: "user", text: content, createdAt: now },
        { id: assistantMsgId, role: "assistant-context", pageContext, createdAt: now },
      ]);
      setInput("");
      textareaRef.current?.focus();
      return;
    }

    setMessages((prev) => [
      ...prev,
      { id: `u-${now}`, role: "user", text: content, createdAt: now },
      { id: assistantMsgId, role: "assistant-ai", aiQuestion: content, createdAt: now },
    ]);
    setInput("");
    textareaRef.current?.focus();
    void runCopilotQuery(content, assistantMsgId);
  };

  // Send the DISPLAYED (possibly Arabic) chip text as the actual message —
  // not the internal English key — so the conversation and the AI pipeline
  // both see what the user actually clicked, in their own language.
  const handleChipClick = (chip: string) => handleUserMessage(t(chip));

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleUserMessage(input);
    }
  };

  if (!isOpen) return null;

  const suggestions = pageContext.kind !== "other" ? [...SUGGESTIONS, PAGE_AWARE_CHIP] : SUGGESTIONS;

  return (
    <>
      {/* Soft dark backdrop — dashboard stays visible behind it, just dimmed
          and slightly blurred. Clicking it closes the panel. */}
      <div
        className="fixed inset-0 z-45 bg-black/45 backdrop-blur-[3px] transition-opacity duration-300"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Copilot panel — dark premium glass, slides in from the trailing edge
          (right in LTR, left in RTL). translate-x is a physical transform,
          so its sign must flip with direction even though position/border
          already use logical end-0/border-s. */}
      <div
        className={cn(
          "fixed inset-y-0 end-0 z-50 flex flex-col",
          "w-full sm:w-[420px]",
          "bg-[#0b1220]/95 dark:bg-[#080e1c]/95 backdrop-blur-2xl",
          "border-s border-white/10",
          isRTL
            ? "shadow-[0_0_0_1px_rgba(255,255,255,0.04)_inset,24px_0_60px_-20px_rgba(0,0,0,0.6)]"
            : "shadow-[0_0_0_1px_rgba(255,255,255,0.04)_inset,-24px_0_60px_-20px_rgba(0,0,0,0.6)]",
          "transition-transform duration-300 ease-out",
          isOpen ? "translate-x-0" : isRTL ? "-translate-x-full" : "translate-x-full"
        )}
        dir={isRTL ? "rtl" : "ltr"}
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
                {activeAgent === "procurement" || activeAgent === "meeting" ? (
                  <span className="text-[11px] text-white/35 truncate">
                    · {t("Agent")}:{" "}
                    <span className="text-white/60">
                      {t(activeAgent === "procurement" ? "Procurement Agent" : "Meeting Agent")}
                    </span>
                  </span>
                ) : (
                  contextLabel && (
                    <span className="text-[11px] text-white/35 truncate">
                      · {t("Context")}: <span className="text-white/60">{contextLabel}</span>
                    </span>
                  )
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <button
              onClick={handleProcurementAgentClick}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-white/70 hover:text-white hover:bg-white/10 transition-colors"
              aria-label={t("Run Procurement Agent")}
              title={t("Run Procurement Agent")}
            >
              <Package className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{t("Procurement Agent")}</span>
            </button>
            <button
              onClick={handleMeetingAgentClick}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-white/70 hover:text-white hover:bg-white/10 transition-colors"
              aria-label={t("Run Meeting Agent")}
              title={t("Run Meeting Agent")}
            >
              <Calendar className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{t("Meeting Agent")}</span>
            </button>
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
                {suggestions.map((s) => (
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

                if (m.role === "assistant-ai") {
                  const isPending = !m.aiResponse && !m.aiError;
                  return (
                    <div key={m.id} className="flex items-end gap-2 animate-in fade-in-0 slide-in-from-bottom-1 duration-300">
                      <IconChip icon={Sparkles} />
                      <div className="flex flex-col items-start min-w-0">
                        {isPending && <AiPendingBubble />}
                        {m.aiError && <AiErrorBubble message={m.aiError} onRetry={() => handleRetry(m.id, m.aiQuestion ?? "", m.agentKind)} />}
                        {m.aiResponse && (
                          <AiAnswerCard response={m.aiResponse} question={m.aiQuestion} onFollowUp={handleUserMessage} />
                        )}
                        <span className="text-[10px] text-white/30 mt-1 ms-1">{formatTime(m.createdAt)}</span>
                      </div>
                    </div>
                  );
                }

                if (m.role === "assistant-insight" && m.insightType) {
                  return (
                    <div key={m.id} className="flex items-end gap-2 animate-in fade-in-0 slide-in-from-bottom-1 duration-300">
                      <IconChip icon={Sparkles} />
                      <div className="flex flex-col items-start min-w-0">
                        {m.isFallback && <FallbackLabel />}
                        {dataLoading ? (
                          <LoadingBubble topic="portfolio" timedOut={dataTimedOut} />
                        ) : (
                          <InsightContent
                            insightType={m.insightType}
                            ctx={{
                              execData,
                              execIsError,
                              summaryData,
                              summaryIsError,
                              projectsData,
                              projectsIsError,
                              targetProject:
                                m.insightType === "project-status"
                                  ? projectsData?.find((p) => p.id === m.targetProjectId)
                                  : undefined,
                              targetHealthScore:
                                m.insightType === "project-status"
                                  ? healthScoresData?.find((h) => h.project_id === m.targetProjectId)
                                  : undefined,
                            }}
                          />
                        )}
                        <span className="text-[10px] text-white/30 mt-1 ms-1">{formatTime(m.createdAt)}</span>
                      </div>
                    </div>
                  );
                }

                if (m.role === "assistant-record" && m.recordKind && m.projectId != null) {
                  return (
                    <div key={m.id} className="flex items-end gap-2 animate-in fade-in-0 slide-in-from-bottom-1 duration-300">
                      <IconChip icon={Sparkles} />
                      <div className="flex flex-col items-start min-w-0">
                        {m.isFallback && <FallbackLabel />}
                        <RecordInsightContent
                          recordKind={m.recordKind}
                          projectId={m.projectId}
                          projectLabel={m.projectLabel ?? ""}
                        />
                        <span className="text-[10px] text-white/30 mt-1 ms-1">{formatTime(m.createdAt)}</span>
                      </div>
                    </div>
                  );
                }

                if (m.role === "assistant-context" && m.pageContext) {
                  return (
                    <div key={m.id} className="flex items-end gap-2 animate-in fade-in-0 slide-in-from-bottom-1 duration-300">
                      <IconChip icon={Sparkles} />
                      <div className="flex flex-col items-start min-w-0">
                        {m.isFallback && <FallbackLabel />}
                        <ContextSummaryContent
                          pageContext={m.pageContext}
                          data={{
                            execData,
                            execLoading,
                            execIsError,
                            summaryData,
                            summaryLoading,
                            summaryIsError,
                            projectsData,
                            projectsLoading,
                            projectsIsError,
                            healthScoresData,
                            healthScoresLoading,
                          }}
                        />
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
                        <p className="text-sm text-white/80 leading-relaxed whitespace-pre-line">{t(m.text ?? "")}</p>
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
              onClick={() => handleUserMessage(input)}
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
