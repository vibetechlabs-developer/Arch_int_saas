import { useEffect, useRef, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { FileUp, Link2, Paperclip, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert } from '@/components/ui/alert';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { validateDocumentFile, ACCEPTED_DOCUMENT_FILE_TYPES } from '@/components/documents/RegisterDocumentSheet';
import { ApiError } from '@/lib/api/client';
import { createPayment, uploadPaymentReceipt } from '@/lib/api/payments';
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
//
// Receipt: primary experience is a real file upload to private storage
// (BE-078), with "Use a URL instead" as an explicit, secondary mode —
// mirrors RegisterDocumentSheet's pattern exactly. Payment has no update
// endpoint, so this is the only moment a receipt can ever be attached.
export function RecordPaymentSheet({ open, onOpenChange, invoice }: RecordPaymentSheetProps) {
  const queryClient = useQueryClient();
  const [receiptUrlMode, setReceiptUrlMode] = useState(false);
  const [selectedReceiptFile, setSelectedReceiptFile] = useState<File | null>(null);
  const [receiptFileError, setReceiptFileError] = useState<string | null>(null);
  const receiptInputRef = useRef<HTMLInputElement>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(formSchema), defaultValues: EMPTY_VALUES });

  useEffect(() => {
    if (open) {
      reset(EMPTY_VALUES);
      setReceiptUrlMode(false);
      setSelectedReceiptFile(null);
      setReceiptFileError(null);
    }
  }, [open, reset]);

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      let receiptStorageKey: string | undefined;
      let receiptUrl = values.receiptUrl || '';
      if (!receiptUrlMode && selectedReceiptFile) {
        const uploaded = await uploadPaymentReceipt(selectedReceiptFile);
        receiptStorageKey = uploaded.key;
        receiptUrl = '';
      }

      return createPayment(invoice.id, {
        paymentDate: values.paymentDate,
        amount: values.amount,
        method: values.method || '',
        referenceNumber: values.referenceNumber || '',
        receiptUrl,
        ...(receiptStorageKey ? { receiptStorageKey } : {}),
        notes: values.notes || '',
      });
    },
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

  const handleReceiptFileChange = (files: FileList | null) => {
    const file = files?.[0];
    if (!file) return;
    const validationMessage = validateDocumentFile(file);
    if (validationMessage) {
      setReceiptFileError(validationMessage);
      return;
    }
    setReceiptFileError(null);
    setSelectedReceiptFile(file);
  };

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

          <div className="flex flex-col gap-2">
            <Label>Receipt</Label>
            {!receiptUrlMode ? (
              <div className="flex flex-col gap-2">
                <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border-subtle p-4">
                  {selectedReceiptFile ? (
                    <div className="flex w-full items-center justify-between gap-2 rounded-md border border-border-subtle bg-surface-secondary px-3 py-2">
                      <span className="flex items-center gap-2 truncate text-small text-text-primary">
                        <Paperclip className="size-4 shrink-0 text-text-tertiary" />
                        {selectedReceiptFile.name}
                      </span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        disabled={mutation.isPending}
                        onClick={() => {
                          setSelectedReceiptFile(null);
                          setReceiptFileError(null);
                        }}
                      >
                        <X />
                      </Button>
                    </div>
                  ) : (
                    <p className="text-small text-text-secondary">Attach a receipt (optional)</p>
                  )}
                  <input
                    ref={receiptInputRef}
                    type="file"
                    accept={ACCEPTED_DOCUMENT_FILE_TYPES.join(',')}
                    className="hidden"
                    aria-label="Receipt file"
                    disabled={mutation.isPending}
                    onChange={(e) => {
                      handleReceiptFileChange(e.target.files);
                      e.target.value = '';
                    }}
                  />
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={mutation.isPending}
                    onClick={() => receiptInputRef.current?.click()}
                  >
                    <FileUp />
                    {selectedReceiptFile ? 'Choose a different file' : 'Choose File'}
                  </Button>
                </div>
                {receiptFileError && <p className="text-small text-danger-text">{receiptFileError}</p>}
                <Button
                  type="button"
                  variant="link"
                  size="sm"
                  className="w-fit px-0"
                  disabled={mutation.isPending}
                  onClick={() => setReceiptUrlMode(true)}
                >
                  <Link2 className="size-3.5" />
                  Use a URL instead
                </Button>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                <Input
                  id="payment-receipt-url"
                  placeholder="https://…"
                  invalid={!!errors.receiptUrl}
                  {...register('receiptUrl')}
                />
                {errors.receiptUrl && <p className="text-small text-danger-text">{errors.receiptUrl.message}</p>}
                <Button
                  type="button"
                  variant="link"
                  size="sm"
                  className="w-fit px-0"
                  disabled={mutation.isPending}
                  onClick={() => setReceiptUrlMode(false)}
                >
                  <FileUp className="size-3.5" />
                  Upload a file instead
                </Button>
              </div>
            )}
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
