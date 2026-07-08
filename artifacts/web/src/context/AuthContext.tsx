import React, { createContext, useContext, useEffect, useState } from "react";
import { useLogin, getMe } from "@workspace/api-client-react";
import type { UserOut, LoginInput } from "@workspace/api-client-react";
import { getToken, setToken as saveToken, clearToken } from "../lib/auth";

interface AuthContextType {
  user: UserOut | null;
  token: string | null;
  login: (data: LoginInput) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [token, setToken] = useState<string | null>(getToken());
  const [isLoading, setIsLoading] = useState(true);

  const loginMutation = useLogin();

  useEffect(() => {
    async function restoreSession() {
      if (token) {
        try {
          // Use raw fetch for restoration to avoid hook dependency cycle issues
          const userData = await getMe();
          setUser(userData);
        } catch (error) {
          console.error("Failed to restore session", error);
          clearToken();
          setToken(null);
          setUser(null);
        }
      }
      setIsLoading(false);
    }
    restoreSession();
  }, [token]);

  const login = async (data: LoginInput) => {
    const response = await loginMutation.mutateAsync({ data });
    saveToken(response.access_token);
    setToken(response.access_token);
    setUser(response.user);
  };

  const logout = () => {
    clearToken();
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isLoading }}>
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
