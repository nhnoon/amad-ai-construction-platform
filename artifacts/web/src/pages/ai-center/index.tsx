import { useParams } from "wouter";
import { Link } from "wouter";
import {
  Sparkles, LayoutGrid, Bot, Brain, Building2, ClipboardList, CalendarDays, FileSignature, LineChart,
} from "lucide-react";
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

// AI Workspace shell (Product UX Phase 1 §1) — replaces the old two-tab
// "one chatbot" AI Center. Seven focused workspaces plus an overview,
// addressed by /ai-center/:workspace so each is bookmarkable and linkable
// from elsewhere in the app (e.g. Project Intelligence cards deep-link
// here). Every workspace below reuses existing endpoints/components —
// nothing here talks to a new AI pipeline or changes retrieval/prompts.

const RAIL_ITEMS = [
  { key: "overview",     label: "Overview",                icon: LayoutGrid },
  { key: "copilot",      label: "AI Copilot",               icon: Bot },
  { key: "memory",       label: "Memory Center",            icon: Brain },
  { key: "projects",     label: "Project Intelligence",     icon: Building2 },
  { key: "site-reports", label: "Site Report Intelligence", icon: ClipboardList },
  { key: "meetings",     label: "Meeting Intelligence",     icon: CalendarDays },
  { key: "contracts",    label: "Contract Intelligence",    icon: FileSignature },
  { key: "executive",    label: "Executive Intelligence",   icon: LineChart },
] as const;

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
};

export default function AICenter() {
  const params = useParams<{ workspace?: string }>();
  const active = params.workspace && WORKSPACE_CONTENT[params.workspace] ? params.workspace : "overview";
  const ActiveContent = WORKSPACE_CONTENT[active];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-foreground flex items-center gap-2">
          <Sparkles className="w-7 h-7 text-primary" />
          AI Workspace
        </h1>
        <p className="text-muted-foreground mt-1">
          Seven focused AI workspaces, grounded in real platform data.
        </p>
      </div>

      {/* Workspace rail — horizontal scroll strip below lg, fixed side rail at lg+ */}
      <div className="flex flex-col lg:flex-row gap-5">
        <nav
          className="flex lg:flex-col gap-1 overflow-x-auto lg:overflow-visible lg:w-56 shrink-0 pb-1 lg:pb-0 -mx-1 px-1 lg:mx-0 lg:px-0"
          aria-label="AI Workspace sections"
        >
          {RAIL_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = active === item.key;
            return (
              <Link
                key={item.key}
                href={item.key === "overview" ? "/ai-center" : `/ai-center/${item.key}`}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium whitespace-nowrap shrink-0 lg:shrink transition-colors ${
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground"
                }`}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex-1 min-w-0">
          <ErrorBoundary key={active}>
            <ActiveContent />
          </ErrorBoundary>
        </div>
      </div>
    </div>
  );
}
