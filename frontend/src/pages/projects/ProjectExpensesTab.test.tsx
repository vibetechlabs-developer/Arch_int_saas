import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProjectExpensesTab from '@/pages/projects/ProjectExpensesTab';
import { createExpense, getExpenses, type Expense } from '@/lib/api/expenses';
import { searchActiveCompanyMembers } from '@/lib/api/memberships';
import type { Project } from '@/lib/api/projects';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/expenses', () => ({
  ...jest.requireActual('@/lib/api/expenses'),
  getExpenses: jest.fn(),
  createExpense: jest.fn(),
}));
jest.mock('@/lib/api/memberships');
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedGetExpenses = getExpenses as jest.Mock;
const mockedCreate = createExpense as jest.Mock;
const mockedSearchMembers = searchActiveCompanyMembers as jest.Mock;

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

function makeExpense(overrides: Partial<Expense> = {}): Expense {
  return {
    id: 'e1',
    companyId: 'c1',
    projectId: 'p1',
    projectName: 'Villa Renovation',
    category: 'Materials',
    vendor: 'ABC Corp',
    employeeId: null,
    employeeName: null,
    amount: '500.00',
    tax: '0.00',
    date: '2026-09-01',
    paymentMethod: '',
    receiptUrl: '',
    notes: '',
    addedById: 'u1',
    addedByName: 'Alice Member',
    approvalStatus: 'draft',
    createdAt: '2026-09-01T00:00:00Z',
    updatedAt: '2026-09-01T00:00:00Z',
    ...overrides,
  };
}

function renderTab() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/projects/p1/expenses']}>
        <Routes>
          <Route path="/projects/:projectId" element={<Outlet context={{ project }} />}>
            <Route path="expenses" element={<ProjectExpensesTab />} />
          </Route>
          <Route path="/expenses/:expenseId" element={<div>Expense detail page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ProjectExpensesTab', () => {
  beforeEach(() => mockedSearchMembers.mockResolvedValue([]));
  afterEach(() => jest.clearAllMocks());

  it('shows a structural skeleton before expenses load', async () => {
    let resolveRequest: (v: Expense[]) => void = () => {};
    mockedGetExpenses.mockReturnValue(new Promise((resolve) => (resolveRequest = resolve)));
    renderTab();

    expect(screen.queryByText('Materials')).not.toBeInTheDocument();
    resolveRequest([makeExpense()]);
    expect((await screen.findAllByText('Materials')).length).toBeGreaterThan(0);
  });

  it('renders expenses with amount, status, vendor, and added-by (success state)', async () => {
    mockedGetExpenses.mockResolvedValue([makeExpense()]);
    renderTab();

    expect((await screen.findAllByText('Materials')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('ABC Corp').length).toBeGreaterThan(0);
    expect(screen.getAllByText('₹500.00').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Draft').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Alice Member').length).toBeGreaterThan(0);
  });

  it('falls back to "Uncategorized" when category is blank', async () => {
    mockedGetExpenses.mockResolvedValue([makeExpense({ category: '' })]);
    renderTab();

    expect((await screen.findAllByText('Uncategorized')).length).toBeGreaterThan(0);
  });

  it('shows a "no expenses recorded yet" empty state with an Add Expense CTA', async () => {
    mockedGetExpenses.mockResolvedValue([]);
    renderTab();

    expect((await screen.findAllByText('No expenses recorded yet')).length).toBeGreaterThan(0);
  });

  it('shows the backend error message when the list request fails', async () => {
    mockedGetExpenses.mockRejectedValue(new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.'));
    renderTab();

    expect(await screen.findByText('You do not have permission to perform this action.')).toBeInTheDocument();
  });

  it('navigates to the expense detail page on row click', async () => {
    mockedGetExpenses.mockResolvedValue([makeExpense()]);
    renderTab();
    const [firstMatch] = await screen.findAllByText('Materials');

    await userEvent.click(firstMatch);

    expect(await screen.findByText('Expense detail page')).toBeInTheDocument();
  });

  it('refetches with the category filter as a real server-side query param', async () => {
    mockedGetExpenses.mockResolvedValue([]);
    renderTab();
    await screen.findAllByText('No expenses recorded yet');
    mockedGetExpenses.mockClear();

    await userEvent.type(screen.getByLabelText('Category filter'), 'Materials');

    await waitFor(() =>
      expect(mockedGetExpenses).toHaveBeenCalledWith(
        'p1',
        expect.objectContaining({ category: 'Materials' }),
      ),
    );
  });

  // The status filter is a Radix Select — consistent with every prior
  // module in this app, its open-and-select interaction is not exercised
  // via userEvent here (a real, previously-diagnosed jsdom pointer-event
  // hang on Radix Popper overlays). The date-range filter below is a
  // plain <input type="date">, so it's tested directly instead.
  it('refetches with the date-range filter as real server-side query params', async () => {
    mockedGetExpenses.mockResolvedValue([]);
    renderTab();
    await screen.findAllByText('No expenses recorded yet');
    mockedGetExpenses.mockClear();

    await userEvent.type(screen.getByLabelText('From date'), '2026-09-01');
    await userEvent.type(screen.getByLabelText('To date'), '2026-09-30');

    await waitFor(() =>
      expect(mockedGetExpenses).toHaveBeenCalledWith(
        'p1',
        expect.objectContaining({ dateFrom: '2026-09-01', dateTo: '2026-09-30' }),
      ),
    );
  });

  it('creates an expense with the exact payload shape', async () => {
    mockedGetExpenses.mockResolvedValue([]);
    mockedCreate.mockResolvedValue(makeExpense({ id: 'e9' }));
    renderTab();
    await screen.findAllByText('No expenses recorded yet');

    await userEvent.click(screen.getAllByRole('button', { name: /add expense/i })[0]);
    await userEvent.type(screen.getByLabelText('Category'), 'Materials');
    await userEvent.type(screen.getByLabelText('Vendor'), 'ABC Corp');
    await userEvent.type(screen.getByLabelText('Amount'), '500.00');
    await userEvent.type(screen.getByLabelText('Expense date'), '2026-09-01');
    await userEvent.click(screen.getByRole('button', { name: 'Add expense' }));

    await waitFor(() =>
      expect(mockedCreate).toHaveBeenCalledWith('p1', {
        category: 'Materials',
        vendor: 'ABC Corp',
        employeeId: null,
        amount: '500.00',
        tax: '0',
        date: '2026-09-01',
        paymentMethod: '',
        receiptUrl: '',
        notes: '',
      }),
    );
  });

  it('requires an amount and expense date before creating', async () => {
    mockedGetExpenses.mockResolvedValue([]);
    renderTab();
    await screen.findAllByText('No expenses recorded yet');

    await userEvent.click(screen.getAllByRole('button', { name: /add expense/i })[0]);
    await userEvent.click(screen.getByRole('button', { name: 'Add expense' }));

    expect(await screen.findByText('Amount is required')).toBeInTheDocument();
    expect(screen.getByText('Expense date is required')).toBeInTheDocument();
    expect(mockedCreate).not.toHaveBeenCalled();
  });

  it('rejects a zero amount', async () => {
    mockedGetExpenses.mockResolvedValue([]);
    renderTab();
    await screen.findAllByText('No expenses recorded yet');

    await userEvent.click(screen.getAllByRole('button', { name: /add expense/i })[0]);
    await userEvent.type(screen.getByLabelText('Amount'), '0.00');
    await userEvent.type(screen.getByLabelText('Expense date'), '2026-09-01');
    await userEvent.click(screen.getByRole('button', { name: 'Add expense' }));

    expect(await screen.findByText('Amount must be greater than zero')).toBeInTheDocument();
    expect(mockedCreate).not.toHaveBeenCalled();
  });

  it('surfaces a backend field error on create', async () => {
    mockedGetExpenses.mockResolvedValue([]);
    mockedCreate.mockRejectedValue(new ApiError('VALIDATION_ERROR', 'date is required.'));
    renderTab();
    await screen.findAllByText('No expenses recorded yet');

    await userEvent.click(screen.getAllByRole('button', { name: /add expense/i })[0]);
    await userEvent.type(screen.getByLabelText('Amount'), '500.00');
    await userEvent.type(screen.getByLabelText('Expense date'), '2026-09-01');
    await userEvent.click(screen.getByRole('button', { name: 'Add expense' }));

    expect(await screen.findByText('date is required.')).toBeInTheDocument();
  });

  it('disables the submit button while the create mutation is pending, preventing duplicate submission', async () => {
    mockedGetExpenses.mockResolvedValue([]);
    let resolveCreate: (v: Expense) => void = () => {};
    mockedCreate.mockReturnValue(new Promise((resolve) => (resolveCreate = resolve)));
    renderTab();
    await screen.findAllByText('No expenses recorded yet');

    await userEvent.click(screen.getAllByRole('button', { name: /add expense/i })[0]);
    await userEvent.type(screen.getByLabelText('Amount'), '500.00');
    await userEvent.type(screen.getByLabelText('Expense date'), '2026-09-01');
    const submitButton = screen.getByRole('button', { name: 'Add expense' });
    await userEvent.click(submitButton);

    await waitFor(() => expect(submitButton).toBeDisabled());
    resolveCreate(makeExpense());
  });

  it('shows a distinct mobile card representation for expense rows alongside the desktop table', async () => {
    mockedGetExpenses.mockResolvedValue([makeExpense()]);
    renderTab();
    await screen.findAllByText('Materials');

    const mobileContainer = document.querySelector('.md\\:hidden');
    expect(mobileContainer).not.toBeNull();
    const mobileScope = within(mobileContainer as HTMLElement);
    expect(mobileScope.getByText('Materials')).toBeInTheDocument();
  });
});
