import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test-utils';
import SetPasswordPage from '@/pages/SetPasswordPage';
import { resetPassword } from '@/lib/api/auth';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/auth');
const mockedResetPassword = resetPassword as jest.Mock;

describe('SetPasswordPage', () => {
  afterEach(() => jest.clearAllMocks());

  it('shows an error state when no token is present in the URL', () => {
    renderWithProviders(<SetPasswordPage />, { route: '/reset-password' });

    expect(screen.getByText(/this link is missing its token/i)).toBeInTheDocument();
  });

  it('rejects a too-short password before calling the API', async () => {
    renderWithProviders(<SetPasswordPage />, { route: '/reset-password?token=abc123' });

    await userEvent.type(screen.getByLabelText('New password'), 'short');
    await userEvent.type(screen.getByLabelText('Confirm password'), 'short');
    await userEvent.click(screen.getByRole('button', { name: /set password/i }));

    expect(await screen.findByText('Password must be at least 8 characters')).toBeInTheDocument();
    expect(mockedResetPassword).not.toHaveBeenCalled();
  });

  it('rejects mismatched passwords before calling the API', async () => {
    renderWithProviders(<SetPasswordPage />, { route: '/reset-password?token=abc123' });

    await userEvent.type(screen.getByLabelText('New password'), 'LongEnough123!');
    await userEvent.type(screen.getByLabelText('Confirm password'), 'DoesNotMatch123!');
    await userEvent.click(screen.getByRole('button', { name: /set password/i }));

    expect(await screen.findByText("Passwords don't match")).toBeInTheDocument();
    expect(mockedResetPassword).not.toHaveBeenCalled();
  });

  it('submits the token and new password, then shows success', async () => {
    mockedResetPassword.mockResolvedValue(undefined);
    renderWithProviders(<SetPasswordPage />, { route: '/reset-password?token=real-token-123' });

    await userEvent.type(screen.getByLabelText('New password'), 'BrandNewPassword123!');
    await userEvent.type(screen.getByLabelText('Confirm password'), 'BrandNewPassword123!');
    await userEvent.click(screen.getByRole('button', { name: /set password/i }));

    await waitFor(() => expect(mockedResetPassword).toHaveBeenCalledWith('real-token-123', 'BrandNewPassword123!'));
    expect(await screen.findByText('Password set')).toBeInTheDocument();
  });

  it('surfaces the backend error message on an invalid/expired token', async () => {
    mockedResetPassword.mockRejectedValue(
      new ApiError('AUTHENTICATION_ERROR', 'Invalid or expired authentication credentials.'),
    );
    renderWithProviders(<SetPasswordPage />, { route: '/reset-password?token=expired-token' });

    await userEvent.type(screen.getByLabelText('New password'), 'BrandNewPassword123!');
    await userEvent.type(screen.getByLabelText('Confirm password'), 'BrandNewPassword123!');
    await userEvent.click(screen.getByRole('button', { name: /set password/i }));

    expect(await screen.findByText('Invalid or expired authentication credentials.')).toBeInTheDocument();
  });
});
