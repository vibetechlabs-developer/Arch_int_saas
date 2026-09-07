import * as React from 'react';
import { cn } from '@/lib/utils';

export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, invalid, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          'flex min-h-[80px] w-full rounded-md border bg-surface px-3 py-2 text-body text-text-primary shadow-xs transition-colors duration-fast placeholder:text-text-tertiary focus-visible:outline-none focus-visible:shadow-focus disabled:cursor-not-allowed disabled:opacity-40',
          invalid ? 'border-danger-text' : 'border-border-subtle',
          className,
        )}
        ref={ref}
        aria-invalid={invalid || undefined}
        {...props}
      />
    );
  },
);
Textarea.displayName = 'Textarea';

export { Textarea };
