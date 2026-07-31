import type { ReactNode } from "react";

// Shared filter dropdown — one canonical native <select> shape (height,
// border token, radius, padding) so every "filter this list by X" control
// looks and behaves identically instead of each page hand-rolling its own
// slightly different class string. Width is caller-supplied via
// `className` (e.g. "min-w-52" or "w-full") since it varies by context.

export function FilterSelect({
  value,
  onChange,
  children,
  className = "",
  testId,
  ariaLabel,
}: {
  value: string;
  onChange: (value: string) => void;
  children: ReactNode;
  className?: string;
  testId?: string;
  ariaLabel?: string;
}) {
  return (
    <select
      className={`h-9 rounded-lg border border-input bg-background px-3 text-sm text-foreground ${className}`}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      data-testid={testId}
      aria-label={ariaLabel}
    >
      {children}
    </select>
  );
}
