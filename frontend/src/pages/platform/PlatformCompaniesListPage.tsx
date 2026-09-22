import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { type ColumnDef, type SortingState } from '@tanstack/react-table';
import { Building2, MoreHorizontal, Pencil, Plus, Trash2 } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { DataTable } from '@/components/common/DataTable';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ApiError } from '@/lib/api/client';
import { deleteCompany, getCompanies, type Company, type CompanyOrdering, type CompanyStatus } from '@/lib/api/company';
import { platformCompanyKeys } from '@/lib/queryKeys';
import { formatDate } from '@/lib/format';
import { CompanyFormSheet } from '@/components/platform/CompanyFormSheet';

function sortingToOrdering(sorting: SortingState): CompanyOrdering {
  if (sorting.length === 0) return '-created_at';
  const [{ id, desc }] = sorting;
  const field = id === 'createdAt' ? 'created_at' : id;
  return (desc ? `-${field}` : field) as CompanyOrdering;
}

export default function PlatformCompaniesListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(0);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<CompanyStatus | 'all'>('all');
  const [sorting, setSorting] = useState<SortingState>([{ id: 'createdAt', desc: true }]);
  const [formOpen, setFormOpen] = useState(false);
  const [editingCompany, setEditingCompany] = useState<Company | undefined>(undefined);
  const [deletingCompany, setDeletingCompany] = useState<Company | null>(null);

  const ordering = sortingToOrdering(sorting);
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: platformCompanyKeys.list({ search, ordering, status: statusFilter, page: page + 1 }),
    queryFn: () =>
      getCompanies({ search, ordering, status: statusFilter === 'all' ? undefined : statusFilter, page: page + 1 }),
    placeholderData: keepPreviousData,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteCompany(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: platformCompanyKeys.lists() });
      toast.success('Company deleted');
      setDeletingCompany(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete company.');
      setDeletingCompany(null);
    },
  });

  if (isError) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const openCreate = () => {
    setEditingCompany(undefined);
    setFormOpen(true);
  };

  const columns: ColumnDef<Company, unknown>[] = [
    {
      accessorKey: 'name',
      header: 'Company',
      cell: ({ row }) => <span className="text-body font-medium text-text-primary">{row.original.name}</span>,
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'currency',
      header: 'Currency',
      enableSorting: false,
      cell: ({ row }) => <span className="text-body text-text-secondary">{row.original.currency}</span>,
    },
    {
      accessorKey: 'gstNumber',
      header: 'GSTIN',
      enableSorting: false,
      cell: ({ row }) => (
        <span className="text-small tabular-nums text-text-secondary">{row.original.gstNumber || '—'}</span>
      ),
    },
    {
      accessorKey: 'createdAt',
      header: 'Created',
      cell: ({ row }) => (
        <span className="text-small text-text-tertiary">{formatDate(row.original.createdAt)}</span>
      ),
    },
    {
      id: 'actions',
      header: '',
      enableSorting: false,
      enableHiding: false,
      cell: ({ row }) => (
        <div className="flex justify-end">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Company actions"
                onClick={(e) => e.stopPropagation()}
              >
                <MoreHorizontal />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onSelect={() => {
                  setEditingCompany(row.original);
                  setFormOpen(true);
                }}
              >
                <Pencil className="size-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem destructive onSelect={() => setDeletingCompany(row.original)}>
                <Trash2 className="size-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Companies"
        description="Every tenant workspace on this platform."
        actions={
          <Button variant="primary" onClick={openCreate}>
            <Plus />
            New Company
          </Button>
        }
      />

      <div className="flex items-center gap-3">
        <Select
          value={statusFilter}
          onValueChange={(value) => {
            setStatusFilter(value as CompanyStatus | 'all');
            setPage(0);
          }}
        >
          <SelectTrigger className="w-44">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="trial">Trial</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="suspended">Suspended</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        isLoading={isLoading || isFetching}
        searchPlaceholder="Search companies by name…"
        manual
        searchValue={search}
        onSearchChange={(value) => {
          setSearch(value);
          setPage(0);
        }}
        pageIndex={page}
        pageCount={data?.pagination.totalPages ?? 1}
        totalItems={data?.pagination.totalItems}
        onPageChange={setPage}
        sorting={sorting}
        onSortingChange={setSorting}
        emptyState={
          search
            ? {
                icon: Building2,
                title: 'No companies match your search',
                description: 'Try a different name.',
              }
            : {
                icon: Building2,
                title: 'No companies yet',
                description: 'Create the first tenant workspace on this platform.',
                action: { label: 'New Company', onClick: openCreate },
              }
        }
        onRowClick={(company) => navigate(`/platform/companies/${company.id}`)}
      />

      <CompanyFormSheet open={formOpen} onOpenChange={setFormOpen} company={editingCompany} />

      <ConfirmationDialog
        open={!!deletingCompany}
        onOpenChange={(open) => !open && setDeletingCompany(null)}
        title="Delete this company?"
        description={`This soft-deletes "${deletingCompany?.name}" and everything scoped to it. It can be restored directly in the database if needed, but there's no undo in this console.`}
        confirmLabel="Delete company"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => deletingCompany && deleteMutation.mutate(deletingCompany.id)}
      />
    </div>
  );
}
