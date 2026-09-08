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
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { ApiError } from '@/lib/api/client';
import { createDocument } from '@/lib/api/documents';
import { documentKeys } from '@/lib/queryKeys';

const formSchema = z.object({
  fileUrl: z.string().min(1, 'File URL is required').url('Enter a valid URL'),
});

type FormValues = z.infer<typeof formSchema>;

export interface RegisterDocumentSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
}

// No file upload endpoint exists anywhere in this backend — a document
// is registered by URL only, the same pattern already established for
// Payment/Expense receipts and Product images. This form has exactly
// one field because that's the entire writable contract.
export function RegisterDocumentSheet({ open, onOpenChange, projectId }: RegisterDocumentSheetProps) {
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(formSchema), defaultValues: { fileUrl: '' } });

  useEffect(() => {
    if (open) reset({ fileUrl: '' });
  }, [open, reset]);

  const mutation = useMutation({
    mutationFn: (values: FormValues) => createDocument(projectId, { fileUrl: values.fileUrl }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.project(projectId) });
      toast.success('Document added');
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
          <SheetTitle>Add document</SheetTitle>
          <SheetDescription>Register a file already hosted elsewhere by its link.</SheetDescription>
        </SheetHeader>

        <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="flex flex-1 flex-col gap-5" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="document-file-url">File URL</Label>
            <Input
              id="document-file-url"
              placeholder="https://…"
              invalid={!!errors.fileUrl}
              {...register('fileUrl')}
            />
            {errors.fileUrl && <p className="text-small text-danger-text">{errors.fileUrl.message}</p>}
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
              Add document
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
