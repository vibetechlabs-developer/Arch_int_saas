import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '@/test-utils';
import CompanySettingsPage from '@/pages/settings/CompanySettingsPage';
import { getCompany, updateCompany, type Company } from '@/lib/api/company';
import { fetchMyMemberships } from '@/lib/api/auth';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/company');
jest.mock('@/lib/api/auth');
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedGetCompany = getCompany as jest.Mock;
const mockedUpdateCompany = updateCompany as jest.Mock;
const mockedFetchMemberships = fetchMyMemberships as jest.Mock;

const company: Company = {
  id: 'c1',
  name: 'Studio One',
  status: 'active',
  currency: 'INR',
  gstNumber: '22AAAAA0000A1Z5',
  settings: {},
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-01T00:00:00Z',
};

beforeEach(() => {
  jest.clearAllMocks();
  mockedFetchMemberships.mockResolvedValue([{ companyId: 'c1', companyName: 'Studio One', status: 'active', roleName: 'Owner' }]);
});

describe('CompanySettingsPage', () => {
  it('loads and displays the resolved company\'s details', async () => {
    mockedGetCompany.mockResolvedValue(company);
    renderWithProviders(<CompanySettingsPage />);

    expect(await screen.findByDisplayValue('Studio One')).toBeInTheDocument();
    expect(screen.getByDisplayValue('INR')).toBeInTheDocument();
    expect(screen.getByDisplayValue('22AAAAA0000A1Z5')).toBeInTheDocument();
    expect(screen.getByText('active')).toBeInTheDocument();
  });

  it('disables Save until a field is actually changed', async () => {
    mockedGetCompany.mockResolvedValue(company);
    renderWithProviders(<CompanySettingsPage />);

    await screen.findByDisplayValue('Studio One');
    expect(screen.getByRole('button', { name: /save changes/i })).toBeDisabled();
  });

  it('saves an edited company name', async () => {
    mockedGetCompany.mockResolvedValue(company);
    mockedUpdateCompany.mockResolvedValue({ ...company, name: 'Studio One Interiors' });
    renderWithProviders(<CompanySettingsPage />);

    await screen.findByDisplayValue('Studio One');
    await userEvent.clear(screen.getByLabelText('Company name'));
    await userEvent.type(screen.getByLabelText('Company name'), 'Studio One Interiors');
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() =>
      expect(mockedUpdateCompany).toHaveBeenCalledWith('c1', {
        name: 'Studio One Interiors',
        currency: 'INR',
        gstNumber: '22AAAAA0000A1Z5',
      }),
    );
  });

  it('rejects a blank company name before calling the API', async () => {
    mockedGetCompany.mockResolvedValue(company);
    renderWithProviders(<CompanySettingsPage />);

    await screen.findByDisplayValue('Studio One');
    await userEvent.clear(screen.getByLabelText('Company name'));
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    expect(await screen.findByText('Company name is required')).toBeInTheDocument();
    expect(mockedUpdateCompany).not.toHaveBeenCalled();
  });

  it('shows RestrictedState on a 403 loading the company', async () => {
    mockedGetCompany.mockRejectedValue(new ApiError('PERMISSION_ERROR', 'You cannot view company settings.', [], undefined, 403));
    renderWithProviders(<CompanySettingsPage />);

    expect(await screen.findByText('Restricted')).toBeInTheDocument();
  });
});
