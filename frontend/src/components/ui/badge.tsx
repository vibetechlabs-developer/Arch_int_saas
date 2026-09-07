import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

// Component_Inventory.md §7: one status per badge, semantic color fill+text
// pairing only — never a decorative color.
const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2 py-0.5 text-caption font-medium',
  {
    variants: {
      variant: {
        neutral: 'bg-surface-secondary text-text-secondary',
        success: 'bg-success-bg text-success-text',
        warning: 'bg-warning-bg text-warning-text',
        danger: 'bg-danger-bg text-danger-text',
        info: 'bg-info-bg text-info-text',
      },
    },
    defaultVariants: { variant: 'neutral' },
  },
);

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
