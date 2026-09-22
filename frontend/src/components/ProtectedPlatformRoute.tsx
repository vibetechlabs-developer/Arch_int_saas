import type { ReactNode } from 'react';
import { Loader2 } from 'lucide-react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';

// Mirrors ProtectedRoute exactly, but gates on isPlatformAdmin instead of a
// plain `user` check, and redirects to the separate /platform/login rather
// than the tenant /login — a company-user session should never be treated
// as eligible here, and vice versa.
export function ProtectedPlatformRoute({ children }: { children: ReactNode }) {
  const { user, isLoading, isPlatformAdmin } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-app">
        <Loader2 className="size-6 animate-spin text-text-tertiary" />
      </div>
    );
  }

  if (!user || !isPlatformAdmin) {
    return <Navigate to="/platform/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
