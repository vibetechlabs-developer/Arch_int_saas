import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Label } from '@/components/ui/label';
import { Alert } from '@/components/ui/alert';
import { Skeleton } from '@/components/ui/skeleton';
import { ErrorState } from '@/components/common/ErrorState';
import { RestrictedState } from '@/components/common/RestrictedState';
import { ApiError } from '@/lib/api/client';
import { assignRolePermissions, getRolePermissions, type Role } from '@/lib/api/roles';
import { getPermissions, groupPermissionsByModule } from '@/lib/api/permissions';
import { permissionKeys, roleKeys } from '@/lib/queryKeys';

export interface ManagePermissionsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  role: Role | null;
}

// Fetches BOTH the permission catalog and this role's real, persisted
// grants (GET /roles/{id}/permissions, BE-072) whenever it opens — never
// starts from a blank/guessed baseline, so this same dialog is correct
// whether `role` was just created (grants genuinely empty) or already has
// real RolePermission rows (grants pre-checked from the server). Save
// submits the complete edited set (PUT is a full replacement, not a
// delta) — every currently-checked box, not just the ones the admin
// touched this session.
export function ManagePermissionsDialog({ open, onOpenChange, role }: ManagePermissionsDialogProps) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [isDirty, setIsDirty] = useState(false);

  const { data: permissions, isLoading: catalogLoading } = useQuery({
    queryKey: permissionKeys.all,
    queryFn: getPermissions,
    enabled: open,
  });
  const groups = permissions ? groupPermissionsByModule(permissions) : [];

  const {
    data: grants,
    isLoading: grantsLoading,
    isError: grantsError,
    error: grantsErrorObj,
    refetch: refetchGrants,
  } = useQuery({
    queryKey: role ? roleKeys.permissions(role.id) : ['roles', 'permissions', 'unresolved'],
    queryFn: () => getRolePermissions(role!.id),
    enabled: open && !!role,
  });

  // Re-syncs local checkbox state from the server every time this dialog
  // is pointed at a (possibly different) role's freshly-fetched grants —
  // this is what guarantees Role A's selections never leak into Role B's
  // editor: switching `role` while open re-keys the query above, and this
  // effect resets `selected` the moment that role's real data arrives.
  useEffect(() => {
    if (grants && role && grants.roleId === role.id) {
      setSelected(new Set(grants.permissionCodes));
      setIsDirty(false);
    }
  }, [grants, role]);

  const mutation = useMutation({
    mutationFn: () => assignRolePermissions(role!.id, Array.from(selected)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: roleKeys.lists() });
      if (role) queryClient.invalidateQueries({ queryKey: roleKeys.permissions(role.id) });
      toast.success(`Permissions saved for ${role?.name}`);
      setIsDirty(false);
      onOpenChange(false);
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : 'Failed to save permissions.');
    },
  });

  const toggle = (code: string, checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(code);
      else next.delete(code);
      return next;
    });
    setIsDirty(true);
  };

  const isLoading = catalogLoading || grantsLoading;
  const isRestricted = grantsError && grantsErrorObj instanceof ApiError && grantsErrorObj.status === 403;

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) setIsDirty(false);
        onOpenChange(next);
      }}
    >
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Manage permissions</DialogTitle>
          <DialogDescription>Choose what {role?.name ?? 'this role'} can do.</DialogDescription>
        </DialogHeader>

        {isRestricted ? (
          <RestrictedState message={grantsErrorObj instanceof ApiError ? grantsErrorObj.message : undefined} />
        ) : grantsError ? (
          <ErrorState error={grantsErrorObj} onRetry={() => refetchGrants()} />
        ) : (
          <>
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
                          setIsDirty(true);
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

            <DialogFooter className="items-center sm:justify-between">
              <p className="text-caption text-text-tertiary">
                {isDirty ? 'You have unsaved changes.' : selected.size > 0 ? `${selected.size} permission(s) granted.` : 'No permissions granted.'}
              </p>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>
                  Cancel
                </Button>
                <Button variant="primary" loading={mutation.isPending} onClick={() => mutation.mutate()}>
                  Save changes
                </Button>
              </div>
            </DialogFooter>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
