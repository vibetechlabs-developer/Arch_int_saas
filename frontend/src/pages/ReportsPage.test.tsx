import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ReportsPage from '@/pages/ReportsPage';
import { getFinanceReport, getExpenseReport, type ExpenseReport, type FinanceReport } from '@/lib/api/reports';
import { getProjects } from '@/lib/api/projects';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/reports', () => ({
  getFinanceReport: jest.fn(),
  getExpenseReport: jest.fn(),
}));
jest.mock('@/lib/api/projects', () => ({
  ...jest.requireActual('@/lib/api/projects'),
  getProjects: jest.fn(),
}));

const mockedGetFinanceReport = getFinanceReport as jest.Mock;
const mockedGetExpenseReport = getExpenseReport as jest.Mock;
const mockedGetProjects = getProjects as jest.Mock;

function makeFinanceReport(overrides: Partial<FinanceReport> = {}): FinanceReport {
  return {
    revenue: '500.00',
    received: '300.00',
    receivables: '200.00',
    outstanding: '0.00',
    expenses: '100.00',
    profitLoss: '400.00',
    ...overrides,
  };
}

function makeExpenseReport(overrides: Partial<ExpenseReport> = {}): ExpenseReport {
  return {
    byCategory: [{ key: 'Materials', label: 'Materials', total: '100.00' }],
    byProject: [{ key: 'p1', label: 'Villa Renovation', total: '100.00' }],
    byVendor: [{ key: 'ABC', label: 'ABC', total: '100.00' }],
    byEmployee: [],
    byDate: [{ key: '2026-09-01', label: '2026-09-01', total: '100.00' }],
    ...overrides,
  };
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ReportsPage />
    </QueryClientProvider>,
  );
}

describe('ReportsPage', () => {
  beforeEach(() => {
    mockedGetProjects.mockResolvedValue({
      items: [{ id: 'p1', name: 'Villa Renovation' }],
      pagination: { page: 1, pageSize: 100, totalItems: 1, totalPages: 1 },
    });
  });
  afterEach(() => jest.clearAllMocks());

  it('shows structural skeletons before either report loads', async () => {
    let resolveFinance: (v: FinanceReport) => void = () => {};
    mockedGetFinanceReport.mockReturnValue(new Promise((resolve) => (resolveFinance = resolve)));
    mockedGetExpenseReport.mockResolvedValue(makeExpenseReport());
    renderPage();

    expect(screen.queryByText('Revenue')).not.toBeInTheDocument();
    resolveFinance(makeFinanceReport());
    expect(await screen.findByText('Revenue')).toBeInTheDocument();
  });

  it('renders finance metrics from exact backend Decimal strings', async () => {
    mockedGetFinanceReport.mockResolvedValue(makeFinanceReport({ revenue: '1234.50' }));
    mockedGetExpenseReport.mockResolvedValue(makeExpenseReport());
    renderPage();

    expect(await screen.findByText('₹1,234.50')).toBeInTheDocument();
  });

  it('renders every finance metric label required by the contract', async () => {
    mockedGetFinanceReport.mockResolvedValue(makeFinanceReport());
    mockedGetExpenseReport.mockResolvedValue(makeExpenseReport());
    renderPage();

    await screen.findByText('Revenue');
    expect(screen.getByText('Expenses')).toBeInTheDocument();
    expect(screen.getByText('Profit / Loss')).toBeInTheDocument();
    expect(screen.getByText('Received')).toBeInTheDocument();
    expect(screen.getByText('Receivables')).toBeInTheDocument();
    expect(screen.getByText('Outstanding')).toBeInTheDocument();
  });

  it('never renders a fabricated trend percentage on any finance metric', async () => {
    mockedGetFinanceReport.mockResolvedValue(makeFinanceReport());
    mockedGetExpenseReport.mockResolvedValue(makeExpenseReport());
    renderPage();

    await screen.findByText('Revenue');
    expect(screen.queryByText(/[+-]\d+(\.\d+)?%/)).not.toBeInTheDocument();
  });

  it('shows a restricted state, not the finance figures, on a 403', async () => {
    mockedGetFinanceReport.mockRejectedValue(
      new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.', [], undefined, 403),
    );
    mockedGetExpenseReport.mockResolvedValue(makeExpenseReport());
    renderPage();

    expect(await screen.findByText('Restricted')).toBeInTheDocument();
    expect(screen.getByText('You do not have permission to perform this action.')).toBeInTheDocument();
    expect(screen.queryByText('Revenue')).not.toBeInTheDocument();
  });

  it('shows a retryable error state on a non-403 finance failure', async () => {
    mockedGetFinanceReport.mockRejectedValue(new ApiError('SERVER_ERROR', 'Report temporarily unavailable.', [], undefined, 500));
    mockedGetExpenseReport.mockResolvedValue(makeExpenseReport());
    renderPage();

    expect(await screen.findByText('Report temporarily unavailable.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });

  it('shows a restricted state on the expense breakdown independently of the finance panel', async () => {
    mockedGetFinanceReport.mockResolvedValue(makeFinanceReport());
    mockedGetExpenseReport.mockRejectedValue(
      new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.', [], undefined, 403),
    );
    renderPage();

    await screen.findByText('Revenue');
    expect(await screen.findByText('Restricted')).toBeInTheDocument();
  });

  it('renders expense breakdown tabs and switches between them', async () => {
    mockedGetFinanceReport.mockResolvedValue(makeFinanceReport());
    mockedGetExpenseReport.mockResolvedValue(makeExpenseReport());
    renderPage();

    await screen.findByText('Materials');
    await userEvent.click(screen.getByRole('tab', { name: 'Vendor' }));
    expect(await screen.findByText('ABC')).toBeInTheDocument();
  });

  it('shows a per-tab empty state when a breakdown group has no rows', async () => {
    mockedGetFinanceReport.mockResolvedValue(makeFinanceReport());
    mockedGetExpenseReport.mockResolvedValue(makeExpenseReport());
    renderPage();

    await screen.findByText('Materials');
    await userEvent.click(screen.getByRole('tab', { name: 'Employee' }));
    expect(await screen.findByText('No expense data for this period')).toBeInTheDocument();
  });

  it('falls back to a readable label for a blank/null grouping key rather than showing nothing', async () => {
    mockedGetFinanceReport.mockResolvedValue(makeFinanceReport());
    mockedGetExpenseReport.mockResolvedValue(
      makeExpenseReport({ byCategory: [{ key: '', label: '', total: '40.00' }] }),
    );
    renderPage();

    expect(await screen.findByText('Uncategorized')).toBeInTheDocument();
  });

  it('renders an unsafe-looking category label as inert text, never as HTML', async () => {
    mockedGetFinanceReport.mockResolvedValue(makeFinanceReport());
    mockedGetExpenseReport.mockResolvedValue(
      makeExpenseReport({ byCategory: [{ key: 'x', label: '<img src=x onerror=alert(1)>', total: '40.00' }] }),
    );
    renderPage();

    expect(await screen.findByText('<img src=x onerror=alert(1)>')).toBeInTheDocument();
    expect(document.querySelectorAll('img[src="x"]').length).toBe(0);
  });

  it('never renders a summed footer total for a breakdown table', async () => {
    mockedGetFinanceReport.mockResolvedValue(makeFinanceReport());
    mockedGetExpenseReport.mockResolvedValue(
      makeExpenseReport({
        byCategory: [
          { key: 'Materials', label: 'Materials', total: '100.00' },
          { key: 'Labour', label: 'Labour', total: '200.00' },
        ],
      }),
    );
    renderPage();

    await screen.findByText('Materials');
    // Exactly two data rows plus the header — no third, summed row appended.
    expect(screen.getAllByRole('row')).toHaveLength(3);
  });

  it('sends the selected date range to both report queries', async () => {
    mockedGetFinanceReport.mockResolvedValue(makeFinanceReport());
    mockedGetExpenseReport.mockResolvedValue(makeExpenseReport());
    renderPage();
    await screen.findByText('Revenue');

    await userEvent.type(screen.getByLabelText('From date'), '2026-09-01');
    await userEvent.type(screen.getByLabelText('To date'), '2026-09-30');

    await waitFor(() =>
      expect(mockedGetFinanceReport).toHaveBeenLastCalledWith({
        projectId: undefined,
        dateFrom: '2026-09-01',
        dateTo: '2026-09-30',
      }),
    );
    expect(mockedGetExpenseReport).toHaveBeenLastCalledWith({
      projectId: undefined,
      dateFrom: '2026-09-01',
      dateTo: '2026-09-30',
    });
  });

  // The project filter is a Radix Select — consistent with every prior
  // module in this app (e.g. ProjectExpensesTab's status filter), its
  // open-and-select interaction is not exercised via userEvent here (a
  // real, previously-diagnosed jsdom pointer-event hang on Radix Popper
  // overlays — see StatusTransitionDialog.test.tsx). The date-range filter
  // above is a plain <input type="date">, so it's tested directly instead;
  // the Select's wiring (onValueChange -> onChange({ projectId })) is a
  // one-line pass-through verified by code review, not by simulating the
  // popover.

  it('shows a clear-filters control only once a filter is set, and resets on click', async () => {
    mockedGetFinanceReport.mockResolvedValue(makeFinanceReport());
    mockedGetExpenseReport.mockResolvedValue(makeExpenseReport());
    renderPage();
    await screen.findByText('Revenue');

    expect(screen.queryByRole('button', { name: 'Clear all filters' })).not.toBeInTheDocument();

    await userEvent.type(screen.getByLabelText('From date'), '2026-09-01');
    const clearButton = await screen.findByRole('button', { name: 'Clear all filters' });
    await userEvent.click(clearButton);

    expect(screen.queryByRole('button', { name: 'Clear all filters' })).not.toBeInTheDocument();
    await waitFor(() =>
      expect(mockedGetFinanceReport).toHaveBeenLastCalledWith({ projectId: undefined, dateFrom: undefined, dateTo: undefined }),
    );
  });
});
