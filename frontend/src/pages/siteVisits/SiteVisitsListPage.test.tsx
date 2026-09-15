import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/test-utils';
import SiteVisitsListPage from '@/pages/siteVisits/SiteVisitsListPage';
import { getSiteVisits } from '@/lib/api/siteVisits';
import { ApiError, type PaginationMeta } from '@/lib/api/client';
import type { SiteVisit } from '@/lib/api/siteVisits';

jest.mock('@/lib/api/siteVisits');
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const mockedGetSiteVisits = getSiteVisits as jest.Mock;

const pagination: PaginationMeta = { page: 1, pageSize: 25, totalItems: 1, totalPages: 1 };

const siteVisit: SiteVisit = {
  id: '1',
  leadId: null,
  leadName: null,
  projectId: 'p1',
  projectName: 'Kitchen Remodel',
  clientId: 'c1',
  clientName: 'Acme Interiors',
  visitDate: '2026-02-01T10:00:00Z',
  assignedToId: null,
  assignedToName: null,
  address: '221B Baker St',
  measurements: '',
  requirements: '',
  photoUrls: [],
  videoUrls: [],
  notes: '',
  budget: null,
  siteConditions: '',
  followUpActions: '',
  reportSubmittedAt: null,
  isCompleted: false,
  companyId: 'co1',
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
};

describe('SiteVisitsListPage', () => {
  afterEach(() => jest.clearAllMocks());

  it('renders site visits once the request resolves (success state)', async () => {
    mockedGetSiteVisits.mockResolvedValue({ items: [siteVisit], pagination });
    renderWithProviders(<SiteVisitsListPage />, { route: '/site-visits' });

    expect((await screen.findAllByText('Kitchen Remodel')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Acme Interiors').length).toBeGreaterThan(0);
  });

  it('shows a "no site visits yet" empty state with a create CTA when there are none', async () => {
    mockedGetSiteVisits.mockResolvedValue({
      items: [],
      pagination: { page: 1, pageSize: 25, totalItems: 0, totalPages: 0 },
    });
    renderWithProviders(<SiteVisitsListPage />, { route: '/site-visits' });

    expect((await screen.findAllByText('No site visits yet')).length).toBeGreaterThan(0);
  });

  it('shows the backend error message when the list request fails', async () => {
    mockedGetSiteVisits.mockRejectedValue(
      new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.'),
    );
    renderWithProviders(<SiteVisitsListPage />, { route: '/site-visits' });

    expect(await screen.findByText('You do not have permission to perform this action.')).toBeInTheDocument();
  });
});
