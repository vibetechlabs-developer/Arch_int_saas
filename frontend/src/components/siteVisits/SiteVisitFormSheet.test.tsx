import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SiteVisitFormSheet } from '@/components/siteVisits/SiteVisitFormSheet';
import { createSiteVisit, updateSiteVisit, type SiteVisit } from '@/lib/api/siteVisits';

jest.mock('@/lib/api/siteVisits', () => ({
  ...jest.requireActual('@/lib/api/siteVisits'),
  createSiteVisit: jest.fn(),
  updateSiteVisit: jest.fn(),
}));
jest.mock('@/lib/api/leads', () => ({
  ...jest.requireActual('@/lib/api/leads'),
  getLeads: jest.fn().mockResolvedValue({ items: [], pagination: { page: 1, pageSize: 25, totalItems: 0, totalPages: 0 } }),
}));
jest.mock('@/lib/api/projects', () => ({
  ...jest.requireActual('@/lib/api/projects'),
  getProjects: jest.fn().mockResolvedValue({ items: [], pagination: { page: 1, pageSize: 100, totalItems: 0, totalPages: 0 } }),
}));
jest.mock('@/lib/api/memberships', () => ({ searchActiveCompanyMembers: jest.fn().mockResolvedValue([]) }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedCreateSiteVisit = createSiteVisit as jest.Mock;
const mockedUpdateSiteVisit = updateSiteVisit as jest.Mock;

const existingSiteVisit: SiteVisit = {
  id: 'sv1',
  leadId: null,
  leadName: null,
  projectId: 'p1',
  projectName: 'Kitchen Remodel',
  clientId: 'c1',
  clientName: 'Acme Interiors',
  visitDate: '2026-02-01T10:00:00Z',
  assignedToId: null,
  assignedToName: null,
  address: 'Old Address',
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
  createdAt: '',
  updatedAt: '',
};

function renderSheet(props: Partial<React.ComponentProps<typeof SiteVisitFormSheet>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const onOpenChange = jest.fn();
  render(
    <QueryClientProvider client={queryClient}>
      <SiteVisitFormSheet open onOpenChange={onOpenChange} {...props} />
    </QueryClientProvider>,
  );
  return { onOpenChange };
}

describe('SiteVisitFormSheet', () => {
  afterEach(() => jest.clearAllMocks());

  it('rejects a blank visit date before ever calling the API', async () => {
    renderSheet();

    await userEvent.click(screen.getByRole('button', { name: /schedule visit/i }));

    expect(await screen.findByText('A visit date/time is required')).toBeInTheDocument();
    expect(mockedCreateSiteVisit).not.toHaveBeenCalled();
  });

  it('requires a lead or a project to be selected before creating a site visit', async () => {
    renderSheet();
    await userEvent.type(screen.getByLabelText('Visit date'), '2026-03-01T10:00');
    await userEvent.click(screen.getByRole('button', { name: /schedule visit/i }));

    expect(await screen.findByText('Link this visit to a lead or a project.')).toBeInTheDocument();
    expect(mockedCreateSiteVisit).not.toHaveBeenCalled();
  });

  it('pre-fills the form and PATCHes the existing site visit when editing', async () => {
    mockedUpdateSiteVisit.mockResolvedValue({ ...existingSiteVisit, address: 'New Address' });
    renderSheet({ siteVisit: existingSiteVisit });

    expect(screen.getByLabelText('Address')).toHaveValue('Old Address');

    await userEvent.clear(screen.getByLabelText('Address'));
    await userEvent.type(screen.getByLabelText('Address'), 'New Address');
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() =>
      expect(mockedUpdateSiteVisit).toHaveBeenCalledWith('sv1', expect.objectContaining({ address: 'New Address' })),
    );
  });

  it('shows linked lead/project as static text in edit mode, not the comboboxes', () => {
    renderSheet({ siteVisit: existingSiteVisit });

    expect(screen.getByText('Kitchen Remodel')).toBeInTheDocument();
    expect(screen.queryByText('Select a lead…')).not.toBeInTheDocument();
    expect(screen.queryByText('Select a project…')).not.toBeInTheDocument();
  });

  it('maps a 400 VALIDATION_ERROR field back onto the matching form field', async () => {
    const { ApiError } = jest.requireActual('@/lib/api/client');
    mockedUpdateSiteVisit.mockRejectedValue(
      new ApiError('VALIDATION_ERROR', 'Request validation failed.', [
        { field: 'address', issue: 'address must be 500 characters or fewer.' },
      ]),
    );
    renderSheet({ siteVisit: existingSiteVisit });

    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    expect(await screen.findByText('address must be 500 characters or fewer.')).toBeInTheDocument();
  });
});
