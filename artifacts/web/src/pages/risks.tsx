import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { AlertTriangle, CircleAlert } from "lucide-react";
import {
  useListProjects,
  useListProjectRisks,
  useListProjectIssues,
  useUpdateProjectRisk,
  useAssignProjectRisk,
  useUnassignProjectRisk,
  useUpdateProjectIssue,
  useAssignProjectIssue,
  useUnassignProjectIssue,
} from "@workspace/api-client-react";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { PageTabs } from "@/components/page-tabs";
import { FilterSelect } from "@/components/filter-select";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { TableSkeletonRows } from "@/components/ui/table-skeleton";
import { OwnershipControl } from "@/components/ownership-control";
import { StatusTransitionControl } from "@/components/status-transition-control";
import { useToast } from "@/hooks/use-toast";
import { makeConflictAwareErrorHandler } from "@/lib/mutationFeedback";

// Risk Register — activates ProjectRisk/ProjectIssue (Sprint 2/3 workflow +
// ownership) for the first time in the frontend; this page previously had
// no real implementation at all (see git history — it was a
// RoadmapPlaceholder). Deliberately kept to a list view (no per-record
// detail drawer) — matches the scope of the other Sprint 6 ownership/
// workflow activations, not a new subsystem. Creating new risks/issues
// (the backend does support POST) is out of scope for this sprint, which
// activates existing daily workflows (assign/status), not new CRUD forms.

type Tab = "risks" | "issues";

const IMPACT_BADGE: Record<string, string> = { low: "badge-success", medium: "badge-warning", high: "badge-danger" };
const SEVERITY_BADGE: Record<string, string> = { low: "badge-success", medium: "badge-warning", high: "badge-danger" };

export default function Risks() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>("risks");
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);

  const { data: projects } = useListProjects({ limit: 60 });
  useEffect(() => {
    if (projects && projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  const risksKey = ["project-risks", selectedProjectId];
  const issuesKey = ["project-issues", selectedProjectId];

  const { data: risks, isLoading: risksLoading, isError: risksError } = useListProjectRisks(
    selectedProjectId ?? 0,
    undefined,
    { query: { enabled: !!selectedProjectId, queryKey: risksKey } }
  );
  const { data: issues, isLoading: issuesLoading, isError: issuesError } = useListProjectIssues(
    selectedProjectId ?? 0,
    undefined,
    { query: { enabled: !!selectedProjectId, queryKey: issuesKey } }
  );

  const onRiskError = makeConflictAwareErrorHandler(toast, qc, [risksKey]);
  const onRiskSuccess = (label: string) => () => {
    toast({ title: label, variant: "success" });
    qc.invalidateQueries({ queryKey: risksKey });
  };
  const updateRisk = useUpdateProjectRisk({ mutation: { onSuccess: onRiskSuccess("Risk updated"), onError: onRiskError } });
  const assignRisk = useAssignProjectRisk({ mutation: { onSuccess: onRiskSuccess("Owner updated"), onError: onRiskError } });
  const unassignRisk = useUnassignProjectRisk({ mutation: { onSuccess: onRiskSuccess("Unassigned"), onError: onRiskError } });

  const onIssueError = makeConflictAwareErrorHandler(toast, qc, [issuesKey]);
  const onIssueSuccess = (label: string) => () => {
    toast({ title: label, variant: "success" });
    qc.invalidateQueries({ queryKey: issuesKey });
  };
  const updateIssue = useUpdateProjectIssue({ mutation: { onSuccess: onIssueSuccess("Issue updated"), onError: onIssueError } });
  const assignIssue = useAssignProjectIssue({ mutation: { onSuccess: onIssueSuccess("Owner updated"), onError: onIssueError } });
  const unassignIssue = useUnassignProjectIssue({ mutation: { onSuccess: onIssueSuccess("Unassigned"), onError: onIssueError } });

  const selectedProject = projects?.find((p) => p.id === selectedProjectId);
  const isLoading = tab === "risks" ? risksLoading : issuesLoading;
  const isError = tab === "risks" ? risksError : issuesError;

  return (
    <WorkspaceLayout
      title={t("Risk Register")}
      subtitle={selectedProject ? `${selectedProject.project_code} — ${selectedProject.project_name}` : "Select a project to begin"}
      backLabel="Back to Operations"
      backHref="/operations"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Operations", href: "/operations" }, { label: t("Risk Register") }]}
      toolbar={
        <FilterSelect className="min-w-52" value={String(selectedProjectId ?? "")} onChange={(v) => setSelectedProjectId(Number(v))} testId="project-selector">
          <option value="" disabled>{t("Select Project")}</option>
          {projects?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.project_code} — {p.project_name}
            </option>
          ))}
        </FilterSelect>
      }
    >
      {!selectedProjectId ? (
        <div className="panel">
          <EmptyState icon={AlertTriangle} title={t("Select a project to view data")} />
        </div>
      ) : (
        <div className="space-y-4">
          <PageTabs<Tab>
            tabs={[
              { id: "risks", label: t("Risks"), count: risks?.length },
              { id: "issues", label: t("Issues"), count: issues?.length },
            ]}
            value={tab}
            onChange={setTab}
          />

          {isError && <ErrorState title={`Failed to load ${tab}`} />}

          {!isError && tab === "risks" && (
            <div className="panel overflow-hidden">
              <div className="overflow-x-auto">
                <table className="data-table" data-testid="risks-table">
                  <thead>
                    <tr>
                      <th>{t("Title")}</th>
                      <th>{t("Probability")}</th>
                      <th>{t("Impact")}</th>
                      <th>{t("Status")}</th>
                      <th>{t("Owner")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {risksLoading ? (
                      <TableSkeletonRows rows={6} cols={5} />
                    ) : !risks?.length ? (
                      <tr>
                        <td colSpan={5}>
                          <EmptyState icon={AlertTriangle} title="No risks logged" description="Risks for this project will appear here." />
                        </td>
                      </tr>
                    ) : (
                      risks.map((r) => (
                        <tr key={r.id}>
                          <td className="text-sm max-w-sm">
                            <p className="font-medium truncate">{r.title}</p>
                            {r.description && <p className="text-xs text-muted-foreground truncate">{r.description}</p>}
                          </td>
                          <td className="text-muted-foreground text-sm capitalize">{r.probability}</td>
                          <td><span className={`badge ${IMPACT_BADGE[r.impact ?? "medium"] ?? "badge-neutral"} capitalize`}>{r.impact ?? "medium"}</span></td>
                          <td>
                            <StatusTransitionControl
                              entity="project_risk"
                              entityLabel="risk"
                              currentStatus={r.status}
                              disabled={updateRisk.isPending}
                              onTransition={(target, closeOutValue) =>
                                updateRisk.mutate({
                                  projectId: selectedProjectId,
                                  riskId: r.id,
                                  data: { status: target, mitigation: closeOutValue, expected_updated_at: r.updated_at ?? undefined },
                                })
                              }
                            />
                          </td>
                          <td>
                            <OwnershipControl
                              projectId={selectedProjectId}
                              ownerId={r.owner_id}
                              ownerText={r.owner}
                              disabled={assignRisk.isPending || unassignRisk.isPending}
                              onAssign={(userId) =>
                                assignRisk.mutate({ projectId: selectedProjectId, riskId: r.id, data: { user_id: userId, expected_updated_at: r.updated_at ?? undefined } })
                              }
                              onUnassign={() => unassignRisk.mutate({ projectId: selectedProjectId, riskId: r.id, data: { expected_updated_at: r.updated_at ?? undefined } })}
                            />
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {!isError && tab === "issues" && (
            <div className="panel overflow-hidden">
              <div className="overflow-x-auto">
                <table className="data-table" data-testid="issues-table">
                  <thead>
                    <tr>
                      <th>{t("Title")}</th>
                      <th>{t("Severity")}</th>
                      <th>{t("Status")}</th>
                      <th>{t("Owner")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {issuesLoading ? (
                      <TableSkeletonRows rows={6} cols={4} />
                    ) : !issues?.length ? (
                      <tr>
                        <td colSpan={4}>
                          <EmptyState icon={CircleAlert} title="No issues logged" description="Issues for this project will appear here." />
                        </td>
                      </tr>
                    ) : (
                      issues.map((i) => (
                        <tr key={i.id}>
                          <td className="text-sm max-w-sm">
                            <p className="font-medium truncate">{i.title}</p>
                            {i.description && <p className="text-xs text-muted-foreground truncate">{i.description}</p>}
                          </td>
                          <td><span className={`badge ${SEVERITY_BADGE[i.severity ?? "medium"] ?? "badge-neutral"} capitalize`}>{i.severity ?? "medium"}</span></td>
                          <td>
                            <StatusTransitionControl
                              entity="project_issue"
                              entityLabel="issue"
                              currentStatus={i.status}
                              disabled={updateIssue.isPending}
                              onTransition={(target, closeOutValue) =>
                                updateIssue.mutate({
                                  projectId: selectedProjectId,
                                  issueId: i.id,
                                  data: { status: target, resolution: closeOutValue, expected_updated_at: i.updated_at ?? undefined },
                                })
                              }
                            />
                          </td>
                          <td>
                            <OwnershipControl
                              projectId={selectedProjectId}
                              ownerId={i.owner_id}
                              ownerText={i.owner}
                              disabled={assignIssue.isPending || unassignIssue.isPending}
                              onAssign={(userId) =>
                                assignIssue.mutate({ projectId: selectedProjectId, issueId: i.id, data: { user_id: userId, expected_updated_at: i.updated_at ?? undefined } })
                              }
                              onUnassign={() => unassignIssue.mutate({ projectId: selectedProjectId, issueId: i.id, data: { expected_updated_at: i.updated_at ?? undefined } })}
                            />
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </WorkspaceLayout>
  );
}
