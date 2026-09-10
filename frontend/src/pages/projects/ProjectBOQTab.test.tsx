import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProjectBOQTab from '@/pages/projects/ProjectBOQTab';
import {
  deleteBOQItem,
  deleteBOQSection,
  getBOQ,
  getBOQSummary,
  type BOQ,
  type BOQSummary,
} from '@/lib/api/boq';
import type { Project } from '@/lib/api/projects';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/boq', () => ({
  ...jest.requireActual('@/lib/api/boq'),
  getBOQ: jest.fn(),
  getBOQSummary: jest.fn(),
  deleteBOQSection: jest.fn(),
  deleteBOQItem: jest.fn(),
}));
jest.mock('@/lib/api/products', () => ({
  ...jest.requireActual('@/lib/api/products'),
  getProducts: jest.fn().mockResolvedValue({ items: [], pagination: { page: 1, pageSize: 100, totalItems: 0, totalPages: 0 } }),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('@/lib/pdf', () => ({ previewPdf: jest.fn(), downloadPdf: jest.fn() }));

const mockedGetBOQ = getBOQ as jest.Mock;
const mockedGetSummary = getBOQSummary as jest.Mock;
const mockedDeleteSection = deleteBOQSection as jest.Mock;
const mockedDeleteItem = deleteBOQItem as jest.Mock;
const mockedPreviewPdf = jest.requireMock('@/lib/pdf').previewPdf as jest.Mock;
const mockedDownloadPdf = jest.requireMock('@/lib/pdf').downloadPdf as jest.Mock;

const project: Project = {
  id: 'p1',
  name: 'Villa Renovation',
  companyId: 'c1',
  clientId: 'cl1',
  clientName: 'Acme Interiors',
  startDate: null,
  deadline: null,
  status: 'draft',
  priority: '',
  assignedToId: null,
  assignedToName: null,
  followUpReminderAt: null,
  createdAt: '',
  updatedAt: '',
};

const boqWithData: BOQ = {
  id: 'boq1',
  projectId: 'p1',
  status: '',
  createdAt: '2026-01-01T00:00:00Z',
  updatedAt: '2026-01-02T00:00:00Z',
  sections: [
    {
      id: 's1',
      boqId: 'boq1',
      name: 'Electrical Works',
      sortOrder: 1,
      createdAt: '',
      updatedAt: '',
      items: [
        {
          id: 'i1',
          sectionId: 's1',
          productId: null,
          productName: null,
          description: 'Modular switchboard',
          quantity: '2.00',
          unit: 'nos',
          rate: '1200.00',
          discount: '0.00',
          tax: '18.00',
          amount: '2400.00',
          isOptional: false,
          isAlternative: false,
          notes: '',
          createdAt: '',
          updatedAt: '',
        },
      ],
    },
  ],
};

const emptyBOQ: BOQ = { ...boqWithData, sections: [] };

// Deliberately distinct from the item's own rate (1200.00)/amount
// (2400.00) so summary assertions can't accidentally match an item cell —
// both the desktop table and mobile cards render at once in jsdom.
const summary: BOQSummary = { subtotal: '5000.00', discount: '100.00', tax: '432.00', total: '5332.00' };

function renderTab() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/projects/p1/boq']}>
        <Routes>
          <Route path="/projects/:projectId" element={<Outlet context={{ project }} />}>
            <Route path="boq" element={<ProjectBOQTab />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ProjectBOQTab', () => {
  afterEach(() => jest.clearAllMocks());

  it('shows a structural skeleton before the BOQ loads', async () => {
    let resolveRequest: (v: BOQ) => void = () => {};
    mockedGetBOQ.mockReturnValue(new Promise((resolve) => (resolveRequest = resolve)));
    mockedGetSummary.mockResolvedValue(summary);
    renderTab();

    expect(screen.queryByText('Electrical Works')).not.toBeInTheDocument();
    resolveRequest(boqWithData);
    expect(await screen.findByText('Electrical Works')).toBeInTheDocument();
  });

  it('shows Preview/Download PDF actions that target this project\'s BOQ export', async () => {
    mockedGetBOQ.mockResolvedValue(boqWithData);
    mockedGetSummary.mockResolvedValue(summary);
    mockedPreviewPdf.mockResolvedValue(undefined);
    mockedDownloadPdf.mockResolvedValue(undefined);
    renderTab();

    await screen.findByText('Electrical Works');
    await userEvent.click(screen.getByRole('button', { name: 'Preview PDF' }));
    await waitFor(() => expect(mockedPreviewPdf).toHaveBeenCalledWith('/projects/p1/boq/pdf'));

    await userEvent.click(screen.getByRole('button', { name: 'Download PDF' }));
    await waitFor(() => expect(mockedDownloadPdf).toHaveBeenCalledWith('/projects/p1/boq/pdf'));
  });

  it('renders sections and items once loaded (success state)', async () => {
    mockedGetBOQ.mockResolvedValue(boqWithData);
    mockedGetSummary.mockResolvedValue(summary);
    renderTab();

    expect(await screen.findByText('Electrical Works')).toBeInTheDocument();
    expect(screen.getAllByText('Modular switchboard').length).toBeGreaterThan(0);
    expect(screen.getByText('1 section')).toBeInTheDocument();
    // "1 item" legitimately appears twice — the BOQ-level count and the
    // section's own item-count badge.
    expect(screen.getAllByText('1 item').length).toBeGreaterThan(0);
  });

  it('shows a "no BOQ items yet" empty state with an Add Section CTA when there are no sections', async () => {
    mockedGetBOQ.mockResolvedValue(emptyBOQ);
    mockedGetSummary.mockResolvedValue({ subtotal: '0.00', discount: '0.00', tax: '0.00', total: '0.00' });
    renderTab();

    expect(await screen.findByText('No BOQ items yet')).toBeInTheDocument();
    expect(screen.getByText('0 sections')).toBeInTheDocument();
  });

  it('shows the backend error message when the BOQ request fails', async () => {
    mockedGetBOQ.mockRejectedValue(new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.'));
    mockedGetSummary.mockResolvedValue(summary);
    renderTab();

    expect(await screen.findByText('You do not have permission to perform this action.')).toBeInTheDocument();
  });

  it('shows the backend error message for a not-found-shaped failure', async () => {
    mockedGetBOQ.mockRejectedValue(new ApiError('NOT_FOUND', 'The requested project was not found.'));
    mockedGetSummary.mockResolvedValue(summary);
    renderTab();

    expect(await screen.findByText('The requested project was not found.')).toBeInTheDocument();
  });

  it('opens the Add Section dialog from the Sections header action', async () => {
    mockedGetBOQ.mockResolvedValue(emptyBOQ);
    mockedGetSummary.mockResolvedValue(summary);
    renderTab();
    await screen.findByText('No BOQ items yet');

    await userEvent.click(screen.getAllByRole('button', { name: /add section/i })[0]);

    expect(await screen.findByText('Add a new section to this BOQ.')).toBeInTheDocument();
  });

  it('shows a confirmation dialog before deleting a section, explaining the item constraint', async () => {
    mockedGetBOQ.mockResolvedValue(boqWithData);
    mockedGetSummary.mockResolvedValue(summary);
    renderTab();
    await screen.findByText('Electrical Works');

    await userEvent.click(screen.getByRole('button', { name: 'Delete Electrical Works' }));

    expect(await screen.findByText('Delete this section?')).toBeInTheDocument();
    expect(mockedDeleteSection).not.toHaveBeenCalled();
  });

  it('deletes a section after confirmation', async () => {
    mockedGetBOQ.mockResolvedValue(boqWithData);
    mockedGetSummary.mockResolvedValue(summary);
    mockedDeleteSection.mockResolvedValue(undefined);
    renderTab();
    await screen.findByText('Electrical Works');

    await userEvent.click(screen.getByRole('button', { name: 'Delete Electrical Works' }));
    await userEvent.click(screen.getByRole('button', { name: 'Delete section' }));

    await waitFor(() => expect(mockedDeleteSection).toHaveBeenCalledWith('s1'));
  });

  it('shows a confirmation dialog before deleting an item', async () => {
    mockedGetBOQ.mockResolvedValue(boqWithData);
    mockedGetSummary.mockResolvedValue(summary);
    renderTab();
    await screen.findByText('Electrical Works');

    await userEvent.click(screen.getAllByRole('button', { name: 'Delete Modular switchboard' })[0]);

    expect(await screen.findByText('Delete this item?')).toBeInTheDocument();
  });

  it('deletes an item after confirmation and refreshes the summary', async () => {
    mockedGetBOQ.mockResolvedValue(boqWithData);
    mockedGetSummary.mockResolvedValue(summary);
    mockedDeleteItem.mockResolvedValue(undefined);
    renderTab();
    await screen.findByText('Electrical Works');
    mockedGetSummary.mockClear();

    await userEvent.click(screen.getAllByRole('button', { name: 'Delete Modular switchboard' })[0]);
    await userEvent.click(screen.getByRole('button', { name: 'Delete item' }));

    await waitFor(() => expect(mockedDeleteItem).toHaveBeenCalledWith('i1'));
    // Deleting invalidates the summary query — TanStack Query refetches it
    // automatically once invalidated (the mock resolves again).
    await waitFor(() => expect(mockedGetSummary).toHaveBeenCalled());
  });

  it('renders the BOQ summary using the exact backend decimal strings (subtotal/discount/tax/grand total)', async () => {
    mockedGetBOQ.mockResolvedValue(boqWithData);
    mockedGetSummary.mockResolvedValue(summary);
    renderTab();

    expect(await screen.findByText('Subtotal')).toBeInTheDocument();
    expect(screen.getByText('₹5,000.00')).toBeInTheDocument();
    expect(screen.getByText('₹100.00')).toBeInTheDocument();
    expect(screen.getByText('₹432.00')).toBeInTheDocument();
    expect(screen.getByText('₹5,332.00')).toBeInTheDocument();
  });

  it('shows a distinct mobile card representation for items alongside the desktop table', async () => {
    mockedGetBOQ.mockResolvedValue(boqWithData);
    mockedGetSummary.mockResolvedValue(summary);
    renderTab();
    await screen.findByText('Electrical Works');

    // jsdom applies no media queries, so both the desktop table and the
    // mobile card list render at once — assert the mobile card carries the
    // real fields (name, qty+unit, rate, amount), not the table markup.
    const mobileContainer = document.querySelector('.md\\:hidden');
    expect(mobileContainer).not.toBeNull();
    const mobileScope = within(mobileContainer as HTMLElement);
    expect(mobileScope.getByText('Modular switchboard')).toBeInTheDocument();
    expect(mobileScope.getByText('2.00 Nos')).toBeInTheDocument();
  });
});
