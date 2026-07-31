import type { ElementType } from "react";
import { Link } from "wouter";

// Shared stat tile — the one reusable "icon + label + live number" card used
// by every workspace overview (Operations, AI Center). Built on the app's
// existing `.panel` primitive (index.css) rather than a bespoke shadow/radius
// combo, so it matches the border-radius/shadow/border treatment every other
// panel in the app already uses. Previously each workspace hand-rolled its
// own near-identical tile markup — this replaces both.

export type StatTileTone = "neutral" | "success" | "warning" | "danger";

const TONE_CLASSES: Record<StatTileTone, string> = {
  neutral: "text-muted-foreground bg-muted",
  success: "text-emerald-600 bg-emerald-500/10 dark:text-emerald-400",
  warning: "text-amber-600 bg-amber-500/10 dark:text-amber-400",
  danger: "text-red-600 bg-red-500/10 dark:text-red-400",
};

export function StatTile({
  icon: Icon,
  label,
  description,
  value,
  valueLabel,
  tone = "neutral",
  href,
  onClick,
}: {
  icon: ElementType;
  label: string;
  description?: string;
  value?: number | string;
  valueLabel?: string;
  tone?: StatTileTone;
  href?: string;
  /** Alternative to `href` for tiles that trigger in-page behavior (e.g. a
   * tab switch) rather than navigation. */
  onClick?: () => void;
}) {
  const interactive = !!(href || onClick);
  const body = (
    <div
      className={`panel px-3 py-2.5 h-full transition-all duration-150 ${
        interactive ? "hover:border-primary/30 hover:-translate-y-0.5 cursor-pointer" : ""
      }`}
    >
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${TONE_CLASSES[tone]}`}>
        <Icon className="w-4 h-4" />
      </div>
      <p className="text-sm font-semibold text-foreground mt-2 truncate">{label}</p>
      {description && <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{description}</p>}
      {value !== undefined && (
        <p className="text-lg font-bold text-foreground kpi-number mt-1.5 leading-none">
          {value}
          {valueLabel && (
            <span className="text-[10px] font-medium text-muted-foreground/70 ms-1.5 tracking-normal">
              {valueLabel}
            </span>
          )}
        </p>
      )}
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="block focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 rounded-xl">
        {body}
      </Link>
    );
  }

  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className="block w-full text-start focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/50 rounded-xl"
      >
        {body}
      </button>
    );
  }

  return body;
}
