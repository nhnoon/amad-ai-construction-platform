import { useState, useEffect } from "react";
import {
  useListProjects,
  useListProjectSafetyEvents,
  useListProjectNcrs,
} from "@workspace/api-client-react";
import { useTranslation } from "react-i18next";
import { ShieldAlert, AlertOctagon } from "lucide-react";

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
    <div className="space-y-6">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("Safety & NCR")}</h1>
          <p className="page-subtitle">
            {selectedProject
              ? `${selectedProject.project_code} — ${selectedProject.project_name}`
              : "Select a project"}
            {events || ncrs ? (
              <>
                {events ? ` · ${events.length} ${t("Safety Events")}` : ""}
                {ncrs ? ` · ${ncrs.length} NCRs` : ""}
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
          <span className="text-amber-500 shrink-0">⚠</span>
          <p className="text-sm font-semibold text-amber-700 dark:text-amber-400">
            {openNcrs} open NCR{openNcrs !== 1 ? "s" : ""} requiring resolution
          </p>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-0 border-b border-border">
        {(["events", "ncrs"] as Tab[]).map((id) => (
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
            {id === "events" ? t("Safety Events") : t("NCRs")}
            <span className="ms-2 text-xs text-muted-foreground">
              {id === "events" ? (events?.length ?? "…") : (ncrs?.length ?? "…")}
            </span>
          </button>
        ))}
      </div>

      {!selectedProjectId ? (
        <div className="panel panel-body flex flex-col items-center justify-center h-48 text-muted-foreground gap-3">
          <ShieldAlert className="w-10 h-10 opacity-30" />
          <p className="text-sm">{t("Select a project to view data")}</p>
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
                  <tr><td colSpan={4} className="text-center py-10 text-muted-foreground">{t("Loading...")}</td></tr>
                ) : eventsError ? (
                  <tr><td colSpan={4} className="text-center py-10"><div className="flex flex-col items-center gap-1 text-muted-foreground"><AlertOctagon className="w-6 h-6 text-destructive opacity-60" /><span className="text-sm">Failed to load safety events</span></div></td></tr>
                ) : !events?.length ? (
                  <tr><td colSpan={4} className="text-center py-10 text-muted-foreground">{t("No data")}</td></tr>
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
                  <tr><td colSpan={5} className="text-center py-10 text-muted-foreground">{t("Loading...")}</td></tr>
                ) : ncrsError ? (
                  <tr><td colSpan={5} className="text-center py-10"><div className="flex flex-col items-center gap-1 text-muted-foreground"><AlertOctagon className="w-6 h-6 text-destructive opacity-60" /><span className="text-sm">Failed to load NCRs</span></div></td></tr>
                ) : !ncrs?.length ? (
                  <tr><td colSpan={5} className="text-center py-10 text-muted-foreground">{t("No data")}</td></tr>
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
    </div>
  );
}
