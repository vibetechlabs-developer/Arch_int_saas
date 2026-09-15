import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LeadFormSheet } from '@/components/leads/LeadFormSheet';
import { createLead, updateLead, type Lead } from '@/lib/api/leads';

jest.mock('@/lib/api/leads');
jest.mock('@/lib/api/memberships', () => ({ searchActiveCompanyMembers: jest.fn().mockResolvedValue([]) }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedCreateLead = createLead as jest.Mock;
const mockedUpdateLead = updateLead as jest.Mock;

const existingLead: Lead = {
  id: '42',
  name: 'Old Prospect',
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

function renderSheet(props: Partial<React.ComponentProps<typeof LeadFormSheet>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const onOpenChange = jest.fn();
  render(
    <QueryClientProvider client={queryClient}>
      <LeadFormSheet open onOpenChange={onOpenChange} {...props} />
    </QueryClientProvider>,
  );
  return { onOpenChange };
}

describe('LeadFormSheet', () => {
  afterEach(() => jest.clearAllMocks());

  it('rejects a blank name before ever calling the API', async () => {
    renderSheet();

    await userEvent.click(screen.getByRole('button', { name: /create lead/i }));

    expect(await screen.findByText('Lead name is required')).toBeInTheDocument();
    expect(mockedCreateLead).not.toHaveBeenCalled();
  });

  it('creates a lead with the entered values and closes on success', async () => {
    mockedCreateLead.mockResolvedValue({ ...existingLead, id: '99', name: 'New Prospect' });
    const { onOpenChange } = renderSheet();

    await userEvent.type(screen.getByLabelText('Name'), 'New Prospect');
    await userEvent.type(screen.getByLabelText('Email'), 'hello@newprospect.com');
    await userEvent.click(screen.getByRole('button', { name: /create lead/i }));

    await waitFor(() =>
      expect(mockedCreateLead).toHaveBeenCalledWith(
        expect.objectContaining({ name: 'New Prospect', email: 'hello@newprospect.com' }),
      ),
    );
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
  });

  it('pre-fills the form and PATCHes the existing lead when editing', async () => {
    mockedUpdateLead.mockResolvedValue({ ...existingLead, name: 'Renamed Prospect' });
    renderSheet({ lead: existingLead });

    expect(screen.getByLabelText('Name')).toHaveValue('Old Prospect');

    await userEvent.clear(screen.getByLabelText('Name'));
    await userEvent.type(screen.getByLabelText('Name'), 'Renamed Prospect');
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() =>
      expect(mockedUpdateLead).toHaveBeenCalledWith('42', expect.objectContaining({ name: 'Renamed Prospect' })),
    );
  });

  it('maps a 400 VALIDATION_ERROR field back onto the matching form field', async () => {
    const { ApiError } = jest.requireActual('@/lib/api/client');
    mockedCreateLead.mockRejectedValue(
      new ApiError('VALIDATION_ERROR', 'Request validation failed.', [
        { field: 'name', issue: 'Lead name cannot be blank or empty.' },
      ]),
    );
    renderSheet();

    await userEvent.type(screen.getByLabelText('Name'), 'Duplicate Prospect');
    await userEvent.click(screen.getByRole('button', { name: /create lead/i }));

    expect(await screen.findByText('Lead name cannot be blank or empty.')).toBeInTheDocument();
  });
});
