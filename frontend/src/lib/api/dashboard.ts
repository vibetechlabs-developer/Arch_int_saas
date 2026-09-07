import { apiClient, unwrap } from './client';

// Mirrors backend/apps/dashboard/serializers.py exactly (GET /reports/dashboard).
export interface DashboardKPIs {
  totalProjects: number;
  activeProjects: number;
  totalQuotations: number;
  totalBilledRevenue: string;
  totalReceived: string;
  pendingAmount: string;
  totalExpenses: string;
  netProfitLoss: string;
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

export interface DashboardData {
  kpis: DashboardKPIs;
  recentProjects: RecentProject[];
  recentQuotations: RecentQuotation[];
  pendingPayments: InvoiceSummary[];
  overdueInvoices: InvoiceSummary[];
  recentExpenses: RecentExpense[];
  upcomingDeadlines: UpcomingDeadline[];
  recentActivities: ActivityLogEntry[];
  projectProfitability: ProjectProfitability[];
}

export async function getDashboard(): Promise<DashboardData> {
  return unwrap<DashboardData>(apiClient.get('/reports/dashboard'));
}
