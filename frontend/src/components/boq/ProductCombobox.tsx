import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Combobox } from '@/components/common/Combobox';
import { getProducts, type Product } from '@/lib/api/products';
import { productKeys } from '@/lib/queryKeys';

export interface ProductComboboxProps {
  value: string | null;
  /** Receives the full Product so the caller can prefill unit/rate/tax from real values — never invented. */
  onSelect: (product: Product) => void;
  selectedLabel?: string | null;
  invalid?: boolean;
}

// Product has no `search` query param on its own contract (confirmed —
// same gap as Category/Subcategory), so like those, the full active-
// product list is loaded once (bounded by pageSize=100) and filtered
// locally by cmdk. Scoped to status=active only — an inactive product
// "can't be selected for new items" per its own model docstring, and the
// existing status filter already supports exactly that exclusion.
export function ProductCombobox({ value, onSelect, selectedLabel, invalid }: ProductComboboxProps) {
  const [search, setSearch] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: productKeys.list({ status: 'active', ordering: 'name', pageSize: 100 }),
    queryFn: () => getProducts({ status: 'active', ordering: 'name', pageSize: 100 }),
  });

  const options = (data?.items ?? []).map((product) => ({
    value: product.id,
    label: product.name,
    sublabel: `${product.categoryName} / ${product.subcategoryName}`,
  }));

  return (
    <Combobox
      value={value}
      onSelect={(id) => {
        const product = data?.items.find((p) => p.id === id);
        if (product) onSelect(product);
      }}
      options={options}
      isLoading={isLoading}
      searchValue={search}
      onSearchChange={setSearch}
      placeholder="Select a product…"
      searchPlaceholder="Search products…"
      emptyMessage="No active products found."
      invalid={invalid}
      selectedLabel={selectedLabel}
      shouldFilter
    />
  );
}
