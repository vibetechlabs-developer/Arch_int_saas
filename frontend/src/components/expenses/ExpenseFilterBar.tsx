import { useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import type { ExpenseApprovalStatus } from '@/lib/api/expenses';

const ALL_STATUSES = '__all__';

export interface ExpenseFilterValues {
  category: string;
  vendor: string;
  approvalStatus: ExpenseApprovalStatus | '';
  dateFrom: string;
  dateTo: string;
}

export interface ExpenseFilterBarProps {
  value: ExpenseFilterValues;
  onChange: (next: Partial<ExpenseFilterValues>) => void;
  onClearAll: () => void;
}

// Category/vendor are real server-side filters (ExpenseListQuerySerializer)
// but match the backend's own field values exactly, not a substring
// search — a short debounce avoids refetching on every keystroke while
// still driving a genuine server-side query, not a client-side filter
// over an already-loaded list.
function DebouncedTextFilter({
  value,
  placeholder,
  ariaLabel,
  onCommit,
}: {
  value: string;
  placeholder: string;
  ariaLabel: string;
  onCommit: (next: string) => void;
}) {
  const [draft, setDraft] = useState(value);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => setDraft(value), [value]);

  return (
    <Input
      value={draft}
      aria-label={ariaLabel}
      placeholder={placeholder}
      className="w-40"
      onChange={(e) => {
        const next = e.target.value;
        setDraft(next);
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => onCommit(next), 350);
      }}
    />
  );
}

export function ExpenseFilterBar({ value, onChange, onClearAll }: ExpenseFilterBarProps) {
  const hasAnyFilter = !!value.category || !!value.vendor || !!value.approvalStatus || !!value.dateFrom || !!value.dateTo;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <DebouncedTextFilter
        value={value.category}
        placeholder="Category"
        ariaLabel="Category filter"
        onCommit={(category) => onChange({ category })}
      />
      <DebouncedTextFilter value={value.vendor} placeholder="Vendor" ariaLabel="Vendor filter" onCommit={(vendor) => onChange({ vendor })} />

      <Select
        value={value.approvalStatus || ALL_STATUSES}
        onValueChange={(v) => onChange({ approvalStatus: v === ALL_STATUSES ? '' : (v as ExpenseApprovalStatus) })}
      >
        <SelectTrigger className="w-36" aria-label="Status filter">
          <SelectValue placeholder="All Statuses" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={ALL_STATUSES}>All Statuses</SelectItem>
          <SelectItem value="draft">Draft</SelectItem>
          <SelectItem value="submitted">Submitted</SelectItem>
          <SelectItem value="approved">Approved</SelectItem>
          <SelectItem value="paid">Paid</SelectItem>
        </SelectContent>
      </Select>

      <Input
        type="date"
        aria-label="From date"
        value={value.dateFrom}
        onChange={(e) => onChange({ dateFrom: e.target.value })}
        className="w-40"
      />
      <Input type="date" aria-label="To date" value={value.dateTo} onChange={(e) => onChange({ dateTo: e.target.value })} className="w-40" />

      {hasAnyFilter && (
        <Button variant="ghost" size="icon" aria-label="Clear all filters" onClick={onClearAll}>
          <X className="size-4" />
        </Button>
      )}
    </div>
  );
}
