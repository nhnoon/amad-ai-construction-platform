import { Bell, Building2, BarChart3, Sparkles, UploadCloud, Zap } from "lucide-react";
import { WorkspaceQuickLink } from "@/components/WorkspaceQuickLink";
import { SectionLabel } from "./shared";

// Quick Actions — shortcuts into existing pages only (no new routes, no new
// navigation structure). Icons intentionally match the ones already used for
// these destinations in the sidebar (AI Center's Sparkles, Reports'
// BarChart3, Alerts' Bell) so the same destination always reads the same way
// across the app. Cards use the shared AMAD v2 WorkspaceQuickLink primitive
// (the same one AI Center Overview's Quick Access grid uses) instead of a
// second, Dashboard-local card implementation.

const ACTIONS = [
  { label: "Upload Document", description: "Add to the document library", icon: UploadCloud, href: "/documents", accent: "text-violet-600 dark:text-violet-400" },
  { label: "Open Copilot", description: "Ask the AI assistant", icon: Sparkles, href: "/copilot", accent: "text-accent" },
  { label: "Open Reports", description: "Executive & weekly reports", icon: BarChart3, href: "/reports", accent: "text-indigo-600 dark:text-indigo-400" },
  { label: "Manage Projects", description: "View the project portfolio", icon: Building2, href: "/projects", accent: "text-sky-600 dark:text-sky-400" },
  { label: "View Alerts", description: "Review flagged issues", icon: Bell, href: "/alerts", accent: "text-rose-600 dark:text-rose-400" },
];

export function QuickActions() {
  return (
    <div>
      <SectionLabel icon={Zap} title="Quick Actions" description="Jump straight into what you need next" />
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
        {ACTIONS.map(({ label, description, icon, href, accent }) => (
          <WorkspaceQuickLink key={href + label} icon={icon} title={label} meta={description} href={href} accent={accent} variant="card" />
        ))}
      </div>
    </div>
  );
}
