import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PaymentHistory } from '@/components/payments/PaymentHistory';
import { createPayment, getPayments, voidPayment, type Payment } from '@/lib/api/payments';
import type { Invoice } from '@/lib/api/invoices';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/payments', () => ({
  ...jest.requireActual('@/lib/api/payments'),
  getPayments: jest.fn(),
  createPayment: jest.fn(),
  voidPayment: jest.fn(),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedGetPayments = getPayments as jest.Mock;
const mockedCreate = createPayment as jest.Mock;
const mockedVoid = voidPayment as jest.Mock;

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
    subtotal: '500.00',
    discount: '0.00',
    tax: '0.00',
    total: '500.00',
    dueDate: null,
    paymentTerms: '',
    status: 'sent',
    notes: '',
    items: [],
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

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
    referenceNumber: 'TXN-123',
    receiptUrl: '',
    notes: '',
    createdAt: '2026-09-01T00:00:00Z',
    updatedAt: '2026-09-01T00:00:00Z',
    ...overrides,
  };
}

function renderHistory(props: Partial<React.ComponentProps<typeof PaymentHistory>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <PaymentHistory invoice={makeInvoice()} canRecordPayment {...props} />
    </QueryClientProvider>,
  );
}

describe('PaymentHistory', () => {
  afterEach(() => jest.clearAllMocks());

  it('shows a loading state before payments resolve', async () => {
    let resolveRequest: (v: Payment[]) => void = () => {};
    mockedGetPayments.mockReturnValue(new Promise((resolve) => (resolveRequest = resolve)));
    renderHistory();

    expect(screen.queryByText('Bank transfer')).not.toBeInTheDocument();
    resolveRequest([makePayment()]);
    expect(await screen.findAllByText('Bank transfer')).not.toHaveLength(0);
  });

  it('renders payment rows with amount, method, and reference (success state)', async () => {
    mockedGetPayments.mockResolvedValue([makePayment()]);
    renderHistory();

    expect((await screen.findAllByText('₹200.00')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Bank transfer').length).toBeGreaterThan(0);
    expect(screen.getAllByText('TXN-123').length).toBeGreaterThan(0);
  });

  it('shows a "no payments recorded yet" empty state with a Record Payment CTA', async () => {
    mockedGetPayments.mockResolvedValue([]);
    renderHistory();

    expect(await screen.findByText('No payments recorded yet')).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'Record Payment' }).length).toBeGreaterThan(0);
  });

  it('omits the Record Payment CTA entirely when canRecordPayment is false', async () => {
    mockedGetPayments.mockResolvedValue([]);
    renderHistory({ canRecordPayment: false });

    await screen.findByText('No payments recorded yet');
    expect(screen.queryByRole('button', { name: /record payment/i })).not.toBeInTheDocument();
  });

  it('shows the backend error message when the payment list request fails', async () => {
    mockedGetPayments.mockRejectedValue(new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.'));
    renderHistory();

    expect(await screen.findByText('You do not have permission to perform this action.')).toBeInTheDocument();
  });

  it('records a payment with the exact payload shape, sending no invoiceId in the body', async () => {
    mockedGetPayments.mockResolvedValue([]);
    mockedCreate.mockResolvedValue(makePayment());
    renderHistory();
    await screen.findByText('No payments recorded yet');

    await userEvent.click(screen.getAllByRole('button', { name: 'Record Payment' })[0]);
    await userEvent.type(screen.getByLabelText('Payment date'), '2026-09-01');
    await userEvent.type(screen.getByLabelText('Amount'), '200.00');
    await userEvent.type(screen.getByLabelText('Method'), 'Bank transfer');
    await userEvent.type(screen.getByLabelText('Reference'), 'TXN-123');
    await userEvent.click(screen.getByRole('button', { name: 'Record payment' }));

    await waitFor(() =>
      expect(mockedCreate).toHaveBeenCalledWith('inv1', {
        paymentDate: '2026-09-01',
        amount: '200.00',
        method: 'Bank transfer',
        referenceNumber: 'TXN-123',
        receiptUrl: '',
        notes: '',
      }),
    );
    const [, payload] = mockedCreate.mock.calls[0];
    expect(payload).not.toHaveProperty('invoiceId');
  });

  it('requires a payment date and a positive amount before submitting', async () => {
    mockedGetPayments.mockResolvedValue([]);
    renderHistory();
    await screen.findByText('No payments recorded yet');

    await userEvent.click(screen.getAllByRole('button', { name: 'Record Payment' })[0]);
    await userEvent.click(screen.getByRole('button', { name: 'Record payment' }));

    expect(await screen.findByText('Payment date is required')).toBeInTheDocument();
    expect(screen.getByText('Amount is required')).toBeInTheDocument();
    expect(mockedCreate).not.toHaveBeenCalled();
  });

  it('rejects a zero amount', async () => {
    mockedGetPayments.mockResolvedValue([]);
    renderHistory();
    await screen.findByText('No payments recorded yet');

    await userEvent.click(screen.getAllByRole('button', { name: 'Record Payment' })[0]);
    await userEvent.type(screen.getByLabelText('Payment date'), '2026-09-01');
    await userEvent.type(screen.getByLabelText('Amount'), '0.00');
    await userEvent.click(screen.getByRole('button', { name: 'Record payment' }));

    expect(await screen.findByText('Amount must be greater than zero')).toBeInTheDocument();
    expect(mockedCreate).not.toHaveBeenCalled();
  });

  it('surfaces a 409 business conflict from the backend on create (e.g. an unpayable invoice status)', async () => {
    mockedGetPayments.mockResolvedValue([]);
    mockedCreate.mockRejectedValue(new ApiError('CONFLICT', "Cannot record a payment against an invoice with status 'draft'."));
    renderHistory();
    await screen.findByText('No payments recorded yet');

    await userEvent.click(screen.getAllByRole('button', { name: 'Record Payment' })[0]);
    await userEvent.type(screen.getByLabelText('Payment date'), '2026-09-01');
    await userEvent.type(screen.getByLabelText('Amount'), '200.00');
    await userEvent.click(screen.getByRole('button', { name: 'Record payment' }));

    expect(await screen.findByText("Cannot record a payment against an invoice with status 'draft'.")).toBeInTheDocument();
  });

  it('disables the submit button while the create mutation is pending, preventing duplicate submission', async () => {
    mockedGetPayments.mockResolvedValue([]);
    let resolveCreate: (v: Payment) => void = () => {};
    mockedCreate.mockReturnValue(new Promise((resolve) => (resolveCreate = resolve)));
    renderHistory();
    await screen.findByText('No payments recorded yet');

    await userEvent.click(screen.getAllByRole('button', { name: 'Record Payment' })[0]);
    await userEvent.type(screen.getByLabelText('Payment date'), '2026-09-01');
    await userEvent.type(screen.getByLabelText('Amount'), '200.00');
    const submitButton = screen.getByRole('button', { name: 'Record payment' });
    await userEvent.click(submitButton);

    await waitFor(() => expect(submitButton).toBeDisabled());
    resolveCreate(makePayment());
  });

  it('shows a confirmation dialog before voiding a payment, and calls the void endpoint on confirm', async () => {
    mockedGetPayments.mockResolvedValue([makePayment()]);
    mockedVoid.mockResolvedValue(undefined);
    renderHistory();
    const [voidButton] = await screen.findAllByRole('button', { name: /void payment of 200\.00/i });

    await userEvent.click(voidButton);
    expect(await screen.findByText('Void this payment?')).toBeInTheDocument();
    expect(mockedVoid).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole('button', { name: 'Void payment' }));

    await waitFor(() => expect(mockedVoid).toHaveBeenCalledWith('pay1'));
  });

  it('shows a distinct mobile card representation for payment rows alongside the desktop table', async () => {
    mockedGetPayments.mockResolvedValue([makePayment()]);
    renderHistory();
    await screen.findAllByText('Bank transfer');

    const mobileContainer = document.querySelector('.md\\:hidden');
    expect(mobileContainer).not.toBeNull();
    const mobileScope = within(mobileContainer as HTMLElement);
    expect(mobileScope.getByText('Bank transfer')).toBeInTheDocument();
    expect(mobileScope.getByText('Ref: TXN-123')).toBeInTheDocument();
  });
});
