import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Combobox } from '@/components/common/Combobox';
import { getClients } from '@/lib/api/clients';
import { clientKeys } from '@/lib/queryKeys';

export interface ClientComboboxProps {
  value: string | null;
  onSelect: (clientId: string) => void;
  /** The already-selected client's display name, so it shows on the trigger even before a search brings it back into `options` (e.g. opening the edit form). */
  selectedLabel?: string | null;
  invalid?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

// Remote-searched Client picker (Project create/edit's client field) — never
// preloads the full client list, searches the real /clients endpoint as the
// user types.
export function ClientCombobox({
  value,
  onSelect,
  selectedLabel,
  invalid,
  disabled,
  placeholder = 'Select a client…',
}: ClientComboboxProps) {
  const [search, setSearch] = useState('');

  const { data, isFetching } = useQuery({
    queryKey: clientKeys.list({ search, ordering: 'name', page: 1 }),
    queryFn: () => getClients({ search, ordering: 'name' }),
  });

  const options = (data?.items ?? []).map((client) => ({
    value: client.id,
    label: client.name,
    sublabel: client.companyName || client.email || undefined,
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
      searchPlaceholder="Search clients…"
      emptyMessage="No clients found."
      invalid={invalid}
      disabled={disabled}
      selectedLabel={selectedLabel}
    />
  );
}
