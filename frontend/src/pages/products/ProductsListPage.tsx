import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { motion, useReducedMotion } from 'framer-motion';
import { type ColumnDef, type SortingState } from '@tanstack/react-table';
import { FolderTree, MoreHorizontal, Package, Pencil, Trash2 } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { DataTable } from '@/components/common/DataTable';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Money } from '@/components/common/Money';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ApiError } from '@/lib/api/client';
import { deleteProduct, getProducts, PRODUCT_UNITS, type Product, type ProductOrdering } from '@/lib/api/products';
import { productKeys } from '@/lib/queryKeys';
import { formatDate } from '@/lib/format';
import { pageTransition, pageTransitionReduced } from '@/lib/motion';
import { ProductFormSheet } from '@/components/products/ProductFormSheet';
import { ProductThumbnail } from '@/components/products/ProductThumbnail';
import { ProductFilterBar, type ProductFilterValues } from '@/components/products/ProductFilterBar';

function sortingToOrdering(sorting: SortingState): ProductOrdering {
  if (sorting.length === 0) return '-updated_at';
  const [{ id, desc }] = sorting;
  const field = id === 'updatedAt' ? 'updated_at' : id;
  return (desc ? `-${field}` : field) as ProductOrdering;
}

function unitLabel(unit: string): string {
  return PRODUCT_UNITS.find((u) => u.value === unit)?.label ?? '—';
}

const EMPTY_FILTERS: ProductFilterValues = {
  categoryId: null,
  categoryLabel: null,
  subcategoryId: null,
  subcategoryLabel: null,
  status: '',
};

export default function ProductsListPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const shouldReduceMotion = useReducedMotion();

  const [page, setPage] = useState(0);
  const [filters, setFilters] = useState<ProductFilterValues>(EMPTY_FILTERS);
  const [sorting, setSorting] = useState<SortingState>([{ id: 'updatedAt', desc: true }]);
  const [formOpen, setFormOpen] = useState(false);
  const [editingProduct, setEditingProduct] = useState<Product | undefined>(undefined);
  const [deletingProduct, setDeletingProduct] = useState<Product | null>(null);

  useEffect(() => {
    if (searchParams.get('new') === 'true') {
      setEditingProduct(undefined);
      setFormOpen(true);
      const next = new URLSearchParams(searchParams);
      next.delete('new');
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const ordering = sortingToOrdering(sorting);
  const queryParams = {
    category: filters.categoryId || undefined,
    subcategory: filters.subcategoryId || undefined,
    status: filters.status || undefined,
    ordering,
    page: page + 1,
  };
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: productKeys.list(queryParams),
    queryFn: () => getProducts(queryParams),
    placeholderData: keepPreviousData,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteProduct(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: productKeys.lists() });
      toast.success('Product deleted');
      setDeletingProduct(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete product.');
      setDeletingProduct(null);
    },
  });

  if (isError) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const openCreate = () => {
    setEditingProduct(undefined);
    setFormOpen(true);
  };

  const updateFilters = (patch: Partial<ProductFilterValues>) => {
    setFilters((prev) => ({ ...prev, ...patch }));
    setPage(0);
  };

  const hasFilters = !!filters.categoryId || !!filters.subcategoryId || !!filters.status;

  const columns: ColumnDef<Product, unknown>[] = [
    {
      accessorKey: 'name',
      header: 'Product',
      cell: ({ row }) => (
        <div className="flex items-center gap-3">
          <ProductThumbnail imageUrl={row.original.imageUrl} alt={row.original.name} />
          <span className="text-body font-medium text-text-primary">{row.original.name}</span>
        </div>
      ),
    },
    {
      accessorKey: 'categoryName',
      header: 'Category',
      enableSorting: false,
      cell: ({ row }) => <span className="text-body text-text-secondary">{row.original.categoryName}</span>,
    },
    {
      accessorKey: 'subcategoryName',
      header: 'Subcategory',
      enableSorting: false,
      cell: ({ row }) => <span className="text-body text-text-secondary">{row.original.subcategoryName}</span>,
    },
    {
      accessorKey: 'unit',
      header: 'Unit',
      enableSorting: false,
      cell: ({ row }) => <span className="text-small text-text-secondary">{unitLabel(row.original.unit)}</span>,
    },
    {
      accessorKey: 'defaultSellingRate',
      header: () => <span className="block text-right">Rate</span>,
      enableSorting: false,
      cell: ({ row }) => (
        <div className="text-right">
          <Money value={row.original.defaultSellingRate} />
        </div>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Status',
      enableSorting: false,
      cell: ({ row }) => <StatusBadge status={row.original.status} />,
    },
    {
      accessorKey: 'updatedAt',
      header: 'Updated',
      cell: ({ row }) => <span className="text-small text-text-tertiary">{formatDate(row.original.updatedAt)}</span>,
    },
    {
      id: 'actions',
      header: '',
      enableSorting: false,
      enableHiding: false,
      cell: ({ row }) => (
        <div className="flex justify-end">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Product actions" onClick={(e) => e.stopPropagation()}>
                <MoreHorizontal />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onSelect={() => {
                  setEditingProduct(row.original);
                  setFormOpen(true);
                }}
              >
                <Pencil className="size-4" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuItem destructive onSelect={() => setDeletingProduct(row.original)}>
                <Trash2 className="size-4" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      ),
    },
  ];

  return (
    <motion.div
      variants={shouldReduceMotion ? pageTransitionReduced : pageTransition}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-6"
    >
      <PageHeader
        title="Products"
        description="The catalog of materials and work items that feed BOQs and quotations."
        actions={
          <>
            <Button variant="outline" onClick={() => navigate('/settings/product-categories')}>
              <FolderTree />
              Manage Categories
            </Button>
            <Button variant="primary" onClick={openCreate}>
              <Package />
              New Product
            </Button>
          </>
        }
      />

      <ProductFilterBar value={filters} onChange={updateFilters} onClearAll={() => updateFilters(EMPTY_FILTERS)} />

      <DataTable
        columns={columns}
        data={data?.items ?? []}
        isLoading={isLoading || isFetching}
        hideSearch
        manual
        pageIndex={page}
        pageCount={data?.pagination.totalPages ?? 1}
        totalItems={data?.pagination.totalItems}
        onPageChange={setPage}
        sorting={sorting}
        onSortingChange={setSorting}
        emptyState={
          hasFilters
            ? {
                icon: Package,
                title: 'No products match these filters',
                description: 'Try a different category, subcategory, or status.',
              }
            : {
                icon: Package,
                title: 'No products yet',
                description: 'Products feed BOQs, quotations, and other commercial workflows. Add your first one to get started.',
                action: { label: 'New Product', onClick: openCreate },
              }
        }
        onRowClick={(product) => navigate(`/products/${product.id}`)}
      />

      <ProductFormSheet open={formOpen} onOpenChange={setFormOpen} product={editingProduct} />

      <ConfirmationDialog
        open={!!deletingProduct}
        onOpenChange={(open) => !open && setDeletingProduct(null)}
        title="Delete this product?"
        description={`This removes "${deletingProduct?.name}" from the catalog.`}
        confirmLabel="Delete product"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => deletingProduct && deleteMutation.mutate(deletingProduct.id)}
      />
    </motion.div>
  );
}
