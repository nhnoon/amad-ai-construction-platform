import { useState } from "react";
import { Link } from "wouter";
import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  BarChart, Bar, Cell,
} from "recharts";
import {
  Building2, FileSignature, AlertTriangle, Wrench, Scale, Wallet, Truck,
  Sparkles, ListChecks, Target, Users, ExternalLink,
} from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { EmptyState } from "@/components/ui/empty-state";
import { PageTabs } from "@/components/page-tabs";
import type { SupplierProfile } from "@/lib/mockSupplierRisk";
import {
  BAND_BADGE, CONTRACT_STATUS_BADGE, CHART_TOOLTIP_STYLE, DemoDataBadge,
  heatColor, formatDate, formatSar,
} from "./shared";

const AXIS_TICK = { fontSize: 9, fill: "hsl(var(--muted-foreground))" };

type DrawerTab = "overview" | "issues" | "performance" | "ai";

function MiniTrend({ title, data, dataKey, color, suffix = "" }: {
  title: string; data: SupplierProfile["performanceTrend"]; dataKey: keyof SupplierProfile["performanceTrend"][number]; color: string; suffix?: string;
}) {
  return (
    <div className="panel">
      <div className="panel-header py-2 px-3">
        <span className="text-xs font-semibold text-foreground">{title}</span>
      </div>
      <div className="h-[110px] px-2 pb-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 6, right: 8, left: -22, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
            <XAxis dataKey="weekLabel" tick={AXIS_TICK} axisLine={false} tickLine={false} interval={2} />
            <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} width={26} />
            <Tooltip contentStyle={CHART_TOOLTIP_STYLE} formatter={(v: number) => [`${v}${suffix}`, ""]} />
            <Line type="monotone" dataKey={dataKey} stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function SupplierDetailDrawer({
  supplier,
  open,
  onOpenChange,
}: {
  supplier: SupplierProfile | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [tab, setTab] = useState<DrawerTab>("overview");

  if (!supplier) return null;
  const openIssueCount = supplier.openIssues.filter((i) => i.status !== "Resolved").length;

  return (
    <Sheet open={open} onOpenChange={(o) => { onOpenChange(o); if (!o) setTab("overview"); }}>
      <SheetContent className="w-full sm:max-w-xl overflow-y-auto">
        <SheetHeader className="text-start space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`badge ${BAND_BADGE[supplier.riskBand]}`}>{supplier.riskBand} risk</span>
            <span className={`badge ${CONTRACT_STATUS_BADGE[supplier.contractStatus]}`}>{supplier.contractStatus}</span>
            <DemoDataBadge />
          </div>
          <SheetTitle className="text-lg leading-snug">{supplier.name}</SheetTitle>
          <SheetDescription className="text-xs">
            {supplier.category} &middot; {supplier.city} ({supplier.region}) &middot; Status: {supplier.status}
          </SheetDescription>
        </SheetHeader>

        <div className="mt-4">
          <PageTabs<DrawerTab>
            tabs={[
              { id: "overview", label: "Overview" },
              { id: "issues", label: "Issues & Claims", count: openIssueCount + supplier.claims.length },
              { id: "performance", label: "Performance" },
              { id: "ai", label: "AI Insights" },
            ]}
            value={tab}
            onChange={setTab}
          />
        </div>

        <div className="mt-4 space-y-5">
          {tab === "overview" && (
            <>
              <div className="grid grid-cols-2 gap-2">
                {[
                  { label: "Overall Risk", value: `${supplier.overallRiskScore}/100`, color: heatColor(supplier.overallRiskScore) },
                  { label: "Delivery", value: `${supplier.deliveryPerformance}%`, color: heatColor(100 - supplier.deliveryPerformance) },
                  { label: "Quality", value: `${supplier.qualityScore}%`, color: heatColor(100 - supplier.qualityScore) },
                  { label: "Financial Stability", value: `${supplier.financialStability}%`, color: heatColor(100 - supplier.financialStability) },
                ].map((m) => (
                  <div key={m.label} className="rounded-lg border border-border/60 px-3 py-2">
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wide">{m.label}</p>
                    <p className="text-lg font-bold tabular-nums" style={{ color: m.color }}>{m.value}</p>
                  </div>
                ))}
              </div>

              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Wallet className="w-3 h-3" /> Payment Status</p>
                <div className="rounded-lg border border-border/60 p-3 grid grid-cols-3 gap-2 text-center">
                  <div><p className="text-sm font-bold text-foreground">{supplier.paymentStatus.onTimePct}%</p><p className="text-[10px] text-muted-foreground">on-time</p></div>
                  <div><p className="text-sm font-bold text-foreground">{supplier.paymentStatus.averageDelayDays}d</p><p className="text-[10px] text-muted-foreground">avg delay</p></div>
                  <div><p className="text-sm font-bold text-foreground">{formatSar(supplier.paymentStatus.outstandingAmountSar)}</p><p className="text-[10px] text-muted-foreground">outstanding</p></div>
                </div>
              </div>

              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Building2 className="w-3 h-3" /> Projects Served ({supplier.projectsServed.length})</p>
                {supplier.projectsServed.length === 0 ? (
                  <p className="text-xs text-muted-foreground">Not currently assigned to any project.</p>
                ) : (
                  <ul className="space-y-1">
                    {supplier.projectsServed.map((p) => (
                      <li key={p.projectId}>
                        <Link href={`/projects/${p.projectId}`} className="flex items-center justify-between text-xs rounded-lg border border-border/60 px-3 py-2 hover:border-primary/40 transition-colors">
                          <span className="text-foreground">{p.projectCode} &middot; {p.projectName}</span>
                          <ExternalLink className="w-3 h-3 text-muted-foreground" />
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><FileSignature className="w-3 h-3" /> Contracts ({supplier.contracts.length})</p>
                {supplier.contracts.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No contracts on record.</p>
                ) : (
                  <ul className="space-y-1.5">
                    {supplier.contracts.map((c) => (
                      <li key={c.id} className="rounded-lg border border-border/60 px-3 py-2 space-y-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-medium text-foreground">{c.title}</span>
                          <span className={`badge ${CONTRACT_STATUS_BADGE[c.status]} text-[10px]`}>{c.status}</span>
                        </div>
                        <p className="text-[11px] text-muted-foreground">{formatSar(c.value)} &middot; expires {formatDate(c.expiryDate)}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}

          {tab === "issues" && (
            <>
              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><AlertTriangle className="w-3 h-3" /> Open Issues ({supplier.openIssues.length})</p>
                {supplier.openIssues.length === 0 ? <EmptyState icon={AlertTriangle} title="No issues on record" /> : (
                  <ul className="space-y-1.5">
                    {supplier.openIssues.map((i) => (
                      <li key={i.id} className="rounded-lg border border-border/60 px-3 py-2 space-y-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-medium text-foreground">{i.title}</span>
                          <span className={`badge ${BAND_BADGE[i.severity]} text-[10px]`}>{i.severity}</span>
                        </div>
                        <p className="text-[11px] text-muted-foreground">{i.status} &middot; {formatDate(i.date)}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Wrench className="w-3 h-3" /> Corrective Actions ({supplier.correctiveActions.length})</p>
                {supplier.correctiveActions.length === 0 ? <p className="text-xs text-muted-foreground">No corrective actions on record.</p> : (
                  <ul className="space-y-1.5">
                    {supplier.correctiveActions.map((a) => (
                      <li key={a.id} className="flex items-center justify-between gap-2 rounded-lg border border-border/60 px-3 py-2 text-xs">
                        <span className="text-foreground">{a.title}</span>
                        <span className={`badge ${a.status === "Completed" ? "badge-success" : "badge-warning"} text-[10px]`}>{a.status}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Scale className="w-3 h-3" /> Claims ({supplier.claims.length})</p>
                {supplier.claims.length === 0 ? <p className="text-xs text-muted-foreground">No claims on record.</p> : (
                  <ul className="space-y-1.5">
                    {supplier.claims.map((c) => (
                      <li key={c.id} className="rounded-lg border border-border/60 px-3 py-2 space-y-1">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-medium text-foreground">{c.title}</span>
                          <span className="badge badge-neutral text-[10px]">{c.status}</span>
                        </div>
                        <p className="text-[11px] text-muted-foreground">{formatSar(c.amount)} &middot; {formatDate(c.date)}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </>
          )}

          {tab === "performance" && (
            <>
              <div className="grid grid-cols-2 gap-2.5">
                <MiniTrend title="Delivery Trend" data={supplier.performanceTrend} dataKey="delivery" color="#0ea5e9" suffix="%" />
                <MiniTrend title="Quality Trend" data={supplier.performanceTrend} dataKey="quality" color="#22c55e" suffix="%" />
                <MiniTrend title="Response Time" data={supplier.performanceTrend} dataKey="responseTimeHours" color="#a855f7" suffix="h" />
                <MiniTrend title="Contract Compliance" data={supplier.performanceTrend} dataKey="compliance" color="#f59e0b" suffix="%" />
              </div>

              <div className="panel">
                <div className="panel-header py-2 px-3"><span className="text-xs font-semibold text-foreground">Risk Breakdown</span></div>
                <div className="h-[160px] px-2 pb-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={supplier.riskBreakdown} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--border))" />
                      <XAxis type="number" domain={[0, 100]} tick={AXIS_TICK} axisLine={false} tickLine={false} />
                      <YAxis type="category" dataKey="label" width={110} tick={AXIS_TICK} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={CHART_TOOLTIP_STYLE} cursor={{ fill: "hsl(var(--muted))", opacity: 0.4 }} />
                      <Bar dataKey="score" radius={[0, 6, 6, 0]} isAnimationActive={false}>
                        {supplier.riskBreakdown.map((d, i) => <Cell key={i} fill={heatColor(d.score)} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Truck className="w-3 h-3" /> Delivery History</p>
                <ul className="space-y-1">
                  {supplier.deliveryHistory.map((d) => (
                    <li key={d.id} className="flex items-center justify-between gap-2 text-xs rounded-lg border border-border/60 px-3 py-1.5">
                      <span className="text-foreground">{d.orderRef} &middot; {d.description}</span>
                      <span className={d.onTime ? "text-emerald-600 dark:text-emerald-400" : "text-red-600 dark:text-red-400"}>
                        {d.onTime ? "On time" : `${d.daysLate}d late`}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}

          {tab === "ai" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <p className="text-sm font-bold text-foreground flex items-center gap-1.5"><Sparkles className="w-4 h-4 text-primary" /> AI Insights Panel</p>
                <DemoDataBadge />
              </div>
              <p className="text-xs text-muted-foreground -mt-2">
                Illustrative of the analysis Hermes would generate once grounded in this supplier's real records — not a live AI call.
              </p>

              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><ListChecks className="w-3 h-3" /> Top Supplier Risks</p>
                <ul className="space-y-1">
                  {supplier.aiInsights.topRisks.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-foreground"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary" /> {r}</li>
                  ))}
                </ul>
              </div>

              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Target className="w-3 h-3" /> Recommended Actions</p>
                <ul className="space-y-1">
                  {supplier.aiInsights.recommendedActions.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-foreground"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-emerald-500" /> {r}</li>
                  ))}
                </ul>
              </div>

              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Users className="w-3 h-3" /> Suggested Alternative Suppliers</p>
                {supplier.aiInsights.suggestedAlternatives.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No lower-risk alternative found in the same category yet.</p>
                ) : (
                  <ul className="space-y-1.5">
                    {supplier.aiInsights.suggestedAlternatives.map((alt) => (
                      <li key={alt.supplierId} className="flex items-center justify-between text-xs rounded-lg border border-border/60 px-3 py-2">
                        <span className="text-foreground">{alt.name}</span>
                        <span className="font-semibold" style={{ color: heatColor(alt.riskScore) }}>{alt.riskScore}/100</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Procurement Observations</p>
                <ul className="space-y-1">
                  {supplier.aiInsights.procurementObservations.map((o, i) => (
                    <li key={i} className="flex items-start gap-2 text-xs text-muted-foreground"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/50" /> {o}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
