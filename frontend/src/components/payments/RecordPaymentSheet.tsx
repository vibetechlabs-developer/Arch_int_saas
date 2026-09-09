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
import { createPayment } from '@/lib/api/payments';
import type { Invoice } from '@/lib/api/invoices';
import { invoiceKeys, paymentKeys } from '@/lib/queryKeys';

const formSchema = z.object({
  paymentDate: z.string().min(1, 'Payment date is required'),
  amount: z
    .string()
    .min(1, 'Amount is required')
    .refine((v) => /^\d+(\.\d+)?$/.test(v), 'Enter a valid amount')
    .refine((v) => !/^0(\.0+)?$/.test(v), 'Amount must be greater than zero'),
  method: z.string().optional(),
  referenceNumber: z.string().optional(),
  receiptUrl: z.string().url('Enter a valid URL').optional().or(z.literal('')),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof formSchema>;

const EMPTY_VALUES: FormValues = { paymentDate: '', amount: '', method: '', referenceNumber: '', receiptUrl: '', notes: '' };

export interface RecordPaymentSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  invoice: Invoice;
}

// The backend intentionally allows overpayment (BE-074: no upper bound in
// PaymentService.create_payment, unchanged by exposing paidAmount/
// outstandingAmount elsewhere) — this form never blocks or caps an
// entered amount against the invoice's outstanding balance, even though
// that figure is now visible on the page. `method` is a free text field
// with no backend enum, so it's a plain Input, not a Select of invented
// options.
export function RecordPaymentSheet({ open, onOpenChange, invoice }: RecordPaymentSheetProps) {
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(formSchema), defaultValues: EMPTY_VALUES });

  useEffect(() => {
    if (open) reset(EMPTY_VALUES);
  }, [open, reset]);

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      createPayment(invoice.id, {
        paymentDate: values.paymentDate,
        amount: values.amount,
        method: values.method || '',
        referenceNumber: values.referenceNumber || '',
        receiptUrl: values.receiptUrl || '',
        notes: values.notes || '',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: paymentKeys.invoice(invoice.id) });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(invoice.id) });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.project(invoice.projectId) });
      toast.success('Payment recorded');
      onOpenChange(false);
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : 'Something went wrong. Please try again.');
    },
  });

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Record payment</SheetTitle>
          <SheetDescription>Record a payment received against {invoice.invoiceNumber}.</SheetDescription>
        </SheetHeader>

        <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="flex flex-1 flex-col gap-5" noValidate>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="payment-date">Payment date</Label>
              <Input id="payment-date" type="date" invalid={!!errors.paymentDate} {...register('paymentDate')} />
              {errors.paymentDate && <p className="text-small text-danger-text">{errors.paymentDate.message}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="payment-amount">Amount</Label>
              <Input id="payment-amount" inputMode="decimal" invalid={!!errors.amount} {...register('amount')} />
              {errors.amount && <p className="text-small text-danger-text">{errors.amount.message}</p>}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="payment-method">Method</Label>
            <Input id="payment-method" placeholder="e.g. Bank transfer" {...register('method')} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="payment-reference">Reference</Label>
            <Input id="payment-reference" {...register('referenceNumber')} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="payment-receipt-url">Receipt URL</Label>
            <Input id="payment-receipt-url" invalid={!!errors.receiptUrl} {...register('receiptUrl')} />
            {errors.receiptUrl && <p className="text-small text-danger-text">{errors.receiptUrl.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="payment-notes">Notes</Label>
            <Textarea id="payment-notes" rows={2} {...register('notes')} />
          </div>

          {mutation.isError && (
            <Alert variant="destructive">
              {mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong.'}
            </Alert>
          )}

          <div className="mt-auto flex justify-end gap-2 border-t border-border-subtle pt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={mutation.isPending}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={mutation.isPending}>
              Record payment
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
