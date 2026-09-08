import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test-utils';
import ProductDetailPage from '@/pages/products/ProductDetailPage';
import { deleteProduct, getProduct, type Product } from '@/lib/api/products';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/products', () => ({
  ...jest.requireActual('@/lib/api/products'),
  getProduct: jest.fn(),
  deleteProduct: jest.fn(),
}));
jest.mock('@/lib/api/productCategories', () => ({
  getCategories: jest.fn().mockResolvedValue({ items: [], pagination: { page: 1, pageSize: 100, totalItems: 0, totalPages: 0 } }),
}));
jest.mock('@/lib/api/productSubcategories', () => ({ getSubcategoriesForCategory: jest.fn().mockResolvedValue([]) }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const mockedGetProduct = getProduct as jest.Mock;
const mockedDeleteProduct = deleteProduct as jest.Mock;

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

describe('ProductDetailPage', () => {
  afterEach(() => jest.clearAllMocks());

  it('shows a skeleton before the product loads', async () => {
    let resolveRequest: (v: Product) => void = () => {};
    mockedGetProduct.mockReturnValue(new Promise((resolve) => (resolveRequest = resolve)));
    renderWithProviders(<ProductDetailPage />, { route: '/products/pr1', path: '/products/:productId' });

    expect(screen.queryByText('Modular Wardrobe Panel')).not.toBeInTheDocument();
    resolveRequest(product);
    expect(await screen.findByText('Modular Wardrobe Panel')).toBeInTheDocument();
  });

  it('renders product details once loaded (success state)', async () => {
    mockedGetProduct.mockResolvedValue(product);
    renderWithProviders(<ProductDetailPage />, { route: '/products/pr1', path: '/products/:productId' });

    expect(await screen.findByText('Modular Wardrobe Panel')).toBeInTheDocument();
    expect(screen.getByText('Furniture / Wardrobes')).toBeInTheDocument();
    expect(screen.getByText('Sq.ft')).toBeInTheDocument();
  });

  it('shows a dedicated Product Not Found state on a 404, not a generic error', async () => {
    mockedGetProduct.mockRejectedValue(new ApiError('NOT_FOUND', 'The requested product was not found.'));
    renderWithProviders(<ProductDetailPage />, { route: '/products/pr1', path: '/products/:productId' });

    expect(await screen.findByText('Product not found')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /back to products/i })).toBeInTheDocument();
  });

  it('shows a confirmation dialog before deleting, explaining the consequence', async () => {
    mockedGetProduct.mockResolvedValue(product);
    renderWithProviders(<ProductDetailPage />, { route: '/products/pr1', path: '/products/:productId' });
    await screen.findByText('Modular Wardrobe Panel');

    await userEvent.click(screen.getByRole('button', { name: /^delete$/i }));

    expect(await screen.findByText('Delete this product?')).toBeInTheDocument();
    expect(screen.getByText('This removes "Modular Wardrobe Panel" from the catalog.')).toBeInTheDocument();
    expect(mockedDeleteProduct).not.toHaveBeenCalled();
  });

  it('deletes the product after confirmation and navigates back to the list', async () => {
    mockedGetProduct.mockResolvedValue(product);
    mockedDeleteProduct.mockResolvedValue(undefined);
    renderWithProviders(<ProductDetailPage />, { route: '/products/pr1', path: '/products/:productId' });
    await screen.findByText('Modular Wardrobe Panel');

    await userEvent.click(screen.getByRole('button', { name: /^delete$/i }));
    await userEvent.click(screen.getByRole('button', { name: 'Delete product' }));

    await waitFor(() => expect(mockedDeleteProduct).toHaveBeenCalledWith('pr1'));
  });

  it('shows the backend error message when delete fails (e.g. a conflict)', async () => {
    mockedGetProduct.mockResolvedValue(product);
    mockedDeleteProduct.mockRejectedValue(new ApiError('CONFLICT', 'This product cannot be deleted right now.'));
    renderWithProviders(<ProductDetailPage />, { route: '/products/pr1', path: '/products/:productId' });
    await screen.findByText('Modular Wardrobe Panel');

    await userEvent.click(screen.getByRole('button', { name: /^delete$/i }));
    await userEvent.click(screen.getByRole('button', { name: 'Delete product' }));

    await waitFor(() => expect(mockedDeleteProduct).toHaveBeenCalled());
  });
});
