import { useMemo, useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { motion, useReducedMotion } from 'framer-motion';
import { ArrowLeft, ChevronLeft, ChevronRight, FileWarning, Repeat, Send, ThumbsDown, ThumbsUp } from 'lucide-react';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Money } from '@/components/common/Money';
import { FinancialSummary } from '@/components/common/FinancialSummary';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { ApiError } from '@/lib/api/client';
import {
  approveQuotation,
  getQuotation,
  getQuotations,
  rejectQuotation,
  sendQuotation,
  type Quotation,
} from '@/lib/api/quotations';
import { quotationKeys } from '@/lib/queryKeys';
import { formatDate, formatDateTime } from '@/lib/format';
import { pageTransition, pageTransitionReduced } from '@/lib/motion';
import { ReviseQuotationSheet } from '@/components/quotations/ReviseQuotationSheet';

type WorkflowAction = 'send' | 'approve' | 'reject';

const ACTION_COPY: Record<WorkflowAction, { title: string; description: string; confirmLabel: string; destructive?: boolean }> = {
  send: {
    title: 'Send this quotation?',
    description: 'Marks this quotation as sent to the client. This does not dispatch an email — coordinate delivery separately.',
    confirmLabel: 'Send quotation',
  },
  approve: {
    title: 'Approve this quotation?',
    description: 'Marks this quotation as approved by the client.',
    confirmLabel: 'Approve quotation',
  },
  reject: {
    title: 'Reject this quotation?',
    description: 'Marks this quotation as rejected. You can create a revision afterward if the project continues.',
    confirmLabel: 'Reject quotation',
    destructive: true,
  },
};

export default function QuotationDetailPage() {
  const { quotationId } = useParams<{ quotationId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const shouldReduceMotion = useReducedMotion();
  const [pendingAction, setPendingAction] = useState<WorkflowAction | null>(null);
  const [reviseOpen, setReviseOpen] = useState(false);

  const { data: quotation, isLoading, isError, error, refetch } = useQuery({
    queryKey: quotationKeys.detail(quotationId!),
    queryFn: () => getQuotation(quotationId!),
    enabled: !!quotationId,
  });

  // The project's full quotation list already carries every version of
  // this quote number — reused here (rather than a dedicated endpoint,
  // since none exists) to know whether this is the latest version and to
  // drive Previous/Next lineage navigation.
  const { data: projectQuotations } = useQuery({
    queryKey: quotationKeys.project(quotation?.projectId ?? ''),
    queryFn: () => getQuotations(quotation!.projectId),
    enabled: !!quotation,
  });

  const versions = useMemo(() => {
    if (!quotation || !projectQuotations) return [];
    return projectQuotations
      .filter((q) => q.quoteNumber === quotation.quoteNumber)
      .sort((a, b) => a.version - b.version);
  }, [quotation, projectQuotations]);

  const versionIndex = versions.findIndex((v) => v.id === quotation?.id);
  const isLatest = versionIndex === -1 || versionIndex === versions.length - 1;
  const previousVersion = versionIndex > 0 ? versions[versionIndex - 1] : undefined;
  const nextVersion = versionIndex !== -1 && versionIndex < versions.length - 1 ? versions[versionIndex + 1] : undefined;

  const workflowMutation = useMutation({
    mutationFn: (action: WorkflowAction) => {
      const fn = action === 'send' ? sendQuotation : action === 'approve' ? approveQuotation : rejectQuotation;
      return fn(quotationId!);
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(quotationKeys.detail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: quotationKeys.project(updated.projectId) });
      toast.success(`Quotation ${updated.status === 'sent' ? 'sent' : updated.status}`);
      setPendingAction(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to update this quotation.');
      setPendingAction(null);
    },
  });

  if (!quotationId) return <Navigate to="/dashboard" replace />;

  if (isError) {
    const notFound = error instanceof ApiError && error.code === 'NOT_FOUND';
    if (notFound) {
      return (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <FileWarning className="size-6 text-text-tertiary" />
          <div className="flex flex-col gap-1">
            <p className="text-body font-medium text-text-primary">Quotation not found</p>
            <p className="text-small text-text-secondary">It may have been deleted, or you don't have access to it.</p>
          </div>
        </div>
      );
    }
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  return (
    <motion.div
      variants={shouldReduceMotion ? pageTransitionReduced : pageTransition}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-6"
    >
      {isLoading || !quotation ? (
        <DetailSkeleton />
      ) : (
        <>
          <Button variant="ghost" size="sm" className="w-fit gap-1.5 text-text-secondary" asChild>
            <Link to={`/projects/${quotation.projectId}/quotations`}>
              <ArrowLeft className="size-4" />
              Back to Quotations
            </Link>
          </Button>

          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex flex-col gap-1.5">
              <span className="text-label text-text-tertiary">
                {quotation.projectName} / {quotation.clientName}
              </span>
              <h2 className="text-h1 font-medium tracking-tight text-text-primary">
                {quotation.quoteNumber}
                <span className="ml-2 text-h4 font-normal text-text-tertiary">v{quotation.version}</span>
              </h2>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={quotation.status} />
                {versions.length > 1 && (
                  <span className="flex items-center gap-1 text-small text-text-tertiary">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-6"
                      aria-label="Previous version"
                      disabled={!previousVersion}
                      onClick={() => previousVersion && navigate(`/quotations/${previousVersion.id}`)}
                    >
                      <ChevronLeft className="size-3.5" />
                    </Button>
                    Version {versionIndex + 1} of {versions.length}
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-6"
                      aria-label="Next version"
                      disabled={!nextVersion}
                      onClick={() => nextVersion && navigate(`/quotations/${nextVersion.id}`)}
                    >
                      <ChevronRight className="size-3.5" />
                    </Button>
                  </span>
                )}
              </div>
            </div>

            {isLatest && (
              <div className="flex flex-wrap items-center gap-2">
                <Button variant="outline" onClick={() => setReviseOpen(true)}>
                  <Repeat />
                  Revise
                </Button>
                {quotation.status === 'draft' && (
                  <Button variant="primary" onClick={() => setPendingAction('send')}>
                    <Send />
                    Send
                  </Button>
                )}
                {quotation.status === 'sent' && (
                  <>
                    <Button variant="outline" onClick={() => setPendingAction('reject')}>
                      <ThumbsDown />
                      Reject
                    </Button>
                    <Button variant="primary" onClick={() => setPendingAction('approve')}>
                      <ThumbsUp />
                      Approve
                    </Button>
                  </>
                )}
              </div>
            )}
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Line Items</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4">
              {quotation.items.length === 0 ? (
                <p className="text-small text-text-secondary">This quotation has no line items.</p>
              ) : (
                <div className="overflow-x-auto rounded-lg border border-border-subtle">
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
                      {quotation.items.map((item) => (
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
              )}

              <FinancialSummary
                subtotal={quotation.subtotal}
                discount={quotation.discount}
                tax={quotation.tax}
                total={quotation.total}
                className="border-t border-border-subtle pt-4"
              />
            </CardContent>
          </Card>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Terms & Notes</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Terms</span>
                  <p className="text-small text-text-primary">{quotation.terms || 'No terms provided.'}</p>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Notes</span>
                  <p className="text-small text-text-primary">{quotation.notes || 'No notes provided.'}</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Details</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Valid until</span>
                  <span className="text-small text-text-primary">
                    {quotation.validUntil ? formatDate(quotation.validUntil) : 'No expiry set'}
                  </span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Created</span>
                  <span className="text-small text-text-primary">{formatDateTime(quotation.createdAt)}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Last updated</span>
                  <span className="text-small text-text-primary">{formatDateTime(quotation.updatedAt)}</span>
                </div>
              </CardContent>
            </Card>
          </div>

          <ReviseQuotationSheet open={reviseOpen} onOpenChange={setReviseOpen} quotation={quotation} />

          {(['send', 'approve', 'reject'] as WorkflowAction[]).map((action) => (
            <ConfirmationDialog
              key={action}
              open={pendingAction === action}
              onOpenChange={(open) => !open && setPendingAction(null)}
              title={ACTION_COPY[action].title}
              description={ACTION_COPY[action].description}
              confirmLabel={ACTION_COPY[action].confirmLabel}
              destructive={ACTION_COPY[action].destructive}
              loading={workflowMutation.isPending && pendingAction === action}
              onConfirm={() => workflowMutation.mutate(action)}
            />
          ))}
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
