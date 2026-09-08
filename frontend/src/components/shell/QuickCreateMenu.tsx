import { FolderKanban, Package, Plus, UserRound } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

// Application_Shell_Navigation.md §"Quick Create": compact command-menu
// list, opens a Dialog/Drawer per entry — never navigates away directly.
// Each entry appears only once its module has a real create flow (its
// list page opens the create Sheet on ?new=true).
export function QuickCreateMenu() {
  const navigate = useNavigate();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="Quick create" className="max-md:size-11">
          <Plus />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuItem onSelect={() => navigate('/clients?new=true')}>
          <UserRound className="size-4" />
          New Client
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate('/projects?new=true')}>
          <FolderKanban className="size-4" />
          New Project
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => navigate('/products?new=true')}>
          <Package className="size-4" />
          New Product
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
