import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { motion, useReducedMotion } from 'framer-motion';
import { ChevronDown, ChevronRight, FolderTree, Plus, Trash2, Pencil } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { ApiError } from '@/lib/api/client';
import { deleteCategory, getCategories, type ProductCategory } from '@/lib/api/productCategories';
import { deleteSubcategory, getSubcategoriesForCategory, type ProductSubcategory } from '@/lib/api/productSubcategories';
import { categoryKeys, subcategoryKeys } from '@/lib/queryKeys';
import { formatDate } from '@/lib/format';
import { pageTransition, pageTransitionReduced } from '@/lib/motion';
import { CategoryFormDialog } from '@/components/products/CategoryFormDialog';
import { SubcategoryFormDialog } from '@/components/products/SubcategoryFormDialog';

export default function ProductCategoriesPage() {
  const shouldReduceMotion = useReducedMotion();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [categoryDialogOpen, setCategoryDialogOpen] = useState(false);
  const [editingCategory, setEditingCategory] = useState<ProductCategory | undefined>(undefined);
  const [deletingCategory, setDeletingCategory] = useState<ProductCategory | null>(null);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: categoryKeys.list({ ordering: 'name', pageSize: 100 }),
    queryFn: () => getCategories({ ordering: 'name', pageSize: 100 }),
  });

  const queryClient = useQueryClient();
  const deleteCategoryMutation = useMutation({
    mutationFn: (id: string) => deleteCategory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: categoryKeys.lists() });
      toast.success('Category deleted');
      setDeletingCategory(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete category.');
      setDeletingCategory(null);
    },
  });

  if (isError) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const categories = data?.items ?? [];

  return (
    <motion.div
      variants={shouldReduceMotion ? pageTransitionReduced : pageTransition}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-6"
    >
      <PageHeader
        title="Product Categories"
        description="Organize the catalog into categories and subcategories."
        actions={
          <Button
            variant="primary"
            onClick={() => {
              setEditingCategory(undefined);
              setCategoryDialogOpen(true);
            }}
          >
            <Plus />
            New Category
          </Button>
        }
      />

      {isLoading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i} className="flex items-center gap-3 p-4">
              <Skeleton className="h-4 w-4" />
              <Skeleton className="h-4 w-48" />
            </Card>
          ))}
        </div>
      ) : categories.length === 0 ? (
        <Card className="p-4">
          <EmptyState
            icon={FolderTree}
            title="No product categories yet"
            description="Create your first category to start organizing the product catalog."
            action={{ label: 'Create Category', onClick: () => setCategoryDialogOpen(true) }}
          />
        </Card>
      ) : (
        <div className="flex flex-col gap-2">
          {categories.map((category) => (
            <CategoryRow
              key={category.id}
              category={category}
              expanded={expandedId === category.id}
              onToggle={() => setExpandedId((prev) => (prev === category.id ? null : category.id))}
              onEdit={() => {
                setEditingCategory(category);
                setCategoryDialogOpen(true);
              }}
              onDelete={() => setDeletingCategory(category)}
            />
          ))}
        </div>
      )}

      <CategoryFormDialog open={categoryDialogOpen} onOpenChange={setCategoryDialogOpen} category={editingCategory} />

      <ConfirmationDialog
        open={!!deletingCategory}
        onOpenChange={(open) => !open && setDeletingCategory(null)}
        title="Delete this category?"
        description={`This removes "${deletingCategory?.name}" from the catalog. Categories with existing subcategories cannot be deleted.`}
        confirmLabel="Delete category"
        destructive
        loading={deleteCategoryMutation.isPending}
        onConfirm={() => deletingCategory && deleteCategoryMutation.mutate(deletingCategory.id)}
      />
    </motion.div>
  );
}

function CategoryRow({
  category,
  expanded,
  onToggle,
  onEdit,
  onDelete,
}: {
  category: ProductCategory;
  expanded: boolean;
  onToggle: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="flex items-center justify-between gap-3 p-4">
        <button
          type="button"
          onClick={onToggle}
          className="flex flex-1 items-center gap-2 text-left focus-visible:outline-none focus-visible:shadow-focus"
          aria-expanded={expanded}
        >
          {expanded ? (
            <ChevronDown className="size-4 shrink-0 text-text-tertiary" />
          ) : (
            <ChevronRight className="size-4 shrink-0 text-text-tertiary" />
          )}
          <span className="text-body font-medium text-text-primary">{category.name}</span>
        </button>
        <span className="hidden text-caption text-text-tertiary sm:block">Updated {formatDate(category.updatedAt)}</span>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" aria-label={`Edit ${category.name}`} onClick={onEdit}>
            <Pencil className="size-4" />
          </Button>
          <Button variant="ghost" size="icon" aria-label={`Delete ${category.name}`} onClick={onDelete}>
            <Trash2 className="size-4 text-danger-text" />
          </Button>
        </div>
      </div>
      {expanded && <SubcategoryPanel category={category} />}
    </Card>
  );
}

function SubcategoryPanel({ category }: { category: ProductCategory }) {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingSubcategory, setEditingSubcategory] = useState<ProductSubcategory | undefined>(undefined);
  const [deletingSubcategory, setDeletingSubcategory] = useState<ProductSubcategory | null>(null);

  const { data: subcategories, isLoading, isError, error, refetch } = useQuery({
    queryKey: subcategoryKeys.forCategory(category.id),
    queryFn: () => getSubcategoriesForCategory(category.id, 'name'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteSubcategory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: subcategoryKeys.forCategory(category.id) });
      toast.success('Subcategory deleted');
      setDeletingSubcategory(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete subcategory.');
      setDeletingSubcategory(null);
    },
  });

  return (
    <div className="border-t border-border-subtle bg-surface-secondary px-4 py-3 pl-10">
      {isError ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <div className="flex flex-col gap-2">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-4 w-32" />
        </div>
      ) : !subcategories || subcategories.length === 0 ? (
        <EmptyState
          icon={FolderTree}
          title="No subcategories yet"
          description="Add a subcategory to organize products under this category."
          action={{ label: 'Add Subcategory', onClick: () => { setEditingSubcategory(undefined); setDialogOpen(true); } }}
        />
      ) : (
        <div className="flex flex-col divide-y divide-border-subtle">
          {subcategories.map((subcategory) => (
            <div key={subcategory.id} className="flex items-center justify-between gap-3 py-2">
              <span className="text-small text-text-primary">{subcategory.name}</span>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Edit ${subcategory.name}`}
                  onClick={() => {
                    setEditingSubcategory(subcategory);
                    setDialogOpen(true);
                  }}
                >
                  <Pencil className="size-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Delete ${subcategory.name}`}
                  onClick={() => setDeletingSubcategory(subcategory)}
                >
                  <Trash2 className="size-4 text-danger-text" />
                </Button>
              </div>
            </div>
          ))}
          <div className="pt-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                setEditingSubcategory(undefined);
                setDialogOpen(true);
              }}
            >
              <Plus />
              Add Subcategory
            </Button>
          </div>
        </div>
      )}

      <SubcategoryFormDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        categoryId={category.id}
        subcategory={editingSubcategory}
      />

      <ConfirmationDialog
        open={!!deletingSubcategory}
        onOpenChange={(open) => !open && setDeletingSubcategory(null)}
        title="Delete this subcategory?"
        description={`This removes "${deletingSubcategory?.name}" from the catalog. Subcategories with existing products cannot be deleted.`}
        confirmLabel="Delete subcategory"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => deletingSubcategory && deleteMutation.mutate(deletingSubcategory.id)}
      />
    </div>
  );
}
