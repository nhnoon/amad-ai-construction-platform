import { useLocation } from "wouter";
import { useTranslation } from "react-i18next";
import { ArrowLeft } from "lucide-react";
import { cn } from "@/lib/utils";

// Generic back-navigation control. RTL-aware: the arrow flips direction in
// Arabic (matching the send-icon flip pattern already used in AIDrawer),
// and stays a plain top-level element (no `hidden` breakpoint classes) so
// it never disappears on mobile.
export function BackButton({ to, label }: { to: string; label: string }) {
  const { t, i18n } = useTranslation();
  const [, setLocation] = useLocation();
  const isRTL = i18n.language?.startsWith("ar");

  return (
    <button
      type="button"
      onClick={() => setLocation(to)}
      className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
    >
      <ArrowLeft className={cn("w-4 h-4 shrink-0", isRTL && "scale-x-[-1]")} />
      <span>{t(label)}</span>
    </button>
  );
}
