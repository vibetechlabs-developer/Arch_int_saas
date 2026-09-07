import { useEffect } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert } from '@/components/ui/alert';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { ApiError } from '@/lib/api/client';
import { createClient, updateClient, type Client, type ClientInput } from '@/lib/api/clients';
import { clientKeys } from '@/lib/queryKeys';

const clientSchema = z.object({
  name: z.string().trim().min(1, 'Client name is required').max(255),
  companyName: z.string().max(255).optional(),
  email: z.string().email('Enter a valid email address').optional().or(z.literal('')),
  mobile: z.string().max(20).optional(),
  gstin: z.string().max(15).optional(),
  notes: z.string().optional(),
});

type ClientFormValues = z.infer<typeof clientSchema>;

const EMPTY_VALUES: ClientFormValues = { name: '', companyName: '', email: '', mobile: '', gstin: '', notes: '' };

export interface ClientFormSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  client?: Client;
  onSaved?: (client: Client) => void;
}

// Same Sheet drives both create and edit — the only difference is whether
// a client is passed in (pre-filled + PATCH) or not (blank + POST).
export function ClientFormSheet({ open, onOpenChange, client, onSaved }: ClientFormSheetProps) {
  const isEdit = !!client;
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ClientFormValues>({ resolver: zodResolver(clientSchema), defaultValues: EMPTY_VALUES });

  useEffect(() => {
    if (!open) return;
    reset(
      client
        ? {
            name: client.name,
            companyName: client.companyName,
            email: client.email,
            mobile: client.mobile,
            gstin: client.gstin,
            notes: client.notes,
          }
        : EMPTY_VALUES,
    );
  }, [open, client, reset]);

  const mutation = useMutation({
    mutationFn: (values: ClientInput) =>
      isEdit ? updateClient(client!.id, values) : createClient(values),
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: clientKeys.lists() });
      if (isEdit) queryClient.invalidateQueries({ queryKey: clientKeys.detail(saved.id) });
      toast.success(isEdit ? 'Client updated' : 'Client created');
      onOpenChange(false);
      onSaved?.(saved);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.code === 'VALIDATION_ERROR') {
        for (const detail of error.details) {
          if (detail.field in EMPTY_VALUES) {
            setError(detail.field as keyof ClientFormValues, { message: detail.issue });
          }
        }
        return;
      }
      const message =
        error instanceof ApiError ? error.message : 'Something went wrong. Please try again.';
      toast.error(message);
    },
  });

  const onSubmit = (values: ClientFormValues) => mutation.mutate(values);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{isEdit ? 'Edit client' : 'New client'}</SheetTitle>
          <SheetDescription>
            {isEdit ? 'Update this client’s details.' : 'Add a new client to this workspace.'}
          </SheetDescription>
        </SheetHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-1 flex-col gap-5" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="client-name">Name</Label>
            <Input id="client-name" invalid={!!errors.name} {...register('name')} />
            {errors.name && <p className="text-small text-danger-text">{errors.name.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="client-company-name">Company name</Label>
            <Input id="client-company-name" invalid={!!errors.companyName} {...register('companyName')} />
            {errors.companyName && <p className="text-small text-danger-text">{errors.companyName.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="client-email">Email</Label>
              <Input id="client-email" type="email" invalid={!!errors.email} {...register('email')} />
              {errors.email && <p className="text-small text-danger-text">{errors.email.message}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="client-mobile">Mobile</Label>
              <Input id="client-mobile" invalid={!!errors.mobile} {...register('mobile')} />
              {errors.mobile && <p className="text-small text-danger-text">{errors.mobile.message}</p>}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="client-gstin">GSTIN</Label>
            <Input id="client-gstin" invalid={!!errors.gstin} {...register('gstin')} />
            {errors.gstin && <p className="text-small text-danger-text">{errors.gstin.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="client-notes">Notes</Label>
            <Textarea id="client-notes" rows={4} invalid={!!errors.notes} {...register('notes')} />
            {errors.notes && <p className="text-small text-danger-text">{errors.notes.message}</p>}
          </div>

          {mutation.isError && !(mutation.error instanceof ApiError && mutation.error.code === 'VALIDATION_ERROR') && (
            <Alert variant="destructive">
              {mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong.'}
            </Alert>
          )}

          <div className="mt-auto flex justify-end gap-2 border-t border-border-subtle pt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              {isEdit ? 'Save changes' : 'Create client'}
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
