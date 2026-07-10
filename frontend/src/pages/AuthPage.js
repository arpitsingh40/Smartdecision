import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight, Target, CheckCircle2, RefreshCw,
  Sparkles, Lock, Mail, User, ShieldCheck, Phone, ArrowLeft,
} from 'lucide-react';
import { Input } from '../components/ui/input';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import { api } from '../lib/api';
import { useAuth } from '../App';
import { auth, RecaptchaVerifier, signInWithPhoneNumber } from '../lib/firebase';

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
  { num: '01', icon: Target, label: 'One goal', sub: 'The thing you keep avoiding.' },
  { num: '02', icon: CheckCircle2, label: 'One action', sub: 'Easiest move for the next 48 h.' },
  { num: '03', icon: RefreshCw, label: 'Real progress', sub: 'Kept promises. Not vibes.' },
];

function PhoneAuthForm({ onSuccess, refCode }) {
  const [phone, setPhone] = useState('');
  const [otp, setOtp] = useState('');
  const [otpSent, setOtpSent] = useState(false);
  const [name, setName] = useState('');
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState(null);
  const [useEmail, setUseEmail] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [emailMode, setEmailMode] = useState('signup');
  const [emailBusy, setEmailBusy] = useState(false);
  const recaptchaRef = useRef(null);

  const sendOtp = async () => {
    const cleaned = phone.trim();
    if (!cleaned || cleaned.length < 10) { toast.error('Enter a valid phone number.'); return; }
    const full = cleaned.startsWith('+') ? cleaned : `+91${cleaned}`;
    setBusy(true);
    try {
      if (!recaptchaRef.current) {
        recaptchaRef.current = new RecaptchaVerifier(auth, 'recaptcha-container', { size: 'invisible' });
      }
      const confirmation = await signInWithPhoneNumber(auth, full, recaptchaRef.current);
      setConfirm(confirmation);
      setOtpSent(true);
      toast.success('OTP sent to your phone.');
    } catch (err) {
      toast.error(err.message || 'Could not send OTP. Try again.');
    } finally { setBusy(false); }
  };

  const verifyOtp = async () => {
    if (!otp.trim()) { toast.error('Enter the OTP you received.'); return; }
    setBusy(true);
    try {
      const result = await confirm.confirm(otp);
      const idToken = await result.user.getIdToken();
      const r = await api.post('/auth/firebase', { id_token: idToken, name: name.trim(), ref: refCode || '' });
      onSuccess(r.data.token, { ...r.data.user, phone: result.user.phoneNumber });
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Invalid OTP. Try again.');
    } finally { setBusy(false); }
  };

  const submitEmail = async (e) => {
    e.preventDefault();
    if (emailBusy) return;
    setEmailBusy(true);
    try {
      const path = emailMode === 'login' ? '/auth/login' : '/auth/signup';
      const payload = emailMode === 'login'
        ? { email, password }
        : { email, password, name, ...(refCode ? { ref: refCode } : {}) };
      const r = await api.post(path, payload);
      onSuccess(r.data.token, r.data.user);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Something went wrong.');
    } finally { setEmailBusy(false); }
  };

  if (useEmail) {
    return (
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
        <Button type="submit" disabled={emailBusy}
          className="w-full rounded-xl h-12 text-sm font-medium mt-3 active:scale-[0.99]">
          {emailBusy ? 'One moment\u2026' : (emailMode === 'signup' ? 'Start Free' : 'Sign in')}
        </Button>
        <div className="flex items-center justify-between mt-2">
          <button type="button" onClick={() => setEmailMode(emailMode === 'signup' ? 'login' : 'signup')}
            className="text-[11px] text-muted-foreground hover:text-foreground underline">
            {emailMode === 'signup' ? 'Already have an account?' : 'Create a new account'}
          </button>
          <button type="button" onClick={() => setUseEmail(false)}
            className="text-[11px] text-muted-foreground hover:text-foreground underline">
            Use phone instead
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
    );
  }

  return (
    <div className="space-y-3">
      <div id="recaptcha-container" />
      {!otpSent ? (
        <>
          <div className="relative">
            <Phone size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground/60" />
            <Input type="tel" value={phone} onChange={(e) => setPhone(e.target.value)}
              placeholder="Phone number (e.g. 9876543210)" className="rounded-xl pl-10 h-12" />
          </div>
          <div className="relative">
            <User size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground/60" />
            <Input value={name} onChange={(e) => setName(e.target.value)}
              placeholder="Your name (optional)" className="rounded-xl pl-10 h-12" />
          </div>
          <Button onClick={sendOtp} disabled={busy || !phone.trim()}
            className="w-full rounded-xl h-12 text-sm font-medium mt-3 active:scale-[0.99]">
            {busy ? 'Sending\u2026' : 'Send OTP'}
          </Button>
        </>
      ) : (
        <>
          <p className="text-sm text-muted-foreground">Enter the OTP sent to {phone}</p>
          <div className="relative">
            <Lock size={14} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted-foreground/60" />
            <Input type="text" inputMode="numeric" value={otp} onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
              placeholder="Enter OTP" maxLength={6} className="rounded-xl pl-10 h-12 text-lg tracking-[0.3em]" />
          </div>
          <Button onClick={verifyOtp} disabled={busy || otp.length < 4}
            className="w-full rounded-xl h-12 text-sm font-medium mt-3 active:scale-[0.99]">
            {busy ? 'Verifying\u2026' : 'Verify & continue'}
          </Button>
          <button type="button" onClick={() => { setOtpSent(false); setOtp(''); }}
            className="text-[11px] text-muted-foreground hover:text-foreground underline mx-auto block mt-2">
            Change phone number
          </button>
        </>
      )}
      <div className="text-center mt-2">
        <button type="button" onClick={() => setUseEmail(true)}
          className="text-[11px] text-muted-foreground hover:text-foreground underline">
          Use email instead
        </button>
      </div>
    </div>
  );
}

export default function AuthPage() {
  const { login } = useAuth();
  const refCode = new URLSearchParams(window.location.search).get('ref') || '';
  const navigate = useNavigate();

  const onSuccess = (token, user) => {
    login(token, user);
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
              <span data-testid="brand-wordmark" className="text-sm tracking-[0.32em] font-semibold uppercase">SmartDecigen</span>
            </button>
            <span className="w-px h-4 bg-border/60 mx-2" />
            <button onClick={() => navigate('/')} className="flex items-center gap-1 text-[11px] text-muted-foreground/70 hover:text-foreground transition-colors">
              <ArrowLeft size={12} strokeWidth={2} /> Back to home
            </button>
          </div>
          <div className="hidden md:flex items-center gap-2 text-[11px] tracking-[0.18em] uppercase text-muted-foreground rise-1">
            <ShieldCheck size={13} strokeWidth={2} className="text-[#b89165]" />
            <span>Decision AI · Built to be returned to</span>
          </div>
        </header>

        <div className="flex-1 grid lg:grid-cols-12 gap-10 lg:gap-16 mt-14 lg:mt-20 items-center pb-10">
          <div className="lg:col-span-7 max-w-2xl">
            <span className="rise-1 inline-flex items-center gap-2 text-[11px] tracking-[0.26em] uppercase text-[#b89165] font-semibold mb-7">
              <span className="w-7 h-px bg-[#b89165]" />
              The Decision AI
            </span>
            <h1 className="rise-1 font-display text-5xl sm:text-6xl lg:text-[5.5rem] leading-[0.95] text-foreground tracking-tight">
              You already<br />know what<br />to do.
            </h1>
            <div className="rise-2 mt-8 flex items-start gap-4">
              <div className="hidden sm:block w-10 h-px bg-[#b89165] mt-3" />
              <p className="font-display text-2xl md:text-[26px] leading-[1.25] text-[#b89165] max-w-md">
                <span className="font-semibold">SmartDeciGen</span> helps you actually do it.
              </p>
            </div>
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

          <div className="lg:col-span-5 rise-3">
            <div data-testid="auth-card"
              className="relative bg-white border border-border/60 rounded-3xl p-7 sm:p-8 premium-lift overflow-hidden">
              <div className="absolute -top-20 -right-20 w-48 h-48 rounded-full pointer-events-none"
                style={{ background: 'radial-gradient(circle, rgba(184,145,101,0.20) 0%, rgba(184,145,101,0) 70%)' }}
                aria-hidden="true" />

              <h2 className="relative font-display text-[28px] leading-tight mb-1">
                Get started.
              </h2>
              <p className="relative text-xs text-muted-foreground mb-6 flex items-center gap-1.5">
                <Sparkles size={11} className="text-[#b89165]" />
                <span>Enter your phone to receive a one-time code</span>
              </p>

              {refCode ? (
                <div className="relative mb-4 rounded-xl border border-emerald-300/60 bg-emerald-50 px-3 py-2 text-xs text-emerald-800" data-testid="referral-banner">
                  A founder invited you. You will both get a bonus when you sign up.
                </div>
              ) : null}

              <PhoneAuthForm onSuccess={onSuccess} refCode={refCode} />

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
