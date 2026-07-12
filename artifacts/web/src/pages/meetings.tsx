import { useState, useEffect } from "react";
import { useLocation } from "wouter";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  useListProjects,
  useListProjectMeetings,
  useListProjectDecisions,
  getListProjectMeetingsQueryKey,
} from "@workspace/api-client-react";
import { useTranslation } from "react-i18next";
import { CalendarDays, AlertOctagon, Plus } from "lucide-react";
import { BackToOperations } from "@/components/back-to-operations";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter,
} from "@/components/ui/dialog";
import { createMeeting, listActionItems, MeetingsApiError } from "@/lib/meetingsClient";

type Tab = "meetings" | "decisions";

const MEETING_TYPES = ["Weekly", "Technical", "Safety", "Commercial"] as const;

function meetingTypeBadge(type: string) {
  const m: Record<string, string> = {
    Weekly:     "badge-info",
    Technical:  "badge-purple",
    Safety:     "badge-warning",
    Commercial: "badge-gold",
  };
  return m[type] ?? "badge-neutral";
}

// Create Meeting dialog — uses only fields the backend Meeting model
// actually supports (title, meeting_date, meeting_type, attendee names).
// Location, meeting notes, and a separate "status" field have no backing
// column in the current schema, so they are intentionally omitted rather
// than collected and silently discarded.
function CreateMeetingDialog({
  open,
  onOpenChange,
  projects,
  defaultProjectId,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projects: { id: number; project_code: string; project_name: string }[];
  defaultProjectId: number | null;
  onCreated: (projectId: number) => void;
}) {
  const { t } = useTranslation();
  const [projectId, setProjectId] = useState<number | null>(defaultProjectId);
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [meetingType, setMeetingType] = useState<string>(MEETING_TYPES[0]);
  const [attendees, setAttendees] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      setProjectId(defaultProjectId);
      setTitle("");
      setDate("");
      setTime("");
      setMeetingType(MEETING_TYPES[0]);
      setAttendees("");
      setError(null);
    }
  }, [open, defaultProjectId]);

  const canSubmit = !!projectId && title.trim().length > 0 && date.trim().length > 0;

  const handleSubmit = async () => {
    if (!projectId || !canSubmit) return;
    setSubmitting(true);
    setError(null);
    try {
      const meetingDate = time ? `${date} ${time}` : date;
      await createMeeting(projectId, {
        title: title.trim(),
        meeting_date: meetingDate,
        meeting_type: meetingType,
        attendees: attendees
          .split(",")
          .map((a) => a.trim())
          .filter(Boolean),
      });
      onCreated(projectId);
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof MeetingsApiError ? err.message : t("Failed to create meeting"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t("Create Meeting")}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-1.5">
            <label className="text-sm font-medium">{t("Project")}</label>
            <select
              className="w-full border rounded-lg px-3 py-2 text-sm bg-background text-foreground h-10"
              value={projectId ?? ""}
              onChange={(e) => setProjectId(Number(e.target.value))}
            >
              <option value="" disabled>{t("Select Project")}</option>
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.project_code} — {p.project_name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium">{t("Meeting Title")}</label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t("e.g. Weekly Progress Sync")} />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">{t("Meeting Date")}</label>
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">{t("Meeting Time")}</label>
              <Input type="time" value={time} onChange={(e) => setTime(e.target.value)} />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium">{t("Meeting Type")}</label>
            <select
              className="w-full border rounded-lg px-3 py-2 text-sm bg-background text-foreground h-10"
              value={meetingType}
              onChange={(e) => setMeetingType(e.target.value)}
            >
              {MEETING_TYPES.map((mt) => (
                <option key={mt} value={mt}>{mt}</option>
              ))}
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium">{t("Attendees")}</label>
            <Textarea
              value={attendees}
              onChange={(e) => setAttendees(e.target.value)}
              placeholder={t("Comma-separated names")}
              rows={2}
            />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
            {t("Cancel")}
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit || submitting}>
            {submitting ? t("Creating...") : t("Create Meeting")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function Meetings() {
  const { t } = useTranslation();
  const [, setLocation] = useLocation();
  const [tab, setTab] = useState<Tab>("meetings");
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const queryClient = useQueryClient();

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

  // No generated hook yet for action items (see lib/meetingsClient.ts) —
  // plain useQuery onto the same endpoint the backend already exposes.
  const { data: actionItems } = useQuery({
    queryKey: ["action-items", selectedProjectId],
    queryFn: () => listActionItems(selectedProjectId as number),
    enabled: !!selectedProjectId,
  });

  const decisionsCountByMeeting = new Map<number, number>();
  (decisions ?? []).forEach((d) => {
    decisionsCountByMeeting.set(d.meeting_id, (decisionsCountByMeeting.get(d.meeting_id) ?? 0) + 1);
  });

  const openActionItemsByMeeting = new Map<number, number>();
  (actionItems ?? []).forEach((a) => {
    if (a.status === "open") {
      openActionItemsByMeeting.set(a.meeting_id, (openActionItemsByMeeting.get(a.meeting_id) ?? 0) + 1);
    }
  });

  const selectedProject = projects?.find((p) => p.id === selectedProjectId);

  return (
    <div className="space-y-6">
      <BackToOperations />

      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("Meetings")}</h1>
          <p className="page-subtitle">
            {selectedProject
              ? `${selectedProject.project_code} — ${selectedProject.project_name}`
              : t("Select a project")}
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
          <Button onClick={() => setCreateOpen(true)} className="gap-1.5 whitespace-nowrap">
            <Plus className="w-4 h-4" />
            {t("Create Meeting")}
          </Button>
        </div>
      </div>

      <CreateMeetingDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        projects={projects ?? []}
        defaultProjectId={selectedProjectId}
        onCreated={(projectId) => {
          setSelectedProjectId(projectId);
          setTab("meetings");
          queryClient.invalidateQueries({ queryKey: getListProjectMeetingsQueryKey(projectId, { limit: 50 }) });
          queryClient.invalidateQueries({ queryKey: ["meetings", projectId] });
        }}
      />

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
                  <th className="min-w-[220px]">{t("Title")}</th>
                  <th>{t("Project")}</th>
                  <th>{t("Meeting Type")}</th>
                  <th>{t("Decisions")}</th>
                  <th>{t("Open Action Items")}</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {meetingsLoading ? (
                  <tr><td colSpan={7} className="text-center py-10 text-muted-foreground">{t("Loading...")}</td></tr>
                ) : meetingsError ? (
                  <tr><td colSpan={7} className="text-center py-10"><div className="flex flex-col items-center gap-1 text-muted-foreground"><AlertOctagon className="w-6 h-6 text-destructive opacity-60" /><span className="text-sm">{t("Failed to load meetings")}</span></div></td></tr>
                ) : !meetings?.length ? (
                  <tr><td colSpan={7} className="text-center py-10 text-muted-foreground">{t("No data")}</td></tr>
                ) : (
                  meetings.map((m) => (
                    <tr key={m.id}>
                      <td className="whitespace-nowrap text-sm font-semibold">{m.meeting_date}</td>
                      <td className="font-medium">{m.title}</td>
                      <td className="text-sm text-muted-foreground whitespace-nowrap">
                        {selectedProject?.project_code}
                      </td>
                      <td>
                        <span className={`badge ${meetingTypeBadge(m.meeting_type)}`}>
                          {m.meeting_type}
                        </span>
                      </td>
                      <td className="text-sm">{decisionsCountByMeeting.get(m.id) ?? 0}</td>
                      <td className="text-sm">{openActionItemsByMeeting.get(m.id) ?? 0}</td>
                      <td>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setLocation(`/meetings/${m.project_id}/${m.id}`)}
                        >
                          {t("Open Meeting")}
                        </Button>
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
                  <tr><td colSpan={3} className="text-center py-10"><div className="flex flex-col items-center gap-1 text-muted-foreground"><AlertOctagon className="w-6 h-6 text-destructive opacity-60" /><span className="text-sm">{t("Failed to load decisions")}</span></div></td></tr>
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
