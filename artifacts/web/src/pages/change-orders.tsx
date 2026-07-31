import { useEffect, useMemo, useState } from "react";
import { useListProjects } from "@workspace/api-client-react";
import { AlertOctagon, FileEdit, ClipboardList, CircleDot, CheckCircle2, DollarSign } from "lucide-react";
import { getToken } from "@/lib/auth";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeletonRows } from "@/components/ui/table-skeleton";
import { StatTile } from "@/components/stat-tile";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { FilterSelect } from "@/components/filter-select";

type ChangeOrderRow = {
  id: number;
  project_id: number;
  co_number: string;
  description: string;
  value: number;
  status: string;
};

function statusBadge(status: string) {
  const m: Record<string, string> = {
    Open: "badge-warning",
    Approved: "badge-success",
    Rejected: "badge-danger",
    Pending: "badge-neutral",
  };
  return m[status] ?? "badge-neutral";
}

export default function ChangeOrders() {
  const { data: projects } = useListProjects({ limit: 60 });
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [rows, setRows] = useState<ChangeOrderRow[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState<string | null>(null);

  useEffect(() => {
    if (projects?.length && !selectedProjectId) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  useEffect(() => {
    let mounted = true;
    const loadRows = async () => {
      if (!selectedProjectId) return;

      setIsLoading(true);
      setIsError(null);

      try {
        const token = getToken();
        const response = await fetch(
          `/api/v1/projects/${selectedProjectId}/change-orders?limit=100`,
          {
            headers: {
              "Content-Type": "application/json",
              ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
          },
        );

        if (!response.ok) {
          throw new Error("Failed to load change orders");
        }

        const data = (await response.json()) as ChangeOrderRow[];
        if (mounted) {
          setRows(data);
        }
      } catch (error) {
        if (mounted) {
          setIsError(error instanceof Error ? error.message : "Failed to load change orders");
          setRows([]);
        }
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    };

    loadRows();
    return () => {
      mounted = false;
    };
  }, [selectedProjectId]);

  const summary = useMemo(() => {
    const byStatus = rows.reduce<Record<string, number>>((acc, row) => {
      acc[row.status] = (acc[row.status] ?? 0) + 1;
      return acc;
    }, {});

    const totalValue = rows.reduce((sum, row) => sum + row.value, 0);

    return {
      total: rows.length,
      totalValue,
      open: byStatus.Open ?? 0,
      approved: byStatus.Approved ?? 0,
    };
  }, [rows]);

  return (
    <WorkspaceLayout
        title="Change Orders"
        subtitle="Track scope/value adjustments and current approval status"
        backLabel="Back to Operations"
        backHref="/operations"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Operations", href: "/operations" },
          { label: "Change Orders" },
        ]}
        toolbar={
          <FilterSelect
            className="min-w-64"
            value={String(selectedProjectId ?? "")}
            onChange={(v) => setSelectedProjectId(Number(v))}
            testId="project-selector"
          >
            <option value="" disabled>
              Select Project
            </option>
            {projects?.map((p) => (
              <option key={p.id} value={p.id}>
                {p.project_code} - {p.project_name}
              </option>
            ))}
          </FilterSelect>
        }
      >

      <div className="grid grid-cols-1 gap-2.5 md:grid-cols-4">
        <StatTile icon={ClipboardList} label="Total COs" description="All change orders on record" value={summary.total} />
        <StatTile icon={CircleDot} label="Open" description="Awaiting approval" value={summary.open} tone={summary.open > 0 ? "warning" : "neutral"} />
        <StatTile icon={CheckCircle2} label="Approved" description="Cleared for execution" value={summary.approved} tone="success" />
        <StatTile icon={DollarSign} label="Total Value" description="Combined scope adjustment" value={summary.totalValue.toLocaleString()} />
      </div>

      {isError && (
        <Alert variant="destructive">
          <AlertOctagon className="h-4 w-4" />
          <AlertDescription>{isError}</AlertDescription>
        </Alert>
      )}

      <div className="panel overflow-hidden">
        <div className="panel-header">
          <span className="panel-title">Change Order Register</span>
        </div>
        <div className="overflow-x-auto">
          <table className="data-table" data-testid="change-orders-table">
            <thead>
              <tr>
                <th>CO Number</th>
                <th>Status</th>
                <th>Value</th>
                <th className="min-w-[220px]">Description</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <TableSkeletonRows rows={5} cols={4} />
              ) : rows.length === 0 ? (
                <tr>
                  <td colSpan={4}>
                    <EmptyState
                      icon={FileEdit}
                      title="No change orders yet"
                      description="Change orders for this project will appear here once submitted."
                    />
                  </td>
                </tr>
              ) : (
                rows.map((row) => (
                  <tr key={row.id}>
                    <td className="font-semibold text-sm">{row.co_number}</td>
                    <td><span className={`badge ${statusBadge(row.status)}`}>{row.status}</span></td>
                    <td className="tabular-nums text-sm">{row.value.toLocaleString()}</td>
                    <td className="text-muted-foreground text-sm max-w-xs truncate">{row.description}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </WorkspaceLayout>
  );
}
