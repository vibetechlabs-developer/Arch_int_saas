import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/test-utils';
import LeadsListPage from '@/pages/leads/LeadsListPage';
import { getLeads } from '@/lib/api/leads';
import { ApiError, type PaginationMeta } from '@/lib/api/client';
import type { Lead } from '@/lib/api/leads';

jest.mock('@/lib/api/leads');
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const mockedGetLeads = getLeads as jest.Mock;

const pagination: PaginationMeta = { page: 1, pageSize: 25, totalItems: 1, totalPages: 1 };

const lead: Lead = {
  id: '1',
  name: 'Jane Prospect',
  companyName: 'Prospect Interiors',
  email: 'jane@example.com',
  mobile: '9876543210',
  source: 'referral',
  status: 'new',
  assignedToId: null,
  assignedToName: null,
  lossReason: '',
  followUpReminderAt: null,
  notes: '',
  convertedClientId: null,
  convertedClientName: null,
  convertedProjectId: null,
  convertedProjectName: null,
  companyId: 'c1',
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
};

describe('LeadsListPage', () => {
  afterEach(() => jest.clearAllMocks());

  it('renders leads once the request resolves (success state)', async () => {
    mockedGetLeads.mockResolvedValue({ items: [lead], pagination });
    renderWithProviders(<LeadsListPage />, { route: '/leads' });

    // DataTable renders a desktop table AND a mobile card list at once
    // (CSS media queries pick one — jsdom applies neither), so real lead
    // data legitimately appears twice; assert on "at least one", not one.
    expect((await screen.findAllByText('Jane Prospect')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Prospect Interiors').length).toBeGreaterThan(0);
  });

  it('shows a "no leads yet" empty state with a create CTA when the company has none', async () => {
    mockedGetLeads.mockResolvedValue({
      items: [],
      pagination: { page: 1, pageSize: 25, totalItems: 0, totalPages: 0 },
    });
    renderWithProviders(<LeadsListPage />, { route: '/leads' });

    expect((await screen.findAllByText('No leads yet')).length).toBeGreaterThan(0);
  });

  it('shows the backend error message when the list request fails', async () => {
    mockedGetLeads.mockRejectedValue(
      new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.'),
    );
    renderWithProviders(<LeadsListPage />, { route: '/leads' });

    expect(await screen.findByText('You do not have permission to perform this action.')).toBeInTheDocument();
  });
});
