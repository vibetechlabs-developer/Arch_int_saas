import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/test-utils';
import ClientsListPage from '@/pages/clients/ClientsListPage';
import { getClients } from '@/lib/api/clients';
import { ApiError, type PaginationMeta } from '@/lib/api/client';
import type { Client } from '@/lib/api/clients';

jest.mock('@/lib/api/clients');
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const mockedGetClients = getClients as jest.Mock;

const pagination: PaginationMeta = { page: 1, pageSize: 25, totalItems: 1, totalPages: 1 };

const client: Client = {
  id: '1',
  name: 'Acme Interiors',
  companyName: 'Acme Pvt Ltd',
  email: 'hi@acme.com',
  mobile: '9876543210',
  gstin: '',
  addresses: [],
  notes: '',
  companyId: 'c1',
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
};

describe('ClientsListPage', () => {
  afterEach(() => jest.clearAllMocks());

  it('renders clients once the request resolves (success state)', async () => {
    mockedGetClients.mockResolvedValue({ items: [client], pagination });
    renderWithProviders(<ClientsListPage />, { route: '/clients' });

    // DataTable renders a desktop table AND a mobile card list at once
    // (CSS media queries pick one — jsdom applies neither), so real client
    // data legitimately appears twice; assert on "at least one", not one.
    expect((await screen.findAllByText('Acme Interiors')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Acme Pvt Ltd').length).toBeGreaterThan(0);
  });

  it('shows a "no clients yet" empty state with a create CTA when the company has none', async () => {
    mockedGetClients.mockResolvedValue({
      items: [],
      pagination: { page: 1, pageSize: 25, totalItems: 0, totalPages: 0 },
    });
    renderWithProviders(<ClientsListPage />, { route: '/clients' });

    expect((await screen.findAllByText('No clients yet')).length).toBeGreaterThan(0);
  });

  it('shows the backend error message when the list request fails', async () => {
    mockedGetClients.mockRejectedValue(
      new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.'),
    );
    renderWithProviders(<ClientsListPage />, { route: '/clients' });

    expect(await screen.findByText('You do not have permission to perform this action.')).toBeInTheDocument();
  });
});
