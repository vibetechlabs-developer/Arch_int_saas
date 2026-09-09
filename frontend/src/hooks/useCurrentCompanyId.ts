import { useQuery } from '@tanstack/react-query';
import { fetchMyMemberships } from '@/lib/api/auth';
import { myMembershipsKeys } from '@/lib/queryKeys';

// There is no "get my current company" endpoint — GET /auth/memberships is
// the only source of the caller's own companyId. Matches the same
// single-active-membership assumption the app's auth/shell layer already
// makes elsewhere (no workspace switcher exists yet); a user with more
// than one active membership sees their first one here.
export function useCurrentCompanyId() {
  const query = useQuery({
    queryKey: myMembershipsKeys.all,
    queryFn: fetchMyMemberships,
    staleTime: 5 * 60 * 1000,
  });

  const memberships = query.data ?? [];
  const companyId = memberships[0]?.companyId ?? null;
  const companyName = memberships[0]?.companyName ?? null;

  return {
    ...query,
    companyId,
    companyName,
    memberships,
    hasMultipleCompanies: memberships.length > 1,
  };
}
