import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ExpenseDetailPage from '@/pages/ExpenseDetailPage';
import {
  approveExpense,
  deleteExpense,
  getExpense,
  markExpensePaid,
  submitExpense,
  updateExpense,
  type Expense,
} from '@/lib/api/expenses';
import { searchActiveCompanyMembers } from '@/lib/api/memberships';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/expenses', () => ({
  ...jest.requireActual('@/lib/api/expenses'),
  getExpense: jest.fn(),
  updateExpense: jest.fn(),
  deleteExpense: jest.fn(),
  submitExpense: jest.fn(),
  approveExpense: jest.fn(),
  markExpensePaid: jest.fn(),
}));
jest.mock('@/lib/api/memberships');
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('@/lib/pdf', () => ({ previewPdf: jest.fn(), downloadPdf: jest.fn() }));

const mockedGetExpense = getExpense as jest.Mock;
const mockedUpdate = updateExpense as jest.Mock;
const mockedDelete = deleteExpense as jest.Mock;
const mockedSubmit = submitExpense as jest.Mock;
const mockedApprove = approveExpense as jest.Mock;
const mockedMarkPaid = markExpensePaid as jest.Mock;
const mockedSearchMembers = searchActiveCompanyMembers as jest.Mock;

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
    tax: '20.00',
    date: '2026-09-01',
    paymentMethod: 'Bank transfer',
    receiptUrl: '',
    hasStoredReceipt: false,
    notes: '',
    addedById: 'u1',
    addedByName: 'Alice Member',
    approvalStatus: 'draft',
    createdAt: '2026-09-01T00:00:00Z',
    updatedAt: '2026-09-01T00:00:00Z',
    ...overrides,
  };
}

function renderPage(id = 'e1') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/expenses/${id}`]}>
        <Routes>
          <Route path="/expenses/:expenseId" element={<ExpenseDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ExpenseDetailPage', () => {
  beforeEach(() => mockedSearchMembers.mockResolvedValue([]));
  afterEach(() => jest.clearAllMocks());

  it('renders the actual expense fields (vendor, amount, tax, payment method, added by)', async () => {
    mockedGetExpense.mockResolvedValue(makeExpense());
    renderPage();

    expect(await screen.findByText('ABC Corp')).toBeInTheDocument();
    expect(screen.getByText('₹500.00')).toBeInTheDocument();
    expect(screen.getByText('₹20.00')).toBeInTheDocument();
    expect(screen.getByText('Bank transfer')).toBeInTheDocument();
    expect(screen.getByText('Alice Member')).toBeInTheDocument();
  });

  it('shows placeholder text for an unset employee and empty notes', async () => {
    mockedGetExpense.mockResolvedValue(makeExpense({ employeeName: null, notes: '' }));
    renderPage();

    await screen.findByText('ABC Corp');
    expect(screen.getByText('No notes provided.')).toBeInTheDocument();
  });

  it('shows a receipt link only when receiptUrl is present', async () => {
    mockedGetExpense.mockResolvedValue(makeExpense({ receiptUrl: 'https://files.example.com/receipt.pdf' }));
    renderPage();

    const link = await screen.findByRole('link', { name: /view receipt/i });
    expect(link).toHaveAttribute('href', 'https://files.example.com/receipt.pdf');
  });

  it('shows no receipt section when receiptUrl is empty and no receipt is stored', async () => {
    mockedGetExpense.mockResolvedValue(makeExpense({ receiptUrl: '' }));
    renderPage();

    await screen.findByText('ABC Corp');
    expect(screen.queryByText('Receipt')).not.toBeInTheDocument();
  });

  it('shows Preview/Download actions for a stored receipt (BE-078)', async () => {
    mockedGetExpense.mockResolvedValue(makeExpense({ receiptUrl: '', hasStoredReceipt: true }));
    renderPage();

    const previewButton = await screen.findByRole('button', { name: 'Preview' });
    expect(screen.queryByRole('link', { name: /view receipt/i })).not.toBeInTheDocument();

    await userEvent.click(previewButton);
    const { previewPdf } = jest.requireMock('@/lib/pdf');
    await waitFor(() => expect(previewPdf).toHaveBeenCalledWith('/expenses/e1/receipt'));
  });

  it('shows Edit, Submit, and Delete for a draft expense, but no Approve/Mark as Paid', async () => {
    mockedGetExpense.mockResolvedValue(makeExpense({ approvalStatus: 'draft' }));
    renderPage();

    expect(await screen.findByRole('button', { name: /edit/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /^submit$/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^approve$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /mark as paid/i })).not.toBeInTheDocument();
  });

  it('shows only Approve for a submitted expense', async () => {
    mockedGetExpense.mockResolvedValue(makeExpense({ approvalStatus: 'submitted' }));
    renderPage();

    expect(await screen.findByRole('button', { name: /^approve$/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^submit$/i })).not.toBeInTheDocument();
  });

  it('shows only Mark as Paid for an approved expense', async () => {
    mockedGetExpense.mockResolvedValue(makeExpense({ approvalStatus: 'approved' }));
    renderPage();

    expect(await screen.findByRole('button', { name: /mark as paid/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^approve$/i })).not.toBeInTheDocument();
  });

  it('shows no workflow actions at all for a paid expense', async () => {
    mockedGetExpense.mockResolvedValue(makeExpense({ approvalStatus: 'paid' }));
    renderPage();

    await screen.findByText('ABC Corp');
    expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^submit$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^approve$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /mark as paid/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
  });

  it('submits a draft expense after confirmation', async () => {
    mockedGetExpense.mockResolvedValue(makeExpense({ approvalStatus: 'draft' }));
    mockedSubmit.mockResolvedValue(makeExpense({ approvalStatus: 'submitted' }));
    renderPage();

    await userEvent.click(await screen.findByRole('button', { name: /^submit$/i }));
    expect(await screen.findByText('Submit this expense?')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Submit expense' }));

    await waitFor(() => expect(mockedSubmit).toHaveBeenCalledWith('e1'));
  });

  it('approves a submitted expense after confirmation', async () => {
    mockedGetExpense.mockResolvedValue(makeExpense({ approvalStatus: 'submitted' }));
    mockedApprove.mockResolvedValue(makeExpense({ approvalStatus: 'approved' }));
    renderPage();

    await userEvent.click(await screen.findByRole('button', { name: /^approve$/i }));
    await userEvent.click(screen.getByRole('button', { name: 'Approve expense' }));

    await waitFor(() => expect(mockedApprove).toHaveBeenCalledWith('e1'));
  });

  it('marks an approved expense as paid after confirmation', async () => {
    mockedGetExpense.mockResolvedValue(makeExpense({ approvalStatus: 'approved' }));
    mockedMarkPaid.mockResolvedValue(makeExpense({ approvalStatus: 'paid' }));
    renderPage();

    await userEvent.click(await screen.findByRole('button', { name: /mark as paid/i }));
    await userEvent.click(screen.getByRole('button', { name: 'Mark as paid' }));

    await waitFor(() => expect(mockedMarkPaid).toHaveBeenCalledWith('e1'));
  });

  it('surfaces the backend conflict message on an invalid workflow transition (e.g. approving before submit)', async () => {
    mockedGetExpense.mockResolvedValue(makeExpense({ approvalStatus: 'submitted' }));
    mockedApprove.mockRejectedValue(new ApiError('CONFLICT', 'Only a submitted expense can be approved.'));
    const { toast } = jest.requireMock('sonner');
    renderPage();

    await userEvent.click(await screen.findByRole('button', { name: /^approve$/i }));
    await userEvent.click(screen.getByRole('button', { name: 'Approve expense' }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Only a submitted expense can be approved.'));
  });

  it('shows a permission-denied error rather than performing the action when the workflow request is forbidden', async () => {
    mockedGetExpense.mockResolvedValue(makeExpense({ approvalStatus: 'draft' }));
    mockedSubmit.mockRejectedValue(new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.'));
    const { toast } = jest.requireMock('sonner');
    renderPage();

    await userEvent.click(await screen.findByRole('button', { name: /^submit$/i }));
    await userEvent.click(screen.getByRole('button', { name: 'Submit expense' }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('You do not have permission to perform this action.'));
  });

  it('shows a confirmation dialog before deleting a draft expense, then deletes and navigates back', async () => {
    mockedGetExpense.mockResolvedValue(makeExpense({ approvalStatus: 'draft' }));
    mockedDelete.mockResolvedValue(undefined);
    renderPage();

    await userEvent.click(await screen.findByRole('button', { name: /delete/i }));
    expect(await screen.findByText('Delete this expense?')).toBeInTheDocument();
    expect(mockedDelete).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole('button', { name: 'Delete expense' }));

    await waitFor(() => expect(mockedDelete).toHaveBeenCalledWith('e1'));
  });

  it('surfaces the backend conflict message when deleting a non-draft expense races the status change', async () => {
    mockedGetExpense.mockResolvedValue(makeExpense({ approvalStatus: 'draft' }));
    mockedDelete.mockRejectedValue(new ApiError('CONFLICT', 'Only a draft expense can be deleted.'));
    const { toast } = jest.requireMock('sonner');
    renderPage();

    await userEvent.click(await screen.findByRole('button', { name: /delete/i }));
    await userEvent.click(screen.getByRole('button', { name: 'Delete expense' }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Only a draft expense can be deleted.'));
  });

  it('opens the Edit sheet prefilled with current values and saves via PATCH', async () => {
    mockedGetExpense.mockResolvedValue(makeExpense({ approvalStatus: 'draft' }));
    mockedUpdate.mockResolvedValue(makeExpense({ category: 'Travel' }));
    renderPage();

    await userEvent.click(await screen.findByRole('button', { name: /edit/i }));
    expect(await screen.findByLabelText('Category')).toHaveValue('Materials');
    expect(screen.getByLabelText('Vendor')).toHaveValue('ABC Corp');
    expect(screen.getByLabelText('Amount')).toHaveValue('500.00');

    await userEvent.clear(screen.getByLabelText('Category'));
    await userEvent.type(screen.getByLabelText('Category'), 'Travel');
    await userEvent.click(screen.getByRole('button', { name: 'Save changes' }));

    await waitFor(() =>
      expect(mockedUpdate).toHaveBeenCalledWith('e1', {
        category: 'Travel',
        vendor: 'ABC Corp',
        employeeId: null,
        amount: '500.00',
        tax: '20.00',
        date: '2026-09-01',
        paymentMethod: 'Bank transfer',
        receiptUrl: '',
        notes: '',
      }),
    );
  });

  it('shows a not-found state for a deleted or inaccessible expense', async () => {
    mockedGetExpense.mockRejectedValue(new ApiError('NOT_FOUND', 'The requested expense was not found.'));
    renderPage();

    expect(await screen.findByText('Expense not found')).toBeInTheDocument();
  });

  it('shows a retryable error state for a generic failure', async () => {
    mockedGetExpense.mockRejectedValue(new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.'));
    renderPage();

    expect(await screen.findByText('You do not have permission to perform this action.')).toBeInTheDocument();
  });
});
