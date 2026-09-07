import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { useAuth } from '@/context/AuthContext';

jest.mock('@/context/AuthContext', () => ({ useAuth: jest.fn() }));
const mockedUseAuth = useAuth as jest.Mock;

function renderProtected() {
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <div>Secret Dashboard</div>
            </ProtectedRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ProtectedRoute', () => {
  it('shows a loading state and renders neither the login page nor the protected content while auth is resolving', () => {
    mockedUseAuth.mockReturnValue({ user: null, isLoading: true });
    renderProtected();
    expect(screen.queryByText('Secret Dashboard')).not.toBeInTheDocument();
    expect(screen.queryByText('Login Page')).not.toBeInTheDocument();
  });

  it('redirects to /login when there is no authenticated user', () => {
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false });
    renderProtected();
    expect(screen.getByText('Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Secret Dashboard')).not.toBeInTheDocument();
  });

  it('renders the protected content once a user is present', () => {
    mockedUseAuth.mockReturnValue({ user: { id: '1', name: 'Alice' }, isLoading: false });
    renderProtected();
    expect(screen.getByText('Secret Dashboard')).toBeInTheDocument();
  });
});
