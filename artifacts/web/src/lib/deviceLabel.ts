// RC1 Phase 1 Sprint 2 — a short, safe, client-derived label sent as
// LoginInput.device to make GET /auth/sessions readable (e.g. "Chrome on
// Windows") instead of just a raw IP/timestamp. Deliberately coarse:
// browser + OS family only, no version numbers or full UA string (the
// backend already captures the full `user_agent` header separately — see
// app/models/auth.py::RefreshToken.user_agent — so nothing is lost by
// keeping this label minimal), and no geolocation of any kind.
export function getDeviceLabel(): string {
  if (typeof navigator === "undefined" || !navigator.userAgent) return "Unknown device";

  const ua = navigator.userAgent;

  let os = "Unknown OS";
  if (/Windows/i.test(ua)) os = "Windows";
  else if (/Mac OS X|Macintosh/i.test(ua)) os = "macOS";
  else if (/Android/i.test(ua)) os = "Android";
  else if (/iPhone|iPad|iPod/i.test(ua)) os = "iOS";
  else if (/Linux/i.test(ua)) os = "Linux";

  let browser = "Unknown browser";
  if (/Edg\//i.test(ua)) browser = "Edge";
  else if (/OPR\/|Opera/i.test(ua)) browser = "Opera";
  else if (/Chrome\//i.test(ua)) browser = "Chrome";
  else if (/Firefox\//i.test(ua)) browser = "Firefox";
  else if (/Safari\//i.test(ua)) browser = "Safari";

  return `${browser} on ${os}`;
}
