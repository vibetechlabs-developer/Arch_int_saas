import type { LucideIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: { label: string; onClick: () => void };
}

// Component_Inventory.md §12: icon + short headline + one-sentence
// explanation + single primary CTA. Lucide icons only, no illustrations.
export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 py-10 text-center">
      <Icon className="size-6 text-text-tertiary" />
      <div className="flex flex-col gap-1">
        <p className="text-body font-medium text-text-primary">{title}</p>
        <p className="text-small text-text-secondary">{description}</p>
      </div>
      {action && (
        <Button variant="secondary" size="sm" onClick={action.onClick} className="mt-1">
          {action.label}
        </Button>
      )}
    </div>
  );
}
