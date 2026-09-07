import React, { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { type User, login as apiLogin, logout as apiLogout, fetchCurrentUser } from '@/lib/api/auth';
import { registerAuthFailureHandler } from '@/lib/api/client';
import { tokenStore } from '@/lib/api/tokenStore';

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Wired once so the axios client can clear app state after an
    // unrecoverable 401 (expired refresh token) without importing React.
    registerAuthFailureHandler(() => setUser(null));
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      if (!tokenStore.getAccessToken()) {
        setIsLoading(false);
        return;
      }
      try {
        const currentUser = await fetchCurrentUser();
        if (!cancelled) setUser(currentUser);
      } catch {
        tokenStore.clear();
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const loggedInUser = await apiLogin(email, password);
    setUser(loggedInUser);
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
  }, []);

  return <AuthContext.Provider value={{ user, isLoading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
