import { render, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ProductCombobox } from '@/components/boq/ProductCombobox';
import { getProducts } from '@/lib/api/products';

jest.mock('@/lib/api/products');
const mockedGetProducts = getProducts as jest.Mock;

function renderCombobox() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ProductCombobox value={null} onSelect={jest.fn()} />
    </QueryClientProvider>,
  );
}

describe('ProductCombobox', () => {
  afterEach(() => jest.clearAllMocks());

  // Product has no `search` param — this asserts the real API integration
  // contract: an active-only, name-ordered, bounded-page request fired on
  // mount, not a hardcoded option list.
  it('requests only active products, ordered by name, on mount', async () => {
    mockedGetProducts.mockResolvedValue({ items: [], pagination: { page: 1, pageSize: 100, totalItems: 0, totalPages: 0 } });
    renderCombobox();

    await waitFor(() =>
      expect(mockedGetProducts).toHaveBeenCalledWith({ status: 'active', ordering: 'name', pageSize: 100 }),
    );
  });
});
