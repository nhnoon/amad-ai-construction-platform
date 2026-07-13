import { CheckCircle2, Clock, Loader2, XCircle, ShieldCheck, ScanText, Building2, Folder } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// Standardized badge set for the Documents workspace — one shared source of
// truth for size/spacing/colors so every badge on this page (list cards,
// detail panel, section headers) looks identical. Presentation only — no
// change to any status value or API shape.

const BASE_BADGE_CLASS = "gap-1.5 text-xs font-medium border-transparent";

export function StatusBadge({ status }: { status: "pending" | "processing" | "completed" | "failed" | string }) {
  const map: Record<string, { icon: typeof Clock; className: string; label: string }> = {
    pending: { icon: Clock, className: "bg-muted text-muted-foreground", label: "Pending" },
    processing: { icon: Loader2, className: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400", label: "Processing" },
    completed: { icon: CheckCircle2, className: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400", label: "Completed" },
    failed: { icon: XCircle, className: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400", label: "Failed" },
  };
  const entry = map[status] ?? map.pending;
  const Icon = entry.icon;
  return (
    <Badge className={cn(BASE_BADGE_CLASS, entry.className)}>
      <Icon className={cn("w-3 h-3", status === "processing" && "animate-spin")} />
      {entry.label}
    </Badge>
  );
}

/** Shown instead of a technical "JSON parsing" explanation when structured
 * fields were recovered via the deterministic labeled-text fallback rather
 * than the AI provider's own structured response. */
export function ValidatedExtractionBadge() {
  return (
    <Badge className={cn(BASE_BADGE_CLASS, "bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-400")}>
      <ShieldCheck className="w-3 h-3" />
      Validated Extraction
    </Badge>
  );
}

/** Shown once OCR has completed, signaling the document is ready for
 * contract analysis — replaces a plain muted-text hint. */
export function OcrReadyBadge() {
  return (
    <Badge className={cn(BASE_BADGE_CLASS, "bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-400")}>
      <ScanText className="w-3 h-3" />
      OCR Ready
    </Badge>
  );
}

export function ScopeBadge({ isGeneral, className }: { isGeneral: boolean; className?: string }) {
  return (
    <Badge
      variant={isGeneral ? "secondary" : "outline"}
      className={cn(BASE_BADGE_CLASS, "border", isGeneral ? "border-transparent" : "border-border", className)}
    >
      {isGeneral ? <Building2 className="w-3 h-3" /> : <Folder className="w-3 h-3" />}
      {isGeneral ? "General" : "Project"}
    </Badge>
  );
}
