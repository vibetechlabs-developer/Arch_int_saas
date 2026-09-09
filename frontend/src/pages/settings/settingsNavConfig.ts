import { Building2, KeyRound, ShieldCheck, User, Users, FolderTree, type LucideIcon } from 'lucide-react';

export interface SettingsNavItem {
  label: string;
  path: string;
  icon: LucideIcon;
  description: string;
}

export interface SettingsNavGroup {
  label: string;
  items: SettingsNavItem[];
}

// Settings' own internal navigation (distinct from the primary app
// sidebar, which links here only once via a single "Settings" entry).
export const SETTINGS_NAV_GROUPS: SettingsNavGroup[] = [
  {
    label: 'Organization',
    items: [
      { label: 'Company', path: '/settings/company', icon: Building2, description: 'Profile, currency, tax details' },
      { label: 'Members', path: '/settings/members', icon: Users, description: 'Invite and manage your team' },
      { label: 'Roles & Permissions', path: '/settings/roles', icon: ShieldCheck, description: 'Define what each role can do' },
      { label: 'Product Categories', path: '/settings/product-categories', icon: FolderTree, description: 'Organize the product catalog' },
    ],
  },
  {
    label: 'Personal',
    items: [
      { label: 'Profile', path: '/settings/profile', icon: User, description: 'Your account details' },
      { label: 'Security', path: '/settings/security', icon: KeyRound, description: 'Password and login security' },
    ],
  },
];

export const ALL_SETTINGS_NAV_ITEMS = SETTINGS_NAV_GROUPS.flatMap((group) => group.items);
