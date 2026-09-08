import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { SidebarNav } from '@/components/shell/SidebarNav';
import { TooltipProvider } from '@/components/ui/tooltip';

function renderNav(route: string, props: Parameters<typeof SidebarNav>[0] = {}) {
  return render(
    <TooltipProvider>
      <MemoryRouter initialEntries={[route]}>
        <SidebarNav {...props} />
      </MemoryRouter>
    </TooltipProvider>,
  );
}

describe('SidebarNav', () => {
  it('exposes every implemented top-level module as a real link', () => {
    renderNav('/dashboard');

    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('href', '/dashboard');
    expect(screen.getByRole('link', { name: 'Clients' })).toHaveAttribute('href', '/clients');
    expect(screen.getByRole('link', { name: 'Projects' })).toHaveAttribute('href', '/projects');
    expect(screen.getByRole('link', { name: 'Products' })).toHaveAttribute('href', '/products');
    expect(screen.getByRole('link', { name: 'Reports' })).toHaveAttribute('href', '/reports');
  });

  it('never exposes Activity — the module remains blocked', () => {
    renderNav('/dashboard');

    expect(screen.queryByRole('link', { name: /activity/i })).not.toBeInTheDocument();
  });

  it('does not expose project-scoped or invoice-scoped modules as primary sidebar items', () => {
    renderNav('/dashboard');

    for (const label of ['BOQ', 'Quotations', 'Invoices', 'Payments', 'Expenses', 'Documents']) {
      expect(screen.queryByRole('link', { name: label })).not.toBeInTheDocument();
    }
  });

  it('marks Projects active for a nested project route, not just the exact /projects path', () => {
    renderNav('/projects/p1/boq');

    expect(screen.getByRole('link', { name: 'Projects' })).toHaveAttribute('aria-current', 'page');
    expect(screen.getByRole('link', { name: 'Clients' })).not.toHaveAttribute('aria-current');
  });

  it('marks Products active while viewing Product Categories, a different URL prefix for the same module', () => {
    renderNav('/settings/product-categories');

    expect(screen.getByRole('link', { name: 'Products' })).toHaveAttribute('aria-current', 'page');
  });

  it('marks Reports active for the Reports route', () => {
    renderNav('/reports');

    expect(screen.getByRole('link', { name: 'Reports' })).toHaveAttribute('aria-current', 'page');
  });

  it('renders inside a nav landmark', () => {
    renderNav('/dashboard');

    expect(screen.getByRole('navigation')).toBeInTheDocument();
  });

  it('collapses to icon-only links that stay reachable and labeled via tooltip', () => {
    renderNav('/dashboard', { collapsed: true });

    const dashboardLink = screen.getByRole('link', { name: 'Dashboard' });
    expect(dashboardLink).toHaveAttribute('href', '/dashboard');
    // Section labels disappear in collapsed mode, but the accessible name
    // (from the tooltip content, matched by the Radix Tooltip a11y wiring)
    // is retained rather than left as an icon with no name at all.
    expect(screen.queryByText('Overview')).not.toBeInTheDocument();
  });
});
