import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Money } from '@/components/common/Money';
import { Wallet } from 'lucide-react';

export interface PaymentSummaryProps {
  total: string | undefined;
  paidAmount: string | undefined;
  outstandingAmount: string | undefined;
  currency?: string;
  loading?: boolean;
}

// BE-074: Invoice Total / Amount Paid / Balance Due, sourced entirely from
// backend-authoritative decimal strings (InvoiceSerializer.total/
// paidAmount/outstandingAmount) — never summed from PaymentHistory or
// computed as total-minus-paid here. `outstandingAmount` is already
// floored at zero server-side, so an overpaid invoice naturally renders
// "Balance Due" as 0, never negative, with no extra logic needed on this
// side; `paidAmount` still shows the real (possibly larger-than-total)
// figure unchanged.
export function PaymentSummary({ total, paidAmount, outstandingAmount, currency, loading }: PaymentSummaryProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <Wallet className="size-4 text-text-tertiary" />
          Payment Summary
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <SummaryFigure label="Invoice Total" value={total} currency={currency} loading={loading} />
          <SummaryFigure label="Amount Paid" value={paidAmount} currency={currency} loading={loading} />
          <SummaryFigure
            label="Balance Due"
            value={outstandingAmount}
            currency={currency}
            loading={loading}
            emphasize
          />
        </div>
      </CardContent>
    </Card>
  );
}

function SummaryFigure({
  label,
  value,
  currency,
  loading,
  emphasize,
}: {
  label: string;
  value: string | undefined;
  currency?: string;
  loading?: boolean;
  emphasize?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1 rounded-lg border border-border-subtle bg-surface-secondary px-4 py-3">
      <span className="text-label text-text-tertiary">{label}</span>
      {loading || value === undefined ? (
        <Skeleton className="h-7 w-24" />
      ) : (
        <Money
          value={value}
          currency={currency}
          className={emphasize ? 'text-h3 font-medium text-text-primary' : 'text-h4 text-text-primary'}
        />
      )}
    </div>
  );
}
