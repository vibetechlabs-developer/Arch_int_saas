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
import { createBOQSection, updateBOQSection, type BOQSection } from '@/lib/api/boq';
import { boqKeys } from '@/lib/queryKeys';

const schema = z.object({ name: z.string().trim().min(1, 'Section name is required').max(255) });
type FormValues = z.infer<typeof schema>;

export interface BOQSectionFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  section?: BOQSection;
}

export function BOQSectionFormDialog({ open, onOpenChange, projectId, section }: BOQSectionFormDialogProps) {
  const isEdit = !!section;
  const queryClient = useQueryClient();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { name: '' } });

  useEffect(() => {
    if (open) reset({ name: section?.name ?? '' });
  }, [open, section, reset]);

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      isEdit ? updateBOQSection(section!.id, values.name) : createBOQSection(projectId, values.name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: boqKeys.project(projectId) });
      queryClient.invalidateQueries({ queryKey: boqKeys.summary(projectId) });
      toast.success(isEdit ? 'Section updated' : 'Section added');
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
          <DialogTitle>{isEdit ? 'Edit section' : 'Add section'}</DialogTitle>
          <DialogDescription>
            {isEdit ? 'Rename this BOQ section.' : 'Add a new section to this BOQ.'}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="boq-section-name">Section name</Label>
            <Input id="boq-section-name" invalid={!!errors.name} {...register('name')} />
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
              {isEdit ? 'Save changes' : 'Add section'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
