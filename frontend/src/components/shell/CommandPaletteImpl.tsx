import { useNavigate } from 'react-router-dom';
import { FolderKanban, LayoutDashboard, Package, UserRound, Users } from 'lucide-react';
import { CommandDialog, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';

export interface CommandPaletteImplProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// Application_Shell_Navigation.md §5: Ctrl/Cmd+K global trigger, opened
// from Shell (single source of truth for the shortcut — the old scaffold
// faked this by dispatching a synthetic KeyboardEvent from the header
// button, which this controlled-props design avoids entirely). Search
// results reuse each module's own `?q=` API — for now only navigation to
// existing pages plus quick-create shortcuts are wired; a real resource
// search group is added module by module as each one ships.
export function CommandPaletteImpl({ open, onOpenChange }: CommandPaletteImplProps) {
  const navigate = useNavigate();

  const go = (path: string) => {
    onOpenChange(false);
    navigate(path);
  };

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Search anything…" />
      <CommandList>
        <CommandGroup heading="Go to">
          <CommandItem onSelect={() => go('/dashboard')}>
            <LayoutDashboard className="size-4" />
            Dashboard
          </CommandItem>
          <CommandItem onSelect={() => go('/clients')}>
            <Users className="size-4" />
            Clients
          </CommandItem>
          <CommandItem onSelect={() => go('/projects')}>
            <FolderKanban className="size-4" />
            Projects
          </CommandItem>
          <CommandItem onSelect={() => go('/products')}>
            <Package className="size-4" />
            Products
          </CommandItem>
        </CommandGroup>
        <CommandGroup heading="Create">
          <CommandItem onSelect={() => go('/clients?new=true')}>
            <UserRound className="size-4" />
            New Client
          </CommandItem>
          <CommandItem onSelect={() => go('/projects?new=true')}>
            <FolderKanban className="size-4" />
            New Project
          </CommandItem>
          <CommandItem onSelect={() => go('/products?new=true')}>
            <Package className="size-4" />
            New Product
          </CommandItem>
        </CommandGroup>
        <CommandEmpty>Nothing found yet — more modules become searchable as they ship.</CommandEmpty>
      </CommandList>
    </CommandDialog>
  );
}
