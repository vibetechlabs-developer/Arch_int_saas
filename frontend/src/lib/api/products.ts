import { apiClient, unwrap, unwrapPaginated, type PaginationMeta } from './client';

// Mirrors backend/apps/products/models.py::ProductUnit's 8 documented values.
export type ProductUnit = 'nos' | 'sqft' | 'sqm' | 'running_ft' | 'kg' | 'litre' | 'set' | 'job';

export const PRODUCT_UNITS: { value: ProductUnit; label: string }[] = [
  { value: 'nos', label: 'Nos' },
  { value: 'sqft', label: 'Sq.ft' },
  { value: 'sqm', label: 'Sq.m' },
  { value: 'running_ft', label: 'Running ft' },
  { value: 'kg', label: 'Kg' },
  { value: 'litre', label: 'Litre' },
  { value: 'set', label: 'Set' },
  { value: 'job', label: 'Job' },
];

export type ProductStatus = 'active' | 'inactive';

// Mirrors backend/apps/products/serializers.py::ProductSerializer.
export interface Product {
  id: string;
  name: string;
  companyId: string;
  subcategoryId: string;
  subcategoryName: string;
  categoryId: string;
  categoryName: string;
  imageUrl: string;
  unit: ProductUnit | '';
  defaultCost: string | null;
  defaultSellingRate: string | null;
  taxRate: string | null;
  status: ProductStatus;
  createdAt: string;
  updatedAt: string;
}

export type ProductOrdering = 'name' | '-name' | 'created_at' | '-created_at' | 'updated_at' | '-updated_at';

export interface ProductListParams {
  category?: string;
  subcategory?: string;
  status?: ProductStatus;
  ordering?: ProductOrdering;
  page?: number;
}

export interface ProductMutableInput {
  name: string;
  imageUrl?: string;
  unit?: ProductUnit | '';
  defaultCost?: string | null;
  defaultSellingRate?: string | null;
  taxRate?: string | null;
  status?: ProductStatus;
}

export interface ProductCreateInput extends ProductMutableInput {
  subcategoryId: string;
}

export async function getProducts(
  params: ProductListParams,
): Promise<{ items: Product[]; pagination: PaginationMeta }> {
  return unwrapPaginated<Product>(
    apiClient.get('/products', {
      params: {
        category: params.category || undefined,
        subcategory: params.subcategory || undefined,
        status: params.status || undefined,
        ordering: params.ordering,
        page: params.page,
      },
    }),
  );
}

export async function getProduct(id: string): Promise<Product> {
  return unwrap<Product>(apiClient.get(`/products/${id}`));
}

export async function createProduct(input: ProductCreateInput): Promise<Product> {
  return unwrap<Product>(apiClient.post('/products', input));
}

export async function updateProduct(id: string, input: Partial<ProductMutableInput>): Promise<Product> {
  return unwrap<Product>(apiClient.patch(`/products/${id}`, input));
}

export async function deleteProduct(id: string): Promise<void> {
  await apiClient.delete(`/products/${id}`);
}
