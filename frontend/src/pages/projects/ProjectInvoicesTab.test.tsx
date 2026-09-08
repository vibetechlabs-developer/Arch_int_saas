import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProjectInvoicesTab from '@/pages/projects/ProjectInvoicesTab';
import { createInvoice, getInvoices, type Invoice } from '@/lib/api/invoices';
import { getQuotations, type Quotation } from '@/lib/api/quotations';
import type { Project } from '@/lib/api/projects';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/invoices', () => ({
  ...jest.requireActual('@/lib/api/invoices'),
  getInvoices: jest.fn(),
  createInvoice: jest.fn(),
}));
jest.mock('@/lib/api/quotations', () => ({
  ...jest.requireActual('@/lib/api/quotations'),
  getQuotations: jest.fn(),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedGetInvoices = getInvoices as jest.Mock;
const mockedCreate = createInvoice as jest.Mock;
const mockedGetQuotations = getQuotations as jest.Mock;

const project: Project = {
  id: 'p1',
  name: 'Villa Renovation',
  companyId: 'c1',
  clientId: 'cl1',
  clientName: 'Acme Interiors',
  startDate: null,
  deadline: null,
  status: 'draft',
  priority: '',
  assignedToId: null,
  assignedToName: null,
  followUpReminderAt: null,
  createdAt: '',
  updatedAt: '',
};

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
    items: [],
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
    version: 1,
    subtotal: '5000.00',
    discount: '100.00',
    tax: '432.00',
    total: '5332.00',
    terms: '',
    paymentSchedule: [],
    validUntil: null,
    status: 'approved',
    notes: '',
    items: [],
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

function renderTab() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/projects/p1/invoices']}>
        <Routes>
          <Route path="/projects/:projectId" element={<Outlet context={{ project }} />}>
            <Route path="invoices" element={<ProjectInvoicesTab />} />
          </Route>
          <Route path="/invoices/:invoiceId" element={<div>Invoice detail page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ProjectInvoicesTab', () => {
  afterEach(() => jest.clearAllMocks());

  it('renders the invoice list once loaded', async () => {
    mockedGetInvoices.mockResolvedValue([makeInvoice()]);
    renderTab();

    expect((await screen.findAllByText('INV-000001')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('₹2,400.00').length).toBeGreaterThan(0);
  });

  it('does not render any Paid or Balance column, since the backend exposes no such field', async () => {
    mockedGetInvoices.mockResolvedValue([makeInvoice()]);
    renderTab();

    await screen.findAllByText('INV-000001');
    expect(screen.queryByText('Paid')).not.toBeInTheDocument();
    expect(screen.queryByText('Balance')).not.toBeInTheDocument();
  });

  it('shows a "no invoices yet" empty state with a Create Invoice CTA', async () => {
    mockedGetInvoices.mockResolvedValue([]);
    renderTab();

    expect((await screen.findAllByText('No invoices yet')).length).toBeGreaterThan(0);
  });

  it('shows the backend error message when the list request fails', async () => {
    mockedGetInvoices.mockRejectedValue(new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.'));
    renderTab();

    expect(await screen.findByText('You do not have permission to perform this action.')).toBeInTheDocument();
  });

  it('navigates to the invoice detail page on row click', async () => {
    mockedGetInvoices.mockResolvedValue([makeInvoice()]);
    renderTab();
    const [firstMatch] = await screen.findAllByText('INV-000001');

    await userEvent.click(firstMatch);

    expect(await screen.findByText('Invoice detail page')).toBeInTheDocument();
  });

  it('creates an invoice from an approved quotation, copying its totals with no discount/tax override', async () => {
    mockedGetInvoices.mockResolvedValue([]);
    mockedGetQuotations.mockResolvedValue([makeQuotation()]);
    mockedCreate.mockResolvedValue(makeInvoice({ id: 'inv9' }));
    renderTab();
    await screen.findAllByText('No invoices yet');

    await userEvent.click(screen.getAllByRole('button', { name: /create invoice/i })[0]);
    await screen.findByRole('radio', { name: /QT-000001/i });
    await userEvent.click(screen.getByRole('radio', { name: /QT-000001/i }));
    expect(await screen.findByText("This invoice will use the quotation's totals")).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Create invoice' }));

    await waitFor(() =>
      expect(mockedCreate).toHaveBeenCalledWith('p1', { quotationId: 'q1', dueDate: null, paymentTerms: '', notes: '' }),
    );
    expect(await screen.findByText('Invoice detail page')).toBeInTheDocument();
  });

  it('requires a quotation to be selected before creating from a quotation', async () => {
    mockedGetInvoices.mockResolvedValue([]);
    mockedGetQuotations.mockResolvedValue([makeQuotation()]);
    renderTab();
    await screen.findAllByText('No invoices yet');

    await userEvent.click(screen.getAllByRole('button', { name: /create invoice/i })[0]);
    await screen.findByRole('radio', { name: /QT-000001/i });
    await userEvent.click(screen.getByRole('button', { name: 'Create invoice' }));

    expect(await screen.findByText('Select a quotation to continue.')).toBeInTheDocument();
    expect(mockedCreate).not.toHaveBeenCalled();
  });

  it('shows an empty state instead of a picker when there are no approved quotations', async () => {
    mockedGetInvoices.mockResolvedValue([]);
    mockedGetQuotations.mockResolvedValue([makeQuotation({ status: 'draft' })]);
    renderTab();
    await screen.findAllByText('No invoices yet');

    await userEvent.click(screen.getAllByRole('button', { name: /create invoice/i })[0]);

    expect(await screen.findByText('No approved quotations')).toBeInTheDocument();
  });

  it('creates an ad hoc invoice with manually entered line items, validated before submit', async () => {
    mockedGetInvoices.mockResolvedValue([]);
    mockedGetQuotations.mockResolvedValue([]);
    mockedCreate.mockResolvedValue(makeInvoice({ id: 'inv9' }));
    renderTab();
    await screen.findAllByText('No invoices yet');

    await userEvent.click(screen.getAllByRole('button', { name: /create invoice/i })[0]);
    await userEvent.click(screen.getByRole('tab', { name: 'Manual' }));

    await userEvent.click(screen.getByRole('button', { name: 'Create invoice' }));
    expect(await screen.findByText('Description is required')).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText('Description'), 'Custom work');
    await userEvent.type(screen.getByLabelText('Quantity'), '2');
    await userEvent.type(screen.getByLabelText('Rate'), '100.00');
    await userEvent.type(screen.getByLabelText('Discount'), '20.00');
    await userEvent.type(screen.getByLabelText('Tax'), '10.00');
    await userEvent.click(screen.getByRole('button', { name: 'Create invoice' }));

    await waitFor(() =>
      expect(mockedCreate).toHaveBeenCalledWith('p1', {
        items: [{ description: 'Custom work', quantity: '2', unit: undefined, rate: '100.00' }],
        discount: '20.00',
        tax: '10.00',
        dueDate: null,
        paymentTerms: '',
        notes: '',
      }),
    );
    expect(await screen.findByText('Invoice detail page')).toBeInTheDocument();
  });

  it('adds and removes line items in the manual create form', async () => {
    mockedGetInvoices.mockResolvedValue([]);
    mockedGetQuotations.mockResolvedValue([]);
    renderTab();
    await screen.findAllByText('No invoices yet');

    await userEvent.click(screen.getAllByRole('button', { name: /create invoice/i })[0]);
    await userEvent.click(screen.getByRole('tab', { name: 'Manual' }));

    expect(screen.getAllByLabelText('Description')).toHaveLength(1);
    await userEvent.click(screen.getByRole('button', { name: /add line/i }));
    expect(screen.getAllByLabelText('Description')).toHaveLength(2);

    await userEvent.click(screen.getByRole('button', { name: 'Remove line 2' }));
    expect(screen.getAllByLabelText('Description')).toHaveLength(1);
  });
});
