import { useEffect, useState } from "react";
import { useListProjects } from "@workspace/api-client-react";
import { Link } from "wouter";
import { ClipboardList, ChevronRight, ExternalLink } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { getToken } from "@/lib/auth";

type ReportCard = {
  report_id: number; project_id: number; project_name: string; report_date: string;
  engineer?: string | null; weather: string; work_progress: string;
  risk_indicator: string; safety_indicator: string; quality_indicator: string;
};

const RISK_TONE: Record<string, string> = {
  High: "badge-danger", Medium: "badge-warning", Low: "badge-success",
};

// Site Report Intelligence workspace — the AI-angle entry point into site
// reports: pick a project, see its recent reports with risk/safety/quality
// indicators (backend's own /site-reports/cards summary, unchanged), open
// any report into the redesigned detail page (staged AI progress + tabbed
// results). Full unfiltered list stays at /site-reports as before.
export default function SiteReportIntelligence() {
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [cards, setCards] = useState<ReportCard[] | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const { data: projects } = useListProjects({ limit: 60 });

  useEffect(() => {
    if (projects && projects.length > 0 && !selectedProjectId) setSelectedProjectId(projects[0].id);
  }, [projects, selectedProjectId]);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      if (!selectedProjectId) return;
      setIsLoading(true);
      try {
        const token = getToken();
        const resp = await fetch(`/api/v1/projects/${selectedProjectId}/site-reports/cards?limit=6`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        const data = resp.ok ? await resp.json() : [];
        if (mounted) setCards(data);
      } catch {
        if (mounted) setCards([]);
      } finally {
        if (mounted) setIsLoading(false);
      }
    };
    load();
    return () => { mounted = false; };
  }, [selectedProjectId]);

  const selectedProject = projects?.find((p) => p.id === selectedProjectId);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-lg font-semibold text-foreground">Site Report Intelligence</h2>
          <p className="text-sm text-muted-foreground">Evidence-grounded analysis, risk scoring, and AI reasoning per site report.</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={selectedProjectId ? String(selectedProjectId) : ""} onValueChange={(v) => setSelectedProjectId(Number(v))}>
            <SelectTrigger className="w-64 h-9"><SelectValue placeholder="Select project" /></SelectTrigger>
            <SelectContent>
              {projects?.map((p) => (
                <SelectItem key={p.id} value={String(p.id)}>{p.project_code} — {p.project_name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Link href="/site-reports" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline whitespace-nowrap">
            All reports <ExternalLink className="w-3 h-3" />
          </Link>
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2].map((i) => <Skeleton key={i} className="h-32 w-full rounded-xl" />)}
        </div>
      ) : !cards?.length ? (
        <EmptyState
          icon={ClipboardList}
          title="No site reports yet"
          description={selectedProject ? `${selectedProject.project_code} has no site reports yet.` : "Select a project to view its recent reports."}
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {cards.map((c) => (
            <Link
              key={c.report_id}
              href={`/projects/${c.project_id}/site-reports/${c.report_id}`}
              className="rounded-xl border border-border bg-card p-4 space-y-2 hover:border-primary/30 transition-colors group"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-semibold text-foreground">{c.report_date}</p>
                <ChevronRight className="w-4 h-4 text-muted-foreground shrink-0 group-hover:translate-x-0.5 transition-transform" />
              </div>
              <p className="text-xs text-muted-foreground">{c.engineer || "Engineer not assigned"} &middot; {c.weather}</p>
              <div className="flex flex-wrap gap-1.5 pt-1">
                <span className={`badge ${RISK_TONE[c.risk_indicator] ?? "badge-neutral"}`}>Risk: {c.risk_indicator}</span>
                <span className={`badge ${RISK_TONE[c.safety_indicator] ?? "badge-neutral"}`}>Safety: {c.safety_indicator}</span>
                <span className={`badge ${RISK_TONE[c.quality_indicator] ?? "badge-neutral"}`}>Quality: {c.quality_indicator}</span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
