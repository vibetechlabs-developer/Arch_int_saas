import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import DashboardPage from '@/pages/DashboardPage';
import { getDashboard, type DashboardData } from '@/lib/api/dashboard';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/dashboard', () => ({
  ...jest.requireActual('@/lib/api/dashboard'),
  getDashboard: jest.fn(),
}));
jest.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'u1', name: 'Alice Member', email: 'alice@company1.com' } }),
}));

const mockedGetDashboard = getDashboard as jest.Mock;

function makeDashboard(overrides: Partial<DashboardData> = {}): DashboardData {
  return {
    canViewFinancials: true,
    kpis: {
      totalProjects: 3,
      activeProjects: 2,
      totalQuotations: 1,
      totalBilledRevenue: '50000.00',
      totalReceived: '20000.00',
      pendingAmount: '30000.00',
      totalExpenses: '5000.00',
      netProfitLoss: '15000.00',
    },
    recentProjects: [{ id: 'p1', name: 'Kitchen Remodel', status: 'draft', clientName: 'Acme', createdAt: '2026-01-01T00:00:00Z' }],
    recentQuotations: [{ id: 'q1', quoteNumber: 'QT-000001', version: 1, status: 'sent', total: '10000.00', projectName: 'Kitchen Remodel' }],
    pendingPayments: [{ id: 'inv1', invoiceNumber: 'INV-000001', total: '5000.00', dueDate: '2026-12-31', projectName: 'Kitchen Remodel' }],
    overdueInvoices: [],
    recentExpenses: [{ id: 'e1', category: 'Materials', amount: '1200.00', date: '2026-01-05', projectName: 'Kitchen Remodel' }],
    upcomingDeadlines: [{ id: 'p1', name: 'Kitchen Remodel', deadline: '2026-01-20' }],
    recentActivities: [
      {
        id: 'a1', companyId: 'c1', actorUserId: 'u1', actorUserName: 'Alice', entityType: 'project', entityId: 'p1',
        action: 'create', beforeState: null, afterState: null, requestId: null, ipAddress: null, createdAt: '2026-01-01T00:00:00Z',
      },
    ],
    projectProfitability: [{ projectId: 'p1', projectName: 'Kitchen Remodel', revenue: '50000.00', expenses: '5000.00', profit: '15000.00' }],
    ...overrides,
  };
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <DashboardPage />
    </QueryClientProvider>,
  );
}

describe('DashboardPage', () => {
  afterEach(() => jest.clearAllMocks());

  // 1. full financial dashboard renders for allowed response
  it('renders the full financial dashboard when canViewFinancials is true', async () => {
    mockedGetDashboard.mockResolvedValue(makeDashboard());
    renderPage();

    expect(await screen.findByText('Total Billed Revenue')).toBeInTheDocument();
    expect(screen.getByText('Net Profit / Loss')).toBeInTheDocument();
    expect(screen.getByText('Total Expenses')).toBeInTheDocument();
    expect(screen.getByText('Recent Expenses')).toBeInTheDocument();
    expect(screen.getByText('Project Profitability')).toBeInTheDocument();
    expect(screen.getByText('Recent Activity')).toBeInTheDocument();
    expect(screen.getByText('Pending Payments')).toBeInTheDocument();
  });

  // 2. operational-only response renders without crashing
  it('renders an operational-only response without crashing', async () => {
    mockedGetDashboard.mockResolvedValue(
      makeDashboard({
        canViewFinancials: false,
        kpis: { totalProjects: 3, activeProjects: 2, totalQuotations: 1 },
        pendingPayments: undefined,
        overdueInvoices: undefined,
        recentExpenses: undefined,
        projectProfitability: undefined,
        recentActivities: undefined,
      }),
    );
    renderPage();

    expect(await screen.findByText('Total Projects')).toBeInTheDocument();
    expect(screen.getByText('Recent Projects')).toBeInTheDocument();
    expect(screen.getByText('Recent Quotations')).toBeInTheDocument();
    expect(screen.getByText('Upcoming Deadlines')).toBeInTheDocument();
  });

  // 3. financial cards not rendered when unavailable
  it('does not render any financial card/section when canViewFinancials is false', async () => {
    mockedGetDashboard.mockResolvedValue(
      makeDashboard({
        canViewFinancials: false,
        kpis: { totalProjects: 3, activeProjects: 2, totalQuotations: 1 },
        pendingPayments: undefined,
        overdueInvoices: undefined,
        recentExpenses: undefined,
        projectProfitability: undefined,
        recentActivities: undefined,
      }),
    );
    renderPage();

    await screen.findByText('Total Projects');
    expect(screen.queryByText('Total Billed Revenue')).not.toBeInTheDocument();
    expect(screen.queryByText('Net Profit / Loss')).not.toBeInTheDocument();
    expect(screen.queryByText('Total Expenses')).not.toBeInTheDocument();
    expect(screen.queryByText('Pending Payments')).not.toBeInTheDocument();
    expect(screen.queryByText('Overdue Invoices')).not.toBeInTheDocument();
    expect(screen.queryByText('Recent Expenses')).not.toBeInTheDocument();
    expect(screen.queryByText('Project Profitability')).not.toBeInTheDocument();
    expect(screen.queryByText('Recent Activity')).not.toBeInTheDocument();
  });

  // 4. financial sections not replaced with fake zero values
  it('never shows a fake ₹0 in place of an omitted financial figure', async () => {
    mockedGetDashboard.mockResolvedValue(
      makeDashboard({
        canViewFinancials: false,
        kpis: { totalProjects: 3, activeProjects: 2, totalQuotations: 1 },
        pendingPayments: undefined,
        overdueInvoices: undefined,
        recentExpenses: undefined,
        projectProfitability: undefined,
        recentActivities: undefined,
      }),
    );
    renderPage();

    await screen.findByText('Total Projects');
    // The revenue/profit/expenses cards (which would show ₹0.00) must be
    // entirely absent, not present-with-zero.
    expect(screen.queryByText('₹0.00')).not.toBeInTheDocument();
  });

  // 5. loading works
  it('shows loading skeletons before the dashboard resolves', async () => {
    let resolveRequest: (v: DashboardData) => void = () => {};
    mockedGetDashboard.mockReturnValue(new Promise((resolve) => (resolveRequest = resolve)));
    renderPage();

    // Real data isn't rendered yet -- the card shells/headings can exist
    // immediately, but the actual backend-sourced content must not.
    expect(screen.queryByText('Kitchen Remodel')).not.toBeInTheDocument();
    expect(screen.queryByText('₹50,000.00')).not.toBeInTheDocument();
    resolveRequest(makeDashboard());
    expect((await screen.findAllByText('Kitchen Remodel')).length).toBeGreaterThan(0);
  });

  // 6. generic error works
  it('shows the backend error message on a generic failure', async () => {
    mockedGetDashboard.mockRejectedValue(new ApiError('INTERNAL_ERROR', 'Something went wrong.', [], undefined, 500));
    renderPage();

    expect(await screen.findByText('Something went wrong.')).toBeInTheDocument();
  });

  // 7. 403 for entire dashboard remains correctly handled
  it('shows the backend message on a full-dashboard 403', async () => {
    mockedGetDashboard.mockRejectedValue(
      new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.', [], undefined, 403),
    );
    renderPage();

    expect(await screen.findByText('You do not have permission to perform this action.')).toBeInTheDocument();
    expect(screen.queryByText('Recent Projects')).not.toBeInTheDocument();
  });

  // 8. existing dashboard behavior doesn't regress
  it('still renders recent projects and quotations using real backend values, unchanged', async () => {
    mockedGetDashboard.mockResolvedValue(makeDashboard());
    renderPage();

    // "Kitchen Remodel" legitimately appears in both the Recent Projects
    // and Recent Quotations cards (a quotation's own projectName) --
    // assert presence, not a single match.
    expect((await screen.findAllByText('Kitchen Remodel')).length).toBeGreaterThan(0);
    expect(screen.getByText('QT-000001')).toBeInTheDocument();
  });
});
