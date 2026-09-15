import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { motion, useReducedMotion } from 'framer-motion';
import { type ColumnDef, type SortingState } from '@tanstack/react-table';
import { MoreHorizontal, Pencil, Plus, Trash2, UserRound, Users } from 'lucide-react';
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
import { deleteLead, getLeads, LEAD_STATUSES, type Lead, type LeadOrdering, type LeadStatus } from '@/lib/api/leads';
import { leadKeys } from '@/lib/queryKeys';
import { formatDate } from '@/lib/format';
import { pageTransition, pageTransitionReduced } from '@/lib/motion';
import { LeadFormSheet } from '@/components/leads/LeadFormSheet';

function sortingToOrdering(sorting: SortingState): LeadOrdering {
  if (sorting.length === 0) return '-created_at';
  const [{ id, desc }] = sorting;
  const field = id === 'createdAt' ? 'created_at' : id;
  return (desc ? `-${field}` : field) as LeadOrdering;
}

export default function LeadsListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const shouldReduceMotion = useReducedMotion();

  const [page, setPage] = useState(0);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<LeadStatus | 'all'>('all');
  const [sorting, setSorting] = useState<SortingState>([{ id: 'createdAt', desc: true }]);
  const [formOpen, setFormOpen] = useState(false);
  const [editingLead, setEditingLead] = useState<Lead | undefined>(undefined);
  const [deletingLead, setDeletingLead] = useState<Lead | null>(null);

  useEffect(() => {
    if (searchParams.get('new') === 'true') {
      setEditingLead(undefined);
      setFormOpen(true);
      const next = new URLSearchParams(searchParams);
      next.delete('new');
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const ordering = sortingToOrdering(sorting);
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: leadKeys.list({ search, ordering, status: statusFilter, page: page + 1 }),
    queryFn: () => getLeads({ search, ordering, status: statusFilter === 'all' ? undefined : statusFilter, page: page + 1 }),
    placeholderData: keepPreviousData,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteLead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      toast.success('Lead deleted');
      setDeletingLead(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete lead.');
      setDeletingLead(null);
    },
  });

  if (isError) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const openCreate = () => {
    setEditingLead(undefined);
    setFormOpen(true);
  };

  const columns: ColumnDef<Lead, unknown>[] = [
    {
      accessorKey: 'name',
      header: 'Name',
      cell: ({ row }) => (
        <div className="flex flex-col">
          <span className="text-body font-medium text-text-primary">{row.original.name}</span>
          {row.original.email && <span className="text-caption text-text-tertiary">{row.original.email}</span>}
        </div>
      ),
    },
    {
      accessorKey: 'companyName',
      header: 'Company',
      enableSorting: false,
      cell: ({ row }) => (
        <span className="text-body text-text-secondary">{row.original.companyName || '—'}</span>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'assignedToName',
      header: 'Assigned to',
      enableSorting: false,
      cell: ({ row }) => (
        <span className="text-body text-text-secondary">{row.original.assignedToName || '—'}</span>
      ),
    },
    {
      accessorKey: 'createdAt',
      header: 'Added',
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
                aria-label="Lead actions"
                onClick={(e) => e.stopPropagation()}
              >
                <MoreHorizontal />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onSelect={() => {
                  setEditingLead(row.original);
                  setFormOpen(true);
                }}
              >
                <Pencil className="size-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem destructive onSelect={() => setDeletingLead(row.original)}>
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
    <motion.div
      variants={shouldReduceMotion ? pageTransitionReduced : pageTransition}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-6"
    >
      <PageHeader
        title="Leads"
        description="Prospects working their way toward becoming a client."
        actions={
          <Button variant="primary" onClick={openCreate}>
            <Plus />
            New Lead
          </Button>
        }
      />

      <div className="flex items-center gap-3">
        <Select
          value={statusFilter}
          onValueChange={(value) => {
            setStatusFilter(value as LeadStatus | 'all');
            setPage(0);
          }}
        >
          <SelectTrigger className="w-48">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            {LEAD_STATUSES.map((status) => (
              <SelectItem key={status} value={status}>
                {status
                  .split('_')
                  .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
                  .join(' ')}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        isLoading={isLoading || isFetching}
        searchPlaceholder="Search by name, company, email, or mobile…"
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
                icon: UserRound,
                title: 'No leads match your search',
                description: 'Try a different name, company, email, or mobile number.',
              }
            : {
                icon: Users,
                title: 'No leads yet',
                description: 'Add your first prospect to start tracking your pipeline.',
                action: { label: 'New Lead', onClick: openCreate },
              }
        }
        onRowClick={(lead) => navigate(`/leads/${lead.id}`)}
      />

      <LeadFormSheet open={formOpen} onOpenChange={setFormOpen} lead={editingLead} />

      <ConfirmationDialog
        open={!!deletingLead}
        onOpenChange={(open) => !open && setDeletingLead(null)}
        title="Delete this lead?"
        description={`This removes "${deletingLead?.name}" from your pipeline.`}
        confirmLabel="Delete lead"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => deletingLead && deleteMutation.mutate(deletingLead.id)}
      />
    </motion.div>
  );
}
