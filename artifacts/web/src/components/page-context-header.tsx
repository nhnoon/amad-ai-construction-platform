import { ArrowLeft, ChevronRight } from "lucide-react";
import { Link, useLocation } from "wouter";

type BreadcrumbItem = {
  label: string;
  href?: string;
};

type PageContextHeaderProps = {
  title: string;
  subtitle: string;
  backLabel: string;
  backHref: string;
  breadcrumbs: BreadcrumbItem[];
};

export function PageContextHeader({
  title,
  subtitle,
  backLabel,
  backHref,
  breadcrumbs,
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
          <button
            type="button"
            onClick={() => setLocation(backHref)}
            className="mb-2 inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            {backLabel}
          </button>
          <h1 className="text-2xl font-bold text-foreground">{title}</h1>
          <p className="text-sm text-muted-foreground mt-1">{subtitle}</p>
        </div>
      </div>
    </div>
  );
}
