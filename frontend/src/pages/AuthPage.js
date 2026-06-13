import { useState } from 'react';
import { ArrowRight, Target, CheckCircle2, RefreshCw } from 'lucide-react';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogTrigger } from '../components/ui/dialog';
import { toast } from 'sonner';
import { api } from '../lib/api';
import { useAuth } from '../App';

// Brand mark — stylised "S" matching the ad's geometric arrow/return motif (navy on cream).
const BrandMark = ({ size = 28 }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
    <path
      d="M22 8.5 A7 7 0 0 0 10 8.5 Q10 13 16 15.5 Q22 18 22 22.5 A7 7 0 0 1 10 22.5"
      stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" fill="none"
    />
    <path d="M9 21 L11 22.7 L9 24.4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
  </svg>
);

const PILLARS = [
  { icon: Target, label: 'One goal.' },
  { icon: CheckCircle2, label: 'One action.' },
  { icon: RefreshCw, label: 'Real progress.' },
];

function AuthForm({ initialMode = 'signup', onAuthed }) {
  const { login } = useAuth();
  const [mode, setMode] = useState(initialMode);
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
      onAuthed?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Something went wrong. Try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div data-testid="auth-form-card">
      <h2 className="font-display text-2xl mb-1 text-foreground">{mode === 'login' ? 'Return to it' : 'Start free'}</h2>
      <p className="text-xs text-muted-foreground mb-6">
        {mode === 'login' ? 'Pick up where you left off.' : '20 free credits on signup — no card required.'}
      </p>
      <form onSubmit={submit} className="space-y-4">
        {mode === 'signup' && (
          <div className="space-y-1.5">
            <Label htmlFor="name" className="text-xs">Name <span className="text-muted-foreground">· optional</span></Label>
            <Input id="name" data-testid="signup-name-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="What should the engine call you?" className="rounded-xl" />
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
          className="w-full rounded-xl active:scale-[0.98] transition-all h-11 text-sm group">
          {busy ? 'One moment…' : (
            <span className="flex items-center justify-center gap-2">
              {mode === 'login' ? 'Sign in' : 'Start Free'}
              <ArrowRight size={15} strokeWidth={2} className="transition-transform group-hover:translate-x-0.5" />
            </span>
          )}
        </Button>
      </form>
      <button type="button" data-testid="auth-mode-toggle"
        onClick={() => setMode(mode === 'login' ? 'signup' : 'login')}
        className="mt-5 text-xs text-muted-foreground hover:text-foreground transition-colors w-full text-center">
        {mode === 'login' ? 'No account yet? Start free →' : 'Already with us? Sign in'}
      </button>
    </div>
  );
}

export default function AuthPage() {
  const [open, setOpen] = useState(false);
  const [dialogMode, setDialogMode] = useState('signup');

  const openWith = (m) => { setDialogMode(m); setOpen(true); };

  return (
    <div className="relative z-10 min-h-screen flex flex-col lg:flex-row bg-background">
      {/* LEFT: brand + ad message + pillars + CTA */}
      <div className="flex-1 flex items-center px-6 sm:px-12 lg:px-20 py-12 lg:py-0">
        <div className="max-w-xl w-full">
          <div className="flex items-center gap-2.5 text-foreground mb-12 lg:mb-16">
            <BrandMark size={26} />
            <span data-testid="brand-wordmark" className="text-sm tracking-[0.32em] font-semibold uppercase">SmartDecigen</span>
          </div>

          <h1 className="font-display text-5xl sm:text-6xl lg:text-7xl leading-[0.95] text-foreground tracking-tight">
            You already
            <br />know what
            <br />to do.
          </h1>

          <div className="mt-8 flex items-start gap-4">
            <div className="hidden sm:block w-10 h-px bg-[#b89165] mt-3" aria-hidden="true" />
            <p className="font-display text-2xl md:text-[26px] leading-[1.25] text-[#b89165] max-w-sm">
              <span className="font-semibold">SmartDeciGen</span> helps you actually do it.
            </p>
          </div>

          <ul className="mt-10 space-y-3 max-w-sm">
            {PILLARS.map(({ icon: Icon, label }, i) => (
              <li key={label} className={`flex items-center gap-3 ${i < PILLARS.length - 1 ? 'pb-3 border-b border-border/60' : ''}`}>
                <span className="flex items-center justify-center w-7 h-7 rounded-full border border-foreground/30 text-foreground">
                  <Icon size={13} strokeWidth={2} />
                </span>
                <span className="text-sm md:text-base text-foreground/85">{label}</span>
              </li>
            ))}
          </ul>

          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button
                data-testid="start-free-cta"
                onClick={() => openWith('signup')}
                className="mt-10 h-14 px-8 rounded-2xl text-base font-medium bg-foreground text-background hover:bg-foreground/90 active:scale-[0.99] transition-all group inline-flex items-center gap-6 min-w-[260px] justify-between"
              >
                <span>Start Free</span>
                <ArrowRight size={18} strokeWidth={2} className="transition-transform group-hover:translate-x-1" />
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-md rounded-2xl border-border/70 bg-white p-7">
              <AuthForm initialMode={dialogMode} onAuthed={() => setOpen(false)} />
            </DialogContent>
          </Dialog>

          <p className="mt-6 text-xs text-muted-foreground tracking-wide">Return to it. Keep moving forward.</p>

          <button
            type="button"
            data-testid="open-signin-link"
            onClick={() => openWith('login')}
            className="mt-3 text-xs text-foreground/60 hover:text-foreground transition-colors underline underline-offset-4"
          >
            Already with us? Sign in
          </button>
        </div>
      </div>

      {/* RIGHT: coded cliff/sunrise scene with ACTION flag — no external image */}
      <div className="relative flex-1 min-h-[440px] lg:min-h-screen overflow-hidden" data-testid="hero-cliff-scene">
        <div className="hero-scene">
          <div className="mountains" aria-hidden="true" />
          <div className="left-cliff" aria-hidden="true" />
          <div className="right-cliff" aria-hidden="true" />
          <div className="person" aria-hidden="true" />
          <svg className="action-line" viewBox="0 0 1000 24" preserveAspectRatio="none" aria-hidden="true">
            <line x1="10" y1="12" x2="990" y2="12" stroke="#0a0e15" strokeWidth="3" strokeDasharray="16 14" strokeLinecap="round" />
          </svg>
          <div className="flag-group" data-testid="action-flag">
            <span>ACTION</span>
            <span className="flag-icon" aria-hidden="true" />
          </div>
          <div className="seam-fade" aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}
