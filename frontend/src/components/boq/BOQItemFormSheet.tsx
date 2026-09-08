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
import { Checkbox } from '@/components/ui/checkbox';
import { Alert } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { ProductCombobox } from '@/components/boq/ProductCombobox';
import { ApiError } from '@/lib/api/client';
import { PRODUCT_UNITS, type Product, type ProductUnit } from '@/lib/api/products';
import { createBOQItem, updateBOQItem, type BOQItem, type BOQItemMutableInput } from '@/lib/api/boq';
import { boqKeys } from '@/lib/queryKeys';

const decimalOptional = z
  .string()
  .optional()
  .refine((v) => !v || /^\d+(\.\d+)?$/.test(v), 'Enter a valid non-negative number');

const itemSchema = z.object({
  description: z.string().trim().max(500).optional(),
  quantity: z
    .string()
    .min(1, 'Quantity is required')
    .refine((v) => /^\d+(\.\d+)?$/.test(v), 'Enter a valid quantity'),
  rate: decimalOptional,
  discount: decimalOptional,
  tax: decimalOptional,
  notes: z.string().optional(),
});

type ItemFormValues = z.infer<typeof itemSchema>;

const EMPTY_VALUES: ItemFormValues = { description: '', quantity: '', rate: '', discount: '', tax: '', notes: '' };

export interface BOQItemFormSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  sectionId: string;
  item?: BOQItem;
}

// Product is not reassignable after create (no productId in the update
// contract) — edit mode shows it as static context, matching Project's
// client-in-edit-mode precedent. On create, selecting a product prefills
// description/unit/rate/tax from the product's own real values (the
// exact mapping BOQItemService itself uses when these fields are left
// blank) so the user sees what will be used and can still override it.
export function BOQItemFormSheet({ open, onOpenChange, projectId, sectionId, item }: BOQItemFormSheetProps) {
  const isEdit = !!item;
  const queryClient = useQueryClient();
  const [productId, setProductId] = useState<string | null>(null);
  const [productLabel, setProductLabel] = useState<string | null>(null);
  const [unit, setUnit] = useState<ProductUnit | ''>('');
  const [isOptional, setIsOptional] = useState(false);
  const [isAlternative, setIsAlternative] = useState(false);
  const [descriptionError, setDescriptionError] = useState<string | null>(null);
  const [unitError, setUnitError] = useState<string | null>(null);
  const [rateError, setRateError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ItemFormValues>({ resolver: zodResolver(itemSchema), defaultValues: EMPTY_VALUES });

  useEffect(() => {
    if (!open) return;
    setDescriptionError(null);
    setUnitError(null);
    setRateError(null);
    if (item) {
      reset({
        description: item.description,
        quantity: item.quantity,
        rate: item.rate,
        discount: item.discount,
        tax: item.tax,
        notes: item.notes,
      });
      setProductId(item.productId);
      setProductLabel(item.productName);
      setUnit(item.unit);
      setIsOptional(item.isOptional);
      setIsAlternative(item.isAlternative);
    } else {
      reset(EMPTY_VALUES);
      setProductId(null);
      setProductLabel(null);
      setUnit('');
      setIsOptional(false);
      setIsAlternative(false);
    }
  }, [open, item, reset]);

  const handleProductSelect = (product: Product) => {
    setProductId(product.id);
    setProductLabel(product.name);
    setDescriptionError(null);
    setUnitError(null);
    setRateError(null);
    // Real product values only — never fabricated. defaultCost is
    // deliberately not used here: the backend maps defaultSellingRate to
    // the item's rate, not defaultCost (confirmed in BOQItemService).
    setValue('description', product.name);
    setUnit(product.unit);
    if (product.defaultSellingRate) setValue('rate', product.defaultSellingRate);
    if (product.taxRate) setValue('tax', product.taxRate);
  };

  const mutation = useMutation({
    mutationFn: (values: ItemFormValues) => {
      const mutableInput: BOQItemMutableInput = {
        description: values.description || '',
        unit: unit || '',
        rate: values.rate || undefined,
        discount: values.discount || '0',
        tax: values.tax || '0',
        isOptional,
        isAlternative,
        notes: values.notes || '',
        quantity: values.quantity,
      };
      return isEdit
        ? updateBOQItem(item!.id, mutableInput)
        : createBOQItem(projectId, sectionId, { ...mutableInput, productId });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: boqKeys.project(projectId) });
      queryClient.invalidateQueries({ queryKey: boqKeys.summary(projectId) });
      toast.success(isEdit ? 'Item updated' : 'Item added');
      onOpenChange(false);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.code === 'VALIDATION_ERROR') {
        for (const detail of error.details) {
          if (detail.field === 'description') {
            setDescriptionError(detail.issue);
            continue;
          }
          if (detail.field === 'unit') {
            setUnitError(detail.issue);
            continue;
          }
          if (detail.field === 'rate') {
            setRateError(detail.issue);
            continue;
          }
          if (detail.field in EMPTY_VALUES) {
            setError(detail.field as keyof ItemFormValues, { message: detail.issue });
          }
        }
        return;
      }
      toast.error(error instanceof ApiError ? error.message : 'Something went wrong. Please try again.');
    },
  });

  const onSubmit = (values: ItemFormValues) => {
    // Mirrors the backend's own rule (confirmed in BOQItemService): free-
    // text items need a description, unit, and rate; a referenced product
    // supplies all three when left blank. Backend still validates
    // authoritatively — this only prevents an avoidable round trip.
    let hasError = false;
    if (!productId && !values.description?.trim()) {
      setDescriptionError('Description is required when no product is referenced.');
      hasError = true;
    }
    if (!productId && !unit) {
      setUnitError('Unit is required when no product is referenced.');
      hasError = true;
    }
    if (!productId && !values.rate) {
      setRateError('Rate is required when no product is referenced.');
      hasError = true;
    }
    if (hasError) return;
    mutation.mutate(values);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{isEdit ? 'Edit item' : 'Add item'}</SheetTitle>
          <SheetDescription>
            {isEdit ? 'Update this line item.' : 'Add a product or free-text line item to this section.'}
          </SheetDescription>
        </SheetHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-1 flex-col gap-5" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label>Product</Label>
            {isEdit ? (
              <p className="rounded-md border border-border-subtle bg-surface-secondary px-3 py-2 text-body text-text-secondary">
                {productLabel ?? 'Free-text item (no product referenced)'}
              </p>
            ) : (
              <ProductCombobox value={productId} onSelect={handleProductSelect} selectedLabel={productLabel} />
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="boq-item-description">Description</Label>
            <Input
              id="boq-item-description"
              invalid={!!errors.description || !!descriptionError}
              {...register('description')}
            />
            {(errors.description || descriptionError) && (
              <p className="text-small text-danger-text">{errors.description?.message ?? descriptionError}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="boq-item-quantity">Quantity</Label>
              <Input id="boq-item-quantity" inputMode="decimal" invalid={!!errors.quantity} {...register('quantity')} />
              {errors.quantity && <p className="text-small text-danger-text">{errors.quantity.message}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Unit</Label>
              <Select value={unit || '__none__'} onValueChange={(v) => { setUnit(v === '__none__' ? '' : (v as ProductUnit)); setUnitError(null); }}>
                <SelectTrigger className={unitError ? 'border-danger-text' : undefined}>
                  <SelectValue placeholder="Select a unit" />
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
              {unitError && <p className="text-small text-danger-text">{unitError}</p>}
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="boq-item-rate">Rate</Label>
              <Input
                id="boq-item-rate"
                inputMode="decimal"
                invalid={!!errors.rate || !!rateError}
                {...register('rate', { onChange: () => setRateError(null) })}
              />
              {(errors.rate || rateError) && <p className="text-small text-danger-text">{errors.rate?.message ?? rateError}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="boq-item-discount">Discount (%)</Label>
              <Input id="boq-item-discount" inputMode="decimal" placeholder="0.00" invalid={!!errors.discount} {...register('discount')} />
              {errors.discount && <p className="text-small text-danger-text">{errors.discount.message}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="boq-item-tax">Tax (%)</Label>
              <Input id="boq-item-tax" inputMode="decimal" placeholder="0.00" invalid={!!errors.tax} {...register('tax')} />
              {errors.tax && <p className="text-small text-danger-text">{errors.tax.message}</p>}
            </div>
          </div>

          <div className="flex flex-col gap-2.5">
            <label className="flex items-center gap-2 text-body text-text-primary">
              <Checkbox checked={isOptional} onCheckedChange={(v) => setIsOptional(!!v)} />
              Optional item
            </label>
            <label className="flex items-center gap-2 text-body text-text-primary">
              <Checkbox checked={isAlternative} onCheckedChange={(v) => setIsAlternative(!!v)} />
              Alternative item
            </label>
            <p className="text-caption text-text-tertiary">Optional and alternative items are excluded from the BOQ's totals.</p>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="boq-item-notes">Notes</Label>
            <Textarea id="boq-item-notes" rows={3} {...register('notes')} />
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
              {isEdit ? 'Save changes' : 'Add item'}
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
