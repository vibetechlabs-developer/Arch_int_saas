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
import { CompanyMemberCombobox } from '@/components/projects/CompanyMemberCombobox';
import { validateDocumentFile, ACCEPTED_DOCUMENT_FILE_TYPES } from '@/components/documents/RegisterDocumentSheet';
import { ApiError } from '@/lib/api/client';
import { createExpense, updateExpense, uploadExpenseReceipt, type Expense } from '@/lib/api/expenses';
import { expenseKeys } from '@/lib/queryKeys';

const decimalOptional = z
  .string()
  .optional()
  .refine((v) => !v || /^\d+(\.\d+)?$/.test(v), 'Enter a valid non-negative number');

const formSchema = z.object({
  category: z.string().optional(),
  vendor: z.string().optional(),
  amount: z
    .string()
    .min(1, 'Amount is required')
    .refine((v) => /^\d+(\.\d+)?$/.test(v), 'Enter a valid amount')
    .refine((v) => !/^0(\.0+)?$/.test(v), 'Amount must be greater than zero'),
  tax: decimalOptional,
  date: z.string().min(1, 'Expense date is required'),
  paymentMethod: z.string().optional(),
  receiptUrl: z.string().url('Enter a valid URL').optional().or(z.literal('')),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof formSchema>;

const EMPTY_VALUES: FormValues = { category: '', vendor: '', amount: '', tax: '', date: '', paymentMethod: '', receiptUrl: '', notes: '' };

export interface ExpenseFormSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  expense?: Expense;
}

// The same sheet drives create and edit — unlike BOQItemFormSheet's
// product reference, an Expense's employee IS mutable via PATCH while
// still draft (confirmed in ExpenseService.update_expense), so the
// employee combobox stays interactive in edit mode too, not static.
//
// Receipt: primary experience is a real file upload to private storage
// (BE-078), with "Use a URL instead" as an explicit, secondary mode —
// mirrors RegisterDocumentSheet's pattern exactly. Leaving the receipt
// picker untouched on an edit never disturbs an existing receipt (file-
// or URL-based) — receiptStorageKey is only ever included in the save
// payload when a new file was actually uploaded this session.
export function ExpenseFormSheet({ open, onOpenChange, projectId, expense }: ExpenseFormSheetProps) {
  const isEdit = !!expense;
  const queryClient = useQueryClient();
  const [employeeId, setEmployeeId] = useState<string | null>(null);
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
    if (!open) return;
    setReceiptUrlMode(false);
    setSelectedReceiptFile(null);
    setReceiptFileError(null);
    if (expense) {
      reset({
        category: expense.category,
        vendor: expense.vendor,
        amount: expense.amount,
        tax: expense.tax,
        date: expense.date,
        paymentMethod: expense.paymentMethod,
        receiptUrl: expense.receiptUrl,
        notes: expense.notes,
      });
      setEmployeeId(expense.employeeId);
    } else {
      reset(EMPTY_VALUES);
      setEmployeeId(null);
    }
  }, [open, expense, reset]);

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      let receiptStorageKey: string | undefined;
      let receiptUrl = values.receiptUrl || '';
      if (!receiptUrlMode && selectedReceiptFile) {
        const uploaded = await uploadExpenseReceipt(selectedReceiptFile);
        receiptStorageKey = uploaded.key;
        receiptUrl = '';
      }

      const payload = {
        category: values.category || '',
        vendor: values.vendor || '',
        employeeId,
        amount: values.amount,
        tax: values.tax || '0',
        date: values.date,
        paymentMethod: values.paymentMethod || '',
        receiptUrl,
        ...(receiptStorageKey ? { receiptStorageKey } : {}),
        notes: values.notes || '',
      };
      return isEdit ? updateExpense(expense!.id, payload) : createExpense(projectId, payload);
    },
    onSuccess: (saved) => {
      queryClient.setQueryData(expenseKeys.detail(saved.id), saved);
      queryClient.invalidateQueries({ queryKey: expenseKeys.project(projectId) });
      toast.success(isEdit ? 'Expense updated' : 'Expense added');
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
          <SheetTitle>{isEdit ? 'Edit expense' : 'Add expense'}</SheetTitle>
          <SheetDescription>
            {isEdit ? 'Update this draft expense.' : 'Record a project cost. It starts as a draft until submitted.'}
          </SheetDescription>
        </SheetHeader>

        <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="flex flex-1 flex-col gap-5" noValidate>
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="expense-category">Category</Label>
              <Input id="expense-category" {...register('category')} />
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="expense-vendor">Vendor</Label>
              <Input id="expense-vendor" {...register('vendor')} />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Employee</Label>
            <CompanyMemberCombobox value={employeeId} onSelect={setEmployeeId} />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="expense-amount">Amount</Label>
              <Input id="expense-amount" inputMode="decimal" invalid={!!errors.amount} {...register('amount')} />
              {errors.amount && <p className="text-small text-danger-text">{errors.amount.message}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="expense-tax">Tax</Label>
              <Input id="expense-tax" inputMode="decimal" placeholder="0.00" invalid={!!errors.tax} {...register('tax')} />
              {errors.tax && <p className="text-small text-danger-text">{errors.tax.message}</p>}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="expense-date">Expense date</Label>
              <Input id="expense-date" type="date" invalid={!!errors.date} {...register('date')} />
              {errors.date && <p className="text-small text-danger-text">{errors.date.message}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="expense-payment-method">Payment method</Label>
              <Input id="expense-payment-method" placeholder="e.g. Bank transfer" {...register('paymentMethod')} />
            </div>
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
                    <p className="text-small text-text-secondary">
                      {expense?.hasStoredReceipt ? 'Replace the uploaded receipt' : 'Attach a receipt (optional)'}
                    </p>
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
                    {selectedReceiptFile || expense?.hasStoredReceipt ? 'Choose a different file' : 'Choose File'}
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
                  id="expense-receipt-url"
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
            <Label htmlFor="expense-notes">Notes</Label>
            <Textarea id="expense-notes" rows={2} {...register('notes')} />
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
              {isEdit ? 'Save changes' : 'Add expense'}
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
