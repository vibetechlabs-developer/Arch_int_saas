import { useState } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { PageHeader } from '@/components/common/PageHeader';
import { ReportFilterBar } from '@/components/reports/ReportFilterBar';
import { FinanceReportPanel } from '@/components/reports/FinanceReportPanel';
import { ExpenseReportPanel } from '@/components/reports/ExpenseReportPanel';
import type { ReportFilters } from '@/lib/api/reports';
import { pageTransition, pageTransitionReduced } from '@/lib/motion';

const EMPTY_FILTERS: ReportFilters = {};

// Only two report endpoints exist today (GET /reports/finance, GET
// /reports/expenses) — both company-wide, both gated by
// report.financial_access. There is no separate Project/Client/Sales
// report endpoint, so this page deliberately has no such tabs; adding
// them would be UI for a capability the backend doesn't have.
export default function ReportsPage() {
  const shouldReduceMotion = useReducedMotion();
  const [filters, setFilters] = useState<ReportFilters>(EMPTY_FILTERS);

  const updateFilters = (patch: Partial<ReportFilters>) => setFilters((prev) => ({ ...prev, ...patch }));

  return (
    <motion.div
      variants={shouldReduceMotion ? pageTransitionReduced : pageTransition}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-6"
    >
      <PageHeader title="Reports" description="Financial performance and expense breakdowns for the company." />

      <ReportFilterBar value={filters} onChange={updateFilters} onClearAll={() => setFilters(EMPTY_FILTERS)} />

      <FinanceReportPanel filters={filters} />
      <ExpenseReportPanel filters={filters} />
    </motion.div>
  );
}
