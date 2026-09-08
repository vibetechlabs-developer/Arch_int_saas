import { apiClient, unwrap } from './client';

// Mirrors backend/apps/expenses/models.py::ExpenseApprovalStatus's 4
// documented values. There is no "rejected" or "cancelled" state — the
// workflow is strictly linear (draft → submitted → approved → paid) and
// there is no reject endpoint anywhere.
export type ExpenseApprovalStatus = 'draft' | 'submitted' | 'approved' | 'paid';

// Mirrors ExpenseSerializer. `category`/`vendor`/`paymentMethod` are all
// unconstrained free text — no enum, no category/vendor management
// model exists anywhere in this API.
export interface Expense {
  id: string;
  companyId: string;
  projectId: string;
  projectName: string;
  category: string;
  vendor: string;
  employeeId: string | null;
  employeeName: string | null;
  amount: string;
  tax: string;
  date: string;
  paymentMethod: string;
  receiptUrl: string;
  notes: string;
  addedById: string | null;
  addedByName: string | null;
  approvalStatus: ExpenseApprovalStatus;
  createdAt: string;
  updatedAt: string;
}

export type ExpenseOrdering =
  | 'created_at'
  | '-created_at'
  | 'date'
  | '-date'
  | 'amount'
  | '-amount'
  | 'updated_at'
  | '-updated_at';

export interface ExpenseListParams {
  category?: string;
  vendor?: string;
  employeeId?: string;
  approvalStatus?: ExpenseApprovalStatus;
  dateFrom?: string;
  dateTo?: string;
  ordering?: ExpenseOrdering;
}

export interface ExpenseCreateInput {
  category?: string;
  vendor?: string;
  employeeId?: string | null;
  amount: string;
  tax?: string | null;
  date: string;
  paymentMethod?: string;
  receiptUrl?: string;
  notes?: string;
}

// Every field optional with no non-None default — an omitted field's
// absence (other than employeeId's explicit-null-clears-it contract)
// signals ExpenseService.update_expense to leave it unchanged. Draft
// expenses only (409 otherwise).
export interface ExpenseUpdateInput {
  category?: string | null;
  vendor?: string | null;
  employeeId?: string | null;
  amount?: string | null;
  tax?: string | null;
  date?: string | null;
  paymentMethod?: string | null;
  receiptUrl?: string | null;
  notes?: string | null;
}

export async function getExpenses(projectId: string, params: ExpenseListParams = {}): Promise<Expense[]> {
  return unwrap<Expense[]>(
    apiClient.get(`/projects/${projectId}/expenses`, {
      params: {
        category: params.category || undefined,
        vendor: params.vendor || undefined,
        employee: params.employeeId || undefined,
        approvalStatus: params.approvalStatus || undefined,
        dateFrom: params.dateFrom || undefined,
        dateTo: params.dateTo || undefined,
        ordering: params.ordering,
      },
    }),
  );
}

export async function getExpense(id: string): Promise<Expense> {
  return unwrap<Expense>(apiClient.get(`/expenses/${id}`));
}

export async function createExpense(projectId: string, input: ExpenseCreateInput): Promise<Expense> {
  return unwrap<Expense>(apiClient.post(`/projects/${projectId}/expenses`, input));
}

export async function updateExpense(id: string, input: ExpenseUpdateInput): Promise<Expense> {
  return unwrap<Expense>(apiClient.patch(`/expenses/${id}`, input));
}

export async function deleteExpense(id: string): Promise<void> {
  await apiClient.delete(`/expenses/${id}`);
}

export async function submitExpense(id: string): Promise<Expense> {
  return unwrap<Expense>(apiClient.post(`/expenses/${id}/submit`));
}

export async function approveExpense(id: string): Promise<Expense> {
  return unwrap<Expense>(apiClient.post(`/expenses/${id}/approve`));
}

export async function markExpensePaid(id: string): Promise<Expense> {
  return unwrap<Expense>(apiClient.post(`/expenses/${id}/mark-paid`));
}
