import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { type ColumnDef, type SortingState } from '@tanstack/react-table';
import { MoreHorizontal, Repeat, ShieldOff, Trash2, UserPlus, Users } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { DataTable } from '@/components/common/DataTable';
import { ErrorState } from '@/components/common/ErrorState';
import { RestrictedState } from '@/components/common/RestrictedState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Button } from '@/components/ui/button';
import { Avatar, AvatarFallback, initialsOf } from '@/components/ui/avatar';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ApiError } from '@/lib/api/client';
import {
  getCompanyMemberships,
  removeMember,
  reactivateMember,
  suspendMember,
  type CompanyMembership,
  type MembershipStatus,
} from '@/lib/api/memberships';
import { membershipKeys } from '@/lib/queryKeys';
import { formatDate } from '@/lib/format';
import { useAuth } from '@/context/AuthContext';
import { InviteMemberSheet } from '@/components/settings/InviteMemberSheet';
import { ChangeMemberRoleDialog } from '@/components/settings/ChangeMemberRoleDialog';
import { MemberDetailSheet } from '@/components/settings/MemberDetailSheet';

function sortingToOrdering(sorting: SortingState): 'created_at' | '-created_at' | 'status' | '-status' {
  if (sorting.length === 0) return '-created_at';
  const [{ id, desc }] = sorting;
  const field = id === 'createdAt' ? 'created_at' : id;
  return (desc ? `-${field}` : field) as 'created_at' | '-created_at' | 'status' | '-status';
}

export default function MembersPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState<MembershipStatus | ''>('');
  const [sorting, setSorting] = useState<SortingState>([{ id: 'createdAt', desc: true }]);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [roleDialogMember, setRoleDialogMember] = useState<CompanyMembership | null>(null);
  const [detailMember, setDetailMember] = useState<CompanyMembership | null>(null);
  const [suspendTarget, setSuspendTarget] = useState<CompanyMembership | null>(null);
  const [reactivateTarget, setReactivateTarget] = useState<CompanyMembership | null>(null);
  const [removeTarget, setRemoveTarget] = useState<CompanyMembership | null>(null);

  useEffect(() => {
    if (searchParams.get('invite') === 'true') {
      setInviteOpen(true);
      const next = new URLSearchParams(searchParams);
      next.delete('invite');
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const ordering = sortingToOrdering(sorting);
  const queryParams = { status: statusFilter || undefined, ordering, page: page + 1 };
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: membershipKeys.list(queryParams),
    queryFn: () => getCompanyMemberships(queryParams),
    placeholderData: keepPreviousData,
  });

  const invalidateMembers = () => queryClient.invalidateQueries({ queryKey: membershipKeys.lists() });

  const suspendMutation = useMutation({
    mutationFn: (id: string) => suspendMember(id),
    onSuccess: () => {
      invalidateMembers();
      toast.success('Member suspended — they will lose access to this company until reactivated.');
      setSuspendTarget(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to suspend member.');
      setSuspendTarget(null);
    },
  });

  const reactivateMutation = useMutation({
    mutationFn: (id: string) => reactivateMember(id),
    onSuccess: () => {
      invalidateMembers();
      toast.success('Member reactivated');
      setReactivateTarget(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to reactivate member.');
      setReactivateTarget(null);
    },
  });

  const removeMutation = useMutation({
    mutationFn: (id: string) => removeMember(id),
    onSuccess: () => {
      invalidateMembers();
      toast.success('Member removed from this company');
      setRemoveTarget(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to remove member.');
      setRemoveTarget(null);
    },
  });

  if (isError) {
    if (error instanceof ApiError && error.status === 403) {
      return <RestrictedState message={error.message} />;
    }
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const columns: ColumnDef<CompanyMembership, unknown>[] = [
    {
      accessorKey: 'userName',
      header: 'Member',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <Avatar>
            <AvatarFallback seed={row.original.userId}>{initialsOf(row.original.userName)}</AvatarFallback>
          </Avatar>
          <div className="flex flex-col">
            <span className="text-body font-medium text-text-primary">{row.original.userName}</span>
            <span className="text-caption text-text-tertiary">{row.original.userEmail}</span>
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'roleName',
      header: 'Role',
      enableSorting: false,
      cell: ({ row }) => <span className="text-body text-text-secondary">{row.original.roleName ?? '—'}</span>,
    },
    {
      accessorKey: 'status',
      header: 'Status',
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'createdAt',
      header: 'Joined',
      cell: ({ row }) => <span className="text-small text-text-tertiary">{formatDate(row.original.createdAt)}</span>,
    },
    {
      id: 'actions',
      header: '',
      enableSorting: false,
      enableHiding: false,
      cell: ({ row }) => {
        const member = row.original;
        const isSelf = !!user && member.userId === user.id;
        return (
          <div className="flex justify-end">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" aria-label="Member actions" onClick={(e) => e.stopPropagation()}>
                  <MoreHorizontal />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onSelect={() => setDetailMember(member)}>View details</DropdownMenuItem>
                <DropdownMenuItem onSelect={() => setRoleDialogMember(member)}>
                  <Repeat className="size-4" />
                  Change role
                </DropdownMenuItem>
                {member.status === 'revoked' ? (
                  <DropdownMenuItem onSelect={() => setReactivateTarget(member)}>Reactivate</DropdownMenuItem>
                ) : (
                  <DropdownMenuItem
                    disabled={isSelf}
                    onSelect={() => setSuspendTarget(member)}
                  >
                    <ShieldOff className="size-4" />
                    {isSelf ? 'Suspend (unavailable for your own account)' : 'Suspend'}
                  </DropdownMenuItem>
                )}
                <DropdownMenuItem destructive disabled={isSelf} onSelect={() => setRemoveTarget(member)}>
                  <Trash2 className="size-4" />
                  {isSelf ? 'Remove (unavailable for your own account)' : 'Remove'}
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
        title="Members"
        description="Invite teammates and manage who has access to this company."
        actions={
          <Button variant="primary" onClick={() => setInviteOpen(true)}>
            <UserPlus />
            Invite member
          </Button>
        }
      />

      <Select
        value={statusFilter || 'all'}
        onValueChange={(value) => {
          setStatusFilter(value === 'all' ? '' : (value as MembershipStatus));
          setPage(0);
        }}
      >
        <SelectTrigger className="w-48">
          <SelectValue placeholder="All statuses" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">All statuses</SelectItem>
          <SelectItem value="active">Active</SelectItem>
          <SelectItem value="invited">Invited</SelectItem>
          <SelectItem value="revoked">Revoked</SelectItem>
        </SelectContent>
      </Select>

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
          statusFilter
            ? { icon: Users, title: 'No members match this filter', description: 'Try a different status.' }
            : {
                icon: Users,
                title: 'No team members yet',
                description: 'Add your first member to start collaborating.',
                action: { label: 'Invite member', onClick: () => setInviteOpen(true) },
              }
        }
        onRowClick={(member) => setDetailMember(member)}
      />

      <InviteMemberSheet open={inviteOpen} onOpenChange={setInviteOpen} />
      <ChangeMemberRoleDialog
        open={!!roleDialogMember}
        onOpenChange={(open) => !open && setRoleDialogMember(null)}
        member={roleDialogMember}
      />
      <MemberDetailSheet
        open={!!detailMember}
        onOpenChange={(open) => !open && setDetailMember(null)}
        member={detailMember}
      />

      <ConfirmationDialog
        open={!!suspendTarget}
        onOpenChange={(open) => !open && setSuspendTarget(null)}
        title="Suspend this member?"
        description={`${suspendTarget?.userName ?? 'This member'} will lose access to this company until reactivated. Their account and any other company memberships are not affected.`}
        confirmLabel="Suspend member"
        destructive
        loading={suspendMutation.isPending}
        onConfirm={() => suspendTarget && suspendMutation.mutate(suspendTarget.id)}
      />

      <ConfirmationDialog
        open={!!reactivateTarget}
        onOpenChange={(open) => !open && setReactivateTarget(null)}
        title="Reactivate this member?"
        description={`${reactivateTarget?.userName ?? 'This member'} will regain access to this company.`}
        confirmLabel="Reactivate member"
        loading={reactivateMutation.isPending}
        onConfirm={() => reactivateTarget && reactivateMutation.mutate(reactivateTarget.id)}
      />

      <ConfirmationDialog
        open={!!removeTarget}
        onOpenChange={(open) => !open && setRemoveTarget(null)}
        title="Remove this member from the company?"
        description={`${removeTarget?.userName ?? 'This member'} loses access to this company. This does not delete their user account or affect any other company they belong to.`}
        confirmLabel="Remove from company"
        destructive
        loading={removeMutation.isPending}
        onConfirm={() => removeTarget && removeMutation.mutate(removeTarget.id)}
      />
    </div>
  );
}
