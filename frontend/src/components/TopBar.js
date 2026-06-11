import { useNavigate } from 'react-router-dom';
import { LogOut, CircleUser } from 'lucide-react';
import { Button } from './ui/button';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { useAuth } from '../App';

export const TopBar = ({ title, backTo }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <header className="relative z-10 flex items-center justify-between max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-2">
      <div className="flex items-center gap-3 min-w-0">
        {backTo && (
          <button data-testid="back-button" onClick={() => navigate(backTo)}
            className="text-xs text-muted-foreground hover:text-foreground transition-colors shrink-0">
            ← Goals
          </button>
        )}
        <h1 className="font-display text-lg sm:text-xl truncate">{title}</h1>
      </div>
      <div className="flex items-center gap-4 shrink-0">
        <span data-testid="credits-balance" className="font-mono-plex text-xs text-muted-foreground">
          {user?.credits ?? 0} credits
        </span>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" data-testid="account-menu-button" className="rounded-xl">
              <CircleUser size={18} strokeWidth={1.75} />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="rounded-xl">
            <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">{user?.email}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem data-testid="logout-button" onClick={logout} className="text-sm cursor-pointer">
              <LogOut size={16} strokeWidth={1.75} className="mr-2" /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
};
