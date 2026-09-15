import { useEffect, useState } from 'react';
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
import { CompanyMemberCombobox } from '@/components/projects/CompanyMemberCombobox';
import { ApiError } from '@/lib/api/client';
import { createLead, updateLead, type Lead, type LeadInput } from '@/lib/api/leads';
import { leadKeys } from '@/lib/queryKeys';

const leadSchema = z.object({
  name: z.string().trim().min(1, 'Lead name is required').max(255),
  companyName: z.string().max(255).optional(),
  email: z.string().email('Enter a valid email address').optional().or(z.literal('')),
  mobile: z.string().max(20).optional(),
  source: z.string().max(100).optional(),
  followUpReminderAt: z.string().optional(),
  notes: z.string().optional(),
});

type LeadFormValues = z.infer<typeof leadSchema>;

const EMPTY_VALUES: LeadFormValues = {
  name: '',
  companyName: '',
  email: '',
  mobile: '',
  source: '',
  followUpReminderAt: '',
  notes: '',
};

function toDatetimeLocal(iso: string | null): string {
  if (!iso) return '';
  const date = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export interface LeadFormSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  lead?: Lead;
  onSaved?: (lead: Lead) => void;
}

// Same Sheet drives both create and edit — the only difference is whether
// a lead is passed in (pre-filled + PATCH) or not (blank + POST). Mirrors
// apps.clients ClientFormSheet's structure. No `status` field here — Lead
// status only moves via the dedicated status/mark-lost/convert actions.
export function LeadFormSheet({ open, onOpenChange, lead, onSaved }: LeadFormSheetProps) {
  const isEdit = !!lead;
  const queryClient = useQueryClient();
  const [assignedToId, setAssignedToId] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LeadFormValues>({ resolver: zodResolver(leadSchema), defaultValues: EMPTY_VALUES });

  useEffect(() => {
    if (!open) return;
    if (lead) {
      reset({
        name: lead.name,
        companyName: lead.companyName,
        email: lead.email,
        mobile: lead.mobile,
        source: lead.source,
        followUpReminderAt: toDatetimeLocal(lead.followUpReminderAt),
        notes: lead.notes,
      });
      setAssignedToId(lead.assignedToId);
    } else {
      reset(EMPTY_VALUES);
      setAssignedToId(null);
    }
  }, [open, lead, reset]);

  const mutation = useMutation({
    mutationFn: (values: LeadFormValues) => {
      const input: LeadInput = {
        name: values.name,
        companyName: values.companyName || '',
        email: values.email || '',
        mobile: values.mobile || '',
        source: values.source || '',
        assignedToId: assignedToId || null,
        followUpReminderAt: values.followUpReminderAt ? new Date(values.followUpReminderAt).toISOString() : null,
        notes: values.notes || '',
      };
      return isEdit ? updateLead(lead!.id, input) : createLead(input);
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      if (isEdit) queryClient.invalidateQueries({ queryKey: leadKeys.detail(saved.id) });
      toast.success(isEdit ? 'Lead updated' : 'Lead created');
      onOpenChange(false);
      onSaved?.(saved);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.code === 'VALIDATION_ERROR') {
        for (const detail of error.details) {
          if (detail.field === 'assignedToId') {
            toast.error(detail.issue);
            continue;
          }
          if (detail.field in EMPTY_VALUES) {
            setError(detail.field as keyof LeadFormValues, { message: detail.issue });
          }
        }
        return;
      }
      const message = error instanceof ApiError ? error.message : 'Something went wrong. Please try again.';
      toast.error(message);
    },
  });

  const onSubmit = (values: LeadFormValues) => mutation.mutate(values);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{isEdit ? 'Edit lead' : 'New lead'}</SheetTitle>
          <SheetDescription>
            {isEdit ? 'Update this lead’s details.' : 'Add a new prospect to your pipeline.'}
          </SheetDescription>
        </SheetHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-1 flex-col gap-5" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="lead-name">Name</Label>
            <Input id="lead-name" invalid={!!errors.name} {...register('name')} />
            {errors.name && <p className="text-small text-danger-text">{errors.name.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="lead-company-name">Company name</Label>
            <Input id="lead-company-name" invalid={!!errors.companyName} {...register('companyName')} />
            {errors.companyName && <p className="text-small text-danger-text">{errors.companyName.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="lead-email">Email</Label>
              <Input id="lead-email" type="email" invalid={!!errors.email} {...register('email')} />
              {errors.email && <p className="text-small text-danger-text">{errors.email.message}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="lead-mobile">Mobile</Label>
              <Input id="lead-mobile" invalid={!!errors.mobile} {...register('mobile')} />
              {errors.mobile && <p className="text-small text-danger-text">{errors.mobile.message}</p>}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="lead-source">Source</Label>
            <Input id="lead-source" placeholder="e.g. Referral, Website, Walk-in" invalid={!!errors.source} {...register('source')} />
            {errors.source && <p className="text-small text-danger-text">{errors.source.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <Label>Assigned to</Label>
              {assignedToId && (
                <button
                  type="button"
                  onClick={() => setAssignedToId(null)}
                  className="text-caption text-text-tertiary hover:text-text-primary"
                >
                  Clear
                </button>
              )}
            </div>
            <CompanyMemberCombobox value={assignedToId} onSelect={setAssignedToId} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="lead-follow-up">Follow-up reminder</Label>
            <Input
              id="lead-follow-up"
              type="datetime-local"
              invalid={!!errors.followUpReminderAt}
              {...register('followUpReminderAt')}
            />
            {errors.followUpReminderAt && (
              <p className="text-small text-danger-text">{errors.followUpReminderAt.message}</p>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="lead-notes">Notes</Label>
            <Textarea id="lead-notes" rows={4} invalid={!!errors.notes} {...register('notes')} />
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
              {isEdit ? 'Save changes' : 'Create lead'}
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
