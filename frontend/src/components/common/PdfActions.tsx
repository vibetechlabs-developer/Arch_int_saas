import { useState } from 'react';
import { Eye, Download } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { ApiError } from '@/lib/api/client';
import { downloadPdf, previewPdf } from '@/lib/pdf';

export interface PdfActionsProps {
  /** The document's own `.../pdf` endpoint (BOQ/Quotation/Invoice, BE-076). */
  url: string;
  className?: string;
}

function describePdfError(error: unknown): string {
  if (error instanceof Error && error.message === 'POPUP_BLOCKED') {
    return 'Your browser blocked the preview. Please allow pop-ups for this site and try again.';
  }
  if (error instanceof ApiError) {
    if (error.status === 403) return "You don't have permission to download this document.";
    if (error.status === 404) return 'Document not found.';
    if (error.status && error.status >= 500) return 'PDF could not be generated. Please try again.';
    return error.message;
  }
  return 'PDF could not be generated. Please try again.';
}

// Shared Preview/Download actions for every document export (BOQ workspace,
// Quotation detail, Invoice detail) — one icon family (lucide), one
// loading/error contract, so none of the three call sites re-implements
// blob handling, object-URL cleanup, or duplicate-click prevention.
export function PdfActions({ url, className }: PdfActionsProps) {
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
      toast.error(describePdfError(error));
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
        Preview PDF
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={() => run('download')}
        disabled={!!pending}
        loading={pending === 'download'}
      >
        <Download />
        Download PDF
      </Button>
    </div>
  );
}
