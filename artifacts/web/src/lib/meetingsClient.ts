import { getToken } from "./auth";

// Thin fetch wrappers for the two meetings endpoints that don't yet have
// generated React Query hooks (lib/api-client-react is generated from an
// OpenAPI spec that predates these routes). Same auth/error pattern as
// lib/copilotClient.ts — no new backend logic, just typed calls onto the
// existing FastAPI routes in backend/app/api/v1/meetings.py.

export interface MeetingActionItem {
  id: number;
  meeting_id: number;
  project_id: number;
  description: string;
  owner: string;
  due_date?: string | null;
  status: string;
  priority: string;
  source: string;
}

export interface Meeting {
  id: number;
  project_id: number;
  meeting_date: string;
  title: string;
  meeting_type: string;
}

export class MeetingsApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "MeetingsApiError";
    this.status = status;
  }
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const resp = await fetch(url, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });

  if (!resp.ok) {
    let detail = `Request failed: ${resp.status}`;
    try {
      const body = await resp.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      // response body wasn't JSON — keep the generic detail
    }
    throw new MeetingsApiError(detail, resp.status);
  }

  return resp.json() as Promise<T>;
}

export function createMeeting(
  projectId: number,
  payload: { title: string; meeting_date: string; meeting_type: string; attendees?: string[] }
): Promise<Meeting> {
  return request<Meeting>(`/api/v1/projects/${projectId}/meetings`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listActionItems(projectId: number, meetingId?: number): Promise<MeetingActionItem[]> {
  const query = meetingId != null ? `?meeting_id=${meetingId}&limit=200` : "?limit=200";
  return request<MeetingActionItem[]>(`/api/v1/projects/${projectId}/action-items${query}`);
}
