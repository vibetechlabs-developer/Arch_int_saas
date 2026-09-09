import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Plus, Receipt as ReceiptIcon, Undo2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { Money } from '@/components/common/Money';
import { ApiError } from '@/lib/api/client';
import { getPayments, voidPayment, type Payment } from '@/lib/api/payments';
import type { Invoice } from '@/lib/api/invoices';
import { invoiceKeys, paymentKeys } from '@/lib/queryKeys';
import { formatDate } from '@/lib/format';
import { RecordPaymentSheet } from './RecordPaymentSheet';

export interface PaymentHistoryProps {
  invoice: Invoice;
  canRecordPayment: boolean;
  currency?: string;
}

// The Paid/Outstanding totals now live in the separate PaymentSummary
// card (BE-074, backend-authoritative InvoiceSerializer.paidAmount/
// outstandingAmount) — this component stays scoped to what it's always
// been: the real, individually-voidable payment rows themselves, never a
// computed total of its own.
export function PaymentHistory({ invoice, canRecordPayment, currency }: PaymentHistoryProps) {
  const queryClient = useQueryClient();
  const [recordOpen, setRecordOpen] = useState(false);
  const [voidingPayment, setVoidingPayment] = useState<Payment | null>(null);

  const {
    data: payments,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: paymentKeys.invoice(invoice.id),
    queryFn: () => getPayments(invoice.id),
  });

  const voidMutation = useMutation({
    mutationFn: (paymentId: string) => voidPayment(paymentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: paymentKeys.invoice(invoice.id) });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.detail(invoice.id) });
      queryClient.invalidateQueries({ queryKey: invoiceKeys.project(invoice.projectId) });
      toast.success('Payment voided');
      setVoidingPayment(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to void this payment.');
      setVoidingPayment(null);
    },
  });

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between">
        <CardTitle>Payment History</CardTitle>
        {canRecordPayment && (
          <Button variant="primary" size="sm" onClick={() => setRecordOpen(true)}>
            <Plus />
            Record Payment
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {isError ? (
          <ErrorState error={error} onRetry={() => refetch()} />
        ) : isLoading ? (
          <PaymentHistorySkeleton />
        ) : !payments || payments.length === 0 ? (
          <EmptyState
            icon={ReceiptIcon}
            title="No payments recorded yet"
            description="Payments recorded against this invoice will appear here."
            action={canRecordPayment ? { label: 'Record Payment', onClick: () => setRecordOpen(true) } : undefined}
          />
        ) : (
          <div className="overflow-hidden rounded-lg border border-border-subtle">
            {/* Desktop table */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-small">
                <thead>
                  <tr className="border-b border-border-subtle bg-surface-secondary text-caption text-text-tertiary">
                    <th className="px-4 py-2 text-left font-medium">Date</th>
                    <th className="px-3 py-2 text-left font-medium">Method</th>
                    <th className="px-3 py-2 text-left font-medium">Reference</th>
                    <th className="px-3 py-2 text-right font-medium">Amount</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {payments.map((payment) => (
                    <tr key={payment.id}>
                      <td className="px-4 py-2.5 text-text-primary">{formatDate(payment.paymentDate)}</td>
                      <td className="px-3 py-2.5 text-text-secondary">{payment.method || '—'}</td>
                      <td className="px-3 py-2.5 text-text-secondary">{payment.referenceNumber || '—'}</td>
                      <td className="px-3 py-2.5 text-right font-medium">
                        <Money value={payment.amount} currency={currency} />
                      </td>
                      <td className="px-3 py-2.5">
                        <div className="flex justify-end">
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label={`Void payment of ${payment.amount} on ${formatDate(payment.paymentDate)}`}
                            onClick={() => setVoidingPayment(payment)}
                          >
                            <Undo2 className="size-4 text-danger-text" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="flex flex-col divide-y divide-border-subtle md:hidden">
              {payments.map((payment) => (
                <div key={payment.id} className="flex flex-col gap-2 p-4">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-body font-medium text-text-primary">{formatDate(payment.paymentDate)}</span>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label={`Void payment of ${payment.amount} on ${formatDate(payment.paymentDate)}`}
                      onClick={() => setVoidingPayment(payment)}
                    >
                      <Undo2 className="size-4 text-danger-text" />
                    </Button>
                  </div>
                  <div className="flex items-center justify-between text-small text-text-secondary">
                    <span>{payment.method || 'No method recorded'}</span>
                    <Money value={payment.amount} currency={currency} className="font-medium" />
                  </div>
                  {payment.referenceNumber && <span className="text-caption text-text-tertiary">Ref: {payment.referenceNumber}</span>}
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>

      <RecordPaymentSheet open={recordOpen} onOpenChange={setRecordOpen} invoice={invoice} />

      <ConfirmationDialog
        open={!!voidingPayment}
        onOpenChange={(open) => !open && setVoidingPayment(null)}
        title="Void this payment?"
        description="This voids the payment (audit-logged, not deleted) and recomputes this invoice's status from its remaining payments."
        confirmLabel="Void payment"
        destructive
        loading={voidMutation.isPending}
        onConfirm={() => voidingPayment && voidMutation.mutate(voidingPayment.id)}
      />
    </Card>
  );
}

function PaymentHistorySkeleton() {
  return (
    <div className="flex flex-col gap-2">
      {Array.from({ length: 2 }).map((_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}
