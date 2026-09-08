import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProductFormSheet } from '@/components/products/ProductFormSheet';
import { createProduct, updateProduct, type Product } from '@/lib/api/products';

jest.mock('@/lib/api/products');
jest.mock('@/lib/api/productCategories', () => ({
  getCategories: jest.fn().mockResolvedValue({ items: [], pagination: { page: 1, pageSize: 100, totalItems: 0, totalPages: 0 } }),
}));
jest.mock('@/lib/api/productSubcategories', () => ({ getSubcategoriesForCategory: jest.fn().mockResolvedValue([]) }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedCreateProduct = createProduct as jest.Mock;
const mockedUpdateProduct = updateProduct as jest.Mock;

const existingProduct: Product = {
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
  createdAt: '',
  updatedAt: '',
};

function renderSheet(props: Partial<React.ComponentProps<typeof ProductFormSheet>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const onOpenChange = jest.fn();
  render(
    <QueryClientProvider client={queryClient}>
      <ProductFormSheet open onOpenChange={onOpenChange} {...props} />
    </QueryClientProvider>,
  );
  return { onOpenChange };
}

describe('ProductFormSheet', () => {
  afterEach(() => jest.clearAllMocks());

  // Create-mode validation only — never opens the Category/Subcategory
  // Combobox popovers, so it's unaffected by the diagnosed Radix+jsdom hang.
  it('rejects a blank product name before ever calling the API', async () => {
    renderSheet();
    await userEvent.click(screen.getByRole('button', { name: /create product/i }));

    expect(await screen.findByText('Product name is required')).toBeInTheDocument();
    expect(mockedCreateProduct).not.toHaveBeenCalled();
  });

  it('requires a subcategory to be selected before creating a product', async () => {
    renderSheet();
    await userEvent.type(screen.getByLabelText('Product name'), 'New Product');
    await userEvent.click(screen.getByRole('button', { name: /create product/i }));

    expect(await screen.findByText('Select a subcategory for this product.')).toBeInTheDocument();
    expect(mockedCreateProduct).not.toHaveBeenCalled();
  });

  // Edit-mode tests never render the Combobox pair at all (subcategory is
  // shown as a static field, matching the backend's "not reassignable"
  // contract) — so these exercise real mutation/field-mapping logic
  // without touching any Radix popover.
  it('pre-fills the form and PATCHes the existing product when editing', async () => {
    mockedUpdateProduct.mockResolvedValue({ ...existingProduct, name: 'Renamed Panel' });
    renderSheet({ product: existingProduct });

    expect(screen.getByLabelText('Product name')).toHaveValue('Modular Wardrobe Panel');
    expect(screen.getByText('Furniture')).toBeInTheDocument();
    expect(screen.getByText('Wardrobes')).toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText('Product name'));
    await userEvent.type(screen.getByLabelText('Product name'), 'Renamed Panel');
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() =>
      expect(mockedUpdateProduct).toHaveBeenCalledWith('pr1', expect.objectContaining({ name: 'Renamed Panel' })),
    );
  });

  it('maps a 400 VALIDATION_ERROR field back onto the matching form field', async () => {
    const { ApiError } = jest.requireActual('@/lib/api/client');
    mockedUpdateProduct.mockRejectedValue(
      new ApiError('VALIDATION_ERROR', 'Request validation failed.', [
        { field: 'taxRate', issue: 'Ensure that there are no more than 5 digits in total.' },
      ]),
    );
    renderSheet({ product: existingProduct });

    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    expect(await screen.findByText('Ensure that there are no more than 5 digits in total.')).toBeInTheDocument();
  });
});
