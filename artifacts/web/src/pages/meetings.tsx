import { useState, useEffect } from "react";
import {
  useListProjects,
  useListProjectMeetings,
  useListProjectDecisions,
} from "@workspace/api-client-react";
import { useTranslation } from "react-i18next";
import { CalendarDays, AlertOctagon } from "lucide-react";

type Tab = "meetings" | "decisions";

function meetingTypeBadge(type: string) {
  const m: Record<string, string> = {
    Weekly:     "badge-info",
    Technical:  "badge-purple",
    Safety:     "badge-warning",
    Commercial: "badge-gold",
  };
  return m[type] ?? "badge-neutral";
}

export default function Meetings() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>("meetings");
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);

  const { data: projects } = useListProjects({ limit: 60 });

  useEffect(() => {
    if (projects && projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  const { data: meetings, isLoading: meetingsLoading, isError: meetingsError } = useListProjectMeetings(
    selectedProjectId ?? 0,
    { limit: 50 },
    { query: { enabled: !!selectedProjectId, queryKey: ["meetings", selectedProjectId] } }
  );

  const { data: decisions, isLoading: decisionsLoading, isError: decisionsError } = useListProjectDecisions(
    selectedProjectId ?? 0,
    { limit: 50 },
    { query: { enabled: !!selectedProjectId, queryKey: ["decisions", selectedProjectId] } }
  );

  const selectedProject = projects?.find((p) => p.id === selectedProjectId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("Meetings")}</h1>
          <p className="page-subtitle">
            {selectedProject
              ? `${selectedProject.project_code} — ${selectedProject.project_name}`
              : "Select a project"}
            {meetings || decisions ? (
              <>
                {meetings ? ` · ${meetings.length} ${t("Meetings")}` : ""}
                {decisions ? ` · ${decisions.length} ${t("Decisions")}` : ""}
              </>
            ) : null}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm font-medium text-muted-foreground whitespace-nowrap shrink-0">
            {t("Select Project")}
          </label>
          <select
            className="border rounded-lg px-3 py-2 text-sm bg-background text-foreground min-w-52 h-10"
            value={selectedProjectId ?? ""}
            onChange={(e) => setSelectedProjectId(Number(e.target.value))}
            data-testid="project-selector"
          >
            <option value="" disabled>{t("Select Project")}</option>
            {projects?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.project_code} — {p.project_name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-0 border-b border-border">
        {(["meetings", "decisions"] as Tab[]).map((id) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            data-testid={`tab-${id}`}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${
              tab === id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {id === "meetings" ? t("Meetings") : t("Decisions")}
            <span className="ms-2 text-xs text-muted-foreground">
              {id === "meetings" ? (meetings?.length ?? "…") : (decisions?.length ?? "…")}
            </span>
          </button>
        ))}
      </div>

      {!selectedProjectId ? (
        <div className="panel panel-body flex flex-col items-center justify-center h-48 text-muted-foreground gap-3">
          <CalendarDays className="w-10 h-10 opacity-30" />
          <p className="text-sm">{t("Select a project to view data")}</p>
        </div>
      ) : tab === "meetings" ? (
        <div className="panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table" data-testid="meetings-table">
              <thead>
                <tr>
                  <th>{t("Meeting Date")}</th>
                  <th className="min-w-[240px]">{t("Title")}</th>
                  <th>{t("Meeting Type")}</th>
                </tr>
              </thead>
              <tbody>
                {meetingsLoading ? (
                  <tr><td colSpan={3} className="text-center py-10 text-muted-foreground">{t("Loading...")}</td></tr>
                ) : meetingsError ? (
                  <tr><td colSpan={3} className="text-center py-10"><div className="flex flex-col items-center gap-1 text-muted-foreground"><AlertOctagon className="w-6 h-6 text-destructive opacity-60" /><span className="text-sm">Failed to load meetings</span></div></td></tr>
                ) : !meetings?.length ? (
                  <tr><td colSpan={3} className="text-center py-10 text-muted-foreground">{t("No data")}</td></tr>
                ) : (
                  meetings.map((m) => (
                    <tr key={m.id}>
                      <td className="whitespace-nowrap text-sm font-semibold">{m.meeting_date}</td>
                      <td className="font-medium">{m.title}</td>
                      <td>
                        <span className={`badge ${meetingTypeBadge(m.meeting_type)}`}>
                          {m.meeting_type}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table" data-testid="decisions-table">
              <thead>
                <tr>
                  <th>{t("Decision Date")}</th>
                  <th className="min-w-[300px]">{t("Decision Text")}</th>
                  <th>{t("Owner")}</th>
                </tr>
              </thead>
              <tbody>
                {decisionsLoading ? (
                  <tr><td colSpan={3} className="text-center py-10 text-muted-foreground">{t("Loading...")}</td></tr>
                ) : decisionsError ? (
                  <tr><td colSpan={3} className="text-center py-10"><div className="flex flex-col items-center gap-1 text-muted-foreground"><AlertOctagon className="w-6 h-6 text-destructive opacity-60" /><span className="text-sm">Failed to load decisions</span></div></td></tr>
                ) : !decisions?.length ? (
                  <tr><td colSpan={3} className="text-center py-10 text-muted-foreground">{t("No data")}</td></tr>
                ) : (
                  decisions.map((d) => (
                    <tr key={d.id}>
                      <td className="whitespace-nowrap text-sm font-semibold">{d.decision_date}</td>
                      <td className="text-sm max-w-md">{d.decision_text}</td>
                      <td className="text-muted-foreground text-sm">{d.owner}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
