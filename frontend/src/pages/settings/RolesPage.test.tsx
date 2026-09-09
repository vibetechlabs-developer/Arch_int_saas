import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test-utils';
import RolesPage from '@/pages/settings/RolesPage';
import { getRoles, createRole, deleteRole, getRolePermissions, assignRolePermissions, type Role } from '@/lib/api/roles';
import { getPermissions } from '@/lib/api/permissions';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/roles');
// Only getPermissions is a real API call — groupPermissionsByModule is a
// pure client-side utility the dialog also depends on; a bare
// jest.mock('@/lib/api/permissions') would auto-mock that too (returning
// undefined), so the real implementation is kept via requireActual.
jest.mock('@/lib/api/permissions', () => ({
  ...jest.requireActual('@/lib/api/permissions'),
  getPermissions: jest.fn(),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedGetRoles = getRoles as jest.Mock;
const mockedCreateRole = createRole as jest.Mock;
const mockedDeleteRole = deleteRole as jest.Mock;
const mockedGetRolePermissions = getRolePermissions as jest.Mock;
const mockedAssignPermissions = assignRolePermissions as jest.Mock;
const mockedGetPermissions = getPermissions as jest.Mock;

const sampleRole: Role = {
  id: 'r1',
  name: 'Accountant / Finance',
  description: 'Handles invoices and payments.',
  companyId: 'c1',
  companyName: 'Studio One',
  isActive: true,
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
};

function mockList(items: Role[]) {
  mockedGetRoles.mockResolvedValue({ items, pagination: { page: 1, pageSize: 25, totalItems: items.length, totalPages: 1 } });
}

beforeEach(() => {
  jest.clearAllMocks();
  // `deleteRole` is never called (see the KNOWN ENVIRONMENT LIMITATION note
  // below) but is still exercised by other suites — mocked here for
  // isolation only.
  mockedDeleteRole.mockResolvedValue(undefined);
  mockedGetPermissions.mockResolvedValue([
    { id: 'p1', code: 'invoice.view', module: 'invoice', action: 'view', description: 'View invoices.', createdAt: '' },
    { id: 'p2', code: 'invoice.create', module: 'invoice', action: 'create', description: 'Create invoices.', createdAt: '' },
  ]);
  // A newly created role genuinely has zero grants yet — this mirrors
  // the real backend response for a role no one has assigned permissions
  // to. ManagePermissionsDialog.test.tsx covers pre-checking an existing
  // role's real (non-empty) grants in isolation.
  mockedGetRolePermissions.mockResolvedValue({ roleId: 'r2', permissionCodes: [] });
});

// KNOWN ENVIRONMENT LIMITATION (see MembersPage.test.tsx's identical note
// for full detail): a bare Radix DropdownMenu hangs indefinitely on
// userEvent.click of its trigger in this Jest/jsdom setup, confirmed via
// isolated minimal reproduction independent of any app code. This page's
// row-level "Role actions" DropdownMenu (Manage permissions/Edit/Delete)
// is therefore not exercised here — those three flows are untested via
// RolesPage pending a jsdom/Radix testing-infra fix or real browser QA.
// ManagePermissionsDialog.test.tsx covers the Manage Permissions flow's
// actual behavior in isolation instead (opened via props, not a
// DropdownMenu click — see that file for pre-check/isolation/persistence
// coverage). Every flow here that doesn't require opening that menu IS
// covered, including the full create-role → manage-permissions chain
// (Dialog + Checkbox, no Select/DropdownMenu involved, so it's
// unaffected).
describe('RolesPage', () => {
  it('renders the role list', async () => {
    mockList([sampleRole]);
    renderWithProviders(<RolesPage />);

    expect((await screen.findAllByText('Accountant / Finance')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('Handles invoices and payments.').length).toBeGreaterThan(0);
  });

  it('shows an empty state prompting role creation', async () => {
    mockList([]);
    renderWithProviders(<RolesPage />);

    expect((await screen.findAllByText('No roles yet')).length).toBeGreaterThan(0);
  });

  it('creates a role, then chains into the manage-permissions step', async () => {
    mockList([]);
    mockedCreateRole.mockResolvedValue({ ...sampleRole, id: 'r2', name: 'Site Supervisor' });
    renderWithProviders(<RolesPage />);

    await screen.findAllByText('No roles yet');
    await userEvent.click(screen.getAllByRole('button', { name: /new role/i })[0]);
    await userEvent.type(screen.getByLabelText('Role name'), 'Site Supervisor');
    await userEvent.click(screen.getByRole('button', { name: /create role/i }));

    await waitFor(() => expect(mockedCreateRole).toHaveBeenCalledWith({ name: 'Site Supervisor', description: '', isActive: true }));
    expect(await screen.findByText('Manage permissions')).toBeInTheDocument();
    // A brand-new role's real grants are genuinely empty — fetched from
    // the server, not assumed blank.
    await waitFor(() => expect(mockedGetRolePermissions).toHaveBeenCalledWith('r2'));
  });

  it('assigns selected permission codes to a newly created role', async () => {
    mockList([]);
    mockedCreateRole.mockResolvedValue({ ...sampleRole, id: 'r2', name: 'Site Supervisor' });
    mockedAssignPermissions.mockResolvedValue({ ...sampleRole, id: 'r2' });
    renderWithProviders(<RolesPage />);

    await screen.findAllByText('No roles yet');
    await userEvent.click(screen.getAllByRole('button', { name: /new role/i })[0]);
    await userEvent.type(screen.getByLabelText('Role name'), 'Site Supervisor');
    await userEvent.click(screen.getByRole('button', { name: /create role/i }));

    await screen.findByText('Manage permissions');
    // Clicks the rendered description text inside the <Label for="perm-...">
    // wrapping the checkbox — the code itself ("invoice.view") is only used
    // as the id/htmlFor pairing, never rendered as visible text.
    await userEvent.click(await screen.findByText('View invoices.'));
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => expect(mockedAssignPermissions).toHaveBeenCalledWith('r2', ['invoice.view']));
  });

  it('surfaces a 409 name-conflict from the backend verbatim', async () => {
    mockList([]);
    mockedCreateRole.mockRejectedValue(new ApiError('CONFLICT', 'A role with this name already exists for this company.', [], undefined, 409));
    renderWithProviders(<RolesPage />);

    await screen.findAllByText('No roles yet');
    await userEvent.click(screen.getAllByRole('button', { name: /new role/i })[0]);
    await userEvent.type(screen.getByLabelText('Role name'), 'Accountant / Finance');
    await userEvent.click(screen.getByRole('button', { name: /create role/i }));

    expect(await screen.findByText('A role with this name already exists for this company.')).toBeInTheDocument();
  });
});
