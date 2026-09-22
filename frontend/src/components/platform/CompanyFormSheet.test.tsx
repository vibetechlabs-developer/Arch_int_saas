import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CompanyFormSheet } from '@/components/platform/CompanyFormSheet';
import { createCompany, updateCompany, type Company } from '@/lib/api/company';

jest.mock('@/lib/api/company', () => ({
  ...jest.requireActual('@/lib/api/company'),
  createCompany: jest.fn(),
  updateCompany: jest.fn(),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedCreateCompany = createCompany as jest.Mock;
const mockedUpdateCompany = updateCompany as jest.Mock;

const existingCompany: Company = {
  id: 'c42',
  name: 'Old Studio',
  status: 'trial',
  currency: 'INR',
  gstNumber: null,
  logoUrl: '',
  settings: {},
  createdAt: '',
  updatedAt: '',
};

function renderSheet(props: Partial<React.ComponentProps<typeof CompanyFormSheet>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const onOpenChange = jest.fn();
  render(
    <QueryClientProvider client={queryClient}>
      <CompanyFormSheet open onOpenChange={onOpenChange} {...props} />
    </QueryClientProvider>,
  );
  return { onOpenChange };
}

describe('CompanyFormSheet', () => {
  afterEach(() => jest.clearAllMocks());

  it('rejects a blank name before ever calling the API', async () => {
    renderSheet();

    await userEvent.click(screen.getByRole('button', { name: /create company/i }));

    expect(await screen.findByText('Company name is required')).toBeInTheDocument();
    expect(mockedCreateCompany).not.toHaveBeenCalled();
  });

  it('creates a company with the entered values (defaulting to trial status) and closes on success', async () => {
    mockedCreateCompany.mockResolvedValue({ ...existingCompany, id: 'c99', name: 'New Studio' });
    const { onOpenChange } = renderSheet();

    await userEvent.type(screen.getByLabelText('Company name'), 'New Studio');
    await userEvent.click(screen.getByRole('button', { name: /create company/i }));

    await waitFor(() =>
      expect(mockedCreateCompany).toHaveBeenCalledWith(
        expect.objectContaining({ name: 'New Studio', status: 'trial', currency: 'INR' }),
      ),
    );
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
  });

  it('pre-fills the form and PATCHes the existing company when editing', async () => {
    mockedUpdateCompany.mockResolvedValue({ ...existingCompany, name: 'Renamed Studio' });
    renderSheet({ company: existingCompany });

    expect(screen.getByLabelText('Company name')).toHaveValue('Old Studio');

    await userEvent.clear(screen.getByLabelText('Company name'));
    await userEvent.type(screen.getByLabelText('Company name'), 'Renamed Studio');
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() =>
      expect(mockedUpdateCompany).toHaveBeenCalledWith('c42', expect.objectContaining({ name: 'Renamed Studio' })),
    );
  });

  it('maps a 400 VALIDATION_ERROR field back onto the matching form field', async () => {
    const { ApiError } = jest.requireActual('@/lib/api/client');
    mockedCreateCompany.mockRejectedValue(
      new ApiError('VALIDATION_ERROR', 'Request validation failed.', [
        { field: 'name', issue: 'Company name cannot be blank or empty.' },
      ]),
    );
    renderSheet();

    await userEvent.type(screen.getByLabelText('Company name'), 'Duplicate Studio');
    await userEvent.click(screen.getByRole('button', { name: /create company/i }));

    expect(await screen.findByText('Company name cannot be blank or empty.')).toBeInTheDocument();
  });
});
