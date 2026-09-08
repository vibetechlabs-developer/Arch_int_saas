import { useState } from 'react';
import { useNavigate, useOutletContext } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { type ColumnDef } from '@tanstack/react-table';
import { FileText, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { DataTable } from '@/components/common/DataTable';
import { ErrorState } from '@/components/common/ErrorState';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Money } from '@/components/common/Money';
import { getQuotations, type Quotation } from '@/lib/api/quotations';
import { quotationKeys } from '@/lib/queryKeys';
import { formatDate } from '@/lib/format';
import type { Project } from '@/lib/api/projects';
import { CreateQuotationSheet } from '@/components/quotations/CreateQuotationSheet';

// GET /projects/{id}/quotations returns every version of every quotation
// (no "latest only" filter on the backend). The list here shows one row
// per quote number — the latest version — since that's what matters for
// a "which quotations exist" overview; older versions are reachable from
// that row's detail page via its own version-lineage navigation.
function latestVersionPerQuoteNumber(quotations: Quotation[]): Quotation[] {
  const byNumber = new Map<string, Quotation>();
  for (const quotation of quotations) {
    const existing = byNumber.get(quotation.quoteNumber);
    if (!existing || quotation.version > existing.version) {
      byNumber.set(quotation.quoteNumber, quotation);
    }
  }
  return Array.from(byNumber.values());
}

export default function ProjectQuotationsTab() {
  const { project } = useOutletContext<{ project: Project }>();
  const navigate = useNavigate();
  const [createOpen, setCreateOpen] = useState(false);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: quotationKeys.project(project.id),
    queryFn: () => getQuotations(project.id),
  });

  if (isError) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const rows = latestVersionPerQuoteNumber(data ?? []);

  const columns: ColumnDef<Quotation, unknown>[] = [
    {
      accessorKey: 'quoteNumber',
      header: 'Quote Number',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <span className="text-body font-medium text-text-primary">{row.original.quoteNumber}</span>
          {row.original.version > 1 && <Badge variant="neutral">v{row.original.version}</Badge>}
        </div>
      ),
    },
    {
      accessorKey: 'clientName',
      header: 'Client',
      enableSorting: false,
      cell: ({ row }) => <span className="text-body text-text-secondary">{row.original.clientName}</span>,
    },
    {
      accessorKey: 'status',
      header: 'Status',
      enableSorting: false,
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'total',
      header: () => <span className="block text-right">Total</span>,
      cell: ({ row }) => (
        <div className="text-right">
          <Money value={row.original.total} />
        </div>
      ),
    },
    {
      accessorKey: 'validUntil',
      header: 'Valid Until',
      cell: ({ row }) => (
        <span className="text-small text-text-secondary">
          {row.original.validUntil ? formatDate(row.original.validUntil) : '—'}
        </span>
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
        <h3 className="text-h3 text-text-primary">Quotations</h3>
        <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
          <Plus />
          New Quotation
        </Button>
      </div>

      <DataTable
        columns={columns}
        data={rows}
        isLoading={isLoading}
        hideSearch
        emptyState={{
          icon: FileText,
          title: 'No quotations yet',
          description: "Create a quotation from this project's BOQ to send it to the client.",
          action: { label: 'New Quotation', onClick: () => setCreateOpen(true) },
        }}
        onRowClick={(quotation) => navigate(`/quotations/${quotation.id}`)}
      />

      <CreateQuotationSheet open={createOpen} onOpenChange={setCreateOpen} projectId={project.id} />
    </div>
  );
}
