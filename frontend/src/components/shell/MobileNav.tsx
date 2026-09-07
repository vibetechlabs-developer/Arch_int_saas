import { Building2 } from 'lucide-react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { SidebarNav } from './SidebarNav';

export interface MobileNavProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// Responsive_Accessibility.md §1: below `md` the sidebar becomes a
// full-screen drawer rather than a shrunk persistent rail.
export function MobileNav({ open, onOpenChange }: MobileNavProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="flex w-72 flex-col p-0" aria-describedby={undefined}>
        <SheetHeader className="flex-row items-center gap-2 border-b border-border-subtle p-4">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent-500 text-text-on-accent">
            <Building2 className="size-4" />
          </span>
          <SheetTitle className="text-h4">INT Projects</SheetTitle>
        </SheetHeader>
        <SidebarNav onNavigate={() => onOpenChange(false)} />
      </SheetContent>
    </Sheet>
  );
}
