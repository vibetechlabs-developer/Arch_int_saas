import { useState } from 'react';
import { Package } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ProductThumbnailProps {
  imageUrl: string;
  alt: string;
  size?: 'sm' | 'lg';
}

// Backend stores a plain `imageUrl` (no file-upload endpoint exists) — this
// just renders it with a broken-link/empty fallback to a neutral icon, never
// a fake stock image.
export function ProductThumbnail({ imageUrl, alt, size = 'sm' }: ProductThumbnailProps) {
  const [broken, setBroken] = useState(false);
  const dimension = size === 'lg' ? 'size-24' : 'size-9';

  if (!imageUrl || broken) {
    return (
      <div className={cn('flex shrink-0 items-center justify-center rounded-md border border-border-subtle bg-surface-secondary', dimension)}>
        <Package className={cn('text-text-tertiary', size === 'lg' ? 'size-8' : 'size-4')} />
      </div>
    );
  }

  return (
    <img
      src={imageUrl}
      alt={alt}
      onError={() => setBroken(true)}
      className={cn('shrink-0 rounded-md border border-border-subtle object-cover', dimension)}
    />
  );
}
