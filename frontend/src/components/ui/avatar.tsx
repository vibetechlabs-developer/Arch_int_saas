import * as React from 'react';
import * as AvatarPrimitive from '@radix-ui/react-avatar';
import { cn } from '@/lib/utils';

const Avatar = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Root>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Root
    ref={ref}
    className={cn('relative flex size-8 shrink-0 overflow-hidden rounded-full', className)}
    {...props}
  />
));
Avatar.displayName = AvatarPrimitive.Root.displayName;

const AvatarImage = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Image>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Image>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Image ref={ref} className={cn('aspect-square size-full', className)} {...props} />
));
AvatarImage.displayName = AvatarPrimitive.Image.displayName;

// Deterministic neutral background derived from the name/id, not random
// (Component_Inventory.md §8).
const FALLBACK_HUES = ['bg-surface-secondary'] as const;

function hashToInitialsColor(seed: string): string {
  let hash = 0;
  for (let i = 0; i < seed.length; i++) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  return FALLBACK_HUES[hash % FALLBACK_HUES.length];
}

const AvatarFallback = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Fallback>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Fallback> & { seed?: string }
>(({ className, seed = '', ...props }, ref) => (
  <AvatarPrimitive.Fallback
    ref={ref}
    className={cn(
      'flex size-full items-center justify-center text-caption font-medium text-text-secondary',
      hashToInitialsColor(seed),
      className,
    )}
    {...props}
  />
));
AvatarFallback.displayName = AvatarPrimitive.Fallback.displayName;

export function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? '';
  const last = parts.length > 1 ? parts[parts.length - 1][0] : '';
  return (first + last).toUpperCase();
}

export function AvatarGroup({
  children,
  className,
  max = 4,
}: {
  children: React.ReactNode;
  className?: string;
  max?: number;
}) {
  const childArray = React.Children.toArray(children);
  const visible = childArray.slice(0, max);
  const overflow = childArray.length - max;

  return (
    <div className={cn('flex items-center -space-x-2', className)}>
      {visible.map((child, i) => (
        <div key={i} className="ring-2 ring-surface rounded-full">
          {child}
        </div>
      ))}
      {overflow > 0 && (
        <div className="flex size-8 items-center justify-center rounded-full bg-surface-secondary text-caption font-medium text-text-secondary ring-2 ring-surface">
          +{overflow}
        </div>
      )}
    </div>
  );
}

export { Avatar, AvatarImage, AvatarFallback };
