import { useQuery } from '@tanstack/react-query';
import { TrendingDown, TrendingUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Money } from '@/components/common/Money';
import { ErrorState } from '@/components/common/ErrorState';
import { RestrictedState } from '@/components/reports/RestrictedState';
import { ApiError } from '@/lib/api/client';
import { getFinanceReport, type ReportFilters } from '@/lib/api/reports';
import { reportKeys } from '@/lib/queryKeys';
import { cn } from '@/lib/utils';

export interface FinanceReportPanelProps {
  filters: ReportFilters;
}

// Reads the Decimal string's own sign character for tone selection only —
// never converts it to a number for the displayed value itself. Every
// amount below is still rendered from the exact backend string via <Money>.
function isNegative(decimalString: string): boolean {
  return decimalString.trim().startsWith('-');
}

export function FinanceReportPanel({ filters }: FinanceReportPanelProps) {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: reportKeys.finance(filters),
    queryFn: () => getFinanceReport(filters),
  });

  if (isError) {
    if (error instanceof ApiError && error.status === 403) {
      return (
        <Card>
          <RestrictedState message={error.message} />
        </Card>
      );
    }
    return (
      <Card>
        <ErrorState error={error} onRetry={() => refetch()} />
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <Card className="flex flex-col gap-5 p-6">
        <span className="text-label text-text-tertiary">Profit &amp; Loss</span>
        {isLoading || !data ? (
          <PanelSkeleton count={3} />
        ) : (
          <div className="grid grid-cols-3 gap-4">
            <MetricTile label="Revenue" value={data.revenue} />
            <MetricTile label="Expenses" value={data.expenses} />
            <MetricTile
              label="Profit / Loss"
              value={data.profitLoss}
              emphasize
              tone={isNegative(data.profitLoss) ? 'danger' : 'success'}
              icon={isNegative(data.profitLoss) ? TrendingDown : TrendingUp}
            />
          </div>
        )}
      </Card>

      <Card className="flex flex-col gap-5 p-6">
        <span className="text-label text-text-tertiary">Receivables &amp; Collections</span>
        {isLoading || !data ? (
          <PanelSkeleton count={3} />
        ) : (
          <div className="grid grid-cols-3 gap-4">
            <MetricTile label="Received" value={data.received} tone="success" />
            <MetricTile label="Receivables" value={data.receivables} />
            <MetricTile label="Outstanding" value={data.outstanding} tone={data.outstanding !== '0.00' ? 'warning' : undefined} />
          </div>
        )}
      </Card>
    </div>
  );
}

function MetricTile({
  label,
  value,
  tone,
  emphasize,
  icon: Icon,
}: {
  label: string;
  value: string;
  tone?: 'success' | 'warning' | 'danger';
  emphasize?: boolean;
  icon?: typeof TrendingUp;
}) {
  const toneClass =
    tone === 'success'
      ? 'text-success-text'
      : tone === 'warning'
        ? 'text-warning-text'
        : tone === 'danger'
          ? 'text-danger-text'
          : 'text-text-primary';

  return (
    <div className="flex flex-col gap-1.5">
      <span className="flex items-center gap-1 text-caption text-text-tertiary">
        {Icon && <Icon className="size-3" />}
        {label}
      </span>
      <Money value={value} className={cn('tabular-nums font-medium', emphasize ? 'text-h3' : 'text-body', toneClass)} />
    </div>
  );
}

function PanelSkeleton({ count }: { count: number }) {
  return (
    <div className="grid grid-cols-3 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="flex flex-col gap-2">
          <Skeleton className="h-3 w-16" />
          <Skeleton className="h-6 w-20" />
        </div>
      ))}
    </div>
  );
}
