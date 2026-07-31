import { useState } from "react";
import { Loader2, Sparkles, ShieldAlert, FileQuestion, ListTodo, ClipboardList, GitCompare, HardHat, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { postCopilotQuery, postMeetingAgent, CopilotApiError, type CopilotQueryResponse } from "@/lib/copilotClient";
import { AIAnswerStructured } from "@/components/AIAnswerStructured";

// AI Action Panel (Phase 2 §3) — "Every major page should expose contextual
// AI actions." Each action reuses an existing endpoint (the general
// /copilot/query pipeline scoped by project_id, or the existing Meeting
// Intelligence Agent) rather than adding any new backend capability. One
// action runs at a time; the result renders inline in the ticket's
// Executive Summary/Key Findings/Evidence/Recommendations/Sources shape.

type ProjectAction = { label: string; icon: React.ElementType; question: string };
const PROJECT_ACTIONS: ProjectAction[] = [
  { label: "Generate Executive Summary", icon: Sparkles, question: "Give me an executive summary of this project." },
  { label: "Identify Risks", icon: ShieldAlert, question: "What are the key risks for this project right now?" },
  { label: "Find Missing Documents", icon: FileQuestion, question: "What documents or records appear to be missing or incomplete for this project?" },
  { label: "Suggest Next Actions", icon: ListTodo, question: "What should the project team prioritize next for this project?" },
];

type MeetingAction = { label: string; icon: React.ElementType; hint: string };
const MEETING_ACTIONS: MeetingAction[] = [
  { label: "Generate Minutes", icon: ClipboardList, hint: "Summarize this meeting as formal minutes." },
  { label: "Extract Decisions", icon: Zap, hint: "List every decision recorded for this meeting." },
  { label: "Create Action Items", icon: ListTodo, hint: "List the open action items from this meeting." },
];

type SiteReportAction = { label: string; icon: React.ElementType; question: string };
const SITE_REPORT_ACTIONS: SiteReportAction[] = [
  { label: "Compare Previous Reports", icon: GitCompare, question: "Compare this site report to previous reports for this project — what has changed?" },
  { label: "Generate Safety Recommendations", icon: HardHat, question: "Based on recent site reports for this project, what safety recommendations apply?" },
];

interface BaseProps {
  className?: string;
}
type Props =
  | (BaseProps & { entityKind: "project"; projectId: number; projectCode: string; projectName: string })
  | (BaseProps & { entityKind: "meeting"; meetingId: number; projectId?: number; meetingTitle: string })
  | (BaseProps & { entityKind: "site_report"; projectId: number; reportLabel: string });

export function AIActionPanel(props: Props) {
  const [activeLabel, setActiveLabel] = useState<string | null>(null);
  const [result, setResult] = useState<CopilotQueryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async (label: string, call: () => Promise<CopilotQueryResponse>) => {
    setActiveLabel(label);
    setError(null);
    setResult(null);
    try {
      const res = await call();
      setResult(res);
    } catch (err) {
      setError(err instanceof CopilotApiError ? err.message : "AI action failed. Please try again.");
    } finally {
      setActiveLabel(null);
    }
  };

  const actions =
    props.entityKind === "project"
      ? PROJECT_ACTIONS.map((a) => ({
          label: a.label, icon: a.icon,
          onRun: () => run(a.label, () => postCopilotQuery({ question: a.question, project_id: props.projectId })),
        }))
      : props.entityKind === "meeting"
        ? MEETING_ACTIONS.map((a) => ({
            label: a.label, icon: a.icon,
            onRun: () => run(a.label, () => postMeetingAgent({ meeting_id: props.meetingId, project_id: props.projectId, language: "en", question: a.hint })),
          }))
        : SITE_REPORT_ACTIONS.map((a) => ({
            label: a.label, icon: a.icon,
            onRun: () => run(a.label, () => postCopilotQuery({ question: a.question, project_id: props.projectId })),
          }));

  return (
    <div className={props.className}>
      <div className="flex items-center gap-2 mb-2">
        <Sparkles className="w-3.5 h-3.5 text-primary" />
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">AI Actions</p>
      </div>
      <div className="flex flex-wrap gap-2 mb-3">
        {actions.map((a) => {
          const Icon = a.icon;
          const isActive = activeLabel === a.label;
          return (
            <Button
              key={a.label}
              size="sm"
              variant="outline"
              onClick={a.onRun}
              disabled={activeLabel !== null}
              className="gap-1.5"
            >
              {isActive ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Icon className="h-3.5 w-3.5" />}
              {a.label}
            </Button>
          );
        })}
      </div>

      {error && (
        <p className="text-sm text-destructive mb-3">{error}</p>
      )}

      {result && <AIAnswerStructured response={result} />}
    </div>
  );
}
