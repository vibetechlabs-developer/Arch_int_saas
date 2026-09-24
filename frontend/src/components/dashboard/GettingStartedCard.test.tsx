import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GettingStartedCard } from '@/components/dashboard/GettingStartedCard';
import { getClients } from '@/lib/api/clients';
import { getCompanyMemberships } from '@/lib/api/memberships';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/clients', () => ({ ...jest.requireActual('@/lib/api/clients'), getClients: jest.fn() }));
jest.mock('@/lib/api/memberships', () => ({
  ...jest.requireActual('@/lib/api/memberships'),
  getCompanyMemberships: jest.fn(),
}));
jest.mock('@/hooks/useCurrentCompanyId', () => ({ useCurrentCompanyId: () => ({ companyId: 'c1' }) }));

const mockedClients = getClients as jest.Mock;
const mockedMembers = getCompanyMemberships as jest.Mock;

const page = (totalItems: number) => ({ items: [], pagination: { page: 1, pageSize: 20, totalItems, totalPages: 1 } });
const kpis = (totalProjects: number, totalQuotations: number) => ({ totalProjects, activeProjects: 0, totalQuotations });

function renderCard(k = kpis(0, 0)) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <GettingStartedCard kpis={k} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('GettingStartedCard', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => jest.clearAllMocks());

  it('walks a brand-new company through every step, none done', async () => {
    mockedClients.mockResolvedValue(page(0));
    mockedMembers.mockResolvedValue(page(1));
    renderCard();

    expect(await screen.findByText('Get started')).toBeInTheDocument();
    expect(screen.getByText(/0 of 4 done/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Add a client' })).toHaveAttribute('href', '/clients');
    expect(screen.getByRole('link', { name: 'Invite people' })).toHaveAttribute('href', '/settings/members');
  });

  it('ticks steps off from real data', async () => {
    mockedClients.mockResolvedValue(page(3));
    mockedMembers.mockResolvedValue(page(1));
    renderCard(kpis(2, 0));

    expect(await screen.findByText(/2 of 4 done/)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Add a client' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Open projects' })).toBeInTheDocument();
  });

  it('disappears entirely once every step is done', async () => {
    mockedClients.mockResolvedValue(page(1));
    mockedMembers.mockResolvedValue(page(3));
    renderCard(kpis(1, 1));

    await waitFor(() => expect(mockedMembers).toHaveBeenCalled());
    await waitFor(() => expect(screen.queryByText('Get started')).not.toBeInTheDocument());
  });

  it('leaves out a step the caller is not permitted to read instead of showing it forever undone', async () => {
    mockedClients.mockRejectedValue(new ApiError('PERMISSION_ERROR', 'no'));
    mockedMembers.mockResolvedValue(page(1));
    renderCard();

    expect(await screen.findByText(/0 of 3 done/)).toBeInTheDocument();
    expect(screen.queryByText('Add your first client')).not.toBeInTheDocument();
  });

  it('can be dismissed, and stays dismissed', async () => {
    mockedClients.mockResolvedValue(page(0));
    mockedMembers.mockResolvedValue(page(1));
    const { unmount } = renderCard();

    await userEvent.click(await screen.findByRole('button', { name: /dismiss getting started/i }));
    expect(screen.queryByText('Get started')).not.toBeInTheDocument();
    unmount();

    renderCard();
    await waitFor(() => expect(mockedClients).toHaveBeenCalledTimes(2));
    expect(screen.queryByText('Get started')).not.toBeInTheDocument();
  });
});
