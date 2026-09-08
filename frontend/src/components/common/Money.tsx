import { formatCurrency } from '@/lib/format';
import { cn } from '@/lib/utils';

export interface MoneyProps {
  value: string | number | null;
  className?: string;
}

// Shared money renderer: tabular numerals, backend decimal strings passed
// straight to Intl.NumberFormat (never routed through JS float math), a
// plain em dash for null/unset amounts rather than "₹0.00" or blank.
export function Money({ value, className }: MoneyProps) {
  if (value === null || value === undefined || value === '') {
    return <span className={cn('text-text-tertiary', className)}>—</span>;
  }
  return <span className={cn('tabular-nums', className)}>{formatCurrency(value)}</span>;
}
