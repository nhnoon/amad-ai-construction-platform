import {
  AlertTriangle,
  CheckCircle2,
  CloudRain,
  Compass,
  FileSearch,
  HelpCircle,
  ListChecks,
  Package,
  Radar,
  ShieldAlert,
  Siren,
  Sparkles,
  Target,
  TrendingUp,
  Wrench,
} from "lucide-react";
import type { ElementType, ReactNode } from "react";

export type AnalysisSource = {
  source_type: string;
  source_id: string;
  label: string;
  excerpt: string;
};

export type RecommendedAction = {
  action: string;
  priority: string;
  reason: string;
  evidence_refs: string[];
  expected_benefit: string;
};

export type PriorityMatrixItem = {
  item: string;
  urgency: string;
  impact: string;
  evidence_refs: string[];
};

export type TrendAnalysis = {
  available: boolean;
  summary?: string | null;
  signals: string[];
};

export type RiskScoreComponent = {
  key: string;
  label: string;
  occurrences: number;
  points: number;
  max_points: number;
  rationale: string;
  evidence_refs: string[];
};

export type RiskScoreBreakdown = {
  total: number;
  level: string;
  components: RiskScoreComponent[];
};

export type SiteReportAnalysis = {
  analysis_generated_from: string;

  reasoning_status: string; // "completed" | "unavailable" | "timed_out"
  reasoning_provider?: string | null;
  reasoning_model?: string | null;
  reasoning_error?: string | null;

  insufficient_evidence: boolean;
  insufficient_evidence_reason?: string | null;
  ocr_quality_note?: string | null;

  executive_summary: string;
  major_findings: string[];
  safety_findings: string[];
  quality_findings: string[];
  schedule_findings: string[];
  procurement_findings: string[];
  equipment_issues: string[];
  weather_impact: string;
  blocked_activities: string[];
  critical_risks: string[];
  recommended_actions: RecommendedAction[];
  priority_matrix: PriorityMatrixItem[];
  next_site_visit_focus: string[];
  questions_for_site_team: string[];
  contradictions: string[];
  trend_analysis: TrendAnalysis;

  confidence_score: number;
  risk_score_breakdown: RiskScoreBreakdown;

  priority_level: string;
  escalation_required: boolean;

  section_sources: Array<{ section: string; sources: string[] }>;
  source_attribution: AnalysisSource[];
};

function Section({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: ElementType;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border/50 bg-card/70 p-4">
      <div className="mb-3 flex items-center gap-2">
        <Icon className="h-4 w-4 text-primary" />
        <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h4>
      </div>
      <div className="text-sm text-foreground leading-relaxed">{children}</div>
    </section>
  );
}

function EvidenceChips({ refs }: { refs: string[] }) {
  if (!refs.length) return null;
  return (
    <span className="ms-1.5 inline-flex flex-wrap gap-1 align-middle">
      {refs.map((r) => (
        <span
          key={r}
          className="rounded-full border border-primary/25 bg-primary/5 px-1.5 py-0.5 font-mono text-[10px] leading-none text-primary/80"
        >
          {r}
        </span>
      ))}
    </span>
  );
}

// Findings from the backend already end with bracketed evidence codes, e.g.
// "...proceeds before inspection. [DA-14, NCR-3]" — split them out into chips
// instead of showing the raw bracket text, so the citation reads as
// structured proof rather than a training artifact.
const EVIDENCE_SUFFIX_RE = /\s*\[([^\]]+)\]\s*$/;

function CitedText({ text }: { text: string }) {
  const match = text.match(EVIDENCE_SUFFIX_RE);
  if (!match) return <span>{text}</span>;
  const body = text.slice(0, match.index).trim();
  const refs = match[1].split(",").map((s) => s.trim()).filter(Boolean);
  return (
    <span>
      {body}
      <EvidenceChips refs={refs} />
    </span>
  );
}

function BulletList({ items }: { items: string[] }) {
  if (!items.length) {
    return <p className="text-sm text-muted-foreground">None identified in this report's evidence window.</p>;
  }
  return (
    <ul className="space-y-2">
      {items.map((item, idx) => (
        <li key={`${item}-${idx}`} className="flex items-start gap-2 text-sm">
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
          <CitedText text={item} />
        </li>
      ))}
    </ul>
  );
}

const PRIORITY_TONE: Record<string, string> = {
  critical: "text-rose-600 border-rose-500/30 bg-rose-500/10",
  high: "text-amber-600 border-amber-500/30 bg-amber-500/10",
  medium: "text-blue-600 border-blue-500/30 bg-blue-500/10",
  low: "text-emerald-600 border-emerald-500/30 bg-emerald-500/10",
};

function PriorityBadge({ level }: { level: string }) {
  const tone = PRIORITY_TONE[level.toLowerCase()] ?? "text-muted-foreground border-border bg-muted/40";
  return (
    <span className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-semibold ${tone}`}>{level}</span>
  );
}

function ReasoningUnavailableNotice({ data }: { data: SiteReportAnalysis }) {
  const isTimeout = data.reasoning_status === "timed_out";
  return (
    <div className="rounded-xl border border-amber-500/30 bg-amber-500/[0.06] p-4">
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-amber-600" />
        <p className="text-sm font-semibold text-amber-700 dark:text-amber-400">
          {isTimeout ? "AI reasoning timed out" : "AI reasoning unavailable"}
        </p>
      </div>
      <p className="mt-2 text-sm text-foreground/80">{data.executive_summary}</p>
      {data.reasoning_error && (
        <p className="mt-1 text-xs text-muted-foreground">Reason: {data.reasoning_error}</p>
      )}
      <p className="mt-2 text-xs text-muted-foreground">
        The deterministic risk score below was still computed directly from this report's evidence — it does not
        depend on the AI reasoning step.
      </p>
    </div>
  );
}

// Product UX Phase 1 §3 — the completed analysis is presented as tabs
// (Overview / AI Findings / Risks / Recommendations / Sources — "Evidence"
// is the report's own raw data, rendered separately in site-report-detail.
// tsx's Evidence tab) instead of one long scroll. `section` selects which
// tab's content to render; the header (risk score + reasoning status) is
// always shown since it orients every tab, not just Overview.

export type AnalysisSection = "overview" | "findings" | "risks" | "recommendations" | "sources";

export function AnalysisHeader({ data }: { data: SiteReportAnalysis }) {
  const risk = data.risk_score_breakdown;
  const riskColor =
    risk.total >= 70 ? "text-rose-600" : risk.total >= 45 ? "text-amber-600" : risk.total >= 20 ? "text-blue-600" : "text-emerald-600";
  return (
    <>
      <div className="rounded-xl border border-border/50 bg-background/50 p-3 text-xs text-muted-foreground">
        {data.analysis_generated_from}
        {data.reasoning_status === "completed" && (
          <span className="ms-1">
            · Reasoned by {data.reasoning_provider ?? "Hermes"}
            {data.reasoning_model ? ` (${data.reasoning_model})` : ""}
          </span>
        )}
      </div>

      <div className="rounded-xl border border-primary/30 bg-gradient-to-br from-primary/5 to-transparent p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">AMAD AI Analysis</p>
            <p className="text-sm font-semibold text-foreground">Evidence-Grounded Site Intelligence</p>
          </div>
          <div className="text-right">
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground" title="Mathematically derived from this report's own evidence — not an AI confidence estimate. See the breakdown below.">
              Risk Score
            </p>
            <p className={`text-xl font-bold tabular-nums ${riskColor}`}>{risk.total}/100</p>
          </div>
        </div>
      </div>

      {data.reasoning_status !== "completed" && <ReasoningUnavailableNotice data={data} />}
    </>
  );
}

function OverviewSection({ data }: { data: SiteReportAnalysis }) {
  return (
    <div className="space-y-4">
      {data.reasoning_status === "completed" && data.insufficient_evidence && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/[0.06] p-4">
          <div className="flex items-center gap-2">
            <HelpCircle className="h-4 w-4 text-amber-600" />
            <p className="text-sm font-semibold text-amber-700 dark:text-amber-400">I don't have enough evidence</p>
          </div>
          <p className="mt-2 text-sm text-foreground/80">{data.insufficient_evidence_reason}</p>
        </div>
      )}

      <Section title="Executive Summary" icon={Sparkles}>
        {data.executive_summary}
      </Section>

      <section className="rounded-xl border border-border/50 bg-card/70 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Priority Level</h4>
            <p className="mt-1 text-sm font-semibold text-foreground">{data.priority_level}</p>
          </div>
          <div className="text-right">
            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Escalation Required</h4>
            <p className={`mt-1 text-sm font-semibold ${data.escalation_required ? "text-rose-600" : "text-emerald-600"}`}>
              {data.escalation_required ? "Yes — Immediate leadership review recommended" : "No — Standard monitoring is sufficient"}
            </p>
          </div>
        </div>
      </section>

      {data.trend_analysis.available && (
        <section className="rounded-xl border border-border/50 bg-card/70 p-4">
          <div className="mb-3 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-primary" />
            <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Trend vs. Prior Reports</h4>
          </div>
          {data.trend_analysis.summary && <p className="mb-2 text-sm text-foreground">{data.trend_analysis.summary}</p>}
          <BulletList items={data.trend_analysis.signals} />
        </section>
      )}

      {data.ocr_quality_note && (
        <div className="rounded-xl border border-border/50 bg-muted/30 p-3 text-xs text-muted-foreground">
          <span className="font-semibold text-foreground">OCR quality note: </span>
          {data.ocr_quality_note}
        </div>
      )}
    </div>
  );
}

function FindingsSection({ data }: { data: SiteReportAnalysis }) {
  return (
    <div className="space-y-4">
      <Section title="Major Findings" icon={ListChecks}><BulletList items={data.major_findings} /></Section>
      <Section title="Safety Findings" icon={ShieldAlert}><BulletList items={data.safety_findings} /></Section>
      <Section title="Quality Findings" icon={FileSearch}><BulletList items={data.quality_findings} /></Section>
      <Section title="Schedule Findings" icon={CheckCircle2}><BulletList items={data.schedule_findings} /></Section>
      <Section title="Procurement Findings" icon={Package}><BulletList items={data.procurement_findings} /></Section>
      <Section title="Equipment Issues" icon={Wrench}><BulletList items={data.equipment_issues} /></Section>
      <Section title="Weather Impact" icon={CloudRain}>
        {data.weather_impact ? <CitedText text={data.weather_impact} /> : <p className="text-sm text-muted-foreground">No weather impact identified.</p>}
      </Section>
      <Section title="Blocked Activities" icon={AlertTriangle}><BulletList items={data.blocked_activities} /></Section>
      {data.contradictions.length > 0 && (
        <Section title="Contradictions Found in Evidence" icon={Siren}><BulletList items={data.contradictions} /></Section>
      )}
    </div>
  );
}

function RisksSection({ data }: { data: SiteReportAnalysis }) {
  const risk = data.risk_score_breakdown;
  return (
    <div className="space-y-4">
      <Section title="Critical Risks" icon={Radar}><BulletList items={data.critical_risks} /></Section>

      <section className="rounded-xl border border-border/50 bg-card/70 p-4">
        <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Risk Score Breakdown</h4>
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm font-semibold text-foreground">Total: {risk.total}/100</p>
          <PriorityBadge level={risk.level} />
        </div>
        <ul className="space-y-2">
          {risk.components.filter((c) => c.points > 0).map((c) => (
            <li key={c.key} className="rounded-lg border border-border/40 bg-background/50 p-2.5">
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs font-semibold text-foreground">{c.label} (×{c.occurrences})</p>
                <p className="text-xs font-mono text-foreground">+{c.points}/{c.max_points}</p>
              </div>
              <p className="mt-1 text-[11px] text-muted-foreground">{c.rationale}</p>
              <EvidenceChips refs={c.evidence_refs} />
            </li>
          ))}
          {risk.components.every((c) => c.points === 0) && (
            <p className="text-sm text-muted-foreground">No risk-contributing factors found in this report's evidence.</p>
          )}
        </ul>
      </section>

      <section className="rounded-xl border border-border/50 bg-card/70 p-4">
        <div className="mb-3 flex items-center gap-2">
          <Compass className="h-4 w-4 text-primary" />
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Priority Matrix</h4>
        </div>
        {data.priority_matrix.length === 0 ? (
          <p className="text-sm text-muted-foreground">No items to prioritize.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-muted-foreground">
                  <th className="pb-2 pe-3 font-semibold">Item</th>
                  <th className="pb-2 pe-3 font-semibold">Urgency</th>
                  <th className="pb-2 font-semibold">Impact</th>
                </tr>
              </thead>
              <tbody>
                {data.priority_matrix.map((row, idx) => (
                  <tr key={idx} className="border-t border-border/30">
                    <td className="py-2 pe-3 text-foreground">
                      {row.item}
                      <EvidenceChips refs={row.evidence_refs} />
                    </td>
                    <td className="py-2 pe-3"><PriorityBadge level={row.urgency} /></td>
                    <td className="py-2"><PriorityBadge level={row.impact} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function RecommendationsSection({ data }: { data: SiteReportAnalysis }) {
  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-border/50 bg-card/70 p-4">
        <div className="mb-3 flex items-center gap-2">
          <Target className="h-4 w-4 text-primary" />
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Recommended Actions</h4>
        </div>
        {data.recommended_actions.length === 0 ? (
          <p className="text-sm text-muted-foreground">No recommendations — insufficient evidence or no material findings.</p>
        ) : (
          <div className="space-y-3">
            {data.recommended_actions.map((rec, idx) => (
              <div key={idx} className="rounded-lg border border-border/40 bg-background/50 p-3 space-y-1.5">
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm font-semibold text-foreground">{rec.action}</p>
                  <PriorityBadge level={rec.priority} />
                </div>
                <p className="text-xs text-muted-foreground">
                  <span className="font-semibold text-foreground/80">Why: </span>
                  {rec.reason}
                </p>
                <p className="text-xs text-muted-foreground">
                  <span className="font-semibold text-foreground/80">Expected benefit: </span>
                  {rec.expected_benefit}
                </p>
                <EvidenceChips refs={rec.evidence_refs} />
              </div>
            ))}
          </div>
        )}
      </section>

      <Section title="Next Site Visit Focus" icon={Target}><BulletList items={data.next_site_visit_focus} /></Section>
      <Section title="Questions for Site Team" icon={HelpCircle}><BulletList items={data.questions_for_site_team} /></Section>
    </div>
  );
}

function SourcesSection({ data }: { data: SiteReportAnalysis }) {
  return (
    <section className="rounded-xl border border-border/50 bg-card/70 p-4">
      <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Source Attribution</h4>
      {data.source_attribution.length === 0 ? (
        <p className="text-sm text-muted-foreground">No sources cited yet — run AI analysis to see which report and dataset evidence backs each finding.</p>
      ) : (
        <ul className="space-y-2">
          {data.source_attribution.map((source, idx) => (
            <li key={`${source.source_type}-${source.source_id}-${idx}`} className="rounded-lg border border-border/40 bg-background/50 p-3">
              <p className="text-xs font-semibold text-foreground">{source.label}</p>
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{source.source_type}</p>
              <p className="mt-1 text-xs text-muted-foreground leading-relaxed">{source.excerpt}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export default function SiteReportAnalysisPanel({
  data, section = "overview", showHeader = true,
}: {
  data: SiteReportAnalysis;
  section?: AnalysisSection;
  showHeader?: boolean;
}) {
  return (
    <div className="space-y-4">
      {showHeader && <AnalysisHeader data={data} />}
      {section === "overview" && <OverviewSection data={data} />}
      {section === "findings" && <FindingsSection data={data} />}
      {section === "risks" && <RisksSection data={data} />}
      {section === "recommendations" && <RecommendationsSection data={data} />}
      {section === "sources" && <SourcesSection data={data} />}
    </div>
  );
}
