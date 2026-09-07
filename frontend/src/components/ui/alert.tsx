import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { AlertCircle, AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import { cn } from '@/lib/utils';

const alertVariants = cva(
  'relative flex w-full gap-3 rounded-lg border p-4 text-small transition-colors duration-standard [&>svg]:size-4 [&>svg]:shrink-0 [&>svg]:mt-0.5',
  {
    variants: {
      variant: {
        neutral: 'border-border-subtle bg-surface-secondary text-text-primary [&>svg]:text-text-secondary',
        info: 'border-info-text/20 bg-info-bg text-info-text [&>svg]:text-info-text',
        success: 'border-success-text/20 bg-success-bg text-success-text [&>svg]:text-success-text',
        warning: 'border-warning-text/20 bg-warning-bg text-warning-text [&>svg]:text-warning-text',
        destructive: 'border-danger-text/20 bg-danger-bg text-danger-text [&>svg]:text-danger-text',
      },
    },
    defaultVariants: {
      variant: 'neutral',
    },
  },
);

export interface AlertProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof alertVariants> {
  icon?: React.ReactNode;
}

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ className, variant = 'neutral', icon, children, ...props }, ref) => {
    const defaultIcon =
      variant === 'destructive' ? (
        <AlertCircle />
      ) : variant === 'warning' ? (
        <AlertTriangle />
      ) : variant === 'success' ? (
        <CheckCircle2 />
      ) : variant === 'info' ? (
        <Info />
      ) : null;

    return (
      <div
        ref={ref}
        role="alert"
        className={cn(alertVariants({ variant }), className)}
        {...props}
      >
        {icon !== undefined ? icon : defaultIcon}
        <div className="flex-1 leading-normal">{children}</div>
      </div>
    );
  },
);
Alert.displayName = 'Alert';

const AlertTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h5
    ref={ref}
    className={cn('text-body font-medium leading-none tracking-tight mb-1', className)}
    {...props}
  />
));
AlertTitle.displayName = 'AlertTitle';

const AlertDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn('text-small opacity-90', className)}
    {...props}
  />
));
AlertDescription.displayName = 'AlertDescription';

export { Alert, AlertTitle, AlertDescription, alertVariants };
