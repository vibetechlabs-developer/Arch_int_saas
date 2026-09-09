import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test-utils';
import MembersPage from '@/pages/settings/MembersPage';
import { getCompanyMemberships, type CompanyMembership } from '@/lib/api/memberships';
import { getRoles } from '@/lib/api/roles';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/memberships');
jest.mock('@/lib/api/roles');
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('@/context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'me-1', name: 'Current User', email: 'me@example.com' } }),
}));

const mockedGetMemberships = getCompanyMemberships as jest.Mock;
const mockedGetRoles = getRoles as jest.Mock;

const activeMember: CompanyMembership = {
  id: 'm1',
  companyId: 'c1',
  companyName: 'Studio One',
  companyStatus: 'active',
  userId: 'u1',
  userEmail: 'designer@example.com',
  userName: 'Dana Designer',
  roleId: 'r1',
  roleName: 'Designer / Architect',
  status: 'active',
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
};

function mockList(items: CompanyMembership[]) {
  mockedGetMemberships.mockResolvedValue({
    items,
    pagination: { page: 1, pageSize: 25, totalItems: items.length, totalPages: 1 },
  });
}

beforeEach(() => {
  jest.clearAllMocks();
  mockedGetRoles.mockResolvedValue({
    items: [{ id: 'r1', name: 'Designer / Architect', description: '', companyId: 'c1', companyName: 'Studio One', isActive: true, createdAt: '', updatedAt: '' }],
    pagination: { page: 1, pageSize: 100, totalItems: 1, totalPages: 1 },
  });
});

// KNOWN ENVIRONMENT LIMITATION (confirmed via isolated minimal reproduction
// independent of any app code — a bare Radix DropdownMenu and a bare Radix
// Select, rendered with zero custom logic, both hang indefinitely on
// userEvent.click of their trigger in this Jest/jsdom setup, with or
// without `pointerEventsCheck: 0`). This extends the already-documented
// "6 skipped baseline" Radix+jsdom issue in this codebase (Popover/Select/
// DropdownMenu vs jsdom) to two more concrete cases. Per project convention
// (see ProductFormSheet.test.tsx), tests that would need to open one of
// these overlays to reach their assertion are not written here rather than
// left hanging or wrapped in it.skip() — every flow below that doesn't
// require opening a Select or DropdownMenu IS covered. Untested here,
// pending either a jsdom/Radix testing-infra fix or real browser QA:
// submitting the invite form (role Select), and every DropdownMenu-gated
// row action (change role, suspend, reactivate, remove, and Roles page's
// edit/delete). A plausible root cause worth investigating separately:
// package.json pins `jest@^29.7.0` against `jest-environment-jsdom@^30.5.1`
// — a major-version mismatch between the test runner and its jsdom
// environment package.
describe('MembersPage', () => {
  it('renders the member list with role and status', async () => {
    mockList([activeMember]);
    renderWithProviders(<MembersPage />);

    expect((await screen.findAllByText('Dana Designer')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('designer@example.com').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Designer / Architect').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Active').length).toBeGreaterThan(0);
  });

  it('shows an empty state with an Invite CTA when there are no members', async () => {
    mockList([]);
    renderWithProviders(<MembersPage />);

    expect((await screen.findAllByText('No team members yet')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Add your first member to start collaborating.').length).toBeGreaterThan(0);
  });

  it('shows RestrictedState on a 403 instead of the generic error state', async () => {
    mockedGetMemberships.mockRejectedValue(new ApiError('PERMISSION_ERROR', 'You do not have access to view members.', [], undefined, 403));
    renderWithProviders(<MembersPage />);

    expect(await screen.findByText('Restricted')).toBeInTheDocument();
    expect(screen.getByText('You do not have access to view members.')).toBeInTheDocument();
  });

  it('opens the invite sheet automatically when navigated with ?invite=true', async () => {
    mockList([]);
    renderWithProviders(<MembersPage />, { route: '/settings/members?invite=true' });

    expect(
      await screen.findByText('Invites an existing user into your company by email. They must already have an account.'),
    ).toBeInTheDocument();
  });

  it('opens the member detail sheet on row click', async () => {
    mockList([activeMember]);
    renderWithProviders(<MembersPage />);

    const names = await screen.findAllByText('Dana Designer');
    await userEvent.click(names[0]);

    expect(await screen.findByText('Member details')).toBeInTheDocument();
    expect(screen.getByText('Read-only membership information.')).toBeInTheDocument();
  });
});
