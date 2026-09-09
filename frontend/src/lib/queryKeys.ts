// Centralized query-key factories (TanStack Query convention: all/lists/list/detail)
// so every module invalidates precisely — a mutation never has to guess string
// literals another file used. Extend with one factory per module as it ships.

export const clientKeys = {
  all: ['clients'] as const,
  lists: () => [...clientKeys.all, 'list'] as const,
  list: (params: Record<string, unknown>) => [...clientKeys.lists(), params] as const,
  detail: (id: string) => [...clientKeys.all, 'detail', id] as const,
};

export const projectKeys = {
  all: ['projects'] as const,
  lists: () => [...projectKeys.all, 'list'] as const,
  list: (params: Record<string, unknown>) => [...projectKeys.lists(), params] as const,
  details: () => [...projectKeys.all, 'detail'] as const,
  detail: (id: string) => [...projectKeys.details(), id] as const,
  team: (id: string) => [...projectKeys.detail(id), 'team'] as const,
};

export const membershipKeys = {
  all: ['companyMemberships'] as const,
  search: (query: string) => [...membershipKeys.all, 'search', query] as const,
  lists: () => [...membershipKeys.all, 'list'] as const,
  list: (params: Record<string, unknown>) => [...membershipKeys.lists(), params] as const,
  detail: (id: string) => [...membershipKeys.all, 'detail', id] as const,
};

// GET /auth/memberships — a distinct resource from /company-memberships
// above (the caller's own cross-company workspace list vs. one company's
// full member roster), so it gets its own key rather than sharing
// membershipKeys.
export const myMembershipsKeys = {
  all: ['myMemberships'] as const,
};

export const companyKeys = {
  all: ['company'] as const,
  detail: (id: string) => [...companyKeys.all, 'detail', id] as const,
};

export const roleKeys = {
  all: ['roles'] as const,
  lists: () => [...roleKeys.all, 'list'] as const,
  list: (params: Record<string, unknown>) => [...roleKeys.lists(), params] as const,
  detail: (id: string) => [...roleKeys.all, 'detail', id] as const,
  // GET /roles/{id}/permissions (BE-072) — a distinct resource from the
  // role's own metadata above, so its cache entry can be invalidated
  // independently after a permissions-only mutation.
  permissions: (id: string) => [...roleKeys.all, 'permissions', id] as const,
};

// GET /permissions is a single global, unfiltered catalog — one cache
// entry, no list/detail split needed.
export const permissionKeys = {
  all: ['permissions'] as const,
};

export const productKeys = {
  all: ['products'] as const,
  lists: () => [...productKeys.all, 'list'] as const,
  list: (params: Record<string, unknown>) => [...productKeys.lists(), params] as const,
  details: () => [...productKeys.all, 'detail'] as const,
  detail: (id: string) => [...productKeys.details(), id] as const,
};

export const categoryKeys = {
  all: ['productCategories'] as const,
  lists: () => [...categoryKeys.all, 'list'] as const,
  list: (params: Record<string, unknown>) => [...categoryKeys.lists(), params] as const,
  detail: (id: string) => [...categoryKeys.all, 'detail', id] as const,
};

export const subcategoryKeys = {
  all: ['productSubcategories'] as const,
  forCategory: (categoryId: string) => [...subcategoryKeys.all, 'category', categoryId] as const,
  detail: (id: string) => [...subcategoryKeys.all, 'detail', id] as const,
};

// GET /projects/{id}/boq returns the whole tree in one call (no separate
// section/item list endpoints exist), so there's no boqKeys.section()/
// item() — a single project(id) key covers the entire tree.
export const boqKeys = {
  all: ['boq'] as const,
  project: (projectId: string) => [...boqKeys.all, 'project', projectId] as const,
  summary: (projectId: string) => [...boqKeys.all, 'summary', projectId] as const,
};

// GET /projects/{id}/quotations returns every version, unpaginated (no
// separate item endpoints — items are always nested), so there's no
// quotationKeys.items(). `project(id)` backs both the list tab and
// QuotationDetailPage's revision-lineage lookup (same cache entry).
export const quotationKeys = {
  all: ['quotations'] as const,
  project: (projectId: string) => [...quotationKeys.all, 'project', projectId] as const,
  detail: (id: string) => [...quotationKeys.all, 'detail', id] as const,
};

// GET /projects/{id}/invoices returns every invoice for the project,
// unpaginated (no separate item endpoints — items are always nested and
// only ever change via a full-array PATCH on the invoice itself).
export const invoiceKeys = {
  all: ['invoices'] as const,
  project: (projectId: string) => [...invoiceKeys.all, 'project', projectId] as const,
  detail: (id: string) => [...invoiceKeys.all, 'detail', id] as const,
};

// GET /invoices/{id}/payments is the only read endpoint Payment has (no
// GET /payments/{id}, no project-scoped list) — so there's no
// paymentKeys.detail()/project(), only the one key this app ever fetches.
export const paymentKeys = {
  all: ['payments'] as const,
  invoice: (invoiceId: string) => [...paymentKeys.all, 'invoice', invoiceId] as const,
};

// GET /projects/{id}/expenses supports real server-side filters/ordering
// (unlike Quotations/Invoices/Payments) but no pagination — the params
// object is folded straight into the list key so each distinct filter
// combination gets its own cache entry, the same convention productKeys/
// clientKeys already use for their paginated lists.
export const expenseKeys = {
  all: ['expenses'] as const,
  project: (projectId: string, params: Record<string, unknown> = {}) => [...expenseKeys.all, 'project', projectId, params] as const,
  detail: (id: string) => [...expenseKeys.all, 'detail', id] as const,
};

// No detail route exists for Documents — the list row already carries
// every field the API returns, and there is no GET-by-id use case in
// this workspace, so there's no documentKeys.detail().
export const documentKeys = {
  all: ['documents'] as const,
  project: (projectId: string) => [...documentKeys.all, 'project', projectId] as const,
};

// Only two report endpoints exist (GET /reports/finance, GET
// /reports/expenses), both taking the same filter shape — no
// reportKeys.dashboard(), since Dashboard already has its own ['dashboard']
// key and is a separate, un-filtered endpoint this module deliberately
// does not touch.
export const reportKeys = {
  all: ['reports'] as const,
  finance: (filters: { projectId?: string; dateFrom?: string; dateTo?: string }) =>
    [...reportKeys.all, 'finance', filters] as const,
  expenses: (filters: { projectId?: string; dateFrom?: string; dateTo?: string }) =>
    [...reportKeys.all, 'expenses', filters] as const,
};
