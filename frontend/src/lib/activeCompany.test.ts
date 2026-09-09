import { activeCompanyStore } from '@/lib/activeCompany';

describe('activeCompanyStore', () => {
  afterEach(() => {
    activeCompanyStore.set(null);
    localStorage.clear();
  });

  it('persists the selected company id to localStorage', () => {
    activeCompanyStore.set('company-a');
    expect(activeCompanyStore.get()).toBe('company-a');
    expect(localStorage.getItem('activeCompanyId')).toBe('company-a');
  });

  it('clears localStorage when set to null', () => {
    activeCompanyStore.set('company-a');
    activeCompanyStore.set(null);
    expect(activeCompanyStore.get()).toBeNull();
    expect(localStorage.getItem('activeCompanyId')).toBeNull();
  });

  it('notifies subscribers only when the value actually changes', () => {
    const listener = jest.fn();
    const unsubscribe = activeCompanyStore.subscribe(listener);

    activeCompanyStore.set('company-a');
    expect(listener).toHaveBeenCalledTimes(1);

    // Setting the same id again must not re-notify — the Header switcher
    // and useCurrentCompanyId's sync effect both call set() defensively.
    activeCompanyStore.set('company-a');
    expect(listener).toHaveBeenCalledTimes(1);

    activeCompanyStore.set('company-b');
    expect(listener).toHaveBeenCalledTimes(2);

    unsubscribe();
    activeCompanyStore.set('company-c');
    expect(listener).toHaveBeenCalledTimes(2);
  });
});
