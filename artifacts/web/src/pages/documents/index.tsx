import { useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useListProjects } from "@workspace/api-client-react";
import {
  FileText, Search, AlertTriangle, CalendarDays, Tag, FileUp, Loader2, Building2, Folder,
  X, UploadCloud, Library,
} from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";
import {
  AICenterApiError, DocumentListScope, DocumentStub,
  createDocument, listDocuments, startDocumentOCR,
} from "@/lib/aiCenterClient";
import DocumentDetailPanel from "./DocumentDetailPanel";
import { ScopeBadge } from "./DocumentBadges";
import SectionHeading from "./SectionHeading";

const ACCEPTED_TYPES = ["application/pdf", "image/png", "image/jpeg"];
const ACCEPTED_EXTENSIONS = ".pdf,.png,.jpg,.jpeg";

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Documents — the complete document workspace, organized as one workflow:
// Upload -> Document Library -> Document Details -> OCR -> Contract
// Analysis. All calls go through the unified /api/v1/documents endpoints
// (backend/app/api/v1/documents.py) — the existing project-scoped routes
// are untouched and still work for older links. This file is presentation
// only; no request shape, endpoint, or business logic changed here.

export default function Documents() {
  const queryClient = useQueryClient();
  const uploadCardRef = useRef<HTMLDivElement>(null);

  // Upload form state
  const [destination, setDestination] = useState<"general" | "project">("general");
  const [uploadProjectId, setUploadProjectId] = useState<number | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  // Browse/filter state
  const [filterScope, setFilterScope] = useState<DocumentListScope>("all");
  const [browseProjectId, setBrowseProjectId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [documentId, setDocumentId] = useState<number | null>(null);

  const { data: projects, isLoading: projectsLoading } = useListProjects();

  const {
    data: documents, isLoading: documentsLoading, isError: documentsError,
  } = useQuery({
    queryKey: ["ai-center-documents-list", filterScope, browseProjectId],
    queryFn: () => listDocuments({
      scope: filterScope,
      projectId: filterScope === "project" && browseProjectId != null ? browseProjectId : undefined,
      limit: 100,
    }),
  });

  const filteredDocuments = useMemo(() => {
    const list = documents ?? [];
    const q = search.trim().toLowerCase();
    if (!q) return list;
    return list.filter(
      (d) => d.title.toLowerCase().includes(q) || d.doc_type.toLowerCase().includes(q)
    );
  }, [documents, search]);

  const selectedDocument = filteredDocuments.find((d) => d.id === documentId)
    ?? documents?.find((d) => d.id === documentId);

  const uploadMutation = useMutation({
    mutationFn: async () => {
      const file = selectedFile as File;
      const doc = await createDocument({
        projectId: destination === "project" ? uploadProjectId : null,
        title: file.name,
      });
      await startDocumentOCR(doc.id, file);
      return doc;
    },
    onSuccess: (doc) => {
      queryClient.invalidateQueries({ queryKey: ["ai-center-documents-list"] });
      setDocumentId(doc.id);
      setSelectedFile(null);
    },
  });

  function handleFileSelect(file: File | null) {
    setFileError(null);
    if (!file) { setSelectedFile(null); return; }
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setFileError("Unsupported file type. Please choose a PDF, PNG, or JPEG file.");
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  }

  function focusUploadCard() {
    uploadCardRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const canUpload = !!selectedFile && (destination === "general" || uploadProjectId != null);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-foreground">Documents</h1>
        <p className="text-muted-foreground mt-1">
          Upload documents to the General Library or a project, then run OCR and contract analysis.
        </p>
      </div>

      {/* ── Upload ────────────────────────────────────────────────────── */}
      <section ref={uploadCardRef}>
        <SectionHeading icon={UploadCloud} title="Upload" description="Add a document to the workspace" />
        <Card className="rounded-xl">
          <CardContent className="pt-6 space-y-5">
            <div className="space-y-2">
              <label className="text-sm font-medium text-foreground">Destination</label>
              <RadioGroup
                value={destination}
                onValueChange={(v) => setDestination(v as "general" | "project")}
                className="grid grid-cols-1 sm:grid-cols-2 gap-3"
              >
                <label
                  className={cn(
                    "flex items-center gap-2.5 rounded-lg border p-3 cursor-pointer transition-colors",
                    destination === "general"
                      ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                      : "border-border hover:bg-muted/40"
                  )}
                >
                  <RadioGroupItem value="general" id="dest-general" />
                  <Building2 className="w-4 h-4 text-muted-foreground shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-foreground">General Library</p>
                    <p className="text-xs text-muted-foreground">Organization-wide, no project required</p>
                  </div>
                </label>
                <label
                  className={cn(
                    "flex items-center gap-2.5 rounded-lg border p-3 cursor-pointer transition-colors",
                    destination === "project"
                      ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                      : "border-border hover:bg-muted/40"
                  )}
                >
                  <RadioGroupItem value="project" id="dest-project" />
                  <Folder className="w-4 h-4 text-muted-foreground shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-foreground">Existing Project</p>
                    <p className="text-xs text-muted-foreground">Linked to one project</p>
                  </div>
                </label>
              </RadioGroup>
            </div>

            {destination === "project" && (
              <div className="space-y-1.5">
                <label className="text-sm font-medium text-foreground">Project</label>
                <Select
                  value={uploadProjectId != null ? String(uploadProjectId) : undefined}
                  onValueChange={(v) => setUploadProjectId(Number(v))}
                  disabled={projectsLoading}
                >
                  <SelectTrigger>
                    <SelectValue placeholder={projectsLoading ? "Loading projects…" : "Select a project (required)"} />
                  </SelectTrigger>
                  <SelectContent>
                    {(projects ?? []).map((p) => (
                      <SelectItem key={p.id} value={String(p.id)}>
                        {p.project_code} — {p.project_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            <div>
              <label
                onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={(e) => {
                  e.preventDefault();
                  setIsDragOver(false);
                  handleFileSelect(e.dataTransfer.files?.[0] ?? null);
                }}
                className={cn(
                  "flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-10 text-center cursor-pointer transition-all",
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
                    <UploadCloud className="w-9 h-9 text-muted-foreground/50" />
                    <p className="text-sm text-foreground font-medium">Drag & drop a file here, or click to browse</p>
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
            </div>

            {fileError && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>{fileError}</AlertDescription>
              </Alert>
            )}

            <div className="flex justify-end">
              <Button onClick={() => uploadMutation.mutate()} disabled={!canUpload || uploadMutation.isPending} className="gap-2">
                {uploadMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileUp className="w-4 h-4" />}
                Upload
              </Button>
            </div>
            {uploadMutation.isError && (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>
                  {uploadMutation.error instanceof AICenterApiError ? uploadMutation.error.message : "Upload failed."}
                </AlertDescription>
              </Alert>
            )}
          </CardContent>
        </Card>
      </section>

      {/* ── Document Library ─────────────────────────────────────────── */}
      <section>
        <SectionHeading icon={Library} title="Document Library" description="Browse, filter, and select a document" />

        <div className="flex items-center gap-3 flex-wrap mb-4">
          <Tabs value={filterScope} onValueChange={(v) => { setFilterScope(v as DocumentListScope); setDocumentId(null); }}>
            <TabsList>
              <TabsTrigger value="all">All Documents</TabsTrigger>
              <TabsTrigger value="general">General Library</TabsTrigger>
              <TabsTrigger value="project">Project Documents</TabsTrigger>
            </TabsList>
          </Tabs>

          {filterScope === "project" && (
            <Select
              value={browseProjectId != null ? String(browseProjectId) : undefined}
              onValueChange={(v) => setBrowseProjectId(Number(v))}
            >
              <SelectTrigger className="w-56">
                <SelectValue placeholder="Narrow to a project (optional)" />
              </SelectTrigger>
              <SelectContent>
                {(projects ?? []).map((p) => (
                  <SelectItem key={p.id} value={String(p.id)}>
                    {p.project_code} — {p.project_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          <div className="flex-1 min-w-[200px] relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
            <Input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search documents by title or type…"
              className="pl-9"
            />
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[360px_1fr] gap-6 items-start">
          {/* Document list */}
          <div className="space-y-2">
            {documentsError ? (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription>Unable to load documents right now.</AlertDescription>
              </Alert>
            ) : documentsLoading ? (
              <div className="space-y-2">
                {[0, 1, 2, 3, 4].map((i) => (
                  <div key={i} className="rounded-lg border border-border p-3 space-y-2">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/2" />
                  </div>
                ))}
              </div>
            ) : filteredDocuments.length === 0 ? (
              <div className="rounded-xl border border-dashed border-border bg-card/30 p-8 text-center">
                <FileText className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
                <p className="text-sm text-muted-foreground mb-4">
                  {documents?.length ? "No documents match your search." : "No documents found for this filter yet."}
                </p>
                {!documents?.length && (
                  <Button size="sm" variant="secondary" onClick={focusUploadCard} className="gap-1.5">
                    <UploadCloud className="w-3.5 h-3.5" />
                    Upload a document
                  </Button>
                )}
              </div>
            ) : (
              filteredDocuments.map((doc: DocumentStub) => (
                <button
                  key={doc.id}
                  onClick={() => setDocumentId(doc.id)}
                  className={cn(
                    "w-full text-left rounded-lg border p-3 transition-all duration-150",
                    documentId === doc.id
                      ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                      : "border-border bg-card hover:bg-muted/50 hover:border-border/80"
                  )}
                >
                  <div className="flex items-start gap-2.5">
                    <FileText className={cn(
                      "w-4 h-4 mt-0.5 shrink-0",
                      documentId === doc.id ? "text-primary" : "text-muted-foreground/60"
                    )} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-medium text-foreground truncate">{doc.title}</p>
                        <ScopeBadge isGeneral={doc.project_id == null} className="shrink-0" />
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                        <span className="inline-flex items-center gap-1"><Tag className="w-3 h-3" />{doc.doc_type}</span>
                        <span className="inline-flex items-center gap-1"><CalendarDays className="w-3 h-3" />{doc.doc_date}</span>
                      </div>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>

          {/* Detail panel */}
          <div>
            {selectedDocument ? (
              <DocumentDetailPanel document={selectedDocument} />
            ) : (
              <div className="rounded-xl border border-dashed border-border bg-card/30 p-12 text-center">
                <FileText className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-foreground mb-2">Select a document</h3>
                <p className="text-muted-foreground">
                  Choose a document from the library to preview it, run OCR, and view contract analysis.
                </p>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}
