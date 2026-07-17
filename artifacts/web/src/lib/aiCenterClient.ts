import { getToken } from "./auth";

// ── AI Center — typed client for existing AI Center backend endpoints ──────
// Matches the existing response schemas exactly (DocumentOut,
// DocumentOCRResultOut, ContractExtractionOut, MemoryOut):
//   backend/app/schemas/documents.py
//   backend/app/schemas/document_ocr.py
//   backend/app/schemas/contract_extraction.py
//   backend/app/schemas/ai_copilot.py (MemoryOut)
// Follows the same pattern as lib/copilotClient.ts (typed fetch wrapper,
// token read fresh per call via getToken()).

export class AICenterApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "AICenterApiError";
    this.status = status;
  }
}

async function parseErrorDetail(resp: Response): Promise<string> {
  let detail = `Request failed: ${resp.status}`;
  try {
    const body = await resp.json();
    if (body?.detail) detail = String(body.detail);
  } catch {
    // response body wasn't JSON — keep the generic detail
  }
  return detail;
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const token = getToken();
  return { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...extra };
}

// ── Documents (project-scoped or General Library / organization-scoped) ──

export interface DocumentStub {
  id: number;
  project_id: number | null;
  organization_id: number | null;
  doc_type: string;
  title: string;
  doc_date: string;
  content_summary: string;
}

export type DocumentListScope = "all" | "general" | "project";

export async function listDocuments(params: {
  scope: DocumentListScope;
  projectId?: number;
  limit?: number;
}): Promise<DocumentStub[]> {
  const qs = new URLSearchParams({
    scope: params.scope,
    limit: String(params.limit ?? 100),
  });
  if (params.projectId != null) qs.set("project_id", String(params.projectId));
  const resp = await fetch(`/api/v1/documents?${qs.toString()}`, { headers: authHeaders() });
  if (!resp.ok) throw new AICenterApiError(await parseErrorDetail(resp), resp.status);
  return resp.json();
}

/** projectId omitted/null creates a General Library document (organization-scoped). */
export async function createDocument(params: {
  projectId?: number | null;
  title: string;
  docType?: string;
}): Promise<DocumentStub> {
  const resp = await fetch(`/api/v1/documents`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      project_id: params.projectId ?? null,
      title: params.title,
      doc_type: params.docType ?? "uploaded",
    }),
  });
  if (!resp.ok) throw new AICenterApiError(await parseErrorDetail(resp), resp.status);
  return resp.json();
}

// ── Document OCR (Phase 1) — unified routes work for both project and
// General Library documents; the document itself carries its own scoping. ──

export interface DocumentOCRResult {
  document_id: number;
  status: "pending" | "processing" | "completed" | "failed";
  page_count: number | null;
  detected_language: string | null;
  extraction_method: string | null;
  text_preview: string;
  text_length: number;
  text_truncated: boolean;
  error_message: string | null;
}

/** Not processed yet — no OCR/extraction has ever been run for this document. */
export const NOT_PROCESSED = "not_processed" as const;
export type NotProcessed = typeof NOT_PROCESSED;

export async function startDocumentOCR(
  documentId: number,
  file: File
): Promise<DocumentOCRResult> {
  const formData = new FormData();
  formData.append("file", file);
  const resp = await fetch(`/api/v1/documents/${documentId}/ocr`, {
    method: "POST",
    headers: authHeaders(), // no Content-Type — browser sets the multipart boundary
    body: formData,
  });
  if (!resp.ok) throw new AICenterApiError(await parseErrorDetail(resp), resp.status);
  return resp.json();
}

export async function getDocumentOCRResult(
  documentId: number
): Promise<DocumentOCRResult | NotProcessed> {
  const resp = await fetch(`/api/v1/documents/${documentId}/ocr`, {
    headers: authHeaders(),
  });
  if (resp.status === 404) return NOT_PROCESSED;
  if (!resp.ok) throw new AICenterApiError(await parseErrorDetail(resp), resp.status);
  return resp.json();
}

// ── Contract Extraction (Phase 2) ───────────────────────────────────────

export interface ContractFields {
  contract_title: string | null;
  project_code: string | null;
  employer: string | null;
  contractor: string | null;
  contract_value: string | null;
  currency: string | null;
  start_date: string | null;
  completion_date: string | null;
  payment_terms: string | null;
  retention: string | null;
  liquidated_damages: string | null;
  insurance: string | null;
  key_obligations: string[] | null;
  risks: string[] | null;
}

export interface ContractExtractionResult {
  document_id: number;
  status: "pending" | "processing" | "completed" | "failed";
  validation_status: "valid" | "invalid" | "fallback_valid" | null;
  provider: string | null;
  model_name: string | null;
  extracted_fields: ContractFields | null;
  error_message: string | null;
}

export async function startContractExtraction(
  documentId: number
): Promise<ContractExtractionResult> {
  const resp = await fetch(`/api/v1/documents/${documentId}/contract-extraction`, {
    method: "POST", headers: authHeaders(),
  });
  if (!resp.ok) throw new AICenterApiError(await parseErrorDetail(resp), resp.status);
  return resp.json();
}

export async function getContractExtraction(
  documentId: number
): Promise<ContractExtractionResult | NotProcessed> {
  const resp = await fetch(`/api/v1/documents/${documentId}/contract-extraction`, {
    headers: authHeaders(),
  });
  if (resp.status === 404) return NOT_PROCESSED;
  if (!resp.ok) throw new AICenterApiError(await parseErrorDetail(resp), resp.status);
  return resp.json();
}

// ── Memory (Phase 3 read layer, grouped server-side in Phase 6) ─────────

export interface MemoryGroupItem {
  title: string | null;
  date: string | null;
  summary: string | null;
  importance: string | null;
}

export interface MemoryGroups {
  meeting: MemoryGroupItem[];
  project: MemoryGroupItem[];
  decision: MemoryGroupItem[];
  supplier: MemoryGroupItem[];
  other: MemoryGroupItem[];
}

// Structured memory (AMAD AI Stabilization) — real AIMemoryRecord rows,
// additive alongside the original note-blob groups above.
export interface StructuredMemory {
  id: number;
  source: string;
  category: string;
  title: string;
  summary: string;
  keywords: string[];
  project_id: number | null;
  project_code: string | null;
  citation: string | null;
  confidence: number;
  priority: "High" | "Medium" | "Low" | string;
  created_at: string;
  can_delete: boolean;
  can_edit: boolean;
}

// Categories a user can pick when creating a memory from the Memory
// Center form — must match backend USER_MEMORY_CATEGORIES exactly
// (app/ai/memory_records.py).
export const USER_MEMORY_CATEGORIES = [
  { value: "project_note", label: "Project" },
  { value: "meeting_note", label: "Meeting" },
  { value: "decision_note", label: "Decision" },
  { value: "risk_note", label: "Risk" },
  { value: "contract_note", label: "Contract" },
  { value: "supplier_note", label: "Supplier" },
  { value: "site_report_note", label: "Site Report" },
  { value: "personal_note", label: "Personal Notes" },
] as const;

export type UserMemoryCategory = (typeof USER_MEMORY_CATEGORIES)[number]["value"];

export interface MemoryOut {
  memory_notes: string;
  profile_memory: string;
  groups: MemoryGroups;
  structured_memories: StructuredMemory[];
  category_counts: Record<string, number>;
}

export async function getMemory(): Promise<MemoryOut> {
  const resp = await fetch(`/api/v1/ai/memory`, { headers: authHeaders() });
  if (!resp.ok) throw new AICenterApiError(await parseErrorDetail(resp), resp.status);
  return resp.json();
}

export async function deleteMemoryRecord(id: number): Promise<void> {
  const resp = await fetch(`/api/v1/ai/memory/${id}`, { method: "DELETE", headers: authHeaders() });
  if (!resp.ok) throw new AICenterApiError(await parseErrorDetail(resp), resp.status);
}

export async function createMemoryRecord(params: {
  title: string;
  summary: string;
  category: UserMemoryCategory;
  projectCode?: string | null;
}): Promise<StructuredMemory> {
  const resp = await fetch(`/api/v1/ai/memory`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({
      title: params.title,
      summary: params.summary,
      category: params.category,
      project_code: params.projectCode || null,
    }),
  });
  if (!resp.ok) throw new AICenterApiError(await parseErrorDetail(resp), resp.status);
  return resp.json();
}

export async function updateMemoryRecord(
  id: number,
  params: { title?: string; summary?: string; category?: UserMemoryCategory },
): Promise<StructuredMemory> {
  const resp = await fetch(`/api/v1/ai/memory/${id}`, {
    method: "PATCH",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify(params),
  });
  if (!resp.ok) throw new AICenterApiError(await parseErrorDetail(resp), resp.status);
  return resp.json();
}
