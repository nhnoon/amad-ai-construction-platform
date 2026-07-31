import { Building2, ClipboardList, FileSignature, CalendarDays, Radar } from "lucide-react";
import { useCurrentEntity, type CurrentEntityKind } from "@/context/CurrentEntityContext";
import { cn } from "@/lib/utils";

// Contextual Hermes indicator (Phase 2 §2): "Currently analyzing: Project
// PRJ-001" / "Contract CT-15" / "Site Report SR-4" — a prominent, named
// element rather than the small inline "· Context: X" tag that used to be
// the only signal. Purely a read of CurrentEntityContext; renders nothing
// when no page has registered an entity (e.g. the dashboard, a list page).

const KIND_META: Record<CurrentEntityKind, { icon: typeof Building2; label: string }> = {
  project: { icon: Building2, label: "Project" },
  site_report: { icon: ClipboardList, label: "Site Report" },
  contract: { icon: FileSignature, label: "Contract" },
  meeting: { icon: CalendarDays, label: "Meeting" },
};

export function CurrentlyAnalyzing({ variant = "light", className }: { variant?: "light" | "dark"; className?: string }) {
  const entity = useCurrentEntity();
  if (!entity) return null;
  const meta = KIND_META[entity.kind];
  const Icon = meta.icon;

  return (
    <div
      className={cn(
        "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm",
        variant === "dark"
          ? "border border-white/10 bg-white/[0.06] text-white/85"
          : "border border-primary/25 bg-primary/[0.06] text-foreground",
        className,
      )}
    >
      <Radar className={cn("h-3.5 w-3.5 shrink-0 animate-pulse", variant === "dark" ? "text-emerald-400" : "text-primary")} />
      <span className={cn("text-xs", variant === "dark" ? "text-white/50" : "text-muted-foreground")}>
        Currently analyzing:
      </span>
      <span className="inline-flex items-center gap-1.5 font-semibold truncate">
        <Icon className="h-3.5 w-3.5 shrink-0" />
        {meta.label} {entity.code}
        {entity.label && <span className="font-normal opacity-70 truncate">— {entity.label}</span>}
      </span>
    </div>
  );
}
