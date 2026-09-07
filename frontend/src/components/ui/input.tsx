import * as React from 'react';
import { cn } from '@/lib/utils';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  invalid?: boolean;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, invalid, ...props }, ref) => {
    return (
      <input
        type={type}
        ref={ref}
        aria-invalid={invalid || undefined}
        className={cn(
          'flex h-9 w-full rounded-md border bg-surface px-3 py-1 text-body text-text-primary shadow-xs transition-colors duration-fast placeholder:text-text-tertiary focus-visible:outline-none focus-visible:shadow-focus disabled:cursor-not-allowed disabled:opacity-40',
          invalid ? 'border-danger-text' : 'border-border-subtle',
          className,
        )}
        {...props}
      />
    );
  },
);
Input.displayName = 'Input';

export { Input };
