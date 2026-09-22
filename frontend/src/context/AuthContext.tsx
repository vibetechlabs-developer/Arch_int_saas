import React, { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import {
  type User,
  login as apiLogin,
  loginPlatformAdmin as apiLoginPlatformAdmin,
  logout as apiLogout,
  fetchCurrentUser,
} from '@/lib/api/auth';
import { registerAuthFailureHandler } from '@/lib/api/client';
import { tokenStore } from '@/lib/api/tokenStore';

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  // True only for a session established via loginPlatformAdmin — the
  // backend enforces the real is_superuser+is_staff gate at that endpoint;
  // this flag just remembers which login flow succeeded, it never
  // re-derives eligibility from `user.isStaff` alone (that field can be
  // true for an ordinary staff account that ISN'T also a superuser, which
  // /platform-auth/login would have rejected).
  isPlatformAdmin: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginPlatformAdmin: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isPlatformAdmin, setIsPlatformAdmin] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Wired once so the axios client can clear app state after an
    // unrecoverable 401 (expired refresh token) without importing React.
    registerAuthFailureHandler(() => {
      setUser(null);
      setIsPlatformAdmin(false);
    });
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
        if (!cancelled) {
          setUser(currentUser);
          setIsPlatformAdmin(tokenStore.getAuthMode() === 'platform');
        }
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
    setIsPlatformAdmin(false);
  }, []);

  const loginPlatformAdmin = useCallback(async (email: string, password: string) => {
    const loggedInUser = await apiLoginPlatformAdmin(email, password);
    setUser(loggedInUser);
    setIsPlatformAdmin(true);
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setUser(null);
    setIsPlatformAdmin(false);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, isPlatformAdmin, login, loginPlatformAdmin, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
