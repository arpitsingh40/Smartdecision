import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogOut, CircleUser, Plus, LayoutDashboard, MessageSquare, BrainCircuit, Users, Gauge, Clock } from 'lucide-react';
import { Button } from './ui/button';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from './ui/dropdown-menu';
import { FeedbackDialog } from './FeedbackDialog';
import { api } from '../lib/api';
import { useAuth } from '../App';

const fmtLeft = (iso) => {
  if (!iso) return '';
  const ms = new Date(iso).getTime() - Date.now();
  if (ms < 0) return 'overdue';
  const m = Math.round(ms / 60000);
  const d = Math.floor(m / 1440); const h = Math.floor((m % 1440) / 60); const mm = m % 60;
  return d > 0 ? `${d}d ${h}h` : h > 0 ? `${h}h` : `${mm}m`;
};

export const TopBar = ({ title, backTo }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [active, setActive] = useState(null);

  const loadActive = useCallback(() => {
    if (!user) return;
    api.get('/brain/active').then((r) => setActive(r.data?.next || null)).catch(() => {});
  }, [user]);

  useEffect(() => {
    loadActive();
    const id = setInterval(loadActive, 60000);
    const onChange = () => loadActive();
    window.addEventListener('sdg-actions-changed', onChange);
    return () => { clearInterval(id); window.removeEventListener('sdg-actions-changed', onChange); };
  }, [loadActive]);
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
        {active && (
          <button data-testid="active-action-timer" onClick={() => navigate('/brain')}
            title={active.action}
            className={`flex items-center gap-1.5 text-xs rounded-full px-2.5 py-1 border transition-colors ${active.overdue ? 'border-amber-400 text-amber-600 bg-amber-50' : 'border-border/70 text-[hsl(var(--ring))] hover:bg-muted/60'}`}>
            <Clock size={12} strokeWidth={2} />
            <span className="font-mono-plex">{active.overdue ? 'Action due' : fmtLeft(active.due_at)}</span>
          </button>
        )}
        <button data-testid="feedback-link" onClick={() => setFeedbackOpen(true)}
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          title="Share feedback">
          <MessageSquare size={13} strokeWidth={1.75} />
          <span className="hidden sm:inline">Feedback</span>
        </button>
        <button data-testid="credits-balance" onClick={() => navigate('/billing')}
          className="group flex items-center gap-1 font-mono-plex text-xs text-muted-foreground hover:text-foreground transition-colors"
          title="Buy credits">
          {user?.credits ?? 0} credits
          <Plus size={12} strokeWidth={2} className="opacity-60 group-hover:opacity-100" />
        </button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" data-testid="account-menu-button" className="rounded-xl">
              <CircleUser size={18} strokeWidth={1.75} />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="rounded-xl">
            <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">{user?.email}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuSeparator />
            <DropdownMenuItem data-testid="team-menu" onClick={() => navigate('/team')} className="text-sm cursor-pointer">
              <Users size={16} strokeWidth={1.75} className="mr-2" /> {user?.org_role === 'member' ? 'Workspace' : 'Team'}
            </DropdownMenuItem>
            {user?.org_role === 'owner' && (
              <DropdownMenuItem data-testid="cockpit-menu" onClick={() => navigate('/cockpit')} className="text-sm cursor-pointer">
                <Gauge size={16} strokeWidth={1.75} className="mr-2" /> Founder Cockpit
              </DropdownMenuItem>
            )}
            <DropdownMenuItem data-testid="decision-brain-menu" onClick={() => navigate('/brain')} className="text-sm cursor-pointer">
              <BrainCircuit size={16} strokeWidth={1.75} className="mr-2" /> Decision Brain
            </DropdownMenuItem>
            <DropdownMenuItem data-testid="buy-credits-menu" onClick={() => navigate('/billing')} className="text-sm cursor-pointer">
              <Plus size={16} strokeWidth={1.75} className="mr-2" /> Buy credits
            </DropdownMenuItem>
            <DropdownMenuItem data-testid="feedback-menu" onClick={() => setFeedbackOpen(true)} className="text-sm cursor-pointer">
              <MessageSquare size={16} strokeWidth={1.75} className="mr-2" /> Share feedback
            </DropdownMenuItem>
            {user?.is_admin && (
              <DropdownMenuItem data-testid="founder-os-menu" onClick={() => navigate('/admin')} className="text-sm cursor-pointer">
                <LayoutDashboard size={16} strokeWidth={1.75} className="mr-2" /> Founder OS
              </DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem data-testid="logout-button" onClick={logout} className="text-sm cursor-pointer">
              <LogOut size={16} strokeWidth={1.75} className="mr-2" /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <FeedbackDialog open={feedbackOpen} onOpenChange={setFeedbackOpen} />
    </header>
  );
};
