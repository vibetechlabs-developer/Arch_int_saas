import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Alert } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/lib/api/client';
import { assignRolePermissions, type Role } from '@/lib/api/roles';
import { getPermissions, groupPermissionsByModule } from '@/lib/api/permissions';
import { permissionKeys, roleKeys } from '@/lib/queryKeys';

export interface AssignInitialPermissionsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  role: Role | null;
}

// Only ever opened right after RoleFormSheet creates a NEW role — a fresh
// Role has zero RolePermission rows, so starting every checkbox unchecked
// here is accurate, not assumed. This dialog is deliberately never reused
// as an "edit an existing role's permissions" screen: PUT
// /roles/{id}/permissions is a full-replacement write with no matching
// read endpoint anywhere in the backend, so there is no safe way to know
// — and therefore pre-check — what an already-configured role currently
// grants. See RolesPage's "Permissions" section for that documented gap.
export function AssignInitialPermissionsDialog({ open, onOpenChange, role }: AssignInitialPermissionsDialogProps) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const { data: permissions, isLoading } = useQuery({
    queryKey: permissionKeys.all,
    queryFn: getPermissions,
    enabled: open,
  });
  const groups = permissions ? groupPermissionsByModule(permissions) : [];

  const mutation = useMutation({
    mutationFn: () => assignRolePermissions(role!.id, Array.from(selected)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: roleKeys.lists() });
      toast.success(`Permissions assigned to ${role?.name}`);
      setSelected(new Set());
      onOpenChange(false);
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : 'Failed to assign permissions.');
    },
  });

  const toggle = (code: string, checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(code);
      else next.delete(code);
      return next;
    });
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setSelected(new Set());
        onOpenChange(next);
      }}
    >
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Assign permissions</DialogTitle>
          <DialogDescription>
            Choose what {role?.name ?? 'this role'} can do. You can grant more later, but changing an
            already-configured role's permissions isn't available in this UI yet.
          </DialogDescription>
        </DialogHeader>

        <div className="flex max-h-96 flex-col gap-4 overflow-y-auto pr-1">
          {isLoading ? (
            <>
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-24 w-full" />
            </>
          ) : (
            groups.map((group) => (
              <div key={group.module} className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="text-label text-text-tertiary capitalize">{group.module}</span>
                  <button
                    type="button"
                    className="text-caption text-accent-500 hover:underline"
                    onClick={() => {
                      const allSelected = group.permissions.every((p) => selected.has(p.code));
                      setSelected((prev) => {
                        const next = new Set(prev);
                        for (const permission of group.permissions) {
                          if (allSelected) next.delete(permission.code);
                          else next.add(permission.code);
                        }
                        return next;
                      });
                    }}
                  >
                    {group.permissions.every((p) => selected.has(p.code)) ? 'Clear all' : 'Select all'}
                  </button>
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-2 rounded-md border border-border-subtle p-3">
                  {group.permissions.map((permission) => (
                    <div key={permission.code} className="flex items-start gap-2">
                      <Checkbox
                        id={`perm-${permission.code}`}
                        checked={selected.has(permission.code)}
                        onCheckedChange={(checked) => toggle(permission.code, !!checked)}
                      />
                      <Label htmlFor={`perm-${permission.code}`} className="flex flex-col gap-0 font-normal">
                        <span className="text-small text-text-primary">{permission.action}</span>
                        <span className="text-caption text-text-tertiary">{permission.description}</span>
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>

        {mutation.isError && (
          <Alert variant="destructive">
            {mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong.'}
          </Alert>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>
            Skip for now
          </Button>
          <Button variant="primary" loading={mutation.isPending} onClick={() => mutation.mutate()}>
            Assign {selected.size > 0 ? `(${selected.size})` : ''}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
