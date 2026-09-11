import { apiClient, unwrap } from './client';

// Mirrors backend/apps/documents/serializers.py::DocumentSerializer.
export interface Document {
  id: string;
  companyId: string;
  projectId: string;
  entityType: string;
  entityId: string;
  fileUrl: string;
  /** True when this document was uploaded via uploadDocumentFile (BE-078) — fetch it through GET /documents/{id}/download rather than fileUrl (blank in that case). */
  hasStoredFile: boolean;
  version: number;
  uploadedById: string | null;
  uploadedByName: string | null;
  uploadedAt: string;
}

export type DocumentOrdering = 'created_at' | '-created_at' | 'version' | '-version';

export interface DocumentListParams {
  entityType?: string;
  entityId?: string;
  ordering?: DocumentOrdering;
}

// `entityType`/`entityId` are deliberately omitted by every caller in
// this module — leaving them out signals the backend to register a
// general project document (defaults to entityType="project",
// entityId=<project id>). Attaching a document to a specific sub-entity
// (a quotation, invoice, expense, ...) is a real backend capability but
// isn't exposed from this general project-level workspace.
//
// Exactly one of `fileUrl` (legacy manual URL registration) /
// `fileStorageKey` (from uploadDocumentFile, BE-078) must be supplied.
export interface DocumentCreateInput {
  fileUrl?: string;
  fileStorageKey?: string;
}

// Mirrors backend/apps/documents/serializers.py::DocumentUploadSerializer.
// No `url` — a private file's only access path is downloadDocumentUrl.
export interface UploadedDocumentFile {
  key: string;
  fileName: string;
  contentType: string;
  size: number;
}

export async function getDocuments(projectId: string, params: DocumentListParams = {}): Promise<Document[]> {
  return unwrap<Document[]>(
    apiClient.get(`/projects/${projectId}/documents`, {
      params: { entityType: params.entityType, entityId: params.entityId, ordering: params.ordering },
    }),
  );
}

export async function getDocument(id: string): Promise<Document> {
  return unwrap<Document>(apiClient.get(`/documents/${id}`));
}

export async function createDocument(projectId: string, input: DocumentCreateInput): Promise<Document> {
  return unwrap<Document>(apiClient.post(`/projects/${projectId}/documents`, input));
}

export async function deleteDocument(id: string): Promise<void> {
  await apiClient.delete(`/documents/${id}`);
}

// Multipart upload to private storage (BE-078) — the browser/axios set the
// Content-Type boundary automatically; never set it manually. Returns a
// storage key (no URL) that the caller passes to createDocument as
// fileStorageKey.
export async function uploadDocumentFile(file: File): Promise<UploadedDocumentFile> {
  const formData = new FormData();
  formData.append('file', file);
  return unwrap<UploadedDocumentFile>(apiClient.post('/documents/upload', formData));
}

/** The authenticated download endpoint for a document with `hasStoredFile: true` — use with previewFile/downloadFile from '@/lib/pdf'. */
export function documentDownloadUrl(documentId: string): string {
  return `/documents/${documentId}/download`;
}
