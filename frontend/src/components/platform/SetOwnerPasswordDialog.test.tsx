import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SetOwnerPasswordDialog } from '@/components/platform/SetOwnerPasswordDialog';
import { setCompanyOwnerPassword } from '@/lib/api/company';

jest.mock('@/lib/api/company', () => ({
  ...jest.requireActual('@/lib/api/company'),
  setCompanyOwnerPassword: jest.fn(),
}));
const mockedToastSuccess = jest.fn();
jest.mock('sonner', () => ({ toast: { success: (...args: unknown[]) => mockedToastSuccess(...args), error: jest.fn() } }));
const mockedSetCompanyOwnerPassword = setCompanyOwnerPassword as jest.Mock;

function renderDialog(onOpenChange = jest.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <SetOwnerPasswordDialog open onOpenChange={onOpenChange} companyId="c1" companyName="Zem ONE" />
    </QueryClientProvider>,
  );
  return { onOpenChange };
}

describe('SetOwnerPasswordDialog', () => {
  afterEach(() => jest.clearAllMocks());

  it('rejects a too-short password before ever calling the API', async () => {
    renderDialog();

    await userEvent.type(screen.getByLabelText('New password'), 'short');
    await userEvent.click(screen.getByRole('button', { name: /set password/i }));

    expect(await screen.findByText('Password must be at least 8 characters')).toBeInTheDocument();
    expect(mockedSetCompanyOwnerPassword).not.toHaveBeenCalled();
  });

  it('sets the password and closes with a confirmation toast on success', async () => {
    mockedSetCompanyOwnerPassword.mockResolvedValue({ email: 'owner@example.com', name: 'Owner Person' });
    const { onOpenChange } = renderDialog();

    await userEvent.type(screen.getByLabelText('New password'), 'BrandNewPassword123!');
    await userEvent.click(screen.getByRole('button', { name: /set password/i }));

    await waitFor(() =>
      expect(mockedSetCompanyOwnerPassword).toHaveBeenCalledWith('c1', 'BrandNewPassword123!'),
    );
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
    expect(mockedToastSuccess).toHaveBeenCalledWith('Password set for Owner Person (owner@example.com)');
  });

  it('shows every backend validation issue inline and keeps the dialog open', async () => {
    const { ApiError } = jest.requireActual('@/lib/api/client');
    mockedSetCompanyOwnerPassword.mockRejectedValue(
      new ApiError('VALIDATION_ERROR', 'Request validation failed.', [
        { field: '__all__', issue: 'This password is too common.' },
        { field: '__all__', issue: 'This password is entirely numeric.' },
      ]),
    );
    const { onOpenChange } = renderDialog();

    await userEvent.type(screen.getByLabelText('New password'), '12345678');
    await userEvent.click(screen.getByRole('button', { name: /set password/i }));

    expect(await screen.findByText('This password is too common.')).toBeInTheDocument();
    expect(screen.getByText('This password is entirely numeric.')).toBeInTheDocument();
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });

  it('shows a 404 "no owner" error from the backend', async () => {
    const { ApiError } = jest.requireActual('@/lib/api/client');
    mockedSetCompanyOwnerPassword.mockRejectedValue(
      new ApiError('NOT_FOUND', 'This company has no active Owner to set a password for.'),
    );
    renderDialog();

    await userEvent.type(screen.getByLabelText('New password'), 'BrandNewPassword123!');
    await userEvent.click(screen.getByRole('button', { name: /set password/i }));

    expect(await screen.findByText('This company has no active Owner to set a password for.')).toBeInTheDocument();
  });
});
