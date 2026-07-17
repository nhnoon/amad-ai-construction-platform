import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Loader2, Circle } from "lucide-react";

// Staged execution progress for "Analyze with AMAD AI" — replaces a bare
// spinner + "Analyzing..." with named stages the user can actually follow
// (Product UX Phase 1 §3). The backend runs this as a single request (see
// AMAD AI Stabilization — evidence+risk gathering is deterministic and
// sub-second, Hermes reasoning gets a ~45s budget, JSON assembly is
// near-instant); this component does not change that call or invent a
// streaming protocol, it maps the known, measured shape of that one
// request onto stage timings so the wait feels legible instead of opaque.
// Stage 3 (Hermes Reasoning) is intentionally indeterminate — its real
// duration varies per report — everything else has a short, honest,
// fixed duration based on the backend's own measured sub-2s floor for
// evidence + risk scoring.

export type Stage = "evidence" | "risk" | "reasoning" | "preparing" | "done";

const STAGES: { key: Stage; label: string }[] = [
  { key: "evidence", label: "Collecting Evidence" },
  { key: "risk", label: "Calculating Risk" },
  { key: "reasoning", label: "Hermes Reasoning" },
  { key: "preparing", label: "Preparing Report" },
  { key: "done", label: "Completed" },
];

const STAGE_INDEX: Record<Stage, number> = { evidence: 0, risk: 1, reasoning: 2, preparing: 3, done: 4 };

/** Drives `evidence -> risk -> reasoning` automatically on a short fixed
 * timer (matching the backend's own sub-2s deterministic floor), then
 * holds at `reasoning` until the caller advances it to `preparing`/`done`
 * once the actual response arrives. */
export function useAnalysisStages(active: boolean) {
  const [stage, setStage] = useState<Stage>("evidence");
  const timers = useRef<number[]>([]);

  useEffect(() => {
    timers.current.forEach((id) => window.clearTimeout(id));
    timers.current = [];
    if (!active) {
      setStage("evidence");
      return;
    }
    timers.current.push(window.setTimeout(() => setStage("risk"), 700));
    timers.current.push(window.setTimeout(() => setStage("reasoning"), 1600));
    return () => timers.current.forEach((id) => window.clearTimeout(id));
  }, [active]);

  return [stage, setStage] as const;
}

export function SiteReportStageProgress({ stage }: { stage: Stage }) {
  const activeIndex = STAGE_INDEX[stage];
  return (
    <div className="space-y-0.5" role="status" aria-live="polite">
      {STAGES.map((s, i) => {
        const isDone = i < activeIndex || stage === "done";
        const isActive = i === activeIndex && stage !== "done";
        return (
          <div key={s.key} className="flex items-center gap-2.5 py-1">
            {isDone ? (
              <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
            ) : isActive ? (
              <Loader2 className="h-4 w-4 text-primary animate-spin shrink-0" />
            ) : (
              <Circle className="h-4 w-4 text-muted-foreground/30 shrink-0" />
            )}
            <span
              className={`text-xs ${
                isDone ? "text-foreground/70" : isActive ? "text-foreground font-medium" : "text-muted-foreground/50"
              }`}
            >
              {s.label}
              {isActive && s.key === "reasoning" && (
                <span className="text-muted-foreground font-normal"> — usually under a minute</span>
              )}
            </span>
          </div>
        );
      })}
    </div>
  );
}
