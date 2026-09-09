import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Avatar, AvatarFallback, initialsOf } from '@/components/ui/avatar';
import { StatusBadge } from '@/components/common/StatusBadge';
import { formatDate } from '@/lib/format';
import type { CompanyMembership } from '@/lib/api/memberships';

export interface MemberDetailSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  member: CompanyMembership | null;
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-caption text-text-tertiary">{label}</span>
      <span className="text-body text-text-primary">{value}</span>
    </div>
  );
}

// Read-only detail view (Phase 8) — every field here is a real
// CompanyMembershipSerializer field, nothing invented. Row actions
// (change role / suspend / reactivate / remove) live on the list page's
// own dropdown, not duplicated here, to keep one place responsible for
// each mutation's confirmation flow.
export function MemberDetailSheet({ open, onOpenChange, member }: MemberDetailSheetProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent aria-describedby={undefined}>
        <SheetHeader>
          <SheetTitle>Member details</SheetTitle>
          <SheetDescription>Read-only membership information.</SheetDescription>
        </SheetHeader>
        {member && (
          <div className="flex flex-col gap-5">
            <div className="flex items-center gap-3">
              <Avatar className="size-12">
                <AvatarFallback seed={member.userId}>{initialsOf(member.userName)}</AvatarFallback>
              </Avatar>
              <div className="flex flex-col">
                <span className="text-h4 text-text-primary">{member.userName}</span>
                <span className="text-small text-text-secondary">{member.userEmail}</span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Role" value={member.roleName ?? 'No role assigned'} />
              <Field label="Status" value={<StatusBadge status={member.status} />} />
              <Field label="Company" value={member.companyName} />
              <Field label="Joined" value={formatDate(member.createdAt)} />
              <Field label="Last updated" value={formatDate(member.updatedAt)} />
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
