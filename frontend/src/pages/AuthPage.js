import { useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { api } from '../lib/api';
import { useAuth } from '../App';

export default function AuthPage() {
  const { login } = useAuth();
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      const path = mode === 'login' ? '/auth/login' : '/auth/signup';
      const payload = mode === 'login' ? { email, password } : { email, password, name };
      const r = await api.post(path, payload);
      login(r.data.token, r.data.user);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Something went wrong. Try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="relative z-10 min-h-screen flex flex-col lg:flex-row">
      <div className="flex-1 flex items-center px-6 sm:px-12 lg:px-20 py-12 lg:py-0">
        <div className="max-w-lg">
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-6">SmartDecigen</p>
          <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl leading-[1.05] text-foreground">
            The distance between knowing and doing — closed.
          </h1>
          <p className="mt-6 text-sm md:text-base text-muted-foreground leading-6 max-w-md">
            A goal-anchored companion that holds your pursuit across weeks. Every conversation ends with one action. Every return begins with what changed.
          </p>
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center px-6 pb-16 lg:pb-0">
        <Card className="w-full max-w-md rounded-2xl premium-lift border border-border/70">
          <CardContent className="p-8">
            <h2 className="font-display text-2xl mb-1">{mode === 'login' ? 'Return to it' : 'Begin'}</h2>
            <p className="text-xs text-muted-foreground mb-6">
              {mode === 'login' ? 'Pick up where you left off.' : 'Name what you are pursuing. We hold the rest.'}
            </p>
            <form onSubmit={submit} className="space-y-4">
              {mode === 'signup' && (
                <div className="space-y-1.5">
                  <Label htmlFor="name" className="text-xs">Name</Label>
                  <Input id="name" data-testid="signup-name-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Optional" className="rounded-xl" />
                </div>
              )}
              <div className="space-y-1.5">
                <Label htmlFor="email" className="text-xs">Email</Label>
                <Input id="email" type="email" required data-testid={mode === 'login' ? 'login-email-input' : 'signup-email-input'}
                  value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@domain.com" className="rounded-xl" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="password" className="text-xs">Password</Label>
                <Input id="password" type="password" required minLength={6} data-testid={mode === 'login' ? 'login-password-input' : 'signup-password-input'}
                  value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 6 characters" className="rounded-xl" />
              </div>
              <Button type="submit" disabled={busy} data-testid="auth-submit-button"
                className="w-full rounded-xl active:scale-[0.98] transition-colors">
                {busy ? 'One moment…' : mode === 'login' ? 'Sign in' : 'Create account'}
              </Button>
            </form>
            <button type="button" data-testid="auth-mode-toggle"
              onClick={() => setMode(mode === 'login' ? 'signup' : 'login')}
              className="mt-5 text-xs text-muted-foreground hover:text-foreground transition-colors">
              {mode === 'login' ? 'No account yet? Create one' : 'Already have an account? Sign in'}
            </button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
