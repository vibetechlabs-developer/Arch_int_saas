import { render, screen, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '@/context/AuthContext';
import { fetchCurrentUser } from '@/lib/api/auth';

jest.mock('@/lib/api/auth', () => ({
  ...jest.requireActual('@/lib/api/auth'),
  fetchCurrentUser: jest.fn(),
}));
const mockedFetchCurrentUser = fetchCurrentUser as jest.Mock;

function Probe() {
  const { user, isLoading } = useAuth();
  if (isLoading) return <div>loading</div>;
  return <div>{user ? `hello ${user.name}` : 'anonymous'}</div>;
}

describe('AuthContext session bootstrap', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  it('stays anonymous and never calls the API when no access token is stored', async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByText('anonymous')).toBeInTheDocument());
    expect(mockedFetchCurrentUser).not.toHaveBeenCalled();
  });

  it('restores the session when a stored access token resolves to a real user', async () => {
    localStorage.setItem('accessToken', 'token-123');
    mockedFetchCurrentUser.mockResolvedValue({
      id: '1',
      name: 'Alice',
      email: 'alice@example.com',
      status: 'active',
      isActive: true,
      isStaff: false,
      createdAt: '',
      updatedAt: '',
    });

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByText('hello Alice')).toBeInTheDocument());
  });

  it('clears stale tokens and falls back to anonymous when the stored token no longer resolves', async () => {
    localStorage.setItem('accessToken', 'expired');
    localStorage.setItem('refreshToken', 'expired-refresh');
    mockedFetchCurrentUser.mockRejectedValue(new Error('401'));

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByText('anonymous')).toBeInTheDocument());
    expect(localStorage.getItem('accessToken')).toBeNull();
    expect(localStorage.getItem('refreshToken')).toBeNull();
  });
});
