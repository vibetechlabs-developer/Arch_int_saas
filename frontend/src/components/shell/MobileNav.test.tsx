import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { MobileNav } from '@/components/shell/MobileNav';

describe('MobileNav', () => {
  it('exposes the same primary destinations as the desktop sidebar', () => {
    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <MobileNav open onOpenChange={jest.fn()} />
      </MemoryRouter>,
    );

    for (const label of ['Dashboard', 'Clients', 'Projects', 'Products', 'Reports']) {
      expect(screen.getByRole('link', { name: label })).toBeInTheDocument();
    }
    expect(screen.queryByRole('link', { name: /activity/i })).not.toBeInTheDocument();
  });
});
