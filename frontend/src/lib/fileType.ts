import { File, FileArchive, FileSpreadsheet, FileText, Image, type LucideIcon } from 'lucide-react';

// Document.fileUrl is the ONLY file reference the backend returns — no
// filename, MIME type, or size field exists anywhere in the API. Both
// helpers below are presentation-only derivations from the URL string,
// never treated as validated or authoritative (per the backend audit).

// Derives a human-readable label from a URL's last path segment. Falls
// back to the raw URL if parsing fails — never throws, never renders
// unescaped HTML (the caller always renders this as plain text).
export function displayFileName(fileUrl: string): string {
  try {
    const { pathname } = new URL(fileUrl);
    const last = pathname.split('/').filter(Boolean).pop();
    if (!last) return fileUrl;
    try {
      return decodeURIComponent(last);
    } catch {
      return last;
    }
  } catch {
    return fileUrl;
  }
}

function extensionOf(name: string): string {
  const dot = name.lastIndexOf('.');
  return dot === -1 ? '' : name.slice(dot + 1).toLowerCase();
}

const IMAGE_EXTENSIONS = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp']);
const SPREADSHEET_EXTENSIONS = new Set(['xls', 'xlsx', 'csv']);
const ARCHIVE_EXTENSIONS = new Set(['zip', 'rar', '7z', 'tar', 'gz']);

export interface DocumentTypeInfo {
  icon: LucideIcon;
  label: string;
  isImage: boolean;
}

// Restrained, one-family (lucide) icon mapping for presentation only —
// never used as a security or content-type decision.
export function documentTypeInfo(fileUrl: string): DocumentTypeInfo {
  const ext = extensionOf(displayFileName(fileUrl));
  if (IMAGE_EXTENSIONS.has(ext)) return { icon: Image, label: 'Image', isImage: true };
  if (ext === 'pdf') return { icon: FileText, label: 'PDF', isImage: false };
  if (SPREADSHEET_EXTENSIONS.has(ext)) return { icon: FileSpreadsheet, label: 'Spreadsheet', isImage: false };
  if (ARCHIVE_EXTENSIONS.has(ext)) return { icon: FileArchive, label: 'Archive', isImage: false };
  if (['doc', 'docx', 'txt', 'rtf'].includes(ext)) return { icon: FileText, label: 'Document', isImage: false };
  return { icon: File, label: ext ? ext.toUpperCase() : 'File', isImage: false };
}
