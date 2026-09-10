import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion, useReducedMotion } from 'framer-motion';
import {
  AlertCircle,
  Banknote,
  CalendarClock,
  Clock,
  FileText,
  FolderKanban,
  Receipt,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { StatCard } from '@/components/common/StatCard';
import { StatusBadge } from '@/components/common/StatusBadge';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { Timeline } from '@/components/common/Timeline';
import { getDashboard, type DashboardKPIs } from '@/lib/api/dashboard';
import { useAuth } from '@/context/AuthContext';
import { formatCurrency, formatDate, formatDateTime, humanizeAction, humanizeEntityType } from '@/lib/format';
import { fadeInUp, fadeInUpReduced, pageTransition, pageTransitionReduced, staggerContainer } from '@/lib/motion';
import { useCountUp } from '@/lib/useCountUp';
import { cn } from '@/lib/utils';

export default function DashboardPage() {
  const { user } = useAuth();
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
  });

  const greeting = getGreeting();
  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

  const shouldReduceMotion = useReducedMotion();

  if (isError) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  return (
    <motion.div
      variants={shouldReduceMotion ? pageTransitionReduced : pageTransition}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-8"
    >
      <div className="flex flex-col gap-1">
        <h2 className="font-display text-h1 font-medium tracking-tight text-text-primary">
          {greeting}
          {user ? `, ${user.name.split(' ')[0]}` : ''}
        </h2>
        <p className="text-body text-text-secondary">{today} — here's what needs your attention.</p>
      </div>

      {isLoading || !data ? (
        <KpiSkeleton />
      ) : (
        <KpiStrip kpis={data.kpis} canViewFinancials={data.canViewFinancials} />
      )}

      {/* Pending Payments / Overdue Invoices carry real invoice amounts —
          only rendered once the response actually includes them
          (report.financial_access). Omitted, not shown empty: an absent
          section here means "not visible to you", never "there are
          none" — a restricted user must never see a false "no pending
          payments"/"nothing overdue" claim. */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {(isLoading || data?.canViewFinancials) && (
          <AttentionPanel
            title="Pending Payments"
            icon={Clock}
            isLoading={isLoading}
            items={data?.pendingPayments}
            renderItem={(item) => (
              <InvoiceRow key={item.id} invoiceNumber={item.invoiceNumber} projectName={item.projectName} total={item.total} sub={item.dueDate ? `Due ${formatDate(item.dueDate)}` : 'No due date'} />
            )}
            emptyTitle="No pending payments"
            emptyDescription="Every sent invoice has been paid."
          />
        )}
        {(isLoading || data?.canViewFinancials) && (
          <AttentionPanel
            title="Overdue Invoices"
            icon={AlertCircle}
            isLoading={isLoading}
            items={data?.overdueInvoices}
            renderItem={(item) => (
              <InvoiceRow key={item.id} invoiceNumber={item.invoiceNumber} projectName={item.projectName} total={item.total} sub={item.dueDate ? `Was due ${formatDate(item.dueDate)}` : 'No due date'} danger />
            )}
            emptyTitle="Nothing overdue"
            emptyDescription="All invoices are within their payment terms."
          />
        )}
        <AttentionPanel
          title="Upcoming Deadlines"
          icon={CalendarClock}
          isLoading={isLoading}
          items={data?.upcomingDeadlines}
          renderItem={(item) => (
            <div key={item.id} className="flex items-center justify-between py-2">
              <span className="text-small text-text-primary">{item.name}</span>
              <span className="text-caption text-text-tertiary">{formatDate(item.deadline)}</span>
            </div>
          )}
          emptyTitle="Nothing due soon"
          emptyDescription="No project deadlines in the next 30 days."
        />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>
              <FolderKanban className="size-4 text-accent-500" />
              Recent Projects
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-1">
            {isLoading ? (
              <ListSkeleton />
            ) : data && data.recentProjects.length > 0 ? (
              data.recentProjects.map((project) => (
                <div key={project.id} className="flex items-center justify-between py-2">
                  <div className="flex flex-col">
                    <span className="text-small font-medium text-text-primary">{project.name}</span>
                    <span className="text-caption text-text-tertiary">{project.clientName}</span>
                  </div>
                  <StatusBadge status={project.status} />
                </div>
              ))
            ) : (
              <EmptyState icon={FolderKanban} title="No projects yet" description="Projects you create will show up here." />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              <FileText className="size-4 text-accent-500" />
              Recent Quotations
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-1">
            {isLoading ? (
              <ListSkeleton />
            ) : data && data.recentQuotations.length > 0 ? (
              data.recentQuotations.map((quotation) => (
                <div key={quotation.id} className="flex items-center justify-between py-2">
                  <div className="flex flex-col">
                    <span className="text-small font-medium text-text-primary">{quotation.quoteNumber}</span>
                    <span className="text-caption text-text-tertiary">{quotation.projectName}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={quotation.status} />
                    <span className="text-small tabular-nums text-text-primary">{formatCurrency(quotation.total)}</span>
                  </div>
                </div>
              ))
            ) : (
              <EmptyState icon={FileText} title="No quotations yet" description="Quotations you create will show up here." />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent Expenses / Project Profitability / Recent Activity are all
          financial or (for Activity) can embed financial figures in an
          audit snapshot — same omit-don't-fake-empty rule as above. */}
      {(isLoading || data?.canViewFinancials) && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle>
                <Receipt className="size-4 text-accent-500" />
                Recent Expenses
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-1">
              {isLoading ? (
                <ListSkeleton />
              ) : data && data.recentExpenses && data.recentExpenses.length > 0 ? (
                data.recentExpenses.map((expense) => (
                  <div key={expense.id} className="flex items-center justify-between py-2">
                    <div className="flex flex-col">
                      <span className="text-small font-medium text-text-primary">{expense.category}</span>
                      <span className="text-caption text-text-tertiary">
                        {expense.projectName} · {formatDate(expense.date)}
                      </span>
                    </div>
                    <span className="text-small tabular-nums text-text-primary">{formatCurrency(expense.amount)}</span>
                  </div>
                ))
              ) : (
                <EmptyState icon={Receipt} title="No expenses yet" description="Logged expenses will show up here." />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>
                <TrendingUp className="size-4 text-accent-500" />
                Project Profitability
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-1">
              {isLoading ? (
                <ListSkeleton />
              ) : data && data.projectProfitability && data.projectProfitability.length > 0 ? (
                data.projectProfitability.map((row) => (
                  <div key={row.projectId} className="flex items-center justify-between py-2">
                    <span className="text-small font-medium text-text-primary">{row.projectName}</span>
                    <span
                      className={
                        'text-small tabular-nums font-medium ' +
                        (Number(row.profit) < 0 ? 'text-danger-text' : 'text-success-text')
                      }
                    >
                      {formatCurrency(row.profit)}
                    </span>
                  </div>
                ))
              ) : (
                <EmptyState icon={TrendingUp} title="No active projects" description="Profitability appears once a project is active." />
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {(isLoading || data?.canViewFinancials) && (
        <Card>
          <CardHeader>
            <CardTitle>
              <Banknote className="size-4 text-accent-500" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <ListSkeleton />
            ) : data && data.recentActivities && data.recentActivities.length > 0 ? (
              <Timeline
                entries={data.recentActivities.map((activity) => ({
                  id: activity.id,
                  title: `${activity.actorUserName ?? 'System'} ${humanizeAction(activity.action)}d ${humanizeEntityType(activity.entityType)}`,
                  meta: formatDateTime(activity.createdAt),
                }))}
              />
            ) : (
              <EmptyState icon={Banknote} title="No activity yet" description="Actions across your workspace will show up here." />
            )}
          </CardContent>
        </Card>
      )}
    </motion.div>
  );
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 18) return 'Good afternoon';
  return 'Good evening';
}

// Editorial composition, not a repeated 4/4-box grid: revenue is the
// featured story (with received/pending as its own sub-narrative), net
// profit gets its own emphasis since it's the bottom line, and the
// remaining counts sit as smaller, clearly secondary tiles underneath.
//
// BE-068: `canViewFinancials` is the only thing that decides whether the
// revenue/net-profit/expenses cards render at all -- never a fallback of
// `Number(kpis.totalBilledRevenue) || 0`, which would silently show a
// fake ₹0 for a restricted caller (the field is genuinely absent from
// `kpis`, not zero) and misrepresent "you can't see this" as "this is
// zero". Operational counts (projects/quotations) always render.
function KpiStrip({ kpis, canViewFinancials }: { kpis: DashboardKPIs; canViewFinancials: boolean }) {
  const shouldReduceMotion = useReducedMotion();
  const itemVariants = shouldReduceMotion ? fadeInUpReduced : fadeInUp;

  const operational: { label: string; numericValue: number }[] = [
    { label: 'Total Projects', numericValue: Number(kpis.totalProjects) || 0 },
    { label: 'Active Projects', numericValue: Number(kpis.activeProjects) || 0 },
    { label: 'Total Quotations', numericValue: Number(kpis.totalQuotations) || 0 },
  ];

  return (
    <motion.div variants={staggerContainer} initial="hidden" animate="show" className="flex flex-col gap-4">
      {canViewFinancials && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <motion.div variants={itemVariants} className="lg:col-span-2">
            <RevenuePanel
              billed={Number(kpis.totalBilledRevenue) || 0}
              received={Number(kpis.totalReceived) || 0}
              pending={Number(kpis.pendingAmount) || 0}
            />
          </motion.div>
          <motion.div variants={itemVariants}>
            <NetProfitCard value={Number(kpis.netProfitLoss) || 0} />
          </motion.div>
        </div>
      )}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {operational.map((card) => (
          <motion.div key={card.label} variants={itemVariants}>
            <StatCard label={card.label} numericValue={card.numericValue} compact />
          </motion.div>
        ))}
        {canViewFinancials && (
          <motion.div variants={itemVariants}>
            <StatCard
              label="Total Expenses"
              numericValue={Number(kpis.totalExpenses) || 0}
              format={formatCurrency}
              compact
            />
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}

function RevenuePanel({ billed, received, pending }: { billed: number; received: number; pending: number }) {
  const animatedBilled = useCountUp(billed);
  return (
    <Card className="flex h-full flex-col justify-between gap-6 p-6">
      <div className="flex flex-col gap-1.5">
        <span className="text-label text-text-tertiary">Total Billed Revenue</span>
        <motion.span
          key={billed}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.2 }}
          className="font-display text-display tabular-nums tracking-tight text-text-primary"
        >
          {formatCurrency(animatedBilled)}
        </motion.span>
      </div>
      <div className="flex flex-wrap items-start gap-8 border-t border-border-subtle pt-4">
        <MiniStat label="Received" value={received} tone="success" />
        <MiniStat label="Pending" value={pending} tone="warning" />
      </div>
    </Card>
  );
}

function MiniStat({ label, value, tone }: { label: string; value: number; tone: 'success' | 'warning' }) {
  const animated = useCountUp(value);
  return (
    <div className="flex flex-col gap-1">
      <span className="text-caption text-text-tertiary">{label}</span>
      <span
        className={cn(
          'text-h3 tabular-nums font-medium',
          tone === 'success' ? 'text-success-text' : 'text-warning-text',
        )}
      >
        {formatCurrency(animated)}
      </span>
    </div>
  );
}

function NetProfitCard({ value }: { value: number }) {
  const animated = useCountUp(value);
  const isPositive = value >= 0;
  return (
    <Card className="flex h-full flex-col justify-between gap-4 p-6">
      <div className="flex items-center justify-between">
        <span className="text-label text-text-tertiary">Net Profit / Loss</span>
        {isPositive ? (
          <TrendingUp className="size-4 text-success-text" />
        ) : (
          <TrendingDown className="size-4 text-danger-text" />
        )}
      </div>
      <span
        className={cn(
          'text-kpi tabular-nums tracking-tight',
          isPositive ? 'text-success-text' : 'text-danger-text',
        )}
      >
        {formatCurrency(animated)}
      </span>
      <span className="text-small text-text-secondary">
        {isPositive ? 'Profitable this period' : 'Operating at a loss this period'}
      </span>
    </Card>
  );
}

function KpiSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="flex flex-col gap-6 p-6 lg:col-span-2">
          <Skeleton className="h-3 w-32" />
          <Skeleton className="h-10 w-48" />
        </Card>
        <Card className="flex flex-col gap-4 p-6">
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-8 w-32" />
        </Card>
      </div>
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} className="flex flex-col gap-2.5 p-4">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-6 w-24" />
          </Card>
        ))}
      </div>
    </div>
  );
}

function ListSkeleton() {
  return (
    <div className="flex flex-col gap-3 py-1">
      {Array.from({ length: 3 }).map((_, i) => (
        <Skeleton key={i} className="h-5 w-full" />
      ))}
    </div>
  );
}

function InvoiceRow({
  invoiceNumber,
  projectName,
  total,
  sub,
  danger,
}: {
  invoiceNumber: string;
  projectName: string;
  total: string;
  sub: string;
  danger?: boolean;
}) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="flex flex-col">
        <span className="text-small font-medium text-text-primary">{invoiceNumber}</span>
        <span className="text-caption text-text-tertiary">{projectName}</span>
      </div>
      <div className="flex flex-col items-end">
        <span className="text-small tabular-nums text-text-primary">{formatCurrency(total)}</span>
        <span className={'text-caption ' + (danger ? 'text-danger-text' : 'text-text-tertiary')}>{sub}</span>
      </div>
    </div>
  );
}

function AttentionPanel<T>({
  title,
  icon: Icon,
  isLoading,
  items,
  renderItem,
  emptyTitle,
  emptyDescription,
}: {
  title: string;
  icon: typeof Clock;
  isLoading: boolean;
  items: T[] | undefined;
  renderItem: (item: T) => ReactNode;
  emptyTitle: string;
  emptyDescription: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <Icon className="size-4 text-accent-500" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col divide-y divide-border-subtle">
        {isLoading ? (
          <ListSkeleton />
        ) : items && items.length > 0 ? (
          items.map(renderItem)
        ) : (
          <EmptyState icon={Icon} title={emptyTitle} description={emptyDescription} />
        )}
      </CardContent>
    </Card>
  );
}

