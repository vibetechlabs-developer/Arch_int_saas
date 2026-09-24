import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ForgotPasswordPage from '@/pages/ForgotPasswordPage';
import { requestPasswordReset } from '@/lib/api/auth';
import { ApiError } from '@/lib/api/client';

jest.mock('@/lib/api/auth', () => ({
  ...jest.requireActual('@/lib/api/auth'),
  requestPasswordReset: jest.fn(),
}));
const mockedRequest = requestPasswordReset as jest.Mock;

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ForgotPasswordPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ForgotPasswordPage', () => {
  afterEach(() => jest.clearAllMocks());

  it('rejects a malformed email before calling the API', async () => {
    renderPage();
    await userEvent.type(screen.getByLabelText('Email'), 'nope');
    await userEvent.click(screen.getByRole('button', { name: /send reset link/i }));
    expect(await screen.findByText('Enter a valid email address')).toBeInTheDocument();
    expect(mockedRequest).not.toHaveBeenCalled();
  });

  it('shows a noncommittal confirmation (never confirms the account exists)', async () => {
    mockedRequest.mockResolvedValue(undefined);
    renderPage();
    await userEvent.type(screen.getByLabelText('Email'), 'someone@example.com');
    await userEvent.click(screen.getByRole('button', { name: /send reset link/i }));

    expect(await screen.findByText('Check your email')).toBeInTheDocument();
    expect(screen.getByText(/if an account exists for/i)).toBeInTheDocument();
    expect(mockedRequest).toHaveBeenCalledWith('someone@example.com');
  });

  it('surfaces the throttling message from the server', async () => {
    mockedRequest.mockRejectedValue(new ApiError('RATE_LIMIT_EXCEEDED', 'Too many requests. Try again later.'));
    renderPage();
    await userEvent.type(screen.getByLabelText('Email'), 'someone@example.com');
    await userEvent.click(screen.getByRole('button', { name: /send reset link/i }));
    await waitFor(() => expect(screen.getByText('Too many requests. Try again later.')).toBeInTheDocument());
  });

  it('always offers a way back to sign in', () => {
    renderPage();
    expect(screen.getByRole('link', { name: /back to sign in/i })).toHaveAttribute('href', '/login');
  });
});
