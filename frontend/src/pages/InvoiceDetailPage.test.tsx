import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import InvoiceDetailPage from '@/pages/InvoiceDetailPage';
import { cancelInvoice, getInvoice, sendInvoice, updateInvoice, type Invoice } from '@/lib/api/invoices';
import { getQuotation, type Quotation } from '@/lib/api/quotations';
import { createPayment, getPayments, type Payment } from '@/lib/api/payments';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/invoices', () => ({
  ...jest.requireActual('@/lib/api/invoices'),
  getInvoice: jest.fn(),
  sendInvoice: jest.fn(),
  cancelInvoice: jest.fn(),
  updateInvoice: jest.fn(),
}));
jest.mock('@/lib/api/quotations', () => ({
  ...jest.requireActual('@/lib/api/quotations'),
  getQuotation: jest.fn(),
}));
jest.mock('@/lib/api/payments', () => ({
  ...jest.requireActual('@/lib/api/payments'),
  getPayments: jest.fn(),
  createPayment: jest.fn(),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedGetInvoice = getInvoice as jest.Mock;
const mockedSend = sendInvoice as jest.Mock;
const mockedCancel = cancelInvoice as jest.Mock;
const mockedUpdate = updateInvoice as jest.Mock;
const mockedGetQuotation = getQuotation as jest.Mock;
const mockedGetPayments = getPayments as jest.Mock;
const mockedCreatePayment = createPayment as jest.Mock;

function makePayment(overrides: Partial<Payment> = {}): Payment {
  return {
    id: 'pay1',
    companyId: 'c1',
    invoiceId: 'inv1',
    clientId: 'cl1',
    projectId: 'p1',
    paymentDate: '2026-09-01',
    amount: '200.00',
    method: 'Bank transfer',
    referenceNumber: '',
    receiptUrl: '',
    notes: '',
    createdAt: '2026-09-01T00:00:00Z',
    updatedAt: '2026-09-01T00:00:00Z',
    ...overrides,
  };
}

function makeInvoice(overrides: Partial<Invoice> = {}): Invoice {
  return {
    id: 'inv1',
    companyId: 'c1',
    projectId: 'p1',
    projectName: 'Villa Renovation',
    quotationId: null,
    clientId: 'cl1',
    clientName: 'Acme Interiors',
    invoiceNumber: 'INV-000001',
    subtotal: '2400.00',
    discount: '0.00',
    tax: '0.00',
    total: '2400.00',
    dueDate: '2026-12-31',
    paymentTerms: '',
    status: 'draft',
    notes: '',
    items: [{ id: 'i1', description: 'Modular switchboard', quantity: '2.00', unit: 'nos', rate: '1200.00', amount: '2400.00' }],
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

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
    version: 2,
    subtotal: '2400.00',
    discount: '0.00',
    tax: '0.00',
    total: '2400.00',
    terms: '',
    paymentSchedule: [],
    validUntil: null,
    status: 'approved',
    notes: '',
    items: [],
    createdAt: '',
    updatedAt: '',
    ...overrides,
  };
}

function renderPage(id = 'inv1') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/invoices/${id}`]}>
        <Routes>
          <Route path="/invoices/:invoiceId" element={<InvoiceDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('InvoiceDetailPage', () => {
  beforeEach(() => mockedGetPayments.mockResolvedValue([]));
  afterEach(() => jest.clearAllMocks());

  it('renders billing lines and the financial summary using exact backend decimal strings', async () => {
    // DataTable-style dual desktop/mobile rendering means real values
    // legitimately appear more than once (item amount + summary lines
    // that happen to share the same figure here) — assert presence, not
    // a single match, matching the established pattern for this app.
    mockedGetInvoice.mockResolvedValue(makeInvoice());
    renderPage();

    expect((await screen.findAllByText('Modular switchboard')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('₹2,400.00').length).toBeGreaterThan(0);
  });

  it('shows placeholder text for empty payment terms and notes', async () => {
    mockedGetInvoice.mockResolvedValue(makeInvoice({ paymentTerms: '', notes: '' }));
    renderPage();

    expect(await screen.findByText('No payment terms provided.')).toBeInTheDocument();
    expect(screen.getByText('No notes provided.')).toBeInTheDocument();
  });

  it('never renders a Paid or Outstanding figure, since the backend exposes no payment aggregate', async () => {
    mockedGetInvoice.mockResolvedValue(makeInvoice());
    renderPage();

    await screen.findAllByText('Modular switchboard');
    expect(screen.queryByText('Paid')).not.toBeInTheDocument();
    expect(screen.queryByText('Outstanding')).not.toBeInTheDocument();
  });

  it('shows Edit and Send for a draft invoice, but not Cancel-only states', async () => {
    mockedGetInvoice.mockResolvedValue(makeInvoice({ status: 'draft' }));
    renderPage();

    expect(await screen.findByRole('button', { name: /edit/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^send$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^cancel$/i })).toBeInTheDocument();
  });

  it('shows only Cancel (no Edit or Send) for a sent invoice', async () => {
    mockedGetInvoice.mockResolvedValue(makeInvoice({ status: 'sent' }));
    renderPage();

    expect(await screen.findByRole('button', { name: /^cancel$/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^send$/i })).not.toBeInTheDocument();
  });

  it('shows no workflow actions at all for a paid invoice', async () => {
    mockedGetInvoice.mockResolvedValue(makeInvoice({ status: 'paid' }));
    renderPage();

    await screen.findAllByText('Modular switchboard');
    expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^send$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^cancel$/i })).not.toBeInTheDocument();
  });

  it('shows the backend-derived Overdue status verbatim, never re-deriving it client-side', async () => {
    mockedGetInvoice.mockResolvedValue(makeInvoice({ status: 'overdue', dueDate: '2020-01-01' }));
    renderPage();

    expect(await screen.findByText('Overdue')).toBeInTheDocument();
  });

  it('sends a draft invoice after confirmation, with non-email-claiming copy', async () => {
    mockedGetInvoice.mockResolvedValue(makeInvoice({ status: 'draft' }));
    mockedSend.mockResolvedValue(makeInvoice({ status: 'sent' }));
    renderPage();

    await userEvent.click(await screen.findByRole('button', { name: /^send$/i }));
    expect(await screen.findByText('Send this invoice?')).toBeInTheDocument();
    expect(screen.getByText(/does not dispatch an email/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Send invoice' }));

    await waitFor(() => expect(mockedSend).toHaveBeenCalledWith('inv1'));
  });

  it('cancels an invoice after confirmation, and clarifies payments are unaffected', async () => {
    mockedGetInvoice.mockResolvedValue(makeInvoice({ status: 'sent' }));
    mockedCancel.mockResolvedValue(makeInvoice({ status: 'cancelled' }));
    renderPage();

    await userEvent.click(await screen.findByRole('button', { name: /^cancel$/i }));
    expect(await screen.findByText('Cancel this invoice?')).toBeInTheDocument();
    expect(screen.getByText(/does not reverse or affect any payments/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Cancel invoice' }));

    await waitFor(() => expect(mockedCancel).toHaveBeenCalledWith('inv1'));
  });

  it('shows the backend conflict message when a workflow transition is rejected by the server', async () => {
    mockedGetInvoice.mockResolvedValue(makeInvoice({ status: 'sent' }));
    mockedCancel.mockRejectedValue(new ApiError('CONFLICT', 'This invoice cannot be cancelled from its current status.'));
    const { toast } = jest.requireMock('sonner');
    renderPage();

    await userEvent.click(await screen.findByRole('button', { name: /^cancel$/i }));
    await userEvent.click(screen.getByRole('button', { name: 'Cancel invoice' }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('This invoice cannot be cancelled from its current status.'));
  });

  it('shows a linked Source Quotation using its real quote number and version', async () => {
    mockedGetInvoice.mockResolvedValue(makeInvoice({ quotationId: 'q1' }));
    mockedGetQuotation.mockResolvedValue(makeQuotation());
    renderPage();

    expect(await screen.findByRole('link', { name: 'QT-000001 · v2' })).toHaveAttribute('href', '/quotations/q1');
  });

  it('does not attempt to fetch a source quotation for an ad hoc invoice', async () => {
    mockedGetInvoice.mockResolvedValue(makeInvoice({ quotationId: null }));
    renderPage();

    await screen.findAllByText('Modular switchboard');
    expect(screen.queryByText('Source Quotation')).not.toBeInTheDocument();
    expect(mockedGetQuotation).not.toHaveBeenCalled();
  });

  it('opens the Edit sheet prefilled with current line items and saves via PATCH', async () => {
    mockedGetInvoice.mockResolvedValue(makeInvoice({ status: 'draft' }));
    mockedUpdate.mockResolvedValue(makeInvoice({ status: 'draft', notes: 'Updated' }));
    renderPage();

    await userEvent.click(await screen.findByRole('button', { name: /edit/i }));
    expect(await screen.findByLabelText('Description')).toHaveValue('Modular switchboard');
    expect(screen.getByLabelText('Quantity')).toHaveValue('2.00');
    expect(screen.getByLabelText('Rate')).toHaveValue('1200.00');

    await userEvent.click(screen.getByRole('button', { name: 'Save changes' }));

    await waitFor(() =>
      expect(mockedUpdate).toHaveBeenCalledWith('inv1', {
        items: [{ description: 'Modular switchboard', quantity: '2.00', unit: 'nos', rate: '1200.00' }],
        discount: '0.00',
        tax: '0.00',
        dueDate: '2026-12-31',
        paymentTerms: '',
        notes: '',
      }),
    );
  });

  it('shows a not-found state for a deleted or inaccessible invoice', async () => {
    mockedGetInvoice.mockRejectedValue(new ApiError('NOT_FOUND', 'The requested invoice was not found.'));
    renderPage();

    expect(await screen.findByText('Invoice not found')).toBeInTheDocument();
  });

  it('shows a retryable error state for a generic failure', async () => {
    mockedGetInvoice.mockRejectedValue(new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.'));
    renderPage();

    expect(await screen.findByText('You do not have permission to perform this action.')).toBeInTheDocument();
  });

  it('shows a distinct mobile card representation for billing lines alongside the desktop table', async () => {
    mockedGetInvoice.mockResolvedValue(makeInvoice());
    renderPage();
    await screen.findAllByText('Modular switchboard');

    // jsdom applies no media queries, so both the desktop table and the
    // mobile card list render at once — assert the mobile card carries the
    // real fields (description, qty+unit, rate, amount), not the table markup.
    const mobileContainer = document.querySelector('.md\\:hidden');
    expect(mobileContainer).not.toBeNull();
    const mobileScope = within(mobileContainer as HTMLElement);
    expect(mobileScope.getByText('Modular switchboard')).toBeInTheDocument();
    expect(mobileScope.getByText('2.00 nos')).toBeInTheDocument();
    expect(mobileScope.getByText('Amount')).toBeInTheDocument();
  });

  it('shows a Payment History section on Invoice detail', async () => {
    mockedGetInvoice.mockResolvedValue(makeInvoice({ status: 'sent' }));
    renderPage();

    expect(await screen.findByText('Payment History')).toBeInTheDocument();
  });

  it('loads the payment list for the correct invoice', async () => {
    mockedGetInvoice.mockResolvedValue(makeInvoice({ id: 'inv1', status: 'sent' }));
    mockedGetPayments.mockResolvedValue([makePayment()]);
    renderPage('inv1');

    await waitFor(() => expect(mockedGetPayments).toHaveBeenCalledWith('inv1'));
    expect((await screen.findAllByText('Bank transfer')).length).toBeGreaterThan(0);
  });

  it('refreshes the authoritative Invoice detail after recording a payment, rendering the backend-refetched status', async () => {
    mockedGetInvoice
      .mockResolvedValueOnce(makeInvoice({ status: 'sent' }))
      .mockResolvedValueOnce(makeInvoice({ status: 'partially_paid' }));
    mockedGetPayments.mockResolvedValue([]);
    mockedCreatePayment.mockResolvedValue(makePayment());
    renderPage();

    await screen.findByText('No payments recorded yet');
    expect(screen.getByText('Sent')).toBeInTheDocument();

    await userEvent.click(screen.getAllByRole('button', { name: 'Record Payment' })[0]);
    await userEvent.type(screen.getByLabelText('Payment date'), '2026-09-01');
    await userEvent.type(screen.getByLabelText('Amount'), '200.00');
    await userEvent.click(screen.getByRole('button', { name: 'Record payment' }));

    await waitFor(() => expect(mockedGetInvoice).toHaveBeenCalledTimes(2));
    expect(await screen.findByText('Partially Paid')).toBeInTheDocument();
  });

  it('shows a permission-denied error rather than the invoice when the request is forbidden', async () => {
    mockedGetInvoice.mockRejectedValue(new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.'));
    renderPage();

    expect(await screen.findByText('You do not have permission to perform this action.')).toBeInTheDocument();
    expect(screen.queryByText('Payment History')).not.toBeInTheDocument();
  });
});
