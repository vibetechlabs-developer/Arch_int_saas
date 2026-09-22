import { Suspense, lazy } from 'react';
import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from '@/context/AuthContext';
import { ThemeProvider } from '@/theme/ThemeProvider';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Toaster } from '@/components/ui/sonner';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { ProtectedPlatformRoute } from '@/components/ProtectedPlatformRoute';
import { Shell } from '@/components/shell/Shell';
import { PlatformShell } from '@/components/platform/PlatformShell';
import { PageLoadingFallback } from '@/components/common/PageLoadingFallback';
import { queryClient } from '@/lib/queryClient';

// Every page is its own lazy-loaded chunk rather than one monolithic
// bundle (the production build previously warned about a 1MB+ single
// chunk) -- Vite/Rollup splits each of these into its own file
// automatically, fetched only when its route is actually visited.
// Shell/ProtectedRoute/providers stay eager: they're needed on every
// route regardless, so deferring them would only add a second waterfall
// for no payload benefit.
const LoginPage = lazy(() => import('@/pages/LoginPage'));
const SetPasswordPage = lazy(() => import('@/pages/SetPasswordPage'));
const DashboardPage = lazy(() => import('@/pages/DashboardPage'));
const ReportsPage = lazy(() => import('@/pages/ReportsPage'));
const ClientsListPage = lazy(() => import('@/pages/clients/ClientsListPage'));
const ClientDetailPage = lazy(() => import('@/pages/clients/ClientDetailPage'));
const LeadsListPage = lazy(() => import('@/pages/leads/LeadsListPage'));
const LeadDetailPage = lazy(() => import('@/pages/leads/LeadDetailPage'));
const SiteVisitsListPage = lazy(() => import('@/pages/siteVisits/SiteVisitsListPage'));
const SiteVisitDetailPage = lazy(() => import('@/pages/siteVisits/SiteVisitDetailPage'));
const ProjectsListPage = lazy(() => import('@/pages/projects/ProjectsListPage'));
const ProjectWorkspaceLayout = lazy(() => import('@/pages/projects/ProjectWorkspaceLayout'));
const ProjectOverviewTab = lazy(() => import('@/pages/projects/ProjectOverviewTab'));
const ProjectTeamTab = lazy(() => import('@/pages/projects/ProjectTeamTab'));
const ProjectBOQTab = lazy(() => import('@/pages/projects/ProjectBOQTab'));
const ProjectQuotationsTab = lazy(() => import('@/pages/projects/ProjectQuotationsTab'));
const QuotationDetailPage = lazy(() => import('@/pages/QuotationDetailPage'));
const ProjectInvoicesTab = lazy(() => import('@/pages/projects/ProjectInvoicesTab'));
const InvoiceDetailPage = lazy(() => import('@/pages/InvoiceDetailPage'));
const ProjectExpensesTab = lazy(() => import('@/pages/projects/ProjectExpensesTab'));
const ExpenseDetailPage = lazy(() => import('@/pages/ExpenseDetailPage'));
const ProjectDocumentsTab = lazy(() => import('@/pages/projects/ProjectDocumentsTab'));
const ProductsListPage = lazy(() => import('@/pages/products/ProductsListPage'));
const ProductDetailPage = lazy(() => import('@/pages/products/ProductDetailPage'));
const ProductCategoriesPage = lazy(() => import('@/pages/settings/ProductCategoriesPage'));
const SettingsLayout = lazy(() => import('@/pages/settings/SettingsLayout'));
const SettingsLandingPage = lazy(() => import('@/pages/settings/SettingsLandingPage'));
const CompanySettingsPage = lazy(() => import('@/pages/settings/CompanySettingsPage'));
const MembersPage = lazy(() => import('@/pages/settings/MembersPage'));
const RolesPage = lazy(() => import('@/pages/settings/RolesPage'));
const PermissionsPage = lazy(() => import('@/pages/settings/PermissionsPage'));
const ProfilePage = lazy(() => import('@/pages/settings/ProfilePage'));
const SecurityPage = lazy(() => import('@/pages/settings/SecurityPage'));
const PlatformLoginPage = lazy(() => import('@/pages/platform/PlatformLoginPage'));
const PlatformCompaniesListPage = lazy(() => import('@/pages/platform/PlatformCompaniesListPage'));
const PlatformCompanyDetailPage = lazy(() => import('@/pages/platform/PlatformCompanyDetailPage'));

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <TooltipProvider>
          <AuthProvider>
            <BrowserRouter>
              <Suspense fallback={<PageLoadingFallback />}>
                <Routes>
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/reset-password" element={<SetPasswordPage />} />
                  <Route path="/platform/login" element={<PlatformLoginPage />} />
                  <Route
                    path="/platform/*"
                    element={
                      <ProtectedPlatformRoute>
                        <PlatformShell>
                          <Suspense fallback={<PageLoadingFallback />}>
                            <Routes>
                              <Route path="/platform" element={<Navigate to="/platform/companies" replace />} />
                              <Route path="/platform/companies" element={<PlatformCompaniesListPage />} />
                              <Route path="/platform/companies/:companyId" element={<PlatformCompanyDetailPage />} />
                              <Route path="*" element={<Navigate to="/platform/companies" replace />} />
                            </Routes>
                          </Suspense>
                        </PlatformShell>
                      </ProtectedPlatformRoute>
                    }
                  />
                  <Route
                    path="/*"
                    element={
                      <ProtectedRoute>
                        <Shell>
                          <Suspense fallback={<PageLoadingFallback />}>
                            <Routes>
                              <Route path="/" element={<Navigate to="/dashboard" replace />} />
                              <Route path="/dashboard" element={<DashboardPage />} />
                              <Route path="/reports" element={<ReportsPage />} />
                              <Route path="/clients" element={<ClientsListPage />} />
                              <Route path="/clients/:clientId" element={<ClientDetailPage />} />
                              <Route path="/leads" element={<LeadsListPage />} />
                              <Route path="/leads/:leadId" element={<LeadDetailPage />} />
                              <Route path="/site-visits" element={<SiteVisitsListPage />} />
                              <Route path="/site-visits/:siteVisitId" element={<SiteVisitDetailPage />} />
                              <Route path="/projects" element={<ProjectsListPage />} />
                              <Route path="/projects/:projectId" element={<ProjectWorkspaceLayout />}>
                                <Route index element={<Navigate to="overview" replace />} />
                                <Route path="overview" element={<ProjectOverviewTab />} />
                                <Route path="team" element={<ProjectTeamTab />} />
                                <Route path="boq" element={<ProjectBOQTab />} />
                                <Route path="quotations" element={<ProjectQuotationsTab />} />
                                <Route path="invoices" element={<ProjectInvoicesTab />} />
                                <Route path="expenses" element={<ProjectExpensesTab />} />
                                <Route path="documents" element={<ProjectDocumentsTab />} />
                              </Route>
                              <Route path="/quotations/:quotationId" element={<QuotationDetailPage />} />
                              <Route path="/invoices/:invoiceId" element={<InvoiceDetailPage />} />
                              <Route path="/expenses/:expenseId" element={<ExpenseDetailPage />} />
                              <Route path="/products" element={<ProductsListPage />} />
                              <Route path="/products/:productId" element={<ProductDetailPage />} />
                              <Route path="/settings" element={<SettingsLayout />}>
                                <Route index element={<SettingsLandingPage />} />
                                <Route path="company" element={<CompanySettingsPage />} />
                                <Route path="members" element={<MembersPage />} />
                                <Route path="roles" element={<RolesPage />} />
                                <Route path="permissions" element={<PermissionsPage />} />
                                <Route path="product-categories" element={<ProductCategoriesPage />} />
                                <Route path="profile" element={<ProfilePage />} />
                                <Route path="security" element={<SecurityPage />} />
                              </Route>
                              <Route path="*" element={<Navigate to="/dashboard" replace />} />
                            </Routes>
                          </Suspense>
                        </Shell>
                      </ProtectedRoute>
                    }
                  />
                </Routes>
              </Suspense>
            </BrowserRouter>
            <Toaster />
          </AuthProvider>
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export default App;
