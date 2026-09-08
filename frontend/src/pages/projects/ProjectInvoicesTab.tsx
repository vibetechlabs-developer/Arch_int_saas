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
import { getInvoices, type Invoice } from '@/lib/api/invoices';
import { invoiceKeys } from '@/lib/queryKeys';
import { formatDate } from '@/lib/format';
import type { Project } from '@/lib/api/projects';
import { CreateInvoiceSheet } from '@/components/invoices/CreateInvoiceSheet';

export default function ProjectInvoicesTab() {
  const { project } = useOutletContext<{ project: Project }>();
  const navigate = useNavigate();
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: invoiceKeys.project(project.id),
    queryFn: () => getInvoices(project.id),
  });

  if (isError) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const columns: ColumnDef<Invoice, unknown>[] = [
    {
      accessorKey: 'invoiceNumber',
      header: 'Invoice #',
      cell: ({ row }) => <span className="text-body font-medium text-text-primary">{row.original.invoiceNumber}</span>,
    },
    {
      accessorKey: 'status',
      header: 'Status',
      enableSorting: false,
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'dueDate',
      header: 'Due Date',
      cell: ({ row }) => (
        <span className="text-small text-text-secondary">{row.original.dueDate ? formatDate(row.original.dueDate) : '—'}</span>
      ),
    },
    {
      accessorKey: 'total',
      header: () => <span className="block text-right">Grand Total</span>,
      cell: ({ row }) => (
        <div className="text-right">
          <Money value={row.original.total} />
        </div>
      ),
    },
    {
      accessorKey: 'createdAt',
      header: 'Created',
      cell: ({ row }) => <span className="text-small text-text-tertiary">{formatDate(row.original.createdAt)}</span>,
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h3 className="text-h3 text-text-primary">Invoices</h3>
        <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
          <Plus />
          Create Invoice
        </Button>
      </div>

      <DataTable
        columns={columns}
        data={data ?? []}
        isLoading={isLoading}
        hideSearch
        emptyState={{
          icon: Receipt,
          title: 'No invoices yet',
          description: "Create an invoice when this project's commercial work is ready for billing.",
          action: { label: 'Create Invoice', onClick: () => setCreateOpen(true) },
        }}
        onRowClick={(invoice) => navigate(`/invoices/${invoice.id}`)}
      />

      <CreateInvoiceSheet open={createOpen} onOpenChange={setCreateOpen} projectId={project.id} />
    </div>
  );
}
