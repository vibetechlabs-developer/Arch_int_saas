import { useState } from 'react';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { type ColumnDef, type SortingState } from '@tanstack/react-table';
import { Info, KeyRound, Lock, MoreHorizontal, Pencil, ShieldCheck, Trash2 } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { DataTable } from '@/components/common/DataTable';
import { ErrorState } from '@/components/common/ErrorState';
import { RestrictedState } from '@/components/common/RestrictedState';
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
import { deleteRole, getRoles, OWNER_SYSTEM_KEY, type Role, type RoleOrdering } from '@/lib/api/roles';
import { roleKeys } from '@/lib/queryKeys';
import { formatDate } from '@/lib/format';
import { RoleFormSheet } from '@/components/settings/RoleFormSheet';
import { ManagePermissionsDialog } from '@/components/settings/ManagePermissionsDialog';

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
  const [managePermissionsFor, setManagePermissionsFor] = useState<Role | null>(null);
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
          {row.original.isSystem && (
            <Badge variant="neutral" className="gap-1">
              <Lock className="size-3" />
              System role
            </Badge>
          )}
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
      cell: ({ row }) => {
        // Only the system Owner role is undeletable server-side — every
        // other role (including other system roles like Admin) follows
        // ordinary delete rules. Disabling here is a UX courtesy, never
        // the security boundary: an attempt past this would still be
        // rejected by the backend's own systemKey check.
        const isProtectedOwner = row.original.systemKey === OWNER_SYSTEM_KEY;
        return (
        <div className="flex justify-end">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Role actions" onClick={(e) => e.stopPropagation()}>
                <MoreHorizontal />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={() => setManagePermissionsFor(row.original)}>
                <KeyRound className="size-4" />
                Manage permissions
              </DropdownMenuItem>
              <DropdownMenuItem
                onSelect={() => {
                  setEditingRole(row.original);
                  setFormOpen(true);
                }}
              >
                <Pencil className="size-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem
                destructive
                disabled={isProtectedOwner}
                onSelect={() => setDeletingRole(row.original)}
              >
                <Trash2 className="size-4" />
                {isProtectedOwner ? 'Delete (system role — cannot be deleted)' : 'Delete'}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        );
      },
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
        onCreated={(role) => setManagePermissionsFor(role)}
      />

      <ManagePermissionsDialog
        open={!!managePermissionsFor}
        onOpenChange={(open) => !open && setManagePermissionsFor(null)}
        role={managePermissionsFor}
      />

      <ConfirmationDialog
        open={!!deletingRole}
        onOpenChange={(open) => !open && setDeletingRole(null)}
        title="Delete this role?"
        description={`This role will be removed. Any members currently holding "${deletingRole?.name}" will immediately lose the permissions it grants and become unassigned — reassign them to a different role first if they should keep access.`}
        confirmLabel="Delete role"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => deletingRole && deleteMutation.mutate(deletingRole.id)}
      />

      <p className="flex items-center gap-1.5 text-caption text-text-tertiary">
        <Info className="size-3.5" />
        Deleting a role unassigns every member who currently holds it — it does not reassign them to another role.
      </p>
    </div>
  );
}
