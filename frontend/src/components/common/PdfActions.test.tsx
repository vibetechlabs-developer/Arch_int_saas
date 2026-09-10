import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PdfActions } from '@/components/common/PdfActions';
import { previewPdf, downloadPdf } from '@/lib/pdf';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/pdf', () => ({
  previewPdf: jest.fn(),
  downloadPdf: jest.fn(),
}));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const mockedPreview = previewPdf as jest.Mock;
const mockedDownload = downloadPdf as jest.Mock;

describe('PdfActions', () => {
  afterEach(() => jest.clearAllMocks());

  it('calls previewPdf with the given url when Preview PDF is clicked', async () => {
    mockedPreview.mockResolvedValue(undefined);
    render(<PdfActions url="/invoices/inv1/pdf" />);

    await userEvent.click(screen.getByRole('button', { name: 'Preview PDF' }));

    await waitFor(() => expect(mockedPreview).toHaveBeenCalledWith('/invoices/inv1/pdf'));
    expect(mockedDownload).not.toHaveBeenCalled();
  });

  it('calls downloadPdf with the given url when Download PDF is clicked', async () => {
    mockedDownload.mockResolvedValue(undefined);
    render(<PdfActions url="/quotations/q1/pdf" />);

    await userEvent.click(screen.getByRole('button', { name: 'Download PDF' }));

    await waitFor(() => expect(mockedDownload).toHaveBeenCalledWith('/quotations/q1/pdf'));
    expect(mockedPreview).not.toHaveBeenCalled();
  });

  it('disables both buttons while a preview is pending, preventing duplicate clicks', async () => {
    let resolvePreview: (value?: unknown) => void = () => {};
    mockedPreview.mockReturnValue(new Promise((resolve) => (resolvePreview = resolve)));
    render(<PdfActions url="/invoices/inv1/pdf" />);

    await userEvent.click(screen.getByRole('button', { name: 'Preview PDF' }));

    await waitFor(() => expect(screen.getByRole('button', { name: 'Download PDF' })).toBeDisabled());
    resolvePreview();
  });

  it('shows a 403-specific message on a permission error', async () => {
    mockedPreview.mockRejectedValue(new ApiError('PERMISSION_ERROR', 'nope', [], undefined, 403));
    const { toast } = jest.requireMock('sonner');
    render(<PdfActions url="/invoices/inv1/pdf" />);

    await userEvent.click(screen.getByRole('button', { name: 'Preview PDF' }));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("You don't have permission to download this document."),
    );
  });

  it('shows a 404-specific message when the document is not found', async () => {
    mockedDownload.mockRejectedValue(new ApiError('NOT_FOUND', 'nope', [], undefined, 404));
    const { toast } = jest.requireMock('sonner');
    render(<PdfActions url="/invoices/inv1/pdf" />);

    await userEvent.click(screen.getByRole('button', { name: 'Download PDF' }));

    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('Document not found.'));
  });

  it('shows a generation-failure message on a 500', async () => {
    mockedDownload.mockRejectedValue(new ApiError('INTERNAL_ERROR', 'nope', [], undefined, 500));
    const { toast } = jest.requireMock('sonner');
    render(<PdfActions url="/invoices/inv1/pdf" />);

    await userEvent.click(screen.getByRole('button', { name: 'Download PDF' }));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith('PDF could not be generated. Please try again.'),
    );
  });

  it('shows a popup-blocked message distinctly', async () => {
    mockedPreview.mockRejectedValue(new Error('POPUP_BLOCKED'));
    const { toast } = jest.requireMock('sonner');
    render(<PdfActions url="/invoices/inv1/pdf" />);

    await userEvent.click(screen.getByRole('button', { name: 'Preview PDF' }));

    await waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(
        'Your browser blocked the preview. Please allow pop-ups for this site and try again.',
      ),
    );
  });
});
