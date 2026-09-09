import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCurrentCompanyId } from '@/hooks/useCurrentCompanyId';
import { activeCompanyStore } from '@/lib/activeCompany';
import { fetchMyMemberships } from '@/lib/api/auth';

jest.mock('@/lib/api/auth', () => ({
  ...jest.requireActual('@/lib/api/auth'),
  fetchMyMemberships: jest.fn(),
}));

const mockedFetchMyMemberships = fetchMyMemberships as jest.MockedFunction<typeof fetchMyMemberships>;

function wrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe('useCurrentCompanyId', () => {
  afterEach(() => {
    activeCompanyStore.set(null);
    jest.clearAllMocks();
  });

  it('defaults to the first membership when nothing is stored', async () => {
    mockedFetchMyMemberships.mockResolvedValue([
      { companyId: 'c1', companyName: 'Studio Alpha', status: 'active', roleName: 'Owner' },
      { companyId: 'c2', companyName: 'Studio Beta', status: 'active', roleName: 'Admin' },
    ]);

    const { result } = renderHook(() => useCurrentCompanyId(), { wrapper });

    await waitFor(() => expect(result.current.companyId).toBe('c1'));
    expect(result.current.hasMultipleCompanies).toBe(true);
    expect(activeCompanyStore.get()).toBe('c1');
  });

  it('honors a previously-stored companyId that is still an active membership', async () => {
    activeCompanyStore.set('c2');
    mockedFetchMyMemberships.mockResolvedValue([
      { companyId: 'c1', companyName: 'Studio Alpha', status: 'active', roleName: 'Owner' },
      { companyId: 'c2', companyName: 'Studio Beta', status: 'active', roleName: 'Admin' },
    ]);

    const { result } = renderHook(() => useCurrentCompanyId(), { wrapper });

    await waitFor(() => expect(result.current.companyId).toBe('c2'));
    expect(result.current.companyName).toBe('Studio Beta');
  });

  it('falls back to the first membership when the stored companyId is no longer valid', async () => {
    activeCompanyStore.set('stale-revoked-company');
    mockedFetchMyMemberships.mockResolvedValue([
      { companyId: 'c1', companyName: 'Studio Alpha', status: 'active', roleName: 'Owner' },
    ]);

    const { result } = renderHook(() => useCurrentCompanyId(), { wrapper });

    await waitFor(() => expect(result.current.companyId).toBe('c1'));
    expect(activeCompanyStore.get()).toBe('c1');
  });

  it('reports a single membership with hasMultipleCompanies false', async () => {
    mockedFetchMyMemberships.mockResolvedValue([
      { companyId: 'c1', companyName: 'Studio Alpha', status: 'active', roleName: 'Owner' },
    ]);

    const { result } = renderHook(() => useCurrentCompanyId(), { wrapper });

    await waitFor(() => expect(result.current.companyId).toBe('c1'));
    expect(result.current.hasMultipleCompanies).toBe(false);
  });
});
