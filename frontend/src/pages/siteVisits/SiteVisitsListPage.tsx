import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { motion, useReducedMotion } from 'framer-motion';
import { type ColumnDef, type SortingState } from '@tanstack/react-table';
import { CalendarCheck, MoreHorizontal, Pencil, Trash2 } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { DataTable } from '@/components/common/DataTable';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ApiError } from '@/lib/api/client';
import { deleteSiteVisit, getSiteVisits, type SiteVisit, type SiteVisitOrdering } from '@/lib/api/siteVisits';
import { siteVisitKeys } from '@/lib/queryKeys';
import { formatDateTime } from '@/lib/format';
import { pageTransition, pageTransitionReduced } from '@/lib/motion';
import { SiteVisitFormSheet } from '@/components/siteVisits/SiteVisitFormSheet';

function sortingToOrdering(sorting: SortingState): SiteVisitOrdering {
  if (sorting.length === 0) return '-visit_date';
  const [{ id, desc }] = sorting;
  const field = id === 'visitDate' ? 'visit_date' : id === 'createdAt' ? 'created_at' : id;
  return (desc ? `-${field}` : field) as SiteVisitOrdering;
}

export default function SiteVisitsListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const shouldReduceMotion = useReducedMotion();

  const [page, setPage] = useState(0);
  const [sorting, setSorting] = useState<SortingState>([{ id: 'visitDate', desc: false }]);
  const [formOpen, setFormOpen] = useState(false);
  const [editingSiteVisit, setEditingSiteVisit] = useState<SiteVisit | undefined>(undefined);
  const [deletingSiteVisit, setDeletingSiteVisit] = useState<SiteVisit | null>(null);

  useEffect(() => {
    if (searchParams.get('new') === 'true') {
      setEditingSiteVisit(undefined);
      setFormOpen(true);
      const next = new URLSearchParams(searchParams);
      next.delete('new');
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const ordering = sortingToOrdering(sorting);
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: siteVisitKeys.list({ ordering, page: page + 1 }),
    queryFn: () => getSiteVisits({ ordering, page: page + 1 }),
    placeholderData: keepPreviousData,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteSiteVisit(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.lists() });
      toast.success('Site visit deleted');
      setDeletingSiteVisit(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete site visit.');
      setDeletingSiteVisit(null);
    },
  });

  if (isError) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const openCreate = () => {
    setEditingSiteVisit(undefined);
    setFormOpen(true);
  };

  const columns: ColumnDef<SiteVisit, unknown>[] = [
    {
      accessorKey: 'visitDate',
      header: 'Visit date',
      cell: ({ row }) => (
        <span className="text-body font-medium text-text-primary">{formatDateTime(row.original.visitDate)}</span>
      ),
    },
    {
      id: 'linkedTo',
      header: 'Linked to',
      enableSorting: false,
      cell: ({ row }) => (
        <div className="flex flex-col">
          <span className="text-body text-text-secondary">
            {row.original.projectName || row.original.leadName || '—'}
          </span>
          {row.original.clientName && (
            <span className="text-caption text-text-tertiary">{row.original.clientName}</span>
          )}
        </div>
      ),
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
      accessorKey: 'isCompleted',
      header: 'Status',
      enableSorting: false,
      cell: ({ row }) => (
        <Badge variant={row.original.isCompleted ? 'success' : 'neutral'}>
          {row.original.isCompleted ? 'Completed' : 'Scheduled'}
        </Badge>
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
                aria-label="Site visit actions"
                onClick={(e) => e.stopPropagation()}
              >
                <MoreHorizontal />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onSelect={() => {
                  setEditingSiteVisit(row.original);
                  setFormOpen(true);
                }}
              >
                <Pencil className="size-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem destructive onSelect={() => setDeletingSiteVisit(row.original)}>
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
        title="Site Visits"
        description="Scheduled and completed visits against your leads and projects."
        actions={
          <Button variant="primary" onClick={openCreate}>
            <CalendarCheck />
            Schedule Visit
          </Button>
        }
      />

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        isLoading={isLoading || isFetching}
        hideSearch
        manual
        pageIndex={page}
        pageCount={data?.pagination.totalPages ?? 1}
        totalItems={data?.pagination.totalItems}
        onPageChange={setPage}
        sorting={sorting}
        onSortingChange={setSorting}
        emptyState={{
          icon: CalendarCheck,
          title: 'No site visits yet',
          description: 'Schedule your first site visit against a lead or a project.',
          action: { label: 'Schedule Visit', onClick: openCreate },
        }}
        onRowClick={(siteVisit) => navigate(`/site-visits/${siteVisit.id}`)}
      />

      <SiteVisitFormSheet open={formOpen} onOpenChange={setFormOpen} siteVisit={editingSiteVisit} />

      <ConfirmationDialog
        open={!!deletingSiteVisit}
        onOpenChange={(open) => !open && setDeletingSiteVisit(null)}
        title="Delete this site visit?"
        description="This removes the scheduled visit and everything captured for it."
        confirmLabel="Delete visit"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => deletingSiteVisit && deleteMutation.mutate(deletingSiteVisit.id)}
      />
    </motion.div>
  );
}
