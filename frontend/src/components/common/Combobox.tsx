import * as React from 'react';
import { Check, ChevronsUpDown, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { cn } from '@/lib/utils';

export interface ComboboxOption {
  value: string;
  label: string;
  sublabel?: string;
}

export interface ComboboxProps {
  value: string | null;
  onSelect: (value: string) => void;
  options: ComboboxOption[];
  isLoading?: boolean;
  searchValue: string;
  onSearchChange: (value: string) => void;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyMessage?: string;
  disabled?: boolean;
  invalid?: boolean;
  /** Shown on the trigger while `value` isn't present in the current (search-filtered) `options` list — e.g. an already-selected item when editing. */
  selectedLabel?: string | null;
  /** True for a fully-preloaded, un-searchable-server-side option set (e.g. product categories — no `search` param exists on that endpoint) — cmdk filters `options` locally instead of trusting the caller to have already filtered them via the API. */
  shouldFilter?: boolean;
}

// A server-searched single-select combobox (Popover + cmdk Command,
// `shouldFilter={false}` since results already came from the API). Used
// wherever a form needs to pick one real backend record by search rather
// than a hardcoded dropdown — the Client selector on Project create/edit,
// the company-member selector on Add Team Member.
export function Combobox({
  value,
  onSelect,
  options,
  isLoading,
  searchValue,
  onSearchChange,
  placeholder = 'Select…',
  searchPlaceholder = 'Search…',
  emptyMessage = 'No results found.',
  disabled,
  invalid,
  selectedLabel,
  shouldFilter = false,
}: ComboboxProps) {
  const [open, setOpen] = React.useState(false);
  const selectedOption = options.find((option) => option.value === value);
  const triggerLabel = selectedOption?.label ?? selectedLabel ?? null;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-label={triggerLabel ?? placeholder}
          disabled={disabled}
          className={cn(
            'w-full justify-between font-normal',
            !triggerLabel && 'text-text-tertiary',
            invalid && 'border-danger-text',
          )}
        >
          <span className="truncate">{triggerLabel ?? placeholder}</span>
          <ChevronsUpDown className="size-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[--radix-popover-trigger-width] p-0" align="start">
        <Command shouldFilter={shouldFilter}>
          <CommandInput placeholder={searchPlaceholder} value={searchValue} onValueChange={onSearchChange} />
          <CommandList>
            {isLoading ? (
              <div className="flex items-center justify-center gap-2 py-6 text-small text-text-tertiary">
                <Loader2 className="size-4 animate-spin" />
                Searching…
              </div>
            ) : (
              <>
                <CommandEmpty>{emptyMessage}</CommandEmpty>
                <CommandGroup>
                  {options.map((option) => (
                    <CommandItem
                      key={option.value}
                      value={option.value}
                      onSelect={() => {
                        onSelect(option.value);
                        setOpen(false);
                      }}
                    >
                      <Check className={cn('size-4', option.value === value ? 'opacity-100' : 'opacity-0')} />
                      <div className="flex flex-col">
                        <span>{option.label}</span>
                        {option.sublabel && <span className="text-caption text-text-tertiary">{option.sublabel}</span>}
                      </div>
                    </CommandItem>
                  ))}
                </CommandGroup>
              </>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
