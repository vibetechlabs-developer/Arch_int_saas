import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, Circle, Rocket, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { getClients } from '@/lib/api/clients';
import { getCompanyMemberships } from '@/lib/api/memberships';
import type { DashboardKPIs } from '@/lib/api/dashboard';
import { useCurrentCompanyId } from '@/hooks/useCurrentCompanyId';
import { cn } from '@/lib/utils';

interface Step {
  key: string;
  title: string;
  description: string;
  done: boolean;
  href: string;
  actionLabel: string;
}

function readDismissed(key: string): boolean {
  try {
    return localStorage.getItem(key) === '1';
  } catch {
    return false;
  }
}

// A guided first-run checklist for a brand-new company: the dashboard is
// all zeros until the first client/project exists, and nothing on it says
// what to do next. Steps tick themselves off from real data, and the whole
// card disappears once everything is done (or the person dismisses it).
// A step whose data the caller isn't allowed to read is left out rather
// than shown as permanently "not done" for something they can't do anyway.
export function GettingStartedCard({ kpis }: { kpis: DashboardKPIs }) {
  const { companyId } = useCurrentCompanyId();
  const dismissKey = `gettingStartedDismissed:${companyId ?? 'unknown'}`;
  const [dismissed, setDismissed] = useState(() => readDismissed(dismissKey));

  const clients = useQuery({
    queryKey: ['gettingStarted', 'clients', companyId],
    queryFn: () => getClients({ page: 1 }),
    retry: false,
    refetchOnMount: 'always',
  });
  const members = useQuery({
    queryKey: ['gettingStarted', 'members', companyId],
    queryFn: () => getCompanyMemberships({ status: 'active', page: 1, pageSize: 2 }),
    retry: false,
    refetchOnMount: 'always',
  });

  if (dismissed || clients.isLoading || members.isLoading) return null;

  const steps: Step[] = [];
  if (clients.isSuccess) {
    steps.push({
      key: 'client',
      title: 'Add your first client',
      description: 'Everything — projects, quotations, invoices — hangs off a client.',
      done: clients.data.pagination.totalItems > 0,
      href: '/clients',
      actionLabel: 'Add a client',
    });
  }
  steps.push(
    {
      key: 'project',
      title: 'Create a project',
      description: 'A project is one job for a client, from first quote to final payment.',
      done: kpis.totalProjects > 0,
      href: '/projects',
      actionLabel: 'Create a project',
    },
    {
      key: 'quotation',
      title: 'Prepare a quotation',
      description: 'Open a project, add its BOQ items, then create a quotation to send.',
      done: kpis.totalQuotations > 0,
      href: '/projects',
      actionLabel: 'Open projects',
    },
  );
  if (members.isSuccess) {
    steps.push({
      key: 'team',
      title: 'Invite your team',
      description: 'Add designers, accountants and site staff, each with the access they need.',
      done: members.data.pagination.totalItems > 1,
      href: '/settings/members',
      actionLabel: 'Invite people',
    });
  }

  const doneCount = steps.filter((step) => step.done).length;
  if (doneCount === steps.length) return null;

  const nextKey = steps.find((step) => !step.done)?.key;

  const dismiss = () => {
    setDismissed(true);
    try {
      localStorage.setItem(dismissKey, '1');
    } catch {
      // Not persisted (private window etc.) -- hidden for this visit only.
    }
  };

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
        <div className="flex flex-col gap-1">
          <CardTitle>
            <Rocket className="size-4 text-accent-500" />
            Get started
          </CardTitle>
          <p className="text-small text-text-secondary">
            {doneCount} of {steps.length} done — a few quick steps to get your workspace working for you.
          </p>
        </div>
        <Button variant="ghost" size="icon" onClick={dismiss} aria-label="Dismiss getting started">
          <X />
        </Button>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div
          className="h-1.5 w-full overflow-hidden rounded-full bg-surface-secondary"
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={steps.length}
          aria-valuenow={doneCount}
          aria-label="Getting started progress"
        >
          <div
            className="h-full rounded-full bg-accent-500 transition-all duration-slow"
            style={{ width: `${(doneCount / steps.length) * 100}%` }}
          />
        </div>

        <ul className="flex flex-col divide-y divide-border-subtle">
          {steps.map((step) => (
            <li key={step.key} className="flex items-center gap-3 py-3">
              {step.done ? (
                <CheckCircle2 className="size-5 shrink-0 text-success-text" aria-label="Done" />
              ) : (
                <Circle className="size-5 shrink-0 text-text-tertiary" aria-label="Not done yet" />
              )}
              <div className="flex min-w-0 flex-1 flex-col">
                <span
                  className={cn(
                    'text-body font-medium',
                    step.done ? 'text-text-tertiary line-through' : 'text-text-primary',
                  )}
                >
                  {step.title}
                </span>
                {!step.done && <span className="text-small text-text-secondary">{step.description}</span>}
              </div>
              {!step.done && (
                <Button variant={step.key === nextKey ? 'primary' : 'outline'} size="sm" asChild>
                  <Link to={step.href}>{step.actionLabel}</Link>
                </Button>
              )}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
