import { useEffect, useRef, useState } from 'react';
import { ImagePlus, Link2, Loader2, Package, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

// Mirrors backend/apps/products/validators.py exactly (JPEG/PNG/WEBP,
// 5 MB) — client-side pre-check for fast feedback only; the backend
// remains the authority and re-validates by decoded content regardless.
export const MAX_PRODUCT_IMAGE_SIZE_BYTES = 5 * 1024 * 1024;
export const ACCEPTED_PRODUCT_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

export function validateProductImageFile(file: File): string | null {
  if (!ACCEPTED_PRODUCT_IMAGE_TYPES.includes(file.type)) {
    return 'Only JPEG, PNG, and WEBP images are supported.';
  }
  if (file.size > MAX_PRODUCT_IMAGE_SIZE_BYTES) {
    return 'Image must be smaller than 5 MB.';
  }
  return null;
}

export interface ProductImagePickerProps {
  /** The persisted (or manually-entered) absolute image URL — '' means no image. */
  currentUrl: string;
  /** A freshly chosen, not-yet-uploaded file — its local preview takes priority over `currentUrl`. */
  pendingFile: File | null;
  onFileSelect: (file: File) => void;
  onRemove: () => void;
  onUrlChange: (url: string) => void;
  /** Inline validation/upload error to show beneath the picker. */
  error?: string | null;
  /** True while the image is actively uploading (or the whole form save is in flight). */
  uploading?: boolean;
  disabled?: boolean;
  /** Field label — defaults to "Product image"; Company Settings' logo upload (BE-078) passes "Company logo" to reuse this same picker rather than building a second one. */
  label?: string;
  /** Alt text for the preview thumbnail — defaults to "Product preview". */
  previewAlt?: string;
}

// Primary experience is real file selection/upload (Choose Image / drag &
// drop), with "Use an image URL instead" as an explicit, secondary,
// non-simultaneous mode — never both a file picker and a URL field shown
// at once, per the brief's "keep the interface clean" instruction. Reused
// as-is for Company logo upload (BE-078) via the `label`/`previewAlt`
// props — the picker itself has no Product-specific behavior.
export function ProductImagePicker({
  currentUrl,
  pendingFile,
  onFileSelect,
  onRemove,
  onUrlChange,
  error,
  uploading,
  disabled,
  label = 'Product image',
  previewAlt = 'Product preview',
}: ProductImagePickerProps) {
  const [urlMode, setUrlMode] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [imageBroken, setImageBroken] = useState(false);

  // Local-preview-only object URL — created for a newly chosen file,
  // revoked on every change and on unmount. Never sent to the backend or
  // persisted as imageUrl; only the upload endpoint's returned absolute
  // URL is ever saved.
  useEffect(() => {
    if (!pendingFile) {
      setPreviewUrl(null);
      return;
    }
    const objectUrl = URL.createObjectURL(pendingFile);
    setPreviewUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [pendingFile]);

  useEffect(() => setImageBroken(false), [previewUrl, currentUrl]);

  const displayUrl = previewUrl ?? currentUrl;
  const hasImage = !!displayUrl && !imageBroken;

  const handleFiles = (files: FileList | null) => {
    const file = files?.[0];
    if (file) onFileSelect(file);
  };

  return (
    <div className="flex flex-col gap-2">
      <Label>{label}</Label>

      {!urlMode ? (
        <div className="flex flex-col gap-3">
          <div
            className={cn(
              'flex flex-col items-center justify-center gap-3 rounded-lg border p-4 transition-colors duration-fast',
              isDragOver ? 'border-accent-500 bg-accent-500/5' : 'border-border-subtle',
              hasImage ? 'border-solid' : 'border-dashed',
            )}
            onDragOver={(e) => {
              e.preventDefault();
              if (!disabled) setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragOver(false);
              if (!disabled) handleFiles(e.dataTransfer.files);
            }}
          >
            {hasImage ? (
              <div className="relative">
                <img
                  src={displayUrl}
                  alt={previewAlt}
                  onError={() => setImageBroken(true)}
                  className="h-32 w-32 rounded-md border border-border-subtle object-cover"
                />
                {uploading && (
                  <div className="absolute inset-0 flex items-center justify-center rounded-md bg-black/40">
                    <Loader2 className="size-5 animate-spin text-white" />
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center gap-1.5 py-2 text-center">
                <Package className="size-8 text-text-tertiary" />
                <p className="text-small text-text-secondary">Drop image here</p>
                <p className="text-caption text-text-tertiary">or choose from computer</p>
              </div>
            )}

            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_PRODUCT_IMAGE_TYPES.join(',')}
              className="hidden"
              aria-label="Product image file"
              disabled={disabled}
              onChange={(e) => {
                handleFiles(e.target.files);
                e.target.value = '';
              }}
            />

            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={disabled}
                onClick={() => fileInputRef.current?.click()}
              >
                <ImagePlus />
                {hasImage ? 'Replace Image' : 'Choose Image'}
              </Button>
              {hasImage && (
                <Button type="button" variant="ghost" size="sm" disabled={disabled} onClick={onRemove}>
                  <X />
                  Remove
                </Button>
              )}
            </div>
          </div>

          <Button
            type="button"
            variant="link"
            size="sm"
            className="w-fit px-0"
            disabled={disabled}
            onClick={() => setUrlMode(true)}
          >
            <Link2 className="size-3.5" />
            Use an image URL instead
          </Button>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <Input
            placeholder="https://…"
            value={currentUrl}
            disabled={disabled}
            invalid={!!error}
            onChange={(e) => onUrlChange(e.target.value)}
            aria-label="Image URL"
          />
          {hasImage && (
            <img
              src={displayUrl}
              alt={previewAlt}
              onError={() => setImageBroken(true)}
              className="h-24 w-24 rounded-md border border-border-subtle object-cover"
            />
          )}
          <Button
            type="button"
            variant="link"
            size="sm"
            className="w-fit px-0"
            disabled={disabled}
            onClick={() => setUrlMode(false)}
          >
            <ImagePlus className="size-3.5" />
            Use file upload instead
          </Button>
        </div>
      )}

      {error && <p className="text-small text-danger-text">{error}</p>}
    </div>
  );
}
