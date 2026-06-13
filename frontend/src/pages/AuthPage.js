import { useState } from 'react';
import {
  ArrowRight, Target, CheckCircle2, RefreshCw,
  Sparkles, Lock, Mail, User, ShieldCheck
} from 'lucide-react';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { api } from '../lib/api';
import { useAuth } from '../App';

// Brand mark — stylised "S" matching the ad's geometric arrow/return motif.
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
  { num: '01', icon: Target,       label: 'One goal',     sub: 'The thing you keep avoiding.' },
  { num: '02', icon: CheckCircle2, label: 'One action',   sub: 'Easiest move for the next 48 h.' },
  { num: '03', icon: RefreshCw,    label: 'Real progress',sub: 'Kept promises. Not vibes.' },
];

const NEXT_STEPS = [
  'Name the goal you keep avoiding.',
  'Get the easiest next move, in plain English.',
  'Come back tomorrow. Tell it what happened.',
];

export default function AuthPage() {
  const { login } = useAuth();
  const [mode, setMode] = useState('signup');
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

  const isSignup = mode === 'signup';

  return (
    <div className="relative z-10 min-h-screen bg-background overflow-hidden">
      {/* warm sunrise aurora — depth without a photo */}
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div
          className="absolute -top-32 -right-40 w-[760px] h-[760px] rounded-full opacity-60"
          style={{ background: 'radial-gradient(circle, #f3d6a8 0%, rgba(243,214,168,0) 65%)' }}
        />
        <div
          className="absolute -bottom-40 -left-32 w-[640px] h-[640px] rounded-full opacity-40"
          style={{ background: 'radial-gradient(circle, #c9a86b 0%, rgba(201,168,107,0) 60%)' }}
        />
        <div
          className="absolute top-1/3 left-1/2 w-[420px] h-[420px] rounded-full opacity-25 -translate-x-1/2"
          style={{ background: 'radial-gradient(circle, #2f8f8a 0%, rgba(47,143,138,0) 60%)' }}
        />
      </div>

      <div className="relative max-w-7xl mx-auto px-6 sm:px-10 lg:px-14 py-8 lg:py-12 min-h-screen flex flex-col">
        {/* top brand bar */}
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2.5 text-foreground rise-1">
            <BrandMark size={26} />
            <span data-testid="brand-wordmark" className="text-sm tracking-[0.32em] font-semibold uppercase">SmartDecigen</span>
          </div>
          <div className="hidden md:flex items-center gap-2 text-[11px] tracking-[0.18em] uppercase text-muted-foreground rise-1">
            <ShieldCheck size={13} strokeWidth={2} className="text-[#b89165]" />
            <span>Decision AI · Built to be returned to</span>
          </div>
        </header>

        {/* hero split */}
        <div className="flex-1 grid lg:grid-cols-12 gap-10 lg:gap-16 mt-14 lg:mt-20 items-center pb-10">
          {/* LEFT: copy + pillars */}
          <div className="lg:col-span-7 max-w-2xl">
            <span className="rise-1 inline-flex items-center gap-2 text-[11px] tracking-[0.26em] uppercase text-[#b89165] font-semibold mb-7">
              <span className="w-7 h-px bg-[#b89165]" />
              The Decision AI
            </span>

            <h1 className="rise-1 font-display text-5xl sm:text-6xl lg:text-[5.5rem] leading-[0.95] text-foreground tracking-tight">
              You already
              <br />know what
              <br />to do.
            </h1>

            <div className="rise-2 mt-8 flex items-start gap-4">
              <div className="hidden sm:block w-10 h-px bg-[#b89165] mt-3" />
              <p className="font-display text-2xl md:text-[26px] leading-[1.25] text-[#b89165] max-w-md">
                <span className="font-semibold">SmartDeciGen</span> helps you actually do it.
              </p>
            </div>

            {/* numbered pillars */}
            <ul className="rise-3 mt-12 grid sm:grid-cols-3 gap-6 sm:gap-8 max-w-2xl">
              {PILLARS.map(({ num, icon: Icon, label, sub }) => (
                <li key={label} className="group">
                  <div className="flex items-center gap-2 text-[10px] tracking-[0.3em] text-[#b89165] font-semibold mb-2">
                    <span>{num}</span>
                    <span className="w-3 h-px bg-[#b89165]/50" />
                    <Icon size={12} strokeWidth={2.5} />
                  </div>
                  <div className="font-display text-xl text-foreground">{label}.</div>
                  <div className="text-xs text-muted-foreground mt-1.5 leading-relaxed">{sub}</div>
                </li>
              ))}
            </ul>

            <p className="rise-4 mt-14 text-xs text-muted-foreground tracking-wide italic">
              Return to it. Keep moving forward.
            </p>
          </div>

          {/* RIGHT: premium inline signup card */}
          <div className="lg:col-span-5 rise-3">
            <div
              data-testid="auth-card"
              className="relative bg-white border border-border/60 rounded-3xl p-7 sm:p-8 premium-lift overflow-hidden"
            >
              {/* gold corner glow */}
              <div
                className="absolute -top-20 -right-20 w-48 h-48 rounded-full pointer-events-none"
                style={{ background: 'radial-gradient(circle, rgba(184,145,101,0.20) 0%, rgba(184,145,101,0) 70%)' }}
                aria-hidden="true"
              />

              {/* mode toggle */}
              <div className="relative flex items-center gap-1 p-1 bg-[hsl(var(--accent))]/40 rounded-full mb-6 w-fit text-xs">
                <button
                  type="button"
                  data-testid="auth-mode-signup"
                  onClick={() => setMode('signup')}
                  className={`px-4 py-1.5 font-medium rounded-full transition-all ${isSignup ? 'bg-foreground text-background shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
                >
                  Start free
                </button>
                <button
                  type="button"
                  data-testid="auth-mode-login"
                  onClick={() => setMode('login')}
                  className={`px-4 py-1.5 font-medium rounded-full transition-all ${!isSignup ? 'bg-foreground text-background shadow-sm' : 'text-muted-foreground hover:text-foreground'}`}
                >
                  Sign in
                </button>
              </div>

              <h2 className="relative font-display text-[28px] leading-tight mb-1">
                {isSignup ? 'Start free.' : 'Welcome back.'}
              </h2>
              <p className="relative text-xs text-muted-foreground mb-6 flex items-center gap-1.5">
                {isSignup ? (
                  <>
                    <Sparkles size={11} className="text-[#b89165]" />
                    <span>100 free credits · No card · ~30 seconds</span>
                  </>
                ) : (
                  <span>Pick up the thread you left.</span>
                )}
              </p>

              <form onSubmit={submit} className="relative space-y-3">
                {isSignup && (
                  <div className="relative">
                    <User size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground/60" />
                    <Input
                      data-testid="signup-name-input"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Your name (optional)"
                      className="rounded-xl pl-10 h-12"
                    />
                  </div>
                )}
                <div className="relative">
                  <Mail size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground/60" />
                  <Input
                    type="email"
                    required
                    data-testid={isSignup ? 'signup-email-input' : 'login-email-input'}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@domain.com"
                    className="rounded-xl pl-10 h-12"
                  />
                </div>
                <div className="relative">
                  <Lock size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground/60" />
                  <Input
                    type="password"
                    required
                    minLength={6}
                    data-testid={isSignup ? 'signup-password-input' : 'login-password-input'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={isSignup ? 'Pick a password (6+ chars)' : 'Your password'}
                    className="rounded-xl pl-10 h-12"
                  />
                </div>
                <Button
                  type="submit"
                  disabled={busy}
                  data-testid="auth-submit-button"
                  className="w-full rounded-xl h-12 text-sm font-medium group mt-3 active:scale-[0.99] transition-transform"
                >
                  {busy ? 'One moment…' : (
                    <span className="flex items-center justify-center gap-2">
                      {isSignup ? 'Start Free' : 'Sign in'}
                      <ArrowRight size={15} strokeWidth={2} className="transition-transform group-hover:translate-x-0.5" />
                    </span>
                  )}
                </Button>
              </form>

              {isSignup && (
                <div className="relative mt-7 pt-6 border-t border-border/60">
                  <div className="flex items-center gap-1.5 mb-3.5">
                    <Sparkles size={11} className="text-[#b89165]" />
                    <span className="text-[10px] tracking-[0.22em] font-semibold uppercase text-[#b89165]">
                      What happens next
                    </span>
                  </div>
                  <ol className="space-y-2.5">
                    {NEXT_STEPS.map((step, i) => (
                      <li key={i} className="flex items-start gap-3 text-[13px] text-foreground/80 leading-relaxed">
                        <span className="w-5 h-5 rounded-full bg-foreground/[0.06] text-foreground/70 text-[10px] font-semibold flex items-center justify-center shrink-0 mt-0.5">
                          {i + 1}
                        </span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}

              <div className="relative mt-6 flex items-center justify-center gap-2.5 text-[10px] text-muted-foreground/85 tracking-wide">
                <span className="inline-flex items-center gap-1"><ShieldCheck size={11} className="text-[#b89165]" /> Privacy-first</span>
                <span className="w-1 h-1 rounded-full bg-muted-foreground/40" />
                <span>No spam</span>
                <span className="w-1 h-1 rounded-full bg-muted-foreground/40" />
                <span>Cancel anytime</span>
              </div>
            </div>

            <p className="text-center mt-5 text-[11px] text-muted-foreground/80 leading-5 max-w-sm mx-auto">
              For people who already know what to do — and are tired of not doing it.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
