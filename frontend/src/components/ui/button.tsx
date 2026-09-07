import * as React from 'react';
import { Slot } from '@radix-ui/react-slot';
import { cva, type VariantProps } from 'class-variance-authority';
import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

// Component_Inventory.md §1: primary = one per view only; destructive is
// reserved for delete/cancel/void actions, never a merely-different action.
const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-body font-medium transition-colors duration-fast ease-standard focus-visible:outline-none focus-visible:shadow-focus disabled:pointer-events-none disabled:opacity-40 [&_svg]:pointer-events-none [&_svg]:shrink-0',
  {
    variants: {
      variant: {
        primary: 'bg-ink text-ink-text hover:bg-ink-hover active:opacity-90',
        secondary: 'bg-surface-secondary text-text-primary border border-border-subtle hover:bg-hover',
        outline: 'border border-border-strong text-text-primary hover:bg-hover',
        ghost: 'text-text-primary hover:bg-hover',
        destructive: 'bg-danger-text text-text-on-accent hover:opacity-90',
        link: 'text-accent-500 underline-offset-4 hover:underline',
      },
      size: {
        sm: 'h-8 px-3 text-small [&_svg]:size-4',
        md: 'h-9 px-4 [&_svg]:size-4',
        lg: 'h-10 px-5 text-body [&_svg]:size-5',
        icon: 'h-9 w-9 [&_svg]:size-4',
      },
    },
    defaultVariants: { variant: 'secondary', size: 'md' },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, loading = false, disabled, children, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button';
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || loading}
        aria-busy={loading || undefined}
        {...props}
      >
        {loading ? <Loader2 className="animate-spin" /> : children}
      </Comp>
    );
  },
);
Button.displayName = 'Button';

export { Button, buttonVariants };
