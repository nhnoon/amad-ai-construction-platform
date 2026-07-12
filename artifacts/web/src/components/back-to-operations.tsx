import { useLocation } from "wouter";
import { useTranslation } from "react-i18next";
import { ArrowLeft } from "lucide-react";
import { cn } from "@/lib/utils";

// Shared back-navigation control for pages that live one level under
// /operations (Procurement, Meetings, ...). Kept as its own component so
// both pages render byte-identical markup and stay in sync if the target
// route ever changes.
export function BackToOperations() {
  const { t, i18n } = useTranslation();
  const [, setLocation] = useLocation();
  const isRTL = i18n.language?.startsWith("ar");

  return (
    <button
      type="button"
      onClick={() => setLocation("/operations")}
      className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
    >
      <ArrowLeft className={cn("w-4 h-4 shrink-0", isRTL && "scale-x-[-1]")} />
      <span>{t("Back to Operations")}</span>
    </button>
  );
}
