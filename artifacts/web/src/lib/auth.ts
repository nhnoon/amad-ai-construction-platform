import { setAuthTokenGetter } from "@workspace/api-client-react";

export const TOKEN_KEY = "construction_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// Initialize the API client auth token getter
setAuthTokenGetter(() => getToken());
