import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert } from '@/components/ui/alert';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { FinancialSummary } from '@/components/common/FinancialSummary';
import { ApiError } from '@/lib/api/client';
import { getBOQSummary } from '@/lib/api/boq';
import { createQuotation } from '@/lib/api/quotations';
import { boqKeys, quotationKeys } from '@/lib/queryKeys';

interface FormValues {
  validUntil: string;
  terms: string;
  notes: string;
}

const EMPTY_VALUES: FormValues = { validUntil: '', terms: '', notes: '' };

export interface CreateQuotationSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
}

// Creates a quotation from the project's current BOQ — the documented
// primary flow (omitting `items` from the request signals the backend to
// snapshot the BOQ's includible items and its computed summary verbatim).
// Manual line-item entry is a separate, larger feature not built here.
// Every field below is genuinely optional per the real contract — there
// is no client-side validation rule to enforce beyond the date input's
// own native format.
export function CreateQuotationSheet({ open, onOpenChange, projectId }: CreateQuotationSheetProps) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const { data: boqSummary, isLoading: summaryLoading } = useQuery({
    queryKey: boqKeys.summary(projectId),
    queryFn: () => getBOQSummary(projectId),
    enabled: open,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { isSubmitting },
  } = useForm<FormValues>({ defaultValues: EMPTY_VALUES });

  useEffect(() => {
    if (open) reset(EMPTY_VALUES);
  }, [open, reset]);

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      createQuotation(projectId, {
        validUntil: values.validUntil || null,
        terms: values.terms,
        notes: values.notes,
      }),
    onSuccess: (quotation) => {
      queryClient.invalidateQueries({ queryKey: quotationKeys.project(projectId) });
      toast.success(`${quotation.quoteNumber} created`);
      onOpenChange(false);
      navigate(`/quotations/${quotation.id}`);
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : 'Something went wrong. Please try again.');
    },
  });

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Create quotation</SheetTitle>
          <SheetDescription>
            This creates a snapshot of the project's current BOQ — its items and totals are copied as they stand
            right now. Later BOQ changes won't affect this quotation.
          </SheetDescription>
        </SheetHeader>

        <div className="flex flex-col gap-1.5 rounded-md border border-border-subtle bg-surface-secondary p-3">
          <span className="text-caption text-text-tertiary">This quotation will use the BOQ's current totals</span>
          <FinancialSummary
            subtotal={boqSummary?.subtotal}
            discount={boqSummary?.discount}
            tax={boqSummary?.tax}
            total={boqSummary?.total}
            loading={summaryLoading}
          />
        </div>

        <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="flex flex-1 flex-col gap-5" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="quotation-valid-until">Valid until</Label>
            <Input id="quotation-valid-until" type="date" {...register('validUntil')} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="quotation-terms">Terms</Label>
            <Textarea id="quotation-terms" rows={3} {...register('terms')} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="quotation-notes">Notes</Label>
            <Textarea id="quotation-notes" rows={3} {...register('notes')} />
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
              Create quotation
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
