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
