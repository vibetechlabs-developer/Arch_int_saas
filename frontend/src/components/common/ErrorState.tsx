import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ApiError } from '@/lib/api/client';

export interface ErrorStateProps {
  error: unknown;
  onRetry?: () => void;
}

// Component_Inventory.md §12: states what happened, why (if known), the
// next action, and a copyable requestId — never a bare "Error."
export function ErrorState({ error, onRetry }: ErrorStateProps) {
  const message = error instanceof ApiError ? error.message : 'Something went wrong loading this data.';
  const requestId = error instanceof ApiError ? error.requestId : undefined;

  return (
    <div className="flex flex-col items-center gap-3 py-10 text-center">
      <AlertTriangle className="size-6 text-danger-text" />
      <div className="flex flex-col gap-1">
        <p className="text-body font-medium text-text-primary">Couldn't load this page</p>
        <p className="text-small text-text-secondary">{message}</p>
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry} className="mt-1">
          Try again
        </Button>
      )}
      {requestId && <p className="text-caption text-text-tertiary">Request ID: {requestId}</p>}
    </div>
  );
}
