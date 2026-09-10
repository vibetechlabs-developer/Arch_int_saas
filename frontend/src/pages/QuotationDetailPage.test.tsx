import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import QuotationDetailPage from '@/pages/QuotationDetailPage';
import {
  approveQuotation,
  getQuotation,
  getQuotations,
  rejectQuotation,
  reviseQuotation,
  sendQuotation,
  type Quotation,
} from '@/lib/api/quotations';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/quotations', () => ({
  ...jest.requireActual('@/lib/api/quotations'),
  getQuotation: jest.fn(),
  getQuotations: jest.fn(),
  sendQuotation: jest.fn(),
  approveQuotation: jest.fn(),
  rejectQuotation: jest.fn(),
  reviseQuotation: jest.fn(),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('@/lib/pdf', () => ({ previewPdf: jest.fn(), downloadPdf: jest.fn() }));

const mockedGetQuotation = getQuotation as jest.Mock;
const mockedGetQuotations = getQuotations as jest.Mock;
const mockedSend = sendQuotation as jest.Mock;
const mockedApprove = approveQuotation as jest.Mock;
const mockedReject = rejectQuotation as jest.Mock;
const mockedRevise = reviseQuotation as jest.Mock;
const mockedPreviewPdf = jest.requireMock('@/lib/pdf').previewPdf as jest.Mock;
const mockedDownloadPdf = jest.requireMock('@/lib/pdf').downloadPdf as jest.Mock;

function makeQuotation(overrides: Partial<Quotation> = {}): Quotation {
  return {
    id: 'q1',
    companyId: 'c1',
    projectId: 'p1',
    projectName: 'Villa Renovation',
    boqId: 'boq1',
    clientId: 'cl1',
    clientName: 'Acme Interiors',
    quoteNumber: 'QT-000001',
    version: 1,
    subtotal: '5000.00',
    discount: '100.00',
    tax: '432.00',
    total: '5332.00',
    terms: '',
    paymentSchedule: [],
    validUntil: '2026-12-31',
    status: 'draft',
    notes: '',
    items: [
      {
        id: 'i1',
        productId: null,
        productName: null,
        description: 'Modular switchboard',
        quantity: '2.00',
        unit: 'nos',
        rate: '1200.00',
        amount: '2400.00',
      },
    ],
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function renderPage(id = 'q1') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/quotations/${id}`]}>
        <Routes>
          <Route path="/quotations/:quotationId" element={<QuotationDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('QuotationDetailPage', () => {
  afterEach(() => jest.clearAllMocks());

  it('shows Preview/Download PDF actions targeting this exact version, not "latest"', async () => {
    const v1 = makeQuotation({ id: 'q1', version: 1 });
    const v2 = makeQuotation({ id: 'q2', version: 2 });
    mockedGetQuotation.mockImplementation((id: string) => Promise.resolve(id === 'q2' ? v2 : v1));
    mockedGetQuotations.mockResolvedValue([v2, v1]);
    mockedPreviewPdf.mockResolvedValue(undefined);
    mockedDownloadPdf.mockResolvedValue(undefined);

    // Viewing the OLDER version (q1) directly -- its own PDF actions must
    // target q1, never silently substitute the newer q2.
    renderPage('q1');
    await screen.findByText('Modular switchboard');

    await userEvent.click(screen.getByRole('button', { name: 'Preview PDF' }));
    await waitFor(() => expect(mockedPreviewPdf).toHaveBeenCalledWith('/quotations/q1/pdf'));

    await userEvent.click(screen.getByRole('button', { name: 'Download PDF' }));
    await waitFor(() => expect(mockedDownloadPdf).toHaveBeenCalledWith('/quotations/q1/pdf'));
  });

  it('renders line items and the financial summary using exact backend decimal strings', async () => {
    mockedGetQuotation.mockResolvedValue(makeQuotation());
    mockedGetQuotations.mockResolvedValue([makeQuotation()]);
    renderPage();

    expect(await screen.findByText('Modular switchboard')).toBeInTheDocument();
    expect(screen.getByText('₹5,000.00')).toBeInTheDocument();
    expect(screen.getByText('₹100.00')).toBeInTheDocument();
    expect(screen.getByText('₹432.00')).toBeInTheDocument();
    expect(screen.getByText('₹5,332.00')).toBeInTheDocument();
  });

  it('shows placeholder text for empty terms and notes', async () => {
    mockedGetQuotation.mockResolvedValue(makeQuotation({ terms: '', notes: '' }));
    mockedGetQuotations.mockResolvedValue([makeQuotation()]);
    renderPage();

    expect(await screen.findByText('No terms provided.')).toBeInTheDocument();
    expect(screen.getByText('No notes provided.')).toBeInTheDocument();
  });

  it('shows only Send for a draft quotation', async () => {
    mockedGetQuotation.mockResolvedValue(makeQuotation({ status: 'draft' }));
    mockedGetQuotations.mockResolvedValue([makeQuotation({ status: 'draft' })]);
    renderPage();

    expect(await screen.findByRole('button', { name: /^send$/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^approve$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^reject$/i })).not.toBeInTheDocument();
  });

  it('shows Approve and Reject (not Send) for a sent quotation', async () => {
    mockedGetQuotation.mockResolvedValue(makeQuotation({ status: 'sent' }));
    mockedGetQuotations.mockResolvedValue([makeQuotation({ status: 'sent' })]);
    renderPage();

    expect(await screen.findByRole('button', { name: /^approve$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^reject$/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^send$/i })).not.toBeInTheDocument();
  });

  it('shows no workflow action buttons for an approved quotation, only Revise', async () => {
    mockedGetQuotation.mockResolvedValue(makeQuotation({ status: 'approved' }));
    mockedGetQuotations.mockResolvedValue([makeQuotation({ status: 'approved' })]);
    renderPage();

    expect(await screen.findByRole('button', { name: /revise/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^send$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^approve$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^reject$/i })).not.toBeInTheDocument();
  });

  it('hides every workflow action, including Revise, when viewing a non-latest version', async () => {
    const v1 = makeQuotation({ id: 'q1', version: 1, status: 'rejected' });
    const v2 = makeQuotation({ id: 'q2', version: 2, status: 'draft' });
    mockedGetQuotation.mockResolvedValue(v1);
    mockedGetQuotations.mockResolvedValue([v1, v2]);
    renderPage('q1');

    await screen.findByText('Version 1 of 2');
    expect(screen.queryByRole('button', { name: /revise/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^send$/i })).not.toBeInTheDocument();
  });

  it('navigates between versions via the lineage Previous/Next controls', async () => {
    const v1 = makeQuotation({ id: 'q1', version: 1, status: 'rejected' });
    const v2 = makeQuotation({ id: 'q2', version: 2, status: 'draft' });
    mockedGetQuotation.mockImplementation((id: string) => Promise.resolve(id === 'q1' ? v1 : v2));
    mockedGetQuotations.mockResolvedValue([v1, v2]);
    renderPage('q1');

    await screen.findByText('Version 1 of 2');
    await userEvent.click(screen.getByRole('button', { name: /next version/i }));

    await waitFor(() => expect(mockedGetQuotation).toHaveBeenCalledWith('q2'));
    expect(await screen.findByText('Version 2 of 2')).toBeInTheDocument();
  });

  it('sends a draft quotation after confirmation', async () => {
    mockedGetQuotation.mockResolvedValue(makeQuotation({ status: 'draft' }));
    mockedGetQuotations.mockResolvedValue([makeQuotation({ status: 'draft' })]);
    mockedSend.mockResolvedValue(makeQuotation({ status: 'sent' }));
    renderPage();

    await userEvent.click(await screen.findByRole('button', { name: /^send$/i }));
    expect(await screen.findByText('Send this quotation?')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Send quotation' }));

    await waitFor(() => expect(mockedSend).toHaveBeenCalledWith('q1'));
  });

  it('approves a sent quotation after confirmation', async () => {
    mockedGetQuotation.mockResolvedValue(makeQuotation({ status: 'sent' }));
    mockedGetQuotations.mockResolvedValue([makeQuotation({ status: 'sent' })]);
    mockedApprove.mockResolvedValue(makeQuotation({ status: 'approved' }));
    renderPage();

    await userEvent.click(await screen.findByRole('button', { name: /^approve$/i }));
    expect(await screen.findByText('Approve this quotation?')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Approve quotation' }));

    await waitFor(() => expect(mockedApprove).toHaveBeenCalledWith('q1'));
  });

  it('shows the backend conflict message when a workflow transition is rejected by the server', async () => {
    mockedGetQuotation.mockResolvedValue(makeQuotation({ status: 'sent' }));
    mockedGetQuotations.mockResolvedValue([makeQuotation({ status: 'sent' })]);
    mockedReject.mockRejectedValue(new ApiError('CONFLICT', 'Only a sent quotation can be rejected.'));
    const { toast } = jest.requireMock('sonner');
    renderPage();

    await userEvent.click(await screen.findByRole('button', { name: /^reject$/i }));
    await userEvent.click(screen.getByRole('button', { name: 'Reject quotation' }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Only a sent quotation can be rejected.'));
  });

  it('opens the Revise sheet prefilled with the current terms and notes, then navigates to the new version', async () => {
    mockedGetQuotation.mockResolvedValue(makeQuotation({ terms: 'Net 30', notes: 'Client prefers matte finish' }));
    mockedGetQuotations.mockResolvedValue([makeQuotation()]);
    mockedRevise.mockResolvedValue(makeQuotation({ id: 'q2', version: 2 }));
    renderPage();

    await userEvent.click(await screen.findByRole('button', { name: /revise/i }));
    expect(await screen.findByLabelText('Terms')).toHaveValue('Net 30');
    expect(screen.getByLabelText('Notes')).toHaveValue('Client prefers matte finish');

    await userEvent.click(screen.getByRole('button', { name: 'Create revision' }));

    await waitFor(() => expect(mockedRevise).toHaveBeenCalledWith('q1', { validUntil: '2026-12-31', terms: 'Net 30', notes: 'Client prefers matte finish' }));
  });

  it('shows a not-found state for a deleted or inaccessible quotation', async () => {
    mockedGetQuotation.mockRejectedValue(new ApiError('NOT_FOUND', 'The requested quotation was not found.'));
    renderPage();

    expect(await screen.findByText('Quotation not found')).toBeInTheDocument();
  });

  it('shows a retryable error state for a generic failure', async () => {
    mockedGetQuotation.mockRejectedValue(new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.'));
    renderPage();

    expect(await screen.findByText('You do not have permission to perform this action.')).toBeInTheDocument();
  });
});
