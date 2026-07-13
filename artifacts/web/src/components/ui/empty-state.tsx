import type { ElementType, ReactNode } from "react";

// Shared empty state — icon + title + description + optional primary action,
// built on the existing `.empty-state*` utility classes in index.css so
// every "no data" moment across the app looks the same instead of each page
// hand-rolling its own version.

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className = "",
}: {
  icon: ElementType;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={`empty-state ${className}`}>
      <Icon className="empty-state-icon" />
      <p className="empty-state-title">{title}</p>
      {description && <p className="empty-state-body max-w-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
