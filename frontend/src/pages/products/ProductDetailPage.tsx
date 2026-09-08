import { useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { motion, useReducedMotion } from 'framer-motion';
import { ArrowLeft, FileWarning, Percent, Pencil, Ruler, Tag, Trash2 } from 'lucide-react';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Money } from '@/components/common/Money';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { ApiError } from '@/lib/api/client';
import { deleteProduct, getProduct, PRODUCT_UNITS } from '@/lib/api/products';
import { productKeys } from '@/lib/queryKeys';
import { formatDateTime } from '@/lib/format';
import { pageTransition, pageTransitionReduced } from '@/lib/motion';
import { ProductFormSheet } from '@/components/products/ProductFormSheet';
import { ProductThumbnail } from '@/components/products/ProductThumbnail';

function unitLabel(unit: string): string {
  return PRODUCT_UNITS.find((u) => u.value === unit)?.label ?? '—';
}

export default function ProductDetailPage() {
  const { productId } = useParams<{ productId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const shouldReduceMotion = useReducedMotion();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const { data: product, isLoading, isError, error, refetch } = useQuery({
    queryKey: productKeys.detail(productId!),
    queryFn: () => getProduct(productId!),
    enabled: !!productId,
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteProduct(productId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: productKeys.lists() });
      toast.success('Product deleted');
      navigate('/products', { replace: true });
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete product.');
      setDeleteOpen(false);
    },
  });

  if (!productId) return <Navigate to="/products" replace />;

  if (isError) {
    const notFound = error instanceof ApiError && error.code === 'NOT_FOUND';
    if (notFound) {
      return (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <FileWarning className="size-6 text-text-tertiary" />
          <div className="flex flex-col gap-1">
            <p className="text-body font-medium text-text-primary">Product not found</p>
            <p className="text-small text-text-secondary">
              It may have been deleted, or you don't have access to it.
            </p>
          </div>
          <Button variant="secondary" size="sm" asChild className="mt-1">
            <Link to="/products">Back to Products</Link>
          </Button>
        </div>
      );
    }
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  return (
    <motion.div
      variants={shouldReduceMotion ? pageTransitionReduced : pageTransition}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-6"
    >
      <Button variant="ghost" size="sm" className="w-fit gap-1.5 text-text-secondary" asChild>
        <Link to="/products">
          <ArrowLeft className="size-4" />
          Back to Products
        </Link>
      </Button>

      {isLoading || !product ? (
        <DetailSkeleton />
      ) : (
        <>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex flex-col gap-1.5">
              <span className="text-label text-text-tertiary">
                {product.categoryName} / {product.subcategoryName}
              </span>
              <h2 className="text-h1 font-medium tracking-tight text-text-primary">{product.name}</h2>
              <StatusBadge status={product.status} />
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={() => setEditOpen(true)}>
                <Pencil />
                Edit
              </Button>
              <Button variant="destructive" onClick={() => setDeleteOpen(true)}>
                <Trash2 />
                Delete
              </Button>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Pricing</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <InfoRow icon={Tag} label="Default cost">
                  <Money value={product.defaultCost} className="text-body text-text-primary" />
                </InfoRow>
                <InfoRow icon={Tag} label="Default selling rate">
                  <Money value={product.defaultSellingRate} className="text-body text-text-primary" />
                </InfoRow>
                <InfoRow icon={Percent} label="Tax rate">
                  <span className="text-body text-text-primary">{product.taxRate ? `${product.taxRate}%` : '—'}</span>
                </InfoRow>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Metadata</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Added</span>
                  <span className="text-small text-text-primary">{formatDateTime(product.createdAt)}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Last updated</span>
                  <span className="text-small text-text-primary">{formatDateTime(product.updatedAt)}</span>
                </div>
              </CardContent>
            </Card>

            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Specifications</CardTitle>
              </CardHeader>
              <CardContent>
                <InfoRow icon={Ruler} label="Unit of measure">
                  <span className="text-body text-text-primary">{unitLabel(product.unit)}</span>
                </InfoRow>
              </CardContent>
            </Card>

            {product.imageUrl && (
              <Card>
                <CardHeader>
                  <CardTitle>Image</CardTitle>
                </CardHeader>
                <CardContent>
                  <ProductThumbnail imageUrl={product.imageUrl} alt={product.name} size="lg" />
                </CardContent>
              </Card>
            )}
          </div>

          <ProductFormSheet open={editOpen} onOpenChange={setEditOpen} product={product} />

          <ConfirmationDialog
            open={deleteOpen}
            onOpenChange={setDeleteOpen}
            title="Delete this product?"
            description={`This removes "${product.name}" from the catalog.`}
            confirmLabel="Delete product"
            destructive
            loading={deleteMutation.isPending}
            onConfirm={() => deleteMutation.mutate()}
          />
        </>
      )}
    </motion.div>
  );
}

function InfoRow({ icon: Icon, label, children }: { icon: typeof Tag; label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2.5">
      <Icon className="mt-0.5 size-4 shrink-0 text-text-tertiary" />
      <div className="flex flex-col gap-0.5">
        <span className="text-caption text-text-tertiary">{label}</span>
        {children}
      </div>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Skeleton className="h-3 w-40" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-5 w-24" />
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="flex flex-col gap-4 p-5 lg:col-span-2">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
        </Card>
        <Card className="flex flex-col gap-4 p-5">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-32" />
        </Card>
      </div>
    </div>
  );
}
