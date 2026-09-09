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
import { inviteMember } from '@/lib/api/memberships';
import { getRoles } from '@/lib/api/roles';
import { membershipKeys, roleKeys } from '@/lib/queryKeys';

const schema = z.object({
  email: z.string().trim().min(1, 'Email is required').email('Enter a valid email address'),
  roleId: z.string().min(1, 'Select a role'),
});
type FormValues = z.infer<typeof schema>;

export interface InviteMemberSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// Invites an EXISTING user (by email) into the company — the backend does
// not create a new account or send a signup email; it 404s if no user with
// that email exists yet. Labeled "Invite" (not "Add User") because that's
// exactly what POST /company-memberships does: create a membership row for
// an identity that already exists, status "invited" until the person's
// next login resolves it into "active".
export function InviteMemberSheet({ open, onOpenChange }: InviteMemberSheetProps) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    setError,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { email: '', roleId: '' } });

  useEffect(() => {
    if (open) reset({ email: '', roleId: '' });
  }, [open, reset]);

  const { data: rolesData, isLoading: rolesLoading } = useQuery({
    queryKey: roleKeys.list({ isActive: true, pageSize: 100 }),
    queryFn: () => getRoles({ isActive: true, pageSize: 100, ordering: 'name' }),
    enabled: open,
  });
  const roles = rolesData?.items ?? [];

  const mutation = useMutation({
    mutationFn: (values: FormValues) => inviteMember({ email: values.email, roleId: values.roleId }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: membershipKeys.lists() });
      toast.success('Member invited');
      onOpenChange(false);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.code === 'VALIDATION_ERROR') {
        for (const detail of error.details) {
          if (detail.field === 'email' || detail.field === 'roleId') {
            setError(detail.field, { message: detail.issue });
          }
        }
        return;
      }
      if (error instanceof ApiError && error.code === 'NOT_FOUND') {
        setError('email', { message: 'No user exists with this email address yet.' });
        return;
      }
      if (error instanceof ApiError && error.code === 'CONFLICT') {
        setError('email', { message: error.message || 'This user is already a member of this company.' });
        return;
      }
      toast.error(error instanceof ApiError ? error.message : 'Failed to invite member.');
    },
  });

  const roleId = watch('roleId');

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent aria-describedby={undefined}>
        <SheetHeader>
          <SheetTitle>Invite member</SheetTitle>
          <SheetDescription>
            Invites an existing user into your company by email. They must already have an account.
          </SheetDescription>
        </SheetHeader>
        <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="flex flex-col gap-5" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="invite-email">Email</Label>
            <Input id="invite-email" type="email" invalid={!!errors.email} {...register('email')} />
            {errors.email && <p className="text-small text-danger-text">{errors.email.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="invite-role">Role</Label>
            {rolesLoading ? (
              <Skeleton className="h-9 w-full" />
            ) : (
              <Select value={roleId} onValueChange={(value) => setValue('roleId', value, { shouldValidate: true })}>
                <SelectTrigger id="invite-role" className={errors.roleId ? 'border-danger-text' : undefined}>
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
            !(mutation.error instanceof ApiError && ['VALIDATION_ERROR', 'NOT_FOUND', 'CONFLICT'].includes(mutation.error.code)) && (
              <Alert variant="destructive">
                {mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong.'}
              </Alert>
            )}

          <div className="mt-2 flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={mutation.isPending}>
              Send invite
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
