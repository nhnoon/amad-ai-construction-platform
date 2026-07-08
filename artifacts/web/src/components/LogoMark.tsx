/**
 * LogoMark — Amad Three Pillars symbol
 *
 * Uses `currentColor` fill so the mark inherits the parent's CSS `color`.
 * Control colour with Tailwind `text-*` classes on the parent or this element.
 *
 * Examples:
 *   <LogoMark className="w-10 h-10 text-white" />        — white on dark bg
 *   <LogoMark className="w-8 h-8 text-[#0D1F3C]" />     — navy on light bg
 *   <LogoMark className="w-6 h-6 text-amber-500" />      — gold accent
 */
export function LogoMark({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      focusable="false"
      className={className}
    >
      {/* Left pillar — support column */}
      <rect x="5" y="22" width="10" height="22" rx="1.5" fill="currentColor" />
      {/* Centre pillar — the commanding column, tallest */}
      <rect x="19" y="8" width="10" height="36" rx="1.5" fill="currentColor" />
      {/* Right pillar — mirrors left, structural symmetry */}
      <rect x="33" y="22" width="10" height="22" rx="1.5" fill="currentColor" />
      {/* Foundation baseline — everything rests on this */}
      <rect x="3" y="44" width="42" height="2" rx="1" fill="currentColor" />
    </svg>
  );
}
