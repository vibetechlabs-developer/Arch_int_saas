import { X } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { getProjects } from '@/lib/api/projects';
import { projectKeys } from '@/lib/queryKeys';
import type { ReportFilters } from '@/lib/api/reports';

const ALL_PROJECTS = '__all__';

export interface ReportFilterBarProps {
  value: ReportFilters;
  onChange: (next: Partial<ReportFilters>) => void;
  onClearAll: () => void;
}

// Both report endpoints share the exact same three query params
// (projectId/dateFrom/dateTo — confirmed from FinanceReportQuerySerializer),
// so one filter bar drives both panels rather than duplicating controls.
// Project has no `search` param on its own contract (same gap as
// Product/Category), so — matching that established precedent — the list
// is loaded once up to the pageSize=100 ceiling and shown as a plain
// dropdown rather than a searchable combobox, since a report filter is a
// lower-frequency action than picking a BOQ line item.
export function ReportFilterBar({ value, onChange, onClearAll }: ReportFilterBarProps) {
  const { data, isLoading } = useQuery({
    queryKey: projectKeys.list({ ordering: 'name', pageSize: 100 }),
    queryFn: () => getProjects({ ordering: 'name', pageSize: 100 }),
  });

  const hasAnyFilter = !!value.projectId || !!value.dateFrom || !!value.dateTo;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select
        value={value.projectId || ALL_PROJECTS}
        onValueChange={(v) => onChange({ projectId: v === ALL_PROJECTS ? undefined : v })}
      >
        <SelectTrigger className="w-52" aria-label="Project filter">
          <SelectValue placeholder={isLoading ? 'Loading projects…' : 'All Projects'} />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_PROJECTS}>All Projects</SelectItem>
          {(data?.items ?? []).map((project) => (
            <SelectItem key={project.id} value={project.id}>
              {project.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Input
        type="date"
        aria-label="From date"
        value={value.dateFrom || ''}
        onChange={(e) => onChange({ dateFrom: e.target.value || undefined })}
        className="w-40"
      />
      <Input
        type="date"
        aria-label="To date"
        value={value.dateTo || ''}
        onChange={(e) => onChange({ dateTo: e.target.value || undefined })}
        className="w-40"
      />

      {hasAnyFilter && (
        <Button variant="ghost" size="icon" aria-label="Clear all filters" onClick={onClearAll}>
          <X className="size-4" />
        </Button>
      )}
    </div>
  );
}
