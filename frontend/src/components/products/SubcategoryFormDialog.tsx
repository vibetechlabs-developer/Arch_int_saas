import { useEffect } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ApiError } from '@/lib/api/client';
import { createSubcategory, updateSubcategory, type ProductSubcategory } from '@/lib/api/productSubcategories';
import { subcategoryKeys } from '@/lib/queryKeys';

const schema = z.object({ name: z.string().trim().min(1, 'Subcategory name is required').max(255) });
type FormValues = z.infer<typeof schema>;

export interface SubcategoryFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  categoryId: string;
  subcategory?: ProductSubcategory;
}

export function SubcategoryFormDialog({ open, onOpenChange, categoryId, subcategory }: SubcategoryFormDialogProps) {
  const isEdit = !!subcategory;
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { name: '' } });

  useEffect(() => {
    if (open) reset({ name: subcategory?.name ?? '' });
  }, [open, subcategory, reset]);

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      isEdit ? updateSubcategory(subcategory!.id, values.name) : createSubcategory(categoryId, values.name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: subcategoryKeys.forCategory(categoryId) });
      toast.success(isEdit ? 'Subcategory updated' : 'Subcategory created');
      onOpenChange(false);
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : 'Something went wrong. Please try again.');
    },
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit subcategory' : 'New subcategory'}</DialogTitle>
          <DialogDescription>
            {isEdit ? 'Rename this subcategory.' : 'Add a new subcategory under this category.'}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="subcategory-name">Subcategory name</Label>
            <Input id="subcategory-name" invalid={!!errors.name} {...register('name')} />
            {errors.name && <p className="text-small text-danger-text">{errors.name.message}</p>}
          </div>
          {mutation.isError && !(mutation.error instanceof ApiError && mutation.error.code === 'VALIDATION_ERROR') && (
            <Alert variant="destructive">
              {mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong.'}
            </Alert>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              {isEdit ? 'Save changes' : 'Create subcategory'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
