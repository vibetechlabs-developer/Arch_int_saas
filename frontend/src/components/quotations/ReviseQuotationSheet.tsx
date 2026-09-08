import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert } from '@/components/ui/alert';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { ApiError } from '@/lib/api/client';
import { reviseQuotation, type Quotation } from '@/lib/api/quotations';
import { quotationKeys } from '@/lib/queryKeys';

interface FormValues {
  validUntil: string;
  terms: string;
  notes: string;
}

export interface ReviseQuotationSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  quotation: Quotation;
}

// Revise creates a new row (a new version of the same quote number) — it
// never mutates the quotation being revised. Line items aren't editable
// here: they always carry over as a fresh BOQ snapshot server-side, the
// same as create. There is no status precondition on this endpoint (only
// "must be the latest version"), which is why Revise is always available
// regardless of the current quotation's status.
export function ReviseQuotationSheet({ open, onOpenChange, quotation }: ReviseQuotationSheetProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm<FormValues>({
    defaultValues: { validUntil: quotation.validUntil ?? '', terms: quotation.terms, notes: quotation.notes },
  });

  useEffect(() => {
    if (open) {
      reset({ validUntil: quotation.validUntil ?? '', terms: quotation.terms, notes: quotation.notes });
    }
  }, [open, quotation, reset]);

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      reviseQuotation(quotation.id, {
        validUntil: values.validUntil || null,
        terms: values.terms,
        notes: values.notes,
      }),
    onSuccess: (revised) => {
      queryClient.setQueryData(quotationKeys.detail(revised.id), revised);
      queryClient.invalidateQueries({ queryKey: quotationKeys.detail(quotation.id) });
      queryClient.invalidateQueries({ queryKey: quotationKeys.project(quotation.projectId) });
      toast.success(`${revised.quoteNumber} v${revised.version} created`);
      onOpenChange(false);
      navigate(`/quotations/${revised.id}`);
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : 'Something went wrong. Please try again.');
    },
  });

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Revise {quotation.quoteNumber}</SheetTitle>
          <SheetDescription>
            This creates version {quotation.version + 1}, rebuilt from the project's current BOQ. Version{' '}
            {quotation.version} stays exactly as it is for the record.
          </SheetDescription>
        </SheetHeader>

        <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="flex flex-1 flex-col gap-5" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="revise-valid-until">Valid until</Label>
            <Input id="revise-valid-until" type="date" {...register('validUntil')} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="revise-terms">Terms</Label>
            <Textarea id="revise-terms" rows={3} {...register('terms')} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="revise-notes">Notes</Label>
            <Textarea id="revise-notes" rows={3} {...register('notes')} />
          </div>

          {mutation.isError && (
            <Alert variant="destructive">
              {mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong.'}
            </Alert>
          )}

          <div className="mt-auto flex justify-end gap-2 border-t border-border-subtle pt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              Create revision
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
