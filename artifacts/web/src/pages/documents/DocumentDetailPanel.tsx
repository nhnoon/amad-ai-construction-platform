import { useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  FileUp, FileText, Loader2, ScanText, Sparkles, AlertTriangle, CalendarDays, Tag,
  X, ClipboardList, ShieldAlert, FileSearch,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
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
  return (
    <div className="rounded-lg border border-dashed border-border bg-card/30 p-6 text-center">
      <ScanText className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
      <p className="text-sm text-muted-foreground">{label}: Not Processed Yet</p>
    </div>
  );
}

export default function DocumentDetailPanel({
  document,
}: {
  document: DocumentStub;
}) {
  const documentId = document.id;
  const queryClient = useQueryClient();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

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

  return (
    <div className="space-y-8">
      {/* ── Document Details ─────────────────────────────────────────── */}
      <section>
        <SectionHeading icon={FileSearch} title="Document Details" />
        <Card className="rounded-xl">
          <CardHeader>
            <div className="flex items-start justify-between gap-3">
              <div>
                <CardTitle className="text-base flex items-center gap-2">
                  <FileText className="w-4 h-4 text-primary shrink-0" />
                  {document.title}
                </CardTitle>
                <CardDescription className="flex items-center gap-3 mt-1.5 flex-wrap">
                  <span className="inline-flex items-center gap-1"><Tag className="w-3 h-3" />{document.doc_type}</span>
                  <span className="inline-flex items-center gap-1"><CalendarDays className="w-3 h-3" />{document.doc_date}</span>
                  <ScopeBadge isGeneral={document.project_id == null} />
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
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
          </CardContent>
        </Card>
      </section>

      {/* ── OCR ──────────────────────────────────────────────────────── */}
      <section>
        <SectionHeading icon={ScanText} title="OCR" description="Text extracted from the uploaded file" />
        <Card className="rounded-xl">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-base sr-only">OCR Status</CardTitle>
            {ocrIsProcessed && <StatusBadge status={ocrResult.status} />}
          </CardHeader>
          <CardContent>
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
          </CardContent>
        </Card>
      </section>

      {/* ── Contract Analysis ───────────────────────────────────────── */}
      <section>
        <SectionHeading icon={Sparkles} title="Contract Analysis" description="Structured fields extracted from the OCR text" />
        <Card className="rounded-xl">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-base sr-only">Contract Analysis</CardTitle>
            <div className="flex items-center gap-2">
              {ocrCompleted && !contractIsProcessed && <OcrReadyBadge />}
              {contractIsProcessed && <StatusBadge status={contractResult.status} />}
              {usedValidatedExtraction && <ValidatedExtractionBadge />}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
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

                <ListFieldGroup
                  title="Key Obligations"
                  icon={ClipboardList}
                  items={contractResult.extracted_fields.key_obligations}
                />
                <ListFieldGroup
                  title="Risks"
                  icon={ShieldAlert}
                  items={contractResult.extracted_fields.risks}
                />
              </div>
            ) : null}
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
