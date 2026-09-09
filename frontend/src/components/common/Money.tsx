import { formatCurrency } from '@/lib/format';
import { cn } from '@/lib/utils';

export interface MoneyProps {
  value: string | number | null;
  currency?: string;
  className?: string;
}

// Shared money renderer: tabular numerals, backend decimal strings passed
// straight to Intl.NumberFormat (never routed through JS float math), a
// plain em dash for null/unset amounts rather than "₹0.00" or blank.
// `currency` defaults to INR (formatCurrency's own default) for the many
// existing callers with no company context in scope — pass the real
// resolved company currency (useCompanyCurrency) wherever it's available.
export function Money({ value, currency, className }: MoneyProps) {
  if (value === null || value === undefined || value === '') {
    return <span className={cn('text-text-tertiary', className)}>—</span>;
  }
  return <span className={cn('tabular-nums', className)}>{formatCurrency(value, currency)}</span>;
}
