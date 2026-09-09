import { Badge, type BadgeProps } from '@/components/ui/badge';

type Semantic = NonNullable<BadgeProps['variant']>;

// Semantic color per status value across every entity this app knows about
// (Component_Inventory.md §7). Status text always accompanies color — never
// color-only (Responsive_Accessibility.md §3).
const STATUS_SEMANTICS: Record<string, Semantic> = {
  // Project (CLAUDE.md lifecycle)
  draft: 'neutral',
  planning: 'info',
  design: 'info',
  quotation: 'info',
  approved: 'success',
  execution: 'warning',
  quality_check: 'warning',
  handover: 'warning',
  completed: 'success',
  on_hold: 'warning',
  cancelled: 'danger',
  // Quotation
  internal_review: 'neutral',
  sent: 'info',
  revision_requested: 'warning',
  rejected: 'danger',
  // Invoice
  partially_paid: 'warning',
  paid: 'success',
  overdue: 'danger',
  // Expense
  submitted: 'info',
  // Product catalog
  active: 'success',
  inactive: 'neutral',
  // Company membership (CompanyMembershipStatus — active is shared with
  // Product catalog above, same semantic color applies)
  invited: 'info',
  revoked: 'danger',
};

export function humanizeStatus(status: string): string {
  return status
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

export function StatusBadge({ status }: { status: string }) {
  const key = status.toLowerCase();
  const variant = STATUS_SEMANTICS[key] ?? 'neutral';
  return <Badge variant={variant}>{humanizeStatus(key)}</Badge>;
}
