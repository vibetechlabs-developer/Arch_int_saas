import { apiClient, unwrap } from './client';
import type { CategoryOrdering } from './productCategories';

// Mirrors backend/apps/products/serializers.py::ProductSubcategorySerializer.
export interface ProductSubcategory {
  id: string;
  name: string;
  companyId: string;
  categoryId: string;
  categoryName: string;
  createdAt: string;
  updatedAt: string;
}

// GET /product-categories/{categoryId}/subcategories returns a plain
// array, not a paginated envelope — unlike every other list endpoint in
// this app (matches the real backend contract exactly).
export async function getSubcategoriesForCategory(
  categoryId: string,
  ordering?: CategoryOrdering,
): Promise<ProductSubcategory[]> {
  return unwrap<ProductSubcategory[]>(
    apiClient.get(`/product-categories/${categoryId}/subcategories`, { params: { ordering } }),
  );
}

export async function createSubcategory(categoryId: string, name: string): Promise<ProductSubcategory> {
  return unwrap<ProductSubcategory>(apiClient.post(`/product-categories/${categoryId}/subcategories`, { name }));
}

export async function getSubcategory(id: string): Promise<ProductSubcategory> {
  return unwrap<ProductSubcategory>(apiClient.get(`/product-subcategories/${id}`));
}

export async function updateSubcategory(id: string, name: string): Promise<ProductSubcategory> {
  return unwrap<ProductSubcategory>(apiClient.patch(`/product-subcategories/${id}`, { name }));
}

export async function deleteSubcategory(id: string): Promise<void> {
  await apiClient.delete(`/product-subcategories/${id}`);
}
