import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Combobox } from '@/components/common/Combobox';
import { getProjects } from '@/lib/api/projects';
import { projectKeys } from '@/lib/queryKeys';

export interface ProjectComboboxProps {
  value: string | null;
  onSelect: (projectId: string) => void;
  selectedLabel?: string | null;
  invalid?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

// Project has no `search` query param (Project_API.md documents no
// free-text filter for this endpoint, unlike Client) — the list is
// loaded once (bounded by pageSize=100, the max StandardPagination
// allows) and filtered locally by cmdk, matching CategoryCombobox's
// identical pattern for the same reason.
export function ProjectCombobox({
  value,
  onSelect,
  selectedLabel,
  invalid,
  disabled,
  placeholder = 'Select a project…',
}: ProjectComboboxProps) {
  const [search, setSearch] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: projectKeys.list({ ordering: 'name', pageSize: 100 }),
    queryFn: () => getProjects({ ordering: 'name', pageSize: 100 }),
  });

  const options = (data?.items ?? []).map((project) => ({
    value: project.id,
    label: project.name,
    sublabel: project.clientName,
  }));

  return (
    <Combobox
      value={value}
      onSelect={onSelect}
      options={options}
      isLoading={isLoading}
      searchValue={search}
      onSearchChange={setSearch}
      placeholder={placeholder}
      searchPlaceholder="Search projects…"
      emptyMessage="No projects found."
      invalid={invalid}
      disabled={disabled}
      selectedLabel={selectedLabel}
      shouldFilter
    />
  );
}
