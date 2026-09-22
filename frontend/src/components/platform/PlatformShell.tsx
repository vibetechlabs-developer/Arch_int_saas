import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, Moon, ShieldCheck, Sun } from 'lucide-react';
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
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/theme/ThemeProvider';

// Deliberately no Sidebar, CommandPalette, QuickCreate, or
// NotificationDrawer here — every one of those is built around a resolved
// tenant company (search scoped to company data, quick-create scoped to
// company records), which a platform-admin session never has
// (request.company_id is always null for this token type). A plain top
// bar is the honest shell for the one real screen area this console has
// today (Companies) rather than reusing Shell and hiding parts of it.
export function PlatformShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/platform/login', { replace: true });
  };

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-app text-text-primary">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-border-subtle bg-app px-4 sm:px-6">
        <div className="flex items-center gap-2.5">
          <span className="flex size-8 items-center justify-center rounded-lg bg-surface-secondary text-text-secondary">
            <ShieldCheck className="size-4" />
          </span>
          <span className="text-h4 text-text-primary">Platform Admin</span>
        </div>

        <div className="flex items-center gap-1.5">
          <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="Toggle theme">
            {isDark ? <Sun /> : <Moon />}
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button type="button" className="ml-1 rounded-full focus-visible:outline-none focus-visible:shadow-focus">
                <Avatar>
                  <AvatarFallback seed={user?.id ?? ''}>{user ? initialsOf(user.name) : null}</AvatarFallback>
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

      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-[1400px] flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8 lg:py-7">{children}</div>
      </main>
    </div>
  );
}
