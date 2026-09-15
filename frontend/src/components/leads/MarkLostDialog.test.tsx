import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MarkLostDialog } from '@/components/leads/MarkLostDialog';
import { markLeadLost, type Lead } from '@/lib/api/leads';

jest.mock('@/lib/api/leads', () => ({
  ...jest.requireActual('@/lib/api/leads'),
  markLeadLost: jest.fn(),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const mockedMarkLeadLost = markLeadLost as jest.Mock;

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
      <MarkLostDialog open onOpenChange={onOpenChange} lead={lead} />
    </QueryClientProvider>,
  );
  return { onOpenChange };
}

describe('MarkLostDialog', () => {
  afterEach(() => jest.clearAllMocks());

  it('rejects a blank loss reason before ever calling the API', async () => {
    renderDialog();

    await userEvent.click(screen.getByRole('button', { name: /mark as lost/i }));

    expect(await screen.findByText('A loss reason is required')).toBeInTheDocument();
    expect(mockedMarkLeadLost).not.toHaveBeenCalled();
  });

  it('marks the lead lost with the entered reason and closes on success', async () => {
    mockedMarkLeadLost.mockResolvedValue({ ...lead, status: 'lost', lossReason: 'Chose a competitor' });
    const { onOpenChange } = renderDialog();

    await userEvent.type(screen.getByLabelText('Loss reason'), 'Chose a competitor');
    await userEvent.click(screen.getByRole('button', { name: /mark as lost/i }));

    await waitFor(() =>
      expect(mockedMarkLeadLost).toHaveBeenCalledWith(
        'l1',
        expect.objectContaining({ lossReason: 'Chose a competitor' }),
      ),
    );
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
  });

  it('shows the backend 409 conflict message inline and keeps the dialog open', async () => {
    const { ApiError } = jest.requireActual('@/lib/api/client');
    mockedMarkLeadLost.mockRejectedValue(new ApiError('CONFLICT', "Cannot mark a 'lost' lead as lost."));
    const { onOpenChange } = renderDialog();

    await userEvent.type(screen.getByLabelText('Loss reason'), 'Second reason');
    await userEvent.click(screen.getByRole('button', { name: /mark as lost/i }));

    await waitFor(() => expect(mockedMarkLeadLost).toHaveBeenCalled());
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });
});
