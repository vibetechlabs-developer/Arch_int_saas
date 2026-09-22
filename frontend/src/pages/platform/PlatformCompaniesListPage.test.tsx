import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/test-utils';
import PlatformCompaniesListPage from '@/pages/platform/PlatformCompaniesListPage';
import { getCompanies } from '@/lib/api/company';
import { ApiError, type PaginationMeta } from '@/lib/api/client';
import type { Company } from '@/lib/api/company';

jest.mock('@/lib/api/company');
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const mockedGetCompanies = getCompanies as jest.Mock;

const pagination: PaginationMeta = { page: 1, pageSize: 25, totalItems: 1, totalPages: 1 };

const company: Company = {
  id: '1',
  name: 'Acme Interiors',
  status: 'active',
  currency: 'INR',
  gstNumber: '29ABCDE1234F1Z5',
  logoUrl: '',
  settings: {},
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
};

describe('PlatformCompaniesListPage', () => {
  afterEach(() => jest.clearAllMocks());

  it('renders companies once the request resolves (success state)', async () => {
    mockedGetCompanies.mockResolvedValue({ items: [company], pagination });
    renderWithProviders(<PlatformCompaniesListPage />, { route: '/platform/companies' });

    expect((await screen.findAllByText('Acme Interiors')).length).toBeGreaterThan(0);
  });

  it('shows a "no companies yet" empty state with a create CTA when there are none', async () => {
    mockedGetCompanies.mockResolvedValue({
      items: [],
      pagination: { page: 1, pageSize: 25, totalItems: 0, totalPages: 0 },
    });
    renderWithProviders(<PlatformCompaniesListPage />, { route: '/platform/companies' });

    expect((await screen.findAllByText('No companies yet')).length).toBeGreaterThan(0);
  });

  it('shows the backend error message when the list request fails', async () => {
    mockedGetCompanies.mockRejectedValue(
      new ApiError('AUTHENTICATION_ERROR', 'Authentication credentials were not provided.'),
    );
    renderWithProviders(<PlatformCompaniesListPage />, { route: '/platform/companies' });

    expect(await screen.findByText('Authentication credentials were not provided.')).toBeInTheDocument();
  });
});
