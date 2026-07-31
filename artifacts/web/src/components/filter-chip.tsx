import type { ElementType, ReactNode } from "react";

// Shared quick-filter pill — the "All (12) / Category (4) / ..." chip row
// used by Memory Center's category filter and Project Workspace's timeline
// type filter. Previously each file hand-rolled an identical pill button;
// this is the one shared implementation both reuse.

export type FilterChipTone = "default" | "amber";

export function FilterChip({
  active,
  onClick,
  icon: Icon,
  iconClassName = "w-3 h-3",
  tone = "default",
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon?: ElementType;
  iconClassName?: string;
  tone?: FilterChipTone;
  children: ReactNode;
}) {
  const activeClass =
    tone === "amber"
      ? "bg-amber-500 text-white border-amber-500"
      : "bg-primary text-primary-foreground border-primary";
  const inactiveClass =
    tone === "amber"
      ? "border-amber-400/50 text-amber-600 dark:text-amber-400 hover:border-amber-400"
      : "border-border text-muted-foreground hover:text-foreground hover:border-primary/40";

  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border transition-colors ${
        active ? activeClass : inactiveClass
      }`}
    >
      {Icon && <Icon className={iconClassName} />}
      {children}
    </button>
  );
}
