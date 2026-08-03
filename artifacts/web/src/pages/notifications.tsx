import { useMemo, useState } from "react";
import { Link } from "wouter";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { BellRing, CheckCheck } from "lucide-react";
import {
  useListNotifications,
  useListProjects,
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
} from "@workspace/api-client-react";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { FilterChip } from "@/components/filter-chip";
import { FilterSelect } from "@/components/filter-select";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { frontendLinkFor } from "@/lib/entityLinks";

// The actual event vocabulary this backend emits (app/ai/notification_service.py
// EVENT_* constants + app/ai/approval_engine.py) — not invented categories.
const EVENT_TYPE_LABELS: Record<string, string> = {
  assigned: "Assigned",
  reassigned: "Reassigned",
  unassigned: "Unassigned",
  status_changed: "Status changed",
  item_completed: "Completed",
  item_reopened: "Reopened",
  due_date_changed: "Due date changed",
  purchase_request_approved: "Purchase request approved",
  purchase_request_rejected: "Purchase request rejected",
  purchase_request_returned: "Purchase request returned",
  approval_requested: "Approval requested",
  approval_reviewer_assigned: "Reviewer assigned",
  approval_reviewer_reassigned: "Reviewer reassigned",
  approval_review_started: "Review started",
  approval_approved: "Approval approved",
  approval_rejected: "Approval rejected",
  approval_returned: "Approval returned",
  approval_cancelled: "Approval cancelled",
};

const SEVERITIES = ["info", "warning", "critical"] as const;

function severityBadgeClass(severity: string) {
  const m: Record<string, string> = { info: "badge-info", warning: "badge-warning", critical: "badge-danger" };
  return m[severity] ?? "badge-neutral";
}

function timeAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

const PAGE_LIMIT = 50;

export default function Notifications() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const qc = useQueryClient();

  const [unreadOnly, setUnreadOnly] = useState(false);
  const [severity, setSeverity] = useState<string>("all");
  const [eventType, setEventType] = useState<string>("all");
  const [projectId, setProjectId] = useState<string>("all");

  const { data: projects } = useListProjects({ limit: 200 });

  const listQueryKey = useMemo(
    () => ["notifications-list", unreadOnly, severity, eventType, projectId] as const,
    [unreadOnly, severity, eventType, projectId]
  );

  const { data: notifications, isLoading, isError } = useListNotifications(
    {
      unread_only: unreadOnly,
      severity: severity === "all" ? undefined : severity,
      event_type: eventType === "all" ? undefined : eventType,
      project_id: projectId === "all" ? undefined : Number(projectId),
      limit: PAGE_LIMIT,
    },
    { query: { queryKey: listQueryKey } }
  );

  const invalidateNotifications = () => {
    qc.invalidateQueries({ queryKey: ["notifications-list"] });
    // Sidebar unread badge (components/layout.tsx) uses this same key.
    qc.invalidateQueries({ queryKey: ["notifications-summary-badge"] });
  };

  const markRead = useMarkNotificationRead({
    mutation: {
      onSuccess: invalidateNotifications,
      onError: (err: Error) => toast({ title: "Could not mark as read", description: err.message, variant: "destructive" }),
    },
  });

  const markAllRead = useMarkAllNotificationsRead({
    mutation: {
      onSuccess: (result) => {
        invalidateNotifications();
        toast({ title: "All caught up", description: `${result.updated_count} notification(s) marked read.`, variant: "success" });
      },
      onError: (err: Error) => toast({ title: "Could not mark all as read", description: err.message, variant: "destructive" }),
    },
  });

  const unreadCount = notifications?.filter((n) => !n.is_read).length ?? 0;

  return (
    <WorkspaceLayout
      title={t("Notifications")}
      subtitle="Assignments, status changes, and approval decisions that involve you"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Notifications" }]}
      toolbar={
        <Button
          variant="outline"
          size="sm"
          onClick={() => markAllRead.mutate()}
          disabled={markAllRead.isPending || unreadCount === 0}
        >
          <CheckCheck className="w-4 h-4 me-1.5" />
          {t("Mark all read")}
        </Button>
      }
    >
      <div className="flex flex-wrap items-center gap-2">
        <FilterChip active={unreadOnly} onClick={() => setUnreadOnly((v) => !v)}>
          {t("Unread only")}
        </FilterChip>
        <span className="w-px h-5 bg-border mx-1" />
        {SEVERITIES.map((s) => (
          <FilterChip key={s} active={severity === s} onClick={() => setSeverity(severity === s ? "all" : s)} tone={s === "critical" ? "amber" : "default"}>
            {t(s[0].toUpperCase() + s.slice(1))}
          </FilterChip>
        ))}
        <FilterSelect value={eventType} onChange={setEventType} ariaLabel="Event type">
          <option value="all">{t("All event types")}</option>
          {Object.entries(EVENT_TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {t(label)}
            </option>
          ))}
        </FilterSelect>
        <FilterSelect value={projectId} onChange={setProjectId} ariaLabel="Project" className="ms-auto">
          <option value="all">{t("All projects")}</option>
          {(projects ?? []).map((p) => (
            <option key={p.id} value={p.id}>
              {p.project_code}
            </option>
          ))}
        </FilterSelect>
      </div>

      {isError && <ErrorState title="Failed to load notifications" />}

      {!isError && (
        <div className="panel divide-y divide-border">
          {isLoading ? (
            <div className="p-4 space-y-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          ) : !notifications?.length ? (
            <EmptyState
              icon={BellRing}
              title={unreadOnly ? "No unread notifications" : "No notifications yet"}
              description="You'll see assignments, status changes, and approval decisions here as they happen."
            />
          ) : (
            notifications.map((n) => {
              const href = frontendLinkFor(n.entity_type, n.entity_id);
              return (
                <div
                  key={n.id}
                  className={`flex items-start gap-3 p-4 ${!n.is_read ? "bg-primary/[0.03]" : ""}`}
                  data-testid={`notification-row-${n.id}`}
                >
                  <span
                    className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${!n.is_read ? "bg-primary" : "bg-transparent"}`}
                    aria-hidden="true"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Link
                        href={href}
                        className={`text-sm hover:underline ${!n.is_read ? "font-semibold text-foreground" : "text-foreground/80"}`}
                        onClick={() => {
                          if (!n.is_read) markRead.mutate({ notificationId: n.id });
                        }}
                      >
                        {n.title}
                      </Link>
                      <span className={`badge ${severityBadgeClass(n.severity)}`}>{n.severity}</span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">{n.message}</p>
                    <p className="text-[11px] text-muted-foreground/70 mt-1">{timeAgo(n.created_at)}</p>
                  </div>
                  {!n.is_read && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="shrink-0"
                      onClick={() => markRead.mutate({ notificationId: n.id })}
                      disabled={markRead.isPending}
                    >
                      {t("Mark read")}
                    </Button>
                  )}
                </div>
              );
            })
          )}
        </div>
      )}
    </WorkspaceLayout>
  );
}
