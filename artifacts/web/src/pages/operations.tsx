import { useLocation } from "wouter";
import {
  Briefcase,
  CalendarDays,
  ShoppingCart,
  ClipboardCheck,
  HelpCircle,
  AlertCircle,
  TrendingUp,
  ArrowRight,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useGetDashboardSummary } from "@workspace/api-client-react";
import { PageContextHeader } from "@/components/page-context-header";

interface OperationModule {
  id: string;
  label: string;
  icon: React.ReactNode;
  recordCount: number;
  status: string;
  route: string;
  accentColor: string;
  iconColor: string;
  priority?: "primary" | "secondary";
}

function OperationCard({ module }: { module: OperationModule }) {
  const [, setLocation] = useLocation();

  return (
    <button
      onClick={() => setLocation(module.route)}
      className={cn(
        "group relative flex flex-col text-start transition-all duration-200",
        "rounded-lg border border-border/50 hover:border-border",
        "bg-card/40 hover:bg-card/60 backdrop-blur-sm",
        "p-4 gap-3",
        "focus:outline-none focus:ring-2 focus:ring-primary/50 focus:ring-offset-2 dark:focus:ring-offset-slate-900"
      )}
      style={{
        borderTop: `2px solid ${module.accentColor}`,
      }}
    >
      {/* Header: Icon + Title + Records */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5 flex-1 min-w-0">
          <div className={`flex-shrink-0 ${module.iconColor}`}>
            {module.icon}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-foreground leading-tight">{module.label}</h3>
          </div>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-lg font-bold text-foreground">{module.recordCount}</p>
          <span className="text-xs text-muted-foreground">items</span>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">{module.status}</p>

      {/* Action Link */}
      <div className="flex items-center gap-1.5 text-xs font-medium text-primary group-hover:text-primary/80 transition-colors">
        <span>Access</span>
        <ArrowRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all duration-200" />
      </div>
    </button>
  );
}

export default function Operations() {
  const { data: summary, isLoading, isError } = useGetDashboardSummary();

  const modules: OperationModule[] = [
    {
      id: "projects",
      label: "Projects",
      icon: <Briefcase className="w-5 h-5" />,
      recordCount: summary?.total_projects ?? 0,
      status: `${summary?.active_projects ?? 0} active · ${summary?.delayed_projects ?? 0} delayed`,
      route: "/projects",
      accentColor: "#3B82F6",
      iconColor: "text-blue-500",
      priority: "primary",
    },
    {
      id: "procurement",
      label: "Procurement",
      icon: <ShoppingCart className="w-5 h-5" />,
      recordCount: summary?.total_purchase_orders ?? 0,
      status: `${summary?.late_purchase_orders ?? 0} late POs · ${summary?.open_purchase_requests ?? 0} open PRs`,
      route: "/procurement",
      accentColor: "#10B981",
      iconColor: "text-green-500",
      priority: "primary",
    },
    {
      id: "site-reports",
      label: "Site Reports",
      icon: <ClipboardCheck className="w-5 h-5" />,
      recordCount: summary?.total_site_reports ?? 0,
      status: "Daily reporting and execution updates",
      route: "/site-reports",
      accentColor: "#F59E0B",
      iconColor: "text-amber-500",
      priority: "primary",
    },
    {
      id: "meetings",
      label: "Meetings",
      icon: <CalendarDays className="w-5 h-5" />,
      recordCount: summary?.total_meetings ?? 0,
      status: `${summary?.total_decisions ?? 0} decisions captured`,
      route: "/meetings",
      accentColor: "#A855F7",
      iconColor: "text-purple-500",
      priority: "secondary",
    },
    {
      id: "rfis",
      label: "RFIs",
      icon: <HelpCircle className="w-5 h-5" />,
      recordCount: summary?.total_decisions ?? 0,
      status: "Project clarifications and responses",
      route: "/rfis",
      accentColor: "#06B6D4",
      iconColor: "text-cyan-500",
      priority: "secondary",
    },
    {
      id: "change-orders",
      label: "Change Orders",
      icon: <AlertCircle className="w-5 h-5" />,
      recordCount: summary?.open_ncrs ?? 0,
      status: "Contract scope and value adjustments",
      route: "/change-orders",
      accentColor: "#EC4899",
      iconColor: "text-pink-500",
      priority: "secondary",
    },
    {
      id: "claims",
      label: "Claims",
      icon: <TrendingUp className="w-5 h-5" />,
      recordCount: summary?.high_severity_events ?? 0,
      status: "Dispute and entitlement tracking",
      route: "/claims",
      accentColor: "#EF4444",
      iconColor: "text-red-500",
      priority: "secondary",
    },
  ];

  // Separate primary and secondary modules
  const primaryModules = modules.filter((m) => m.priority === "primary");
  const secondaryModules = modules.filter((m) => m.priority === "secondary");

  return (
    <div className="space-y-8">
      <PageContextHeader
        title="Operations"
        subtitle="Manage all project operations and domain workspaces"
        backLabel="Back to Dashboard"
        backHref="/"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Operations" },
        ]}
      />

      {isLoading && (
        <div className="rounded-xl border border-border/50 bg-card/60 p-4 text-sm text-muted-foreground inline-flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading live module metrics...
        </div>
      )}

      {isError && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive">
          Failed to load live module metrics. Navigation remains available.
        </div>
      )}

      {/* Primary Operations (Higher Emphasis) */}
      <div>
        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Primary Modules
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {primaryModules.map((module) => (
            <OperationCard key={module.id} module={module} />
          ))}
        </div>
      </div>

      {/* Secondary Operations */}
      <div>
        <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
          Secondary Modules
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {secondaryModules.map((module) => (
            <OperationCard key={module.id} module={module} />
          ))}
        </div>
      </div>
    </div>
  );
}
