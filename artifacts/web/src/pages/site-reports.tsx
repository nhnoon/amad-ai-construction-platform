import { useState, useEffect } from "react";
import { useListProjects, useListProjectSiteReports } from "@workspace/api-client-react";
import { useTranslation } from "react-i18next";
import { Skeleton } from "@/components/ui/skeleton";
import { CloudSun, AlertOctagon } from "lucide-react";

const WEATHER_BADGE: Record<string, string> = {
  Clear:        "badge-success",
  Windy:        "badge-warning",
  Hot:          "badge-warning",
  Humid:        "badge-info",
  Dusty:        "badge-warning",
  "Light Rain": "badge-info",
};

export default function SiteReports() {
  const { t } = useTranslation();
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);

  const { data: projects } = useListProjects({ limit: 60 });

  useEffect(() => {
    if (projects && projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  const { data: reports, isLoading, isError } = useListProjectSiteReports(
    selectedProjectId ?? 0,
    { limit: 50 },
    { query: { enabled: !!selectedProjectId, queryKey: ["site-reports", selectedProjectId] } }
  );

  const selectedProject = projects?.find((p) => p.id === selectedProjectId);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">{t("Site Reports")}</h1>
          <p className="page-subtitle">
            {selectedProject
              ? `${selectedProject.project_code} — ${selectedProject.project_name}`
              : "Select a project to begin"}
            {reports ? ` · ${reports.length} reports` : ""}
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

      {!selectedProjectId ? (
        <div className="panel panel-body flex flex-col items-center justify-center h-48 text-muted-foreground gap-3">
          <CloudSun className="w-10 h-10 opacity-30" />
          <p className="text-sm">{t("Select a project to view data")}</p>
        </div>
      ) : (
        <div className="panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table" data-testid="site-reports-table">
              <thead>
                <tr>
                  <th>{t("Report Date")}</th>
                  <th>{t("Weather")}</th>
                  <th className="min-w-[320px]">{t("Summary")}</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <tr><td colSpan={3} className="text-center py-10 text-muted-foreground">{t("Loading...")}</td></tr>
                ) : isError ? (
                  <tr><td colSpan={3} className="text-center py-10"><div className="flex flex-col items-center gap-1 text-muted-foreground"><AlertOctagon className="w-6 h-6 text-destructive opacity-60" /><span className="text-sm">Failed to load site reports</span></div></td></tr>
                ) : !reports?.length ? (
                  <tr><td colSpan={3} className="text-center py-10 text-muted-foreground">{t("No data")}</td></tr>
                ) : (
                  reports.map((r) => (
                    <tr key={r.id}>
                      <td className="font-semibold text-sm whitespace-nowrap">{r.report_date}</td>
                      <td>
                        <span className={`badge ${WEATHER_BADGE[r.weather] ?? "badge-neutral"}`}>
                          {r.weather}
                        </span>
                      </td>
                      <td className="text-muted-foreground text-sm max-w-md">
                        {r.summary}
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
  );
}
