import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Combobox } from '@/components/common/Combobox';
import { getCategories } from '@/lib/api/productCategories';
import { categoryKeys } from '@/lib/queryKeys';

export interface CategoryComboboxProps {
  value: string | null;
  onSelect: (categoryId: string) => void;
  selectedLabel?: string | null;
  invalid?: boolean;
  disabled?: boolean;
  placeholder?: string;
}

// ProductCategory has no `search` query param (a single-field entity, per
// the backend contract) — the full list is loaded once (bounded by
// pageSize=100, the max StandardPagination allows) and filtered locally
// by cmdk, rather than a server round-trip per keystroke.
export function CategoryCombobox({
  value,
  onSelect,
  selectedLabel,
  invalid,
  disabled,
  placeholder = 'Select a category…',
}: CategoryComboboxProps) {
  const [search, setSearch] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: categoryKeys.list({ ordering: 'name', pageSize: 100 }),
    queryFn: () => getCategories({ ordering: 'name', pageSize: 100 }),
  });

  const options = (data?.items ?? []).map((category) => ({ value: category.id, label: category.name }));

  return (
    <Combobox
      value={value}
      onSelect={onSelect}
      options={options}
      isLoading={isLoading}
      searchValue={search}
      onSearchChange={setSearch}
      placeholder={placeholder}
      searchPlaceholder="Search categories…"
      emptyMessage="No categories found."
      invalid={invalid}
      disabled={disabled}
      selectedLabel={selectedLabel}
      shouldFilter
    />
  );
}
