import { useEffect, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { CategoryCombobox } from '@/components/products/CategoryCombobox';
import { SubcategoryCombobox } from '@/components/products/SubcategoryCombobox';
import { ProductThumbnail } from '@/components/products/ProductThumbnail';
import { ApiError } from '@/lib/api/client';
import {
  createProduct,
  updateProduct,
  PRODUCT_UNITS,
  type Product,
  type ProductMutableInput,
  type ProductStatus,
  type ProductUnit,
} from '@/lib/api/products';
import { productKeys } from '@/lib/queryKeys';

const decimalField = z
  .string()
  .optional()
  .refine((v) => !v || /^\d+(\.\d+)?$/.test(v), 'Enter a valid non-negative number');

const productSchema = z.object({
  name: z.string().trim().min(1, 'Product name is required').max(255),
  imageUrl: z.string().url('Enter a valid image URL').optional().or(z.literal('')),
  defaultCost: decimalField,
  defaultSellingRate: decimalField,
  taxRate: decimalField,
});

type ProductFormValues = z.infer<typeof productSchema>;

const EMPTY_VALUES: ProductFormValues = { name: '', imageUrl: '', defaultCost: '', defaultSellingRate: '', taxRate: '' };

export interface ProductFormSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  product?: Product;
  onSaved?: (product: Product) => void;
}

// Same Sheet drives create and edit. Subcategory is required to create a
// product but is not editable afterward (no documented reassignment
// endpoint) — the Category/Subcategory combobox pair only appears in
// create mode; edit mode shows them as static fields instead.
export function ProductFormSheet({ open, onOpenChange, product, onSaved }: ProductFormSheetProps) {
  const isEdit = !!product;
  const queryClient = useQueryClient();
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [subcategoryId, setSubcategoryId] = useState<string | null>(null);
  const [subcategoryError, setSubcategoryError] = useState<string | null>(null);
  const [unit, setUnit] = useState<ProductUnit | ''>('');
  const [statusValue, setStatusValue] = useState<ProductStatus>('active');

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ProductFormValues>({ resolver: zodResolver(productSchema), defaultValues: EMPTY_VALUES });

  const imageUrl = watch('imageUrl');

  useEffect(() => {
    if (!open) return;
    setSubcategoryError(null);
    if (product) {
      reset({
        name: product.name,
        imageUrl: product.imageUrl,
        defaultCost: product.defaultCost ?? '',
        defaultSellingRate: product.defaultSellingRate ?? '',
        taxRate: product.taxRate ?? '',
      });
      setCategoryId(product.categoryId);
      setSubcategoryId(product.subcategoryId);
      setUnit(product.unit);
      setStatusValue(product.status);
    } else {
      reset(EMPTY_VALUES);
      setCategoryId(null);
      setSubcategoryId(null);
      setUnit('');
      setStatusValue('active');
    }
  }, [open, product, reset]);

  const mutation = useMutation({
    mutationFn: (values: ProductFormValues) => {
      const mutableInput: ProductMutableInput = {
        name: values.name,
        imageUrl: values.imageUrl || '',
        unit: unit || '',
        defaultCost: values.defaultCost || null,
        defaultSellingRate: values.defaultSellingRate || null,
        taxRate: values.taxRate || null,
        status: statusValue,
      };
      return isEdit
        ? updateProduct(product!.id, mutableInput)
        : createProduct({ ...mutableInput, subcategoryId: subcategoryId! });
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: productKeys.lists() });
      if (isEdit) queryClient.invalidateQueries({ queryKey: productKeys.detail(saved.id) });
      toast.success(isEdit ? 'Product updated' : 'Product created');
      onOpenChange(false);
      onSaved?.(saved);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.code === 'VALIDATION_ERROR') {
        for (const detail of error.details) {
          if (detail.field === 'subcategoryId') {
            setSubcategoryError(detail.issue);
            continue;
          }
          if (detail.field in EMPTY_VALUES) {
            setError(detail.field as keyof ProductFormValues, { message: detail.issue });
          }
        }
        return;
      }
      toast.error(error instanceof ApiError ? error.message : 'Something went wrong. Please try again.');
    },
  });

  const onSubmit = (values: ProductFormValues) => {
    if (!isEdit && !subcategoryId) {
      setSubcategoryError('Select a subcategory for this product.');
      return;
    }
    mutation.mutate(values);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{isEdit ? 'Edit product' : 'New product'}</SheetTitle>
          <SheetDescription>
            {isEdit ? 'Update this product’s catalog details.' : 'Add a new product to the catalog.'}
          </SheetDescription>
        </SheetHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-1 flex-col gap-5" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="product-name">Product name</Label>
            <Input id="product-name" invalid={!!errors.name} {...register('name')} />
            {errors.name && <p className="text-small text-danger-text">{errors.name.message}</p>}
          </div>

          {isEdit ? (
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <Label>Category</Label>
                <p className="rounded-md border border-border-subtle bg-surface-secondary px-3 py-2 text-body text-text-secondary">
                  {product!.categoryName}
                </p>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Subcategory</Label>
                <p className="rounded-md border border-border-subtle bg-surface-secondary px-3 py-2 text-body text-text-secondary">
                  {product!.subcategoryName}
                </p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <Label>Category</Label>
                <CategoryCombobox
                  value={categoryId}
                  onSelect={(id) => {
                    setCategoryId(id);
                    setSubcategoryId(null);
                    setSubcategoryError(null);
                  }}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Subcategory</Label>
                <SubcategoryCombobox
                  categoryId={categoryId}
                  value={subcategoryId}
                  onSelect={(id) => {
                    setSubcategoryId(id);
                    setSubcategoryError(null);
                  }}
                  invalid={!!subcategoryError}
                />
              </div>
              {subcategoryError && <p className="col-span-2 -mt-2 text-small text-danger-text">{subcategoryError}</p>}
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="product-image-url">Image URL</Label>
            <Input id="product-image-url" placeholder="https://…" invalid={!!errors.imageUrl} {...register('imageUrl')} />
            {errors.imageUrl && <p className="text-small text-danger-text">{errors.imageUrl.message}</p>}
            {imageUrl && (
              <div className="mt-1">
                <ProductThumbnail imageUrl={imageUrl} alt="Preview" size="lg" />
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <Label>Unit</Label>
              <Select value={unit || '__none__'} onValueChange={(v) => setUnit(v === '__none__' ? '' : (v as ProductUnit))}>
                <SelectTrigger>
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
            </div>
            <div className="flex flex-col gap-1.5">
              <Label>Status</Label>
              <Select value={statusValue} onValueChange={(v) => setStatusValue(v as ProductStatus)}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="product-default-cost">Default cost</Label>
              <Input
                id="product-default-cost"
                inputMode="decimal"
                placeholder="0.00"
                invalid={!!errors.defaultCost}
                {...register('defaultCost')}
              />
              {errors.defaultCost && <p className="text-small text-danger-text">{errors.defaultCost.message}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="product-selling-rate">Default selling rate</Label>
              <Input
                id="product-selling-rate"
                inputMode="decimal"
                placeholder="0.00"
                invalid={!!errors.defaultSellingRate}
                {...register('defaultSellingRate')}
              />
              {errors.defaultSellingRate && (
                <p className="text-small text-danger-text">{errors.defaultSellingRate.message}</p>
              )}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="product-tax-rate">Tax rate (%)</Label>
            <Input
              id="product-tax-rate"
              inputMode="decimal"
              placeholder="0.00"
              invalid={!!errors.taxRate}
              {...register('taxRate')}
            />
            {errors.taxRate && <p className="text-small text-danger-text">{errors.taxRate.message}</p>}
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
              {isEdit ? 'Save changes' : 'Create product'}
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
