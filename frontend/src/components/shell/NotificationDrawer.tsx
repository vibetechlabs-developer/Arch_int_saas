import { BellOff } from 'lucide-react';
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet';
import { EmptyState } from '@/components/common/EmptyState';

export interface NotificationDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// No notifications backend exists yet (Phase 5 per CLAUDE.md's MVP
// phasing) — this shows an honest empty state rather than fabricated
// entries, matching guardrail #7 ("no fake data shapes").
export function NotificationDrawer({ open, onOpenChange }: NotificationDrawerProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent aria-describedby={undefined}>
        <SheetHeader>
          <SheetTitle>Notifications</SheetTitle>
        </SheetHeader>
        <EmptyState
          icon={BellOff}
          title="No notifications yet"
          description="In-app notifications ship in a later phase of the build."
        />
      </SheetContent>
    </Sheet>
  );
}
