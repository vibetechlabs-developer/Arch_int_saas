import { useQuery } from '@tanstack/react-query';
import { Receipt } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { Money } from '@/components/common/Money';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { RestrictedState } from '@/components/common/RestrictedState';
import { ApiError } from '@/lib/api/client';
import { getExpenseReport, type ExpenseReportEntry, type ReportFilters } from '@/lib/api/reports';
import { reportKeys } from '@/lib/queryKeys';

export interface ExpenseReportPanelProps {
  filters: ReportFilters;
}

const GROUPS: { key: 'byCategory' | 'byProject' | 'byVendor' | 'byEmployee' | 'byDate'; label: string; column: string; fallback: string }[] = [
  { key: 'byCategory', label: 'Category', column: 'Category', fallback: 'Uncategorized' },
  { key: 'byProject', label: 'Project', column: 'Project', fallback: 'Unknown project' },
  { key: 'byVendor', label: 'Vendor', column: 'Vendor', fallback: 'No vendor' },
  { key: 'byEmployee', label: 'Employee', column: 'Employee', fallback: 'Unassigned' },
  { key: 'byDate', label: 'Date', column: 'Date', fallback: 'Unspecified' },
];

// Deliberately shows no summed "Total" footer row: each breakdown includes
// every non-deleted expense regardless of approval_status (a broader scope
// than FinanceReportService's approved/paid-only `expenses` figure), so a
// client-computed sum here would not equal — and would be mistaken for —
// that authoritative figure. Only backend-returned per-row totals are
// rendered.
export function ExpenseReportPanel({ filters }: ExpenseReportPanelProps) {
  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: reportKeys.expenses(filters),
    queryFn: () => getExpenseReport(filters),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          <Receipt className="size-4 text-accent-500" />
          Expense Breakdown
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isError ? (
          error instanceof ApiError && error.status === 403 ? (
            <RestrictedState message={error.message} />
          ) : (
            <ErrorState error={error} onRetry={() => refetch()} />
          )
        ) : isLoading || !data ? (
          <TableSkeleton />
        ) : (
          <Tabs defaultValue="byCategory">
            <TabsList>
              {GROUPS.map((group) => (
                <TabsTrigger key={group.key} value={group.key}>
                  {group.label}
                </TabsTrigger>
              ))}
            </TabsList>
            {GROUPS.map((group) => (
              <TabsContent key={group.key} value={group.key}>
                <BreakdownTable rows={data[group.key]} column={group.column} fallback={group.fallback} />
              </TabsContent>
            ))}
          </Tabs>
        )}
      </CardContent>
    </Card>
  );
}

function BreakdownTable({ rows, column, fallback }: { rows: ExpenseReportEntry[]; column: string; fallback: string }) {
  if (rows.length === 0) {
    return (
      <EmptyState
        icon={Receipt}
        title="No expense data for this period"
        description="Adjust the filters or select a different date range."
      />
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{column}</TableHead>
          <TableHead className="text-right">Total</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row, i) => (
          <TableRow key={row.key ?? `${fallback}-${i}`}>
            <TableCell>{row.label || fallback}</TableCell>
            <TableCell className="text-right">
              <Money value={row.total} />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

function TableSkeleton() {
  return (
    <div className="flex flex-col gap-3 py-1">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-6 w-full" />
      ))}
    </div>
  );
}
