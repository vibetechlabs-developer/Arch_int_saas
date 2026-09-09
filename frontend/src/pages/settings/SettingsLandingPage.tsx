import { Link } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { Card } from '@/components/ui/card';
import { SETTINGS_NAV_GROUPS } from './settingsNavConfig';

// Settings landing (Phase 3): real navigation into every settings area,
// no fabricated stats or oversized decorative cards — each row is exactly
// as useful as the page it links to.
export default function SettingsLandingPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Settings" description="Manage your company, team, and account." />

      {SETTINGS_NAV_GROUPS.map((group) => (
        <div key={group.label} className="flex flex-col gap-2">
          <h3 className="text-label text-text-tertiary">{group.label}</h3>
          <Card className="divide-y divide-border-subtle overflow-hidden">
            {group.items.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className="flex items-center gap-3 p-4 transition-colors duration-fast hover:bg-hover"
              >
                <span className="flex size-9 shrink-0 items-center justify-center rounded-md bg-surface-secondary text-text-secondary">
                  <item.icon className="size-4" />
                </span>
                <div className="flex min-w-0 flex-1 flex-col">
                  <span className="text-body font-medium text-text-primary">{item.label}</span>
                  <span className="text-small text-text-secondary">{item.description}</span>
                </div>
                <ChevronRight className="size-4 shrink-0 text-text-tertiary" />
              </Link>
            ))}
          </Card>
        </div>
      ))}
    </div>
  );
}
