// Tracks which of the caller's active company memberships is "current" for
// this browser session. TenantJWTAuthentication (backend) resolves tenant
// scope per-request from a companyId query param/body field — it is never
// baked into the JWT — so switching workspace is purely a client-side
// concern: persist the choice, attach it to every outgoing request, and
// reset any tenant-scoped cache on change. A plain module-level store (not
// React state) so the axios request interceptor — which runs outside React
// — can read the current value synchronously on every call.
const STORAGE_KEY = 'activeCompanyId';

type Listener = () => void;
const listeners = new Set<Listener>();

let activeCompanyId: string | null = (() => {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
})();

export const activeCompanyStore = {
  get: (): string | null => activeCompanyId,
  set: (companyId: string | null): void => {
    if (companyId === activeCompanyId) return;
    activeCompanyId = companyId;
    try {
      if (companyId) localStorage.setItem(STORAGE_KEY, companyId);
      else localStorage.removeItem(STORAGE_KEY);
    } catch {
      // Private browsing / storage disabled — the in-memory value still
      // works for the rest of this session.
    }
    listeners.forEach((listener) => listener());
  },
  subscribe: (listener: Listener): (() => void) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
};
