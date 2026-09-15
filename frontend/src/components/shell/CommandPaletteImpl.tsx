import { useNavigate } from 'react-router-dom';
import {
  BarChart3,
  FolderKanban,
  FolderTree,
  KeyRound,
  LayoutDashboard,
  Package,
  Settings,
  ShieldCheck,
  User,
  UserPlus,
  UserRound,
  UserRoundSearch,
  Users,
} from 'lucide-react';
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
          <CommandItem onSelect={() => go('/leads')}>
            <UserRoundSearch className="size-4" />
            Leads
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
          <CommandItem onSelect={() => go('/reports')}>
            <BarChart3 className="size-4" />
            Reports
          </CommandItem>
          <CommandItem onSelect={() => go('/settings')}>
            <Settings className="size-4" />
            Settings
          </CommandItem>
          <CommandItem onSelect={() => go('/settings/members')}>
            <Users className="size-4" />
            Manage Members
          </CommandItem>
          <CommandItem onSelect={() => go('/settings/roles')}>
            <ShieldCheck className="size-4" />
            Manage Roles
          </CommandItem>
          <CommandItem onSelect={() => go('/settings/company')}>
            <Settings className="size-4" />
            Company Settings
          </CommandItem>
          <CommandItem onSelect={() => go('/settings/product-categories')}>
            <FolderTree className="size-4" />
            Product Categories
          </CommandItem>
          <CommandItem onSelect={() => go('/settings/profile')}>
            <User className="size-4" />
            Profile
          </CommandItem>
          <CommandItem onSelect={() => go('/settings/security')}>
            <KeyRound className="size-4" />
            Security
          </CommandItem>
        </CommandGroup>
        <CommandGroup heading="Create">
          <CommandItem onSelect={() => go('/leads?new=true')}>
            <UserRoundSearch className="size-4" />
            New Lead
          </CommandItem>
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
          <CommandItem onSelect={() => go('/settings/members?addUser=true')}>
            <UserPlus className="size-4" />
            Add User
          </CommandItem>
        </CommandGroup>
        <CommandEmpty>Nothing found yet — more modules become searchable as they ship.</CommandEmpty>
      </CommandList>
    </CommandDialog>
  );
}
