import { useEffect, useRef, useState, type FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { FileUp, Link2, Paperclip, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert } from '@/components/ui/alert';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { ApiError } from '@/lib/api/client';
import { createDocument, uploadDocumentFile } from '@/lib/api/documents';
import { documentKeys } from '@/lib/queryKeys';

// Mirrors backend/apps/common/storage.py::validate_document_upload exactly
// (PDF/JPEG/PNG/WEBP, 20 MB) — client-side pre-check for fast feedback
// only; the backend remains the authority and re-validates by decoded
// content regardless.
export const MAX_DOCUMENT_FILE_SIZE_BYTES = 20 * 1024 * 1024;
export const ACCEPTED_DOCUMENT_FILE_TYPES = ['application/pdf', 'image/jpeg', 'image/png', 'image/webp'];

export function validateDocumentFile(file: File): string | null {
  if (!ACCEPTED_DOCUMENT_FILE_TYPES.includes(file.type)) {
    return 'Only PDF, JPEG, PNG, or WEBP files are supported.';
  }
  if (file.size > MAX_DOCUMENT_FILE_SIZE_BYTES) {
    return 'File must be smaller than 20 MB.';
  }
  return null;
}

function isValidUrl(value: string): boolean {
  try {
    new URL(value);
    return true;
  } catch {
    return false;
  }
}

export interface RegisterDocumentSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
}

// Primary experience is a real file upload (BE-078, private storage —
// PDF/JPEG/PNG/WEBP), with "Use a URL instead" as an explicit, secondary,
// non-simultaneous mode for a file already hosted elsewhere — mirrors
// ProductImagePicker's Choose File / "Use a URL instead" pattern exactly,
// adapted for a non-image file type. Plain state + manual validation
// (not react-hook-form/Zod) since the two modes validate entirely
// different things — a single shared schema would have to validate
// fileUrl even while a file is being uploaded instead.
export function RegisterDocumentSheet({ open, onOpenChange, projectId }: RegisterDocumentSheetProps) {
  const queryClient = useQueryClient();
  const [urlMode, setUrlMode] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileUrl, setFileUrl] = useState('');
  const [fieldError, setFieldError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setUrlMode(false);
      setSelectedFile(null);
      setFileUrl('');
      setFieldError(null);
    }
  }, [open]);

  const mutation = useMutation({
    mutationFn: async () => {
      if (urlMode) {
        return createDocument(projectId, { fileUrl });
      }
      const uploaded = await uploadDocumentFile(selectedFile!);
      return createDocument(projectId, { fileStorageKey: uploaded.key });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.project(projectId) });
      toast.success('Document added');
      onOpenChange(false);
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : 'Something went wrong. Please try again.');
    },
  });

  const handleFileChange = (files: FileList | null) => {
    const file = files?.[0];
    if (!file) return;
    const validationMessage = validateDocumentFile(file);
    if (validationMessage) {
      setFieldError(validationMessage);
      return;
    }
    setFieldError(null);
    setSelectedFile(file);
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (urlMode) {
      if (!fileUrl.trim()) {
        setFieldError('File URL is required');
        return;
      }
      if (!isValidUrl(fileUrl.trim())) {
        setFieldError('Enter a valid URL');
        return;
      }
    } else if (!selectedFile) {
      setFieldError('Choose a file to upload.');
      return;
    }
    setFieldError(null);
    mutation.mutate();
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>Add document</SheetTitle>
          <SheetDescription>
            {urlMode ? 'Register a file already hosted elsewhere by its link.' : 'Upload a PDF, JPEG, PNG, or WEBP file.'}
          </SheetDescription>
        </SheetHeader>

        <form onSubmit={onSubmit} className="flex flex-1 flex-col gap-5" noValidate>
          {!urlMode ? (
            <div className="flex flex-col gap-2">
              <Label>File</Label>
              <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-dashed border-border-subtle p-4">
                {selectedFile ? (
                  <div className="flex w-full items-center justify-between gap-2 rounded-md border border-border-subtle bg-surface-secondary px-3 py-2">
                    <span className="flex items-center gap-2 truncate text-small text-text-primary">
                      <Paperclip className="size-4 shrink-0 text-text-tertiary" />
                      {selectedFile.name}
                    </span>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      disabled={mutation.isPending}
                      onClick={() => {
                        setSelectedFile(null);
                        setFieldError(null);
                      }}
                    >
                      <X />
                    </Button>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-1.5 py-2 text-center">
                    <FileUp className="size-8 text-text-tertiary" />
                    <p className="text-small text-text-secondary">Choose a file to upload</p>
                    <p className="text-caption text-text-tertiary">PDF, JPEG, PNG, or WEBP — up to 20 MB</p>
                  </div>
                )}

                <input
                  ref={fileInputRef}
                  type="file"
                  accept={ACCEPTED_DOCUMENT_FILE_TYPES.join(',')}
                  className="hidden"
                  aria-label="Document file"
                  disabled={mutation.isPending}
                  onChange={(e) => {
                    handleFileChange(e.target.files);
                    e.target.value = '';
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={mutation.isPending}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <FileUp />
                  {selectedFile ? 'Choose a different file' : 'Choose File'}
                </Button>
              </div>
              {fieldError && <p className="text-small text-danger-text">{fieldError}</p>}

              <Button
                type="button"
                variant="link"
                size="sm"
                className="w-fit px-0"
                disabled={mutation.isPending}
                onClick={() => {
                  setUrlMode(true);
                  setFieldError(null);
                }}
              >
                <Link2 className="size-3.5" />
                Use a URL instead
              </Button>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              <Label htmlFor="document-file-url">File URL</Label>
              <Input
                id="document-file-url"
                placeholder="https://…"
                invalid={!!fieldError}
                value={fileUrl}
                onChange={(e) => setFileUrl(e.target.value)}
              />
              {fieldError && <p className="text-small text-danger-text">{fieldError}</p>}

              <Button
                type="button"
                variant="link"
                size="sm"
                className="w-fit px-0"
                disabled={mutation.isPending}
                onClick={() => {
                  setUrlMode(false);
                  setFieldError(null);
                }}
              >
                <FileUp className="size-3.5" />
                Upload a file instead
              </Button>
            </div>
          )}

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
