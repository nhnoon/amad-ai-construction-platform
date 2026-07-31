import type { ElementType } from "react";
import { Link } from "wouter";
import { ChevronRight } from "lucide-react";

// AMAD v2 — Quick Action / Contextual Navigation primitive. A slim row,
// not a card: icon, title, one line of the most important metadata, and
// a chevron. Built specifically so a long list of destinations (e.g. 15
// AI workspaces) reads as a scannable list rather than a wall of
// equal-weight tiles — the opposite of StatTile's card treatment, used
// deliberately here instead of it.

export function WorkspaceQuickLink({
  icon: Icon,
  title,
  meta,
  href,
  accent = "text-muted-foreground",
  variant = "row",
}: {
  icon: ElementType;
  title: string;
  meta?: string;
  href: string;
  accent?: string;
  /** "row" — dense list item (e.g. a long, searchable directory).
   * "card" — small square nav tile for a short, curated set of
   * destinations (e.g. an Overview page's Quick Access grid). Same
   * primitive, two densities, so future pages pick whichever fits
   * instead of inventing a new component. */
  variant?: "row" | "card";
}) {
  if (variant === "card") {
    return (
      <Link
        href={href}
        className="panel p-2.5 flex flex-col gap-1.5 hover:border-primary/30 hover:-translate-y-0.5 transition-all duration-150 group"
      >
        <div className="flex items-center justify-between">
          <div className={`w-6 h-6 rounded-md flex items-center justify-center shrink-0 bg-muted ${accent}`}>
            <Icon className="w-3.5 h-3.5" />
          </div>
          <ChevronRight className="w-3 h-3 text-muted-foreground/40 shrink-0 group-hover:translate-x-0.5 group-hover:text-foreground transition-all" />
        </div>
        <div className="min-w-0">
          <p className="text-[11px] font-semibold text-foreground truncate leading-tight">{title}</p>
          {meta && <p className="text-[9px] text-muted-foreground truncate mt-0.5">{meta}</p>}
        </div>
      </Link>
    );
  }

  return (
    <Link
      href={href}
      className="flex items-center gap-2.5 px-2.5 py-2 rounded-lg hover:bg-muted/60 transition-colors group"
    >
      <Icon className={`w-4 h-4 shrink-0 ${accent}`} />
      <span className="text-sm font-medium text-foreground truncate flex-1 min-w-0">{title}</span>
      {meta && <span className="text-[11px] text-muted-foreground shrink-0 hidden sm:inline">{meta}</span>}
      <ChevronRight className="w-3.5 h-3.5 text-muted-foreground/50 shrink-0 group-hover:translate-x-0.5 group-hover:text-foreground transition-all" />
    </Link>
  );
}
