import { getToken } from "./auth";

// ── AMAD Copilot — real backend AI pipeline client (Phase 5) ────────────────
// Calls the EXISTING backend endpoint POST /api/v1/ai/copilot/query, which
// already implements intent detection, RBAC-scoped retrieval, grounding
// validation, an LLM provider abstraction (mock or real, per backend
// LLM_PROVIDER config), source citations, and bilingual (EN/AR) responses.
// This file adds no new backend logic — it's a typed fetch wrapper matching
// the existing CopilotQueryRequest/CopilotQueryResponse schema exactly.

export interface CopilotCitation {
  id: number;
  source_type: string;
  source_id: string;
  label: string;
  evidence_snippet?: string | null;
  ui_metadata?: Record<string, unknown> | null;
}

// The backend's render_blocks are typed dicts on the Python side
// (list[dict[str, Any]]) with a `type` discriminant; kept loose here to
// match that same contract rather than re-declaring a strict union.
export interface CopilotRenderBlock {
  type: string;
  [key: string]: unknown;
}

export interface CopilotQueryResponse {
  conversation_id: number;
  message_id: number;
  answer: string;
  status: string;
  intent: string;
  citations: CopilotCitation[];
  confidence: string;
  model?: string | null;
  provider?: string | null;
  latency_ms: number;
  evidence_count: number;
  short_summary?: string | null;
  key_findings?: string[] | null;
  comparison_data?: Record<string, unknown> | null;
  follow_up_suggestions?: string[] | null;
  clarification_required: boolean;
  clarification_question?: string | null;
  clarification_options?: string[] | null;
  resolved_query?: string | null;
  domains_used?: string[] | null;
  is_multi_domain: boolean;
  render_blocks?: CopilotRenderBlock[] | null;
}

export class CopilotApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "CopilotApiError";
    this.status = status;
  }
}

export async function postCopilotQuery(
  payload: { question: string; conversation_id?: number; project_id?: number },
  signal?: AbortSignal
): Promise<CopilotQueryResponse> {
  const token = getToken();
  const resp = await fetch("/api/v1/ai/copilot/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!resp.ok) {
    let detail = `Request failed: ${resp.status}`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // response body wasn't JSON — keep the generic detail
    }
    throw new CopilotApiError(detail, resp.status);
  }

  return resp.json() as Promise<CopilotQueryResponse>;
}

// Calls the EXISTING backend endpoint POST /api/v1/ai/agents/procurement —
// same response shape as postCopilotQuery (same RBAC-scoped retrieval, LLM
// provider, grounding, and citations). Retrieval is always procurement-scoped
// regardless of `question` (see execute_procurement_agent) — an optional
// question only changes what the LLM is asked to focus on in its answer.
export async function postProcurementAgent(
  payload: { project_id?: number; conversation_id?: number; language: "en" | "ar"; question?: string },
  signal?: AbortSignal
): Promise<CopilotQueryResponse> {
  const token = getToken();
  const resp = await fetch("/api/v1/ai/agents/procurement", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!resp.ok) {
    let detail = `Request failed: ${resp.status}`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // response body wasn't JSON — keep the generic detail
    }
    throw new CopilotApiError(detail, resp.status);
  }

  return resp.json() as Promise<CopilotQueryResponse>;
}

// Calls the EXISTING backend endpoint POST /api/v1/ai/agents/meeting — same
// response shape as postCopilotQuery. meeting_id omitted runs the
// portfolio-wide meetings status summary (execute_meeting_agent's
// no-meeting_id branch); meeting_id given runs the single-meeting detail
// analysis. Same RBAC-scoped retrieval, LLM provider, grounding, and
// citations as every other agent endpoint.
export async function postMeetingAgent(
  payload: {
    meeting_id?: number;
    project_id?: number;
    conversation_id?: number;
    language: "en" | "ar";
    question?: string;
  },
  signal?: AbortSignal
): Promise<CopilotQueryResponse> {
  const token = getToken();
  const resp = await fetch("/api/v1/ai/agents/meeting", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(payload),
    signal,
  });

  if (!resp.ok) {
    let detail = `Request failed: ${resp.status}`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // response body wasn't JSON — keep the generic detail
    }
    throw new CopilotApiError(detail, resp.status);
  }

  return resp.json() as Promise<CopilotQueryResponse>;
}

// Mirrors the backend's own Arabic-detection heuristic (pipeline.py
// `_detect_arabic`) so the frontend can pick RTL layout and bilingual UI
// labels per message, matching whatever language the backend replied in.
export function isArabicText(text: string | undefined | null): boolean {
  if (!text) return false;
  const arabicChars = (text.match(/[؀-ۿ]/g) ?? []).length;
  return arabicChars / text.length > 0.2;
}
