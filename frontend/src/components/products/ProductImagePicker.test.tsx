import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ProductImagePicker, validateProductImageFile } from '@/components/products/ProductImagePicker';

const jpegFile = () => new File([new Uint8Array([1, 2, 3])], 'photo.jpg', { type: 'image/jpeg' });

const createObjectURLMock = jest.fn(() => 'blob:mock-preview-url');
const revokeObjectURLMock = jest.fn();

beforeAll(() => {
  // jsdom has no real object URL implementation.
  (URL as unknown as { createObjectURL: typeof createObjectURLMock }).createObjectURL = createObjectURLMock;
  (URL as unknown as { revokeObjectURL: typeof revokeObjectURLMock }).revokeObjectURL = revokeObjectURLMock;
});

function renderPicker(overrides: Partial<React.ComponentProps<typeof ProductImagePicker>> = {}) {
  const props = {
    currentUrl: '',
    pendingFile: null,
    onFileSelect: jest.fn(),
    onRemove: jest.fn(),
    onUrlChange: jest.fn(),
    ...overrides,
  };
  const utils = render(<ProductImagePicker {...props} />);
  return { ...utils, props };
}

describe('validateProductImageFile', () => {
  it('rejects an unsupported MIME type', () => {
    const file = new File(['x'], 'photo.gif', { type: 'image/gif' });
    expect(validateProductImageFile(file)).toBe('Only JPEG, PNG, and WEBP images are supported.');
  });

  it('rejects a file over 5 MB', () => {
    const big = new File([new Uint8Array(6 * 1024 * 1024)], 'photo.jpg', { type: 'image/jpeg' });
    expect(validateProductImageFile(big)).toBe('Image must be smaller than 5 MB.');
  });

  it('accepts a valid small JPEG', () => {
    expect(validateProductImageFile(jpegFile())).toBeNull();
  });
});

describe('ProductImagePicker', () => {
  afterEach(() => jest.clearAllMocks());

  it('shows the "Choose Image" dropzone empty state when there is no image', () => {
    renderPicker();
    expect(screen.getByText('Drop image here')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /choose image/i })).toBeInTheDocument();
  });

  it('calls onFileSelect with the chosen file', async () => {
    const { props } = renderPicker();
    const file = jpegFile();

    await userEvent.upload(screen.getByLabelText('Product image file'), file);

    expect(props.onFileSelect).toHaveBeenCalledWith(file);
  });

  it('shows a preview and "Replace Image"/"Remove" once an image exists', () => {
    renderPicker({ currentUrl: 'https://files.example.com/a.jpg' });

    expect(screen.getByRole('img', { name: 'Product preview' })).toHaveAttribute(
      'src',
      'https://files.example.com/a.jpg',
    );
    expect(screen.getByRole('button', { name: /replace image/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /remove/i })).toBeInTheDocument();
  });

  it('calls onRemove when Remove is clicked', async () => {
    const { props } = renderPicker({ currentUrl: 'https://files.example.com/a.jpg' });
    await userEvent.click(screen.getByRole('button', { name: /remove/i }));
    expect(props.onRemove).toHaveBeenCalled();
  });

  it('prefers a pending local file preview over the persisted URL', () => {
    renderPicker({ currentUrl: 'https://files.example.com/old.jpg', pendingFile: jpegFile() });
    expect(screen.getByRole('img', { name: 'Product preview' })).toHaveAttribute('src', 'blob:mock-preview-url');
  });

  it('falls back to a placeholder icon, not a broken-image icon, when the URL 404s', () => {
    renderPicker({ currentUrl: 'https://files.example.com/missing.jpg' });
    const img = screen.getByRole('img', { name: 'Product preview' });

    fireEvent.error(img);

    expect(screen.queryByRole('img', { name: 'Product preview' })).not.toBeInTheDocument();
    expect(screen.getByText('Drop image here')).toBeInTheDocument();
  });

  it('switches to a plain URL field via "Use an image URL instead", and back', async () => {
    renderPicker({ currentUrl: 'https://files.example.com/a.jpg' });

    await userEvent.click(screen.getByRole('button', { name: /use an image url instead/i }));
    expect(screen.getByLabelText('Image URL')).toHaveValue('https://files.example.com/a.jpg');
    expect(screen.queryByRole('button', { name: /choose image/i })).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /use file upload instead/i }));
    expect(screen.getByRole('button', { name: /replace image/i })).toBeInTheDocument();
  });

  it('never shows both the file picker and the URL field at the same time', async () => {
    renderPicker();
    expect(screen.queryByLabelText('Image URL')).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole('button', { name: /use an image url instead/i }));
    expect(screen.queryByRole('button', { name: /choose image/i })).not.toBeInTheDocument();
  });

  it('calls onUrlChange while typing in URL mode', async () => {
    const { props } = renderPicker();
    await userEvent.click(screen.getByRole('button', { name: /use an image url instead/i }));

    await userEvent.type(screen.getByLabelText('Image URL'), 'x');

    expect(props.onUrlChange).toHaveBeenCalledWith('x');
  });

  it('shows the passed-in error message', () => {
    renderPicker({ error: 'Image must be smaller than 5 MB.' });
    expect(screen.getByText('Image must be smaller than 5 MB.')).toBeInTheDocument();
  });

  it('disables all controls while uploading/saving', () => {
    renderPicker({ disabled: true });
    expect(screen.getByRole('button', { name: /choose image/i })).toBeDisabled();
    expect(screen.getByLabelText('Product image file')).toBeDisabled();
  });
});
