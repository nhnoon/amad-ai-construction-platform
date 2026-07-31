import type { ElementType } from "react";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { EmptyState } from "@/components/ui/empty-state";
import type { PageContextHeaderProps } from "@/components/page-context-header";

// Shared shell for modules that exist in the product vision / roadmap but
// have no backend or real UI yet. Renders the standard page header (so the
// module is a first-class, bookmarkable destination) plus a status badge
// and a capability preview, instead of every future module hand-rolling
// its own "coming soon" screen.

export type RoadmapStatus = "in-development" | "planned";

const STATUS_LABEL: Record<RoadmapStatus, string> = {
  "in-development": "In Development",
  planned: "Planned",
};

const STATUS_BADGE: Record<RoadmapStatus, string> = {
  "in-development": "badge-info",
  planned: "badge-gold",
};

export function RoadmapPlaceholder({
  title,
  subtitle,
  breadcrumbs,
  icon: Icon,
  status,
  phase,
  description,
  capabilities,
}: {
  title: string;
  subtitle: string;
  breadcrumbs: PageContextHeaderProps["breadcrumbs"];
  icon: ElementType;
  status: RoadmapStatus;
  phase: string;
  description: string;
  capabilities: string[];
}) {
  return (
    <WorkspaceLayout
      title={title}
      subtitle={subtitle}
      breadcrumbs={breadcrumbs}
      badge={<span className={`badge ${STATUS_BADGE[status]}`}>{STATUS_LABEL[status]}</span>}
    >
      <div className="panel">
        <EmptyState icon={Icon} title={`${title} is on the roadmap`} description={description} />
        <div className="panel-body pt-0 border-t border-border/50">
          <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground mb-3">{phase}</p>
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {capabilities.map((c) => (
              <li
                key={c}
                className="flex items-center gap-2 text-sm text-foreground/80 px-3 py-2 rounded-lg bg-muted/40 border border-border/50"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-primary/60 shrink-0" />
                {c}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </WorkspaceLayout>
  );
}
