import { AlertOctagon } from "lucide-react";

// Shared "failed to load" state — the destructive counterpart to EmptyState,
// built on the same `.panel` shell every other card in the app uses, so
// every load-failure moment looks identical instead of each page hand-rolling
// its own red box or dashed div.

export function ErrorState({
  title = "Failed to load",
  description = "Check your connection or permissions and try again.",
  action,
  className = "",
}: {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`panel panel-body flex items-center justify-center h-48 ${className}`}>
      <div className="text-center text-muted-foreground">
        <AlertOctagon className="w-8 h-8 mx-auto mb-2 text-destructive opacity-60" />
        <p className="text-sm font-medium text-foreground">{title}</p>
        <p className="text-xs mt-1">{description}</p>
        {action && <div className="mt-3">{action}</div>}
      </div>
    </div>
  );
}
