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
import { createExpense, updateExpense, type Expense } from '@/lib/api/expenses';
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
export function ExpenseFormSheet({ open, onOpenChange, projectId, expense }: ExpenseFormSheetProps) {
  const isEdit = !!expense;
  const queryClient = useQueryClient();
  const [employeeId, setEmployeeId] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(formSchema), defaultValues: EMPTY_VALUES });

  useEffect(() => {
    if (!open) return;
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
    mutationFn: (values: FormValues) => {
      const payload = {
        category: values.category || '',
        vendor: values.vendor || '',
        employeeId,
        amount: values.amount,
        tax: values.tax || '0',
        date: values.date,
        paymentMethod: values.paymentMethod || '',
        receiptUrl: values.receiptUrl || '',
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

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="expense-receipt-url">Receipt URL</Label>
            <Input id="expense-receipt-url" invalid={!!errors.receiptUrl} {...register('receiptUrl')} />
            {errors.receiptUrl && <p className="text-small text-danger-text">{errors.receiptUrl.message}</p>}
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
