import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProductFormSheet } from '@/components/products/ProductFormSheet';
import { createProduct, updateProduct, uploadProductImage, type Product } from '@/lib/api/products';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/products');
jest.mock('@/lib/api/productCategories', () => ({
  getCategories: jest.fn().mockResolvedValue({ items: [], pagination: { page: 1, pageSize: 100, totalItems: 0, totalPages: 0 } }),
}));
jest.mock('@/lib/api/productSubcategories', () => ({ getSubcategoriesForCategory: jest.fn().mockResolvedValue([]) }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedCreateProduct = createProduct as jest.Mock;
const mockedUpdateProduct = updateProduct as jest.Mock;
const mockedUploadProductImage = uploadProductImage as jest.Mock;

const jpegFile = () => new File([new Uint8Array([1, 2, 3])], 'photo.jpg', { type: 'image/jpeg' });

beforeAll(() => {
  (URL as unknown as { createObjectURL: () => string }).createObjectURL = () => 'blob:mock-preview-url';
  (URL as unknown as { revokeObjectURL: () => void }).revokeObjectURL = () => {};
});

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

  // --- Image upload integration ------------------------------------------

  // Create-mode: selecting a file shows an immediate local preview without
  // uploading yet (the file is only uploaded at Save time — see the
  // module-level comment in ProductFormSheet on why). Never opens the
  // Category/Subcategory Combobox, so it's unaffected by the diagnosed
  // Radix+jsdom hang; the full create+upload path is exercised via the
  // edit-mode (PATCH) tests below instead, which share the same mutation
  // logic end to end.
  it('shows a local preview immediately on file selection, before any upload call', async () => {
    renderSheet();

    await userEvent.upload(screen.getByLabelText('Product image file'), jpegFile());

    expect(await screen.findByRole('img', { name: 'Product preview' })).toHaveAttribute(
      'src',
      'blob:mock-preview-url',
    );
    expect(mockedUploadProductImage).not.toHaveBeenCalled();
  });

  it('never sends the local blob: preview URL to the backend — only the uploaded URL', async () => {
    mockedUploadProductImage.mockResolvedValue({
      url: 'https://cdn.example.com/products/c1/abc.jpg',
      fileName: 'photo.jpg',
      contentType: 'image/jpeg',
      size: 3,
    });
    mockedUpdateProduct.mockResolvedValue(existingProduct);
    renderSheet({ product: existingProduct });

    await userEvent.upload(screen.getByLabelText('Product image file'), jpegFile());
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() =>
      expect(mockedUpdateProduct).toHaveBeenCalledWith(
        'pr1',
        expect.objectContaining({ imageUrl: 'https://cdn.example.com/products/c1/abc.jpg' }),
      ),
    );
    const [, payload] = mockedUpdateProduct.mock.calls[0];
    expect(payload.imageUrl).not.toMatch(/^blob:/);
  });

  it('shows "Uploading image…" while the upload is in flight, then disables Save throughout (duplicate-submit prevention)', async () => {
    let resolveUpload: (v: unknown) => void = () => {};
    mockedUploadProductImage.mockReturnValue(new Promise((resolve) => (resolveUpload = resolve)));
    mockedUpdateProduct.mockResolvedValue(existingProduct);
    renderSheet({ product: existingProduct });

    await userEvent.upload(screen.getByLabelText('Product image file'), jpegFile());
    const saveButton = screen.getByRole('button', { name: /save changes/i });
    await userEvent.click(saveButton);

    expect(await screen.findByText('Uploading image…')).toBeInTheDocument();
    expect(saveButton).toBeDisabled();
    expect(mockedUpdateProduct).not.toHaveBeenCalled();

    resolveUpload({ url: 'https://cdn.example.com/x.jpg', fileName: 'photo.jpg', contentType: 'image/jpeg', size: 3 });
    await waitFor(() => expect(mockedUpdateProduct).toHaveBeenCalledTimes(1));
  });

  it('shows an inline image error and never calls updateProduct when the upload fails', async () => {
    mockedUploadProductImage.mockRejectedValue(new ApiError('VALIDATION_ERROR', 'The uploaded file is not a valid image.'));
    renderSheet({ product: existingProduct });

    await userEvent.upload(screen.getByLabelText('Product image file'), jpegFile());
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    expect(await screen.findByText('The uploaded file is not a valid image.')).toBeInTheDocument();
    expect(mockedUpdateProduct).not.toHaveBeenCalled();
  });

  it('shows the existing persisted image on open, with Replace/Remove available', () => {
    renderSheet({ product: { ...existingProduct, imageUrl: 'https://files.example.com/existing.jpg' } });

    expect(screen.getByRole('img', { name: 'Product preview' })).toHaveAttribute(
      'src',
      'https://files.example.com/existing.jpg',
    );
    expect(screen.getByRole('button', { name: /replace image/i })).toBeInTheDocument();
  });

  it('removes the image and PATCHes an empty imageUrl on save', async () => {
    mockedUpdateProduct.mockResolvedValue({ ...existingProduct, imageUrl: '' });
    renderSheet({ product: { ...existingProduct, imageUrl: 'https://files.example.com/existing.jpg' } });

    await userEvent.click(screen.getByRole('button', { name: /remove/i }));
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() =>
      expect(mockedUpdateProduct).toHaveBeenCalledWith('pr1', expect.objectContaining({ imageUrl: '' })),
    );
    expect(mockedUploadProductImage).not.toHaveBeenCalled();
  });

  it('supports the external Image URL mode end to end, without ever calling the upload endpoint', async () => {
    mockedUpdateProduct.mockResolvedValue(existingProduct);
    renderSheet({ product: existingProduct });

    await userEvent.click(screen.getByRole('button', { name: /use an image url instead/i }));
    await userEvent.type(screen.getByLabelText('Image URL'), 'https://files.example.com/manual.jpg');
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() =>
      expect(mockedUpdateProduct).toHaveBeenCalledWith(
        'pr1',
        expect.objectContaining({ imageUrl: 'https://files.example.com/manual.jpg' }),
      ),
    );
    expect(mockedUploadProductImage).not.toHaveBeenCalled();
  });

  it('maps a backend imageUrl validation error onto the picker, not a generic toast', async () => {
    mockedUpdateProduct.mockRejectedValue(
      new ApiError('VALIDATION_ERROR', 'Request validation failed.', [
        { field: 'imageUrl', issue: 'Enter a valid URL.' },
      ]),
    );
    renderSheet({ product: existingProduct });

    await userEvent.click(screen.getByRole('button', { name: /use an image url instead/i }));
    await userEvent.type(screen.getByLabelText('Image URL'), 'not-a-url');
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    expect(await screen.findByText('Enter a valid URL.')).toBeInTheDocument();
  });
});
