import { useParams } from "wouter";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import CopilotPage from "@/pages/copilot";
import RecentMemoriesPanel from "./RecentMemoriesPanel";
import Overview from "./workspaces/Overview";
import MemoryCenter from "./MemoryCenter";
import ProjectIntelligence from "./workspaces/ProjectIntelligence";
import SiteReportIntelligence from "./workspaces/SiteReportIntelligence";
import MeetingIntelligence from "./workspaces/MeetingIntelligence";
import ContractIntelligence from "./workspaces/ContractIntelligence";
import ExecutiveIntelligence from "./workspaces/ExecutiveIntelligence";
import IntelligentSearch from "./workspaces/IntelligentSearch";
import EmailIntelligence from "./workspaces/EmailIntelligence";
import ProjectMemory from "./workspaces/project-memory";
import PredictiveIntelligence from "./workspaces/predictive-intelligence";
import SupplierRiskIntelligence from "./workspaces/supplier-risk";
import MaterialIntelligence from "./workspaces/material-intelligence";
import CrossProjectLearning from "./workspaces/cross-project-learning";
import ExecutiveDecisionCenter from "./workspaces/executive-decision-center";

// AI Workspace shell (Product UX Phase 1 §1) — replaces the old two-tab
// "one chatbot" AI Center. Seven focused workspaces plus an overview,
// addressed by /ai-center/:workspace so each is bookmarkable and linkable
// from elsewhere in the app (e.g. Project Intelligence cards deep-link
// here). Every workspace below reuses existing endpoints/components —
// nothing here talks to a new AI pipeline or changes retrieval/prompts.
//
// No internal section rail here (enterprise nav refactor): the global
// sidebar's "AI Center" group is the single, sole way to switch between
// these workspaces — this page renders only the active one.

function CopilotWorkspace() {
  return (
    <div className="flex flex-col lg:flex-row gap-4">
      <div className="flex-1 min-w-0">
        <ErrorBoundary>
          <CopilotPage compact />
        </ErrorBoundary>
      </div>
      <ErrorBoundary>
        <RecentMemoriesPanel className="w-full lg:w-80 shrink-0 h-[75vh] min-h-[480px]" />
      </ErrorBoundary>
    </div>
  );
}

const WORKSPACE_CONTENT: Record<string, React.ComponentType> = {
  overview: Overview,
  copilot: CopilotWorkspace,
  memory: MemoryCenter,
  projects: ProjectIntelligence,
  "site-reports": SiteReportIntelligence,
  meetings: MeetingIntelligence,
  contracts: ContractIntelligence,
  executive: ExecutiveIntelligence,
  search: IntelligentSearch,
  email: EmailIntelligence,
  "project-memory": ProjectMemory,
  "predictive-intelligence": PredictiveIntelligence,
  "supplier-risk": SupplierRiskIntelligence,
  "material-intelligence": MaterialIntelligence,
  "cross-project-learning": CrossProjectLearning,
  "executive-decision-center": ExecutiveDecisionCenter,
};

export default function AICenter() {
  const params = useParams<{ workspace?: string }>();
  const active = params.workspace && WORKSPACE_CONTENT[params.workspace] ? params.workspace : "overview";
  const ActiveContent = WORKSPACE_CONTENT[active];

  // AMAD v2 — Overview, Executive Intelligence, and Executive Decision
  // Center render their own Page Hero as the first thing on the page (see
  // workspaces/Overview.tsx, workspaces/ExecutiveIntelligence.tsx, and
  // workspaces/executive-decision-center/index.tsx), so all three skip the
  // generic WorkspaceLayout breadcrumb/title wrapper here. Every other
  // workspace is untouched: same WorkspaceLayout header as before — the
  // remaining 13 detail workspaces are explicitly not being redesigned yet.
  if (active === "overview" || active === "executive" || active === "executive-decision-center") {
    return (
      <div className="space-y-5">
        <ErrorBoundary key={active}>
          <ActiveContent />
        </ErrorBoundary>
      </div>
    );
  }

  return (
    <WorkspaceLayout
      title="AI Workspace"
      subtitle="Seven focused AI workspaces, grounded in real platform data"
      backLabel="Back to Dashboard"
      backHref="/"
      breadcrumbs={[
        { label: "Dashboard", href: "/" },
        { label: "AI Center" },
      ]}
    >
      <ErrorBoundary key={active}>
        <ActiveContent />
      </ErrorBoundary>
    </WorkspaceLayout>
  );
}
