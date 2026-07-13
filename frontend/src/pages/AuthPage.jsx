import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight, Target, CheckCircle2, RefreshCw,
  Sparkles, Lock, Mail, User, ShieldCheck, ArrowLeft,
} from 'lucide-react';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { api } from '../lib/api';
import { useAuth } from '../App';

const BrandMark = ({ size = 28 }) => (
  <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden="true">
    <path d="M22 8.5 A7 7 0 0 0 10 8.5 Q10 13 16 15.5 Q22 18 22 22.5 A7 7 0 0 1 10 22.5" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" fill="none" />
    <path d="M9 21 L11 22.7 L9 24.4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
  </svg>
);

const PILLARS = [
  { num: '01', icon: Target, label: 'One goal', sub: 'The thing you keep avoiding.' },
  { num: '02', icon: CheckCircle2, label: 'One action', sub: 'Easiest move for the next 48 h.' },
  { num: '03', icon: RefreshCw, label: 'Real progress', sub: 'Kept promises. Not vibes.' },
];

export default function AuthPage() {
  const { login } = useAuth();
  const refCode = new URLSearchParams(window.location.search).get('ref') || '';
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [emailMode, setEmailMode] = useState('signup');
  const [busy, setBusy] = useState(false);

  const submitEmail = async (e) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      const path = emailMode === 'login' ? '/auth/login' : '/auth/signup';
      const payload = emailMode === 'login'
        ? { email, password }
        : { email, password, name, ...(refCode ? { ref: refCode } : {}) };
      const r = await api.post(path, payload);
      login(r.data.token, r.data.user);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Something went wrong.');
    } finally { setBusy(false); }
  };

  return (
    <div className="relative z-10 min-h-screen bg-background overflow-hidden">
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute -top-32 -right-40 w-[760px] h-[760px] rounded-full opacity-60"
          style={{ background: 'radial-gradient(circle, #f3d6a8 0%, rgba(243,214,168,0) 65%)' }} />
        <div className="absolute -bottom-40 -left-32 w-[640px] h-[640px] rounded-full opacity-40"
          style={{ background: 'radial-gradient(circle, #c9a86b 0%, rgba(201,168,107,0) 60%)' }} />
        <div className="absolute top-1/3 left-1/2 w-[420px] h-[420px] rounded-full opacity-25 -translate-x-1/2"
          style={{ background: 'radial-gradient(circle, #2f8f8a 0%, rgba(47,143,138,0) 60%)' }} />
      </div>

      <div className="relative max-w-7xl mx-auto px-6 sm:px-10 lg:px-14 py-8 lg:py-12 min-h-screen flex flex-col">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-2.5 text-foreground rise-1">
            <button onClick={() => navigate('/')} className="flex items-center gap-2.5">
              <BrandMark size={26} />
              <span className="text-sm tracking-[0.32em] font-semibold uppercase">SmartDecigen</span>
            </button>
            <span className="w-px h-4 bg-border/60 mx-2" />
            <button onClick={() => navigate('/')} className="flex items-center gap-1 text-[11px] text-muted-foreground/70 hover:text-foreground transition-colors">
              <ArrowLeft size={12} strokeWidth={2} /> Back to home
            </button>
          </div>
          <div className="hidden md:flex items-center gap-2 text-[11px] tracking-[0.18em] uppercase text-muted-foreground rise-1">
            <ShieldCheck size={13} strokeWidth={2} className="text-[#b89165]" />
            <span>AI Chief of Staff · Built to be returned to</span>
          </div>
        </header>

        <div className="flex-1 grid lg:grid-cols-12 gap-10 lg:gap-16 mt-14 lg:mt-20 items-center pb-10">
          <div className="lg:col-span-7 max-w-2xl">
            <span className="rise-1 inline-flex items-center gap-2 text-[11px] tracking-[0.26em] uppercase text-[#b89165] font-semibold mb-7">
              <span className="w-7 h-px bg-[#b89165]" />
              AI Chief of Staff
            </span>
            <h1 className="rise-1 font-display text-5xl sm:text-6xl lg:text-[5.5rem] leading-[0.95] text-foreground tracking-tight">
              For founders who are<br />tired of guessing.
            </h1>
            <div className="rise-2 mt-8 flex items-start gap-4">
              <div className="hidden sm:block w-10 h-px bg-[#b89165] mt-3" />
              <p className="font-display text-2xl md:text-[26px] leading-[1.25] text-[#b89165] max-w-md">
                <span className="font-semibold">SmartDeciGen</span> pressure-tests your decisions and holds you accountable.
              </p>
            </div>
            <ul className="rise-3 mt-12 grid sm:grid-cols-3 gap-6 sm:gap-8 max-w-2xl">
              {PILLARS.map(({ num, icon: Icon, label, sub }, idx) => (
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

          <div className="lg:col-span-5 rise-3">
            <div className="relative bg-white border border-border/60 rounded-3xl p-7 sm:p-8 premium-lift overflow-hidden">
              <div className="absolute -top-20 -right-20 w-48 h-48 rounded-full pointer-events-none"
                style={{ background: 'radial-gradient(circle, rgba(184,145,101,0.20) 0%, rgba(184,145,101,0) 70%)' }}
                aria-hidden="true" />

              <h2 className="relative font-display text-[28px] leading-tight mb-1">
                Try free.
              </h2>
              <p className="relative text-xs text-muted-foreground mb-6 flex items-center gap-1.5">
                <Sparkles size={11} className="text-[#b89165]" />
                <span>50 decisions on us. No card. ~30 seconds.</span>
              </p>

              {refCode ? (
                <div className="relative mb-4 rounded-xl border border-emerald-300/60 bg-emerald-50 px-3 py-2 text-xs text-emerald-800">
                  A founder invited you. You will both get a bonus when you sign up.
                </div>
              ) : null}

              <form onSubmit={submitEmail} className="space-y-3">
                {emailMode === 'signup' && (
                  <div className="relative">
                    <User size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground/60" />
                    <Input value={name} onChange={(e) => setName(e.target.value)}
                      placeholder="Your name (optional)" className="rounded-xl pl-10 h-12" />
                  </div>
                )}
                <div className="relative">
                  <Mail size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground/60" />
                  <Input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@domain.com" className="rounded-xl pl-10 h-12" />
                </div>
                <div className="relative">
                  <Lock size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground/60" />
                  <Input type="password" required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)}
                    placeholder={emailMode === 'signup' ? 'Pick a password (6+ chars)' : 'Your password'}
                    className="rounded-xl pl-10 h-12" />
                </div>
                <Button type="submit" disabled={busy}
                  className="w-full rounded-xl h-12 text-sm font-medium mt-3 active:scale-[0.99]">
                  {busy ? 'One moment\u2026' : (emailMode === 'signup' ? 'Start Free' : 'Sign in')}
                </Button>
                <div className="flex items-center justify-between mt-2">
                  <button type="button" onClick={() => setEmailMode(emailMode === 'signup' ? 'login' : 'signup')}
                    className="text-[11px] text-muted-foreground hover:text-foreground underline">
                    {emailMode === 'signup' ? 'Already have an account?' : 'Create a new account'}
                  </button>
                </div>
                {emailMode === 'login' && (
                  <div className="text-center mt-1">
                    <button type="button" onClick={() => toast.message('Contact support at ceo@smartdecigen.com to reset your password.')}
                      className="text-[11px] text-muted-foreground hover:text-foreground underline">
                      Forgot password?
                    </button>
                  </div>
                )}
              </form>

              <div className="relative mt-6 flex items-center justify-center gap-2.5 text-[10px] text-muted-foreground/85 tracking-wide">
                <span className="inline-flex items-center gap-1"><ShieldCheck size={11} className="text-[#b89165]" /> Privacy-first</span>
                <span className="w-1 h-1 rounded-full bg-muted-foreground/40" />
                <span>No spam</span>
                <span className="w-1 h-1 rounded-full bg-muted-foreground/40" />
                <span>Cancel anytime</span>
              </div>
            </div>
            <p className="text-center mt-5 text-[11px] text-muted-foreground/80 leading-5 max-w-sm mx-auto">
              For founders who are tired of guessing — and ready to decide.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
