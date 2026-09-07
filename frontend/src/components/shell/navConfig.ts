import { LayoutDashboard, Users, type LucideIcon } from 'lucide-react';

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

// Application_Shell_Navigation.md §"Role-Based Navigation": a group/item
// renders only once its module has shipped a real page — absent, never
// present-but-disabled. Every future module sprint appends its own entry
// here, never before its page is real.
export const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Overview',
    items: [{ label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard }],
  },
  {
    label: 'Workspace',
    items: [{ label: 'Clients', path: '/clients', icon: Users }],
  },
];
