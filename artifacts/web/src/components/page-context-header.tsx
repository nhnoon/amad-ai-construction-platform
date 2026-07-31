import { ReactNode } from "react";
import { ArrowLeft, ChevronRight } from "lucide-react";
import { Link, useLocation } from "wouter";

type BreadcrumbItem = {
  label: string;
  href?: string;
};

export type PageContextHeaderProps = {
  title: string;
  subtitle: string;
  /** Omit both on top-level pages with nothing meaningful to go "back" to
   * (e.g. the Dashboard) — the back link only renders when both are set. */
  backLabel?: string;
  backHref?: string;
  breadcrumbs: BreadcrumbItem[];
  /** Inline adornment rendered next to the title — status pills / code chips
   * on detail pages (e.g. a project's status badge). Omit on list pages. */
  badge?: ReactNode;
  /** Primary actions / filters row — the "Toolbar" region of the shared page
   * template (Breadcrumb / Title / Description / Toolbar / Content). Renders
   * right-aligned next to the title on wide screens, wraps below it on narrow
   * ones. Omit for pages with no page-level actions. */
  toolbar?: ReactNode;
};

export function PageContextHeader({
  title,
  subtitle,
  backLabel,
  backHref,
  breadcrumbs,
  badge,
  toolbar,
}: PageContextHeaderProps) {
  const [, setLocation] = useLocation();

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        {breadcrumbs.map((crumb, idx) => (
          <div key={`${crumb.label}-${idx}`} className="flex items-center gap-2">
            {crumb.href ? (
              <Link href={crumb.href} className="hover:text-foreground transition-colors">
                {crumb.label}
              </Link>
            ) : (
              <span className="font-medium text-foreground">{crumb.label}</span>
            )}
            {idx < breadcrumbs.length - 1 && <ChevronRight className="h-3 w-3" />}
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          {backHref && backLabel && (
            <button
              type="button"
              onClick={() => setLocation(backHref)}
              className="mb-2 inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              {backLabel}
            </button>
          )}
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="text-2xl font-bold text-foreground">{title}</h1>
            {badge}
          </div>
          <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>
        </div>
        {toolbar && (
          <div className="flex flex-wrap items-center gap-2 shrink-0">
            {toolbar}
          </div>
        )}
      </div>
    </div>
  );
}
