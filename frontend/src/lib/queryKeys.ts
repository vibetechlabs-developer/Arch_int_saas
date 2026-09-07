// Centralized query-key factories (TanStack Query convention: all/lists/list/detail)
// so every module invalidates precisely — a mutation never has to guess string
// literals another file used. Extend with one factory per module as it ships.

export const clientKeys = {
  all: ['clients'] as const,
  lists: () => [...clientKeys.all, 'list'] as const,
  list: (params: Record<string, unknown>) => [...clientKeys.lists(), params] as const,
  detail: (id: string) => [...clientKeys.all, 'detail', id] as const,
};
