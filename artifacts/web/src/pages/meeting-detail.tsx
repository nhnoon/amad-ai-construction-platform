import { useParams } from "wouter";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Users, ListChecks, CalendarX } from "lucide-react";
import {
  useListProjectMeetings,
  useListProjectDecisions,
  useListProjects,
  useListActionItems,
  useUpdateActionItem,
  useAssignActionItem,
  useUnassignActionItem,
} from "@workspace/api-client-react";
import { BackButton } from "@/components/back-button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { useRegisterCurrentEntity } from "@/context/CurrentEntityContext";
import { CurrentlyAnalyzing } from "@/components/CurrentlyAnalyzing";
import { AIActionPanel } from "@/components/AIActionPanel";
import { OwnershipControl } from "@/components/ownership-control";
import { StatusTransitionControl } from "@/components/status-transition-control";
import { useToast } from "@/hooks/use-toast";
import { makeConflictAwareErrorHandler } from "@/lib/mutationFeedback";

function meetingTypeBadge(type: string) {
  const m: Record<string, string> = {
    Weekly:     "badge-info",
    Technical:  "badge-purple",
    Safety:     "badge-warning",
    Commercial: "badge-gold",
  };
  return m[type] ?? "badge-neutral";
}

export default function MeetingDetail() {
  const { t, i18n } = useTranslation();
  const { toast } = useToast();
  const qc = useQueryClient();
  const isRTL = i18n.language?.startsWith("ar");
  const { projectId, meetingId } = useParams<{ projectId: string; meetingId: string }>();
  const projectIdNum = Number(projectId);
  const meetingIdNum = Number(meetingId);
  // Exact phrase required by the Meeting Agent spec — kept literal (not
  // routed through the shared i18n dictionary) so it never drifts from the
  // identical string the backend's deterministic fallback already returns.
  const unavailable = isRTL ? "غير متاح من قاعدة البيانات الحالية" : "Unavailable from current database.";

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

  // Sprint 6: switched from the hand-rolled lib/meetingsClient.ts fetch to
  // the typed generated hook — needed to get owner_id/updated_at (Sprint
  // 2/3 fields the old hand-written MeetingActionItem type predates),
  // which OwnershipControl/StatusTransitionControl require below.
  const actionItemsKey = ["action-items", projectIdNum, meetingIdNum];
  const { data: actionItems } = useListActionItems(
    projectIdNum,
    { meeting_id: meetingIdNum },
    { query: { enabled: !!projectIdNum && !!meetingIdNum, queryKey: actionItemsKey } }
  );

  const onActionItemError = makeConflictAwareErrorHandler(toast, qc, [actionItemsKey]);
  const onActionItemSuccess = (label: string) => () => {
    toast({ title: label, variant: "success" });
    qc.invalidateQueries({ queryKey: actionItemsKey });
  };
  const updateActionItem = useUpdateActionItem({ mutation: { onSuccess: onActionItemSuccess("Action item updated"), onError: onActionItemError } });
  const assignActionItem = useAssignActionItem({ mutation: { onSuccess: onActionItemSuccess("Owner updated"), onError: onActionItemError } });
  const unassignActionItem = useUnassignActionItem({ mutation: { onSuccess: onActionItemSuccess("Unassigned"), onError: onActionItemError } });

  useRegisterCurrentEntity(
    meeting ? { kind: "meeting", code: `MTG-${meeting.id}`, label: meeting.title, projectId: projectIdNum } : null,
  );

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
    <WorkspaceLayout
        title={meeting.title}
        subtitle={`${meeting.meeting_date}${project ? ` · ${project.project_code} — ${project.project_name}` : ""}`}
        backLabel="Back to Meetings"
        backHref="/meetings"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Meetings", href: "/meetings" },
          { label: meeting.title },
        ]}
        badge={<span className={`badge ${meetingTypeBadge(meeting.meeting_type)}`}>{meeting.meeting_type}</span>}
      >

      <CurrentlyAnalyzing />

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
                    {t("Due")}: {a.due_date || unavailable}
                  </p>
                  <div className="mt-2 pt-2 border-t border-border/50 flex items-center justify-between gap-2">
                    <StatusTransitionControl
                      entity="action_item"
                      entityLabel="action item"
                      currentStatus={a.status}
                      disabled={updateActionItem.isPending}
                      onTransition={(target) =>
                        updateActionItem.mutate({
                          projectId: projectIdNum,
                          actionItemId: a.id,
                          data: { status: target, expected_updated_at: a.updated_at ?? undefined },
                        })
                      }
                    />
                    <OwnershipControl
                      projectId={projectIdNum}
                      ownerId={a.owner_id}
                      ownerText={a.owner}
                      disabled={assignActionItem.isPending || unassignActionItem.isPending}
                      onAssign={(userId) =>
                        assignActionItem.mutate({ projectId: projectIdNum, actionItemId: a.id, data: { user_id: userId, expected_updated_at: a.updated_at ?? undefined } })
                      }
                      onUnassign={() =>
                        unassignActionItem.mutate({ projectId: projectIdNum, actionItemId: a.id, data: { expected_updated_at: a.updated_at ?? undefined } })
                      }
                    />
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Meeting Agent — AI Action Panel (Phase 2 §3) */}
      <div className="panel">
        <div className="panel-body">
          <AIActionPanel entityKind="meeting" meetingId={meetingIdNum} projectId={projectIdNum} meetingTitle={meeting.title} />
        </div>
      </div>
    </WorkspaceLayout>
  );
}
