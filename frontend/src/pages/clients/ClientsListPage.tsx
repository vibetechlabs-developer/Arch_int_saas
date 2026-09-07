import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { motion, useReducedMotion } from 'framer-motion';
import { type ColumnDef, type SortingState } from '@tanstack/react-table';
import { Building2, MoreHorizontal, Pencil, Plus, Trash2, UserRound } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { DataTable } from '@/components/common/DataTable';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ApiError } from '@/lib/api/client';
import { deleteClient, getClients, type Client, type ClientOrdering } from '@/lib/api/clients';
import { clientKeys } from '@/lib/queryKeys';
import { formatDate } from '@/lib/format';
import { pageTransition, pageTransitionReduced } from '@/lib/motion';
import { ClientFormSheet } from '@/components/clients/ClientFormSheet';

function sortingToOrdering(sorting: SortingState): ClientOrdering {
  if (sorting.length === 0) return '-created_at';
  const [{ id, desc }] = sorting;
  const field = id === 'createdAt' ? 'created_at' : id;
  return (desc ? `-${field}` : field) as ClientOrdering;
}

export default function ClientsListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const shouldReduceMotion = useReducedMotion();

  const [page, setPage] = useState(0);
  const [search, setSearch] = useState('');
  const [sorting, setSorting] = useState<SortingState>([{ id: 'createdAt', desc: true }]);
  const [formOpen, setFormOpen] = useState(false);
  const [editingClient, setEditingClient] = useState<Client | undefined>(undefined);
  const [deletingClient, setDeletingClient] = useState<Client | null>(null);

  useEffect(() => {
    if (searchParams.get('new') === 'true') {
      setEditingClient(undefined);
      setFormOpen(true);
      const next = new URLSearchParams(searchParams);
      next.delete('new');
      setSearchParams(next, { replace: true });
    }
    // Only ever reacts to the URL flag on the params that were present at mount/navigation.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const ordering = sortingToOrdering(sorting);
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: clientKeys.list({ search, ordering, page: page + 1 }),
    queryFn: () => getClients({ search, ordering, page: page + 1 }),
    placeholderData: keepPreviousData,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteClient(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: clientKeys.lists() });
      toast.success('Client deleted');
      setDeletingClient(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete client.');
      setDeletingClient(null);
    },
  });

  if (isError) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const openCreate = () => {
    setEditingClient(undefined);
    setFormOpen(true);
  };

  const columns: ColumnDef<Client, unknown>[] = [
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
      accessorKey: 'mobile',
      header: 'Mobile',
      enableSorting: false,
      cell: ({ row }) => <span className="text-body text-text-secondary">{row.original.mobile || '—'}</span>,
    },
    {
      accessorKey: 'gstin',
      header: 'GSTIN',
      enableSorting: false,
      cell: ({ row }) => (
        <span className="text-small tabular-nums text-text-secondary">{row.original.gstin || '—'}</span>
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
                aria-label="Client actions"
                onClick={(e) => e.stopPropagation()}
              >
                <MoreHorizontal />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onSelect={() => {
                  setEditingClient(row.original);
                  setFormOpen(true);
                }}
              >
                <Pencil className="size-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem destructive onSelect={() => setDeletingClient(row.original)}>
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
        title="Clients"
        description="The people and businesses you deliver projects for."
        actions={
          <Button variant="primary" onClick={openCreate}>
            <Plus />
            New Client
          </Button>
        }
      />

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
                title: 'No clients match your search',
                description: 'Try a different name, company, email, or mobile number.',
              }
            : {
                icon: Building2,
                title: 'No clients yet',
                description: 'Add your first client to begin creating projects for them.',
                action: { label: 'New Client', onClick: openCreate },
              }
        }
        onRowClick={(client) => navigate(`/clients/${client.id}`)}
      />

      <ClientFormSheet open={formOpen} onOpenChange={setFormOpen} client={editingClient} />

      <ConfirmationDialog
        open={!!deletingClient}
        onOpenChange={(open) => !open && setDeletingClient(null)}
        title="Delete this client?"
        description={`This removes "${deletingClient?.name}" from your client list. Projects already linked to them are not affected.`}
        confirmLabel="Delete client"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => deletingClient && deleteMutation.mutate(deletingClient.id)}
      />
    </motion.div>
  );
}
