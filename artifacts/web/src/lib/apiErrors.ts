// custom-fetch.ts's ApiError class isn't re-exported from
// @workspace/api-client-react's public index (only the generated hooks +
// schemas + auth-getter helpers are) — these small duck-typed helpers let
// every mutation error handler pull out the HTTP status and the FastAPI
// `detail` message without importing an internal class.

export function apiErrorStatus(err: unknown): number | undefined {
  if (typeof err === "object" && err !== null && "status" in err) {
    const status = (err as { status?: unknown }).status;
    if (typeof status === "number") return status;
  }
  return undefined;
}

export function apiErrorDetail(err: unknown, fallback = "Something went wrong."): string {
  if (typeof err === "object" && err !== null) {
    const data = (err as { data?: unknown }).data;
    if (data && typeof data === "object" && "detail" in data) {
      const detail = (data as { detail?: unknown }).detail;
      if (typeof detail === "string") return detail;
    }
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

export function isConflict(err: unknown): boolean {
  return apiErrorStatus(err) === 409;
}
