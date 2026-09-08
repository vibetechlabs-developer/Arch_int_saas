import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Combobox } from '@/components/common/Combobox';
import { getSubcategoriesForCategory } from '@/lib/api/productSubcategories';
import { subcategoryKeys } from '@/lib/queryKeys';

export interface SubcategoryComboboxProps {
  categoryId: string | null;
  value: string | null;
  onSelect: (subcategoryId: string) => void;
  selectedLabel?: string | null;
  invalid?: boolean;
}

// Scoped to one category (no "all subcategories" endpoint exists — only
// GET /product-categories/{categoryId}/subcategories, an unpaginated
// plain array, per the backend contract). Disabled until a category is
// chosen; the caller clears `value` whenever `categoryId` changes.
export function SubcategoryCombobox({ categoryId, value, onSelect, selectedLabel, invalid }: SubcategoryComboboxProps) {
  const [search, setSearch] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: categoryId ? subcategoryKeys.forCategory(categoryId) : subcategoryKeys.forCategory('none'),
    queryFn: () => getSubcategoriesForCategory(categoryId!, 'name'),
    enabled: !!categoryId,
  });

  const options = (data ?? []).map((subcategory) => ({ value: subcategory.id, label: subcategory.name }));

  return (
    <Combobox
      value={value}
      onSelect={onSelect}
      options={options}
      isLoading={isLoading}
      searchValue={search}
      onSearchChange={setSearch}
      placeholder={categoryId ? 'Select a subcategory…' : 'Select a category first'}
      searchPlaceholder="Search subcategories…"
      emptyMessage="No subcategories found."
      invalid={invalid}
      disabled={!categoryId}
      selectedLabel={selectedLabel}
      shouldFilter
    />
  );
}
