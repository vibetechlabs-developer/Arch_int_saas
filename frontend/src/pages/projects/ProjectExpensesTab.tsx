import { useState } from 'react';
import { useNavigate, useOutletContext } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { type ColumnDef } from '@tanstack/react-table';
import { Plus, Receipt } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DataTable } from '@/components/common/DataTable';
import { ErrorState } from '@/components/common/ErrorState';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Money } from '@/components/common/Money';
import { getExpenses, type Expense } from '@/lib/api/expenses';
import { expenseKeys } from '@/lib/queryKeys';
import { formatDate } from '@/lib/format';
import type { Project } from '@/lib/api/projects';
import { ExpenseFormSheet } from '@/components/expenses/ExpenseFormSheet';
import { ExpenseFilterBar, type ExpenseFilterValues } from '@/components/expenses/ExpenseFilterBar';

const EMPTY_FILTERS: ExpenseFilterValues = { category: '', vendor: '', approvalStatus: '', dateFrom: '', dateTo: '' };

export default function ProjectExpensesTab() {
  const { project } = useOutletContext<{ project: Project }>();
  const navigate = useNavigate();
  const [createOpen, setCreateOpen] = useState(false);
  const [filters, setFilters] = useState<ExpenseFilterValues>(EMPTY_FILTERS);

  const queryParams = {
    category: filters.category || undefined,
    vendor: filters.vendor || undefined,
    approvalStatus: filters.approvalStatus || undefined,
    dateFrom: filters.dateFrom || undefined,
    dateTo: filters.dateTo || undefined,
  };

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: expenseKeys.project(project.id, queryParams),
    queryFn: () => getExpenses(project.id, queryParams),
  });

  if (isError) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const updateFilters = (patch: Partial<ExpenseFilterValues>) => setFilters((prev) => ({ ...prev, ...patch }));
  const hasFilters = !!filters.category || !!filters.vendor || !!filters.approvalStatus || !!filters.dateFrom || !!filters.dateTo;

  const columns: ColumnDef<Expense, unknown>[] = [
    {
      accessorKey: 'category',
      header: 'Category',
      cell: ({ row }) => (
        <span className="text-body font-medium text-text-primary">{row.original.category || 'Uncategorized'}</span>
      ),
    },
    {
      accessorKey: 'vendor',
      header: 'Vendor',
      cell: ({ row }) => <span className="text-body text-text-secondary">{row.original.vendor || '—'}</span>,
    },
    {
      accessorKey: 'date',
      header: 'Date',
      cell: ({ row }) => <span className="text-small text-text-secondary">{formatDate(row.original.date)}</span>,
    },
    {
      accessorKey: 'amount',
      header: () => <span className="block text-right">Amount</span>,
      cell: ({ row }) => (
        <div className="text-right">
          <Money value={row.original.amount} />
        </div>
      ),
    },
    {
      accessorKey: 'approvalStatus',
      header: 'Status',
      cell: ({ row }) => <StatusBadge status={row.original.approvalStatus} />,
    },
    {
      accessorKey: 'addedByName',
      header: 'Added By',
      cell: ({ row }) => <span className="text-small text-text-tertiary">{row.original.addedByName ?? '—'}</span>,
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h3 className="text-h3 text-text-primary">Expenses</h3>
        <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
          <Plus />
          Add Expense
        </Button>
      </div>

      <ExpenseFilterBar value={filters} onChange={updateFilters} onClearAll={() => setFilters(EMPTY_FILTERS)} />

      <DataTable
        columns={columns}
        data={data ?? []}
        isLoading={isLoading}
        hideSearch
        emptyState={
          hasFilters
            ? {
                icon: Receipt,
                title: 'No expenses match these filters',
                description: 'Try a different category, vendor, status, or date range.',
              }
            : {
                icon: Receipt,
                title: 'No expenses recorded yet',
                description: "Record project costs and track their approval status here.",
                action: { label: 'Add Expense', onClick: () => setCreateOpen(true) },
              }
        }
        onRowClick={(expense) => navigate(`/expenses/${expense.id}`)}
      />

      <ExpenseFormSheet open={createOpen} onOpenChange={setCreateOpen} projectId={project.id} />
    </div>
  );
}
