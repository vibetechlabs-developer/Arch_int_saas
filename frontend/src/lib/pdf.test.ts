import { apiClient } from '@/lib/api/client';
import { downloadPdf, previewPdf } from '@/lib/pdf';

jest.mock('@/lib/api/client', () => ({
  ...jest.requireActual('@/lib/api/client'),
  apiClient: { get: jest.fn() },
}));

const mockedGet = apiClient.get as jest.Mock;

function makeBlobResponse(overrides: Partial<{ headers: Record<string, string> }> = {}) {
  return {
    data: new Blob(['%PDF-1.4 fake'], { type: 'application/pdf' }),
    headers: { 'content-disposition': 'attachment; filename="Invoice-INV-000001.pdf"', ...overrides.headers },
  };
}

describe('previewPdf', () => {
  afterEach(() => jest.clearAllMocks());

  it('requests the PDF as an authenticated blob with ?mode=preview', async () => {
    mockedGet.mockResolvedValue(makeBlobResponse());
    window.open = jest.fn().mockReturnValue({});

    await previewPdf('/invoices/inv1/pdf');

    expect(mockedGet).toHaveBeenCalledWith('/invoices/inv1/pdf', {
      params: { mode: 'preview' },
      responseType: 'blob',
    });
  });

  it('opens the blob URL in a new tab', async () => {
    mockedGet.mockResolvedValue(makeBlobResponse());
    const openSpy = jest.fn().mockReturnValue({});
    window.open = openSpy;

    await previewPdf('/invoices/inv1/pdf');

    expect(openSpy).toHaveBeenCalledWith('blob:mock-object-url', '_blank');
  });

  it('throws POPUP_BLOCKED when the browser prevents the new tab', async () => {
    mockedGet.mockResolvedValue(makeBlobResponse());
    window.open = jest.fn().mockReturnValue(null);

    await expect(previewPdf('/invoices/inv1/pdf')).rejects.toThrow('POPUP_BLOCKED');
  });

  it('propagates a backend error instead of opening anything', async () => {
    mockedGet.mockRejectedValue(new Error('Not found'));
    const openSpy = jest.fn();
    window.open = openSpy;

    await expect(previewPdf('/invoices/inv1/pdf')).rejects.toThrow('Not found');
    expect(openSpy).not.toHaveBeenCalled();
  });
});

describe('downloadPdf', () => {
  afterEach(() => jest.clearAllMocks());

  it('requests the PDF as an authenticated blob with no preview param', async () => {
    mockedGet.mockResolvedValue(makeBlobResponse());

    await downloadPdf('/invoices/inv1/pdf');

    expect(mockedGet).toHaveBeenCalledWith('/invoices/inv1/pdf', {
      params: undefined,
      responseType: 'blob',
    });
  });

  it('creates a temporary anchor using the server-provided filename, then cleans it up', async () => {
    mockedGet.mockResolvedValue(makeBlobResponse());
    const clickSpy = jest.fn();
    const originalCreateElement = document.createElement.bind(document);
    const createElementSpy = jest
      .spyOn(document, 'createElement')
      .mockImplementation((tag: string) => {
        const el = originalCreateElement(tag);
        if (tag === 'a') el.click = clickSpy;
        return el;
      });
    const appendSpy = jest.spyOn(document.body, 'appendChild');
    const removeSpy = jest.spyOn(document.body, 'removeChild');

    await downloadPdf('/invoices/inv1/pdf');

    expect(clickSpy).toHaveBeenCalledTimes(1);
    expect(appendSpy).toHaveBeenCalled();
    expect(removeSpy).toHaveBeenCalled();

    createElementSpy.mockRestore();
    appendSpy.mockRestore();
    removeSpy.mockRestore();
  });

  it('falls back to a default filename when no Content-Disposition header is present', async () => {
    mockedGet.mockResolvedValue({ data: new Blob(['%PDF-1.4 fake']), headers: {} });
    const clickSpy = jest.fn();
    const originalCreateElement = document.createElement.bind(document);
    let capturedDownloadAttr = '';
    jest.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      const el = originalCreateElement(tag);
      if (tag === 'a') {
        el.click = clickSpy;
        Object.defineProperty(el, 'download', {
          set(value: string) {
            capturedDownloadAttr = value;
          },
          get() {
            return capturedDownloadAttr;
          },
        });
      }
      return el;
    });

    await downloadPdf('/invoices/inv1/pdf');

    expect(capturedDownloadAttr).toBe('document.pdf');
    jest.restoreAllMocks();
  });
});
