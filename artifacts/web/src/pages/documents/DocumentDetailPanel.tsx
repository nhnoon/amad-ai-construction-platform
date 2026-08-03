import { useRef, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  FileUp, FileText, Loader2, ScanText, Sparkles, AlertTriangle, CalendarDays, Tag,
  X, ClipboardList, ShieldAlert, FileSearch, History, Download, Archive, ArchiveRestore,
  MoreVertical, CheckCircle2,
} from "lucide-react";
import {
  useListDocumentVersions,
  useUploadDocumentVersion,
  useArchiveDocument,
  useUnarchiveDocument,
  useListApprovals,
  downloadDocument,
} from "@workspace/api-client-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { EmptyState } from "@/components/ui/empty-state";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import {
  AICenterApiError,
  ContractExtractionResult,
  DocumentOCRResult,
  DocumentStub,
  NOT_PROCESSED,
  getContractExtraction,
  getDocumentOCRResult,
  startContractExtraction,
  startDocumentOCR,
} from "@/lib/aiCenterClient";
import { OcrReadyBadge, ScopeBadge, StatusBadge, ValidatedExtractionBadge } from "./DocumentBadges";
import SectionHeading from "./SectionHeading";
import { useRegisterCurrentEntity } from "@/context/CurrentEntityContext";
import { CurrentlyAnalyzing } from "@/components/CurrentlyAnalyzing";
import { useToast } from "@/hooks/use-toast";
import { useUserDirectory } from "@/lib/useUserDirectory";
import { apiErrorDetail } from "@/lib/apiErrors";

// Document workspace: preview, OCR, and contract analysis for ONE document.
// Presentation-only refinement — same endpoints, same request shapes, same
// mutation/query logic as before (POST/GET .../ocr, POST/GET
// .../contract-extraction).

const ACCEPTED_TYPES = ["application/pdf", "image/png", "image/jpeg"];
const ACCEPTED_EXTENSIONS = ".pdf,.png,.jpg,.jpeg";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Fields grouped for readability, per the contract's natural structure.
// contract_title is folded into "Contract Overview" (not called out
// separately by the spec, but dropping it would lose real, already-
// extracted data).
const FIELD_LABELS: Record<string, string> = {
  contract_title: "Contract Title",
  project_code: "Project Code",
  employer: "Employer",
  contractor: "Contractor",
  contract_value: "Contract Value",
  currency: "Currency",
  start_date: "Start Date",
  completion_date: "Completion Date",
  payment_terms: "Payment Terms",
  retention: "Retention",
  liquidated_damages: "Liquidated Damages",
  insurance: "Insurance",
};

const FIELD_GROUPS: { title: string; fields: string[] }[] = [
  { title: "Contract Overview", fields: ["contract_title", "employer", "contractor", "project_code", "contract_value", "currency"] },
  { title: "Schedule", fields: ["start_date", "completion_date"] },
  { title: "Commercial Terms", fields: ["retention", "payment_terms", "liquidated_damages", "insurance"] },
];

function FieldRow({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-4 py-2.5 first:pt-0 last:pb-0">
      <span className="w-40 shrink-0 text-sm text-muted-foreground">{label}</span>
      {value == null ? (
        <span className="text-sm text-muted-foreground italic">Not stated in document</span>
      ) : (
        <span className="text-sm text-foreground">{String(value)}</span>
      )}
    </div>
  );
}

function FieldGroupCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div>
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">{title}</p>
      <div className="rounded-lg border border-border divide-y divide-border px-4">{children}</div>
    </div>
  );
}

function ListFieldGroup({ title, icon: Icon, items }: { title: string; icon: typeof ClipboardList; items: string[] | null }) {
  return (
    <div>
      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 flex items-center gap-1.5">
        <Icon className="w-3.5 h-3.5" />
        {title}
      </p>
      <div className="rounded-lg border border-border p-4">
        {!items || items.length === 0 ? (
          <span className="text-sm text-muted-foreground italic">Not stated in document</span>
        ) : (
          <ul className="list-disc ps-4 space-y-1 text-sm text-foreground">
            {items.map((v, i) => <li key={i}>{v}</li>)}
          </ul>
        )}
      </div>
    </div>
  );
}

function NotProcessedState({ label }: { label: string }) {
  return <EmptyState icon={ScanText} title={`${label}: Not Processed Yet`} className="py-6" />;
}

export default function DocumentDetailPanel({
  document,
}: {
  document: DocumentStub;
}) {
  const documentId = document.id;
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { resolveUserName } = useUserDirectory();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const versionFileInputRef = useRef<HTMLInputElement>(null);
  const [downloadingVersion, setDownloadingVersion] = useState<number | null>(null);

  // ── Document Storage System (Sprint 1, activated Sprint 6) ────────────
  const versionsQuery = useListDocumentVersions(documentId, {
    query: { queryKey: ["document-versions", documentId] },
  });
  const uploadVersionMutation = useUploadDocumentVersion({
    mutation: {
      onSuccess: (result) => {
        queryClient.invalidateQueries({ queryKey: ["document-versions", documentId] });
        queryClient.invalidateQueries({ queryKey: ["ai-center-documents-list"] });
        toast({
          title: result.is_duplicate ? "Identical to current version" : "New version uploaded",
          description: result.is_duplicate ? "This file matches the current version — nothing changed." : `Version ${result.version_number} is now current.`,
          variant: "success",
        });
      },
      onError: (err) => toast({ title: "Upload failed", description: apiErrorDetail(err), variant: "destructive" }),
    },
  });
  const archiveMutation = useArchiveDocument({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["ai-center-documents-list"] });
        toast({ title: "Document archived", variant: "success" });
      },
      onError: (err) => toast({ title: "Archive failed", description: apiErrorDetail(err), variant: "destructive" }),
    },
  });
  const unarchiveMutation = useUnarchiveDocument({
    mutation: {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: ["ai-center-documents-list"] });
        toast({ title: "Document unarchived", variant: "success" });
      },
      onError: (err) => toast({ title: "Unarchive failed", description: apiErrorDetail(err), variant: "destructive" }),
    },
  });

  // Read-only "approved version" context (Sprint 5 Approval Engine) — never
  // implies this page can settle/mutate anything beyond the approval record.
  const { data: documentApprovals } = useListApprovals(
    { entity_type: "document", project_id: document.project_id ?? undefined, status: "Approved" },
    { query: { queryKey: ["document-approvals", documentId], enabled: true } }
  );
  const approvedVersion = documentApprovals?.find((a) => a.entity_id === documentId)?.target_version ?? null;

  async function handleDownload(version?: number) {
    setDownloadingVersion(version ?? document.version_number ?? 0);
    try {
      const blob = await downloadDocument(documentId, version != null ? { version } : undefined);
      const url = URL.createObjectURL(blob);
      const a = window.document.createElement("a");
      a.href = url;
      a.download = document.title || `document-${documentId}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast({ title: "Download failed", description: apiErrorDetail(err), variant: "destructive" });
    } finally {
      setDownloadingVersion(null);
    }
  }

  function handleVersionFileSelect(file: File | null) {
    if (!file) return;
    uploadVersionMutation.mutate({ documentId, data: { file } });
    if (versionFileInputRef.current) versionFileInputRef.current.value = "";
  }

  const ocrQuery = useQuery<DocumentOCRResult | typeof NOT_PROCESSED, AICenterApiError>({
    queryKey: ["ai-center-ocr", documentId],
    queryFn: () => getDocumentOCRResult(documentId),
  });

  const contractQuery = useQuery<ContractExtractionResult | typeof NOT_PROCESSED, AICenterApiError>({
    queryKey: ["ai-center-contract", documentId],
    queryFn: () => getContractExtraction(documentId),
  });

  const ocrMutation = useMutation({
    mutationFn: () => startDocumentOCR(documentId, selectedFile as File),
    onSuccess: (result) => {
      queryClient.setQueryData(["ai-center-ocr", documentId], result);
    },
  });

  const contractMutation = useMutation({
    mutationFn: () => startContractExtraction(documentId),
    onSuccess: (result) => {
      queryClient.setQueryData(["ai-center-contract", documentId], result);
    },
  });

  function handleFileSelect(file: File | null) {
    setFileError(null);
    if (!file) {
      setSelectedFile(null);
      return;
    }
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setFileError("Unsupported file type. Please choose a PDF, PNG, or JPEG file.");
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  }

  const ocrResult = ocrQuery.data;
  const ocrIsProcessed = ocrResult && ocrResult !== NOT_PROCESSED;
  const ocrCompleted = ocrIsProcessed && ocrResult.status === "completed";

  const contractResult = contractQuery.data;
  const contractIsProcessed = contractResult && contractResult !== NOT_PROCESSED;
  const usedValidatedExtraction = contractIsProcessed && contractResult.validation_status === "fallback_valid";
  const contractCompleted = contractIsProcessed && contractResult.status === "completed" && contractResult.extracted_fields;

  // Contextual Hermes (Phase 2 §2) — this document IS a contract once its
  // extraction has completed; register it so "Currently analyzing: Contract
  // …" shows the same way it does for a Project or Site Report.
  useRegisterCurrentEntity(
    contractCompleted
      ? { kind: "contract", code: `DOC-${documentId}`, label: contractResult.extracted_fields!.contract_title || document.title, projectId: document.project_id ?? undefined }
      : null,
  );

  const overviewRef = useRef<HTMLDivElement>(null);
  const obligationsRef = useRef<HTMLDivElement>(null);
  const risksRef = useRef<HTMLDivElement>(null);
  const [flashSection, setFlashSection] = useState<string | null>(null);
  const scrollToSection = (ref: React.RefObject<HTMLDivElement | null>, key: string) => {
    ref.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    setFlashSection(key);
    window.setTimeout(() => setFlashSection((cur) => (cur === key ? null : cur)), 1400);
  };

  return (
    <div className="space-y-8">
      {/* ── Document Details ─────────────────────────────────────────── */}
      <section>
        <SectionHeading icon={FileSearch} title="Document Details" />
        <div className="panel">
          <div className="panel-header items-start">
            <div>
              <p className="panel-title flex items-center gap-2">
                <FileText className="w-4 h-4 text-primary shrink-0" />
                {document.title}
                {document.is_archived && <span className="badge badge-neutral">Archived</span>}
              </p>
              <div className="flex items-center gap-3 mt-1.5 flex-wrap text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1"><Tag className="w-3 h-3" />{document.doc_type}</span>
                <span className="inline-flex items-center gap-1"><CalendarDays className="w-3 h-3" />{document.doc_date}</span>
                <ScopeBadge isGeneral={document.project_id == null} />
                {document.version_number != null && (
                  <span className="inline-flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
                    Current: v{document.version_number}
                  </span>
                )}
              </div>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="shrink-0" aria-label="Document actions">
                  <MoreVertical className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => handleDownload()} disabled={!document.version_number || downloadingVersion != null}>
                  <Download className="w-4 h-4 me-2" /> Download current version
                </DropdownMenuItem>
                {document.is_archived ? (
                  <DropdownMenuItem onClick={() => unarchiveMutation.mutate({ documentId })} disabled={unarchiveMutation.isPending}>
                    <ArchiveRestore className="w-4 h-4 me-2" /> Unarchive
                  </DropdownMenuItem>
                ) : (
                  <DropdownMenuItem onClick={() => archiveMutation.mutate({ documentId })} disabled={archiveMutation.isPending}>
                    <Archive className="w-4 h-4 me-2" /> Archive
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
          <div className="panel-body space-y-4">
            <div>
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">Summary</p>
              <p className="text-sm text-foreground">{document.content_summary || "No summary available for this document."}</p>
            </div>

            <div className="pt-1">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Upload File</p>
              <label
                onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragOver(false);
                  handleFileSelect(e.dataTransfer.files?.[0] ?? null);
                }}
                className={cn(
                  "flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-6 text-center cursor-pointer transition-all",
                  isDragOver
                    ? "border-primary bg-primary/5 scale-[1.01]"
                    : "border-border bg-muted/20 hover:border-primary/40 hover:bg-muted/30"
                )}
              >
                {selectedFile ? (
                  <div className="flex items-center gap-3 rounded-lg border border-border bg-background px-4 py-3">
                    <FileText className="w-5 h-5 text-primary shrink-0" />
                    <div className="text-left">
                      <p className="text-sm font-medium text-foreground">{selectedFile.name}</p>
                      <p className="text-xs text-muted-foreground">{formatFileSize(selectedFile.size)}</p>
                    </div>
                    <button
                      type="button"
                      onClick={(e) => { e.stopPropagation(); handleFileSelect(null); }}
                      className="ms-2 rounded-full p-1 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                      aria-label="Remove selected file"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <>
                    <FileUp className="w-7 h-7 text-muted-foreground/50" />
                    <p className="text-sm text-foreground">Drag & drop a file here, or click to browse</p>
                    <p className="text-xs text-muted-foreground">PDF, PNG, JPEG — up to 20 MB</p>
                  </>
                )}
                <input
                  type="file"
                  accept={ACCEPTED_EXTENSIONS}
                  className="hidden"
                  onChange={(e) => handleFileSelect(e.target.files?.[0] ?? null)}
                />
              </label>

              {fileError && (
                <Alert variant="destructive" className="mt-3">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>{fileError}</AlertDescription>
                </Alert>
              )}

              <div className="flex justify-end mt-3">
                <Button
                  onClick={() => ocrMutation.mutate()}
                  disabled={!selectedFile || ocrMutation.isPending}
                  className="gap-2"
                >
                  {ocrMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <ScanText className="w-4 h-4" />}
                  Run OCR
                </Button>
              </div>
              {ocrMutation.isError && (
                <Alert variant="destructive" className="mt-3">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertDescription>
                    {ocrMutation.error instanceof AICenterApiError ? ocrMutation.error.message : "OCR request failed."}
                  </AlertDescription>
                </Alert>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── Version History (Sprint 1 storage, activated Sprint 6) ──────── */}
      <section>
        <SectionHeading icon={History} title="Version History" description="Every uploaded file for this document, newest first" />
        <div className="panel">
          <div className="panel-header items-center justify-between">
            <p className="panel-title sr-only">Version History</p>
            <input
              ref={versionFileInputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS}
              className="hidden"
              onChange={(e) => handleVersionFileSelect(e.target.files?.[0] ?? null)}
            />
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5"
              onClick={() => versionFileInputRef.current?.click()}
              disabled={uploadVersionMutation.isPending}
            >
              {uploadVersionMutation.isPending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileUp className="w-3.5 h-3.5" />}
              Upload new version
            </Button>
          </div>
          <div className="panel-body">
            {approvedVersion != null && (
              <p className="text-xs text-muted-foreground mb-3 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                Version {approvedVersion} was approved.
                {document.version_number != null && approvedVersion !== document.version_number && (
                  <span className="text-amber-600 dark:text-amber-400">
                    {" "}The current version (v{document.version_number}) is newer and does not inherit that approval.
                  </span>
                )}
              </p>
            )}
            {versionsQuery.isLoading ? (
              <div className="space-y-2">
                {[0, 1].map((i) => <Skeleton key={i} className="h-12 w-full rounded-lg" />)}
              </div>
            ) : versionsQuery.isError ? (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>Unable to load version history right now.</AlertDescription>
              </Alert>
            ) : !versionsQuery.data?.length ? (
              <EmptyState icon={History} title="No versions uploaded yet" description="Upload a file above to start this document's version history." className="py-6" />
            ) : (
              <ul className="divide-y divide-border">
                {versionsQuery.data.map((v) => (
                  <li key={v.version_number} className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0">
                    <div className="min-w-0">
                      <p className="text-sm text-foreground flex items-center gap-2">
                        <span className="font-medium">v{v.version_number}</span>
                        {v.is_current && <span className="badge badge-success text-[10px]">Current</span>}
                        <span className="truncate text-muted-foreground text-xs">{v.original_filename}</span>
                      </p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        {formatFileSize(v.file_size)} · {resolveUserName(v.uploaded_by) ?? "Unknown"} · {new Date(v.uploaded_at).toLocaleString()}
                      </p>
                    </div>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="shrink-0 gap-1.5"
                      onClick={() => handleDownload(v.version_number)}
                      disabled={downloadingVersion != null}
                    >
                      {downloadingVersion === v.version_number ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
                      Download
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>

      {/* ── OCR ──────────────────────────────────────────────────────── */}
      <section>
        <SectionHeading icon={ScanText} title="OCR" description="Text extracted from the uploaded file" />
        <div className="panel">
          <div className="panel-header">
            <p className="panel-title sr-only">OCR Status</p>
            {ocrIsProcessed && <StatusBadge status={ocrResult.status} />}
          </div>
          <div className="panel-body">
            {ocrQuery.isLoading ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-14 rounded-lg" />)}
              </div>
            ) : ocrQuery.isError ? (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>Unable to load OCR status right now.</AlertDescription>
              </Alert>
            ) : !ocrIsProcessed ? (
              <NotProcessedState label="OCR" />
            ) : (
              <div className="space-y-4 text-sm">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {[
                    { label: "Page Count", value: ocrResult.page_count ?? "—" },
                    { label: "Language", value: ocrResult.detected_language ?? "—" },
                    { label: "Method", value: ocrResult.extraction_method ?? "—" },
                    { label: "Characters", value: ocrResult.text_length.toLocaleString() },
                  ].map((stat) => (
                    <div key={stat.label} className="rounded-lg border border-border bg-muted/20 p-3">
                      <p className="text-[11px] text-muted-foreground uppercase tracking-wide">{stat.label}</p>
                      <p className="text-sm font-semibold text-foreground mt-0.5 truncate">{stat.value}</p>
                    </div>
                  ))}
                </div>

                {ocrResult.error_message && (
                  <Alert variant="destructive">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>{ocrResult.error_message}</AlertDescription>
                  </Alert>
                )}

                {ocrResult.status === "completed" && ocrResult.text_preview && (
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Extracted Text</p>
                      {ocrResult.text_truncated && (
                        <span className="text-[11px] text-muted-foreground">Preview truncated</span>
                      )}
                    </div>
                    <div className="rounded-lg border border-border overflow-hidden">
                      <ScrollArea className="h-48">
                        <p className="text-xs text-foreground/80 whitespace-pre-wrap font-mono p-3 leading-relaxed">
                          {ocrResult.text_preview}
                          {ocrResult.text_truncated && "…"}
                        </p>
                      </ScrollArea>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ── Contract Analysis ───────────────────────────────────────── */}
      <section>
        <SectionHeading icon={Sparkles} title="Contract Analysis" description="Structured fields extracted from the OCR text" />
        {contractCompleted && <CurrentlyAnalyzing className="mb-3" />}
        <div className="panel">
          <div className="panel-header">
            <p className="panel-title sr-only">Contract Analysis</p>
            <div className="flex items-center gap-2">
              {ocrCompleted && !contractIsProcessed && <OcrReadyBadge />}
              {contractIsProcessed && <StatusBadge status={contractResult.status} />}
              {usedValidatedExtraction && <ValidatedExtractionBadge />}
            </div>
          </div>
          <div className="panel-body space-y-4">
            {contractCompleted && (
              <div>
                <div className="flex items-center gap-1.5 mb-2">
                  <Sparkles className="w-3.5 h-3.5 text-primary" />
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">AI Actions</p>
                </div>
                <div className="flex flex-wrap gap-2 mb-1">
                  <Button size="sm" variant="outline" className="gap-1.5" onClick={() => scrollToSection(overviewRef, "overview")}>
                    <FileSearch className="w-3.5 h-3.5" />Summarize
                  </Button>
                  <Button size="sm" variant="outline" className="gap-1.5" onClick={() => scrollToSection(risksRef, "risks")}>
                    <ShieldAlert className="w-3.5 h-3.5" />Highlight Risks
                  </Button>
                  <Button size="sm" variant="outline" className="gap-1.5" onClick={() => scrollToSection(obligationsRef, "obligations")}>
                    <ClipboardList className="w-3.5 h-3.5" />Extract Obligations
                  </Button>
                </div>
              </div>
            )}
            <div className="flex items-center justify-between flex-wrap gap-2">
              <p className="text-sm text-muted-foreground">
                {ocrCompleted
                  ? "Ready to extract structured contract fields from the text above."
                  : "Run OCR to completion first."}
              </p>
              <Button
                onClick={() => contractMutation.mutate()}
                disabled={!ocrCompleted || contractMutation.isPending}
                variant="secondary"
                className="gap-2"
              >
                {contractMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                Run Contract Analysis
              </Button>
            </div>

            {contractMutation.isError && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  {contractMutation.error instanceof AICenterApiError ? contractMutation.error.message : "Contract analysis request failed."}
                </AlertDescription>
              </Alert>
            )}

            {contractQuery.isLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-24 w-full rounded-lg" />
                <Skeleton className="h-16 w-full rounded-lg" />
              </div>
            ) : contractQuery.isError ? (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>Unable to load contract analysis status right now.</AlertDescription>
              </Alert>
            ) : !contractIsProcessed ? (
              <NotProcessedState label="Contract Analysis" />
            ) : contractResult.status === "failed" ? (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  {contractResult.error_message
                    ? "We couldn't identify structured contract fields in this document. Try re-running OCR or reviewing the extracted text above."
                    : "Contract analysis did not complete."}
                </AlertDescription>
              </Alert>
            ) : contractResult.status === "completed" && contractResult.extracted_fields ? (
              <div className="space-y-5">
                {usedValidatedExtraction && (
                  <p className="text-sm text-muted-foreground">
                    Some fields were identified using validated document parsing. A few details may be
                    missing if they weren't clearly stated in the document.
                  </p>
                )}

                <div ref={overviewRef} className={cn("space-y-5 rounded-lg transition-shadow duration-500", flashSection === "overview" && "ring-2 ring-primary/50")}>
                  {FIELD_GROUPS.map((group) => (
                    <FieldGroupCard key={group.title} title={group.title}>
                      {group.fields.map((field) => (
                        <FieldRow
                          key={field}
                          label={FIELD_LABELS[field]}
                          value={contractResult.extracted_fields![field as keyof typeof contractResult.extracted_fields]}
                        />
                      ))}
                    </FieldGroupCard>
                  ))}
                </div>

                <div ref={obligationsRef} className={cn("rounded-lg transition-shadow duration-500", flashSection === "obligations" && "ring-2 ring-primary/50")}>
                  <ListFieldGroup
                    title="Key Obligations"
                    icon={ClipboardList}
                    items={contractResult.extracted_fields.key_obligations}
                  />
                </div>
                <div ref={risksRef} className={cn("rounded-lg transition-shadow duration-500", flashSection === "risks" && "ring-2 ring-primary/50")}>
                  <ListFieldGroup
                    title="Risks"
                    icon={ShieldAlert}
                    items={contractResult.extracted_fields.risks}
                  />
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </section>
    </div>
  );
}
