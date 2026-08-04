import { setAuthTokenGetter, setRefreshHandler, setOnAuthFailure, refreshToken as refreshTokenApi } from "@workspace/api-client-react";
import { apiErrorStatus } from "./apiErrors";

// RC1 Phase 1 Sprint 2 — Frontend Session Integration.
//
// Access and refresh tokens are stored under separate localStorage keys.
// Known, accepted risk (unchanged from Sprint 1's backend report, carried
// forward rather than silently dropped): any script able to execute on
// this origin (XSS) can read both keys — localStorage has no httpOnly
// equivalent. A full httpOnly-cookie migration was evaluated for this
// sprint and deliberately deferred (see Sprint 2 report §3/§14) rather
// than attempted as a partial migration, since a half-cookie/half-bearer
// scheme would be harder to reason about than the status quo. Neither
// token is ever logged (no console.log/console.error of a token value
// anywhere in this module or its callers) or rendered in any UI.
export const TOKEN_KEY = "construction_token";
export const REFRESH_TOKEN_KEY = "construction_refresh_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

// Access-token change listeners — see subscribeToken() below. Exists so
// AuthContext's `token` state stays correct even when the token changes
// from OUTSIDE a React event handler, namely a silent refresh triggered
// by the shared fetch layer (custom-fetch.ts) deep inside some unrelated
// request. Without this, any code holding the access token in React state
// (e.g. pages/copilot.tsx's own hand-rolled fetch calls, which bypass the
// generated client and its Authorization-header auto-attach) would keep
// using a stale value until the next full page load — harmless while
// access tokens lived 8 hours, but a real bug once Sprint 2 shortens that
// lifetime to 30 minutes (see ACCESS_TOKEN_EXPIRE_MINUTES).
type TokenListener = (token: string | null) => void;
const _tokenListeners = new Set<TokenListener>();

export function subscribeToken(listener: TokenListener): () => void {
  _tokenListeners.add(listener);
  return () => _tokenListeners.delete(listener);
}

function notifyTokenListeners(token: string | null): void {
  _tokenListeners.forEach((listener) => listener(token));
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  notifyTokenListeners(token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  notifyTokenListeners(null);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setRefreshToken(token: string): void {
  localStorage.setItem(REFRESH_TOKEN_KEY, token);
}

export function clearRefreshToken(): void {
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

/** Clears both tokens together — the only correct way to end a local
 * session, so logout / refresh-failure / session-expiry all funnel
 * through this rather than each remembering to clear both keys. */
export function clearAllTokens(): void {
  clearToken();
  clearRefreshToken();
}

// Initialize the API client auth token getter
setAuthTokenGetter(() => getToken());

// Distinguishes "the backend explicitly rejected the refresh token" (401
// — expired, revoked, or replay-detected: the session really is gone,
// safe to clear) from "we couldn't even reach the backend to ask" (offline,
// backend down, a 5xx, a parse error — the stored refresh token might
// still be perfectly valid). Set by the refresh handler immediately
// before it resolves, read once by setOnAuthFailure right after —
// customFetch always awaits the handler and calls onAuthFailure
// synchronously after, so there is no interleaving even when several
// concurrent callers share one in-flight refresh (see
// getOrStartRefresh in custom-fetch.ts): they all observe the SAME
// attempt's outcome, set exactly once per attempt.
let _lastRefreshFailureWasNetworkError = false;

// Silent refresh (see setRefreshHandler in custom-fetch.ts): invoked by
// the shared fetch layer on a 401, at most once per concurrent burst.
// Must resolve to the new access token on success or null on any
// failure — swallows its own errors so customFetch doesn't need to.
setRefreshHandler(async () => {
  const currentRefreshToken = getRefreshToken();
  _lastRefreshFailureWasNetworkError = false;
  if (!currentRefreshToken) return null;
  try {
    const response = await refreshTokenApi({ refresh_token: currentRefreshToken });
    setToken(response.access_token);
    setRefreshToken(response.refresh_token);
    return response.access_token;
  } catch (err) {
    // Anything other than a clean 401 (network failure, offline, backend
    // unavailable, an unexpected 5xx, a response-parse error) means we
    // genuinely don't know whether the refresh token is still good — do
    // not treat it as a rejection.
    if (apiErrorStatus(err) !== 401) {
      _lastRefreshFailureWasNetworkError = true;
    }
    return null;
  }
});

// Fired whenever a refresh attempt resolves to null. Only actually clears
// the session when that null came from a real 401 rejection — a
// network/backend-availability failure leaves both tokens in place so a
// later request, once connectivity returns, can retry refresh with the
// still-intact stored refresh token instead of forcing a fresh login.
// Does not redirect itself (this module has no router access);
// AuthContext observes the cleared token (via subscribeToken) and its own
// request failures to drive the redirect to /login.
setOnAuthFailure(() => {
  if (_lastRefreshFailureWasNetworkError) return;
  clearAllTokens();
});
