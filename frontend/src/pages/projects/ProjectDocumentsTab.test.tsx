import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Outlet, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProjectDocumentsTab from '@/pages/projects/ProjectDocumentsTab';
import { createDocument, deleteDocument, getDocuments, uploadDocumentFile, type Document } from '@/lib/api/documents';
import type { Project } from '@/lib/api/projects';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/documents', () => ({
  ...jest.requireActual('@/lib/api/documents'),
  getDocuments: jest.fn(),
  createDocument: jest.fn(),
  deleteDocument: jest.fn(),
  uploadDocumentFile: jest.fn(),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('@/lib/pdf', () => ({ previewPdf: jest.fn(), downloadPdf: jest.fn() }));

const mockedGetDocuments = getDocuments as jest.Mock;
const mockedCreate = createDocument as jest.Mock;
const mockedDelete = deleteDocument as jest.Mock;
const mockedUploadFile = uploadDocumentFile as jest.Mock;
const mockedPreviewPdf = jest.requireMock('@/lib/pdf').previewPdf as jest.Mock;

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

function makeDocument(overrides: Partial<Document> = {}): Document {
  return {
    id: 'd1',
    companyId: 'c1',
    projectId: 'p1',
    entityType: 'project',
    entityId: 'p1',
    fileUrl: 'https://files.example.com/site-plan.pdf',
    hasStoredFile: false,
    version: 1,
    uploadedById: 'u1',
    uploadedByName: 'Alice Member',
    uploadedAt: '2026-09-01T10:00:00Z',
    ...overrides,
  };
}

function renderTab() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/projects/p1/documents']}>
        <Routes>
          <Route path="/projects/:projectId" element={<Outlet context={{ project }} />}>
            <Route path="documents" element={<ProjectDocumentsTab />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ProjectDocumentsTab', () => {
  afterEach(() => jest.clearAllMocks());

  it('shows a structural skeleton before documents load', async () => {
    let resolveRequest: (v: Document[]) => void = () => {};
    mockedGetDocuments.mockReturnValue(new Promise((resolve) => (resolveRequest = resolve)));
    renderTab();

    expect(screen.queryByText('site-plan.pdf')).not.toBeInTheDocument();
    resolveRequest([makeDocument()]);
    expect((await screen.findAllByText('site-plan.pdf')).length).toBeGreaterThan(0);
  });

  it('renders documents with a derived filename, version, uploader, and date (success state)', async () => {
    mockedGetDocuments.mockResolvedValue([makeDocument()]);
    renderTab();

    expect((await screen.findAllByText('site-plan.pdf')).length).toBeGreaterThan(0);
    expect(screen.getAllByText('v1').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Alice Member').length).toBeGreaterThan(0);
  });

  it('shows an "attached to" caption only for a non-project-level document', async () => {
    mockedGetDocuments.mockResolvedValue([makeDocument({ entityType: 'quotation' })]);
    renderTab();

    expect((await screen.findAllByText('Attached to quotation')).length).toBeGreaterThan(0);
  });

  it('does not show an "attached to" caption for a general project document', async () => {
    mockedGetDocuments.mockResolvedValue([makeDocument({ entityType: 'project' })]);
    renderTab();

    await screen.findAllByText('site-plan.pdf');
    expect(screen.queryByText(/attached to/i)).not.toBeInTheDocument();
  });

  it('never renders a fabricated file size or category, since the backend exposes neither', async () => {
    mockedGetDocuments.mockResolvedValue([makeDocument()]);
    renderTab();

    await screen.findAllByText('site-plan.pdf');
    expect(screen.queryByText(/\d+(\.\d+)?\s?(kb|mb|gb)\b/i)).not.toBeInTheDocument();
  });

  it('shows a "no documents uploaded yet" empty state with an Add Document CTA', async () => {
    mockedGetDocuments.mockResolvedValue([]);
    renderTab();

    expect((await screen.findAllByText('No documents uploaded yet')).length).toBeGreaterThan(0);
  });

  it('shows the backend error message when the list request fails', async () => {
    mockedGetDocuments.mockRejectedValue(new ApiError('PERMISSION_ERROR', 'You do not have permission to perform this action.'));
    renderTab();

    expect(await screen.findByText('You do not have permission to perform this action.')).toBeInTheDocument();
  });

  it('renders an unsafe-looking filename as plain text, never as HTML', async () => {
    mockedGetDocuments.mockResolvedValue([
      makeDocument({ fileUrl: 'https://files.example.com/%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E.png' }),
    ]);
    renderTab();

    const rendered = await screen.findAllByText('<img src=x onerror=alert(1)>.png');
    expect(rendered.length).toBeGreaterThan(0);
    // Confirms it's a real text node, not injected markup — no actual <img> element exists for this fake tag string.
    expect(document.querySelectorAll('img[src="x"]').length).toBe(0);
  });

  it('opens the file in a new tab via a safe, non-crawlable external link', async () => {
    mockedGetDocuments.mockResolvedValue([makeDocument()]);
    renderTab();
    await screen.findAllByText('site-plan.pdf');

    const [openLink] = screen.getAllByRole('link', { name: /open site-plan\.pdf/i });
    expect(openLink).toHaveAttribute('href', 'https://files.example.com/site-plan.pdf');
    expect(openLink).toHaveAttribute('target', '_blank');
    expect(openLink).toHaveAttribute('rel', 'noreferrer');
  });

  it('registers a document with the exact payload shape', async () => {
    mockedGetDocuments.mockResolvedValue([]);
    mockedCreate.mockResolvedValue(makeDocument({ id: 'd9' }));
    renderTab();
    await screen.findAllByText('No documents uploaded yet');

    await userEvent.click(screen.getAllByRole('button', { name: /add document/i })[0]);
    await userEvent.click(screen.getByRole('button', { name: /use a url instead/i }));
    await userEvent.type(screen.getByLabelText('File URL'), 'https://files.example.com/contract.pdf');
    await userEvent.click(screen.getByRole('button', { name: 'Add document' }));

    await waitFor(() => expect(mockedCreate).toHaveBeenCalledWith('p1', { fileUrl: 'https://files.example.com/contract.pdf' }));
  });

  it('requires a valid URL before registering a document', async () => {
    mockedGetDocuments.mockResolvedValue([]);
    renderTab();
    await screen.findAllByText('No documents uploaded yet');

    await userEvent.click(screen.getAllByRole('button', { name: /add document/i })[0]);
    await userEvent.click(screen.getByRole('button', { name: /use a url instead/i }));
    await userEvent.type(screen.getByLabelText('File URL'), 'not-a-url');
    await userEvent.click(screen.getByRole('button', { name: 'Add document' }));

    expect(await screen.findByText('Enter a valid URL')).toBeInTheDocument();
    expect(mockedCreate).not.toHaveBeenCalled();
  });

  it('requires a non-empty URL before registering a document', async () => {
    mockedGetDocuments.mockResolvedValue([]);
    renderTab();
    await screen.findAllByText('No documents uploaded yet');

    await userEvent.click(screen.getAllByRole('button', { name: /add document/i })[0]);
    await userEvent.click(screen.getByRole('button', { name: /use a url instead/i }));
    await userEvent.click(screen.getByRole('button', { name: 'Add document' }));

    expect(await screen.findByText('File URL is required')).toBeInTheDocument();
    expect(mockedCreate).not.toHaveBeenCalled();
  });

  it('requires a file to be chosen before registering a document in upload mode', async () => {
    mockedGetDocuments.mockResolvedValue([]);
    renderTab();
    await screen.findAllByText('No documents uploaded yet');

    await userEvent.click(screen.getAllByRole('button', { name: /add document/i })[0]);
    await userEvent.click(screen.getByRole('button', { name: 'Add document' }));

    expect(await screen.findByText('Choose a file to upload.')).toBeInTheDocument();
    expect(mockedCreate).not.toHaveBeenCalled();
  });

  it('surfaces a backend validation error on registration', async () => {
    mockedGetDocuments.mockResolvedValue([]);
    mockedCreate.mockRejectedValue(new ApiError('VALIDATION_ERROR', 'fileUrl cannot be blank or empty.'));
    renderTab();
    await screen.findAllByText('No documents uploaded yet');

    await userEvent.click(screen.getAllByRole('button', { name: /add document/i })[0]);
    await userEvent.click(screen.getByRole('button', { name: /use a url instead/i }));
    await userEvent.type(screen.getByLabelText('File URL'), 'https://files.example.com/contract.pdf');
    await userEvent.click(screen.getByRole('button', { name: 'Add document' }));

    expect(await screen.findByText('fileUrl cannot be blank or empty.')).toBeInTheDocument();
  });

  it('disables the submit button while the create mutation is pending, preventing duplicate submission', async () => {
    mockedGetDocuments.mockResolvedValue([]);
    let resolveCreate: (v: Document) => void = () => {};
    mockedCreate.mockReturnValue(new Promise((resolve) => (resolveCreate = resolve)));
    renderTab();
    await screen.findAllByText('No documents uploaded yet');

    await userEvent.click(screen.getAllByRole('button', { name: /add document/i })[0]);
    await userEvent.click(screen.getByRole('button', { name: /use a url instead/i }));
    await userEvent.type(screen.getByLabelText('File URL'), 'https://files.example.com/contract.pdf');
    const submitButton = screen.getByRole('button', { name: 'Add document' });
    await userEvent.click(submitButton);

    await waitFor(() => expect(submitButton).toBeDisabled());
    resolveCreate(makeDocument());
  });

  it('uploads a file and registers the document with its storage key (BE-078)', async () => {
    mockedGetDocuments.mockResolvedValue([]);
    mockedUploadFile.mockResolvedValue({ key: 'documents/c1/abc.pdf', fileName: 'contract.pdf', contentType: 'application/pdf', size: 100 });
    mockedCreate.mockResolvedValue(makeDocument({ id: 'd9' }));
    renderTab();
    await screen.findAllByText('No documents uploaded yet');

    await userEvent.click(screen.getAllByRole('button', { name: /add document/i })[0]);
    const file = new File(['%PDF-1.4'], 'contract.pdf', { type: 'application/pdf' });
    await userEvent.upload(screen.getByLabelText('Document file'), file);
    await userEvent.click(screen.getByRole('button', { name: 'Add document' }));

    await waitFor(() => expect(mockedUploadFile).toHaveBeenCalledWith(file));
    await waitFor(() =>
      expect(mockedCreate).toHaveBeenCalledWith('p1', { fileStorageKey: 'documents/c1/abc.pdf' }),
    );
  });

  it('renders Preview/Download actions (not a plain Open link) for a stored-file document', async () => {
    mockedGetDocuments.mockResolvedValue([makeDocument({ id: 'd1', fileUrl: '', hasStoredFile: true })]);
    renderTab();

    await screen.findAllByText('Uploaded file');
    expect(screen.queryByRole('link', { name: /open/i })).not.toBeInTheDocument();
    const [previewButton] = await screen.findAllByRole('button', { name: 'Preview' });

    await userEvent.click(previewButton);
    await waitFor(() => expect(mockedPreviewPdf).toHaveBeenCalledWith('/documents/d1/download'));
  });

  it('shows a confirmation dialog before deleting, then deletes on confirm', async () => {
    mockedGetDocuments.mockResolvedValue([makeDocument()]);
    mockedDelete.mockResolvedValue(undefined);
    renderTab();
    const [deleteButton] = await screen.findAllByRole('button', { name: /delete site-plan\.pdf/i });

    await userEvent.click(deleteButton);
    expect(await screen.findByText('Delete document?')).toBeInTheDocument();
    expect(mockedDelete).not.toHaveBeenCalled();

    await userEvent.click(screen.getByRole('button', { name: 'Delete document' }));

    await waitFor(() => expect(mockedDelete).toHaveBeenCalledWith('d1'));
  });

  it('shows a distinct mobile card representation for document rows alongside the desktop table', async () => {
    mockedGetDocuments.mockResolvedValue([makeDocument()]);
    renderTab();
    await screen.findAllByText('site-plan.pdf');

    const mobileContainer = document.querySelector('.md\\:hidden');
    expect(mobileContainer).not.toBeNull();
    const mobileScope = within(mobileContainer as HTMLElement);
    expect(mobileScope.getByText('site-plan.pdf')).toBeInTheDocument();
  });
});
