import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";

// Shared search box — Input + leading Search icon, positioned with logical
// `start`/`ps` so it mirrors correctly in RTL. Every page's "search this
// list" box should use this instead of hand-rolling the icon + input pair.

export function SearchInput({
  value,
  onChange,
  placeholder,
  className = "",
  testId,
  /** Toolbar-embedded filter (e.g. a workspace header's "Filter modules…")
   * rather than a list page's primary search — smaller height/icon/text,
   * matching the compact controls it sits next to. */
  compact = false,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  testId?: string;
  compact?: boolean;
}) {
  return (
    <div className={`relative ${compact ? "" : "flex-1 min-w-52 max-w-sm"} ${className}`}>
      <Search
        className={
          compact
            ? "absolute start-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/60 pointer-events-none"
            : "absolute start-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none"
        }
      />
      <Input
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={compact ? "ps-8 h-8 text-xs" : "ps-9 h-9"}
        data-testid={testId}
      />
    </div>
  );
}
