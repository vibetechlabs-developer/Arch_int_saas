import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ApiError } from '@/lib/api/client';
import { setCompanyOwnerPassword } from '@/lib/api/company';
import { platformCompanyKeys } from '@/lib/queryKeys';

const setOwnerPasswordSchema = z.object({
  newPassword: z.string().trim().min(8, 'Password must be at least 8 characters'),
});

type SetOwnerPasswordFormValues = z.infer<typeof setOwnerPasswordSchema>;

const EMPTY_VALUES: SetOwnerPasswordFormValues = { newPassword: '' };

export interface SetOwnerPasswordDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  companyId: string;
  companyName: string;
  ownerName?: string;
  ownerEmail?: string;
}

// POST /companies/{id}/owner/set-password (platform-admin only) — a direct
// alternative to the normal email-token activation link, since this
// environment's email backend only prints to the server console, which a
// platform admin working from the browser has no way to read.
export function SetOwnerPasswordDialog({
  open,
  onOpenChange,
  companyId,
  companyName,
  ownerName,
  ownerEmail,
}: SetOwnerPasswordDialogProps) {
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<SetOwnerPasswordFormValues>({
    resolver: zodResolver(setOwnerPasswordSchema),
    defaultValues: EMPTY_VALUES,
  });

  const mutation = useMutation({
    mutationFn: (values: SetOwnerPasswordFormValues) => setCompanyOwnerPassword(companyId, values.newPassword),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: platformCompanyKeys.owner(companyId) });
      toast.success(`Password set for ${result.name} (${result.email})`);
      handleOpenChange(false);
    },
  });

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      reset(EMPTY_VALUES);
      mutation.reset();
    }
    onOpenChange(next);
  };

  const errorMessages =
    mutation.error instanceof ApiError
      ? mutation.error.details.length > 0
        ? mutation.error.details.map((detail) => detail.issue)
        : [mutation.error.message]
      : mutation.isError
        ? ['Something went wrong setting this password.']
        : [];

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Set Owner password</DialogTitle>
          <DialogDescription>
            {ownerName && ownerEmail ? (
              <>
                Directly set the password for {ownerName} ({ownerEmail}), "{companyName}"'s Owner, so they can sign
                in without waiting on an activation email.
              </>
            ) : (
              <>
                Directly set the password for "{companyName}"'s Owner, so they can sign in without waiting on an
                activation email.
              </>
            )}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="owner-new-password">New password</Label>
            <Input
              id="owner-new-password"
              type="password"
              autoComplete="new-password"
              invalid={!!errors.newPassword}
              aria-describedby={errors.newPassword ? 'owner-new-password-error' : undefined}
              {...register('newPassword')}
            />
            {errors.newPassword && (
              <p id="owner-new-password-error" className="text-small text-danger-text">
                {errors.newPassword.message}
              </p>
            )}
          </div>

          {errorMessages.length > 0 && (
            <Alert variant="destructive">
              {errorMessages.length === 1 ? (
                errorMessages[0]
              ) : (
                <ul className="list-disc pl-4">
                  {errorMessages.map((issue) => (
                    <li key={issue}>{issue}</li>
                  ))}
                </ul>
              )}
            </Alert>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting || mutation.isPending}>
              Set password
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
