// AMAD v2 — canonical "synthetic data" marker. Every demo/mock-sourced
// figure or section carries this exact badge (gold, dashed-free pill,
// 9px label) so the distinction from real, already-fetched data stays
// visually consistent everywhere it appears. Extracted from the
// AI Center Overview implementation, where this markup was repeated
// inline five times with an identical class string.

export function DemoDataBadge({ label = "Demo Data" }: { label?: string }) {
  return <span className="badge badge-gold text-[9px]">{label}</span>;
}
