import { useEffect, useState } from "react";
import { useLocation, useParams } from "wouter";
import { ArrowLeft, Sparkles, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import SiteReportAnalysisPanel, { AnalysisHeader, type SiteReportAnalysis } from "@/components/site-report-analysis-panel";
import { SiteReportStageProgress, useAnalysisStages, type Stage } from "@/components/site-report-stage-progress";
import { getToken } from "@/lib/auth";

// The backend enforces its own hard 60s wall-clock ceiling for /analyze
// (evidence gathering + risk score is sub-second; Hermes gets ~45s — see
// SITE_REPORT_HERMES_TIMEOUT_SECONDS — with a single bounded local JSON
// repair, never a second Hermes call, on validation failure). The backend
// always returns a real result within that window: either a completed
// analysis, or a "timed_out"/"unavailable" one with the deterministic
// evidence and risk score still shown. This client-side timeout is a
// pure safety net for a connection silently dropped by some intermediary
// mid-request — generous enough to never race the backend's own ceiling,
// but finite so the UI is never left waiting forever either way.
const ANALYZE_TIMEOUT_MS = 75_000;

type ReportEngineer = {
  id?: number | null;
  full_name?: string | null;
  email?: string | null;
  role_on_project?: string | null;
};

type ReportManpowerBySubcontractor = {
  subcontractor_id: number;
  subcontractor_name: string;
  workers: number;
  activity_count: number;
};

type SiteReportIntelligence = {
  report_id: number;
  project_id: number;
  project_code: string;
  project_name: string;
  engineer?: ReportEngineer | null;
  supervisor?: ReportEngineer | null;
  report_date: string;
  weather: string;
  temperature?: string | null;
  manpower: {
    total_workers: number;
    subcontractor_breakdown: ReportManpowerBySubcontractor[];
  };
  equipment: string[];
  completed_work: string[];
  work_in_progress: string[];
  materials_used: string[];
  site_issues: string[];
  delays: string[];
  blockers: string[];
  recommendations: string[];
  safety_observations: string[];
  quality_observations: string[];
  photos: Array<{ source_type: string; source_id: number; title: string; date?: string | null }>;
  attachments: Array<{ source_type: string; source_id: number; title: string; date?: string | null }>;
  document_references: Array<{ source_type: string; source_id: number; title: string; date?: string | null }>;
  raw_summary: string;
};

async function apiRequest<T>(path: string, method: "GET" | "POST", signal?: AbortSignal): Promise<T> {
  const token = getToken();
  const response = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    signal,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

function SectionCard({ title, items }: { title: string; items: string[] }) {
  return (
    <section className="rounded-xl border border-border/50 bg-card/70 p-4">
      <h3 className="mb-3 text-sm font-semibold text-foreground">{title}</h3>
      <ul className="space-y-2">
        {items.map((item, idx) => (
          <li key={`${title}-${idx}`} className="flex items-start gap-2 text-sm text-muted-foreground">
            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function AnalysisPrompt({ onAnalyze, analyzing }: { onAnalyze: () => void; analyzing: boolean }) {
  if (analyzing) {
    return (
      <div className="rounded-xl border border-dashed border-border p-8 text-center">
        <p className="text-sm text-muted-foreground">Analysis in progress — see the stages above.</p>
      </div>
    );
  }
  return (
    <div className="rounded-xl border border-dashed border-border p-8 text-center space-y-3">
      <Sparkles className="h-6 w-6 text-primary mx-auto" />
      <p className="text-sm font-medium text-foreground">Run AI analysis to see this section</p>
      <p className="text-xs text-muted-foreground max-w-sm mx-auto">
        Executive summary, findings, risk scoring, and recommendations are generated together in one AI reasoning pass.
      </p>
      <Button size="sm" onClick={onAnalyze} className="gap-1.5">
        <Sparkles className="h-3.5 w-3.5" />
        Analyze with AMAD AI
      </Button>
    </div>
  );
}

const REASONING_STATUS_PILL: Record<string, { label: string; className: string }> = {
  completed: { label: "AI analysis complete", className: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" },
  timed_out: { label: "AI reasoning timed out — evidence shown", className: "bg-amber-500/10 text-amber-600 dark:text-amber-400" },
  unavailable: { label: "AI reasoning unavailable — evidence shown", className: "bg-amber-500/10 text-amber-600 dark:text-amber-400" },
};

export default function SiteReportDetail() {
  const [, setLocation] = useLocation();
  const { projectId, reportId } = useParams<{ projectId: string; reportId: string }>();

  const projectIdNum = Number(projectId);
  const reportIdNum = Number(reportId);

  const [report, setReport] = useState<SiteReportIntelligence | null>(null);
  const [analysis, setAnalysis] = useState<SiteReportAnalysis | null>(null);
  const [loadingReport, setLoadingReport] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState("overview");
  const [stage, setStage] = useAnalysisStages(analyzing);

  useEffect(() => {
    let mounted = true;
    const loadReport = async () => {
      if (!projectIdNum || !reportIdNum) {
        setError("Invalid project or report ID.");
        setLoadingReport(false);
        return;
      }
      setLoadingReport(true);
      setError(null);
      try {
        const data = await apiRequest<SiteReportIntelligence>(
          `/api/v1/projects/${projectIdNum}/site-reports/${reportIdNum}/intelligence`, "GET",
        );
        if (mounted) setReport(data);
      } catch (err) {
        if (mounted) setError(err instanceof Error ? err.message : "Failed to load site report intelligence.");
      } finally {
        if (mounted) setLoadingReport(false);
      }
    };
    loadReport();
    return () => { mounted = false; };
  }, [projectIdNum, reportIdNum]);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    setError(null);

    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), ANALYZE_TIMEOUT_MS);

    try {
      const data = await apiRequest<SiteReportAnalysis>(
        `/api/v1/projects/${projectIdNum}/site-reports/${reportIdNum}/analyze`, "POST", controller.signal,
      );
      setStage("preparing");
      // Brief, honest pause — the response has arrived, this reflects the
      // real (near-instant) client-side render step, not a fake delay
      // standing in for backend work that already finished.
      await new Promise((resolve) => window.setTimeout(resolve, 350));
      setAnalysis(data);
      setStage("done");
      setTab("overview");
    } catch (err) {
      const isTimeout = err instanceof DOMException && err.name === "AbortError";
      setError(
        isTimeout
          ? "AI analysis is taking far longer than expected and was cancelled. Please try again — the report's evidence and risk score are unaffected."
          : err instanceof Error ? err.message : "Analysis failed.",
      );
    } finally {
      window.clearTimeout(timeoutId);
      setAnalyzing(false);
    }
  };

  if (loadingReport) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-5 w-48" />
        <Skeleton className="h-16 w-full rounded-xl" />
        <Skeleton className="h-96 w-full rounded-xl" />
      </div>
    );
  }

  if (!report) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" className="gap-2" onClick={() => setLocation("/site-reports")}>
          <ArrowLeft className="h-4 w-4" />
          Back to Site Reports
        </Button>
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          {error || "Site report not found."}
        </div>
      </div>
    );
  }

  const statusPill = analysis ? REASONING_STATUS_PILL[analysis.reasoning_status] : null;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <Button variant="ghost" className="mb-2 h-auto p-0 text-muted-foreground hover:text-foreground" onClick={() => setLocation("/site-reports")}>
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back to Site Reports
          </Button>
          <h1 className="text-2xl font-bold text-foreground">{report.project_name}</h1>
          <p className="text-sm text-muted-foreground">{report.project_code} - Site Report {report.report_date}</p>
        </div>

        <div className="flex flex-col items-end gap-2">
          {statusPill && (
            <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${statusPill.className}`}>
              {statusPill.label}
            </span>
          )}
          <Button size="sm" onClick={handleAnalyze} disabled={analyzing} className="gap-1.5">
            {analysis ? <RotateCcw className="h-3.5 w-3.5" /> : <Sparkles className="h-3.5 w-3.5" />}
            {analyzing ? "Analyzing..." : analysis ? "Re-analyze" : "Analyze with AMAD AI"}
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {analyzing && (
        <div className="rounded-xl border border-primary/30 bg-primary/[0.03] p-5">
          <SiteReportStageProgress stage={stage as Stage} />
        </div>
      )}

      {analysis && !analyzing && (
        <ErrorBoundary>
          <AnalysisHeader data={analysis} />
        </ErrorBoundary>
      )}

      <Tabs value={tab} onValueChange={setTab} className="space-y-4">
        <TabsList className="flex-wrap h-auto">
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="findings">AI Findings</TabsTrigger>
          <TabsTrigger value="evidence">Evidence</TabsTrigger>
          <TabsTrigger value="risks">Risks</TabsTrigger>
          <TabsTrigger value="recommendations">Recommendations</TabsTrigger>
          <TabsTrigger value="sources">Sources</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          {analysis ? (
            <ErrorBoundary><SiteReportAnalysisPanel data={analysis} section="overview" showHeader={false} /></ErrorBoundary>
          ) : (
            <div className="space-y-4">
              <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <div className="rounded-xl border border-border/50 bg-card/70 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Engineer</p>
                  <p className="mt-1 text-sm font-semibold text-foreground">{report.engineer?.full_name || "Not assigned"}</p>
                </div>
                <div className="rounded-xl border border-border/50 bg-card/70 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Weather</p>
                  <p className="mt-1 text-sm font-semibold text-foreground">{report.weather}</p>
                </div>
                <div className="rounded-xl border border-border/50 bg-card/70 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Total Workforce</p>
                  <p className="mt-1 text-sm font-semibold text-foreground">{report.manpower.total_workers}</p>
                </div>
              </section>
              <AnalysisPrompt onAnalyze={handleAnalyze} analyzing={analyzing} />
            </div>
          )}
        </TabsContent>

        <TabsContent value="findings">
          {analysis ? (
            <ErrorBoundary><SiteReportAnalysisPanel data={analysis} section="findings" showHeader={false} /></ErrorBoundary>
          ) : (
            <AnalysisPrompt onAnalyze={handleAnalyze} analyzing={analyzing} />
          )}
        </TabsContent>

        <TabsContent value="evidence">
          <div className="space-y-4">
            <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="rounded-xl border border-border/50 bg-card/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Project</p>
                <p className="mt-1 text-sm font-semibold text-foreground">{report.project_code} - {report.project_name}</p>
              </div>
              <div className="rounded-xl border border-border/50 bg-card/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Engineer</p>
                <p className="mt-1 text-sm font-semibold text-foreground">{report.engineer?.full_name || "Not assigned"}</p>
                {report.engineer?.email && <p className="text-xs text-muted-foreground">{report.engineer.email}</p>}
              </div>
              <div className="rounded-xl border border-border/50 bg-card/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Supervisor</p>
                <p className="mt-1 text-sm font-semibold text-foreground">{report.supervisor?.full_name || "Not assigned"}</p>
                {report.supervisor?.email && <p className="text-xs text-muted-foreground">{report.supervisor.email}</p>}
              </div>
              <div className="rounded-xl border border-border/50 bg-card/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Report Date</p>
                <p className="mt-1 text-sm font-semibold text-foreground">{report.report_date}</p>
              </div>
              <div className="rounded-xl border border-border/50 bg-card/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Weather</p>
                <p className="mt-1 text-sm font-semibold text-foreground">{report.weather}</p>
              </div>
              <div className="rounded-xl border border-border/50 bg-card/70 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Temperature</p>
                <p className="mt-1 text-sm font-semibold text-foreground">{report.temperature || "No temperature data stored"}</p>
              </div>
            </section>

            <section className="rounded-xl border border-border/50 bg-card/70 p-4">
              <h3 className="mb-3 text-sm font-semibold text-foreground">Manpower</h3>
              <p className="mb-3 text-sm font-semibold text-foreground">Total Workforce: {report.manpower.total_workers}</p>
              <div className="space-y-2">
                {report.manpower.subcontractor_breakdown.map((row) => (
                  <div key={row.subcontractor_id} className="flex items-center justify-between rounded-lg border border-border/40 bg-background/50 px-3 py-2">
                    <div>
                      <p className="text-sm font-medium text-foreground">{row.subcontractor_name}</p>
                      <p className="text-xs text-muted-foreground">{row.activity_count} activities</p>
                    </div>
                    <p className="text-sm font-semibold text-foreground">{row.workers} workers</p>
                  </div>
                ))}
              </div>
            </section>

            <SectionCard title="Equipment" items={report.equipment} />
            <SectionCard title="Completed Work" items={report.completed_work} />
            <SectionCard title="Work In Progress" items={report.work_in_progress} />
            <SectionCard title="Materials Used" items={report.materials_used} />
            <SectionCard title="Site Issues" items={report.site_issues} />
            <SectionCard title="Delays" items={report.delays} />
            <SectionCard title="Blockers" items={report.blockers} />
            <SectionCard title="Safety Observations" items={report.safety_observations} />
            <SectionCard title="Quality Observations" items={report.quality_observations} />

            <section className="rounded-xl border border-border/50 bg-card/70 p-4">
              <h3 className="mb-3 text-sm font-semibold text-foreground">Photos</h3>
              {report.photos.length === 0 ? (
                <p className="text-sm text-muted-foreground">No photo records stored for this report scope.</p>
              ) : (
                <ul className="space-y-2">
                  {report.photos.map((att) => (
                    <li key={`${att.source_type}-${att.source_id}`} className="rounded-lg border border-border/40 bg-background/50 p-3">
                      <p className="text-sm font-medium text-foreground">{att.title}</p>
                      <p className="text-xs text-muted-foreground">{att.source_type} #{att.source_id}{att.date ? ` - ${att.date}` : ""}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="rounded-xl border border-border/50 bg-card/70 p-4">
              <h3 className="mb-3 text-sm font-semibold text-foreground">Attachments</h3>
              {report.attachments.length === 0 ? (
                <p className="text-sm text-muted-foreground">No attachments linked to this report.</p>
              ) : (
                <ul className="space-y-2">
                  {report.attachments.map((att) => (
                    <li key={`${att.source_type}-${att.source_id}`} className="rounded-lg border border-border/40 bg-background/50 p-3">
                      <p className="text-sm font-medium text-foreground">{att.title}</p>
                      <p className="text-xs text-muted-foreground">{att.source_type} #{att.source_id}{att.date ? ` - ${att.date}` : ""}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="rounded-xl border border-border/50 bg-card/70 p-4">
              <h3 className="mb-3 text-sm font-semibold text-foreground">Document References</h3>
              {report.document_references.length === 0 ? (
                <p className="text-sm text-muted-foreground">No document references linked to this report.</p>
              ) : (
                <ul className="space-y-2">
                  {report.document_references.map((att) => (
                    <li key={`${att.source_type}-${att.source_id}-${att.title}`} className="rounded-lg border border-border/40 bg-background/50 p-3">
                      <p className="text-sm font-medium text-foreground">{att.title}</p>
                      <p className="text-xs text-muted-foreground">{att.source_type} #{att.source_id}{att.date ? ` - ${att.date}` : ""}</p>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        </TabsContent>

        <TabsContent value="risks">
          {analysis ? (
            <ErrorBoundary><SiteReportAnalysisPanel data={analysis} section="risks" showHeader={false} /></ErrorBoundary>
          ) : (
            <AnalysisPrompt onAnalyze={handleAnalyze} analyzing={analyzing} />
          )}
        </TabsContent>

        <TabsContent value="recommendations">
          {analysis ? (
            <ErrorBoundary><SiteReportAnalysisPanel data={analysis} section="recommendations" showHeader={false} /></ErrorBoundary>
          ) : (
            <AnalysisPrompt onAnalyze={handleAnalyze} analyzing={analyzing} />
          )}
        </TabsContent>

        <TabsContent value="sources">
          {analysis ? (
            <ErrorBoundary><SiteReportAnalysisPanel data={analysis} section="sources" showHeader={false} /></ErrorBoundary>
          ) : (
            <AnalysisPrompt onAnalyze={handleAnalyze} analyzing={analyzing} />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
