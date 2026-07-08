import { useGetProject, useGetProjectHealth } from "@workspace/api-client-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useParams, Link } from "wouter";
import { useTranslation } from "react-i18next";
import {
  ArrowLeft, MapPin, Building2, Calendar, DollarSign, Hash, Tag, AlertOctagon,
  HeartPulse,
} from "lucide-react";

const STATUS_BADGE: Record<string, string> = {
  Active:    "badge-success",
  Delayed:   "badge-danger",
  Completed: "badge-info",
  Suspended: "badge-neutral",
  Planning:  "badge-purple",
  "On Hold": "badge-warning",
};

const LEVEL_CONFIG: Record<string, { color: string; bg: string; border: string; label: string }> = {
  "Excellent": {
    color: "#16a34a", bg: "rgba(22,163,74,0.08)", border: "rgba(22,163,74,0.25)", label: "Excellent",
  },
  "Good": {
    color: "#2563eb", bg: "rgba(37,99,235,0.08)", border: "rgba(37,99,235,0.25)", label: "Good",
  },
  "At Risk": {
    color: "#d97706", bg: "rgba(217,119,6,0.08)", border: "rgba(217,119,6,0.25)", label: "At Risk",
  },
  "Critical": {
    color: "#dc2626", bg: "rgba(220,38,38,0.08)", border: "rgba(220,38,38,0.25)", label: "Critical",
  },
};

function DetailRow({
  icon: Icon, label, value,
}: {
  icon: React.ElementType;
  label: string;
  value?: string | number | null;
}) {
  if (!value && value !== 0) return null;
  return (
    <div className="flex items-start gap-3 py-3 border-b border-border last:border-0">
      <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center shrink-0 mt-0.5">
        <Icon className="w-4 h-4 text-muted-foreground" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-muted-foreground uppercase tracking-wide font-medium mb-0.5">
          {label}
        </p>
        <p className="text-sm font-semibold text-foreground leading-snug">{value}</p>
      </div>
    </div>
  );
}

function formatBudget(v?: number | null) {
  if (v == null) return null;
  if (v >= 1_000_000_000) return `SAR ${(v / 1_000_000_000).toFixed(2)}B`;
  if (v >= 1_000_000) return `SAR ${(v / 1_000_000).toFixed(1)}M`;
  return `SAR ${v.toLocaleString()}`;
}

function HealthScorePanel({ projectId }: { projectId: number }) {
  const { data: health, isLoading } = useGetProjectHealth(projectId, {
    query: { enabled: !!projectId, queryKey: ["project-health", projectId] },
  });

  if (isLoading) {
    return (
      <div className="panel">
        <div className="panel-header">
          <span className="panel-title">Project Health Score</span>
        </div>
        <div className="panel-body space-y-3">
          <Skeleton className="h-16 w-full rounded-xl" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </div>
      </div>
    );
  }

  if (!health) return null;

  const cfg = LEVEL_CONFIG[health.level] ?? LEVEL_CONFIG["Good"];

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="flex items-center gap-2">
          <HeartPulse className="w-4 h-4 text-muted-foreground" />
          <span className="panel-title">Project Health Score</span>
        </div>
      </div>
      <div className="panel-body space-y-4">
        {/* Score ring + level */}
        <div
          className="rounded-xl px-5 py-4 flex items-center gap-4"
          style={{ backgroundColor: cfg.bg, border: `1px solid ${cfg.border}` }}
        >
          {/* Circular score */}
          <div className="relative w-16 h-16 shrink-0">
            <svg viewBox="0 0 64 64" className="w-16 h-16 -rotate-90">
              <circle cx="32" cy="32" r="26" fill="none" stroke="currentColor" strokeWidth="6"
                className="text-muted opacity-20" />
              <circle
                cx="32" cy="32" r="26" fill="none" strokeWidth="6"
                strokeDasharray={`${(health.score / 100) * 163.4} 163.4`}
                strokeLinecap="round"
                style={{ stroke: cfg.color, transition: "stroke-dasharray 0.6s ease" }}
              />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-sm font-bold tabular-nums" style={{ color: cfg.color }}>
                {health.score}
              </span>
            </div>
          </div>
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-0.5">
              Health Level
            </p>
            <p className="text-xl font-bold" style={{ color: cfg.color }}>{health.level}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{health.score}/100 health score</p>
          </div>
        </div>

        {/* Score bar */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Score</span>
            <span className="font-semibold" style={{ color: cfg.color }}>{health.score}/100</span>
          </div>
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{ width: `${health.score}%`, backgroundColor: cfg.color }}
            />
          </div>
        </div>

        {/* Penalty breakdown */}
        {(health.schedule_penalty > 0 || health.safety_penalty > 0 ||
          health.ncr_penalty > 0 || health.procurement_penalty > 0 ||
          health.risk_penalty > 0) && (
          <div className="space-y-1.5">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Score Breakdown
            </p>
            {[
              { label: "Schedule", penalty: health.schedule_penalty },
              { label: "Safety Events", penalty: health.safety_penalty },
              { label: "Open NCRs", penalty: health.ncr_penalty },
              { label: "Late POs", penalty: health.procurement_penalty },
              { label: "Project Risks", penalty: health.risk_penalty },
            ]
              .filter((f) => f.penalty > 0)
              .map((f) => (
                <div key={f.label} className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">{f.label}</span>
                  <span className="text-destructive font-semibold">−{f.penalty.toFixed(1)}</span>
                </div>
              ))}
          </div>
        )}

        {/* Reasons */}
        {health.reasons.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Key Issues
            </p>
            <ul className="space-y-1">
              {health.reasons.map((reason, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-foreground">
                  <span className="mt-0.5 shrink-0" style={{ color: cfg.color }}>•</span>
                  <span>{reason}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {health.reasons.length === 0 && (
          <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
            ✓ No issues detected — project is on track
          </p>
        )}
      </div>
    </div>
  );
}

export default function ProjectDetail() {
  const { t } = useTranslation();
  const params = useParams();
  const id = parseInt(params.id || "0", 10);
  const { data: project, isLoading, isError } = useGetProject(id, {
    query: { enabled: !!id, queryKey: ["project", id] },
  });

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-5 w-32" />
        <div className="space-y-2">
          <Skeleton className="h-9 w-2/3" />
          <Skeleton className="h-5 w-32" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Skeleton className="h-80 rounded-xl" />
          <Skeleton className="h-80 rounded-xl" />
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="space-y-4">
        <Link href="/projects" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4" />{t("Back to Projects")}
        </Link>
        <div className="panel panel-body flex flex-col items-center justify-center py-16 gap-3 text-muted-foreground">
          <AlertOctagon className="w-8 h-8 text-destructive opacity-60" />
          <p className="text-sm font-medium">Failed to load project</p>
          <p className="text-xs">Check your connection or permissions and try again.</p>
        </div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="space-y-4">
        <Link href="/projects" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
          <ArrowLeft className="w-4 h-4" />
          {t("Back to Projects")}
        </Link>
        <div className="panel panel-body text-center text-muted-foreground py-16">
          Project not found.
        </div>
      </div>
    );
  }

  const statusBadge = STATUS_BADGE[project.status] ?? "badge-neutral";

  return (
    <div className="space-y-6">
      <Link href="/projects" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors">
        <ArrowLeft className="w-4 h-4" />
        {t("Back to Projects")}
      </Link>

      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <span className="text-xs font-mono font-semibold text-muted-foreground bg-muted px-2.5 py-1 rounded-lg">
              {project.project_code}
            </span>
            <span className={`badge ${statusBadge}`}>{project.status}</span>
          </div>
          <h1 className="text-2xl font-bold text-foreground leading-tight">
            {project.project_name}
          </h1>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">{t("Project Details")}</span>
          </div>
          <div className="panel-body space-y-0 divide-y divide-border">
            <DetailRow icon={Hash} label={t("Code")} value={project.project_code} />
            <DetailRow icon={Tag} label={t("Project Type")} value={project.project_type} />
            <DetailRow icon={Building2} label={t("Client")} value={project.client_name} />
            <DetailRow icon={MapPin} label={t("City")} value={project.city} />
          </div>
        </div>

        <div className="panel">
          <div className="panel-header">
            <span className="panel-title">Timeline & Financials</span>
          </div>
          <div className="panel-body space-y-0 divide-y divide-border">
            <DetailRow icon={Calendar} label={t("Start Date")} value={project.start_date} />
            <DetailRow icon={Calendar} label={t("Planned Finish")} value={project.planned_finish} />
            {project.actual_finish && (
              <DetailRow icon={Calendar} label={t("Actual Finish")} value={project.actual_finish} />
            )}
            <DetailRow icon={DollarSign} label={t("Budget")} value={formatBudget(project.budget)} />
          </div>
        </div>
      </div>

      {/* Health Score Panel */}
      {!!id && <HealthScorePanel projectId={id} />}

      {project.status === "Delayed" && (
        <div className="rounded-xl border border-red-200 bg-red-50 dark:border-red-900/30 dark:bg-red-900/10 px-5 py-4 flex items-start gap-3">
          <span className="text-red-500 text-lg leading-none mt-0.5">⚠</span>
          <div>
            <p className="text-sm font-semibold text-red-700 dark:text-red-400">
              Project is behind schedule
            </p>
            <p className="text-xs text-red-600/70 dark:text-red-400/70 mt-0.5">
              This project has been flagged as delayed. Review site reports and procurement
              records for bottlenecks.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
