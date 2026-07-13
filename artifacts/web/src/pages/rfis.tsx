import { useEffect, useMemo, useState } from "react";
import { useListProjects, useListProjectDecisions } from "@workspace/api-client-react";
import { AlertOctagon, History } from "lucide-react";
import { getToken } from "@/lib/auth";
import { PageContextHeader } from "@/components/page-context-header";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeletonRows } from "@/components/ui/table-skeleton";

type DocRecord = {
  id: number;
  doc_type: string;
  title: string;
  doc_date: string;
  content_summary: string;
};

type CorrespondenceRecord = {
  id: number;
  related_record_type: string;
  sent_date: string;
  sender: string;
  recipient: string;
  subject: string;
};

function isRfiLike(value: string | null | undefined) {
  if (!value) return false;
  return value.toLowerCase().includes("rfi");
}

function sourceBadge(source: string) {
  const m: Record<string, string> = {
    Decision: "badge-info",
    Document: "badge-purple",
    Correspondence: "badge-gold",
  };
  return m[source] ?? "badge-neutral";
}

export default function RFIs() {
  const { data: projects } = useListProjects({ limit: 60 });
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [documents, setDocuments] = useState<DocRecord[]>([]);
  const [correspondence, setCorrespondence] = useState<CorrespondenceRecord[]>([]);
  const [loadingRecords, setLoadingRecords] = useState(false);
  const [recordsError, setRecordsError] = useState<string | null>(null);

  const { data: decisions, isLoading: loadingDecisions, isError: decisionsError } = useListProjectDecisions(
    selectedProjectId ?? 0,
    { limit: 100 },
    { query: { enabled: !!selectedProjectId } },
  );

  useEffect(() => {
    if (projects?.length && !selectedProjectId) {
      setSelectedProjectId(projects[0].id);
    }
  }, [projects, selectedProjectId]);

  useEffect(() => {
    let mounted = true;
    const loadRfiRecords = async () => {
      if (!selectedProjectId) return;
      setLoadingRecords(true);
      setRecordsError(null);

      try {
        const token = getToken();
        const headers = {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        };

        const [docsResponse, corrResponse] = await Promise.all([
          fetch(`/api/v1/projects/${selectedProjectId}/documents?limit=100`, { headers }),
          fetch(`/api/v1/projects/${selectedProjectId}/correspondence?limit=100`, { headers }),
        ]);

        if (!docsResponse.ok || !corrResponse.ok) {
          throw new Error("Failed to load RFI records");
        }

        const docsData = (await docsResponse.json()) as DocRecord[];
        const corrData = (await corrResponse.json()) as CorrespondenceRecord[];

        if (mounted) {
          setDocuments(docsData.filter((doc) => isRfiLike(doc.doc_type) || isRfiLike(doc.title)));
          setCorrespondence(
            corrData.filter(
              (row) => isRfiLike(row.related_record_type) || isRfiLike(row.subject),
            ),
          );
        }
      } catch (error) {
        if (mounted) {
          setRecordsError(error instanceof Error ? error.message : "Failed to load RFI records");
          setDocuments([]);
          setCorrespondence([]);
        }
      } finally {
        if (mounted) {
          setLoadingRecords(false);
        }
      }
    };

    loadRfiRecords();
    return () => {
      mounted = false;
    };
  }, [selectedProjectId]);

  const project = projects?.find((p) => p.id === selectedProjectId);

  const decisionRows = decisions ?? [];

  const timelineRows = useMemo(() => {
    const decisionTimeline = decisionRows.map((row) => ({
      id: `decision-${row.id}`,
      date: row.decision_date,
      source: "Decision",
      title: row.decision_text,
      owner: row.owner,
    }));

    const docTimeline = documents.map((row) => ({
      id: `doc-${row.id}`,
      date: row.doc_date,
      source: "Document",
      title: `${row.title} (${row.doc_type})`,
      owner: "Project Document",
    }));

    const corrTimeline = correspondence.map((row) => ({
      id: `corr-${row.id}`,
      date: row.sent_date,
      source: "Correspondence",
      title: row.subject,
      owner: `${row.sender} → ${row.recipient}`,
    }));

    return [...decisionTimeline, ...docTimeline, ...corrTimeline].sort((a, b) =>
      b.date.localeCompare(a.date),
    );
  }, [decisionRows, documents, correspondence]);

  const isLoading = loadingRecords || loadingDecisions;

  return (
    <div className="space-y-6">
      <PageContextHeader
        title="Requests for Information"
        subtitle="Manage clarification records, references, and response traceability"
        backLabel="Back to Operations"
        backHref="/operations"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Operations", href: "/operations" },
          { label: "RFIs" },
        ]}
      />

      <div className="panel panel-body flex flex-wrap items-center gap-3">
        <label className="text-sm font-medium text-muted-foreground">Project</label>
        <select
          className="h-10 min-w-64 rounded-lg border border-border bg-background px-3 text-sm"
          value={selectedProjectId ?? ""}
          onChange={(e) => setSelectedProjectId(Number(e.target.value))}
          data-testid="project-selector"
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
        {project && <p className="text-sm text-muted-foreground">{project.project_name}</p>}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="panel panel-body">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">RFI Decisions</p>
          <p className="mt-2 text-2xl font-bold text-foreground">{decisionRows.length}</p>
        </div>
        <div className="panel panel-body">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">RFI Documents</p>
          <p className="mt-2 text-2xl font-bold text-foreground">{documents.length}</p>
        </div>
        <div className="panel panel-body">
          <p className="text-xs uppercase tracking-wide text-muted-foreground">RFI Correspondence</p>
          <p className="mt-2 text-2xl font-bold text-foreground">{correspondence.length}</p>
        </div>
      </div>

      {(recordsError || decisionsError) && (
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 text-sm text-destructive inline-flex items-center gap-2">
          <AlertOctagon className="h-4 w-4" />
          {recordsError || "Failed to load project decisions"}
        </div>
      )}

      <div className="panel overflow-hidden">
        <div className="panel-header">
          <span className="panel-title">RFI Timeline</span>
        </div>
        <div className="overflow-x-auto">
          <table className="data-table" data-testid="rfi-timeline-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Source</th>
                <th className="min-w-[240px]">Title / Detail</th>
                <th>Owner / Flow</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <TableSkeletonRows rows={5} cols={4} />
              ) : timelineRows.length === 0 ? (
                <tr>
                  <td colSpan={4}>
                    <EmptyState
                      icon={History}
                      title="No RFI-related records"
                      description="RFI decisions, documents, and correspondence for this project will appear here."
                    />
                  </td>
                </tr>
              ) : (
                timelineRows.map((row) => (
                  <tr key={row.id}>
                    <td className="whitespace-nowrap text-sm text-muted-foreground">{row.date}</td>
                    <td><span className={`badge ${sourceBadge(row.source)}`}>{row.source}</span></td>
                    <td className="text-sm">{row.title}</td>
                    <td className="text-muted-foreground text-sm">{row.owner}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
