import { useEffect, useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ChevronDown, ChevronRight, ListTree, Pencil, Plus, Trash2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { Money } from '@/components/common/Money';
import { FinancialSummary } from '@/components/common/FinancialSummary';
import { ApiError } from '@/lib/api/client';
import { PRODUCT_UNITS } from '@/lib/api/products';
import {
  deleteBOQItem,
  deleteBOQSection,
  getBOQ,
  getBOQSummary,
  type BOQItem,
  type BOQSection,
} from '@/lib/api/boq';
import { boqKeys } from '@/lib/queryKeys';
import { formatDateTime } from '@/lib/format';
import type { Project } from '@/lib/api/projects';
import { BOQSectionFormDialog } from '@/components/boq/BOQSectionFormDialog';
import { BOQItemFormSheet } from '@/components/boq/BOQItemFormSheet';

function unitLabel(unit: string): string {
  return PRODUCT_UNITS.find((u) => u.value === unit)?.label ?? '—';
}

export default function ProjectBOQTab() {
  const { project } = useOutletContext<{ project: Project }>();
  const projectId = project.id;
  const queryClient = useQueryClient();

  const { data: boq, isLoading, isError, error, refetch } = useQuery({
    queryKey: boqKeys.project(projectId),
    queryFn: () => getBOQ(projectId),
  });
  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: boqKeys.summary(projectId),
    queryFn: () => getBOQSummary(projectId),
  });

  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [sectionDialogOpen, setSectionDialogOpen] = useState(false);
  const [editingSection, setEditingSection] = useState<BOQSection | undefined>(undefined);
  const [deletingSection, setDeletingSection] = useState<BOQSection | null>(null);
  const [itemSheet, setItemSheet] = useState<{ sectionId: string; item?: BOQItem } | null>(null);
  const [deletingItem, setDeletingItem] = useState<BOQItem | null>(null);

  useEffect(() => {
    // Every section starts expanded — a BOQ typically has few enough
    // sections that showing everything is more useful than a collapsed
    // default; users can collapse the ones they don't need.
    if (boq) setExpanded(new Set(boq.sections.map((s) => s.id)));
  }, [boq?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const deleteSectionMutation = useMutation({
    mutationFn: (id: string) => deleteBOQSection(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: boqKeys.project(projectId) });
      queryClient.invalidateQueries({ queryKey: boqKeys.summary(projectId) });
      toast.success('Section deleted');
      setDeletingSection(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete section.');
      setDeletingSection(null);
    },
  });

  const deleteItemMutation = useMutation({
    mutationFn: (id: string) => deleteBOQItem(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: boqKeys.project(projectId) });
      queryClient.invalidateQueries({ queryKey: boqKeys.summary(projectId) });
      toast.success('Item deleted');
      setDeletingItem(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete item.');
      setDeletingItem(null);
    },
  });

  if (isError) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  if (isLoading || !boq) {
    return <BOQSkeleton />;
  }

  const totalItems = boq.sections.reduce((sum, s) => sum + s.items.length, 0);
  const openAddSection = () => {
    setEditingSection(undefined);
    setSectionDialogOpen(true);
  };

  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardHeader>
          <CardTitle>Bill of Quantities</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-1 text-small text-text-secondary">
            <span>
              {boq.sections.length} section{boq.sections.length === 1 ? '' : 's'}
            </span>
            <span>
              {totalItems} item{totalItems === 1 ? '' : 's'}
            </span>
            <span>Last updated {formatDateTime(boq.updatedAt)}</span>
          </div>
          <FinancialSummary
            subtotal={summary?.subtotal}
            discount={summary?.discount}
            tax={summary?.tax}
            total={summary?.total}
            loading={summaryLoading}
            className="border-t border-border-subtle pt-4"
          />
        </CardContent>
      </Card>

      <div className="flex items-center justify-between">
        <h3 className="text-h3 text-text-primary">Sections</h3>
        <Button variant="primary" size="sm" onClick={openAddSection}>
          <Plus />
          Add Section
        </Button>
      </div>

      {boq.sections.length === 0 ? (
        <Card className="p-4">
          <EmptyState
            icon={ListTree}
            title="No BOQ items yet"
            description="Start by adding a section, then add products or items to it."
            action={{ label: 'Add Section', onClick: openAddSection }}
          />
        </Card>
      ) : (
        <div className="flex flex-col gap-3">
          {boq.sections.map((section) => (
            <BOQSectionBlock
              key={section.id}
              section={section}
              expanded={expanded.has(section.id)}
              onToggle={() =>
                setExpanded((prev) => {
                  const next = new Set(prev);
                  next.has(section.id) ? next.delete(section.id) : next.add(section.id);
                  return next;
                })
              }
              onEdit={() => {
                setEditingSection(section);
                setSectionDialogOpen(true);
              }}
              onDelete={() => setDeletingSection(section)}
              onAddItem={() => setItemSheet({ sectionId: section.id })}
              onEditItem={(item) => setItemSheet({ sectionId: section.id, item })}
              onDeleteItem={setDeletingItem}
            />
          ))}
        </div>
      )}

      <BOQSectionFormDialog
        open={sectionDialogOpen}
        onOpenChange={setSectionDialogOpen}
        projectId={projectId}
        section={editingSection}
      />

      <ConfirmationDialog
        open={!!deletingSection}
        onOpenChange={(open) => !open && setDeletingSection(null)}
        title="Delete this section?"
        description={`This removes "${deletingSection?.name}" from the BOQ. Sections with existing items cannot be deleted.`}
        confirmLabel="Delete section"
        destructive
        loading={deleteSectionMutation.isPending}
        onConfirm={() => deletingSection && deleteSectionMutation.mutate(deletingSection.id)}
      />

      {itemSheet && (
        <BOQItemFormSheet
          open={!!itemSheet}
          onOpenChange={(open) => !open && setItemSheet(null)}
          projectId={projectId}
          sectionId={itemSheet.sectionId}
          item={itemSheet.item}
        />
      )}

      <ConfirmationDialog
        open={!!deletingItem}
        onOpenChange={(open) => !open && setDeletingItem(null)}
        title="Delete this item?"
        description={`This removes "${deletingItem?.description}" from the section.`}
        confirmLabel="Delete item"
        destructive
        loading={deleteItemMutation.isPending}
        onConfirm={() => deletingItem && deleteItemMutation.mutate(deletingItem.id)}
      />
    </div>
  );
}

function BOQSectionBlock({
  section,
  expanded,
  onToggle,
  onEdit,
  onDelete,
  onAddItem,
  onEditItem,
  onDeleteItem,
}: {
  section: BOQSection;
  expanded: boolean;
  onToggle: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onAddItem: () => void;
  onEditItem: (item: BOQItem) => void;
  onDeleteItem: (item: BOQItem) => void;
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
          <span className="text-body font-medium text-text-primary">{section.name}</span>
          <Badge variant="neutral">
            {section.items.length} item{section.items.length === 1 ? '' : 's'}
          </Badge>
        </button>
        <div className="flex items-center gap-1">
          <Button variant="secondary" size="sm" onClick={onAddItem}>
            <Plus />
            Add Item
          </Button>
          <Button variant="ghost" size="icon" aria-label={`Edit ${section.name}`} onClick={onEdit}>
            <Pencil className="size-4" />
          </Button>
          <Button variant="ghost" size="icon" aria-label={`Delete ${section.name}`} onClick={onDelete}>
            <Trash2 className="size-4 text-danger-text" />
          </Button>
        </div>
      </div>

      {expanded &&
        (section.items.length === 0 ? (
          <div className="border-t border-border-subtle bg-surface-secondary px-4 py-3">
            <EmptyState icon={ListTree} title="No items yet" description="Add a product or free-text item to this section." action={{ label: 'Add Item', onClick: onAddItem }} />
          </div>
        ) : (
          <div className="border-t border-border-subtle">
            {/* Desktop table */}
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-small">
                <thead>
                  <tr className="border-b border-border-subtle text-caption text-text-tertiary">
                    <th className="px-4 py-2 text-left font-medium">Item</th>
                    <th className="px-3 py-2 text-left font-medium">Unit</th>
                    <th className="px-3 py-2 text-right font-medium">Qty</th>
                    <th className="px-3 py-2 text-right font-medium">Rate</th>
                    <th className="px-3 py-2 text-right font-medium">Disc %</th>
                    <th className="px-3 py-2 text-right font-medium">Tax %</th>
                    <th className="px-4 py-2 text-right font-medium">Amount</th>
                    <th className="px-3 py-2" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-subtle">
                  {section.items.map((item) => (
                    <tr key={item.id} className="hover:bg-hover">
                      <td className="max-w-xs px-4 py-2.5">
                        <div className="flex flex-col">
                          <span className="text-text-primary">{item.description}</span>
                          <div className="flex gap-1.5">
                            {item.isOptional && <span className="text-caption text-text-tertiary">Optional</span>}
                            {item.isAlternative && <span className="text-caption text-text-tertiary">Alternative</span>}
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-2.5 text-text-secondary">{unitLabel(item.unit)}</td>
                      <td className="px-3 py-2.5 text-right tabular-nums text-text-secondary">{item.quantity}</td>
                      <td className="px-3 py-2.5 text-right">
                        <Money value={item.rate} />
                      </td>
                      <td className="px-3 py-2.5 text-right tabular-nums text-text-secondary">{item.discount}</td>
                      <td className="px-3 py-2.5 text-right tabular-nums text-text-secondary">{item.tax}</td>
                      <td className="px-4 py-2.5 text-right font-medium">
                        <Money value={item.amount} />
                      </td>
                      <td className="px-3 py-2.5">
                        <ItemActionsMenu item={item} onEdit={() => onEditItem(item)} onDelete={() => onDeleteItem(item)} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="flex flex-col divide-y divide-border-subtle md:hidden">
              {section.items.map((item) => (
                <div key={item.id} className="flex flex-col gap-2 p-4">
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-body font-medium text-text-primary">{item.description}</span>
                    <ItemActionsMenu item={item} onEdit={() => onEditItem(item)} onDelete={() => onDeleteItem(item)} />
                  </div>
                  <div className="flex items-center justify-between text-small text-text-secondary">
                    <span>
                      {item.quantity} {unitLabel(item.unit)}
                    </span>
                    <Money value={item.rate} />
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-caption text-text-tertiary">Amount</span>
                    <Money value={item.amount} className="font-medium" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
    </Card>
  );
}

function ItemActionsMenu({ item, onEdit, onDelete }: { item: BOQItem; onEdit: () => void; onDelete: () => void }) {
  return (
    <div className="flex items-center justify-end gap-1">
      <Button variant="ghost" size="icon" aria-label={`Edit ${item.description}`} onClick={onEdit}>
        <Pencil className="size-4" />
      </Button>
      <Button variant="ghost" size="icon" aria-label={`Delete ${item.description}`} onClick={onDelete}>
        <Trash2 className="size-4 text-danger-text" />
      </Button>
    </div>
  );
}

function BOQSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <Card className="flex flex-col gap-4 p-5">
        <Skeleton className="h-4 w-40" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
      </Card>
      {Array.from({ length: 2 }).map((_, i) => (
        <Card key={i} className="flex flex-col gap-3 p-4">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-10 w-full" />
          <Skeleton className="h-10 w-full" />
        </Card>
      ))}
    </div>
  );
}
