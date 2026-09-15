import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SubmitReportDialog } from '@/components/siteVisits/SubmitReportDialog';
import { submitSiteVisitReport, type SiteVisit } from '@/lib/api/siteVisits';

jest.mock('@/lib/api/siteVisits', () => ({
  ...jest.requireActual('@/lib/api/siteVisits'),
  submitSiteVisitReport: jest.fn(),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const mockedSubmitReport = submitSiteVisitReport as jest.Mock;

const baseSiteVisit: SiteVisit = {
  id: 'sv1',
  leadId: 'l1',
  leadName: 'Jane Prospect',
  projectId: null,
  projectName: null,
  clientId: null,
  clientName: null,
  visitDate: '2026-02-01T10:00:00Z',
  assignedToId: null,
  assignedToName: null,
  address: '',
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

function renderDialog(siteVisit: SiteVisit, onOpenChange = jest.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <SubmitReportDialog open onOpenChange={onOpenChange} siteVisit={siteVisit} />
    </QueryClientProvider>,
  );
  return { onOpenChange };
}

describe('SubmitReportDialog', () => {
  afterEach(() => jest.clearAllMocks());

  it('submits the report and closes on success', async () => {
    mockedSubmitReport.mockResolvedValue({ ...baseSiteVisit, isCompleted: true, reportSubmittedAt: '2026-02-01T11:00:00Z' });
    const { onOpenChange } = renderDialog(baseSiteVisit);

    await userEvent.click(screen.getByRole('button', { name: /submit report/i }));

    await waitFor(() => expect(mockedSubmitReport).toHaveBeenCalledWith('sv1', { createProject: false, projectName: undefined }));
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
  });

  it('disables "also create a project" when no client is resolved yet', () => {
    renderDialog(baseSiteVisit);
    expect(screen.getByRole('switch')).toBeDisabled();
    expect(screen.getByText(/convert the lead to a client first/i)).toBeInTheDocument();
  });

  it('enables "also create a project" once a client is resolved', async () => {
    const visitWithClient: SiteVisit = { ...baseSiteVisit, clientId: 'c1', clientName: 'Jane Client' };
    renderDialog(visitWithClient);

    expect(screen.getByRole('switch')).not.toBeDisabled();
    await userEvent.click(screen.getByRole('switch'));
    expect(screen.getByLabelText(/project name/i)).toBeInTheDocument();
  });

  it('shows the backend 409 conflict message and keeps the dialog open', async () => {
    const { ApiError } = jest.requireActual('@/lib/api/client');
    mockedSubmitReport.mockRejectedValue(
      new ApiError('CONFLICT', 'Cannot create a project from this site visit: no client is linked yet.'),
    );
    const { onOpenChange } = renderDialog(baseSiteVisit);

    await userEvent.click(screen.getByRole('button', { name: /submit report/i }));

    await waitFor(() => expect(mockedSubmitReport).toHaveBeenCalled());
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });
});
