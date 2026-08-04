import React, { createContext, useContext, useEffect, useState } from "react";
import { useLogin, getMe, logout as logoutApi, logoutAllSessions as logoutAllSessionsApi } from "@workspace/api-client-react";
import type { UserOut, LoginInput } from "@workspace/api-client-react";
import {
  getToken,
  setToken as saveToken,
  clearToken,
  getRefreshToken,
  setRefreshToken as saveRefreshToken,
  clearAllTokens,
  subscribeToken,
} from "../lib/auth";
import { apiErrorStatus } from "../lib/apiErrors";

interface AuthContextType {
  user: UserOut | null;
  token: string | null;
  login: (data: LoginInput) => Promise<void>;
  logout: () => Promise<void>;
  // RC1 Phase 1 Sprint 2 — revoke every session for the caller (all
  // devices), not just the current one. See POST /auth/logout-all.
  logoutAllSessions: () => Promise<void>;
  isLoading: boolean;
  // Phase 2 — Security & Authentication Hardening: the Change Password
  // screen calls this after a successful change so the app picks up the
  // fresh token/user (must_change_password now false) without a second
  // login round-trip. Does not touch the refresh token/session — password
  // change reissues an access token only (see backend
  // app/api/v1/auth.py::change_password).
  setSession: (token: string, user: UserOut) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [token, setToken] = useState<string | null>(getToken());
  const [isLoading, setIsLoading] = useState(true);

  const loginMutation = useLogin();

  // Keeps `token` state correct even when the stored token changes from
  // OUTSIDE a call to login()/setSession()/logout() below — namely a
  // silent refresh (or a refresh-failure clear) triggered deep inside an
  // unrelated request by the shared fetch layer. See subscribeToken()'s
  // doc comment in lib/auth.ts for why this matters once access tokens
  // are short-lived (Part G).
  useEffect(() => {
    return subscribeToken((newToken) => {
      setToken(newToken);
      if (!newToken) setUser(null);
    });
  }, []);

  useEffect(() => {
    async function restoreSession() {
      if (token) {
        try {
          // A 401 here transparently attempts a silent refresh (see
          // custom-fetch.ts's setRefreshHandler wiring in lib/auth.ts)
          // before this call ever throws — so reaching the catch below
          // means refresh was already attempted and failed, or the
          // failure isn't auth-related at all (network/backend down).
          const userData = await getMe();
          setUser(userData);
        } catch (error) {
          // Only an actual 401 (refresh attempted and failed, or no
          // refresh token to try) means the session is really gone —
          // clear it. Any other failure (offline, backend unavailable,
          // a transient 5xx) must NOT delete a possibly-still-valid
          // token; the stored session survives to retry on next load.
          if (apiErrorStatus(error) === 401) {
            clearAllTokens();
            setToken(null);
            setUser(null);
          }
        }
      }
      setIsLoading(false);
    }
    restoreSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const login = async (data: LoginInput) => {
    const response = await loginMutation.mutateAsync({ data });
    saveToken(response.access_token);
    saveRefreshToken(response.refresh_token);
    setToken(response.access_token);
    setUser(response.user);
  };

  const logout = async () => {
    const refreshTokenValue = getRefreshToken();
    // Clear local credentials immediately — the UI must never keep
    // showing an authenticated shell while a network call to /auth/logout
    // is still in flight (or fails outright, e.g. offline). The backend
    // call below is best-effort revocation, not a precondition for the
    // local logout to "count".
    clearAllTokens();
    setToken(null);
    setUser(null);
    if (refreshTokenValue) {
      try {
        await logoutApi({ refresh_token: refreshTokenValue });
      } catch {
        // Backend unreachable or already-revoked — the local session is
        // already cleared either way, so there is nothing left to do.
      }
    }
  };

  const logoutAllSessions = async () => {
    // Unlike logout() above, this needs the CURRENT access token to
    // authorize the call, so it must fire before local credentials are
    // cleared — then clear regardless of outcome (best-effort, same as
    // single-session logout).
    try {
      await logoutAllSessionsApi();
    } catch {
      // Best-effort — fall through to clearing the local session anyway.
    } finally {
      clearAllTokens();
      setToken(null);
      setUser(null);
    }
  };

  const setSession = (newToken: string, newUser: UserOut) => {
    saveToken(newToken);
    setToken(newToken);
    setUser(newUser);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, logoutAllSessions, isLoading, setSession }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
