import { useQuery } from '@tanstack/react-query';
import { getCompany } from '@/lib/api/company';
import { companyKeys } from '@/lib/queryKeys';
import { useCurrentCompanyId } from '@/hooks/useCurrentCompanyId';

const DEFAULT_CURRENCY = 'INR';

// The one place money-formatting components resolve a real ISO-4217
// currency code from — `Company.currency` (BE-074's Phase 14: "use the
// current company's REAL currency support... do not hardcode INR/USD").
// Falls back to INR only while the company hasn't loaded yet or the
// lookup fails, never a silent wrong-currency swap once real data exists.
export function useCompanyCurrency(): { currency: string; isLoading: boolean } {
  const { companyId } = useCurrentCompanyId();

  const { data: company, isLoading } = useQuery({
    queryKey: companyId ? companyKeys.detail(companyId) : ['company', 'unresolved'],
    queryFn: () => getCompany(companyId!),
    enabled: !!companyId,
    staleTime: 5 * 60 * 1000,
  });

  return { currency: company?.currency || DEFAULT_CURRENCY, isLoading: isLoading && !!companyId };
}
