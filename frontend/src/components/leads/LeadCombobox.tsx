import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Combobox } from '@/components/common/Combobox';
import { getLeads } from '@/lib/api/leads';
import { leadKeys } from '@/lib/queryKeys';

export interface LeadComboboxProps {
  value: string | null;
  onSelect: (leadId: string) => void;
  selectedLabel?: string | null;
  invalid?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

// Remote-searched Lead picker (Site Visit create's lead field), mirroring
// apps.clients ClientCombobox exactly — Lead's own GET /leads endpoint
// supports a real `search` query param, unlike Project.
export function LeadCombobox({
  value,
  onSelect,
  selectedLabel,
  invalid,
  disabled,
  placeholder = 'Select a lead…',
}: LeadComboboxProps) {
  const [search, setSearch] = useState('');

  const { data, isFetching } = useQuery({
    queryKey: leadKeys.list({ search, ordering: 'name', page: 1 }),
    queryFn: () => getLeads({ search, ordering: 'name' }),
  });

  const options = (data?.items ?? []).map((lead) => ({
    value: lead.id,
    label: lead.name,
    sublabel: lead.companyName || lead.email || undefined,
  }));

  return (
    <Combobox
      value={value}
      onSelect={onSelect}
      options={options}
      isLoading={isFetching}
      searchValue={search}
      onSearchChange={setSearch}
      placeholder={placeholder}
      searchPlaceholder="Search leads…"
      emptyMessage="No leads found."
      invalid={invalid}
      disabled={disabled}
      selectedLabel={selectedLabel}
    />
  );
}
