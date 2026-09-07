import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ClientFormSheet } from '@/components/clients/ClientFormSheet';
import { createClient, updateClient, type Client } from '@/lib/api/clients';

jest.mock('@/lib/api/clients');
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedCreateClient = createClient as jest.Mock;
const mockedUpdateClient = updateClient as jest.Mock;

const existingClient: Client = {
  id: '42',
  name: 'Old Co',
  companyName: '',
  email: '',
  mobile: '',
  gstin: '',
  addresses: [],
  notes: '',
  companyId: 'c1',
  createdAt: '',
  updatedAt: '',
};

function renderSheet(props: Partial<React.ComponentProps<typeof ClientFormSheet>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const onOpenChange = jest.fn();
  render(
    <QueryClientProvider client={queryClient}>
      <ClientFormSheet open onOpenChange={onOpenChange} {...props} />
    </QueryClientProvider>,
  );
  return { onOpenChange };
}

describe('ClientFormSheet', () => {
  afterEach(() => jest.clearAllMocks());

  it('rejects a blank name before ever calling the API', async () => {
    renderSheet();

    await userEvent.click(screen.getByRole('button', { name: /create client/i }));

    expect(await screen.findByText('Client name is required')).toBeInTheDocument();
    expect(mockedCreateClient).not.toHaveBeenCalled();
  });

  it('creates a client with the entered values and closes on success', async () => {
    mockedCreateClient.mockResolvedValue({ ...existingClient, id: '99', name: 'New Co' });
    const { onOpenChange } = renderSheet();

    await userEvent.type(screen.getByLabelText('Name'), 'New Co');
    await userEvent.type(screen.getByLabelText('Email'), 'hello@newco.com');
    await userEvent.click(screen.getByRole('button', { name: /create client/i }));

    await waitFor(() =>
      expect(mockedCreateClient).toHaveBeenCalledWith(
        expect.objectContaining({ name: 'New Co', email: 'hello@newco.com' }),
      ),
    );
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
  });

  it('pre-fills the form and PATCHes the existing client when editing', async () => {
    mockedUpdateClient.mockResolvedValue({ ...existingClient, name: 'Renamed Co' });
    renderSheet({ client: existingClient });

    expect(screen.getByLabelText('Name')).toHaveValue('Old Co');

    await userEvent.clear(screen.getByLabelText('Name'));
    await userEvent.type(screen.getByLabelText('Name'), 'Renamed Co');
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() =>
      expect(mockedUpdateClient).toHaveBeenCalledWith('42', expect.objectContaining({ name: 'Renamed Co' })),
    );
  });

  it('maps a 400 VALIDATION_ERROR field back onto the matching form field', async () => {
    const { ApiError } = jest.requireActual('@/lib/api/client');
    mockedCreateClient.mockRejectedValue(
      new ApiError('VALIDATION_ERROR', 'Request validation failed.', [
        { field: 'name', issue: 'A client with this name already exists.' },
      ]),
    );
    renderSheet();

    await userEvent.type(screen.getByLabelText('Name'), 'Duplicate Co');
    await userEvent.click(screen.getByRole('button', { name: /create client/i }));

    expect(await screen.findByText('A client with this name already exists.')).toBeInTheDocument();
  });
});
