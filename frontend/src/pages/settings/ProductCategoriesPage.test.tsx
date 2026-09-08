import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test-utils';
import ProductCategoriesPage from '@/pages/settings/ProductCategoriesPage';
import { createCategory, deleteCategory, getCategories, updateCategory, type ProductCategory } from '@/lib/api/productCategories';
import {
  createSubcategory,
  deleteSubcategory,
  getSubcategoriesForCategory,
  updateSubcategory,
  type ProductSubcategory,
} from '@/lib/api/productSubcategories';

jest.mock('@/lib/api/productCategories');
jest.mock('@/lib/api/productSubcategories');
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedGetCategories = getCategories as jest.Mock;
const mockedCreateCategory = createCategory as jest.Mock;
const mockedUpdateCategory = updateCategory as jest.Mock;
const mockedDeleteCategory = deleteCategory as jest.Mock;
const mockedGetSubcategories = getSubcategoriesForCategory as jest.Mock;
const mockedCreateSubcategory = createSubcategory as jest.Mock;
const mockedUpdateSubcategory = updateSubcategory as jest.Mock;
const mockedDeleteSubcategory = deleteSubcategory as jest.Mock;

const category: ProductCategory = {
  id: 'cat1',
  name: 'Furniture',
  companyId: 'c1',
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-02T00:00:00Z',
};

const subcategory: ProductSubcategory = {
  id: 'sc1',
  name: 'Wardrobes',
  companyId: 'c1',
  categoryId: 'cat1',
  categoryName: 'Furniture',
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-02T00:00:00Z',
};

function categoriesPage(items: ProductCategory[]) {
  return { items, pagination: { page: 1, pageSize: 100, totalItems: items.length, totalPages: items.length > 0 ? 1 : 0 } };
}

async function expandCategory(name: string) {
  await userEvent.click(screen.getByRole('button', { name }));
}

describe('ProductCategoriesPage', () => {
  beforeEach(() => {
    mockedGetSubcategories.mockResolvedValue([subcategory]);
  });
  afterEach(() => jest.clearAllMocks());

  it('renders the category list once loaded', async () => {
    mockedGetCategories.mockResolvedValue(categoriesPage([category]));
    renderWithProviders(<ProductCategoriesPage />, { route: '/settings/product-categories' });

    expect(await screen.findByText('Furniture')).toBeInTheDocument();
  });

  it('creates a new category', async () => {
    mockedGetCategories.mockResolvedValue(categoriesPage([]));
    mockedCreateCategory.mockResolvedValue({ ...category, name: 'Lighting' });
    renderWithProviders(<ProductCategoriesPage />, { route: '/settings/product-categories' });
    await screen.findByText('No product categories yet');

    await userEvent.click(screen.getByRole('button', { name: /new category/i }));
    await userEvent.type(screen.getByLabelText('Category name'), 'Lighting');
    await userEvent.click(screen.getByRole('button', { name: /create category/i }));

    await waitFor(() => expect(mockedCreateCategory).toHaveBeenCalledWith('Lighting'));
  });

  it('edits an existing category', async () => {
    mockedGetCategories.mockResolvedValue(categoriesPage([category]));
    mockedUpdateCategory.mockResolvedValue({ ...category, name: 'Modular Furniture' });
    renderWithProviders(<ProductCategoriesPage />, { route: '/settings/product-categories' });
    await screen.findByText('Furniture');

    await userEvent.click(screen.getByRole('button', { name: 'Edit Furniture' }));
    await userEvent.clear(screen.getByLabelText('Category name'));
    await userEvent.type(screen.getByLabelText('Category name'), 'Modular Furniture');
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => expect(mockedUpdateCategory).toHaveBeenCalledWith('cat1', 'Modular Furniture'));
  });

  it('shows a confirmation dialog before deleting a category', async () => {
    mockedGetCategories.mockResolvedValue(categoriesPage([category]));
    mockedDeleteCategory.mockResolvedValue(undefined);
    renderWithProviders(<ProductCategoriesPage />, { route: '/settings/product-categories' });
    await screen.findByText('Furniture');

    await userEvent.click(screen.getByRole('button', { name: 'Delete Furniture' }));
    expect(await screen.findByText('Delete this category?')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Delete category' }));
    await waitFor(() => expect(mockedDeleteCategory).toHaveBeenCalledWith('cat1'));
  });

  it('lists subcategories once a category is expanded', async () => {
    mockedGetCategories.mockResolvedValue(categoriesPage([category]));
    renderWithProviders(<ProductCategoriesPage />, { route: '/settings/product-categories' });
    await screen.findByText('Furniture');

    await expandCategory('Furniture');

    expect(await screen.findByText('Wardrobes')).toBeInTheDocument();
    expect(mockedGetSubcategories).toHaveBeenCalledWith('cat1', 'name');
  });

  it('creates a new subcategory under the expanded category', async () => {
    mockedGetCategories.mockResolvedValue(categoriesPage([category]));
    mockedCreateSubcategory.mockResolvedValue({ ...subcategory, id: 'sc2', name: 'Cabinets' });
    renderWithProviders(<ProductCategoriesPage />, { route: '/settings/product-categories' });
    await screen.findByText('Furniture');
    await expandCategory('Furniture');
    await screen.findByText('Wardrobes');

    await userEvent.click(screen.getByRole('button', { name: /add subcategory/i }));
    await userEvent.type(screen.getByLabelText('Subcategory name'), 'Cabinets');
    await userEvent.click(screen.getByRole('button', { name: /create subcategory/i }));

    await waitFor(() => expect(mockedCreateSubcategory).toHaveBeenCalledWith('cat1', 'Cabinets'));
  });

  it('edits an existing subcategory', async () => {
    mockedGetCategories.mockResolvedValue(categoriesPage([category]));
    mockedUpdateSubcategory.mockResolvedValue({ ...subcategory, name: 'Wall Wardrobes' });
    renderWithProviders(<ProductCategoriesPage />, { route: '/settings/product-categories' });
    await screen.findByText('Furniture');
    await expandCategory('Furniture');
    await screen.findByText('Wardrobes');

    await userEvent.click(screen.getByRole('button', { name: 'Edit Wardrobes' }));
    await userEvent.clear(screen.getByLabelText('Subcategory name'));
    await userEvent.type(screen.getByLabelText('Subcategory name'), 'Wall Wardrobes');
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => expect(mockedUpdateSubcategory).toHaveBeenCalledWith('sc1', 'Wall Wardrobes'));
  });

  it('deletes a subcategory after confirmation', async () => {
    mockedGetCategories.mockResolvedValue(categoriesPage([category]));
    mockedDeleteSubcategory.mockResolvedValue(undefined);
    renderWithProviders(<ProductCategoriesPage />, { route: '/settings/product-categories' });
    await screen.findByText('Furniture');
    await expandCategory('Furniture');
    await screen.findByText('Wardrobes');

    await userEvent.click(screen.getByRole('button', { name: 'Delete Wardrobes' }));
    expect(await screen.findByText('Delete this subcategory?')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: 'Delete subcategory' }));
    await waitFor(() => expect(mockedDeleteSubcategory).toHaveBeenCalledWith('sc1'));
  });
});
