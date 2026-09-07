import { Bell, LogOut, Menu, Moon, Search, Sun, User as UserIcon } from 'lucide-react';
import { useLocation, useNavigate } from 'react-router-dom';
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
  const pageTitle = currentItem?.label ?? 'INT Projects';

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
        <h1 className="text-h4 text-text-primary">{pageTitle}</h1>
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
