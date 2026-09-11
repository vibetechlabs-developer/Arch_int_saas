import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ManagePermissionsDialog } from '@/components/settings/ManagePermissionsDialog';
import { getRolePermissions, assignRolePermissions, type Role } from '@/lib/api/roles';
import { getPermissions } from '@/lib/api/permissions';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/roles', () => ({
  ...jest.requireActual('@/lib/api/roles'),
  getRolePermissions: jest.fn(),
  assignRolePermissions: jest.fn(),
}));
// Only getPermissions is a real API call — groupPermissionsByModule is a
// pure client-side utility this dialog also depends on; a bare
// jest.mock('@/lib/api/permissions') would auto-mock that too (returning
// undefined), so the real implementation is kept via requireActual.
jest.mock('@/lib/api/permissions', () => ({
  ...jest.requireActual('@/lib/api/permissions'),
  getPermissions: jest.fn(),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedGetRolePermissions = getRolePermissions as jest.Mock;
const mockedAssignPermissions = assignRolePermissions as jest.Mock;
const mockedGetPermissions = getPermissions as jest.Mock;

const roleA: Role = {
  id: 'role-a',
  name: 'Accountant / Finance',
  description: '',
  companyId: 'c1',
  companyName: 'Studio One',
  isActive: true,
  systemKey: null,
  isSystem: false,
  createdAt: '',
  updatedAt: '',
};
const roleB: Role = { ...roleA, id: 'role-b', name: 'Sales' };

const catalog = [
  { id: 'p1', code: 'invoice.view', module: 'invoice', action: 'view', description: 'View invoices.', createdAt: '' },
  { id: 'p2', code: 'invoice.create', module: 'invoice', action: 'create', description: 'Create invoices.', createdAt: '' },
];

// A dedicated, minimal provider wrapper (rather than the shared
// renderWithProviders helper) so the SAME QueryClient instance is
// available across `rerender` calls below — required to prove
// invalidate-then-refetch (save persistence, reopen reflecting server
// state) actually works against one continuous cache, not a fresh
// client per render.
function renderDialog(props: Partial<React.ComponentProps<typeof ManagePermissionsDialog>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const onOpenChange = jest.fn();
  const utils = render(
    <QueryClientProvider client={queryClient}>
      <ManagePermissionsDialog open role={roleA} onOpenChange={onOpenChange} {...props} />
    </QueryClientProvider>,
  );
  return {
    ...utils,
    onOpenChange,
    rerenderWith: (nextProps: Partial<React.ComponentProps<typeof ManagePermissionsDialog>>) =>
      utils.rerender(
        <QueryClientProvider client={queryClient}>
          <ManagePermissionsDialog open role={roleA} onOpenChange={onOpenChange} {...props} {...nextProps} />
        </QueryClientProvider>,
      ),
  };
}

beforeEach(() => {
  jest.clearAllMocks();
  mockedGetPermissions.mockResolvedValue(catalog);
});

describe('ManagePermissionsDialog', () => {
  it('fetches and displays the permission catalog grouped by module', async () => {
    mockedGetRolePermissions.mockResolvedValue({ roleId: 'role-a', permissionCodes: [] });
    renderDialog();

    expect(await screen.findByText('invoice')).toBeInTheDocument();
    expect(screen.getByText('View invoices.')).toBeInTheDocument();
    expect(screen.getByText('Create invoices.')).toBeInTheDocument();
  });

  it('pre-checks exactly the permissions this role currently holds', async () => {
    mockedGetRolePermissions.mockResolvedValue({ roleId: 'role-a', permissionCodes: ['invoice.view'] });
    renderDialog();

    await screen.findByText('invoice');
    expect(screen.getByRole('checkbox', { name: /view/i })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: /create/i })).not.toBeChecked();
  });

  it('shows a genuinely empty role (no grants) as fully unchecked, not loading forever', async () => {
    mockedGetRolePermissions.mockResolvedValue({ roleId: 'role-a', permissionCodes: [] });
    renderDialog();

    await screen.findByText('invoice');
    expect(screen.getByRole('checkbox', { name: /view/i })).not.toBeChecked();
    expect(screen.getByText('No permissions granted.')).toBeInTheDocument();
  });

  it('does not leak Role A\'s selections into Role B\'s editor', async () => {
    mockedGetRolePermissions.mockImplementation((roleId: string) =>
      Promise.resolve(
        roleId === 'role-a'
          ? { roleId: 'role-a', permissionCodes: ['invoice.view'] }
          : { roleId: 'role-b', permissionCodes: ['invoice.create'] },
      ),
    );
    const { rerenderWith } = renderDialog({ role: roleA });

    await screen.findByText('invoice');
    expect(screen.getByRole('checkbox', { name: /view/i })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: /create/i })).not.toBeChecked();

    rerenderWith({ role: roleB });

    await waitFor(() => expect(screen.getByRole('checkbox', { name: /create/i })).toBeChecked());
    expect(screen.getByRole('checkbox', { name: /view/i })).not.toBeChecked();
  });

  it('submits the complete edited set (existing grant kept + new one added), not just the delta', async () => {
    mockedGetRolePermissions.mockResolvedValue({ roleId: 'role-a', permissionCodes: ['invoice.view'] });
    mockedAssignPermissions.mockResolvedValue({ ...roleA });
    renderDialog();

    await screen.findByText('invoice');
    await userEvent.click(screen.getByText('Create invoices.'));
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() =>
      expect(mockedAssignPermissions).toHaveBeenCalledWith(
        'role-a',
        expect.arrayContaining(['invoice.view', 'invoice.create']),
      ),
    );
    expect(mockedAssignPermissions.mock.calls[0][1]).toHaveLength(2);
  });

  it('reflects the newly persisted state on reopen, not stale local state', async () => {
    mockedGetRolePermissions.mockResolvedValueOnce({ roleId: 'role-a', permissionCodes: ['invoice.view'] });
    mockedAssignPermissions.mockResolvedValue({ ...roleA });
    const { rerenderWith } = renderDialog();

    await screen.findByText('invoice');
    await userEvent.click(screen.getByText('Create invoices.'));

    // The server now genuinely holds both codes — simulate that for the
    // next fetch, matching what invalidateQueries + refetch would surface.
    mockedGetRolePermissions.mockResolvedValueOnce({
      roleId: 'role-a',
      permissionCodes: ['invoice.view', 'invoice.create'],
    });
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));
    await waitFor(() => expect(mockedAssignPermissions).toHaveBeenCalled());

    // Close, then reopen — the dialog must show real server truth, not
    // whatever local checkbox state happened to be left over.
    rerenderWith({ open: false });
    rerenderWith({ open: true });

    await waitFor(() => expect(screen.getByRole('checkbox', { name: /create/i })).toBeChecked());
    expect(screen.getByRole('checkbox', { name: /view/i })).toBeChecked();
  });

  it('shows RestrictedState on a 403 fetching current grants', async () => {
    mockedGetRolePermissions.mockRejectedValue(
      new ApiError('PERMISSION_ERROR', 'You cannot view this role\'s permissions.', [], undefined, 403),
    );
    renderDialog();

    expect(await screen.findByText('Restricted')).toBeInTheDocument();
  });

  it('shows an error state (not a blank empty list) on a failed grants fetch', async () => {
    mockedGetRolePermissions.mockRejectedValue(new ApiError('NOT_FOUND', 'The requested role was not found.', [], undefined, 404));
    renderDialog();

    expect(await screen.findByText("Couldn't load this page")).toBeInTheDocument();
    expect(screen.queryByText('invoice')).not.toBeInTheDocument();
  });

  it('disables Save while the mutation is pending, preventing duplicate submission', async () => {
    mockedGetRolePermissions.mockResolvedValue({ roleId: 'role-a', permissionCodes: [] });
    let resolveAssign: (v: unknown) => void = () => {};
    mockedAssignPermissions.mockReturnValue(new Promise((resolve) => (resolveAssign = resolve)));
    renderDialog();

    await screen.findByText('invoice');
    const saveButton = screen.getByRole('button', { name: /save changes/i });
    await userEvent.click(saveButton);

    expect(saveButton).toBeDisabled();
    expect(mockedAssignPermissions).toHaveBeenCalledTimes(1);
    await userEvent.click(saveButton);
    expect(mockedAssignPermissions).toHaveBeenCalledTimes(1);

    resolveAssign({ ...roleA });
  });
});
