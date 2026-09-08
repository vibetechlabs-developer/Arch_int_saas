import { useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { motion, useReducedMotion } from 'framer-motion';
import { ArrowLeft, CheckCircle2, ExternalLink, Pencil, Send, Trash2, Wallet } from 'lucide-react';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Money } from '@/components/common/Money';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { ApiError } from '@/lib/api/client';
import { approveExpense, deleteExpense, getExpense, markExpensePaid, submitExpense, type Expense } from '@/lib/api/expenses';
import { expenseKeys } from '@/lib/queryKeys';
import { formatDate, formatDateTime } from '@/lib/format';
import { pageTransition, pageTransitionReduced } from '@/lib/motion';
import { ExpenseFormSheet } from '@/components/expenses/ExpenseFormSheet';

type WorkflowAction = 'submit' | 'approve' | 'markPaid';

const ACTION_COPY: Record<WorkflowAction, { title: string; description: string; confirmLabel: string }> = {
  submit: {
    title: 'Submit this expense?',
    description: 'Sends this expense for approval. It can no longer be edited once submitted.',
    confirmLabel: 'Submit expense',
  },
  approve: {
    title: 'Approve this expense?',
    description: 'Marks this expense as approved.',
    confirmLabel: 'Approve expense',
  },
  markPaid: {
    title: 'Mark this expense as paid?',
    description: 'Marks this expense as paid. This does not record a payment elsewhere in the system.',
    confirmLabel: 'Mark as paid',
  },
};

export default function ExpenseDetailPage() {
  const { expenseId } = useParams<{ expenseId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const shouldReduceMotion = useReducedMotion();
  const [editOpen, setEditOpen] = useState(false);
  const [pendingAction, setPendingAction] = useState<WorkflowAction | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const { data: expense, isLoading, isError, error, refetch } = useQuery({
    queryKey: expenseKeys.detail(expenseId!),
    queryFn: () => getExpense(expenseId!),
    enabled: !!expenseId,
  });

  const workflowMutation = useMutation({
    mutationFn: (action: WorkflowAction) => {
      const fn = action === 'submit' ? submitExpense : action === 'approve' ? approveExpense : markExpensePaid;
      return fn(expenseId!);
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(expenseKeys.detail(updated.id), updated);
      queryClient.invalidateQueries({ queryKey: expenseKeys.project(updated.projectId) });
      toast.success(
        updated.approvalStatus === 'submitted'
          ? 'Expense submitted'
          : updated.approvalStatus === 'approved'
            ? 'Expense approved'
            : 'Expense marked as paid',
      );
      setPendingAction(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to update this expense.');
      setPendingAction(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteExpense(expenseId!),
    onSuccess: () => {
      if (expense) {
        queryClient.removeQueries({ queryKey: expenseKeys.detail(expense.id) });
        queryClient.invalidateQueries({ queryKey: expenseKeys.project(expense.projectId) });
      }
      toast.success('Expense deleted');
      navigate(expense ? `/projects/${expense.projectId}/expenses` : '/dashboard', { replace: true });
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete this expense.');
      setDeleteOpen(false);
    },
  });

  if (!expenseId) return <Navigate to="/dashboard" replace />;

  if (isError) {
    const notFound = error instanceof ApiError && error.code === 'NOT_FOUND';
    if (notFound) {
      return (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <Wallet className="size-6 text-text-tertiary" />
          <div className="flex flex-col gap-1">
            <p className="text-body font-medium text-text-primary">Expense not found</p>
            <p className="text-small text-text-secondary">It may have been deleted, or you don't have access to it.</p>
          </div>
        </div>
      );
    }
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const canEditOrDelete = expense?.approvalStatus === 'draft';
  const canSubmit = expense?.approvalStatus === 'draft';
  const canApprove = expense?.approvalStatus === 'submitted';
  const canMarkPaid = expense?.approvalStatus === 'approved';

  return (
    <motion.div
      variants={shouldReduceMotion ? pageTransitionReduced : pageTransition}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-6"
    >
      {isLoading || !expense ? (
        <DetailSkeleton />
      ) : (
        <>
          <Button variant="ghost" size="sm" className="w-fit gap-1.5 text-text-secondary" asChild>
            <Link to={`/projects/${expense.projectId}/expenses`}>
              <ArrowLeft className="size-4" />
              Back to Expenses
            </Link>
          </Button>

          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex flex-col gap-1.5">
              <span className="text-label text-text-tertiary">{expense.projectName}</span>
              <h2 className="text-h1 font-medium tracking-tight text-text-primary">{expense.category || 'Uncategorized'}</h2>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={expense.approvalStatus} />
                <span className="text-small text-text-tertiary">{formatDate(expense.date)}</span>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {canEditOrDelete && (
                <>
                  <Button variant="outline" onClick={() => setEditOpen(true)}>
                    <Pencil />
                    Edit
                  </Button>
                  <Button variant="destructive" onClick={() => setDeleteOpen(true)}>
                    <Trash2 />
                    Delete
                  </Button>
                </>
              )}
              {canSubmit && (
                <Button variant="primary" onClick={() => setPendingAction('submit')}>
                  <Send />
                  Submit
                </Button>
              )}
              {canApprove && (
                <Button variant="primary" onClick={() => setPendingAction('approve')}>
                  <CheckCircle2 />
                  Approve
                </Button>
              )}
              {canMarkPaid && (
                <Button variant="primary" onClick={() => setPendingAction('markPaid')}>
                  <Wallet />
                  Mark as Paid
                </Button>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle>Amount</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-1">
                  <span className="text-label text-text-tertiary">Amount</span>
                  <Money value={expense.amount} className="text-h3 font-medium text-text-primary" />
                </div>
                <div className="flex flex-col gap-1">
                  <span className="text-label text-text-tertiary">Tax</span>
                  <Money value={expense.tax} className="text-h3 font-medium text-text-primary" />
                </div>
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Details</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Vendor</span>
                  <span className="text-body text-text-primary">{expense.vendor || '—'}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Employee</span>
                  <span className="text-body text-text-primary">{expense.employeeName ?? '—'}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Payment method</span>
                  <span className="text-body text-text-primary">{expense.paymentMethod || '—'}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Added by</span>
                  <span className="text-body text-text-primary">{expense.addedByName ?? '—'}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Added</span>
                  <span className="text-body text-text-primary">{formatDateTime(expense.createdAt)}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Last updated</span>
                  <span className="text-body text-text-primary">{formatDateTime(expense.updatedAt)}</span>
                </div>
              </CardContent>
            </Card>

            {expense.receiptUrl && (
              <Card>
                <CardHeader>
                  <CardTitle>Receipt</CardTitle>
                </CardHeader>
                <CardContent>
                  <a
                    href={expense.receiptUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 text-body font-medium text-accent-500 hover:underline focus-visible:outline-none focus-visible:shadow-focus"
                  >
                    View receipt
                    <ExternalLink className="size-4" />
                  </a>
                </CardContent>
              </Card>
            )}

            <Card className={expense.receiptUrl ? 'lg:col-span-2' : 'lg:col-span-3'}>
              <CardHeader>
                <CardTitle>Notes</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-small text-text-primary">{expense.notes || 'No notes provided.'}</p>
              </CardContent>
            </Card>
          </div>

          <ExpenseFormSheet open={editOpen} onOpenChange={setEditOpen} projectId={expense.projectId} expense={expense} />

          {(['submit', 'approve', 'markPaid'] as WorkflowAction[]).map((action) => (
            <ConfirmationDialog
              key={action}
              open={pendingAction === action}
              onOpenChange={(open) => !open && setPendingAction(null)}
              title={ACTION_COPY[action].title}
              description={ACTION_COPY[action].description}
              confirmLabel={ACTION_COPY[action].confirmLabel}
              loading={workflowMutation.isPending && pendingAction === action}
              onConfirm={() => workflowMutation.mutate(action)}
            />
          ))}

          <ConfirmationDialog
            open={deleteOpen}
            onOpenChange={setDeleteOpen}
            title="Delete this expense?"
            description="This removes this draft expense permanently."
            confirmLabel="Delete expense"
            destructive
            loading={deleteMutation.isPending}
            onConfirm={() => deleteMutation.mutate()}
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
