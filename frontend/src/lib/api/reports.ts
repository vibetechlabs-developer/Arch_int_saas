import { apiClient, unwrap } from './client';

// Mirrors backend/apps/reports/serializers.py::FinanceReportSerializer
// exactly (GET /reports/finance). Every field is a Decimal string — never
// parsed into a float for display; render via <Money>.
export interface FinanceReport {
  revenue: string;
  received: string;
  receivables: string;
  outstanding: string;
  expenses: string;
  profitLoss: string;
}

// Mirrors ExpenseReportEntrySerializer — `key`/`label` are null for a
// grouping value the backend itself has none for (e.g. a null employeeId),
// not an error condition.
export interface ExpenseReportEntry {
  key: string | null;
  label: string | null;
  total: string;
}

// Mirrors ExpenseReportSerializer (GET /reports/expenses).
export interface ExpenseReport {
  byCategory: ExpenseReportEntry[];
  byProject: ExpenseReportEntry[];
  byVendor: ExpenseReportEntry[];
  byEmployee: ExpenseReportEntry[];
  byDate: ExpenseReportEntry[];
}

// Shared filter shape for both report endpoints — mirrors
// FinanceReportQuerySerializer exactly (projectId/dateFrom/dateTo only;
// there is no status/client filter on either endpoint).
export interface ReportFilters {
  projectId?: string;
  dateFrom?: string;
  dateTo?: string;
}

export async function getFinanceReport(filters: ReportFilters): Promise<FinanceReport> {
  return unwrap<FinanceReport>(
    apiClient.get('/reports/finance', {
      params: {
        projectId: filters.projectId || undefined,
        dateFrom: filters.dateFrom || undefined,
        dateTo: filters.dateTo || undefined,
      },
    }),
  );
}

export async function getExpenseReport(filters: ReportFilters): Promise<ExpenseReport> {
  return unwrap<ExpenseReport>(
    apiClient.get('/reports/expenses', {
      params: {
        projectId: filters.projectId || undefined,
        dateFrom: filters.dateFrom || undefined,
        dateTo: filters.dateTo || undefined,
      },
    }),
  );
}
