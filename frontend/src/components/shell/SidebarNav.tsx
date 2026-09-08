import { Link, useLocation } from 'react-router-dom';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { NAV_GROUPS, type NavItem } from './navConfig';

// A nav item is active for its own path/subtree (exact match or a nested
// route under it) or any of its declared `matchPaths` subtrees (e.g.
// Products staying active while viewing /settings/product-categories,
// which manages Products' taxonomy from a different URL prefix).
function isItemActive(item: NavItem, pathname: string): boolean {
  const ownMatch = pathname === item.path || pathname.startsWith(`${item.path}/`);
  const extraMatch = item.matchPaths?.some((p) => pathname === p || pathname.startsWith(`${p}/`)) ?? false;
  return ownMatch || extraMatch;
}

// Shared nav-list markup between the persistent desktop rail (Sidebar.tsx)
// and the mobile drawer (MobileNav.tsx) — one nav-visibility rule
// implemented once (Application_Shell_Navigation.md §Sidebar). Uses a
// plain `Link` with a manually computed active state (rather than
// `NavLink`'s built-in matching) so a `matchPaths` entry can activate an
// item from outside its own path subtree — `aria-current="page"` is set
// explicitly to keep the accessibility behavior NavLink would otherwise
// have provided automatically.
export function SidebarNav({ collapsed = false, onNavigate }: { collapsed?: boolean; onNavigate?: () => void }) {
  const { pathname } = useLocation();

  return (
    <nav className="flex flex-1 flex-col gap-4 overflow-y-auto px-2 py-2">
      {NAV_GROUPS.map((group) => (
        <div key={group.label} className="flex flex-col gap-0.5">
          {!collapsed && <span className="px-2 pb-1 text-label text-text-tertiary">{group.label}</span>}
          {group.items.map((item) => {
            const isActive = isItemActive(item, pathname);
            const link = (
              <Link
                to={item.path}
                onClick={onNavigate}
                aria-current={isActive ? 'page' : undefined}
                aria-label={collapsed ? item.label : undefined}
                className={cn(
                  'relative flex items-center gap-2.5 rounded-md px-2.5 py-2 text-body transition-colors duration-fast',
                  collapsed && 'justify-center px-0',
                  isActive ? 'text-text-primary' : 'text-text-secondary hover:bg-hover hover:text-text-primary',
                )}
              >
                {isActive && (
                  <span className="absolute -left-2 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-accent-500 transition-all duration-standard" />
                )}
                <item.icon className="size-4 shrink-0" />
                {!collapsed && item.label}
              </Link>
            );
            return (
              <div key={item.path}>
                {collapsed ? (
                  <Tooltip delayDuration={200}>
                    <TooltipTrigger asChild>{link}</TooltipTrigger>
                    <TooltipContent side="right">{item.label}</TooltipContent>
                  </Tooltip>
                ) : (
                  link
                )}
              </div>
            );
          })}
        </div>
      ))}
    </nav>
  );
}
