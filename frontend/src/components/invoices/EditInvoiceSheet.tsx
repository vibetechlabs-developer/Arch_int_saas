import { useEffect } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Alert } from '@/components/ui/alert';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { ApiError } from '@/lib/api/client';
import { updateInvoice, type Invoice } from '@/lib/api/invoices';
import type { ProductUnit } from '@/lib/api/products';
import { invoiceKeys } from '@/lib/queryKeys';
import { InvoiceLineItemFields, invoiceLineFormSchema, type InvoiceLineFormValues } from './InvoiceLineItemFields';

export interface EditInvoiceSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  invoice: Invoice;
}

// PATCH /invoices/{id} edits a draft invoice's items/discount/tax/
// dueDate/paymentTerms/notes regardless of whether it originated from a
// quotation or ad hoc — the backend treats both origins identically once
// created, so this single form covers both. Only ever shown for a
// status === 'draft' invoice (enforced 409 otherwise).
export function EditInvoiceSheet({ open, onOpenChange, invoice }: EditInvoiceSheetProps) {
  const queryClient = useQueryClient();

  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<InvoiceLineFormValues>({ resolver: zodResolver(invoiceLineFormSchema) });

  useEffect(() => {
    if (!open) return;
    reset({
      items: invoice.items.length
        ? invoice.items.map((item) => ({ description: item.description, quantity: item.quantity, unit: item.unit, rate: item.rate }))
        : [{ description: '', quantity: '', unit: '', rate: '' }],
      discount: invoice.discount,
      tax: invoice.tax,
      dueDate: invoice.dueDate ?? '',
      paymentTerms: invoice.paymentTerms,
      notes: invoice.notes,
    });
  }, [open, invoice, reset]);

  const mutation = useMutation({
    mutationFn: (values: InvoiceLineFormValues) =>
      updateInvoice(invoice.id, {
        items: values.items.map((item) => ({
          description: item.description,
          quantity: item.quantity,
          unit: (item.unit || undefined) as ProductUnit | undefined,
          rate: item.rate,
        })),
        discount: values.discount || '0',
        tax: values.tax || '0',
        dueDate: values.dueDate || null,
        paymentTerms: values.paymentTerms ?? '',
        notes: values.notes ?? '',
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(invoiceKeys.detail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: invoiceKeys.project(updated.projectId) });
      toast.success('Invoice updated');
      onOpenChange(false);
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : 'Something went wrong. Please try again.');
    },
  });

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>Edit {invoice.invoiceNumber}</SheetTitle>
          <SheetDescription>Only a draft invoice can be edited. Saving replaces the line items shown below.</SheetDescription>
        </SheetHeader>

        <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="flex flex-1 flex-col gap-5" noValidate>
          <InvoiceLineItemFields control={control} register={register} errors={errors} />

          {mutation.isError && (
            <Alert variant="destructive">{mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong.'}</Alert>
          )}

          <div className="mt-auto flex justify-end gap-2 border-t border-border-subtle pt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              Save changes
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
