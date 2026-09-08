import { apiClient, unwrap } from './client';

// Mirrors backend/apps/documents/serializers.py::DocumentSerializer. This
// is the entire field set — there is no title, description, category,
// MIME type, file size, or original filename anywhere in this API.
export interface Document {
  id: string;
  companyId: string;
  projectId: string;
  entityType: string;
  entityId: string;
  fileUrl: string;
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
export interface DocumentCreateInput {
  fileUrl: string;
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
