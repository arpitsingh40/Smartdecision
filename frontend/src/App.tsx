import { useState, useEffect, createContext, useContext, useCallback, lazy, Suspense, FC } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { ThemeProvider } from 'next-themes';
import { Toaster } from './components/ui/sonner';
import ErrorBoundary from './components/ErrorBoundary';

const withErrorBoundary = (Component: React.LazyExoticComponent<React.ComponentType<any>>) =>
  (props: any) => <ErrorBoundary><Component {...props} /></ErrorBoundary>;
import { Button } from './components/ui/button';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from './components/ui/dialog';
import { api, setAuthToken } from './lib/api';
import { toast } from 'sonner';
import './App.css';

const LandingPage = lazy(() => import('./pages/LandingPage'));
const AuthPage = lazy(() => import('./pages/AuthPage'));
const JourneyPage = lazy(() => import('./pages/JourneyPage'));
const ThreadPage = lazy(() => import('./pages/ThreadPage'));
const BrainPage = lazy(() => import('./pages/BrainPage'));
const DecisionsPage = lazy(() => import('./pages/DecisionsPage'));
const AdminPage = lazy(() => import('./pages/AdminPage'));
const BillingPage = lazy(() => import('./pages/BillingPage'));
const PaymentResultPage = lazy(() => import('./pages/PaymentResultPage'));
const TeamPage = lazy(() => import('./pages/TeamPage'));
const JoinPage = lazy(() => import('./pages/JoinPage'));
const CockpitPage = lazy(() => import('./pages/CockpitPage'));
const MyTasksPage = lazy(() => import('./pages/MyTasksPage'));
const GoalSetupPage = lazy(() => import('./pages/GoalSetupPage'));
const MissionControlPage = lazy(() => import('./pages/MissionControlPage'));
const ProfilePage = lazy(() => import('./pages/ProfilePage'));
const DecisionCardPage = lazy(() => import('./pages/DecisionCardPage'));
const HabitsPage = lazy(() => import('./pages/HabitsPage'));
const PlaybooksPage = lazy(() => import('./pages/PlaybooksPage'));
const WeeklyReviewPage = lazy(() => import('./pages/WeeklyReviewPage'));

interface AppUser {
  id: string;
  email: string;
  name: string;
  credits: number;
  is_admin: boolean;
  questionnaire_completed: boolean;
  org_id?: string;
  org_role?: string;
  phone?: string;
  [key: string]: unknown;
}

interface AuthContextType {
  token: string | null;
  user: AppUser | null;
  login: (tok: string, usr: AppUser) => void;
  logout: () => void;
  setCredits: (credits: number) => void;
  setUser: React.Dispatch<React.SetStateAction<AppUser | null>>;
}

const AuthContext = createContext<AuthContextType | null>(null);
export const useAuth = (): AuthContextType => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthContext.Provider");
  return ctx;
};

function InsufficientCreditsModal() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const handler = (e: CustomEvent) => {
      setMessage(e.detail || 'No active subscription. Subscribe to continue using the engine.');
      setOpen(true);
    };
    window.addEventListener('sdg-insufficient-credits', handler as EventListener);
    return () => window.removeEventListener('sdg-insufficient-credits', handler as EventListener);
  }, []);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-md rounded-2xl">
        <DialogHeader>
          <DialogTitle className="font-display text-xl font-normal">Need a subscription</DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground mt-1">
            {message}
          </DialogDescription>
        </DialogHeader>
        <div className="py-2 text-sm text-muted-foreground leading-relaxed">
          Subscribe to a plan to get 10M tokens per month and keep your conversations going.
        </div>
        <DialogFooter className="flex gap-2 sm:gap-3">
          <Button variant="outline" onClick={() => setOpen(false)} className="rounded-xl">
            Dismiss
          </Button>
          <Button onClick={() => { setOpen(false); navigate('/app/billing'); }} className="rounded-xl">
            View plans
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

const App: FC = () => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('sdg_token'));
  const [user, setUser] = useState<AppUser | null>(() => {
    try { return JSON.parse(localStorage.getItem('sdg_user') || 'null'); } catch { return null; }
  });

  useEffect(() => { setAuthToken(token); }, [token]);

  const login = useCallback((tok: string, usr: AppUser) => {
    localStorage.setItem('sdg_token', tok);
    localStorage.setItem('sdg_user', JSON.stringify(usr));
    setAuthToken(tok);
    setToken(tok);
    setUser(usr);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('sdg_token');
    localStorage.removeItem('sdg_user');
    localStorage.removeItem('sdg_last_thread');
    setAuthToken(null);
    setToken(null);
    setUser(null);
  }, []);

  const setCredits = useCallback((credits: number) => {
    setUser((u) => {
      if (!u) return u;
      const next = { ...u, credits };
      localStorage.setItem('sdg_user', JSON.stringify(next));
      return next;
    });
  }, []);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    const verify = (attempt: number) => {
      api.get<AppUser>('/auth/me').then((r) => {
        if (cancelled) return;
        setUser(r.data);
        localStorage.setItem('sdg_user', JSON.stringify(r.data));
      }).catch((err) => {
        if (cancelled) return;
        if (err?.response?.status === 401) { logout(); return; }
        if (attempt < 3) setTimeout(() => verify(attempt + 1), 1000 * Math.pow(2, attempt));
      });
    };
    verify(0);
    return () => { cancelled = true; };
  }, [token, logout]);

  useEffect(() => {
    const beat = () => api.post('/track/session', { session_id: sessionStorage.getItem('sdg_session') || null })
      .then((r: { data: { session_id: string } }) => sessionStorage.setItem('sdg_session', r.data.session_id))
      .catch(() => {});
    beat();
    const id = setInterval(beat, 60000);
    return () => clearInterval(id);
  }, [token]);

  useEffect(() => {
    if (!token || !user) return;
    const pending = localStorage.getItem('sdg_pending_invite');
    if (!pending || user.org_id) return;
    api.post('/org/join', { code: pending })
      .then((r: { data: { id: string; name: string; role: string } }) => {
        localStorage.removeItem('sdg_pending_invite');
        setUser((u) => (u ? { ...u, org_id: r.data.id, org_role: r.data.role } : u));
        toast.success(`You've joined ${r.data.name}.`);
      })
      .catch(() => { localStorage.removeItem('sdg_pending_invite'); });
  }, [token, user]);

  return (
    <AuthContext.Provider value={{ token, user, login, logout, setCredits, setUser }}>
      <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <div className="paper min-h-screen">
        <BrowserRouter>
          <InsufficientCreditsModal />
          <Suspense fallback={<div className="flex items-center justify-center min-h-screen bg-background"><div className="space-y-4 w-full max-w-md mx-auto px-6"><div className="h-8 w-3/5 animate-pulse rounded-lg bg-primary/10" /><div className="h-4 w-2/5 animate-pulse rounded-lg bg-primary/10" /><div className="mt-8 space-y-3"><div className="h-3 w-full animate-pulse rounded-lg bg-primary/10" /><div className="h-3 w-full animate-pulse rounded-lg bg-primary/10" /><div className="h-3 w-4/5 animate-pulse rounded-lg bg-primary/10" /></div></div></div>}>
          <Routes>
            <Route path="/" element={token ? <Navigate to="/app" replace /> : withErrorBoundary(LandingPage)({})} />
            <Route path="/auth" element={token ? <Navigate to="/app" replace /> : withErrorBoundary(AuthPage)({})} />
            <Route path="/app" element={token ? withErrorBoundary(JourneyPage)({}) : <Navigate to="/auth" replace />} />
            <Route path="/app/decisions" element={token ? withErrorBoundary(DecisionsPage)({}) : <Navigate to="/auth" replace />} />
            <Route path="/app/brain" element={token ? withErrorBoundary(BrainPage)({}) : <Navigate to="/auth" replace />} />
            <Route path="/app/brain/:decisionId" element={token ? withErrorBoundary(BrainPage)({}) : <Navigate to="/auth" replace />} />
            <Route path="/app/thread/:threadId" element={token ? withErrorBoundary(ThreadPage)({}) : <Navigate to="/auth" replace />} />
            <Route path="/app/team" element={token ? withErrorBoundary(TeamPage)({}) : <Navigate to="/auth" replace />} />
            <Route path="/app/my-tasks" element={token ? withErrorBoundary(MyTasksPage)({}) : <Navigate to="/auth" replace />} />
            <Route path="/app/cockpit" element={token ? withErrorBoundary(CockpitPage)({}) : <Navigate to="/auth" replace />} />
            <Route path="/app/mission-control" element={token ? withErrorBoundary(MissionControlPage)({}) : <Navigate to="/auth" replace />} />
            <Route path="/app/goal-setup" element={token ? withErrorBoundary(GoalSetupPage)({}) : <Navigate to="/auth" replace />} />
            <Route path="/app/founder-profile" element={token ? withErrorBoundary(ProfilePage)({}) : <Navigate to="/auth" replace />} />
            <Route path="/app/questionnaire" element={token ? withErrorBoundary(ProfilePage)({}) : <Navigate to="/auth" replace />} />
            <Route path="/app/profile" element={token ? withErrorBoundary(ProfilePage)({}) : <Navigate to="/auth" replace />} />
            <Route path="/join/:code" element={withErrorBoundary(JoinPage)({})} />
            <Route path="/d/:shareId" element={withErrorBoundary(DecisionCardPage)({})} />
            <Route path="/app/billing" element={token ? withErrorBoundary(BillingPage)({}) : <Navigate to="/auth" replace />} />
            <Route path="/pay/result" element={withErrorBoundary(PaymentResultPage)({})} />
            <Route path="/app/admin" element={token ? withErrorBoundary(AdminPage)({}) : <Navigate to="/auth" replace />} />
            <Route path="/app/habits" element={token ? withErrorBoundary(HabitsPage)({}) : <Navigate to="/auth" replace />} />
            <Route path="/app/playbooks" element={token ? withErrorBoundary(PlaybooksPage)({}) : <Navigate to="/auth" replace />} />
            <Route path="/app/weekly-review" element={token ? withErrorBoundary(WeeklyReviewPage)({}) : <Navigate to="/auth" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          </Suspense>
        </BrowserRouter>
        <Toaster position="bottom-right" />
      </div>
      </ThemeProvider>
    </AuthContext.Provider>
  );
}

export default App;
