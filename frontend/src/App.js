import { useState, useEffect, createContext, useContext, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { Toaster } from './components/ui/sonner';
import { Button } from './components/ui/button';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from './components/ui/dialog';
import LandingPage from './pages/LandingPage';
import AuthPage from './pages/AuthPage';
import JourneyPage from './pages/JourneyPage';
import NewGoalPage from './pages/NewGoalPage';
import ThreadPage from './pages/ThreadPage';
import BrainPage from './pages/BrainPage';
import DecisionsPage from './pages/DecisionsPage';
import AdminPage from './pages/AdminPage';
import BillingPage from './pages/BillingPage';
import TestCheckoutPage from './pages/TestCheckoutPage';
import PaymentResultPage from './pages/PaymentResultPage';
import TeamPage from './pages/TeamPage';
import JoinPage from './pages/JoinPage';
import CockpitPage from './pages/CockpitPage';
import MyTasksPage from './pages/MyTasksPage';
import GoalSetupPage from './pages/GoalSetupPage';
import FounderProfilePage from './pages/FounderProfilePage';
import DecisionCardPage from './pages/DecisionCardPage';
import QuestionnairePage from './pages/QuestionnairePage';
import { api, setAuthToken } from './lib/api';
import { trackPixel } from './lib/pixel';
import { toast } from 'sonner';
import './App.css';

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

function InsufficientCreditsModal() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    const handler = (e) => {
      setMessage(e.detail || 'No active subscription. Subscribe to continue using the engine.');
      setOpen(true);
    };
    window.addEventListener('sdg-insufficient-credits', handler);
    return () => window.removeEventListener('sdg-insufficient-credits', handler);
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

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('sdg_token'));
  const [user, setUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('sdg_user') || 'null'); } catch { return null; }
  });

  useEffect(() => { setAuthToken(token); }, [token]);

  const login = useCallback((tok, usr) => {
    localStorage.setItem('sdg_token', tok);
    localStorage.setItem('sdg_user', JSON.stringify(usr));
    setAuthToken(tok);
    setToken(tok);
    setUser(usr);
    // Meta Pixel: signup -> Lead. We detect a brand-new account by the absence of a
    // completed questionnaire AND credits matching the fresh-signup grant. For login,
    // questionnaire_completed will typically already be true OR credits will have moved.
    try {
      const isFreshSignup = usr && usr.questionnaire_completed === false;
      if (isFreshSignup) {
        trackPixel('Lead', { content_name: 'signup', value: 0, currency: 'INR' });
      }
    } catch (_e) { /* noop */ }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('sdg_token');
    localStorage.removeItem('sdg_user');
    localStorage.removeItem('sdg_last_thread');
    setAuthToken(null);
    setToken(null);
    setUser(null);
  }, []);

  const setCredits = useCallback((credits) => {
    setUser((u) => {
      if (!u) return u;
      const next = { ...u, credits };
      localStorage.setItem('sdg_user', JSON.stringify(next));
      return next;
    });
  }, []);

  useEffect(() => {
    if (!token) return;
    api.get('/auth/me').then((r) => {
      setUser(r.data);
      localStorage.setItem('sdg_user', JSON.stringify(r.data));
    }).catch(() => logout());
  }, [token]);

  // traffic heartbeat: one session per visit, refreshed every 60s (time-spent tracking)
  useEffect(() => {
    const beat = () => api.post('/track/session', { session_id: sessionStorage.getItem('sdg_session') || null })
      .then((r) => sessionStorage.setItem('sdg_session', r.data.session_id))
      .catch(() => {});
    beat();
    const id = setInterval(beat, 60000);
    return () => clearInterval(id);
  }, [token]);

  // join-link fallback: if a user signed in/up after opening an invite link, finish the join
  useEffect(() => {
    if (!token || !user) return;
    const pending = localStorage.getItem('sdg_pending_invite');
    if (!pending || user.org_id) return;
    api.post('/org/join', { code: pending })
      .then((r) => {
        localStorage.removeItem('sdg_pending_invite');
        setUser((u) => (u ? { ...u, org_id: r.data.id, org_role: r.data.role } : u));
        toast.success(`You've joined ${r.data.name}.`);
      })
      .catch(() => { localStorage.removeItem('sdg_pending_invite'); });
  }, [token, user]);

  return (
    <AuthContext.Provider value={{ token, user, login, logout, setCredits, setUser }}>
      <div className="paper-noise min-h-screen">
        <BrowserRouter>
          <InsufficientCreditsModal />
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/auth" element={token ? <Navigate to="/app" replace /> : <AuthPage />} />
            <Route path="/app" element={token ? <JourneyPage /> : <Navigate to="/auth" replace />} />
            <Route path="/app/decisions" element={token ? <DecisionsPage /> : <Navigate to="/auth" replace />} />
            <Route path="/app/brain" element={token ? <BrainPage /> : <Navigate to="/auth" replace />} />
            <Route path="/app/brain/:decisionId" element={token ? <BrainPage /> : <Navigate to="/auth" replace />} />
            <Route path="/app/new" element={token ? <NewGoalPage /> : <Navigate to="/auth" replace />} />
            <Route path="/app/thread/:threadId" element={token ? <ThreadPage /> : <Navigate to="/auth" replace />} />
            <Route path="/app/team" element={token ? <TeamPage /> : <Navigate to="/auth" replace />} />
            <Route path="/app/my-tasks" element={token ? <MyTasksPage /> : <Navigate to="/auth" replace />} />
            <Route path="/app/cockpit" element={token ? <CockpitPage /> : <Navigate to="/auth" replace />} />
            <Route path="/app/goal-setup" element={token ? <GoalSetupPage /> : <Navigate to="/auth" replace />} />
            <Route path="/app/founder-profile" element={token ? <FounderProfilePage /> : <Navigate to="/auth" replace />} />
            <Route path="/join/:code" element={<JoinPage />} />
            <Route path="/d/:shareId" element={<DecisionCardPage />} />
            <Route path="/app/billing" element={token ? <BillingPage /> : <Navigate to="/auth" replace />} />
            <Route path="/app/pay/test-checkout" element={token ? <TestCheckoutPage /> : <Navigate to="/auth" replace />} />
            <Route path="/pay/result" element={<PaymentResultPage />} />
            <Route path="/app/questionnaire" element={token ? <QuestionnairePage /> : <Navigate to="/auth" replace />} />
            <Route path="/app/admin" element={token ? <AdminPage /> : <Navigate to="/auth" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="bottom-right" />
      </div>
    </AuthContext.Provider>
  );
}

export default App;
