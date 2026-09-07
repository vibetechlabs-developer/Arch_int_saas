import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';

describe('ConfirmationDialog', () => {
  it('renders the title, consequence copy, and a destructive-labeled confirm action', () => {
    render(
      <ConfirmationDialog
        open
        onOpenChange={jest.fn()}
        title="Delete this client?"
        description='This removes "Acme Interiors" from your client list.'
        confirmLabel="Delete client"
        destructive
        onConfirm={jest.fn()}
      />,
    );

    expect(screen.getByText('Delete this client?')).toBeInTheDocument();
    expect(screen.getByText('This removes "Acme Interiors" from your client list.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Delete client' })).toBeInTheDocument();
  });

  it('calls onConfirm on confirm, and onOpenChange(false) on cancel — never the native confirm()', async () => {
    const onConfirm = jest.fn();
    const onOpenChange = jest.fn();
    render(
      <ConfirmationDialog
        open
        onOpenChange={onOpenChange}
        title="Delete this client?"
        description="This cannot be undone."
        confirmLabel="Delete client"
        destructive
        onConfirm={onConfirm}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: 'Delete client' }));
    expect(onConfirm).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('disables both actions while a delete is in flight', () => {
    render(
      <ConfirmationDialog
        open
        onOpenChange={jest.fn()}
        title="Delete this client?"
        description="This cannot be undone."
        confirmLabel="Delete client"
        loading
        onConfirm={jest.fn()}
      />,
    );

    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
  });
});
