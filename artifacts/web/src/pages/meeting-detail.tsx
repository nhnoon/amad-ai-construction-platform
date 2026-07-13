import { useEffect, useState } from "react";
import { useParams } from "wouter";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Sparkles, RefreshCw, CalendarDays, Users, ListChecks, CalendarX } from "lucide-react";
import {
  useListProjectMeetings,
  useListProjectDecisions,
  useListProjects,
} from "@workspace/api-client-react";
import { BackButton } from "@/components/back-button";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { listActionItems } from "@/lib/meetingsClient";
import { postMeetingAgent, CopilotApiError, type CopilotQueryResponse, type CopilotCitation } from "@/lib/copilotClient";
import { SOURCE_TYPE_LABELS, prettifySourceType } from "@/components/ai-answer-ui";

function meetingTypeBadge(type: string) {
  const m: Record<string, string> = {
    Weekly:     "badge-info",
    Technical:  "badge-purple",
    Safety:     "badge-warning",
    Commercial: "badge-gold",
  };
  return m[type] ?? "badge-neutral";
}

const AGENT_TIMEOUT_MS = 10000; // backend itself is bounded to a few seconds (see _MEETING_AGENT_LLM_TIMEOUT_S); this is just an outer network safety net

// Same staged-progress concept as components/ai-answer-ui.tsx's
// AiThinkingProgress, restyled with this page's light/dark-adaptive design
// tokens instead of that component's fixed dark-glass palette — this page
// (unlike the AIDrawer panel) follows the app's normal theme.
const THINKING_STEPS_EN = ["Understanding your request", "Retrieving live AMAD data", "Validating evidence", "Preparing executive analysis"];
const THINKING_STEPS_AR = ["فهم طلبك", "جلب بيانات آماد المباشرة", "التحقق من الأدلة", "إعداد التحليل التنفيذي"];

function ThinkingSteps({ ar }: { ar: boolean }) {
  const steps = ar ? THINKING_STEPS_AR : THINKING_STEPS_EN;
  const [activeIndex, setActiveIndex] = useState(0);
  useEffect(() => {
    setActiveIndex(0);
    const timers = steps.slice(1).map((_, i) => window.setTimeout(() => setActiveIndex(i + 1), (i + 1) * 650));
    return () => timers.forEach((id) => window.clearTimeout(id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  return (
    <div className="space-y-1.5" dir={ar ? "rtl" : "ltr"}>
      {steps.map((label, i) => {
        const done = i < activeIndex;
        const active = i === activeIndex;
        return (
          <div key={label} className={`flex items-center gap-2 text-xs ${ar ? "flex-row-reverse text-right" : ""}`}>
            <span
              className={`flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-full border text-[9px] ${
                done ? "border-emerald-500 bg-emerald-500/10 text-emerald-600" : active ? "border-amber-500" : "border-border"
              }`}
            >
              {done ? "✓" : active ? <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse" /> : null}
            </span>
            <span className={done ? "text-foreground/80" : active ? "text-foreground font-medium" : "text-muted-foreground/50"}>
              {label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

const CONFIDENCE_PRESENTATION: Record<string, { pct: number; textClass: string; barClass: string; labelEn: string; labelAr: string }> = {
  high:   { pct: 92, textClass: "text-emerald-600", barClass: "bg-emerald-500", labelEn: "High", labelAr: "عالية" },
  medium: { pct: 65, textClass: "text-amber-600",   barClass: "bg-amber-500",   labelEn: "Medium", labelAr: "متوسطة" },
  low:    { pct: 35, textClass: "text-orange-600",  barClass: "bg-orange-500",  labelEn: "Low", labelAr: "منخفضة" },
  none:   { pct: 10, textClass: "text-muted-foreground", barClass: "bg-muted-foreground/40", labelEn: "None", labelAr: "لا توجد" },
};

function ConfidenceMeterLight({ confidence, ar }: { confidence: string; ar: boolean }) {
  const p = CONFIDENCE_PRESENTATION[confidence] ?? CONFIDENCE_PRESENTATION.none;
  return (
    <div className={`flex items-center gap-1.5 ${ar ? "flex-row-reverse" : ""}`}>
      <span className={`text-[10px] font-bold uppercase tracking-wide ${p.textClass}`}>{ar ? p.labelAr : p.labelEn}</span>
      <div className="h-1.5 w-10 rounded-full bg-muted overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-700 ease-out ${p.barClass}`} style={{ width: `${p.pct}%` }} />
      </div>
      <span className="text-[10px] text-muted-foreground tabular-nums">{p.pct}%</span>
    </div>
  );
}

function SourcesGroupedLight({ citations, ar }: { citations: CopilotCitation[]; ar: boolean }) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  if (!citations.length) return null;

  const groups = new Map<string, CopilotCitation[]>();
  for (const c of citations) {
    const key = c.source_type || "other";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(c);
  }
  const toggle = (key: string) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  return (
    <div className="pt-2 border-t border-border/60 space-y-1.5">
      <p className="text-xs font-semibold text-muted-foreground">{ar ? "المصادر" : "Sources"}</p>
      <div className="grid grid-cols-2 gap-1.5">
        {Array.from(groups.entries()).map(([type, items]) => {
          const label = SOURCE_TYPE_LABELS[type] ? (ar ? SOURCE_TYPE_LABELS[type].ar : SOURCE_TYPE_LABELS[type].en) : prettifySourceType(type);
          const isOpen = expanded.has(type);
          return (
            <div key={type} className="rounded-lg border border-border/60 bg-muted/30 overflow-hidden min-w-0">
              <button
                type="button"
                onClick={() => toggle(type)}
                className={`w-full flex items-center justify-between gap-1.5 px-2.5 py-2 text-start hover:bg-muted/50 transition-colors ${ar ? "flex-row-reverse text-end" : ""}`}
              >
                <span className="text-xs font-medium text-foreground truncate">{label}</span>
                <span className="text-[10px] text-muted-foreground shrink-0">
                  {items.length} {ar ? "سجل" : items.length === 1 ? "record" : "records"}
                </span>
              </button>
              {isOpen && (
                <ul className={`px-2.5 pb-2 space-y-1 text-[11px] text-muted-foreground ${ar ? "text-end" : ""}`}>
                  {items.map((c) => (
                    <li key={c.id} className="truncate">{c.label}</li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function MeetingDetail() {
  const { t, i18n } = useTranslation();
  const isRTL = i18n.language?.startsWith("ar");
  const { projectId, meetingId } = useParams<{ projectId: string; meetingId: string }>();
  const projectIdNum = Number(projectId);
  const meetingIdNum = Number(meetingId);
  // Exact phrase required by the Meeting Agent spec — kept literal (not
  // routed through the shared i18n dictionary) so it never drifts from the
  // identical string the backend's deterministic fallback already returns.
  const unavailable = isRTL ? "غير متاح من قاعدة البيانات الحالية" : "Unavailable from current database.";

  const [agentResponse, setAgentResponse] = useState<CopilotQueryResponse | null>(null);
  const [agentError, setAgentError] = useState<string | null>(null);
  const [agentLoading, setAgentLoading] = useState(false);

  const { data: projects } = useListProjects({ limit: 60 });
  const project = projects?.find((p) => p.id === projectIdNum);

  const { data: meetings, isLoading: meetingLoading } = useListProjectMeetings(
    projectIdNum,
    { limit: 100 },
    { query: { enabled: !!projectIdNum, queryKey: ["meetings", projectIdNum] } }
  );
  const meeting = meetings?.find((m) => m.id === meetingIdNum);

  const { data: decisions } = useListProjectDecisions(
    projectIdNum,
    { limit: 100 },
    { query: { enabled: !!projectIdNum, queryKey: ["decisions", projectIdNum] } }
  );
  const meetingDecisions = (decisions ?? []).filter((d) => d.meeting_id === meetingIdNum);

  const { data: actionItems } = useQuery({
    queryKey: ["action-items", projectIdNum, meetingIdNum],
    queryFn: () => listActionItems(projectIdNum, meetingIdNum),
    enabled: !!projectIdNum && !!meetingIdNum,
  });

  const runMeetingAgent = async () => {
    setAgentLoading(true);
    setAgentError(null);
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), AGENT_TIMEOUT_MS);
    try {
      const res = await postMeetingAgent(
        {
          meeting_id: meetingIdNum,
          language: isRTL ? "ar" : "en",
          question: isRTL ? "لخص هذا الاجتماع" : "Summarize this meeting",
        },
        controller.signal
      );
      window.clearTimeout(timeoutId);
      setAgentResponse(res);
    } catch (err) {
      window.clearTimeout(timeoutId);
      const isAbort = err instanceof DOMException && err.name === "AbortError";
      setAgentError(
        isAbort
          ? t("The AI service is taking longer than expected. Please try again.")
          : err instanceof CopilotApiError
            ? err.message
            : t("The AI service is currently unavailable.")
      );
    } finally {
      setAgentLoading(false);
    }
  };

  if (meetingLoading) {
    return (
      <div className="space-y-4">
        <BackButton to="/meetings" label="Back to Meetings" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full rounded-xl" />
        <Skeleton className="h-40 w-full rounded-xl" />
      </div>
    );
  }

  if (!meeting) {
    return (
      <div className="space-y-4">
        <BackButton to="/meetings" label="Back to Meetings" />
        <div className="panel">
          <EmptyState icon={CalendarX} title={t("Meeting not found")} />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <BackButton to="/meetings" label="Back to Meetings" />

      {/* Meeting information */}
      <div className="page-header">
        <div>
          <h1 className="page-title">{meeting.title}</h1>
          <p className="page-subtitle flex flex-wrap items-center gap-2 mt-1">
            <span className="inline-flex items-center gap-1">
              <CalendarDays className="w-3.5 h-3.5" /> {meeting.meeting_date}
            </span>
            {project && <span>· {project.project_code} — {project.project_name}</span>}
            <span className={`badge ${meetingTypeBadge(meeting.meeting_type)}`}>{meeting.meeting_type}</span>
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Decisions */}
        <div className="panel">
          <div className="panel-header flex items-center gap-2">
            <ListChecks className="w-4 h-4 text-muted-foreground" />
            <h2 className="font-semibold text-sm">{t("Decisions")}</h2>
            <span className="text-xs text-muted-foreground">{meetingDecisions.length}</span>
          </div>
          <div className="panel-body space-y-3">
            {meetingDecisions.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("No data")}</p>
            ) : (
              meetingDecisions.map((d) => (
                <div key={d.id} className="rounded-lg border border-border/60 p-3">
                  <p className="text-sm">{d.decision_text}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {t("Owner")}: {d.owner} · {d.decision_date}
                  </p>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Action Items */}
        <div className="panel">
          <div className="panel-header flex items-center gap-2">
            <Users className="w-4 h-4 text-muted-foreground" />
            <h2 className="font-semibold text-sm">{t("Action Items")}</h2>
            <span className="text-xs text-muted-foreground">{actionItems?.length ?? 0}</span>
          </div>
          <div className="panel-body space-y-3">
            {!actionItems?.length ? (
              <p className="text-sm text-muted-foreground">{t("No data")}</p>
            ) : (
              actionItems.map((a) => (
                <div key={a.id} className="rounded-lg border border-border/60 p-3">
                  <p className="text-sm">{a.description}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {t("Owner")}: {a.owner || unavailable} ·{" "}
                    {t("Due")}: {a.due_date || unavailable} ·{" "}
                    <span className={`badge ${a.status === "open" ? "badge-warning" : "badge-success"}`}>{a.status}</span>
                  </p>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Meeting Agent */}
      <div className="panel">
        <div className="panel-header flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-muted-foreground" />
            <h2 className="font-semibold text-sm">{t("Meeting Agent")}</h2>
          </div>
          <Button size="sm" onClick={runMeetingAgent} disabled={agentLoading} className="gap-1.5">
            {agentLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
            {t("Summarize this meeting")}
          </Button>
        </div>
        <div className="panel-body">
          {agentLoading && !agentResponse && <ThinkingSteps ar={!!isRTL} />}
          {agentError && <p className="text-sm text-destructive">{agentError}</p>}
          {agentResponse && (
            <div className="space-y-3">
              <div className="flex items-center justify-end">
                <ConfidenceMeterLight confidence={agentResponse.confidence} ar={!!isRTL} />
              </div>
              <div className="whitespace-pre-line text-sm leading-relaxed">{agentResponse.answer}</div>
              <SourcesGroupedLight citations={agentResponse.citations} ar={!!isRTL} />
            </div>
          )}
          {!agentLoading && !agentResponse && !agentError && (
            <p className="text-sm text-muted-foreground">
              {t('Click "Summarize this meeting" to get an AI-generated summary of this meeting only.')}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
