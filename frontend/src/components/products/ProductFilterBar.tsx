import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { CategoryCombobox } from '@/components/products/CategoryCombobox';
import { SubcategoryCombobox } from '@/components/products/SubcategoryCombobox';
import type { ProductStatus } from '@/lib/api/products';

const ALL_STATUSES = '__all__';

export interface ProductFilterValues {
  categoryId: string | null;
  categoryLabel: string | null;
  subcategoryId: string | null;
  subcategoryLabel: string | null;
  status: ProductStatus | '';
}

export interface ProductFilterBarProps {
  value: ProductFilterValues;
  onChange: (next: Partial<ProductFilterValues>) => void;
  onClearAll: () => void;
}

// Category → Subcategory is a dependent pair here too: changing the
// Category filter clears whatever Subcategory was selected (there's no
// "all subcategories" endpoint to validate it still belongs), and the
// Subcategory filter stays disabled until a Category is chosen.
export function ProductFilterBar({ value, onChange, onClearAll }: ProductFilterBarProps) {
  const hasAnyFilter = !!value.categoryId || !!value.subcategoryId || !!value.status;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="flex w-56 items-center gap-1">
        <CategoryCombobox
          value={value.categoryId}
          selectedLabel={value.categoryLabel}
          onSelect={(categoryId) => onChange({ categoryId, categoryLabel: null, subcategoryId: null, subcategoryLabel: null })}
          placeholder="All Categories"
        />
        {value.categoryId && (
          <Button
            variant="ghost"
            size="icon"
            aria-label="Clear category filter"
            onClick={() => onChange({ categoryId: null, categoryLabel: null, subcategoryId: null, subcategoryLabel: null })}
          >
            <X className="size-4" />
          </Button>
        )}
      </div>

      <div className="flex w-56 items-center gap-1">
        <SubcategoryCombobox
          categoryId={value.categoryId}
          value={value.subcategoryId}
          selectedLabel={value.subcategoryLabel}
          onSelect={(subcategoryId) => onChange({ subcategoryId, subcategoryLabel: null })}
        />
        {value.subcategoryId && (
          <Button variant="ghost" size="icon" aria-label="Clear subcategory filter" onClick={() => onChange({ subcategoryId: null, subcategoryLabel: null })}>
            <X className="size-4" />
          </Button>
        )}
      </div>

      <Select
        value={value.status || ALL_STATUSES}
        onValueChange={(v) => onChange({ status: v === ALL_STATUSES ? '' : (v as ProductStatus) })}
      >
        <SelectTrigger className="w-40" aria-label="Status filter">
          <SelectValue placeholder="All Statuses" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_STATUSES}>All Statuses</SelectItem>
          <SelectItem value="active">Active</SelectItem>
          <SelectItem value="inactive">Inactive</SelectItem>
        </SelectContent>
      </Select>

      {hasAnyFilter && (
        <Button variant="link" size="sm" onClick={onClearAll} className="px-1">
          Clear all
        </Button>
      )}
    </div>
  );
}
