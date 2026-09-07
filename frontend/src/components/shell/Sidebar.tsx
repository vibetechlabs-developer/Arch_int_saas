import { Building2, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SidebarNav } from './SidebarNav';

export interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

// Application_Shell_Navigation.md §Sidebar: bg-surface-secondary, no
// workspace switcher (flagged gap #1 — no memberships-list endpoint yet),
// active item = slim left-edge indicator, width transition at motion-slow.
// Persistent rail only at md+ (Responsive_Accessibility.md §1) — below
// that, MobileNav's drawer takes over entirely.
export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <aside
      className={cn(
        'hidden h-full shrink-0 flex-col border-r border-border-subtle bg-surface-secondary transition-[width] duration-slow ease-emphasis md:flex',
        collapsed ? 'w-16' : 'w-60',
      )}
    >
      <div className={cn('flex h-14 items-center gap-2 px-4', collapsed && 'justify-center px-0')}>
        <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent-500 text-text-on-accent">
          <Building2 className="size-4" />
        </span>
        {!collapsed && <span className="text-h4 text-text-primary">INT Projects</span>}
      </div>

      <SidebarNav collapsed={collapsed} />

      <button
        type="button"
        onClick={onToggle}
        aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        className={cn(
          'flex h-10 items-center gap-2 border-t border-border-subtle px-4 text-text-tertiary transition-colors hover:text-text-primary',
          collapsed && 'justify-center px-0',
        )}
      >
        {collapsed ? <ChevronsRight className="size-4" /> : <ChevronsLeft className="size-4" />}
      </button>
    </aside>
  );
}
