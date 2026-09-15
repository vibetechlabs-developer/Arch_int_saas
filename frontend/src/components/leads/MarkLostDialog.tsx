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
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ApiError } from '@/lib/api/client';
import { markLeadLost, type Lead } from '@/lib/api/leads';
import { leadKeys } from '@/lib/queryKeys';

const markLostSchema = z.object({
  lossReason: z.string().trim().min(1, 'A loss reason is required'),
  followUpReminderAt: z.string().optional(),
});

type MarkLostFormValues = z.infer<typeof markLostSchema>;

const EMPTY_VALUES: MarkLostFormValues = { lossReason: '', followUpReminderAt: '' };

export interface MarkLostDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  lead: Lead;
}

// POST /leads/{id}/mark-lost (04_API/CRM_API.md: "requires loss reason,
// optional follow-up date").
export function MarkLostDialog({ open, onOpenChange, lead }: MarkLostDialogProps) {
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<MarkLostFormValues>({ resolver: zodResolver(markLostSchema), defaultValues: EMPTY_VALUES });

  const mutation = useMutation({
    mutationFn: (values: MarkLostFormValues) =>
      markLeadLost(lead.id, {
        lossReason: values.lossReason,
        followUpReminderAt: values.followUpReminderAt ? new Date(values.followUpReminderAt).toISOString() : null,
      }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: leadKeys.detail(updated.id) });
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      toast.success('Lead marked as lost');
      handleOpenChange(false);
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : 'Something went wrong marking this lead as lost.');
    },
  });

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      reset(EMPTY_VALUES);
      mutation.reset();
    }
    onOpenChange(next);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Mark lead as lost</DialogTitle>
          <DialogDescription>
            Record why "{lead.name}" didn't convert. This can't be undone from here.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="mark-lost-reason">Loss reason</Label>
            <Textarea id="mark-lost-reason" rows={3} invalid={!!errors.lossReason} {...register('lossReason')} />
            {errors.lossReason && <p className="text-small text-danger-text">{errors.lossReason.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="mark-lost-follow-up">Follow-up reminder (optional)</Label>
            <Input id="mark-lost-follow-up" type="datetime-local" {...register('followUpReminderAt')} />
          </div>

          {mutation.isError && (
            <Alert variant="destructive">
              {mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong.'}
            </Alert>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => handleOpenChange(false)} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive" loading={isSubmitting || mutation.isPending}>
              Mark as lost
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
