import { useState } from 'react';
import { Link, Navigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { motion, useReducedMotion } from 'framer-motion';
import { ArrowLeft, Ban, FileWarning, Pencil, Send } from 'lucide-react';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Money } from '@/components/common/Money';
import { FinancialSummary } from '@/components/common/FinancialSummary';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { ApiError } from '@/lib/api/client';
import { cancelInvoice, getInvoice, sendInvoice } from '@/lib/api/invoices';
import { getQuotation } from '@/lib/api/quotations';
import { invoiceKeys, quotationKeys } from '@/lib/queryKeys';
import { formatDate, formatDateTime } from '@/lib/format';
import { pageTransition, pageTransitionReduced } from '@/lib/motion';
import { EditInvoiceSheet } from '@/components/invoices/EditInvoiceSheet';

type WorkflowAction = 'send' | 'cancel';

export default function InvoiceDetailPage() {
  const { invoiceId } = useParams<{ invoiceId: string }>();
  const queryClient = useQueryClient();
  const shouldReduceMotion = useReducedMotion();
  const [pendingAction, setPendingAction] = useState<WorkflowAction | null>(null);
  const [editOpen, setEditOpen] = useState(false);

  const { data: invoice, isLoading, isError, error, refetch } = useQuery({
    queryKey: invoiceKeys.detail(invoiceId!),
    queryFn: () => getInvoice(invoiceId!),
    enabled: !!invoiceId,
  });

  // Invoice only carries `quotationId`, not the human-readable quote
  // number/version — a single conditional fetch of the one linked
  // quotation (not a list, so not an N+1) is needed to show something
  // more useful than a bare UUID.
  const { data: sourceQuotation } = useQuery({
    queryKey: quotationKeys.detail(invoice?.quotationId ?? ''),
    queryFn: () => getQuotation(invoice!.quotationId!),
    enabled: !!invoice?.quotationId,
  });

  const workflowMutation = useMutation({
    mutationFn: (action: WorkflowAction) => (action === 'send' ? sendInvoice(invoiceId!) : cancelInvoice(invoiceId!)),
    onSuccess: (updated) => {
      queryClient.setQueryData(invoiceKeys.detail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: invoiceKeys.project(updated.projectId) });
      toast.success(updated.status === 'sent' ? 'Invoice marked as sent' : 'Invoice cancelled');
      setPendingAction(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to update this invoice.');
      setPendingAction(null);
    },
  });

  if (!invoiceId) return <Navigate to="/dashboard" replace />;

  if (isError) {
    const notFound = error instanceof ApiError && error.code === 'NOT_FOUND';
    if (notFound) {
      return (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <FileWarning className="size-6 text-text-tertiary" />
          <div className="flex flex-col gap-1">
            <p className="text-body font-medium text-text-primary">Invoice not found</p>
            <p className="text-small text-text-secondary">It may have been deleted, or you don't have access to it.</p>
          </div>
        </div>
      );
    }
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const canEdit = invoice?.status === 'draft';
  const canSend = invoice?.status === 'draft';
  const canCancel = invoice?.status === 'draft' || invoice?.status === 'sent' || invoice?.status === 'partially_paid';

  return (
    <motion.div
      variants={shouldReduceMotion ? pageTransitionReduced : pageTransition}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-6"
    >
      {isLoading || !invoice ? (
        <DetailSkeleton />
      ) : (
        <>
          <Button variant="ghost" size="sm" className="w-fit gap-1.5 text-text-secondary" asChild>
            <Link to={`/projects/${invoice.projectId}/invoices`}>
              <ArrowLeft className="size-4" />
              Back to Invoices
            </Link>
          </Button>

          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex flex-col gap-1.5">
              <span className="text-label text-text-tertiary">
                {invoice.projectName} / {invoice.clientName}
              </span>
              <h2 className="text-h1 font-medium tracking-tight text-text-primary">{invoice.invoiceNumber}</h2>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={invoice.status} />
                {invoice.dueDate && (
                  <span className="text-small text-text-tertiary">Due {formatDate(invoice.dueDate)}</span>
                )}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {canEdit && (
                <Button variant="outline" onClick={() => setEditOpen(true)}>
                  <Pencil />
                  Edit
                </Button>
              )}
              {canSend && (
                <Button variant="primary" onClick={() => setPendingAction('send')}>
                  <Send />
                  Send
                </Button>
              )}
              {canCancel && (
                <Button variant="destructive" onClick={() => setPendingAction('cancel')}>
                  <Ban />
                  Cancel
                </Button>
              )}
            </div>
          </div>

          {invoice.quotationId && (
            <Card>
              <CardContent className="flex items-center justify-between p-4">
                <span className="text-small text-text-tertiary">Source Quotation</span>
                {sourceQuotation ? (
                  <Link
                    to={`/quotations/${sourceQuotation.id}`}
                    className="text-body font-medium text-accent-500 hover:underline focus-visible:outline-none focus-visible:shadow-focus"
                  >
                    {sourceQuotation.quoteNumber} · v{sourceQuotation.version}
                  </Link>
                ) : (
                  <Skeleton className="h-5 w-24" />
                )}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>Billing Lines</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              {invoice.items.length === 0 ? (
                <p className="text-small text-text-secondary">This invoice has no line items.</p>
              ) : (
                <div className="overflow-hidden rounded-lg border border-border-subtle">
                  {/* Desktop table */}
                  <div className="hidden overflow-x-auto md:block">
                    <table className="w-full text-small">
                      <thead>
                        <tr className="border-b border-border-subtle bg-surface-secondary text-caption text-text-tertiary">
                          <th className="px-4 py-2 text-left font-medium">Item</th>
                          <th className="px-3 py-2 text-left font-medium">Unit</th>
                          <th className="px-3 py-2 text-right font-medium">Qty</th>
                          <th className="px-3 py-2 text-right font-medium">Rate</th>
                          <th className="px-4 py-2 text-right font-medium">Amount</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border-subtle">
                        {invoice.items.map((item) => (
                          <tr key={item.id}>
                            <td className="px-4 py-2.5 text-text-primary">{item.description}</td>
                            <td className="px-3 py-2.5 text-text-secondary">{item.unit || '—'}</td>
                            <td className="px-3 py-2.5 text-right tabular-nums text-text-secondary">{item.quantity}</td>
                            <td className="px-3 py-2.5 text-right">
                              <Money value={item.rate} />
                            </td>
                            <td className="px-4 py-2.5 text-right font-medium">
                              <Money value={item.amount} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Mobile cards — a dense multi-column table doesn't fit a
                      narrow viewport, so each line renders as its own card
                      with the same real fields, amount emphasized. */}
                  <div className="flex flex-col divide-y divide-border-subtle md:hidden">
                    {invoice.items.map((item) => (
                      <div key={item.id} className="flex flex-col gap-2 p-4">
                        <span className="text-body font-medium text-text-primary">{item.description}</span>
                        <div className="flex items-center justify-between text-small text-text-secondary">
                          <span>
                            {item.quantity} {item.unit || ''}
                          </span>
                          <Money value={item.rate} />
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-caption text-text-tertiary">Amount</span>
                          <Money value={item.amount} className="font-medium" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <FinancialSummary
                subtotal={invoice.subtotal}
                discount={invoice.discount}
                tax={invoice.tax}
                total={invoice.total}
                className="border-t border-border-subtle pt-4"
              />
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Payment Terms & Notes</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Payment Terms</span>
                  <p className="text-small text-text-primary">{invoice.paymentTerms || 'No payment terms provided.'}</p>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Notes</span>
                  <p className="text-small text-text-primary">{invoice.notes || 'No notes provided.'}</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Details</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Due date</span>
                  <span className="text-small text-text-primary">{invoice.dueDate ? formatDate(invoice.dueDate) : 'No due date set'}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Created</span>
                  <span className="text-small text-text-primary">{formatDateTime(invoice.createdAt)}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Last updated</span>
                  <span className="text-small text-text-primary">{formatDateTime(invoice.updatedAt)}</span>
                </div>
              </CardContent>
            </Card>
          </div>

          <EditInvoiceSheet open={editOpen} onOpenChange={setEditOpen} invoice={invoice} />

          <ConfirmationDialog
            open={pendingAction === 'send'}
            onOpenChange={(open) => !open && setPendingAction(null)}
            title="Send this invoice?"
            description="Marks this invoice as sent to the client. This does not dispatch an email — coordinate delivery separately."
            confirmLabel="Send invoice"
            loading={workflowMutation.isPending && pendingAction === 'send'}
            onConfirm={() => workflowMutation.mutate('send')}
          />

          <ConfirmationDialog
            open={pendingAction === 'cancel'}
            onOpenChange={(open) => !open && setPendingAction(null)}
            title="Cancel this invoice?"
            description="This marks the invoice as cancelled. It does not reverse or affect any payments already recorded against it."
            confirmLabel="Cancel invoice"
            destructive
            loading={workflowMutation.isPending && pendingAction === 'cancel'}
            onConfirm={() => workflowMutation.mutate('cancel')}
          />
        </>
      )}
    </motion.div>
  );
}

function DetailSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Skeleton className="h-3 w-40" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-5 w-24" />
      </div>
      <Card className="flex flex-col gap-4 p-5">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-10 w-full" />
        <Skeleton className="h-10 w-full" />
      </Card>
    </div>
  );
}
