import { useState, useEffect } from "react";
import {
  useListProjects,
  useListProjectSafetyEvents,
  useListProjectNcrs,
} from "@workspace/api-client-react";
import { useTranslation } from "react-i18next";
import { ShieldAlert, AlertOctagon, AlertTriangle, ClipboardCheck } from "lucide-react";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { PageTabs } from "@/components/page-tabs";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeletonRows } from "@/components/ui/table-skeleton";
import { FilterSelect } from "@/components/filter-select";

type Tab = "events" | "ncrs";

function severityBadge(severity: string) {
  const m: Record<string, string> = {
    High:   "badge-danger",
    Medium: "badge-warning",
    Low:    "badge-success",
  };
  return m[severity] ?? "badge-neutral";
}

function ncrStatusBadge(status: string) {
  const m: Record<string, string> = {
    Open:                        "badge-danger",
    Closed:                      "badge-success",
    "Under Corrective Action":   "badge-warning",
    "In Progress":               "badge-warning",
  };
  return m[status] ?? "badge-neutral";
}

export default function Safety() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>("events");
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);

  const { data: projects } = useListProjects({ limit: 60 });

  useEffect(() => {
    if (projects && projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  const { data: events, isLoading: eventsLoading, isError: eventsError } = useListProjectSafetyEvents(
    selectedProjectId ?? 0,
    { limit: 50 },
    { query: { enabled: !!selectedProjectId, queryKey: ["safety-events", selectedProjectId] } }
  );

  const { data: ncrs, isLoading: ncrsLoading, isError: ncrsError } = useListProjectNcrs(
    selectedProjectId ?? 0,
    { limit: 50 },
    { query: { enabled: !!selectedProjectId, queryKey: ["ncrs", selectedProjectId] } }
  );

  const selectedProject = projects?.find((p) => p.id === selectedProjectId);
  const highCount = events?.filter((e) => e.severity === "High").length ?? 0;
  const openNcrs = ncrs?.filter((n) => n.status === "Open").length ?? 0;

  return (
    <WorkspaceLayout
        title={t("Safety & NCR")}
        subtitle={`${selectedProject ? `${selectedProject.project_code} — ${selectedProject.project_name}` : "Select a project"}${events ? ` · ${events.length} ${t("Safety Events")}` : ""}${ncrs ? ` · ${ncrs.length} NCRs` : ""}`}
        backLabel="Back to Operations"
        backHref="/operations"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Operations", href: "/operations" },
          { label: t("Safety & NCR") },
        ]}
        toolbar={
          <FilterSelect
            className="min-w-52"
            value={String(selectedProjectId ?? "")}
            onChange={(v) => setSelectedProjectId(Number(v))}
            testId="project-selector"
          >
            <option value="" disabled>{t("Select Project")}</option>
            {projects?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.project_code} — {p.project_name}
              </option>
            ))}
          </FilterSelect>
        }
      >

      {/* Alert banners */}
      {highCount > 0 && (
        <div className="rounded-xl border border-red-200 bg-red-50 dark:border-red-900/30 dark:bg-red-900/10 px-5 py-3 flex items-center gap-3">
          <ShieldAlert className="w-4 h-4 text-red-500 shrink-0" />
          <p className="text-sm font-semibold text-red-700 dark:text-red-400">
            {highCount} high-severity safety event{highCount !== 1 ? "s" : ""} on this project
          </p>
        </div>
      )}
      {openNcrs > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 dark:border-amber-900/30 dark:bg-amber-900/10 px-5 py-3 flex items-center gap-3">
          <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0" />
          <p className="text-sm font-semibold text-amber-700 dark:text-amber-400">
            {openNcrs} open NCR{openNcrs !== 1 ? "s" : ""} requiring resolution
          </p>
        </div>
      )}

      <PageTabs<Tab>
        tabs={[
          { id: "events", label: t("Safety Events"), count: events?.length },
          { id: "ncrs", label: t("NCRs"), count: ncrs?.length },
        ]}
        value={tab}
        onChange={setTab}
      />

      {!selectedProjectId ? (
        <div className="panel">
          <EmptyState icon={ShieldAlert} title={t("Select a project to view data")} />
        </div>
      ) : tab === "events" ? (
        <div className="panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table" data-testid="safety-events-table">
              <thead>
                <tr>
                  <th>{t("Issue Date")}</th>
                  <th>{t("Severity")}</th>
                  <th className="min-w-[220px]">{t("Description")}</th>
                  <th className="min-w-[220px]">{t("Corrective Action")}</th>
                </tr>
              </thead>
              <tbody>
                {eventsLoading ? (
                  <TableSkeletonRows rows={5} cols={4} />
                ) : eventsError ? (
                  <tr><td colSpan={4} className="text-center py-10"><div className="flex flex-col items-center gap-1 text-muted-foreground"><AlertOctagon className="w-6 h-6 text-destructive opacity-60" /><span className="text-sm">Failed to load safety events</span></div></td></tr>
                ) : !events?.length ? (
                  <tr>
                    <td colSpan={4}>
                      <EmptyState icon={ShieldAlert} title="No safety events logged" description="Safety events for this project will appear here." />
                    </td>
                  </tr>
                ) : (
                  events.map((e) => (
                    <tr key={e.id}>
                      <td className="whitespace-nowrap text-sm font-semibold">{e.event_date}</td>
                      <td>
                        <span className={`badge ${severityBadge(e.severity)}`}>{e.severity}</span>
                      </td>
                      <td className="text-sm text-muted-foreground max-w-xs">{e.description}</td>
                      <td className="text-sm text-muted-foreground max-w-xs">{e.corrective_action}</td>
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
            <table className="data-table" data-testid="ncrs-table">
              <thead>
                <tr>
                  <th>{t("Issue Date")}</th>
                  <th>{t("Type")}</th>
                  <th>{t("Status")}</th>
                  <th className="min-w-[220px]">{t("Description")}</th>
                  <th className="min-w-[180px]">{t("Root Cause")}</th>
                </tr>
              </thead>
              <tbody>
                {ncrsLoading ? (
                  <TableSkeletonRows rows={5} cols={5} />
                ) : ncrsError ? (
                  <tr><td colSpan={5} className="text-center py-10"><div className="flex flex-col items-center gap-1 text-muted-foreground"><AlertOctagon className="w-6 h-6 text-destructive opacity-60" /><span className="text-sm">Failed to load NCRs</span></div></td></tr>
                ) : !ncrs?.length ? (
                  <tr>
                    <td colSpan={5}>
                      <EmptyState icon={ClipboardCheck} title="No NCRs logged" description="Non-conformance reports for this project will appear here." />
                    </td>
                  </tr>
                ) : (
                  ncrs.map((n) => (
                    <tr key={n.id}>
                      <td className="whitespace-nowrap text-sm font-semibold">{n.issue_date}</td>
                      <td className="text-sm">{n.ncr_type}</td>
                      <td>
                        <span className={`badge ${ncrStatusBadge(n.status)}`}>{n.status}</span>
                      </td>
                      <td className="text-sm text-muted-foreground max-w-xs">{n.description}</td>
                      <td className="text-sm text-muted-foreground max-w-xs">{n.root_cause}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </WorkspaceLayout>
  );
}
