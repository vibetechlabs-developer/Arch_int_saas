import { Skeleton } from '@/components/ui/skeleton';
import { Money } from '@/components/common/Money';
import { cn } from '@/lib/utils';

export interface FinancialSummaryProps {
  subtotal: string | undefined;
  discount: string | undefined;
  tax: string | undefined;
  total: string | undefined;
  loading?: boolean;
  className?: string;
}

// Reusable Subtotal/Discount/Tax/Grand Total row — every amount is a
// backend decimal string rendered as-is (no frontend math). First used by
// the BOQ workspace summary; now shared with Quotation detail, since both
// need the exact same four-field commercial total shape.
export function FinancialSummary({ subtotal, discount, tax, total, loading, className }: FinancialSummaryProps) {
  return (
    <div className={cn('grid grid-cols-2 gap-4 sm:grid-cols-4', className)}>
      <SummaryStat label="Subtotal" value={subtotal} loading={!!loading} />
      <SummaryStat label="Discount" value={discount} loading={!!loading} />
      <SummaryStat label="Tax" value={tax} loading={!!loading} />
      <SummaryStat label="Grand Total" value={total} loading={!!loading} emphasize />
    </div>
  );
}

function SummaryStat({
  label,
  value,
  loading,
  emphasize,
}: {
  label: string;
  value: string | undefined;
  loading: boolean;
  emphasize?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-label text-text-tertiary">{label}</span>
      {loading || value === undefined ? (
        <Skeleton className="h-6 w-20" />
      ) : (
        <Money value={value} className={emphasize ? 'text-h3 font-medium text-text-primary' : 'text-body text-text-primary'} />
      )}
    </div>
  );
}
