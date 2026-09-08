import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test-utils';
import ProductsListPage from '@/pages/products/ProductsListPage';
import { getProducts } from '@/lib/api/products';
import { ApiError, type PaginationMeta } from '@/lib/api/client';
import type { Product } from '@/lib/api/products';

jest.mock('@/lib/api/products');
jest.mock('@/lib/api/productCategories', () => ({
  getCategories: jest.fn().mockResolvedValue({ items: [], pagination: { page: 1, pageSize: 100, totalItems: 0, totalPages: 0 } }),
}));
jest.mock('@/lib/api/productSubcategories', () => ({ getSubcategoriesForCategory: jest.fn().mockResolvedValue([]) }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const mockedGetProducts = getProducts as jest.Mock;

const product: Product = {
  id: 'pr1',
  name: 'Modular Wardrobe Panel',
  companyId: 'c1',
  subcategoryId: 'sc1',
  subcategoryName: 'Wardrobes',
  categoryId: 'cat1',
  categoryName: 'Furniture',
  imageUrl: '',
  unit: 'sqft',
  defaultCost: '450.00',
  defaultSellingRate: '650.00',
  taxRate: '18.00',
  status: 'active',
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-02T00:00:00Z',
};

function pagination(overrides: Partial<PaginationMeta> = {}): PaginationMeta {
  return { page: 1, pageSize: 25, totalItems: 1, totalPages: 1, ...overrides };
}

describe('ProductsListPage', () => {
  afterEach(() => jest.clearAllMocks());

  it('shows loading skeleton rows before the request resolves', async () => {
    let resolveRequest: (v: { items: Product[]; pagination: PaginationMeta }) => void = () => {};
    mockedGetProducts.mockReturnValue(new Promise((resolve) => (resolveRequest = resolve)));
    renderWithProviders(<ProductsListPage />, { route: '/products' });

    expect(screen.queryByText('Modular Wardrobe Panel')).not.toBeInTheDocument();
    resolveRequest({ items: [product], pagination: pagination() });
    expect(await screen.findAllByText('Modular Wardrobe Panel')).not.toHaveLength(0);
  });

  it('renders products once the request resolves (success state)', async () => {
    mockedGetProducts.mockResolvedValue({ items: [product], pagination: pagination() });
    renderWithProviders(<ProductsListPage />, { route: '/products' });

    expect((await screen.findAllByText('Modular Wardrobe Panel')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Furniture').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Wardrobes').length).toBeGreaterThan(0);
  });

  it('shows a "no products yet" empty state with a create CTA when there are none', async () => {
    mockedGetProducts.mockResolvedValue({ items: [], pagination: pagination({ totalItems: 0, totalPages: 0 }) });
    renderWithProviders(<ProductsListPage />, { route: '/products' });

    expect((await screen.findAllByText('No products yet')).length).toBeGreaterThan(0);
  });

  it('shows the backend error message when the list request fails', async () => {
    mockedGetProducts.mockRejectedValue(new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.'));
    renderWithProviders(<ProductsListPage />, { route: '/products' });

    expect(await screen.findByText('You do not have permission to perform this action.')).toBeInTheDocument();
  });

  it('requests the next page when pagination advances', async () => {
    mockedGetProducts.mockResolvedValue({ items: [product], pagination: pagination({ totalPages: 3 }) });
    renderWithProviders(<ProductsListPage />, { route: '/products' });
    await screen.findAllByText('Modular Wardrobe Panel');
    mockedGetProducts.mockClear();

    const nextButtons = screen.getAllByRole('button', { name: 'Next page' });
    await userEvent.click(nextButtons[0]);

    await waitFor(() => expect(mockedGetProducts).toHaveBeenCalledWith(expect.objectContaining({ page: 2 })));
  });
});
