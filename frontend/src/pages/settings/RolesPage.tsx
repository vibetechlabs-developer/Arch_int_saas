import { useState } from 'react';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { type ColumnDef, type SortingState } from '@tanstack/react-table';
import { Info, MoreHorizontal, Pencil, ShieldCheck, Trash2 } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { DataTable } from '@/components/common/DataTable';
import { ErrorState } from '@/components/common/ErrorState';
import { RestrictedState } from '@/components/common/RestrictedState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ApiError } from '@/lib/api/client';
import { deleteRole, getRoles, type Role, type RoleOrdering } from '@/lib/api/roles';
import { roleKeys } from '@/lib/queryKeys';
import { formatDate } from '@/lib/format';
import { RoleFormSheet } from '@/components/settings/RoleFormSheet';
import { AssignInitialPermissionsDialog } from '@/components/settings/AssignInitialPermissionsDialog';

function sortingToOrdering(sorting: SortingState): RoleOrdering {
  if (sorting.length === 0) return '-created_at';
  const [{ id, desc }] = sorting;
  const field = id === 'createdAt' ? 'created_at' : id === 'isActive' ? 'is_active' : id;
  return (desc ? `-${field}` : field) as RoleOrdering;
}

export default function RolesPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [sorting, setSorting] = useState<SortingState>([{ id: 'name', desc: false }]);
  const [formOpen, setFormOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<Role | undefined>(undefined);
  const [assignPermissionsFor, setAssignPermissionsFor] = useState<Role | null>(null);
  const [deletingRole, setDeletingRole] = useState<Role | null>(null);

  const ordering = sortingToOrdering(sorting);
  const queryParams = { ordering, page: page + 1 };
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: roleKeys.list(queryParams),
    queryFn: () => getRoles(queryParams),
    placeholderData: keepPreviousData,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteRole(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: roleKeys.lists() });
      toast.success('Role deleted');
      setDeletingRole(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete role.');
      setDeletingRole(null);
    },
  });

  if (isError) {
    if (error instanceof ApiError && error.status === 403) {
      return <RestrictedState message={error.message} />;
    }
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const columns: ColumnDef<Role, unknown>[] = [
    {
      accessorKey: 'name',
      header: 'Role',
      cell: ({ row }) => (
        <div className="flex items-center gap-2">
          <span className="text-body font-medium text-text-primary">{row.original.name}</span>
          {!row.original.isActive && <Badge variant="neutral">Inactive</Badge>}
        </div>
      ),
    },
    {
      accessorKey: 'description',
      header: 'Description',
      enableSorting: false,
      cell: ({ row }) => (
        <span className="text-body text-text-secondary">{row.original.description || '—'}</span>
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
              <Button variant="ghost" size="icon" aria-label="Role actions" onClick={(e) => e.stopPropagation()}>
                <MoreHorizontal />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onSelect={() => {
                  setEditingRole(row.original);
                  setFormOpen(true);
                }}
              >
                <Pencil className="size-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem destructive onSelect={() => setDeletingRole(row.original)}>
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
        title="Roles & Permissions"
        description="Define roles and what each one can do in your company."
        actions={
          <Button
            variant="primary"
            onClick={() => {
              setEditingRole(undefined);
              setFormOpen(true);
            }}
          >
            <ShieldCheck />
            New role
          </Button>
        }
      />

      <Alert variant="info">
        <AlertDescription>
          Editing permissions for an existing role isn't available yet — the platform can't currently read a role's
          existing permission grants, so a blind update could accidentally revoke access. Permissions can only be
          assigned right after creating a new role. See the permission catalog for reference.
        </AlertDescription>
      </Alert>

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
          icon: ShieldCheck,
          title: 'No roles yet',
          description: 'Create your first role to start assigning permissions to your team.',
          action: {
            label: 'New role',
            onClick: () => {
              setEditingRole(undefined);
              setFormOpen(true);
            },
          },
        }}
      />

      <RoleFormSheet
        open={formOpen}
        onOpenChange={setFormOpen}
        role={editingRole}
        onCreated={(role) => setAssignPermissionsFor(role)}
      />

      <AssignInitialPermissionsDialog
        open={!!assignPermissionsFor}
        onOpenChange={(open) => !open && setAssignPermissionsFor(null)}
        role={assignPermissionsFor}
      />

      <ConfirmationDialog
        open={!!deletingRole}
        onOpenChange={(open) => !open && setDeletingRole(null)}
        title="Delete this role?"
        description={`This role will be permanently removed. Members currently holding "${deletingRole?.name}" should be reassigned a new role first.`}
        confirmLabel="Delete role"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => deletingRole && deleteMutation.mutate(deletingRole.id)}
      />

      <p className="flex items-center gap-1.5 text-caption text-text-tertiary">
        <Info className="size-3.5" />
        Deleting a role does not automatically reassign the members who currently hold it.
      </p>
    </div>
  );
}
