import * as React from 'react';
import {
  type ColumnDef,
  type OnChangeFn,
  type RowSelectionState,
  type SortingState,
  type Updater,
  type VisibilityState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from '@tanstack/react-table';
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, Columns3, Search, type LucideIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/common/EmptyState';
import { cn } from '@/lib/utils';

// Component_Inventory.md §3: the single most load-bearing component —
// sort, filter/search, pagination, column visibility, row selection,
// density toggle, sticky header, hover row highlight (no vertical borders).
//
// Two modes:
//  - Client-side (default): pass the full `data` array once; search/sort/
//    pagination all happen in-browser via TanStack Table's row models.
//  - Server-side (`manual`): `data` is just the current page's rows as
//    returned by the API. Search/sort/page are controlled props and every
//    change re-fetches — required whenever the backend already paginates
//    (never fetch a whole collection just to filter it client-side).
export interface DataTableProps<TData> {
  columns: ColumnDef<TData, unknown>[];
  data: TData[];
  isLoading?: boolean;
  searchPlaceholder?: string;
  emptyState: {
    title: string;
    description: string;
    icon?: LucideIcon;
    action?: { label: string; onClick: () => void };
  };
  enableRowSelection?: boolean;
  onRowClick?: (row: TData) => void;
  toolbarActions?: React.ReactNode;
  /** Omit the search box entirely — for a manual-mode list whose backend has no free-text search param (e.g. Projects, which only supports structured filters). */
  hideSearch?: boolean;

  manual?: boolean;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
  pageIndex?: number;
  pageCount?: number;
  totalItems?: number;
  onPageChange?: (pageIndex: number) => void;
  sorting?: SortingState;
  onSortingChange?: (sorting: SortingState) => void;
}

export function DataTable<TData>({
  columns,
  data,
  isLoading,
  searchPlaceholder = 'Search…',
  emptyState,
  enableRowSelection = false,
  onRowClick,
  toolbarActions,
  hideSearch = false,
  manual = false,
  searchValue,
  onSearchChange,
  pageIndex = 0,
  pageCount = 1,
  totalItems,
  onPageChange,
  sorting: manualSorting,
  onSortingChange,
}: DataTableProps<TData>) {
  const [internalSorting, setInternalSorting] = React.useState<SortingState>([]);
  const [internalGlobalFilter, setInternalGlobalFilter] = React.useState('');
  const [columnVisibility, setColumnVisibility] = React.useState<VisibilityState>({});
  const [rowSelection, setRowSelection] = React.useState<RowSelectionState>({});
  const [density, setDensity] = React.useState<'comfortable' | 'compact'>('comfortable');

  // Debounce the visible input so manual search doesn't re-fetch per keystroke,
  // while still tracking an external reset (e.g. a "Clear filters" action).
  const [searchDraft, setSearchDraft] = React.useState(searchValue ?? '');
  const debounceRef = React.useRef<ReturnType<typeof setTimeout>>();
  React.useEffect(() => {
    setSearchDraft(searchValue ?? '');
  }, [searchValue]);

  const handleSearchInputChange = (value: string) => {
    if (!manual) {
      setInternalGlobalFilter(value);
      return;
    }
    setSearchDraft(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => onSearchChange?.(value), 350);
  };

  const sorting = manual ? (manualSorting ?? []) : internalSorting;
  const handleSortingChange: OnChangeFn<SortingState> = (updater: Updater<SortingState>) => {
    if (manual) {
      const next = typeof updater === 'function' ? updater(manualSorting ?? []) : updater;
      onSortingChange?.(next);
    } else {
      setInternalSorting(updater);
    }
  };

  const tableColumns = React.useMemo<ColumnDef<TData, unknown>[]>(() => {
    if (!enableRowSelection) return columns;
    return [
      {
        id: 'select',
        header: ({ table }) => (
          <Checkbox
            checked={table.getIsAllPageRowsSelected()}
            onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
            aria-label="Select all rows"
          />
        ),
        cell: ({ row }) => (
          <Checkbox
            checked={row.getIsSelected()}
            onCheckedChange={(value) => row.toggleSelected(!!value)}
            onClick={(e) => e.stopPropagation()}
            aria-label="Select row"
          />
        ),
        enableSorting: false,
        enableHiding: false,
      },
      ...columns,
    ];
  }, [columns, enableRowSelection]);

  const table = useReactTable({
    data,
    columns: tableColumns,
    state: {
      sorting,
      globalFilter: manual ? undefined : internalGlobalFilter,
      columnVisibility,
      rowSelection,
      ...(manual ? { pagination: { pageIndex, pageSize: 25 } } : {}),
    },
    onSortingChange: handleSortingChange,
    onGlobalFilterChange: manual ? undefined : setInternalGlobalFilter,
    onColumnVisibilityChange: setColumnVisibility,
    onRowSelectionChange: setRowSelection,
    onPaginationChange: manual
      ? (updater: Updater<{ pageIndex: number; pageSize: number }>) => {
          const next =
            typeof updater === 'function' ? updater({ pageIndex, pageSize: 25 }) : updater;
          onPageChange?.(next.pageIndex);
        }
      : undefined,
    manualSorting: manual,
    manualFiltering: manual,
    manualPagination: manual,
    pageCount: manual ? pageCount : undefined,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: manual ? undefined : getSortedRowModel(),
    getFilteredRowModel: manual ? undefined : getFilteredRowModel(),
    getPaginationRowModel: manual ? undefined : getPaginationRowModel(),
    initialState: { pagination: { pageSize: 25 } },
  });

  const rows = table.getRowModel().rows;
  const cellPadding = density === 'compact' ? 'py-1.5' : 'py-3';
  const searchInputValue = manual ? searchDraft : internalGlobalFilter;
  const currentPage = manual ? pageIndex + 1 : table.getState().pagination.pageIndex + 1;
  const totalPages = manual ? Math.max(1, pageCount) : Math.max(1, table.getPageCount());
  const rowCountLabel = manual ? (totalItems ?? rows.length) : table.getFilteredRowModel().rows.length;
  const canPreviousPage = manual ? pageIndex > 0 : table.getCanPreviousPage();
  const canNextPage = manual ? pageIndex + 1 < pageCount : table.getCanNextPage();
  const goPreviousPage = () => (manual ? onPageChange?.(pageIndex - 1) : table.previousPage());
  const goNextPage = () => (manual ? onPageChange?.(pageIndex + 1) : table.nextPage());

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        {hideSearch ? (
          <div />
        ) : (
          <div className="relative w-64">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-text-tertiary" />
            <Input
              value={searchInputValue}
              onChange={(e) => handleSearchInputChange(e.target.value)}
              placeholder={searchPlaceholder}
              className="pl-8"
            />
          </div>
        )}
        <div className="flex items-center gap-2">
          {toolbarActions}
          <Select value={density} onValueChange={(v) => setDensity(v as typeof density)}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="comfortable">Comfortable</SelectItem>
              <SelectItem value="compact">Compact</SelectItem>
            </SelectContent>
          </Select>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Columns3 />
                Columns
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {table
                .getAllColumns()
                .filter((column) => column.getCanHide())
                .map((column) => (
                  <DropdownMenuCheckboxItem
                    key={column.id}
                    checked={column.getIsVisible()}
                    onCheckedChange={(value) => column.toggleVisibility(!!value)}
                    onSelect={(e) => e.preventDefault()}
                  >
                    {column.id}
                  </DropdownMenuCheckboxItem>
                ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Desktop / Tablet Table View */}
      <div className="hidden rounded-lg border border-border-subtle bg-surface md:block">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id} className="hover:bg-transparent">
                {headerGroup.headers.map((header) => {
                  const sortDirection = header.column.getIsSorted();
                  return (
                    <TableHead key={header.id}>
                      {header.isPlaceholder ? null : header.column.getCanSort() ? (
                        <button
                          type="button"
                          onClick={header.column.getToggleSortingHandler()}
                          className="inline-flex items-center gap-1 hover:text-text-primary"
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {sortDirection === 'asc' ? (
                            <ArrowUp className="size-3" />
                          ) : sortDirection === 'desc' ? (
                            <ArrowDown className="size-3" />
                          ) : (
                            <ArrowUpDown className="size-3 opacity-40" />
                          )}
                        </button>
                      ) : (
                        flexRender(header.column.columnDef.header, header.getContext())
                      )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 6 }).map((_, i) => (
                <TableRow key={i} className="hover:bg-transparent">
                  {tableColumns.map((_, j) => (
                    <TableCell key={j} className={cellPadding}>
                      <Skeleton className="h-4 w-full max-w-[10rem]" />
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : rows.length === 0 ? (
              <TableRow className="hover:bg-transparent">
                <TableCell colSpan={tableColumns.length}>
                  <EmptyState icon={emptyState.icon ?? Search} title={emptyState.title} description={emptyState.description} action={emptyState.action} />
                </TableCell>
              </TableRow>
            ) : (
              rows.map((row) => (
                <TableRow
                  key={row.id}
                  onClick={() => onRowClick?.(row.original)}
                  className={cn(onRowClick && 'cursor-pointer')}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id} className={cellPadding}>
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Mobile Stacked Card View (< md) */}
      <div className="flex flex-col gap-3 md:hidden">
        {isLoading ? (
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface p-4">
              <Skeleton className="h-4 w-1/3" />
              <Skeleton className="h-4 w-2/3" />
            </div>
          ))
        ) : rows.length === 0 ? (
          <div className="rounded-lg border border-border-subtle bg-surface p-4">
            <EmptyState icon={emptyState.icon ?? Search} title={emptyState.title} description={emptyState.description} action={emptyState.action} />
          </div>
        ) : (
          rows.map((row) => (
            <div
              key={row.id}
              onClick={() => onRowClick?.(row.original)}
              className={cn(
                'flex flex-col gap-2 rounded-lg border border-border-subtle bg-surface p-4 shadow-sm transition-colors duration-fast',
                onRowClick && 'cursor-pointer hover:bg-hover active:scale-[0.99]',
              )}
            >
              {row
                .getVisibleCells()
                .filter((cell) => cell.column.id !== 'select')
                .map((cell) => (
                  <div key={cell.id} className="flex items-center justify-between gap-2 py-0.5 min-h-[28px]">
                    <span className="text-caption text-text-tertiary">
                      {typeof cell.column.columnDef.header === 'string'
                        ? cell.column.columnDef.header
                        : cell.column.id}
                    </span>
                    <span className="text-body text-text-primary text-right">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </span>
                  </div>
                ))}
            </div>
          ))
        )}
      </div>

      {!isLoading && rows.length > 0 && (
        <div className="flex items-center justify-between text-small text-text-secondary">
          <span>
            Page {currentPage} of {totalPages} · {rowCountLabel} rows
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="icon"
              onClick={goPreviousPage}
              disabled={!canPreviousPage}
              aria-label="Previous page"
            >
              <ChevronLeft />
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={goNextPage}
              disabled={!canNextPage}
              aria-label="Next page"
            >
              <ChevronRight />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
