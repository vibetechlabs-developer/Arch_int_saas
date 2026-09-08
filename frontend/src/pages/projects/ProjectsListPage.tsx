import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { motion, useReducedMotion } from 'framer-motion';
import { type ColumnDef, type SortingState } from '@tanstack/react-table';
import { FolderKanban, MoreHorizontal, Pencil, Repeat, Trash2 } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { DataTable } from '@/components/common/DataTable';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ApiError } from '@/lib/api/client';
import { deleteProject, getProjects, type Project, type ProjectOrdering } from '@/lib/api/projects';
import { projectKeys } from '@/lib/queryKeys';
import { formatDate } from '@/lib/format';
import { pageTransition, pageTransitionReduced } from '@/lib/motion';
import { ProjectFormSheet } from '@/components/projects/ProjectFormSheet';
import { StatusTransitionDialog } from '@/components/projects/StatusTransitionDialog';
import { ProjectFilterBar, type ProjectFilterValues } from '@/components/projects/ProjectFilterBar';

function sortingToOrdering(sorting: SortingState): ProjectOrdering {
  if (sorting.length === 0) return '-updated_at';
  const [{ id, desc }] = sorting;
  const field = id === 'startDate' ? 'start_date' : id === 'updatedAt' ? 'updated_at' : id;
  return (desc ? `-${field}` : field) as ProjectOrdering;
}

const EMPTY_FILTERS: ProjectFilterValues = { status: '', clientId: null, clientLabel: null, priority: '' };

export default function ProjectsListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const shouldReduceMotion = useReducedMotion();

  const [page, setPage] = useState(0);
  const [filters, setFilters] = useState<ProjectFilterValues>(EMPTY_FILTERS);
  const [sorting, setSorting] = useState<SortingState>([{ id: 'updatedAt', desc: true }]);
  const [formOpen, setFormOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<Project | undefined>(undefined);
  const [statusProject, setStatusProject] = useState<Project | null>(null);
  const [deletingProject, setDeletingProject] = useState<Project | null>(null);

  useEffect(() => {
    if (searchParams.get('new') === 'true') {
      setEditingProject(undefined);
      setFormOpen(true);
      const next = new URLSearchParams(searchParams);
      next.delete('new');
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const ordering = sortingToOrdering(sorting);
  const queryParams = {
    status: filters.status || undefined,
    client: filters.clientId || undefined,
    priority: filters.priority || undefined,
    ordering,
    page: page + 1,
  };
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: projectKeys.list(queryParams),
    queryFn: () => getProjects(queryParams),
    placeholderData: keepPreviousData,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteProject(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
      toast.success('Project deleted');
      setDeletingProject(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete project.');
      setDeletingProject(null);
    },
  });

  if (isError) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const openCreate = () => {
    setEditingProject(undefined);
    setFormOpen(true);
  };

  const updateFilters = (patch: Partial<ProjectFilterValues>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(0);
  };

  const hasFilters = !!filters.status || !!filters.clientId || !!filters.priority;

  const columns: ColumnDef<Project, unknown>[] = [
    {
      accessorKey: 'name',
      header: 'Project',
      cell: ({ row }) => (
        <div className="flex flex-col">
          <span className="text-body font-medium text-text-primary">{row.original.name}</span>
          <span className="text-caption text-text-tertiary">{row.original.clientName}</span>
        </div>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      enableSorting: false,
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'priority',
      header: 'Priority',
      enableSorting: false,
      cell: ({ row }) =>
        row.original.priority ? <Badge variant="neutral">{row.original.priority}</Badge> : <span className="text-text-tertiary">—</span>,
    },
    {
      accessorKey: 'startDate',
      header: 'Start Date',
      cell: ({ row }) => (
        <span className="text-small text-text-secondary">
          {row.original.startDate ? formatDate(row.original.startDate) : '—'}
        </span>
      ),
    },
    {
      accessorKey: 'deadline',
      header: 'Deadline',
      cell: ({ row }) => (
        <span className="text-small text-text-secondary">
          {row.original.deadline ? formatDate(row.original.deadline) : '—'}
        </span>
      ),
    },
    {
      accessorKey: 'updatedAt',
      header: 'Updated',
      cell: ({ row }) => <span className="text-small text-text-tertiary">{formatDate(row.original.updatedAt)}</span>,
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
              <Button variant="ghost" size="icon" aria-label="Project actions" onClick={(e) => e.stopPropagation()}>
                <MoreHorizontal />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onSelect={() => {
                  setEditingProject(row.original);
                  setFormOpen(true);
                }}
              >
                <Pencil className="size-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => setStatusProject(row.original)}>
                <Repeat className="size-4" />
                Change status
              </DropdownMenuItem>
              <DropdownMenuItem destructive onSelect={() => setDeletingProject(row.original)}>
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
        title="Projects"
        description="Where client, BOQ, quotation, invoice, and expense data connect."
        actions={
          <Button variant="primary" onClick={openCreate}>
            <FolderKanban />
            New Project
          </Button>
        }
      />

      <ProjectFilterBar value={filters} onChange={updateFilters} onClearAll={() => updateFilters(EMPTY_FILTERS)} />

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
        emptyState={
          hasFilters
            ? {
                icon: FolderKanban,
                title: 'No projects match these filters',
                description: 'Try a different status, client, or priority.',
              }
            : {
                icon: FolderKanban,
                title: 'No projects yet',
                description:
                  'Projects connect a client to their BOQ, quotations, invoices, expenses, and documents. Create your first one to get started.',
                action: { label: 'New Project', onClick: openCreate },
              }
        }
        onRowClick={(project) => navigate(`/projects/${project.id}/overview`)}
      />

      <ProjectFormSheet open={formOpen} onOpenChange={setFormOpen} project={editingProject} />

      {statusProject && (
        <StatusTransitionDialog open={!!statusProject} onOpenChange={(open) => !open && setStatusProject(null)} project={statusProject} />
      )}

      <ConfirmationDialog
        open={!!deletingProject}
        onOpenChange={(open) => !open && setDeletingProject(null)}
        title="Delete this project?"
        description={`This removes "${deletingProject?.name}" and its team assignments. Related BOQs, quotations, invoices, and expenses are not affected.`}
        confirmLabel="Delete project"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => deletingProject && deleteMutation.mutate(deletingProject.id)}
      />
    </motion.div>
  );
}
