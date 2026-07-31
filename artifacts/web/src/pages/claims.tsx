import { useEffect, useMemo, useState } from "react";
import { useListProjects } from "@workspace/api-client-react";
import { AlertOctagon, Scale, TrendingUp, CircleDot, CheckCircle2, DollarSign } from "lucide-react";
import { getToken } from "@/lib/auth";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeletonRows } from "@/components/ui/table-skeleton";
import { StatTile } from "@/components/stat-tile";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { FilterSelect } from "@/components/filter-select";

type ClaimRow = {
  id: number;
  project_id: number;
  claim_number: string;
  claim_type: string;
  amount: number;
  status: string;
  narrative: string;
};

function statusBadge(status: string) {
  const m: Record<string, string> = {
    Open: "badge-warning",
    Closed: "badge-success",
    Rejected: "badge-danger",
    "Under Review": "badge-info",
  };
  return m[status] ?? "badge-neutral";
}

export default function Claims() {
  const { data: projects } = useListProjects({ limit: 60 });
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [rows, setRows] = useState<ClaimRow[]>([]);
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
        const response = await fetch(`/api/v1/projects/${selectedProjectId}/claims?limit=100`, {
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });

        if (!response.ok) {
          throw new Error("Failed to load claims");
        }

        const data = (await response.json()) as ClaimRow[];
        if (mounted) {
          setRows(data);
        }
      } catch (error) {
        if (mounted) {
          setIsError(error instanceof Error ? error.message : "Failed to load claims");
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

    const totalAmount = rows.reduce((sum, row) => sum + row.amount, 0);

    return {
      total: rows.length,
      totalAmount,
      open: byStatus.Open ?? 0,
      closed: byStatus.Closed ?? 0,
    };
  }, [rows]);

  return (
    <WorkspaceLayout
        title="Claims"
        subtitle="Track claim exposure, statuses, and supporting narratives"
        backLabel="Back to Operations"
        backHref="/operations"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Operations", href: "/operations" },
          { label: "Claims" },
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
        <StatTile icon={TrendingUp} label="Total Claims" description="All claims on record" value={summary.total} />
        <StatTile icon={CircleDot} label="Open" description="Active exposure" value={summary.open} tone={summary.open > 0 ? "warning" : "neutral"} />
        <StatTile icon={CheckCircle2} label="Closed" description="Resolved claims" value={summary.closed} tone="success" />
        <StatTile icon={DollarSign} label="Total Amount" description="Combined claim value" value={summary.totalAmount.toLocaleString()} />
      </div>

      {isError && (
        <Alert variant="destructive">
          <AlertOctagon className="h-4 w-4" />
          <AlertDescription>{isError}</AlertDescription>
        </Alert>
      )}

      <div className="panel overflow-hidden">
        <div className="panel-header">
          <span className="panel-title">Claims Register</span>
        </div>
        <div className="overflow-x-auto">
          <table className="data-table" data-testid="claims-table">
            <thead>
              <tr>
                <th>Claim Number</th>
                <th>Type</th>
                <th>Status</th>
                <th>Amount</th>
                <th className="min-w-[220px]">Narrative</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <TableSkeletonRows rows={5} cols={5} />
              ) : rows.length === 0 ? (
                <tr>
                  <td colSpan={5}>
                    <EmptyState
                      icon={Scale}
                      title="No claims yet"
                      description="Claims for this project will appear here once filed."
                    />
                  </td>
                </tr>
              ) : (
                rows.map((row) => (
                  <tr key={row.id}>
                    <td className="font-semibold text-sm">{row.claim_number}</td>
                    <td className="text-sm">{row.claim_type}</td>
                    <td><span className={`badge ${statusBadge(row.status)}`}>{row.status}</span></td>
                    <td className="tabular-nums text-sm">{row.amount.toLocaleString()}</td>
                    <td className="text-muted-foreground text-sm max-w-xs truncate">{row.narrative}</td>
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
