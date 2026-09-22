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
const mockedToastSuccess = jest.fn();
jest.mock('sonner', () => ({ toast: { success: (...args: unknown[]) => mockedToastSuccess(...args), error: jest.fn() } }));

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

async function fillOwnerFields(name = 'New Owner', email = 'new-owner@example.com') {
  await userEvent.type(screen.getByLabelText('Owner name'), name);
  await userEvent.type(screen.getByLabelText('Owner email'), email);
}

describe('CompanyFormSheet', () => {
  afterEach(() => jest.clearAllMocks());

  it('rejects a blank name before ever calling the API', async () => {
    renderSheet();

    await userEvent.click(screen.getByRole('button', { name: /create company/i }));

    expect(await screen.findByText('Company name is required')).toBeInTheDocument();
    expect(mockedCreateCompany).not.toHaveBeenCalled();
  });

  it('requires an owner name and email in create mode before ever calling the API', async () => {
    renderSheet();

    await userEvent.type(screen.getByLabelText('Company name'), 'New Studio');
    await userEvent.click(screen.getByRole('button', { name: /create company/i }));

    expect(await screen.findByText(/enter the new owner/i)).toBeInTheDocument();
    expect(mockedCreateCompany).not.toHaveBeenCalled();
  });

  it('does not show owner fields at all when editing', () => {
    renderSheet({ company: existingCompany });
    expect(screen.queryByLabelText('Owner name')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Owner email')).not.toBeInTheDocument();
  });

  it('creates a company with the entered values plus its first owner, and closes on success', async () => {
    mockedCreateCompany.mockResolvedValue({
      ...existingCompany,
      id: 'c99',
      name: 'New Studio',
      owner: { userCreated: true, activationRequired: true },
    });
    const { onOpenChange } = renderSheet();

    await userEvent.type(screen.getByLabelText('Company name'), 'New Studio');
    await fillOwnerFields();
    await userEvent.click(screen.getByRole('button', { name: /create company/i }));

    await waitFor(() =>
      expect(mockedCreateCompany).toHaveBeenCalledWith(
        expect.objectContaining({
          name: 'New Studio',
          status: 'trial',
          currency: 'INR',
          ownerEmail: 'new-owner@example.com',
          ownerName: 'New Owner',
        }),
      ),
    );
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
    expect(mockedToastSuccess).toHaveBeenCalledWith(expect.stringMatching(/account-setup email was sent/i));
  });

  it('shows a different success message when the owner email already had an account', async () => {
    mockedCreateCompany.mockResolvedValue({
      ...existingCompany,
      owner: { userCreated: false, activationRequired: false },
    });
    renderSheet();

    await userEvent.type(screen.getByLabelText('Company name'), 'New Studio');
    await fillOwnerFields('Existing Person', 'existing@example.com');
    await userEvent.click(screen.getByRole('button', { name: /create company/i }));

    await waitFor(() =>
      expect(mockedToastSuccess).toHaveBeenCalledWith(expect.stringMatching(/existing account was granted/i)),
    );
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
    await fillOwnerFields();
    await userEvent.click(screen.getByRole('button', { name: /create company/i }));

    expect(await screen.findByText('Company name cannot be blank or empty.')).toBeInTheDocument();
  });

  it('maps a 400 VALIDATION_ERROR on ownerEmail onto the owner section, not a form field', async () => {
    const { ApiError } = jest.requireActual('@/lib/api/client');
    mockedCreateCompany.mockRejectedValue(
      new ApiError('VALIDATION_ERROR', 'Request validation failed.', [
        { field: 'ownerEmail', issue: 'This email already has an unresolvable conflict.' },
      ]),
    );
    renderSheet();

    await userEvent.type(screen.getByLabelText('Company name'), 'New Studio');
    await fillOwnerFields();
    await userEvent.click(screen.getByRole('button', { name: /create company/i }));

    expect(await screen.findByText('This email already has an unresolvable conflict.')).toBeInTheDocument();
  });
});
