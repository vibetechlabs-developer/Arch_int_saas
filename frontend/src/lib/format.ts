// The backend's Company model has a real per-company `currency` field
// (apps/company/models.py), but it isn't exposed to a regular company user
// anywhere yet (no "my company" endpoint — the same class of gap as the
// membership-list one flagged in the Milestone 1 plan). Defaulting to INR
// rather than USD until that's wired up, since this deployment's real
// users are India-based.
// `currency` defaults to INR only for callers that genuinely have no
// company context (matches this app's pre-existing default) — anywhere a
// real Company is in scope should pass its actual `currency` field
// (useCompanyCurrency) rather than relying on this default silently.
export function formatCurrency(value: string | number, currency: string = 'INR'): string {
  const numeric = typeof value === 'string' ? Number(value) : value;
  return new Intl.NumberFormat('en-IN', { style: 'currency', currency, maximumFractionDigits: 2 }).format(numeric);
}

export function formatDate(value: string): string {
  return new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function formatDateTime(value: string): string {
  return new Date(value).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

export function humanizeAction(action: string): string {
  return action.charAt(0) + action.slice(1).toLowerCase();
}

export function humanizeEntityType(entityType: string): string {
  return entityType
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}
