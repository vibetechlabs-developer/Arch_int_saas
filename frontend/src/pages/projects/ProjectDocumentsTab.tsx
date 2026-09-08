import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { type ColumnDef } from '@tanstack/react-table';
import { ExternalLink, FolderOpen, Plus, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { DataTable } from '@/components/common/DataTable';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { ApiError } from '@/lib/api/client';
import { deleteDocument, getDocuments, type Document } from '@/lib/api/documents';
import { documentKeys } from '@/lib/queryKeys';
import { formatDateTime } from '@/lib/format';
import { displayFileName, documentTypeInfo } from '@/lib/fileType';
import type { Project } from '@/lib/api/projects';
import { RegisterDocumentSheet } from '@/components/documents/RegisterDocumentSheet';

function DocumentName({ document }: { document: Document }) {
  const { icon: Icon, isImage } = documentTypeInfo(document.fileUrl);
  const [thumbnailFailed, setThumbnailFailed] = useState(false);
  const name = displayFileName(document.fileUrl);
  const isGeneralProjectDocument = document.entityType === 'project';

  return (
    <div className="flex items-center gap-3">
      {isImage && !thumbnailFailed ? (
        <img
          src={document.fileUrl}
          alt=""
          className="size-8 shrink-0 rounded object-cover"
          onError={() => setThumbnailFailed(true)}
        />
      ) : (
        <Icon className="size-4 shrink-0 text-text-tertiary" />
      )}
      <div className="flex flex-col overflow-hidden">
        <span className="truncate text-body font-medium text-text-primary" title={name}>
          {name}
        </span>
        {!isGeneralProjectDocument && (
          <span className="text-caption text-text-tertiary">Attached to {document.entityType}</span>
        )}
      </div>
    </div>
  );
}

export default function ProjectDocumentsTab() {
  const { project } = useOutletContext<{ project: Project }>();
  const queryClient = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [deletingDocument, setDeletingDocument] = useState<Document | null>(null);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: documentKeys.project(project.id),
    queryFn: () => getDocuments(project.id),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: documentKeys.project(project.id) });
      toast.success('Document deleted');
      setDeletingDocument(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete this document.');
      setDeletingDocument(null);
    },
  });

  if (isError) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const columns: ColumnDef<Document, unknown>[] = [
    {
      accessorKey: 'fileUrl',
      header: 'Name',
      cell: ({ row }) => <DocumentName document={row.original} />,
    },
    {
      accessorKey: 'version',
      header: 'Version',
      cell: ({ row }) => <span className="tabular-nums text-small text-text-secondary">v{row.original.version}</span>,
    },
    {
      accessorKey: 'uploadedByName',
      header: 'Uploaded By',
      cell: ({ row }) => <span className="text-small text-text-secondary">{row.original.uploadedByName ?? '—'}</span>,
    },
    {
      accessorKey: 'uploadedAt',
      header: 'Uploaded',
      cell: ({ row }) => <span className="text-small text-text-tertiary">{formatDateTime(row.original.uploadedAt)}</span>,
    },
    {
      id: 'actions',
      header: '',
      enableSorting: false,
      enableHiding: false,
      cell: ({ row }) => (
        <div className="flex items-center justify-end gap-1">
          <Button variant="ghost" size="icon" aria-label={`Open ${displayFileName(row.original.fileUrl)}`} asChild>
            <a href={row.original.fileUrl} target="_blank" rel="noreferrer">
              <ExternalLink className="size-4" />
            </a>
          </Button>
          <Button
            variant="ghost"
            size="icon"
            aria-label={`Delete ${displayFileName(row.original.fileUrl)}`}
            onClick={() => setDeletingDocument(row.original)}
          >
            <Trash2 className="size-4 text-danger-text" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h3 className="text-h3 text-text-primary">Documents</h3>
        <Button variant="primary" size="sm" onClick={() => setAddOpen(true)}>
          <Plus />
          Add Document
        </Button>
      </div>

      <DataTable
        columns={columns}
        data={data ?? []}
        isLoading={isLoading}
        hideSearch
        emptyState={{
          icon: FolderOpen,
          title: 'No documents uploaded yet',
          description: 'Upload files related to this project so the team can access them here.',
          action: { label: 'Add Document', onClick: () => setAddOpen(true) },
        }}
      />

      <RegisterDocumentSheet open={addOpen} onOpenChange={setAddOpen} projectId={project.id} />

      <ConfirmationDialog
        open={!!deletingDocument}
        onOpenChange={(open) => !open && setDeletingDocument(null)}
        title="Delete document?"
        description={`This removes "${deletingDocument ? displayFileName(deletingDocument.fileUrl) : ''}" from this project. It does not delete the underlying file from where it's hosted.`}
        confirmLabel="Delete document"
        destructive
        loading={deleteMutation.isPending}
        onConfirm={() => deletingDocument && deleteMutation.mutate(deletingDocument.id)}
      />
    </div>
  );
}
