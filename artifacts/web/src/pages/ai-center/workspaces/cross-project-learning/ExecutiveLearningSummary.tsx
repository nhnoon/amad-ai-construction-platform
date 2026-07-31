import { BookOpen, Building2, Repeat, CheckCircle2, Gauge } from "lucide-react";
import { StatTile } from "@/components/stat-tile";
import type { CrossProjectLearningSnapshot } from "@/lib/mockCrossProjectLearning";

// Executive Learning Summary — the headline "how much organizational
// knowledge do we have, and is it useful" snapshot at the top of the page.

export function ExecutiveLearningSummary({ stats }: { stats: CrossProjectLearningSnapshot["stats"] }) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5">
        <StatTile icon={BookOpen} label="Knowledge Items" value={stats.totalKnowledgeItems} tone="neutral" />
        <StatTile icon={Building2} label="Projects Represented" value={stats.projectsRepresented} tone="neutral" />
        <StatTile icon={Repeat} label="Recurring Patterns" value={stats.recurringPatternCount} tone={stats.recurringPatternCount > 0 ? "warning" : "success"} />
        <StatTile icon={CheckCircle2} label="Successful Resolutions" value={`${stats.successfulResolutionPct}%`} tone={stats.successfulResolutionPct >= 50 ? "success" : "warning"} />
        <StatTile icon={Gauge} label="Avg Match Confidence" value={`${stats.avgConfidence}%`} tone="neutral" />
      </div>
      <p className="text-sm text-muted-foreground">
        {stats.recurringPatternCount} issue{stats.recurringPatternCount === 1 ? " has" : "s have"} recurred across more than one project —
        the strongest signal that organizational experience, not just per-project history, is available to reuse.
      </p>
    </div>
  );
}
