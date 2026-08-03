import { useMemo, useState } from "react";
import { Link } from "wouter";
import { useTranslation } from "react-i18next";
import { ListChecks } from "lucide-react";
import { useListMyWork, useListProjects } from "@workspace/api-client-react";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { FilterChip } from "@/components/filter-chip";
import { FilterSelect } from "@/components/filter-select";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { TableSkeletonRows } from "@/components/ui/table-skeleton";
import { entityIcon, entityLabel, frontendLinkFor, genericStatusBadgeClass, type WorkEntityType } from "@/lib/entityLinks";

const ENTITY_FILTERS: { id: WorkEntityType | "all"; label: string }[] = [
  { id: "all", label: "All" },
  { id: "project_risk", label: "Risks" },
  { id: "project_issue", label: "Issues" },
  { id: "action_item", label: "Action Items" },
  { id: "safety_event", label: "Safety Events" },
  { id: "ncr", label: "NCRs" },
  { id: "purchase_request", label: "Purchase Requests" },
  { id: "approval", label: "Approvals" },
];

const PAGE_LIMIT = 100;

export default function Tasks() {
  const { t } = useTranslation();
  const [entityType, setEntityType] = useState<WorkEntityType | "all">("all");
  const [projectId, setProjectId] = useState<string>("all");
  const [openOnly, setOpenOnly] = useState(false);
  const [overdue, setOverdue] = useState(false);
  const [dueSoon, setDueSoon] = useState(false);

  const { data: projects } = useListProjects({ limit: 200 });

  const { data: items, isLoading, isError } = useListMyWork({
    entity_type: entityType === "all" ? undefined : entityType,
    project_id: projectId === "all" ? undefined : Number(projectId),
    open_only: openOnly,
    overdue,
    due_soon: dueSoon,
    limit: PAGE_LIMIT,
  });

  const projectOptions = useMemo(
    () => (projects ?? []).map((p) => ({ id: p.id, label: p.project_code })),
    [projects]
  );

  return (
    <WorkspaceLayout
      title={t("My Work")}
      subtitle="Everything assigned to you — risks, issues, action items, safety events, NCRs, purchase requests, and approvals — in one place"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "My Work" }]}
      toolbar={items ? <span className="text-xs text-muted-foreground">{items.length.toLocaleString()} items</span> : undefined}
    >
      <div className="flex flex-wrap items-center gap-2">
        {ENTITY_FILTERS.map((f) => (
          <FilterChip key={f.id} active={entityType === f.id} onClick={() => setEntityType(f.id)}>
            {t(f.label)}
          </FilterChip>
        ))}
        <span className="w-px h-5 bg-border mx-1" />
        <FilterChip active={openOnly} onClick={() => setOpenOnly((v) => !v)}>
          {t("Open only")}
        </FilterChip>
        <FilterChip active={overdue} onClick={() => setOverdue((v) => !v)} tone="amber">
          {t("Overdue")}
        </FilterChip>
        <FilterChip active={dueSoon} onClick={() => setDueSoon((v) => !v)}>
          {t("Due soon")}
        </FilterChip>
        <FilterSelect value={projectId} onChange={setProjectId} ariaLabel="Project" className="ms-auto">
          <option value="all">{t("All projects")}</option>
          {projectOptions.map((p) => (
            <option key={p.id} value={p.id}>
              {p.label}
            </option>
          ))}
        </FilterSelect>
      </div>

      {isError && <ErrorState title="Failed to load My Work" />}

      {!isError && (
        <div className="panel overflow-hidden">
          <div className="overflow-x-auto">
            <table className="data-table" data-testid="my-work-table">
              <thead>
                <tr>
                  <th>{t("Type")}</th>
                  <th>{t("Title")}</th>
                  <th>{t("Project")}</th>
                  <th>{t("Status")}</th>
                  <th>{t("Priority")}</th>
                  <th>{t("Due")}</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  <TableSkeletonRows rows={8} cols={6} />
                ) : !items?.length ? (
                  <tr>
                    <td colSpan={6}>
                      <EmptyState
                        icon={ListChecks}
                        title="Nothing assigned to you"
                        description="Work assigned to you across risks, issues, action items, safety events, NCRs, purchase requests, and approvals will show up here."
                      />
                    </td>
                  </tr>
                ) : (
                  items.map((item) => {
                    const Icon = entityIcon(item.entity_type);
                    return (
                      <tr key={`${item.entity_type}-${item.entity_id}`} className={item.is_overdue ? "bg-red-50/50 dark:bg-red-900/5" : ""}>
                        <td className="whitespace-nowrap">
                          <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                            <Icon className="w-3.5 h-3.5" />
                            {t(entityLabel(item.entity_type))}
                          </span>
                        </td>
                        <td className="text-sm max-w-sm truncate">
                          <Link href={frontendLinkFor(item.entity_type, item.entity_id)} className="hover:underline">
                            {item.title}
                          </Link>
                        </td>
                        <td className="text-muted-foreground text-sm whitespace-nowrap">{item.project_code ?? "—"}</td>
                        <td>
                          <span className={`badge ${genericStatusBadgeClass(item.status)}`}>{item.status}</span>
                        </td>
                        <td className="text-muted-foreground text-sm capitalize">{item.priority ?? "—"}</td>
                        <td className="text-sm whitespace-nowrap">
                          {item.due_date ? (
                            <span className={item.is_overdue ? "text-destructive font-medium" : item.is_due_soon ? "text-amber-600 dark:text-amber-400 font-medium" : "text-muted-foreground"}>
                              {item.due_date}
                            </span>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </WorkspaceLayout>
  );
}
