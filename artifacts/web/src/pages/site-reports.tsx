import { useState, useEffect } from "react";
import { useListProjects } from "@workspace/api-client-react";
import { Link } from "wouter";
import { useTranslation } from "react-i18next";
import { CloudSun, AlertOctagon, ChevronRight, FileStack } from "lucide-react";
import { getToken } from "@/lib/auth";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { EmptyState } from "@/components/ui/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { FilterSelect } from "@/components/filter-select";

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
  const [cards, setCards] = useState<Array<{
    report_id: number;
    project_id: number;
    project_name: string;
    report_date: string;
    engineer?: string | null;
    weather: string;
    work_progress: string;
    risk_indicator: string;
    safety_indicator: string;
    quality_indicator: string;
  }> | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);

  const { data: projects } = useListProjects({ limit: 60 });

  useEffect(() => {
    if (projects && projects.length > 0 && !selectedProjectId) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  useEffect(() => {
    let mounted = true;
    const loadCards = async () => {
      if (!selectedProjectId) return;
      setIsLoading(true);
      setIsError(false);
      try {
        const token = getToken();
        const response = await fetch(`/api/v1/projects/${selectedProjectId}/site-reports/cards?limit=50`, {
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });
        if (!response.ok) {
          throw new Error("Failed to load report cards");
        }
        const data = await response.json();
        if (mounted) {
          setCards(data);
        }
      } catch {
        if (mounted) {
          setIsError(true);
          setCards([]);
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    loadCards();
    return () => {
      mounted = false;
    };
  }, [selectedProjectId]);

  const selectedProject = projects?.find((p) => p.id === selectedProjectId);

  return (
    <WorkspaceLayout
        title={t("Site Reports")}
        subtitle={`${
          selectedProject
            ? `${selectedProject.project_code} — ${selectedProject.project_name}`
            : "Select a project to begin"
        }${cards ? ` · ${cards.length} reports` : ""}`}
        backLabel="Back to Operations"
        backHref="/operations"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Operations", href: "/operations" },
          { label: "Site Reports" },
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

      {!selectedProjectId ? (
        <div className="panel">
          <EmptyState icon={CloudSun} title={t("Select a project to view data")} />
        </div>
      ) : (
        <div className="panel overflow-hidden">
          <div className="grid grid-cols-1 gap-4 p-4 md:grid-cols-2 xl:grid-cols-3" data-testid="site-reports-cards">
            {isLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-44 w-full rounded-xl" />
              ))
            ) : isError ? (
              <div className="col-span-full text-center py-10">
                <div className="flex flex-col items-center gap-1 text-muted-foreground">
                  <AlertOctagon className="w-6 h-6 text-destructive opacity-60" />
                  <span className="text-sm">Failed to load site reports</span>
                </div>
              </div>
            ) : !cards?.length ? (
              <div className="col-span-full">
                <EmptyState icon={FileStack} title="No site reports yet" description="Site reports for this project will appear here once submitted." />
              </div>
            ) : (
              cards.map((card) => (
                <article key={card.report_id} className="rounded-xl border border-border/50 bg-card/70 p-4">
                  <div className="mb-3 flex items-center justify-between gap-2">
                    <p className="text-sm font-semibold text-foreground">{card.project_name}</p>
                    <span className={`badge ${WEATHER_BADGE[card.weather] ?? "badge-neutral"}`}>{card.weather}</span>
                  </div>

                  <div className="space-y-2 text-xs text-muted-foreground">
                    <p><span className="font-semibold text-foreground">Report Date:</span> {card.report_date}</p>
                    <p><span className="font-semibold text-foreground">Engineer:</span> {card.engineer || "Not assigned"}</p>
                    <p><span className="font-semibold text-foreground">Work Progress:</span> {card.work_progress}</p>
                    <p><span className="font-semibold text-foreground">Risk Indicator:</span> {card.risk_indicator}</p>
                    <p><span className="font-semibold text-foreground">Safety Indicator:</span> {card.safety_indicator}</p>
                    <p><span className="font-semibold text-foreground">Quality Indicator:</span> {card.quality_indicator}</p>
                  </div>

                  <div className="mt-4">
                    <Link
                      href={`/projects/${card.project_id}/site-reports/${card.report_id}`}
                      className="inline-flex items-center gap-1 text-sm font-semibold text-primary hover:underline"
                    >
                      Open Report
                      <ChevronRight className="w-3.5 h-3.5" />
                    </Link>
                  </div>
                </article>
              ))
            )}
          </div>
        </div>
      )}
    </WorkspaceLayout>
  );
}
