import { Bell, LogOut, Menu, Moon, Search, Sun, User as UserIcon } from 'lucide-react';
import { useLocation, useMatch, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, initialsOf } from '@/components/ui/avatar';
import { QuickCreateMenu } from './QuickCreateMenu';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/theme/ThemeProvider';
import { NAV_GROUPS } from './navConfig';
import { projectKeys } from '@/lib/queryKeys';
import type { Project } from '@/lib/api/projects';

export interface HeaderProps {
  onOpenCommandPalette: () => void;
  onOpenNotifications: () => void;
  onOpenMobileNav: () => void;
}

const ALL_NAV_ITEMS = NAV_GROUPS.flatMap((group) => group.items);

// Application_Shell_Navigation.md §"Top Header": breadcrumb+title on the
// left; search → quick create → notifications → theme toggle → user menu
// on the right, in that order (Help is omitted — no help destination
// exists yet, per the nav-visibility rule of "absent, not disabled").
export function Header({ onOpenCommandPalette, onOpenNotifications, onOpenMobileNav }: HeaderProps) {
  const { user, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // `useMatch` works from anywhere in the tree (it matches against the
  // current location directly), unlike `useParams` — Header is a sibling
  // of the routed content under Shell, not a descendant of it, so it has
  // no other way to know the current :projectId.
  const projectMatch = useMatch('/projects/:projectId/*');

  let breadcrumb: string[];
  if (projectMatch?.params.projectId) {
    const cached = queryClient.getQueryData<Project>(projectKeys.detail(projectMatch.params.projectId));
    breadcrumb = ['Projects'];
    // Only append once the real name has loaded — never flash the raw UUID.
    if (cached?.name) breadcrumb.push(cached.name);
    if (cached?.name && location.pathname.endsWith('/team')) breadcrumb.push('Team');
  } else {
    // Exact match first, then the longest nav path that's a parent of the
    // current route (e.g. /clients/:id under the "Clients" nav item) — a
    // detail page itself carries the specific title in its own PageHeader,
    // so the top bar staying at the module label is a deliberate choice,
    // not a fallback bug.
    const currentItem =
      ALL_NAV_ITEMS.find((item) => item.path === location.pathname) ??
      ALL_NAV_ITEMS.filter((item) => location.pathname.startsWith(`${item.path}/`)).sort(
        (a, b) => b.path.length - a.path.length,
      )[0];
    breadcrumb = [currentItem?.label ?? 'INT Projects'];
  }

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border-subtle bg-app px-4 sm:px-6">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={onOpenMobileNav}
          aria-label="Open navigation"
          className="max-md:size-11 md:hidden"
        >
          <Menu />
        </Button>
        <h1 className="flex items-center gap-1.5 text-h4 text-text-primary">
          {breadcrumb.map((crumb, i) => (
            <span key={i} className="flex items-center gap-1.5">
              {i > 0 && <span className="text-text-tertiary">/</span>}
              <span className={i < breadcrumb.length - 1 ? 'text-text-secondary' : undefined}>{crumb}</span>
            </span>
          ))}
        </h1>
      </div>

      <div className="flex items-center gap-1.5">
        <Button
          variant="ghost"
          size="sm"
          onClick={onOpenCommandPalette}
          className="gap-2 text-text-tertiary"
        >
          <Search className="size-4" />
          <span className="hidden sm:inline">Search…</span>
          <kbd className="hidden rounded border border-border-subtle bg-surface-secondary px-1.5 py-0.5 text-caption sm:inline">
            ⌘K
          </kbd>
        </Button>

        <QuickCreateMenu />

        <Button
          variant="ghost"
          size="icon"
          onClick={onOpenNotifications}
          aria-label="Notifications"
          className="max-md:size-11"
        >
          <Bell />
        </Button>

        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          aria-label="Toggle theme"
          className="max-md:size-11"
        >
          {isDark ? <Sun /> : <Moon />}
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button type="button" className="ml-1 rounded-full focus-visible:outline-none focus-visible:shadow-focus">
              <Avatar>
                <AvatarFallback seed={user?.id ?? ''}>
                  {user ? initialsOf(user.name) : <UserIcon className="size-4" />}
                </AvatarFallback>
              </Avatar>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="flex flex-col gap-0.5 normal-case">
              <span className="text-body font-medium text-text-primary">{user?.name}</span>
              <span className="text-small text-text-tertiary">{user?.email}</span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem destructive onSelect={handleLogout}>
              <LogOut className="size-4" />
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
