import { useState, useEffect, createContext, useContext, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from './components/ui/sonner';
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import NewGoalPage from './pages/NewGoalPage';
import ThreadPage from './pages/ThreadPage';
import BrainPage from './pages/BrainPage';
import AdminPage from './pages/AdminPage';
import BillingPage from './pages/BillingPage';
import TestCheckoutPage from './pages/TestCheckoutPage';
import PaymentResultPage from './pages/PaymentResultPage';
import { api, setAuthToken } from './lib/api';
import { trackPixel } from './lib/pixel';
import './App.css';

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  return (
    <AuthContext.Provider value={{ token, user, login, logout, setCredits, setUser }}>
      <div className="paper-noise min-h-screen">
        <BrowserRouter>
          <Routes>
            <Route path="/auth" element={token ? <Navigate to="/" replace /> : <AuthPage />} />
            <Route path="/" element={token ? <DashboardPage /> : <Navigate to="/auth" replace />} />
            <Route path="/new" element={token ? <NewGoalPage /> : <Navigate to="/auth" replace />} />
            <Route path="/thread/:threadId" element={token ? <ThreadPage /> : <Navigate to="/auth" replace />} />
            <Route path="/brain" element={token ? <BrainPage /> : <Navigate to="/auth" replace />} />
            <Route path="/billing" element={token ? <BillingPage /> : <Navigate to="/auth" replace />} />
            <Route path="/pay/test-checkout" element={token ? <TestCheckoutPage /> : <Navigate to="/auth" replace />} />
            <Route path="/pay/result" element={<PaymentResultPage />} />
            <Route path="/admin" element={token ? <AdminPage /> : <Navigate to="/auth" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
        <Toaster position="bottom-right" />
      </div>
    </AuthContext.Provider>
  );
}

export default App;
