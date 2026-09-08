import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProjectQuotationsTab from '@/pages/projects/ProjectQuotationsTab';
import { createQuotation, getQuotations, type Quotation } from '@/lib/api/quotations';
import { getBOQSummary } from '@/lib/api/boq';
import type { Project } from '@/lib/api/projects';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/quotations', () => ({
  ...jest.requireActual('@/lib/api/quotations'),
  getQuotations: jest.fn(),
  createQuotation: jest.fn(),
}));
jest.mock('@/lib/api/boq', () => ({
  ...jest.requireActual('@/lib/api/boq'),
  getBOQSummary: jest.fn(),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedGetQuotations = getQuotations as jest.Mock;
const mockedCreate = createQuotation as jest.Mock;
const mockedGetSummary = getBOQSummary as jest.Mock;

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
      <MemoryRouter initialEntries={['/projects/p1/quotations']}>
        <Routes>
          <Route path="/projects/:projectId" element={<Outlet context={{ project }} />}>
            <Route path="quotations" element={<ProjectQuotationsTab />} />
          </Route>
          <Route path="/quotations/:quotationId" element={<div>Quotation detail page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ProjectQuotationsTab', () => {
  afterEach(() => jest.clearAllMocks());

  // DataTable renders a desktop table AND a mobile card list at once
  // (CSS media queries pick one — jsdom applies neither), so real data
  // legitimately appears twice; assert on "at least one", not one, and
  // click the first match — both are wired to the same onRowClick.

  it('renders the quotation list once loaded', async () => {
    mockedGetQuotations.mockResolvedValue([makeQuotation()]);
    renderTab();

    expect((await screen.findAllByText('QT-000001')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Acme Interiors').length).toBeGreaterThan(0);
    expect(screen.getAllByText('₹5,332.00').length).toBeGreaterThan(0);
  });

  it('shows only the latest version per quote number, with a version badge', async () => {
    mockedGetQuotations.mockResolvedValue([
      makeQuotation({ id: 'q1', version: 1, status: 'rejected' }),
      makeQuotation({ id: 'q2', version: 2, status: 'draft', total: '6000.00' }),
    ]);
    renderTab();

    expect((await screen.findAllByText('QT-000001')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('v2').length).toBeGreaterThan(0);
    expect(screen.getAllByText('₹6,000.00').length).toBeGreaterThan(0);
    expect(screen.queryByText('₹5,332.00')).not.toBeInTheDocument();
  });

  it('shows a "no quotations yet" empty state with a New Quotation CTA', async () => {
    mockedGetQuotations.mockResolvedValue([]);
    renderTab();

    expect((await screen.findAllByText('No quotations yet')).length).toBeGreaterThan(0);
  });

  it('shows the backend error message when the list request fails', async () => {
    mockedGetQuotations.mockRejectedValue(new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.'));
    renderTab();

    expect(await screen.findByText('You do not have permission to perform this action.')).toBeInTheDocument();
  });

  it('navigates to the quotation detail page on row click', async () => {
    mockedGetQuotations.mockResolvedValue([makeQuotation()]);
    renderTab();
    const [firstMatch] = await screen.findAllByText('QT-000001');

    await userEvent.click(firstMatch);

    expect(await screen.findByText('Quotation detail page')).toBeInTheDocument();
  });

  it('opens the Create Quotation sheet showing a live BOQ totals preview', async () => {
    mockedGetQuotations.mockResolvedValue([]);
    let resolveSummary: (v: unknown) => void = () => {};
    mockedGetSummary.mockReturnValue(new Promise((resolve) => (resolveSummary = resolve)));
    renderTab();
    await screen.findAllByText('No quotations yet');

    await userEvent.click(screen.getAllByRole('button', { name: /new quotation/i })[0]);

    expect(await screen.findByText(/This creates a snapshot of the project's current BOQ/)).toBeInTheDocument();
    resolveSummary({ subtotal: '5000.00', discount: '100.00', tax: '432.00', total: '5332.00' });
    expect(await screen.findByText('₹5,332.00')).toBeInTheDocument();
  });

  it('creates a quotation from the BOQ without sending items, discount, or tax, then navigates to it', async () => {
    mockedGetQuotations.mockResolvedValue([]);
    mockedGetSummary.mockResolvedValue({ subtotal: '5000.00', discount: '100.00', tax: '432.00', total: '5332.00' });
    mockedCreate.mockResolvedValue(makeQuotation({ id: 'q9' }));
    renderTab();
    await screen.findAllByText('No quotations yet');

    await userEvent.click(screen.getAllByRole('button', { name: /new quotation/i })[0]);
    await screen.findByText(/This creates a snapshot of the project's current BOQ/);
    await userEvent.type(screen.getByLabelText('Terms'), 'Payment due in 30 days');
    await userEvent.click(screen.getByRole('button', { name: 'Create quotation' }));

    await waitFor(() =>
      expect(mockedCreate).toHaveBeenCalledWith('p1', {
        validUntil: null,
        terms: 'Payment due in 30 days',
        notes: '',
      }),
    );
    const [, payload] = mockedCreate.mock.calls[0];
    expect(payload).not.toHaveProperty('items');
    expect(payload).not.toHaveProperty('discount');
    expect(payload).not.toHaveProperty('tax');
    expect(await screen.findByText('Quotation detail page')).toBeInTheDocument();
  });

  it('surfaces the backend error message when creation fails', async () => {
    mockedGetQuotations.mockResolvedValue([]);
    mockedGetSummary.mockResolvedValue({ subtotal: '0.00', discount: '0.00', tax: '0.00', total: '0.00' });
    mockedCreate.mockRejectedValue(new ApiError('CONFLICT', 'The BOQ has no includible items.'));
    renderTab();
    await screen.findAllByText('No quotations yet');

    await userEvent.click(screen.getAllByRole('button', { name: /new quotation/i })[0]);
    await screen.findByText(/This creates a snapshot of the project's current BOQ/);
    await userEvent.click(screen.getByRole('button', { name: 'Create quotation' }));

    expect(await screen.findByText('The BOQ has no includible items.')).toBeInTheDocument();
  });
});
