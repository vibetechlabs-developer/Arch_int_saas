import { useFieldArray, Controller, type Control, type FieldErrors, type UseFormRegister } from 'react-hook-form';
import { z } from 'zod';
import { Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { PRODUCT_UNITS } from '@/lib/api/products';

const decimalOptional = z
  .string()
  .optional()
  .refine((v) => !v || /^-?\d+(\.\d+)?$/.test(v), 'Enter a valid number');

const itemRowSchema = z.object({
  description: z.string().trim().min(1, 'Description is required'),
  quantity: z
    .string()
    .min(1, 'Quantity is required')
    .refine((v) => /^\d+(\.\d+)?$/.test(v), 'Enter a valid quantity')
    .refine((v) => !/^0(\.0+)?$/.test(v), 'Quantity must be greater than zero'),
  unit: z.string().optional(),
  rate: z.string().min(1, 'Rate is required').refine((v) => /^-?\d+(\.\d+)?$/.test(v), 'Enter a valid rate'),
});

// Shared by ManualInvoiceForm (create, ad hoc path) and EditInvoiceSheet
// (draft-only edit) — both submit the exact same shape to the backend
// (a full `items` array replacement plus invoice-level discount/tax/
// dueDate/paymentTerms/notes), so one schema and one form component
// serves both instead of duplicating the line-item editor twice.
export const invoiceLineFormSchema = z.object({
  items: z.array(itemRowSchema).min(1, 'Add at least one line item'),
  discount: decimalOptional,
  tax: decimalOptional,
  dueDate: z.string().optional(),
  paymentTerms: z.string().optional(),
  notes: z.string().optional(),
});

export type InvoiceLineFormValues = z.infer<typeof invoiceLineFormSchema>;

export const EMPTY_INVOICE_LINE_ROW = { description: '', quantity: '', unit: '', rate: '' };

export const EMPTY_INVOICE_LINE_VALUES: InvoiceLineFormValues = {
  items: [EMPTY_INVOICE_LINE_ROW],
  discount: '',
  tax: '',
  dueDate: '',
  paymentTerms: '',
  notes: '',
};

export interface InvoiceLineItemFieldsProps {
  control: Control<InvoiceLineFormValues>;
  register: UseFormRegister<InvoiceLineFormValues>;
  errors: FieldErrors<InvoiceLineFormValues>;
}

// Line items are never previewed with a computed amount here — that
// figure is server-computed (quantity × rate) and only ever rendered,
// post-save, from the backend's own response. No frontend arithmetic.
export function InvoiceLineItemFields({ control, register, errors }: InvoiceLineItemFieldsProps) {
  const { fields, append, remove } = useFieldArray({ control, name: 'items' });
  const itemsRootError = errors.items?.root?.message ?? (typeof errors.items?.message === 'string' ? errors.items.message : undefined);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <Label>Line items</Label>
        <Button type="button" variant="outline" size="sm" onClick={() => append(EMPTY_INVOICE_LINE_ROW)}>
          <Plus />
          Add line
        </Button>
      </div>
      {itemsRootError && <p className="text-small text-danger-text">{itemsRootError}</p>}

      <div className="flex flex-col gap-3">
        {fields.map((field, index) => {
          const rowError = errors.items?.[index];
          return (
            <div key={field.id} className="flex flex-col gap-3 rounded-lg border border-border-subtle p-3">
              <div className="flex items-start gap-2">
                <div className="flex flex-1 flex-col gap-1.5">
                  <Label htmlFor={`invoice-item-description-${index}`}>Description</Label>
                  <Input
                    id={`invoice-item-description-${index}`}
                    invalid={!!rowError?.description}
                    {...register(`items.${index}.description`)}
                  />
                  {rowError?.description && <p className="text-small text-danger-text">{rowError.description.message}</p>}
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="mt-6"
                  aria-label={`Remove line ${index + 1}`}
                  disabled={fields.length <= 1}
                  onClick={() => remove(index)}
                >
                  <Trash2 className="size-4 text-danger-text" />
                </Button>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor={`invoice-item-quantity-${index}`}>Quantity</Label>
                  <Input
                    id={`invoice-item-quantity-${index}`}
                    inputMode="decimal"
                    invalid={!!rowError?.quantity}
                    {...register(`items.${index}.quantity`)}
                  />
                  {rowError?.quantity && <p className="text-small text-danger-text">{rowError.quantity.message}</p>}
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor={`invoice-item-unit-${index}`}>Unit</Label>
                  <Controller
                    control={control}
                    name={`items.${index}.unit`}
                    render={({ field: controllerField }) => (
                      <Select
                        value={controllerField.value || '__none__'}
                        onValueChange={(v) => controllerField.onChange(v === '__none__' ? '' : v)}
                      >
                        <SelectTrigger id={`invoice-item-unit-${index}`}>
                          <SelectValue placeholder="Unspecified" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="__none__">Unspecified</SelectItem>
                          {PRODUCT_UNITS.map((u) => (
                            <SelectItem key={u.value} value={u.value}>
                              {u.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor={`invoice-item-rate-${index}`}>Rate</Label>
                  <Input id={`invoice-item-rate-${index}`} inputMode="decimal" invalid={!!rowError?.rate} {...register(`items.${index}.rate`)} />
                  {rowError?.rate && <p className="text-small text-danger-text">{rowError.rate.message}</p>}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="invoice-discount">Discount</Label>
          <Input id="invoice-discount" inputMode="decimal" placeholder="0.00" invalid={!!errors.discount} {...register('discount')} />
          {errors.discount && <p className="text-small text-danger-text">{errors.discount.message}</p>}
        </div>
        <div className="flex flex-col gap-1.5">
          <Label htmlFor="invoice-tax">Tax</Label>
          <Input id="invoice-tax" inputMode="decimal" placeholder="0.00" invalid={!!errors.tax} {...register('tax')} />
          {errors.tax && <p className="text-small text-danger-text">{errors.tax.message}</p>}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="invoice-due-date">Due date</Label>
        <Input id="invoice-due-date" type="date" {...register('dueDate')} />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="invoice-payment-terms">Payment terms</Label>
        <Textarea id="invoice-payment-terms" rows={2} {...register('paymentTerms')} />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="invoice-notes">Notes</Label>
        <Textarea id="invoice-notes" rows={2} {...register('notes')} />
      </div>
    </div>
  );
}
