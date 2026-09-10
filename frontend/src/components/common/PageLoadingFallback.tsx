import { Loader2 } from 'lucide-react';

// Suspense fallback shown for the moment a route's own lazy-loaded chunk
// (App.tsx) is being fetched — mirrors ProtectedRoute's existing
// spinner treatment. Sized to sit inside the Shell's content area (or
// fill the pre-Shell viewport for /login and /reset-password), never a
// full h-screen overlay that would cover the sidebar/header too.
export function PageLoadingFallback() {
  return (
    <div className="flex min-h-[50vh] w-full items-center justify-center">
      <Loader2 className="size-6 animate-spin text-text-tertiary" />
    </div>
  );
}
