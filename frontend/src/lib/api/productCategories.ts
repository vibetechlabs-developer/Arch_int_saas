import { apiClient, unwrap, unwrapPaginated, type PaginationMeta } from './client';

// Mirrors backend/apps/products/serializers.py::ProductCategorySerializer.
export interface ProductCategory {
  id: string;
  name: string;
  companyId: string;
  createdAt: string;
  updatedAt: string;
}

export type CategoryOrdering = 'name' | '-name' | 'created_at' | '-created_at' | 'updated_at' | '-updated_at';

export async function getCategories(
  params: { ordering?: CategoryOrdering; page?: number; pageSize?: number } = {},
): Promise<{ items: ProductCategory[]; pagination: PaginationMeta }> {
  return unwrapPaginated<ProductCategory>(
    apiClient.get('/product-categories', { params: { ordering: params.ordering, page: params.page, pageSize: params.pageSize } }),
  );
}

export async function getCategory(id: string): Promise<ProductCategory> {
  return unwrap<ProductCategory>(apiClient.get(`/product-categories/${id}`));
}

export async function createCategory(name: string): Promise<ProductCategory> {
  return unwrap<ProductCategory>(apiClient.post('/product-categories', { name }));
}

export async function updateCategory(id: string, name: string): Promise<ProductCategory> {
  return unwrap<ProductCategory>(apiClient.patch(`/product-categories/${id}`, { name }));
}

export async function deleteCategory(id: string): Promise<void> {
  await apiClient.delete(`/product-categories/${id}`);
}
