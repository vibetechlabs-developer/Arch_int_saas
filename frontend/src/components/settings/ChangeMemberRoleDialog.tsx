import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Alert } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/lib/api/client';
import { assignMemberRole, type CompanyMembership } from '@/lib/api/memberships';
import { getRoles } from '@/lib/api/roles';
import { membershipKeys, roleKeys } from '@/lib/queryKeys';

export interface ChangeMemberRoleDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  member: CompanyMembership | null;
}

// Backend enforces a privilege-escalation guard here (an actor can never
// assign a role granting codes beyond their own) and there is no self-role
// change protection beyond that generic guard — a 403 from either surfaces
// through the Alert below exactly as returned, never re-worded.
export function ChangeMemberRoleDialog({ open, onOpenChange, member }: ChangeMemberRoleDialogProps) {
  const queryClient = useQueryClient();
  const [roleId, setRoleId] = useState<string>('');

  useEffect(() => {
    if (open) setRoleId(member?.roleId ?? '');
  }, [open, member]);

  const { data: rolesData, isLoading: rolesLoading } = useQuery({
    queryKey: roleKeys.list({ isActive: true, pageSize: 100 }),
    queryFn: () => getRoles({ isActive: true, pageSize: 100, ordering: 'name' }),
    enabled: open,
  });
  const roles = rolesData?.items ?? [];

  const mutation = useMutation({
    mutationFn: () => assignMemberRole(member!.id, roleId || null),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: membershipKeys.lists() });
      queryClient.invalidateQueries({ queryKey: membershipKeys.detail(member!.id) });
      toast.success('Role updated');
      onOpenChange(false);
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : 'Failed to update role.');
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Change role</DialogTitle>
          <DialogDescription>{member ? `Update the role for ${member.userName}.` : ''}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-1.5">
          <Label htmlFor="change-role">Role</Label>
          {rolesLoading ? (
            <Skeleton className="h-9 w-full" />
          ) : (
            <Select value={roleId} onValueChange={setRoleId}>
              <SelectTrigger id="change-role">
                <SelectValue placeholder="Select a role" />
              </SelectTrigger>
              <SelectContent>
                {roles.map((role) => (
                  <SelectItem key={role.id} value={role.id}>
                    {role.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>

        {mutation.isError && (
          <Alert variant="destructive">
            {mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong.'}
          </Alert>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="primary"
            loading={mutation.isPending}
            disabled={!member || roleId === (member.roleId ?? '')}
            onClick={() => mutation.mutate()}
          >
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
