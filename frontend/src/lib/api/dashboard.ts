import { apiClient, unwrap } from './client';

// Mirrors backend/apps/dashboard/serializers.py exactly (GET /reports/dashboard).
// BE-068: the five money fields are genuinely absent from the JSON (not
// null, not zero) for a caller without report.financial_access — declared
// optional here so the type itself forces every read site to handle
// "not present", rather than silently coercing a missing field to 0.
export interface DashboardKPIs {
  totalProjects: number;
  activeProjects: number;
  totalQuotations: number;
  totalBilledRevenue?: string;
  totalReceived?: string;
  pendingAmount?: string;
  totalExpenses?: string;
  netProfitLoss?: string;
}

export interface RecentProject {
  id: string;
  name: string;
  status: string;
  clientName: string;
  createdAt: string;
}

export interface RecentQuotation {
  id: string;
  quoteNumber: string;
  version: number;
  status: string;
  total: string;
  projectName: string;
}

/** Shared shape for both `pendingPayments` and `overdueInvoices`. */
export interface InvoiceSummary {
  id: string;
  invoiceNumber: string;
  total: string;
  dueDate: string | null;
  projectName: string;
}

export interface RecentExpense {
  id: string;
  category: string;
  amount: string;
  date: string;
  projectName: string;
}

export interface UpcomingDeadline {
  id: string;
  name: string;
  deadline: string;
}

export interface ProjectProfitability {
  projectId: string;
  projectName: string;
  revenue: string;
  expenses: string;
  profit: string;
}

export interface ActivityLogEntry {
  id: string;
  companyId: string | null;
  actorUserId: string | null;
  actorUserName: string | null;
  entityType: string;
  entityId: string;
  action: string;
  beforeState: Record<string, unknown> | null;
  afterState: Record<string, unknown> | null;
  requestId: string | null;
  ipAddress: string | null;
  createdAt: string;
}

// BE-068: `pendingPayments`/`overdueInvoices`/`recentExpenses`/
// `projectProfitability`/`recentActivities` are genuinely financial (the
// last one because its audit-log beforeState/afterState snapshots can
// contain real invoice/payment amounts) and are entirely absent from the
// response for a caller without report.financial_access — optional here
// for the same reason as DashboardKPIs' money fields. `canViewFinancials`
// is a UX convenience only; the omission above is what's actually
// authoritative, not this flag.
export interface DashboardData {
  canViewFinancials: boolean;
  kpis: DashboardKPIs;
  recentProjects: RecentProject[];
  recentQuotations: RecentQuotation[];
  pendingPayments?: InvoiceSummary[];
  overdueInvoices?: InvoiceSummary[];
  recentExpenses?: RecentExpense[];
  upcomingDeadlines: UpcomingDeadline[];
  recentActivities?: ActivityLogEntry[];
  projectProfitability?: ProjectProfitability[];
}

export async function getDashboard(): Promise<DashboardData> {
  return unwrap<DashboardData>(apiClient.get('/reports/dashboard'));
}
