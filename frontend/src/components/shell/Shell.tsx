import { useEffect, useState, type ReactNode } from 'react';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { CommandPaletteImpl } from './CommandPaletteImpl';
import { NotificationDrawer } from './NotificationDrawer';
import { MobileNav } from './MobileNav';

// Application_Shell_Navigation.md §"Shell Layout (Desktop)": sidebar
// (bg-surface-secondary) + header/content (bg-app), border-subtle
// separator only, no drop shadow between chrome and content. Below `md`
// the persistent Sidebar is replaced entirely by MobileNav's drawer
// (Responsive_Accessibility.md §1).
export function Shell({ children }: { children: ReactNode }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    }
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, []);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-app text-text-primary">
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed((prev) => !prev)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          onOpenCommandPalette={() => setCommandPaletteOpen(true)}
          onOpenNotifications={() => setNotificationsOpen(true)}
          onOpenMobileNav={() => setMobileNavOpen(true)}
        />
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto flex max-w-[1400px] flex-col gap-6 px-4 py-6 sm:px-6 lg:px-8 lg:py-7">
            {children}
          </div>
        </main>
      </div>

      <CommandPaletteImpl open={commandPaletteOpen} onOpenChange={setCommandPaletteOpen} />
      <NotificationDrawer open={notificationsOpen} onOpenChange={setNotificationsOpen} />
      <MobileNav open={mobileNavOpen} onOpenChange={setMobileNavOpen} />
    </div>
  );
}

export default Shell;
