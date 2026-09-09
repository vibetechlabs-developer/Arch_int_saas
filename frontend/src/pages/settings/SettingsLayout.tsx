import { Link, Outlet, useLocation } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { pageTransition, pageTransitionReduced } from '@/lib/motion';
import { cn } from '@/lib/utils';
import { SETTINGS_NAV_GROUPS } from './settingsNavConfig';

function isSettingsItemActive(path: string, pathname: string): boolean {
  return pathname === path || pathname.startsWith(`${path}/`);
}

// Settings' own two-level IA (Phase 2): a grouped internal nav alongside
// every /settings/* page's content, separate from the single "Settings"
// entry the primary app sidebar carries. Desktop: fixed-width left rail.
// Mobile (<md, Phase 31): a horizontally scrollable pill row so the full
// list stays reachable without a second drawer layer.
export default function SettingsLayout() {
  const { pathname } = useLocation();
  const shouldReduceMotion = useReducedMotion();

  return (
    <motion.div
      variants={shouldReduceMotion ? pageTransitionReduced : pageTransition}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-6 lg:flex-row lg:items-start lg:gap-8"
    >
      <nav
        aria-label="Settings"
        className="flex gap-1 overflow-x-auto pb-1 lg:w-56 lg:shrink-0 lg:flex-col lg:gap-4 lg:overflow-visible lg:pb-0"
      >
        {SETTINGS_NAV_GROUPS.map((group) => (
          <div key={group.label} className="flex shrink-0 flex-col gap-0.5 lg:shrink">
            <span className="hidden px-2 pb-1 text-label text-text-tertiary lg:block">{group.label}</span>
            {group.items.map((item) => {
              const isActive = isSettingsItemActive(item.path, pathname);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  aria-current={isActive ? 'page' : undefined}
                  className={cn(
                    'flex shrink-0 items-center gap-2.5 whitespace-nowrap rounded-md px-3 py-2 text-body transition-colors duration-fast lg:whitespace-normal',
                    isActive
                      ? 'bg-hover text-text-primary'
                      : 'text-text-secondary hover:bg-hover hover:text-text-primary',
                  )}
                >
                  <item.icon className="size-4 shrink-0" />
                  {item.label}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="min-w-0 flex-1">
        <Outlet />
      </div>
    </motion.div>
  );
}
