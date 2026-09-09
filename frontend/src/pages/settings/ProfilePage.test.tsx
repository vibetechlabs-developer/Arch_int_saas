import { screen } from '@testing-library/react';
import { renderWithProviders } from '@/test-utils';
import ProfilePage from '@/pages/settings/ProfilePage';

jest.mock('@/context/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 'u1',
      name: 'Dana Designer',
      email: 'dana@example.com',
      status: 'active',
      isActive: true,
      isStaff: false,
      createdAt: '2026-01-01T00:00:00Z',
      updatedAt: '2026-01-01T00:00:00Z',
    },
  }),
}));

describe('ProfilePage', () => {
  it('renders the current user\'s real profile fields, read-only', () => {
    renderWithProviders(<ProfilePage />);

    expect(screen.getByText('Dana Designer')).toBeInTheDocument();
    expect(screen.getByText('dana@example.com')).toBeInTheDocument();
    expect(screen.getByText('Company user')).toBeInTheDocument();
  });

  it('honestly discloses that editing is not available, rather than showing a fake form', () => {
    renderWithProviders(<ProfilePage />);

    expect(screen.getByText(/editing your profile isn't available yet/i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /save/i })).not.toBeInTheDocument();
  });
});
