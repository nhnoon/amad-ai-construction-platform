import type { ReactNode } from "react";

// AMAD v2 — Page Hero primitive (component hierarchy: Page Hero).
//
// Reserved for pages that act as a landing/command surface — not every
// page gets one. Uses the sidebar's navy surface tokens (bg-sidebar /
// text-sidebar-foreground) so it reads as a deliberate "anchor" moment in
// both light and dark mode, rather than reusing the neutral `.panel` card
// language every other section on the page already uses. Gold (accent /
// sidebar-primary) is reserved for the eyebrow label and primary metric —
// controlled, not decorative.
//
// Composition over configuration: `search`, `scopeSelector`, and
// `primaryAction` are slots (ReactNode), not baked-in inputs/buttons, so
// this primitive stays reusable across future pages with different needs
// instead of accumulating page-specific props.

export function PageHero({
  eyebrow,
  title,
  description,
  meta,
  search,
  scopeSelector,
  primaryAction,
}: {
  eyebrow: string;
  title: string;
  description: string;
  meta?: ReactNode;
  search?: ReactNode;
  scopeSelector?: ReactNode;
  primaryAction?: ReactNode;
}) {
  return (
    <section className="rounded-2xl bg-sidebar text-sidebar-foreground border border-sidebar-border shadow-md overflow-hidden">
      <div className="p-5 md:p-6 space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 max-w-2xl space-y-1.5">
            <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-sidebar-primary">{eyebrow}</p>
            <h1 className="text-xl md:text-2xl font-bold tracking-tight text-sidebar-foreground leading-tight">{title}</h1>
            <p className="text-[13px] text-sidebar-foreground/70 leading-normal">{description}</p>
          </div>
          {primaryAction && <div className="shrink-0">{primaryAction}</div>}
        </div>

        {(search || scopeSelector || meta) && (
          <div className="flex flex-wrap items-center gap-2.5 pt-3 border-t border-sidebar-border/60">
            {search && <div className="flex-1 min-w-[220px] max-w-sm">{search}</div>}
            {scopeSelector && <div className="shrink-0">{scopeSelector}</div>}
            {meta && <div className="ms-auto text-xs text-sidebar-foreground/50 shrink-0">{meta}</div>}
          </div>
        )}
      </div>
    </section>
  );
}
