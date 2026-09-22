import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import PlatformLoginPage from '@/pages/platform/PlatformLoginPage';
import { useAuth } from '@/context/AuthContext';
import { ApiError } from '@/lib/api/client';

jest.mock('@/context/AuthContext', () => ({ useAuth: jest.fn() }));
const mockedUseAuth = useAuth as jest.Mock;

const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

describe('PlatformLoginPage', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it('shows validation errors and never calls loginPlatformAdmin when submitted empty', async () => {
    const loginPlatformAdmin = jest.fn();
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false, isPlatformAdmin: false, loginPlatformAdmin });
    render(
      <MemoryRouter>
        <PlatformLoginPage />
      </MemoryRouter>,
    );

    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    expect(await screen.findByText('Email is required')).toBeInTheDocument();
    expect(screen.getByText('Password is required')).toBeInTheDocument();
    expect(loginPlatformAdmin).not.toHaveBeenCalled();
  });

  it('calls loginPlatformAdmin with the entered credentials and navigates to Companies on success', async () => {
    const loginPlatformAdmin = jest.fn().mockResolvedValue(undefined);
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false, isPlatformAdmin: false, loginPlatformAdmin });
    render(
      <MemoryRouter>
        <PlatformLoginPage />
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText('Email'), 'admin@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 'StrongPassword123!');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => expect(loginPlatformAdmin).toHaveBeenCalledWith('admin@example.com', 'StrongPassword123!'));
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/platform/companies', { replace: true }));
  });

  it('surfaces the backend error message when login is rejected (e.g. not a real platform admin)', async () => {
    const loginPlatformAdmin = jest
      .fn()
      .mockRejectedValue(new ApiError('AUTHENTICATION_ERROR', 'Invalid email or password.'));
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false, isPlatformAdmin: false, loginPlatformAdmin });
    render(
      <MemoryRouter>
        <PlatformLoginPage />
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText('Email'), 'not-an-admin@example.com');
    await userEvent.type(screen.getByLabelText('Password'), 'whatever');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    expect(await screen.findByText('Invalid email or password.')).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('redirects to Companies immediately if already an authenticated platform admin', () => {
    mockedUseAuth.mockReturnValue({
      user: { id: 'u1', name: 'Admin', email: 'admin@example.com' },
      isLoading: false,
      isPlatformAdmin: true,
      loginPlatformAdmin: jest.fn(),
    });
    render(
      <MemoryRouter>
        <PlatformLoginPage />
      </MemoryRouter>,
    );

    expect(screen.queryByRole('button', { name: /sign in/i })).not.toBeInTheDocument();
  });
});
