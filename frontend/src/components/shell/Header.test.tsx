import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Header } from '@/components/shell/Header';
import { quotationKeys, invoiceKeys, expenseKeys } from '@/lib/queryKeys';
import type { Quotation } from '@/lib/api/quotations';
import type { Invoice } from '@/lib/api/invoices';
import type { Expense } from '@/lib/api/expenses';

jest.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'u1', name: 'Alice Member', email: 'alice@company1.com' }, logout: jest.fn() }),
}));
jest.mock('@/theme/ThemeProvider', () => ({ useTheme: () => ({ isDark: false, toggleTheme: jest.fn() }) }));

const noop = jest.fn();

function renderHeader(route: string, path: string, seed?: (queryClient: QueryClient) => void) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  seed?.(queryClient);
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route
            path={path}
            element={<Header onOpenCommandPalette={noop} onOpenNotifications={noop} onOpenMobileNav={noop} />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const quotation: Quotation = {
  id: 'q1',
  companyId: 'c1',
  projectId: 'p1',
  projectName: 'Villa Renovation',
  boqId: null,
  clientId: 'cl1',
  clientName: 'Acme Interiors',
  quoteNumber: 'QT-0001',
  version: 1,
  subtotal: '0.00',
  discount: '0.00',
  tax: '0.00',
  total: '0.00',
  terms: '',
  paymentSchedule: [],
  validUntil: null,
  status: 'draft',
  notes: '',
  items: [],
  createdAt: '',
  updatedAt: '',
};

const invoice: Invoice = {
  id: 'i1',
  companyId: 'c1',
  projectId: 'p1',
  projectName: 'Villa Renovation',
  quotationId: null,
  clientId: 'cl1',
  clientName: 'Acme Interiors',
  invoiceNumber: 'INV-0001',
  subtotal: '0.00',
  discount: '0.00',
  tax: '0.00',
  total: '0.00',
  dueDate: null,
  paymentTerms: '',
  status: 'draft',
  paidAmount: '0.00',
  outstandingAmount: '0.00',
  notes: '',
  items: [],
  createdAt: '',
  updatedAt: '',
};

const expense: Expense = {
  id: 'e1',
  companyId: 'c1',
  projectId: 'p1',
  projectName: 'Villa Renovation',
  category: 'Materials',
  vendor: '',
  employeeId: null,
  employeeName: null,
  amount: '0.00',
  tax: '0.00',
  date: '2026-09-01',
  paymentMethod: '',
  receiptUrl: '',
  hasStoredReceipt: false,
  notes: '',
  addedById: null,
  addedByName: null,
  approvalStatus: 'draft',
  createdAt: '',
  updatedAt: '',
};

describe('Header breadcrumbs', () => {
  it('shows the full Projects / <Project> / Quotations / <Number> chain for a quotation detail route', () => {
    renderHeader('/quotations/q1', '/quotations/:quotationId', (qc) =>
      qc.setQueryData(quotationKeys.detail('q1'), quotation),
    );

    expect(screen.getByText('Projects')).toBeInTheDocument();
    expect(screen.getByText('Villa Renovation')).toBeInTheDocument();
    expect(screen.getByText('Quotations')).toBeInTheDocument();
    expect(screen.getByText('QT-0001')).toBeInTheDocument();
  });

  it('shows the full Projects / <Project> / Invoices / <Number> chain for an invoice detail route', () => {
    renderHeader('/invoices/i1', '/invoices/:invoiceId', (qc) => qc.setQueryData(invoiceKeys.detail('i1'), invoice));

    expect(screen.getByText('Villa Renovation')).toBeInTheDocument();
    expect(screen.getByText('Invoices')).toBeInTheDocument();
    expect(screen.getByText('INV-0001')).toBeInTheDocument();
  });

  it('shows the full Projects / <Project> / Expenses / <Category> chain for an expense detail route', () => {
    renderHeader('/expenses/e1', '/expenses/:expenseId', (qc) => qc.setQueryData(expenseKeys.detail('e1'), expense));

    expect(screen.getByText('Villa Renovation')).toBeInTheDocument();
    expect(screen.getByText('Expenses')).toBeInTheDocument();
    expect(screen.getByText('Materials')).toBeInTheDocument();
  });

  it('falls back to the bare module name — never a raw UUID — before the detail record has loaded into cache', () => {
    renderHeader('/quotations/q1', '/quotations/:quotationId');

    expect(screen.getByText('Quotations')).toBeInTheDocument();
    expect(screen.queryByText('q1')).not.toBeInTheDocument();
    expect(screen.queryByText('Projects')).not.toBeInTheDocument();
  });
});
