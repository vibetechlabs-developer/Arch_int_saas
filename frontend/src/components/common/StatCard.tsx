import { motion } from 'framer-motion';
import { ArrowDownRight, ArrowUpRight } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { useCountUp } from '@/lib/useCountUp';
import { cn } from '@/lib/utils';

export interface StatCardProps {
  label: string;
  /** Display value string or number */
  value?: string | number;
  /** Raw numeric value the count-up animates toward */
  numericValue?: number;
  /** Formats the animated numeric value into display text */
  format?: (value: number) => string;
  /** Omitted entirely when the backend has no comparison-period data */
  trend?: { direction: 'up' | 'down'; label: string } | null;
  caption?: string;
  /** Optional minimal sparkline data points (3-12 values) */
  sparkline?: number[];
  /** Smaller tier — used for secondary metrics sitting beside a featured card, per the editorial "not every metric identical" composition rule. */
  compact?: boolean;
}

/**
 * KPI card: label (text-label) + text-kpi value (tabular-nums) + optional trend + optional minimal sparkline.
 * Purely informational card with no oversized colorful icon tiles and no hover elevation.
 */
export function StatCard({
  label,
  value,
  numericValue,
  format = (v) => String(Math.round(v)),
  trend,
  caption,
  sparkline,
  compact = false,
}: StatCardProps) {
  const targetNumber = typeof numericValue === 'number'
    ? numericValue
    : typeof value === 'number'
      ? value
      : null;

  const animatedNumber = useCountUp(targetNumber ?? 0);
  const displayValue = targetNumber !== null ? format(animatedNumber) : (value ?? '');

  return (
    <Card className={cn('flex flex-col gap-2.5', compact ? 'p-4' : 'gap-3 p-5')}>
      <div className="flex items-center justify-between">
        <div className="flex flex-col gap-1.5">
          <span className="text-label text-text-tertiary">{label}</span>
          {!compact && <span className="block h-0.5 w-4 rounded-full bg-accent-500/60" aria-hidden="true" />}
        </div>
        {trend && (
          <span
            className={cn(
              'inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-caption font-medium',
              trend.direction === 'up' ? 'bg-success-bg text-success-text' : 'bg-danger-bg text-danger-text',
            )}
          >
            {trend.direction === 'up' ? <ArrowUpRight className="size-3" /> : <ArrowDownRight className="size-3" />}
            {trend.label}
          </span>
        )}
      </div>

      <div className="flex items-end justify-between gap-2">
        <motion.div
          key={String(targetNumber ?? value)}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2 }}
          className={cn('tabular-nums tracking-tight text-text-primary', compact ? 'text-h3' : 'text-kpi')}
        >
          {displayValue}
        </motion.div>

        {sparkline && sparkline.length > 1 && (
          <MinimalSparkline data={sparkline} isPositive={trend?.direction !== 'down'} />
        )}
      </div>

      {caption && <div className="text-small text-text-secondary">{caption}</div>}
    </Card>
  );
}

function MinimalSparkline({ data, isPositive = true }: { data: number[]; isPositive?: boolean }) {
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const width = 64;
  const height = 24;
  const padding = 2;

  const points = data
    .map((val, idx) => {
      const x = padding + (idx / (data.length - 1)) * (width - padding * 2);
      const y = height - padding - ((val - min) / range) * (height - padding * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');

  return (
    <svg
      className="h-6 w-16 shrink-0 overflow-visible"
      viewBox={`0 0 ${width} ${height}`}
      fill="none"
      aria-hidden="true"
    >
      <polyline
        points={points}
        stroke={isPositive ? 'var(--status-success-text)' : 'var(--status-danger-text)'}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
