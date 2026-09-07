import { NavLink } from 'react-router-dom';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';
import { NAV_GROUPS } from './navConfig';

// Shared nav-list markup between the persistent desktop rail (Sidebar.tsx)
// and the mobile drawer (MobileNav.tsx) — one nav-visibility rule
// implemented once (Application_Shell_Navigation.md §Sidebar).
export function SidebarNav({ collapsed = false, onNavigate }: { collapsed?: boolean; onNavigate?: () => void }) {
  return (
    <nav className="flex flex-1 flex-col gap-4 overflow-y-auto px-2 py-2">
      {NAV_GROUPS.map((group) => (
        <div key={group.label} className="flex flex-col gap-0.5">
          {!collapsed && <span className="px-2 pb-1 text-label text-text-tertiary">{group.label}</span>}
          {group.items.map((item) => (
            <NavLink key={item.path} to={item.path} onClick={onNavigate}>
              {({ isActive }) => {
                const link = (
                  <span
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
                  </span>
                );
                return collapsed ? (
                  <Tooltip delayDuration={200}>
                    <TooltipTrigger asChild>{link}</TooltipTrigger>
                    <TooltipContent side="right">{item.label}</TooltipContent>
                  </Tooltip>
                ) : (
                  link
                );
              }}
            </NavLink>
          ))}
        </div>
      ))}
    </nav>
  );
}
