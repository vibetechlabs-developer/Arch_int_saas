import { titleForPath } from '@/components/PageTitle';

describe('titleForPath', () => {
  it.each([
    ['/dashboard', 'Dashboard · INT Projects'],
    ['/leads', 'Leads · INT Projects'],
    ['/leads/abc-123', 'Lead · INT Projects'],
    ['/projects/9/invoices', 'Project · INT Projects'],
    ['/settings/security', 'Security · INT Projects'],
    ['/platform/companies/xyz', 'Company · INT Projects'],
    ['/login', 'Sign in · INT Projects'],
    ['/forgot-password', 'Forgot password · INT Projects'],
    ['/', 'INT Projects'],
  ])('%s -> %s', (path, expected) => {
    expect(titleForPath(path)).toBe(expected);
  });

  it('names an unknown route instead of showing a misleading title', () => {
    expect(titleForPath('/no/such/page')).toBe('Page not found · INT Projects');
  });
});
