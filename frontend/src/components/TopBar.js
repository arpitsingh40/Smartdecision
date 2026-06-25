import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { LogOut, CircleUser, Plus, LayoutDashboard, MessageSquare, Users, Gauge, Clock, Compass, CheckSquare, UserCog } from 'lucide-react';
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

export const TopBar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
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

  const nav = [
    { to: '/', label: 'Workspace', icon: Compass, testid: 'nav-workspace' },
    { to: '/decisions', label: 'My Decisions', icon: CheckSquare, testid: 'nav-decisions' },
    ...(user?.org_role === 'owner' ? [{ to: '/cockpit', label: 'Cockpit', icon: Gauge, testid: 'nav-cockpit' }] : []),
    ...(user?.org_role === 'owner' ? [{ to: '/founder-profile', label: 'My Profile', icon: UserCog, testid: 'nav-founder-profile' }] : []),
    { to: '/team', label: 'Team', icon: Users, testid: 'nav-team' },
  ];
  const isActive = (to) => (to === '/' ? location.pathname === '/' : location.pathname.startsWith(to));

  return (
    <header className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-2">
      <div className="flex items-center justify-between gap-3">
        <button onClick={() => navigate('/')} data-testid="brand-home" className="flex items-center gap-2 shrink-0">
          <span className="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-primary text-primary-foreground font-display text-sm">S</span>
          <span className="font-display text-lg sm:text-xl hidden sm:inline">SmartDeciGen</span>
        </button>

        <nav className="hidden md:flex items-center gap-1 ml-2 mr-auto">
          {nav.map((n) => {
            const Icon = n.icon;
            return (
              <button key={n.to} data-testid={n.testid} onClick={() => navigate(n.to)}
                className={`flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-sm transition-colors ${isActive(n.to) ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'}`}>
                <Icon size={15} strokeWidth={1.75} /> {n.label}
              </button>
            );
          })}
        </nav>

        <div className="flex items-center gap-3 sm:gap-4 shrink-0">
          {active && (
            <button data-testid="active-action-timer" onClick={() => navigate('/decisions')} title={active.action}
              className={`flex items-center gap-1.5 text-xs rounded-full px-2.5 py-1 border transition-colors ${active.overdue ? 'border-amber-400 text-amber-600 bg-amber-50' : 'border-border/70 text-[hsl(var(--ring))] hover:bg-muted/60'}`}>
              <Clock size={12} strokeWidth={2} />
              <span className="font-mono-plex">{active.overdue ? 'Action due' : fmtLeft(active.due_at)}</span>
            </button>
          )}
          <button data-testid="credits-balance" onClick={() => navigate('/billing')}
            className="group flex items-center gap-1 font-mono-plex text-xs text-muted-foreground hover:text-foreground transition-colors" title="Buy credits">
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
              <div className="md:hidden">
                {nav.map((n) => (
                  <DropdownMenuItem key={n.to} data-testid={`menu-${n.testid}`} onClick={() => navigate(n.to)} className="text-sm cursor-pointer">
                    <n.icon size={16} strokeWidth={1.75} className="mr-2" /> {n.label}
                  </DropdownMenuItem>
                ))}
                <DropdownMenuSeparator />
              </div>
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
      </div>
      <FeedbackDialog open={feedbackOpen} onOpenChange={setFeedbackOpen} />
    </header>
  );
};
