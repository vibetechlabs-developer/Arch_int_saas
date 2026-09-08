import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BOQSectionFormDialog } from '@/components/boq/BOQSectionFormDialog';
import { createBOQSection, updateBOQSection, type BOQSection } from '@/lib/api/boq';

jest.mock('@/lib/api/boq');
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedCreate = createBOQSection as jest.Mock;
const mockedUpdate = updateBOQSection as jest.Mock;

const section: BOQSection = {
  id: 's1',
  boqId: 'boq1',
  name: 'Electrical Works',
  sortOrder: 1,
  items: [],
  createdAt: '',
  updatedAt: '',
};

function renderDialog(props: Partial<React.ComponentProps<typeof BOQSectionFormDialog>> = {}) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const onOpenChange = jest.fn();
  render(
    <QueryClientProvider client={queryClient}>
      <BOQSectionFormDialog open onOpenChange={onOpenChange} projectId="p1" {...props} />
    </QueryClientProvider>,
  );
  return { onOpenChange };
}

describe('BOQSectionFormDialog', () => {
  afterEach(() => jest.clearAllMocks());

  it('rejects a blank section name', async () => {
    renderDialog();
    await userEvent.click(screen.getByRole('button', { name: /add section/i }));

    expect(await screen.findByText('Section name is required')).toBeInTheDocument();
    expect(mockedCreate).not.toHaveBeenCalled();
  });

  it('creates a new section', async () => {
    mockedCreate.mockResolvedValue({ ...section, id: 's2', name: 'Plumbing Works' });
    const { onOpenChange } = renderDialog();

    await userEvent.type(screen.getByLabelText('Section name'), 'Plumbing Works');
    await userEvent.click(screen.getByRole('button', { name: /add section/i }));

    await waitFor(() => expect(mockedCreate).toHaveBeenCalledWith('p1', 'Plumbing Works'));
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
  });

  it('edits an existing section', async () => {
    mockedUpdate.mockResolvedValue({ ...section, name: 'Renamed Section' });
    renderDialog({ section });

    expect(screen.getByLabelText('Section name')).toHaveValue('Electrical Works');
    await userEvent.clear(screen.getByLabelText('Section name'));
    await userEvent.type(screen.getByLabelText('Section name'), 'Renamed Section');
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }));

    await waitFor(() => expect(mockedUpdate).toHaveBeenCalledWith('s1', 'Renamed Section'));
  });
});
