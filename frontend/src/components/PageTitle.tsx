import { useEffect } from 'react';
import { matchPath, useLocation } from 'react-router-dom';

const APP_NAME = 'INT Projects';

// First match wins, so more specific patterns come before their parents.
// Names what the user is looking at (not the app) so several open tabs are
// tellable apart -- every tab used to read "Architecture SAS".
const TITLES: Array<{ pattern: string; title: string }> = [
  { pattern: '/login', title: 'Sign in' },
  { pattern: '/forgot-password', title: 'Forgot password' },
  { pattern: '/reset-password', title: 'Set your password' },
  { pattern: '/platform/login', title: 'Platform sign in' },
  { pattern: '/platform/companies/:companyId', title: 'Company' },
  { pattern: '/platform/companies', title: 'Companies' },
  { pattern: '/platform', title: 'Companies' },
  { pattern: '/dashboard', title: 'Dashboard' },
  { pattern: '/reports', title: 'Reports' },
  { pattern: '/clients/:clientId', title: 'Client' },
  { pattern: '/clients', title: 'Clients' },
  { pattern: '/leads/:leadId', title: 'Lead' },
  { pattern: '/leads', title: 'Leads' },
  { pattern: '/site-visits/:siteVisitId', title: 'Site visit' },
  { pattern: '/site-visits', title: 'Site visits' },
  { pattern: '/projects/:projectId/*', title: 'Project' },
  { pattern: '/projects', title: 'Projects' },
  { pattern: '/quotations/:quotationId', title: 'Quotation' },
  { pattern: '/invoices/:invoiceId', title: 'Invoice' },
  { pattern: '/expenses/:expenseId', title: 'Expense' },
  { pattern: '/products/:productId', title: 'Product' },
  { pattern: '/products', title: 'Products' },
  { pattern: '/settings/company', title: 'Company settings' },
  { pattern: '/settings/members', title: 'Members' },
  { pattern: '/settings/roles', title: 'Roles & permissions' },
  { pattern: '/settings/permissions', title: 'Permission catalog' },
  { pattern: '/settings/product-categories', title: 'Product categories' },
  { pattern: '/settings/profile', title: 'Profile' },
  { pattern: '/settings/security', title: 'Security' },
  { pattern: '/settings', title: 'Settings' },
];

export function titleForPath(pathname: string): string {
  if (pathname === '/') return APP_NAME;
  const hit = TITLES.find(({ pattern }) => matchPath({ path: pattern, end: true }, pathname));
  return hit ? `${hit.title} · ${APP_NAME}` : `Page not found · ${APP_NAME}`;
}

// Renders nothing -- keeps document.title in step with the route.
export function PageTitle() {
  const { pathname } = useLocation();

  useEffect(() => {
    document.title = titleForPath(pathname);
  }, [pathname]);

  return null;
}
