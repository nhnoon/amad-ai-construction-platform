import { Link } from "wouter";
import { AlertTriangle, FileStack, HeartPulse, Lightbulb, ShieldAlert, Sparkles } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { GLASS, GLASS_HEADER, IconChip, SectionLabel, type Tone } from "./shared";
import type { ExecutiveIntelligence } from "../../lib/useExecutive";
import type { DashboardSummary } from "@workspace/api-client-react";

// Executive Insights — short, plain-language summaries synthesized entirely
// from data already fetched for this page (DashboardSummary, Executive
// Intelligence, document count). No new metrics are invented here; where a
// number isn't available from an existing endpoint (e.g. a portfolio-wide
// "AI analyses completed" count), the card says so honestly instead of
// showing a fabricated figure.

interface InsightCardProps {
  icon: typeof HeartPulse;
  tone: Tone;
  title: string;
  body: string;
  href?: string;
}

function InsightCard({ icon, tone, title, body, href }: InsightCardProps) {
  const content = (
    <div className={`${GLASS} h-full p-5 transition-all duration-200 hover:shadow-md ${href ? "cursor-pointer" : ""}`}>
      <div className="flex items-center gap-3 mb-3">
        <IconChip icon={icon} className="h-8 w-8" tone={tone} />
        <span className="text-sm font-bold text-foreground">{title}</span>
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">{body}</p>
    </div>
  );
  return href ? <Link href={href}>{content}</Link> : content;
}

export function ExecutiveInsights({
  summary, execData, documentCount, isLoading,
}: {
  summary?: DashboardSummary;
  execData?: ExecutiveIntelligence;
  documentCount?: number;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div>
        <SectionLabel icon={Lightbulb} title="Executive Insights" description="What the portfolio data means, in plain language" />
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} className={`${GLASS} h-[140px] w-full`} />)}
        </div>
      </div>
    );
  }

  const dp = summary?.delayed_projects ?? 0;
  const openNcrs = summary?.open_ncrs ?? 0;
  const totalNcrs = summary?.total_ncrs ?? 0;
  const attentionProjects = execData?.attention_required?.slice(0, 3) ?? [];

  const healthBody = execData
    ? `Portfolio score is ${execData.portfolio_score}/100 (${execData.portfolio_status}). ${execData.excellent_count + execData.good_count} of ${execData.total_projects} projects are in good standing; ${execData.critical_count} need intervention.`
    : "Portfolio health scoring is not yet available.";

  const delayedBody = dp === 0
    ? "No projects are currently behind schedule."
    : attentionProjects.length > 0
    ? `${dp} project${dp !== 1 ? "s are" : " is"} behind schedule, including ${attentionProjects.map((p) => p.project_code).join(", ")}.`
    : `${dp} project${dp !== 1 ? "s are" : " is"} currently behind schedule.`;

  const ncrBody = totalNcrs === 0
    ? "No non-conformance reports have been logged."
    : openNcrs === 0
    ? `All ${totalNcrs} logged non-conformance report${totalNcrs !== 1 ? "s have" : " has"} been closed.`
    : `${openNcrs} of ${totalNcrs} non-conformance report${totalNcrs !== 1 ? "s are" : " is"} still open and awaiting resolution.`;

  const docBody = documentCount === undefined
    ? "Document library data is not available."
    : documentCount === 0
    ? "No documents have been added to the library yet."
    : `${documentCount} document${documentCount !== 1 ? "s are" : " is"} stored in the General and Project libraries, available for OCR and contract analysis.`;

  const aiBody = execData?.executive_summary
    ? execData.executive_summary
    : "An AI-generated portfolio summary will appear here once executive intelligence data is available.";

  return (
    <div>
      <SectionLabel icon={Lightbulb} title="Executive Insights" description="What the portfolio data means, in plain language" />
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        <InsightCard icon={HeartPulse} tone="neutral" title="Portfolio Health" body={healthBody} href="/reports" />
        <InsightCard icon={AlertTriangle} tone={dp > 0 ? "warning" : "success"} title="Delayed Projects" body={delayedBody} href="/projects" />
        <InsightCard icon={ShieldAlert} tone={openNcrs > 0 ? "danger" : "success"} title="Open NCRs" body={ncrBody} href="/safety" />
        <InsightCard icon={FileStack} tone="neutral" title="Document Library" body={docBody} href="/documents" />
        <InsightCard icon={Sparkles} tone="neutral" title="Recent AI Activity" body={aiBody} href="/reports" />
      </div>
    </div>
  );
}
