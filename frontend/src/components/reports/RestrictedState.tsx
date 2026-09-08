import { Lock } from 'lucide-react';

export interface RestrictedStateProps {
  /** The backend's own 403 detail message — never a client-invented one. */
  message?: string;
}

// Distinct from ErrorState: a 403 here means the report exists and the
// request succeeded in every technical sense — the caller's role simply
// doesn't hold report.financial_access. No "Try again" action, since
// retrying changes nothing; only a permission grant would.
export function RestrictedState({ message }: RestrictedStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 py-10 text-center">
      <Lock className="size-6 text-text-tertiary" />
      <div className="flex flex-col gap-1">
        <p className="text-body font-medium text-text-primary">Restricted</p>
        <p className="text-small text-text-secondary">
          {message ?? "You don't have permission to view this report."}
        </p>
      </div>
    </div>
  );
}
