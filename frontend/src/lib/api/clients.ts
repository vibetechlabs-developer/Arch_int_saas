import { apiClient, unwrap, unwrapPaginated, type PaginationMeta } from './client';

// Mirrors backend/apps/clients/serializers.py::ClientSerializer exactly.
// `companyName` is the CLIENT's own business/trading name (Client.company_name)
// — distinct from `companyId`, the tenant Company this client belongs to.
export interface Client {
  id: string;
  name: string;
  companyName: string;
  email: string;
  mobile: string;
  gstin: string;
  addresses: unknown[];
  notes: string;
  companyId: string;
  createdAt: string;
  updatedAt: string;
}

export type ClientOrdering = 'name' | '-name' | 'created_at' | '-created_at' | 'updated_at' | '-updated_at';

export interface ClientListParams {
  search?: string;
  ordering?: ClientOrdering;
  page?: number;
}

export interface ClientInput {
  name: string;
  companyName?: string;
  email?: string;
  mobile?: string;
  gstin?: string;
  notes?: string;
}

export async function getClients(params: ClientListParams): Promise<{ items: Client[]; pagination: PaginationMeta }> {
  return unwrapPaginated<Client>(
    apiClient.get('/clients', {
      params: {
        search: params.search || undefined,
        ordering: params.ordering,
        page: params.page,
      },
    }),
  );
}

export async function getClient(id: string): Promise<Client> {
  return unwrap<Client>(apiClient.get(`/clients/${id}`));
}

export async function createClient(input: ClientInput): Promise<Client> {
  return unwrap<Client>(apiClient.post('/clients', input));
}

export async function updateClient(id: string, input: Partial<ClientInput>): Promise<Client> {
  return unwrap<Client>(apiClient.patch(`/clients/${id}`, input));
}

export async function deleteClient(id: string): Promise<void> {
  await apiClient.delete(`/clients/${id}`);
}
