import { apiClient } from '@/lib/api/client';

// Shared preview/download plumbing for every server-rendered PDF export
// (BOQ/Quotation/Invoice, BE-076). Always an authenticated axios request
// returning a blob — never a raw <a href> to a protected URL, and never
// the auth token placed in a query string.
async function fetchPdfBlob(url: string, mode: 'preview' | 'download'): Promise<{ blob: Blob; filename: string }> {
  const response = await apiClient.get<Blob>(url, {
    params: mode === 'preview' ? { mode: 'preview' } : undefined,
    responseType: 'blob',
  });
  const disposition = response.headers['content-disposition'] as string | undefined;
  const match = disposition ? /filename="([^"]+)"/.exec(disposition) : null;
  return { blob: response.data, filename: match?.[1] ?? 'document.pdf' };
}

/**
 * Opens the PDF in a new tab via an object URL (never a public/unprotected
 * URL — the request itself is authenticated, only the resulting blob is
 * ever exposed to the browser). Throws `POPUP_BLOCKED` if the browser
 * prevented the new tab, so callers can surface a clear message instead of
 * silently doing nothing.
 */
export async function previewPdf(url: string): Promise<void> {
  const { blob } = await fetchPdfBlob(url, 'preview');
  const objectUrl = URL.createObjectURL(blob);
  const win = window.open(objectUrl, '_blank');
  // Revoked after a delay rather than immediately — revoking synchronously
  // can race the new tab's own fetch of the blob: URL before it finishes
  // loading the object.
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 60_000);
  if (!win) {
    throw new Error('POPUP_BLOCKED');
  }
}

/** Downloads the PDF using the server's own Content-Disposition filename. */
export async function downloadPdf(url: string): Promise<void> {
  const { blob, filename } = await fetchPdfBlob(url, 'download');
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(objectUrl);
}
