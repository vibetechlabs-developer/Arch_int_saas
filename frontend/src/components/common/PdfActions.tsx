import { useState } from 'react';
import { Eye, Download } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { ApiError } from '@/lib/api/client';
import { downloadPdf, previewPdf } from '@/lib/pdf';

export interface PdfActionsProps {
  /** The document's own `.../pdf` (BE-076) or private-file `.../download` / `.../receipt` (BE-078) endpoint. */
  url: string;
  className?: string;
  /** Button labels — default to the original PDF-export wording; a generic stored file (document/receipt, BE-078) passes "Preview"/"Download" instead. */
  previewLabel?: string;
  downloadLabel?: string;
  /** Message shown for a non-403/404/5xx failure — defaults to the original PDF-export wording. */
  genericErrorMessage?: string;
}

function describeFileActionError(error: unknown, genericErrorMessage: string): string {
  if (error instanceof Error && error.message === 'POPUP_BLOCKED') {
    return 'Your browser blocked the preview. Please allow pop-ups for this site and try again.';
  }
  if (error instanceof ApiError) {
    if (error.status === 403) return "You don't have permission to download this document.";
    if (error.status === 404) return 'Document not found.';
    if (error.status && error.status >= 500) return genericErrorMessage;
    return error.message;
  }
  return genericErrorMessage;
}

// Shared Preview/Download actions for every server-generated PDF export
// (BOQ workspace, Quotation detail, Invoice detail, BE-076) and every
// privately-stored file (Document/Expense receipt/Payment receipt, BE-078)
// — one icon family (lucide), one loading/error contract, so none of the
// call sites re-implements blob handling, object-URL cleanup, or
// duplicate-click prevention.
export function PdfActions({
  url,
  className,
  previewLabel = 'Preview PDF',
  downloadLabel = 'Download PDF',
  genericErrorMessage = 'PDF could not be generated. Please try again.',
}: PdfActionsProps) {
  const [pending, setPending] = useState<'preview' | 'download' | null>(null);

  const run = async (mode: 'preview' | 'download') => {
    if (pending) return;
    setPending(mode);
    try {
      if (mode === 'preview') {
        await previewPdf(url);
      } else {
        await downloadPdf(url);
      }
    } catch (error) {
      toast.error(describeFileActionError(error, genericErrorMessage));
    } finally {
      setPending(null);
    }
  };

  return (
    <div className={className ?? 'flex items-center gap-2'}>
      <Button
        variant="outline"
        size="sm"
        onClick={() => run('preview')}
        disabled={!!pending}
        loading={pending === 'preview'}
      >
        <Eye />
        {previewLabel}
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={() => run('download')}
        disabled={!!pending}
        loading={pending === 'download'}
      >
        <Download />
        {downloadLabel}
      </Button>
    </div>
  );
}
