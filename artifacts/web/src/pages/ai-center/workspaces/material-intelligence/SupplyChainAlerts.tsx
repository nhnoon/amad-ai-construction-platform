import { useState } from "react";
import {
  Bell, TrendingUp, Truck, PackageX, Clock3, Users, FileSignature, ShieldAlert, type LucideIcon,
} from "lucide-react";
import type { AlertType, SupplyChainAlert } from "@/lib/mockMaterialIntelligence";
import { EmptyState } from "@/components/ui/empty-state";
import { FilterChip } from "@/components/filter-chip";
import { RISK_BADGE, formatSar, formatDate } from "./shared";

const ALERT_ICON: Record<AlertType, LucideIcon> = {
  price_increase: TrendingUp,
  delivery_delay: Truck,
  shortage: PackageX,
  lead_time_increase: Clock3,
  supplier_dependency: Users,
  contract_expiry: FileSignature,
  unapproved_substitute: ShieldAlert,
};

const STATUS_BADGE: Record<SupplyChainAlert["status"], string> = {
  Open: "badge-warning",
  Acknowledged: "badge-info",
  Resolved: "badge-success",
};

// Supply Chain Alerts — realistic named scenarios (price increases,
// delivery delays, shortages, lead-time increases, supplier dependency,
// contract expiries, unapproved substitutes), each carrying severity,
// affected projects, estimated impact, and a recommended action.

export function SupplyChainAlerts({ alerts }: { alerts: SupplyChainAlert[] }) {
  const [statusFilter, setStatusFilter] = useState<SupplyChainAlert["status"] | "all">("all");
  const filtered = alerts.filter((a) => statusFilter === "all" || a.status === statusFilter);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-1.5">
        {(["all", "Open", "Acknowledged", "Resolved"] as const).map((s) => (
          <FilterChip key={s} active={statusFilter === s} onClick={() => setStatusFilter(s)}>
            {s === "all" ? `All (${alerts.length})` : `${s} (${alerts.filter((a) => a.status === s).length})`}
          </FilterChip>
        ))}
      </div>

      {filtered.length === 0 ? (
        <EmptyState icon={Bell} title="No alerts match the current filter" />
      ) : (
        <div className="grid gap-2.5 sm:grid-cols-2">
          {filtered.map((alert) => {
            const Icon = ALERT_ICON[alert.type];
            return (
              <div key={alert.id} className="panel panel-body space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-start gap-2.5 min-w-0">
                    <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 mt-0.5">
                      <Icon className="w-4 h-4 text-primary" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-foreground leading-snug">{alert.title}</p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">{alert.materialName} &middot; {formatDate(alert.date)}</p>
                    </div>
                  </div>
                  <span className={`badge ${RISK_BADGE[alert.severity]} text-[10px] shrink-0`}>{alert.severity}</span>
                </div>

                <p className="text-xs text-muted-foreground">
                  Affects {alert.affectedProjects.length === 0 ? "no active projects" : alert.affectedProjects.map((p) => p.projectCode).join(", ")}
                  {" "}&middot; est. impact {formatSar(alert.estimatedImpactSar)}
                </p>

                <div className="rounded-lg bg-primary/5 border border-primary/10 px-3 py-2">
                  <p className="text-xs text-foreground">{alert.recommendedAction}</p>
                </div>

                <span className={`badge ${STATUS_BADGE[alert.status]} text-[10px]`}>{alert.status}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
