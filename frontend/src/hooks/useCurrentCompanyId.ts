import { useEffect, useSyncExternalStore } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchMyMemberships } from '@/lib/api/auth';
import { myMembershipsKeys } from '@/lib/queryKeys';
import { activeCompanyStore } from '@/lib/activeCompany';

// GET /auth/memberships is the source of every company the caller belongs
// to; activeCompanyStore (a plain module-level store, not React state, so
// the axios interceptor can also read it outside React) tracks which one is
// "current" for this browser session. If the stored id no longer matches
// any active membership (first login, a switched account, or a membership
// that was since revoked) this falls back to the first membership and
// persists that as the new default — matching the single-membership
// behavior this hook always had before a switcher existed.
export function useCurrentCompanyId() {
  const query = useQuery({
    queryKey: myMembershipsKeys.all,
    queryFn: fetchMyMemberships,
    staleTime: 5 * 60 * 1000,
  });

  const storedCompanyId = useSyncExternalStore(activeCompanyStore.subscribe, activeCompanyStore.get);
  const memberships = query.data ?? [];
  const active =
    memberships.find((membership) => membership.companyId === storedCompanyId) ?? memberships[0] ?? null;

  useEffect(() => {
    if (active && active.companyId !== storedCompanyId) {
      activeCompanyStore.set(active.companyId);
    }
  }, [active, storedCompanyId]);

  return {
    ...query,
    companyId: active?.companyId ?? null,
    companyName: active?.companyName ?? null,
    memberships,
    hasMultipleCompanies: memberships.length > 1,
  };
}
