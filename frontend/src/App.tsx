import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from '@/context/AuthContext';
import { ThemeProvider } from '@/theme/ThemeProvider';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Toaster } from '@/components/ui/sonner';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Shell } from '@/components/shell/Shell';
import { queryClient } from '@/lib/queryClient';
import LoginPage from '@/pages/LoginPage';
import DashboardPage from '@/pages/DashboardPage';
import ClientsListPage from '@/pages/clients/ClientsListPage';
import ClientDetailPage from '@/pages/clients/ClientDetailPage';
import ProjectsListPage from '@/pages/projects/ProjectsListPage';
import ProjectWorkspaceLayout from '@/pages/projects/ProjectWorkspaceLayout';
import ProjectOverviewTab from '@/pages/projects/ProjectOverviewTab';
import ProjectTeamTab from '@/pages/projects/ProjectTeamTab';
import ProjectBOQTab from '@/pages/projects/ProjectBOQTab';
import ProjectQuotationsTab from '@/pages/projects/ProjectQuotationsTab';
import QuotationDetailPage from '@/pages/QuotationDetailPage';
import ProjectInvoicesTab from '@/pages/projects/ProjectInvoicesTab';
import InvoiceDetailPage from '@/pages/InvoiceDetailPage';
import ProductsListPage from '@/pages/products/ProductsListPage';
import ProductDetailPage from '@/pages/products/ProductDetailPage';
import ProductCategoriesPage from '@/pages/settings/ProductCategoriesPage';

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <TooltipProvider>
          <AuthProvider>
            <BrowserRouter>
              <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route
                  path="/*"
                  element={
                    <ProtectedRoute>
                      <Shell>
                        <Routes>
                          <Route path="/" element={<Navigate to="/dashboard" replace />} />
                          <Route path="/dashboard" element={<DashboardPage />} />
                          <Route path="/clients" element={<ClientsListPage />} />
                          <Route path="/clients/:clientId" element={<ClientDetailPage />} />
                          <Route path="/projects" element={<ProjectsListPage />} />
                          <Route path="/projects/:projectId" element={<ProjectWorkspaceLayout />}>
                            <Route index element={<Navigate to="overview" replace />} />
                            <Route path="overview" element={<ProjectOverviewTab />} />
                            <Route path="team" element={<ProjectTeamTab />} />
                            <Route path="boq" element={<ProjectBOQTab />} />
                            <Route path="quotations" element={<ProjectQuotationsTab />} />
                            <Route path="invoices" element={<ProjectInvoicesTab />} />
                          </Route>
                          <Route path="/quotations/:quotationId" element={<QuotationDetailPage />} />
                          <Route path="/invoices/:invoiceId" element={<InvoiceDetailPage />} />
                          <Route path="/products" element={<ProductsListPage />} />
                          <Route path="/products/:productId" element={<ProductDetailPage />} />
                          <Route path="/settings/product-categories" element={<ProductCategoriesPage />} />
                          <Route path="*" element={<Navigate to="/dashboard" replace />} />
                        </Routes>
                      </Shell>
                    </ProtectedRoute>
                  }
                />
              </Routes>
            </BrowserRouter>
            <Toaster />
          </AuthProvider>
        </TooltipProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export default App;
