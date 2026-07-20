import { useState, useEffect, useCallback } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useTheme } from 'next-themes';
import { LogOut, CircleUser, Plus, LayoutDashboard, MessageSquare, Users, Gauge, Clock, BookOpen, CheckSquare, UserCog, MessageCircle, Target, Flag, CheckCircle, Sun, Moon, ShieldCheck, Flame, Compass, Zap, Wifi, History } from 'lucide-react';
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
  const { theme, setTheme } = useTheme();
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [active, setActive] = useState(null);
  const [unlocks, setUnlocks] = useState(null);
  const [threadCount, setThreadCount] = useState(0);
  const [journeyState, setJourneyState] = useState(null);

  const loadActive = useCallback(() => {
    if (!user) return;
    api.get('/brain/active').then((r) => setActive(r.data?.next || null)).catch(() => {});
  }, [user]);

  useEffect(() => {
    if (!user) return undefined;
    const loadJourney = () => api.get('/journey').then((r) => {
      setUnlocks(r.data?.unlocks || null);
      setJourneyState({
        started: r.data?.started || false,
        has_direction: r.data?.has_direction || false,
        milestones: (r.data?.milestones || []).length > 0,
        team_plan: !!(r.data?.team?.plan),
      });
    }).catch(() => {});
    loadJourney();
    window.addEventListener('sdg-journey-changed', loadJourney);
    return () => window.removeEventListener('sdg-journey-changed', loadJourney);
  }, [user]);

  useEffect(() => {
    if (!user) return;
    api.get('/goals').then((r) => {
      const items = r.data?.goals || [];
      setThreadCount(items.filter((g) => g.status === 'active').length);
    }).catch(() => {});
  }, [user]);

  useEffect(() => {
    loadActive();
    const id = setInterval(loadActive, 60000);
    const onChange = () => loadActive();
    window.addEventListener('sdg-actions-changed', onChange);
    return () => { clearInterval(id); window.removeEventListener('sdg-actions-changed', onChange); };
  }, [loadActive]);

  const u = unlocks || {};
  const nav = [
    ...(threadCount > 0 ? [{ to: '/app', label: `Situations (${threadCount})`, icon: MessageCircle, testid: 'nav-situations' }] : [{ to: '/app', label: 'Home', icon: MessageCircle, testid: 'nav-home' }]),
    { to: '/app/brain', label: 'Brain', icon: BookOpen, testid: 'nav-knowledge' },
    ...(u.decisions ? [{ to: '/app/decisions', label: 'My Decisions', icon: CheckSquare, testid: 'nav-decisions' }] : []),
    ...(u.team ? [{ to: '/app/team', label: 'Team', icon: Users, testid: 'nav-team' }] : []),
    ...(u.cockpit ? [{ to: '/app/cockpit', label: 'Cockpit', icon: Gauge, testid: 'nav-cockpit' }] : []),
    ...(u.cockpit ? [{ to: '/app/mission-control', label: 'Mission Control', icon: ShieldCheck, testid: 'nav-mission-control' }] : []),
    ...(u.cockpit ? [{ to: '/app/founder-profile', label: 'My Profile', icon: UserCog, testid: 'nav-founder-profile' }] : []),
  ];
  const isActive = (to) => (to === '/app' ? location.pathname === '/app' : location.pathname.startsWith(to));

  const toggleTheme = () => setTheme(theme === 'dark' ? 'light' : 'dark');

  return (
    <header className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-2">
      <div className="flex items-center justify-between gap-3">
        <button onClick={() => navigate('/app')} data-testid="brand-home" className="flex items-center gap-2 shrink-0">
          <span className="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-text text-background font-display text-sm">S</span>
          <span className="font-display text-lg sm:text-xl hidden sm:inline">SmartDeciGen</span>
        </button>

        <nav className="hidden md:flex items-center gap-1 ml-2 mr-auto">
          {nav.map((n) => {
            const Icon = n.icon;
            return (
              <button key={n.to} data-testid={n.testid} onClick={() => navigate(n.to)}
                className={`flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-sm transition-colors ${isActive(n.to) ? 'bg-surface-2 text-text' : 'text-muted hover:text-text hover:bg-surface-2/60'}`}>
                <Icon size={15} strokeWidth={1.75} /> {n.label}
              </button>
            );
          })}
        </nav>

        <div className="flex items-center gap-3 sm:gap-4 shrink-0">
          <button
            onClick={toggleTheme}
            data-testid="theme-toggle"
            className="flex items-center justify-center w-8 h-8 rounded-xl text-muted hover:text-text hover:bg-surface-2/60 transition-all duration-200"
            aria-label="Toggle theme"
          >
            {theme === 'dark' ? <Sun size={15} strokeWidth={1.75} /> : <Moon size={15} strokeWidth={1.75} />}
          </button>
          {active && (
            <button data-testid="active-action-timer" onClick={() => navigate('/app/decisions')} title={active.action}
              className={`flex items-center gap-1.5 text-xs rounded-full px-2.5 py-1 border transition-colors ${active.overdue ? 'border-destructive/40 text-destructive bg-destructive/10' : 'border-hairline text-accent hover:bg-surface-2/60'}`}>
              <Clock size={12} strokeWidth={2} />
              <span className="font-mono-plex">{active.overdue ? 'Action due' : fmtLeft(active.due_at)}</span>
            </button>
          )}
          <button data-testid="credits-balance" onClick={() => navigate('/app/billing')}
            className="group flex items-center gap-1 font-mono-plex text-xs text-muted hover:text-text transition-colors" title="Subscription & tokens">
            {user?.credits ?? 0} tokens · plan
            <Plus size={12} strokeWidth={2} className="opacity-60 group-hover:opacity-100" />
          </button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" data-testid="account-menu-button" className="rounded-xl">
                <CircleUser size={18} strokeWidth={1.75} />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="rounded-xl">
              <DropdownMenuLabel className="text-xs font-normal text-muted">{user?.email}</DropdownMenuLabel>
              {journeyState && (
                <div className="px-3 py-2 space-y-1 border-b border-hairline mb-1" data-testid="progress-checklist">
                  <p className="text-[10px] uppercase tracking-wider text-muted/70">Your progress</p>
                  {[
                    { done: journeyState.started, label: 'Start your conversation', icon: MessageCircle },
                    { done: journeyState.has_direction, label: 'Get a direction', icon: Target },
                    { done: journeyState.milestones, label: 'Set measurable milestones', icon: Flag },
                    { done: threadCount > 0, label: 'Start daily check-ins', icon: CheckCircle },
                    { done: journeyState.team_plan, label: 'Set up your team', icon: Users },
                  ].map((s) => (
                    <div key={s.label} className="flex items-center gap-2 text-xs">
                      {s.done
                        ? <CheckCircle size={12} className="text-accent shrink-0" />
                        : <div className="w-3 h-3 rounded-full border border-muted/40 shrink-0" />}
                      <span className={s.done ? 'text-muted/70' : 'text-muted'}>{s.label}</span>
                    </div>
                  ))}
                </div>
              )}
              <DropdownMenuSeparator />
              <div className="md:hidden">
                {nav.map((n) => (
                  <DropdownMenuItem key={n.to} data-testid={`menu-${n.testid}`} onClick={() => navigate(n.to)} className="text-sm cursor-pointer">
                    <n.icon size={16} strokeWidth={1.75} className="mr-2" /> {n.label}
                  </DropdownMenuItem>
                ))}
                <DropdownMenuSeparator />
              </div>
              <DropdownMenuItem onClick={() => navigate('/app/habits')} className="text-sm cursor-pointer">
                <Flame size={16} strokeWidth={1.75} className="mr-2" /> Habits
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate('/app/playbooks')} className="text-sm cursor-pointer">
                <BookOpen size={16} strokeWidth={1.75} className="mr-2" /> Playbooks
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate('/app/weekly-review')} className="text-sm cursor-pointer">
                <Compass size={16} strokeWidth={1.75} className="mr-2" /> Weekly Review
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate('/app/business-os')} className="text-sm cursor-pointer">
                <Zap size={16} strokeWidth={1.75} className="mr-2" /> Business OS
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate('/app/connections')} className="text-sm cursor-pointer">
                <Wifi size={16} strokeWidth={1.75} className="mr-2" /> Connections
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => navigate('/app/record-room')} className="text-sm cursor-pointer">
                <History size={16} strokeWidth={1.75} className="mr-2" /> Record Room
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem data-testid="buy-credits-menu" onClick={() => navigate('/app/billing')} className="text-sm cursor-pointer">
                <Plus size={16} strokeWidth={1.75} className="mr-2" /> Subscription & tokens
              </DropdownMenuItem>
              <DropdownMenuItem data-testid="feedback-menu" onClick={() => setFeedbackOpen(true)} className="text-sm cursor-pointer">
                <MessageSquare size={16} strokeWidth={1.75} className="mr-2" /> Share feedback
              </DropdownMenuItem>
              {user?.is_admin && (
                <DropdownMenuItem data-testid="founder-os-menu" onClick={() => navigate('/app/admin')} className="text-sm cursor-pointer">
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
