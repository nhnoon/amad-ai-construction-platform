import { useState } from "react";
import { Link } from "wouter";
import { ResponsiveContainer, BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip } from "recharts";
import {
  Sparkles, ListChecks, Target, Users, Wrench, ExternalLink, Info, TrendingUp, TrendingDown, Minus,
} from "lucide-react";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { PageTabs } from "@/components/page-tabs";
import type { MaterialProfile } from "@/lib/mockMaterialIntelligence";
import {
  RISK_BADGE, SUPPLY_STATUS_BADGE, CHART_TOOLTIP_STYLE, DemoDataBadge,
  heatColor, formatSar, formatPrice, formatDate, formatPct,
} from "./shared";
import { PriceTrendChart } from "./PriceTrendChart";
import { PortfolioExposureTable } from "./PortfolioExposureTable";

const AXIS_TICK = { fontSize: 9, fill: "hsl(var(--muted-foreground))" };

type DrawerTab = "overview" | "history" | "exposure" | "suppliers" | "risks" | "ai";

function TrendPill({ pct }: { pct: number }) {
  const Icon = pct > 0 ? TrendingUp : pct < 0 ? TrendingDown : Minus;
  const tone = pct > 0 ? "text-red-600 dark:text-red-400" : pct < 0 ? "text-emerald-600 dark:text-emerald-400" : "text-muted-foreground";
  return <span className={`inline-flex items-center gap-1 text-xs font-semibold ${tone}`}><Icon className="w-3 h-3" /> {formatPct(pct)}</span>;
}

export function MaterialDetailDrawer({
  material,
  open,
  onOpenChange,
}: {
  material: MaterialProfile | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [tab, setTab] = useState<DrawerTab>("overview");
  if (!material) return null;

  return (
    <Sheet open={open} onOpenChange={(o) => { onOpenChange(o); if (!o) setTab("overview"); }}>
      <SheetContent className="w-full sm:max-w-xl overflow-y-auto">
        <SheetHeader className="text-start space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`badge ${RISK_BADGE[material.riskLevel]}`}>{material.riskLevel} risk</span>
            <span className={`badge ${SUPPLY_STATUS_BADGE[material.supplyStatus]}`}>{material.supplyStatus}</span>
            <DemoDataBadge />
          </div>
          <SheetTitle className="text-lg leading-snug">{material.name}</SheetTitle>
          <SheetDescription className="text-xs">
            {material.category} &middot; {material.region} &middot; per {material.unit}
          </SheetDescription>
        </SheetHeader>

        <div className="mt-4">
          <PageTabs<DrawerTab>
            tabs={[
              { id: "overview", label: "Overview" },
              { id: "history", label: "Price History" },
              { id: "exposure", label: "Exposure", count: material.affectedProjects.length },
              { id: "suppliers", label: "Suppliers", count: material.suppliers.length },
              { id: "risks", label: "Supply Risks", count: material.supplyRisks.length },
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
                <div className="rounded-lg border border-border/60 px-3 py-2">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Current Illustrative Price</p>
                  <p className="text-lg font-bold text-foreground tabular-nums">SAR {formatPrice(material.currentPrice)} <span className="text-xs font-normal text-muted-foreground">/{material.unit}</span></p>
                </div>
                <div className="rounded-lg border border-border/60 px-3 py-2">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Volatility</p>
                  <p className="text-lg font-bold tabular-nums" style={{ color: heatColor(material.volatility) }}>{material.volatility}/100</p>
                </div>
                <div className="rounded-lg border border-border/60 px-3 py-2">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide">30-Day / 90-Day Change</p>
                  <div className="flex items-center gap-2"><TrendPill pct={material.change30dPct} /><span className="text-muted-foreground">/</span><TrendPill pct={material.change90dPct} /></div>
                </div>
                <div className="rounded-lg border border-border/60 px-3 py-2">
                  <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Lead Time</p>
                  <p className="text-lg font-bold text-foreground tabular-nums">{material.avgLeadTimeDays}d <span className="text-xs font-normal text-muted-foreground">({material.leadTimeTrend.toLowerCase()})</span></p>
                </div>
              </div>

              <div className="rounded-lg border border-border/60 p-3 space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Info className="w-3 h-3" /> Forecast Range (90-day, illustrative)</p>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div><p className="text-sm font-bold text-emerald-600 dark:text-emerald-400">{formatPrice(material.forecast.best)}</p><p className="text-[10px] text-muted-foreground">Best</p></div>
                  <div><p className="text-sm font-bold text-foreground">{formatPrice(material.forecast.expected)}</p><p className="text-[10px] text-muted-foreground">Expected</p></div>
                  <div><p className="text-sm font-bold text-red-600 dark:text-red-400">{formatPrice(material.forecast.worst)}</p><p className="text-[10px] text-muted-foreground">Worst</p></div>
                </div>
              </div>

              <p className="text-[11px] text-muted-foreground">
                Source: {material.source} &middot; Last updated {formatDate(material.lastUpdated)}
              </p>
            </>
          )}

          {tab === "history" && (
            <>
              <PriceTrendChart
                data={material.priceHistory.map((p) => ({ period: p.period, price: p.price }))}
                series={[{ key: "price", label: material.name, color: "#0ea5e9" }]}
                valueSuffix={` SAR/${material.unit}`}
              />
              <div className="rounded-lg border border-border/60 p-3">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-2">Risk Breakdown</p>
                <div className="h-[150px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={material.riskBreakdown} layout="vertical" margin={{ top: 0, right: 16, left: 8, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--border))" />
                      <XAxis type="number" domain={[0, 100]} tick={AXIS_TICK} axisLine={false} tickLine={false} />
                      <YAxis type="category" dataKey="label" width={120} tick={AXIS_TICK} axisLine={false} tickLine={false} />
                      <Tooltip contentStyle={CHART_TOOLTIP_STYLE} cursor={{ fill: "hsl(var(--muted))", opacity: 0.4 }} />
                      <Bar dataKey="score" radius={[0, 6, 6, 0]} isAnimationActive={false}>
                        {material.riskBreakdown.map((d, i) => <Cell key={i} fill={heatColor(d.score)} />)}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </>
          )}

          {tab === "exposure" && (
            <PortfolioExposureTable
              rows={material.affectedProjects.map((p) => ({ ...p, materialId: material.id, materialName: material.name }))}
              showMaterialColumn={false}
              showFilters={false}
            />
          )}

          {tab === "suppliers" && (
            <div className="space-y-1.5">
              {material.suppliers.length === 0 ? (
                <p className="text-xs text-muted-foreground">No suppliers on record for this material.</p>
              ) : (
                material.suppliers.map((s) => (
                  <div key={s.supplierId} className="rounded-lg border border-border/60 p-3 space-y-1.5">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium text-foreground">{s.name}</span>
                      <span className="text-xs font-semibold text-foreground">{s.shareOfSupplyPct}%</span>
                    </div>
                    <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                      <div className="h-full rounded-full bg-primary" style={{ width: `${s.shareOfSupplyPct}%` }} />
                    </div>
                  </div>
                ))
              )}
              {material.alternatives.length > 0 && (
                <div className="pt-2 space-y-1.5">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Users className="w-3 h-3" /> Alternative Materials</p>
                  {material.alternatives.map((a) => (
                    <div key={a.name} className="rounded-lg border border-border/60 px-3 py-2">
                      <p className="text-xs font-medium text-foreground">{a.name}</p>
                      <p className="text-[11px] text-muted-foreground">{a.note}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === "risks" && (
            <>
              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Supply Risks</p>
                {material.supplyRisks.map((r) => (
                  <div key={r.id} className="rounded-lg border border-border/60 px-3 py-2 space-y-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-medium text-foreground">{r.title}</span>
                      <span className={`badge ${RISK_BADGE[r.severity]} text-[10px]`}>{r.severity}</span>
                    </div>
                    <p className="text-[11px] text-muted-foreground">{r.description}</p>
                  </div>
                ))}
              </div>
              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Wrench className="w-3 h-3" /> Open Procurement Issues</p>
                {material.procurementIssues.length === 0 ? (
                  <p className="text-xs text-muted-foreground">No open procurement issues for this material.</p>
                ) : (
                  material.procurementIssues.map((i) => (
                    <div key={i.id} className="flex items-center justify-between gap-2 rounded-lg border border-border/60 px-3 py-2 text-xs">
                      <span className="text-foreground">{i.title}</span>
                      <span className="badge badge-neutral text-[10px]">{i.status}</span>
                    </div>
                  ))
                )}
              </div>
            </>
          )}

          {tab === "ai" && (
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <p className="text-sm font-bold text-foreground flex items-center gap-1.5"><Sparkles className="w-4 h-4 text-primary" /> AI Insights</p>
                <DemoDataBadge />
              </div>
              <p className="text-xs text-muted-foreground -mt-2">
                Illustrative of the analysis Hermes would generate once grounded in real market data — not a live AI call.
              </p>
              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><ListChecks className="w-3 h-3" /> Top Risks</p>
                <ul className="space-y-1">
                  {material.aiInsights.topRisks.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-foreground"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-primary" /> {r}</li>
                  ))}
                </ul>
              </div>
              <div className="space-y-1.5">
                <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Target className="w-3 h-3" /> Recommended Actions</p>
                <ul className="space-y-1">
                  {material.aiInsights.recommendedActions.map((r, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-foreground"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-emerald-500" /> {r}</li>
                  ))}
                </ul>
              </div>
              {material.aiInsights.suggestedAlternatives.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5"><Users className="w-3 h-3" /> Suggested Alternatives</p>
                  <ul className="space-y-1">
                    {material.aiInsights.suggestedAlternatives.map((a, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-foreground"><span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/50" /> {a}</li>
                    ))}
                  </ul>
                </div>
              )}
              {material.affectedProjects[0] && (
                <Link href={`/projects/${material.affectedProjects[0].projectId}`} className="inline-flex items-center gap-1 text-xs text-primary hover:underline">
                  View most-exposed project <ExternalLink className="w-3 h-3" />
                </Link>
              )}
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
