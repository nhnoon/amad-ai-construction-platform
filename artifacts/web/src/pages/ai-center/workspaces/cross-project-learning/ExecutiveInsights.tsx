import { Repeat, Target, AlertTriangle, Truck, Boxes, Sparkles } from "lucide-react";
import type { CrossProjectLearningSnapshot } from "@/lib/mockCrossProjectLearning";
import { DemoDataBadge } from "./shared";

function Section({ icon: Icon, title, children }: { icon: typeof Repeat; title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
        <Icon className="w-3 h-3" /> {title}
      </p>
      {children}
    </div>
  );
}

// Executive Insights — the portfolio-wide "what does our history teach
// us" synthesis: top recurring problems, most successful actions, most
// common causes, and the suppliers/materials that show up most often.
// Distinct from the per-item AI Recommendation Panel inside the drawer.

export function ExecutiveInsights({ insights }: { insights: CrossProjectLearningSnapshot["executiveInsights"] }) {
  return (
    <div className="panel panel-body space-y-4">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h3 className="text-sm font-bold text-foreground flex items-center gap-1.5"><Sparkles className="w-4 h-4 text-primary" /> Executive Insights</h3>
        <DemoDataBadge />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Section icon={Repeat} title="Top Recurring Problems">
          {insights.topRecurringProblems.length === 0 ? (
            <p className="text-xs text-muted-foreground">No issue has recurred across more than one project yet.</p>
          ) : (
            <ul className="space-y-1.5">
              {insights.topRecurringProblems.map((p) => (
                <li key={p.templateId} className="flex items-center justify-between gap-2 text-sm">
                  <span className="text-foreground">{p.title}</span>
                  <span className="text-xs font-semibold text-muted-foreground shrink-0">{p.occurrences}&times; &middot; {p.projects.length} project{p.projects.length === 1 ? "" : "s"}</span>
                </li>
              ))}
            </ul>
          )}
        </Section>

        <Section icon={Target} title="Most Successful Actions">
          <ul className="space-y-1">
            {insights.mostSuccessfulActions.map((a, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-foreground"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-emerald-500" /> {a}</li>
            ))}
          </ul>
        </Section>

        <Section icon={AlertTriangle} title="Most Common Causes">
          <ul className="space-y-1">
            {insights.mostCommonCauses.map((c, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-foreground"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-amber-500" /> {c}</li>
            ))}
          </ul>
        </Section>

        <div className="space-y-4">
          <Section icon={Truck} title="Frequently Affected Suppliers">
            {insights.frequentSuppliers.length === 0 ? <p className="text-xs text-muted-foreground">No supplier appears in more than one case.</p> : (
              <div className="flex flex-wrap gap-1.5">
                {insights.frequentSuppliers.map((s) => (
                  <span key={s.name} className="text-[11px] rounded-full bg-muted px-2.5 py-1 text-muted-foreground">{s.name} &middot; {s.count}&times;</span>
                ))}
              </div>
            )}
          </Section>
          <Section icon={Boxes} title="Frequently Delayed Materials">
            {insights.frequentMaterials.length === 0 ? <p className="text-xs text-muted-foreground">No material appears in more than one case.</p> : (
              <div className="flex flex-wrap gap-1.5">
                {insights.frequentMaterials.map((m) => (
                  <span key={m.name} className="text-[11px] rounded-full bg-muted px-2.5 py-1 text-muted-foreground">{m.name} &middot; {m.count}&times;</span>
                ))}
              </div>
            )}
          </Section>
        </div>
      </div>
    </div>
  );
}
