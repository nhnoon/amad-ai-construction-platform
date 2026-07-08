import { useEffect, useMemo, useState } from "react";
import { useListProjects } from "@workspace/api-client-react";
import { AlertOctagon, Loader2 } from "lucide-react";
import { getToken } from "@/lib/auth";
import { PageContextHeader } from "@/components/page-context-header";

type ClaimRow = {
  id: number;
  project_id: number;
  claim_number: string;
  claim_type: string;
  amount: number;
  status: string;
  narrative: string;
};

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
    <div className="space-y-6">
      <PageContextHeader
        title="Claims"
        subtitle="Track claim exposure, statuses, and supporting narratives"
        backLabel="Back to Operations"
        backHref="/operations"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Operations", href: "/operations" },
          { label: "Claims" },
        ]}
      />

      <div className="rounded-xl border border-border/50 bg-card/70 p-4 flex flex-wrap items-center gap-3">
        <label className="text-sm font-medium text-muted-foreground">Project</label>
        <select
          className="h-10 min-w-64 rounded-lg border border-border bg-background px-3 text-sm"
          value={selectedProjectId ?? ""}
          onChange={(e) => setSelectedProjectId(Number(e.target.value))}
        >
          <option value="" disabled>
            Select Project
          </option>
          {projects?.map((p) => (
            <option key={p.id} value={p.id}>
              {p.project_code} - {p.project_name}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <div className="rounded-xl border border-border/50 bg-card/70 p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Total Claims</p>
          <p className="mt-2 text-2xl font-bold text-foreground">{summary.total}</p>
        </div>
        <div className="rounded-xl border border-border/50 bg-card/70 p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Open</p>
          <p className="mt-2 text-2xl font-bold text-foreground">{summary.open}</p>
        </div>
        <div className="rounded-xl border border-border/50 bg-card/70 p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Closed</p>
          <p className="mt-2 text-2xl font-bold text-foreground">{summary.closed}</p>
        </div>
        <div className="rounded-xl border border-border/50 bg-card/70 p-4">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">Total Amount</p>
          <p className="mt-2 text-2xl font-bold text-foreground">{summary.totalAmount.toLocaleString()}</p>
        </div>
      </div>

      {isLoading && (
        <div className="rounded-xl border border-border/50 bg-card/70 p-4 text-sm text-muted-foreground inline-flex items-center gap-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading claims...
        </div>
      )}

      {isError && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive inline-flex items-center gap-2">
          <AlertOctagon className="h-4 w-4" />
          {isError}
        </div>
      )}

      <div className="rounded-xl border border-border/50 bg-card/70 overflow-hidden">
        <div className="border-b border-border/50 px-4 py-3">
          <h2 className="text-sm font-semibold text-foreground">Claims Register</h2>
        </div>
        {rows.length === 0 ? (
          <p className="p-4 text-sm text-muted-foreground">No claims found for this project.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border/50 text-muted-foreground">
                  <th className="px-4 py-3 text-left font-medium">Claim Number</th>
                  <th className="px-4 py-3 text-left font-medium">Type</th>
                  <th className="px-4 py-3 text-left font-medium">Status</th>
                  <th className="px-4 py-3 text-left font-medium">Amount</th>
                  <th className="px-4 py-3 text-left font-medium">Narrative</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} className="border-b border-border/40">
                    <td className="px-4 py-3 font-medium text-foreground">{row.claim_number}</td>
                    <td className="px-4 py-3">{row.claim_type}</td>
                    <td className="px-4 py-3">{row.status}</td>
                    <td className="px-4 py-3 tabular-nums">{row.amount.toLocaleString()}</td>
                    <td className="px-4 py-3 text-muted-foreground">{row.narrative}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
