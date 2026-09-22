import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { ProtectedPlatformRoute } from '@/components/ProtectedPlatformRoute';
import { useAuth } from '@/context/AuthContext';

jest.mock('@/context/AuthContext', () => ({ useAuth: jest.fn() }));
const mockedUseAuth = useAuth as jest.Mock;

function renderProtected() {
  return render(
    <MemoryRouter initialEntries={['/platform/companies']}>
      <Routes>
        <Route path="/platform/login" element={<div>Platform Login Page</div>} />
        <Route
          path="/platform/companies"
          element={
            <ProtectedPlatformRoute>
              <div>Secret Companies List</div>
            </ProtectedPlatformRoute>
          }
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('ProtectedPlatformRoute', () => {
  it('shows a loading state and renders neither screen while auth is resolving', () => {
    mockedUseAuth.mockReturnValue({ user: null, isLoading: true, isPlatformAdmin: false });
    renderProtected();
    expect(screen.queryByText('Secret Companies List')).not.toBeInTheDocument();
    expect(screen.queryByText('Platform Login Page')).not.toBeInTheDocument();
  });

  it('redirects to /platform/login when there is no authenticated user', () => {
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false, isPlatformAdmin: false });
    renderProtected();
    expect(screen.getByText('Platform Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Secret Companies List')).not.toBeInTheDocument();
  });

  it('redirects to /platform/login for an authenticated company user who is NOT a platform admin', () => {
    mockedUseAuth.mockReturnValue({ user: { id: '1', name: 'Alice' }, isLoading: false, isPlatformAdmin: false });
    renderProtected();
    expect(screen.getByText('Platform Login Page')).toBeInTheDocument();
    expect(screen.queryByText('Secret Companies List')).not.toBeInTheDocument();
  });

  it('renders the protected content for an authenticated platform admin', () => {
    mockedUseAuth.mockReturnValue({ user: { id: '1', name: 'Admin' }, isLoading: false, isPlatformAdmin: true });
    renderProtected();
    expect(screen.getByText('Secret Companies List')).toBeInTheDocument();
  });
});
