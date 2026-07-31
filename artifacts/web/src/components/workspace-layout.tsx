import type { ReactNode } from "react";
import { PageContextHeader, type PageContextHeaderProps } from "./page-context-header";

// The one shared page shell every workspace renders through. Every page
// used to hand-roll its own `<div className="space-y-6"><PageContextHeader
// .../>{...content}</div>` wrapper — identical in every real instance, but
// re-typed per file with nothing enforcing that the spacing or step order
// (breadcrumb -> title -> subtitle -> toolbar -> content) stayed the same.
// WorkspaceLayout is that wrapper made explicit: it owns steps 1-4 via
// PageContextHeader and exposes a single `children` slot for step 5 (main
// content), so no page can drift onto a different header rhythm.

export function WorkspaceLayout({
  children,
  ...header
}: PageContextHeaderProps & { children: ReactNode }) {
  return (
    <div className="space-y-6">
      <PageContextHeader {...header} />
      {children}
    </div>
  );
}
