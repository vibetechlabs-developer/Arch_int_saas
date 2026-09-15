import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConvertLeadDialog } from '@/components/leads/ConvertLeadDialog';
import { convertLead, type Lead } from '@/lib/api/leads';

jest.mock('@/lib/api/leads', () => ({
  ...jest.requireActual('@/lib/api/leads'),
  convertLead: jest.fn(),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const mockedConvertLead = convertLead as jest.Mock;

const lead: Lead = {
  id: 'l1',
  name: 'Jane Prospect',
  companyName: '',
  email: '',
  mobile: '',
  source: '',
  status: 'new',
  assignedToId: null,
  assignedToName: null,
  lossReason: '',
  followUpReminderAt: null,
  notes: '',
  convertedClientId: null,
  convertedClientName: null,
  convertedProjectId: null,
  convertedProjectName: null,
  companyId: 'c1',
  createdAt: '',
  updatedAt: '',
};

function renderDialog(onOpenChange = jest.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <ConvertLeadDialog open onOpenChange={onOpenChange} lead={lead} />
    </QueryClientProvider>,
  );
  return { onOpenChange };
}

describe('ConvertLeadDialog', () => {
  afterEach(() => jest.clearAllMocks());

  it('converts the lead without a project by default', async () => {
    mockedConvertLead.mockResolvedValue({ ...lead, status: 'won', convertedClientId: 'cl1' });
    const { onOpenChange } = renderDialog();

    await userEvent.click(screen.getByRole('button', { name: /convert lead/i }));

    await waitFor(() =>
      expect(mockedConvertLead).toHaveBeenCalledWith('l1', { createProject: false, projectName: undefined }),
    );
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
  });

  it('reveals a project name field once "also create a project" is toggled on', async () => {
    renderDialog();

    expect(screen.queryByLabelText(/project name/i)).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole('switch'));
    expect(screen.getByLabelText(/project name/i)).toBeInTheDocument();
  });

  it('shows the backend 409 conflict message and keeps the dialog open for a lost lead', async () => {
    const { ApiError } = jest.requireActual('@/lib/api/client');
    mockedConvertLead.mockRejectedValue(new ApiError('CONFLICT', 'A lost lead cannot be converted.'));
    const { onOpenChange } = renderDialog();

    await userEvent.click(screen.getByRole('button', { name: /convert lead/i }));

    await waitFor(() => expect(mockedConvertLead).toHaveBeenCalled());
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });
});
