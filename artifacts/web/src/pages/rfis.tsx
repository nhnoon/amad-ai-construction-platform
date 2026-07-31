import { useEffect, useMemo, useState } from "react";
import { useListProjects, useListProjectDecisions } from "@workspace/api-client-react";
import { AlertOctagon, History, HelpCircle, FileText, Mail } from "lucide-react";
import { getToken } from "@/lib/auth";
import { WorkspaceLayout } from "@/components/workspace-layout";
import { EmptyState } from "@/components/ui/empty-state";
import { TableSkeletonRows } from "@/components/ui/table-skeleton";
import { StatTile } from "@/components/stat-tile";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { FilterSelect } from "@/components/filter-select";

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
    { query: { enabled: !!selectedProjectId, queryKey: ["rfi-decisions", selectedProjectId] } },
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
    <WorkspaceLayout
        title="Requests for Information"
        subtitle={project ? project.project_name : "Manage clarification records, references, and response traceability"}
        backLabel="Back to Operations"
        backHref="/operations"
        breadcrumbs={[
          { label: "Dashboard", href: "/" },
          { label: "Operations", href: "/operations" },
          { label: "RFIs" },
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

      <div className="grid grid-cols-1 gap-2.5 md:grid-cols-3">
        <StatTile icon={HelpCircle} label="RFI Decisions" description="Formal decisions on record" value={decisionRows.length} />
        <StatTile icon={FileText} label="RFI Documents" description="Referenced supporting documents" value={documents.length} />
        <StatTile icon={Mail} label="RFI Correspondence" description="Sent and received traceability" value={correspondence.length} />
      </div>

      {(recordsError || decisionsError) && (
        <Alert variant="destructive">
          <AlertOctagon className="h-4 w-4" />
          <AlertDescription>{recordsError || "Failed to load project decisions"}</AlertDescription>
        </Alert>
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
    </WorkspaceLayout>
  );
}
