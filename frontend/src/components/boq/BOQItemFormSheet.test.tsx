import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BOQItemFormSheet } from '@/components/boq/BOQItemFormSheet';
import { createBOQItem, updateBOQItem, type BOQItem } from '@/lib/api/boq';

jest.mock('@/lib/api/boq');
jest.mock('@/lib/api/products', () => ({
  ...jest.requireActual('@/lib/api/products'),
  getProducts: jest.fn().mockResolvedValue({ items: [], pagination: { page: 1, pageSize: 100, totalItems: 0, totalPages: 0 } }),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedCreateItem = createBOQItem as jest.Mock;
const mockedUpdateItem = updateBOQItem as jest.Mock;

const existingItem: BOQItem = {
  id: 'i1',
  sectionId: 's1',
  productId: null,
  productName: null,
  description: 'Modular switchboard',
  quantity: '2.00',
  unit: 'nos',
  rate: '1200.00',
  discount: '0.00',
  tax: '18.00',
  amount: '2400.00',
  isOptional: false,
  isAlternative: false,
  notes: '',
  createdAt: '',
  updatedAt: '',
};

function renderSheet(props: Partial<React.ComponentProps<typeof BOQItemFormSheet>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const onOpenChange = jest.fn();
  render(
    <QueryClientProvider client={queryClient}>
      <BOQItemFormSheet open onOpenChange={onOpenChange} projectId="p1" sectionId="s1" {...props} />
    </QueryClientProvider>,
  );
  return { onOpenChange };
}

describe('BOQItemFormSheet', () => {
  afterEach(() => jest.clearAllMocks());

  it('requires a quantity before creating an item', async () => {
    renderSheet();
    await userEvent.click(screen.getByRole('button', { name: /add item/i }));

    expect(await screen.findByText('Quantity is required')).toBeInTheDocument();
    expect(mockedCreateItem).not.toHaveBeenCalled();
  });

  it('requires description, unit, and rate for a free-text item with no product', async () => {
    renderSheet();
    await userEvent.type(screen.getByLabelText('Quantity'), '5');
    await userEvent.click(screen.getByRole('button', { name: /add item/i }));

    expect(await screen.findByText('Description is required when no product is referenced.')).toBeInTheDocument();
    expect(screen.getByText('Unit is required when no product is referenced.')).toBeInTheDocument();
    expect(screen.getByText('Rate is required when no product is referenced.')).toBeInTheDocument();
    expect(mockedCreateItem).not.toHaveBeenCalled();
  });

  // Edit mode never touches the Product combobox (shown as static context)
  // and this test never opens the Unit Select either — it only changes a
  // plain text field, so it's unaffected by the diagnosed Radix+jsdom hang.
  it('pre-fills the form and PATCHes the existing item when editing', async () => {
    mockedUpdateItem.mockResolvedValue({ ...existingItem, quantity: '3.00', amount: '3600.00' });
    renderSheet({ item: existingItem });

    expect(screen.getByLabelText('Description')).toHaveValue('Modular switchboard');
    expect(screen.getByLabelText('Quantity')).toHaveValue('2.00');
    expect(screen.getByText('Free-text item (no product referenced)')).toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText('Quantity'));
    await userEvent.type(screen.getByLabelText('Quantity'), '3');
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() =>
      expect(mockedUpdateItem).toHaveBeenCalledWith('i1', expect.objectContaining({ quantity: '3' })),
    );
  });

  it('maps a 400 VALIDATION_ERROR field back onto the matching form field', async () => {
    const { ApiError } = jest.requireActual('@/lib/api/client');
    mockedUpdateItem.mockRejectedValue(
      new ApiError('VALIDATION_ERROR', 'Request validation failed.', [
        { field: 'discount', issue: 'Ensure this value is less than or equal to 100.' },
      ]),
    );
    renderSheet({ item: existingItem });

    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    expect(await screen.findByText('Ensure this value is less than or equal to 100.')).toBeInTheDocument();
  });

  it('shows a product referenced on an item as static, non-editable context in edit mode', () => {
    renderSheet({ item: { ...existingItem, productId: 'pr1', productName: 'Modular Switchboard 32A' } });

    expect(screen.getByText('Modular Switchboard 32A')).toBeInTheDocument();
    // Editing never renders the Product picker at all — nothing to query for its absence beyond
    // confirming the static text takes its place.
  });
});
