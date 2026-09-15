import { BarChart3, CalendarCheck, FolderKanban, LayoutDashboard, Package, Settings, UserRoundSearch, Users, type LucideIcon } from 'lucide-react';

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
  /**
   * Extra route prefixes that should also mark this item active, for a
   * page that lives outside its own `path` subtree but is conceptually
   * part of the same module (e.g. Product Categories, which manages
   * Products' taxonomy but is routed under /settings — not /products —
   * since it isn't itself a product record).
   */
  matchPaths?: string[];
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

// Application_Shell_Navigation.md §"Role-Based Navigation": a group/item
// renders only once its module has shipped a real page — absent, never
// present-but-disabled. Every future module sprint appends its own entry
// here, never before its page is real.
//
// Deliberately NOT listed here as their own top-level items: BOQ,
// Quotations, Invoices, Payments, Expenses, Documents. Every one of these
// is project-scoped (nested under /projects/:projectId/*) or, for
// Payments, invoice-scoped (inside Invoice detail) — there is no
// company-wide list endpoint or page for any of them. They're reached via
// Project Workspace / Invoice Detail, not the primary sidebar; adding them
// here would either 404 with no context or require inventing a
// company-wide page the backend doesn't support. Activity is excluded
// entirely — see FRONTEND_TASKS.md's Phase 10 (Blocked).
export const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Overview',
    items: [{ label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard }],
  },
  {
    label: 'Workspace',
    items: [
      { label: 'Leads', path: '/leads', icon: UserRoundSearch },
      { label: 'Site Visits', path: '/site-visits', icon: CalendarCheck },
      { label: 'Clients', path: '/clients', icon: Users },
      { label: 'Projects', path: '/projects', icon: FolderKanban },
    ],
  },
  {
    label: 'Commercial',
    items: [
      { label: 'Products', path: '/products', icon: Package },
      { label: 'Reports', path: '/reports', icon: BarChart3 },
    ],
  },
  {
    label: 'Account',
    items: [{ label: 'Settings', path: '/settings', icon: Settings }],
  },
];
