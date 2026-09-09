import { useEffect } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/lib/api/client';
import { addUser } from '@/lib/api/memberships';
import { getRoles } from '@/lib/api/roles';
import { membershipKeys, roleKeys } from '@/lib/queryKeys';

const schema = z.object({
  name: z.string().trim().min(1, 'Name is required').max(255),
  email: z.string().trim().min(1, 'Email is required').email('Enter a valid email address'),
  roleId: z.string().min(1, 'Select a role'),
});
type FormValues = z.infer<typeof schema>;

export interface AddUserSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// POST /company-memberships/add-user: creates a brand-new User account
// when the email has none yet (unusable password, account-setup email
// sent), or safely links the existing one (never duplicated) — either
// way the admin just fills in the same three fields. The backend
// decides which happened; this UI never needs to know or ask.
export function AddUserSheet({ open, onOpenChange }: AddUserSheetProps) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    setError,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { name: '', email: '', roleId: '' } });

  useEffect(() => {
    if (open) reset({ name: '', email: '', roleId: '' });
  }, [open, reset]);

  const { data: rolesData, isLoading: rolesLoading } = useQuery({
    queryKey: roleKeys.list({ isActive: true, pageSize: 100 }),
    queryFn: () => getRoles({ isActive: true, pageSize: 100, ordering: 'name' }),
    enabled: open,
  });
  const roles = rolesData?.items ?? [];

  const mutation = useMutation({
    mutationFn: (values: FormValues) => addUser({ email: values.email, name: values.name, roleId: values.roleId }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: membershipKeys.lists() });
      toast.success(
        result.activationRequired
          ? 'User added. An account setup email was sent.'
          : 'User added successfully.',
      );
      onOpenChange(false);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.code === 'VALIDATION_ERROR') {
        for (const detail of error.details) {
          if (detail.field === 'email' || detail.field === 'roleId' || detail.field === 'name') {
            setError(detail.field, { message: detail.issue });
          }
        }
        return;
      }
      if (error instanceof ApiError && error.code === 'CONFLICT') {
        setError('email', { message: error.message || 'This user is already a member of this company.' });
        return;
      }
      toast.error(error instanceof ApiError ? error.message : 'Failed to add user.');
    },
  });

  const roleId = watch('roleId');

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent aria-describedby={undefined}>
        <SheetHeader>
          <SheetTitle>Add user</SheetTitle>
          <SheetDescription>Add a person to this company and assign their access role.</SheetDescription>
        </SheetHeader>
        <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="flex flex-col gap-5" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="add-user-name">Full name</Label>
            <Input id="add-user-name" invalid={!!errors.name} {...register('name')} />
            {errors.name && <p className="text-small text-danger-text">{errors.name.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="add-user-email">Email</Label>
            <Input id="add-user-email" type="email" invalid={!!errors.email} {...register('email')} />
            {errors.email && <p className="text-small text-danger-text">{errors.email.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="add-user-role">Role</Label>
            {rolesLoading ? (
              <Skeleton className="h-9 w-full" />
            ) : (
              <Select value={roleId} onValueChange={(value) => setValue('roleId', value, { shouldValidate: true })}>
                <SelectTrigger id="add-user-role" className={errors.roleId ? 'border-danger-text' : undefined}>
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
            {errors.roleId && <p className="text-small text-danger-text">{errors.roleId.message}</p>}
          </div>

          {mutation.isError &&
            !(mutation.error instanceof ApiError && ['VALIDATION_ERROR', 'CONFLICT'].includes(mutation.error.code)) && (
              <Alert variant="destructive">
                {mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong.'}
              </Alert>
            )}

          {mutation.isPending && (
            <p aria-live="polite" className="text-small text-text-tertiary">
              Adding user…
            </p>
          )}

          <div className="mt-2 flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={mutation.isPending} aria-label="Add user">
              Add user
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
