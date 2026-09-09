import { useEffect } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Alert } from '@/components/ui/alert';
import { ApiError } from '@/lib/api/client';
import { createRole, updateRole, type Role } from '@/lib/api/roles';
import { roleKeys } from '@/lib/queryKeys';

const schema = z.object({
  name: z.string().trim().min(1, 'Role name is required').max(100),
  description: z.string().max(2000).optional(),
  isActive: z.boolean(),
});
type FormValues = z.infer<typeof schema>;

export interface RoleFormSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  role?: Role;
  /** Called after a successful CREATE (not edit) with the new role, so the caller can chain the "assign initial permissions" step. */
  onCreated?: (role: Role) => void;
}

export function RoleFormSheet({ open, onOpenChange, role, onCreated }: RoleFormSheetProps) {
  const isEdit = !!role;
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', description: '', isActive: true },
  });

  useEffect(() => {
    if (open) {
      reset({ name: role?.name ?? '', description: role?.description ?? '', isActive: role?.isActive ?? true });
    }
  }, [open, role, reset]);

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      isEdit
        ? updateRole(role!.id, values)
        : createRole({ name: values.name, description: values.description, isActive: values.isActive }),
    onSuccess: (savedRole) => {
      queryClient.invalidateQueries({ queryKey: roleKeys.lists() });
      toast.success(isEdit ? 'Role updated' : 'Role created');
      onOpenChange(false);
      if (!isEdit) onCreated?.(savedRole);
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : 'Something went wrong. Please try again.');
    },
  });

  const isActive = watch('isActive');

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent aria-describedby={undefined}>
        <SheetHeader>
          <SheetTitle>{isEdit ? 'Edit role' : 'New role'}</SheetTitle>
          <SheetDescription>
            {isEdit
              ? 'Update this role\'s name, description, or active status.'
              : "Create a role, then choose which permissions it grants."}
          </SheetDescription>
        </SheetHeader>
        <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="flex flex-col gap-5" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="role-name">Role name</Label>
            <Input id="role-name" invalid={!!errors.name} {...register('name')} />
            {errors.name && <p className="text-small text-danger-text">{errors.name.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="role-description">Description</Label>
            <Textarea id="role-description" invalid={!!errors.description} {...register('description')} />
            {errors.description && <p className="text-small text-danger-text">{errors.description.message}</p>}
          </div>

          <div className="flex items-center justify-between rounded-md border border-border-subtle p-3">
            <div className="flex flex-col">
              <Label htmlFor="role-active">Active</Label>
              <span className="text-caption text-text-tertiary">Inactive roles can't be assigned to members.</span>
            </div>
            <Switch id="role-active" checked={isActive} onCheckedChange={(checked) => setValue('isActive', checked)} />
          </div>

          {mutation.isError && !(mutation.error instanceof ApiError && mutation.error.code === 'VALIDATION_ERROR') && (
            <Alert variant="destructive">
              {mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong.'}
            </Alert>
          )}

          <div className="mt-2 flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={mutation.isPending}>
              {isEdit ? 'Save changes' : 'Create role'}
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
