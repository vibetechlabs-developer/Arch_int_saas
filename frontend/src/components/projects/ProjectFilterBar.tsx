import { useEffect, useState } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ClientCombobox } from '@/components/clients/ClientCombobox';
import { humanizeStatus } from '@/components/common/StatusBadge';
import { PROJECT_STATUSES, type ProjectStatus } from '@/lib/api/projects';

const ALL_STATUSES = '__all__';

export interface ProjectFilterValues {
  status: ProjectStatus | '';
  clientId: string | null;
  clientLabel: string | null;
  priority: string;
}

export interface ProjectFilterBarProps {
  value: ProjectFilterValues;
  onChange: (next: Partial<ProjectFilterValues>) => void;
  onClearAll: () => void;
}

// Compact, enterprise-grade filter row — only the filters the backend
// actually supports (status, client, priority — no free-text search on
// Project). Each control clears independently; "Clear all" appears only
// once something is actually applied.
export function ProjectFilterBar({ value, onChange, onClearAll }: ProjectFilterBarProps) {
  const [priorityDraft, setPriorityDraft] = useState(value.priority);
  useEffect(() => setPriorityDraft(value.priority), [value.priority]);

  const hasAnyFilter = !!value.status || !!value.clientId || !!value.priority;

  const commitPriority = () => {
    if (priorityDraft !== value.priority) onChange({ priority: priorityDraft });
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select
        value={value.status || ALL_STATUSES}
        onValueChange={(v) => onChange({ status: v === ALL_STATUSES ? '' : (v as ProjectStatus) })}
      >
        <SelectTrigger className="w-44" aria-label="Status filter">
          <SelectValue placeholder="All Statuses" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_STATUSES}>All Statuses</SelectItem>
          {PROJECT_STATUSES.map((status) => (
            <SelectItem key={status} value={status}>
              {humanizeStatus(status)}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <div className="flex w-56 items-center gap-1">
        <ClientCombobox
          value={value.clientId}
          selectedLabel={value.clientLabel}
          onSelect={(clientId) => onChange({ clientId, clientLabel: null })}
          placeholder="All Clients"
        />
        {value.clientId && (
          <Button variant="ghost" size="icon" aria-label="Clear client filter" onClick={() => onChange({ clientId: null, clientLabel: null })}>
            <X className="size-4" />
          </Button>
        )}
      </div>

      <div className="flex w-40 items-center gap-1">
        <Input
          value={priorityDraft}
          onChange={(e) => setPriorityDraft(e.target.value)}
          onBlur={commitPriority}
          onKeyDown={(e) => e.key === 'Enter' && commitPriority()}
          placeholder="Priority"
        />
        {value.priority && (
          <Button variant="ghost" size="icon" aria-label="Clear priority filter" onClick={() => onChange({ priority: '' })}>
            <X className="size-4" />
          </Button>
        )}
      </div>

      {hasAnyFilter && (
        <Button variant="link" size="sm" onClick={onClearAll} className="px-1">
          Clear all
        </Button>
      )}
    </div>
  );
}
