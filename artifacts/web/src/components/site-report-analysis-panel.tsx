import {
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  FileSearch,
  Radar,
  ShieldAlert,
  Siren,
  Target,
} from "lucide-react";
import type { ElementType, ReactNode } from "react";

export type AnalysisSource = {
  source_type: string;
  source_id: string;
  label: string;
  excerpt: string;
};

export type SiteReportAnalysis = {
  analysis_generated_from: string;
  executive_summary: string;
  progress_assessment: string;
  delay_analysis: string;
  risk_analysis: string;
  safety_findings: string[];
  quality_findings: string[];
  schedule_impact: string;
  recommended_actions: string[];
  priority_level: string;
  escalation_required: boolean;
  confidence_score: number;
  section_sources: Array<{
    section: string;
    sources: string[];
  }>;
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

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-2">
      {items.map((item, idx) => (
        <li key={`${item}-${idx}`} className="flex items-start gap-2 text-sm">
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function SiteReportAnalysisPanel({ data }: { data: SiteReportAnalysis }) {
  const confidenceColor =
    data.confidence_score >= 80
      ? "text-emerald-600"
      : data.confidence_score >= 60
        ? "text-amber-600"
        : "text-rose-600";

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-border/50 bg-background/50 p-3 text-xs text-muted-foreground">
        {data.analysis_generated_from}
      </div>

      <div className="rounded-xl border border-primary/30 bg-gradient-to-br from-primary/5 to-transparent p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">AMAD AI Analysis</p>
            <p className="text-sm font-semibold text-foreground">Structured Site Report Intelligence</p>
          </div>
          <div className="text-right">
            <p className="text-[11px] uppercase tracking-wider text-muted-foreground">Confidence</p>
            <p className={`text-xl font-bold tabular-nums ${confidenceColor}`}>{data.confidence_score}%</p>
          </div>
        </div>
      </div>

      <Section title="Executive Summary" icon={ClipboardCheck}>
        {data.executive_summary}
      </Section>

      <Section title="Progress Assessment" icon={CheckCircle2}>
        {data.progress_assessment}
      </Section>

      <Section title="Delay Analysis" icon={AlertTriangle}>
        {data.delay_analysis}
      </Section>

      <Section title="Risk Analysis" icon={Radar}>
        {data.risk_analysis}
      </Section>

      <Section title="Schedule Impact" icon={AlertTriangle}>
        {data.schedule_impact}
      </Section>

      <Section title="Safety Findings" icon={ShieldAlert}>
        <BulletList items={data.safety_findings} />
      </Section>

      <Section title="Quality Findings" icon={FileSearch}>
        <BulletList items={data.quality_findings} />
      </Section>

      <Section title="Recommended Actions" icon={Target}>
        <BulletList items={data.recommended_actions} />
      </Section>

      <section className="rounded-xl border border-border/50 bg-card/70 p-4">
        <div className="mb-3 flex items-center gap-2">
          <Siren className="h-4 w-4 text-primary" />
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Priority Level</h4>
        </div>
        <p className="text-sm font-semibold text-foreground">{data.priority_level}</p>
      </section>

      <section className="rounded-xl border border-border/50 bg-card/70 p-4">
        <div className="mb-3 flex items-center gap-2">
          <Siren className="h-4 w-4 text-primary" />
          <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Escalation Required</h4>
        </div>
        <p className={`text-sm font-semibold ${data.escalation_required ? "text-rose-600" : "text-emerald-600"}`}>
          {data.escalation_required ? "Yes - Immediate leadership review recommended" : "No - Standard monitoring is sufficient"}
        </p>
      </section>

      <section className="rounded-xl border border-border/50 bg-card/70 p-4">
        <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Section Sources</h4>
        <ul className="space-y-2">
          {data.section_sources.map((row, idx) => (
            <li key={`${row.section}-${idx}`} className="rounded-lg border border-border/40 bg-background/50 p-3">
              <p className="text-xs font-semibold text-foreground">{row.section}</p>
              <p className="mt-1 text-xs text-muted-foreground">Source: {row.sources.join(", ")}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-xl border border-border/50 bg-card/70 p-4">
        <h4 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Source Attribution</h4>
        <ul className="space-y-2">
          {data.source_attribution.map((source, idx) => (
            <li key={`${source.source_type}-${source.source_id}-${idx}`} className="rounded-lg border border-border/40 bg-background/50 p-3">
              <p className="text-xs font-semibold text-foreground">{source.label}</p>
              <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{source.source_type} #{source.source_id}</p>
              <p className="mt-1 text-xs text-muted-foreground leading-relaxed">{source.excerpt}</p>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
