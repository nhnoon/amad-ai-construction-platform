import { Link } from "wouter";
import { Bell, Building2, BarChart3, Sparkles, UploadCloud, Zap } from "lucide-react";
import { GLASS, IconChip, SectionLabel } from "./shared";

// Quick Actions — shortcuts into existing pages only (no new routes, no new
// navigation structure). Icons intentionally match the ones already used for
// these destinations in the sidebar (AI Center's Sparkles, Reports'
// BarChart3, Alerts' Bell) so the same destination always reads the same way
// across the app.

const ACTIONS = [
  { label: "Upload Document", description: "Add to the document library", icon: UploadCloud, href: "/documents" },
  { label: "Open Copilot", description: "Ask the AI assistant", icon: Sparkles, href: "/copilot" },
  { label: "Open Reports", description: "Executive & weekly reports", icon: BarChart3, href: "/reports" },
  { label: "Manage Projects", description: "View the project portfolio", icon: Building2, href: "/projects" },
  { label: "View Alerts", description: "Review flagged issues", icon: Bell, href: "/alerts" },
];

export function QuickActions() {
  return (
    <div>
      <SectionLabel icon={Zap} title="Quick Actions" description="Jump straight into what you need next" />
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        {ACTIONS.map(({ label, description, icon, href }) => (
          <Link key={href + label} href={href}>
            <div className={`${GLASS} p-4 h-full flex flex-col items-start gap-3 transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 cursor-pointer`}>
              <IconChip icon={icon} className="h-9 w-9" />
              <div className="min-w-0">
                <p className="text-xs font-semibold text-foreground truncate">{label}</p>
                <p className="text-[10px] text-muted-foreground truncate">{description}</p>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
