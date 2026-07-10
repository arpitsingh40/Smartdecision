import { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../lib/api';
import { TopBar } from '../components/TopBar';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import {
  Loader2, Lock, Sparkles, Send, RotateCcw, UserCog, ArrowRight, Brain, CheckCircle2, Building2,
} from 'lucide-react';

const FIELD_LABELS = {
  personality: 'Personality',
  working_style: 'How you work',
  communication_style: 'Communication style',
  decision_style: 'Decision style',
  risk_appetite: 'Risk appetite',
  strengths: 'Strengths to lean on',
  blind_spots: 'Blind spots to cover',
  motivations: 'What drives you',
  industry_summary: 'Your industry',
};

export default function FounderProfilePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [denied, setDenied] = useState(false);
  const [noOrg, setNoOrg] = useState(false);

  const [profile, setProfile] = useState(null);          // distilled profile (when done)
  const [question, setQuestion] = useState(null);        // current pending question
  const [transcript, setTranscript] = useState([]);      // [{q,a}]
  const [count, setCount] = useState(0);
  const [target, setTarget] = useState(6);
  const [canFinish, setCanFinish] = useState(false);
  const [answer, setAnswer] = useState('');
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get('/founder/profile');
      const d = r.data;
      setTarget(d.interview?.target || 6);
      setCount(d.interview?.count || 0);
      setCanFinish(!!d.interview?.can_finish);
      setTranscript(d.interview?.transcript || []);
      if (d.has_profile) {
        setProfile(d.profile);
        setQuestion(null);
      } else if (d.interview?.status === 'in_progress' && d.interview?.pending_question) {
        setQuestion(d.interview.pending_question);
        setProfile(null);
      } else {
        setQuestion(null);
        setProfile(null);
      }
    } catch (e) {
      if (e?.response?.status === 404) setNoOrg(true);
      else setDenied(true);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [question, transcript, profile]);

  const start = async () => {
    setBusy(true);
    try {
      const r = await api.post('/founder/interview/start');
      setProfile(null); setTranscript([]); setCount(0); setCanFinish(false);
      setQuestion(r.data.question); setTarget(r.data.target);
    } catch (e) { toast.error(e?.response?.data?.detail || 'Could not start.'); }
    finally { setBusy(false); }
  };

  const send = async () => {
    if (busy || !answer.trim()) return;
    const myQ = question; const myA = answer.trim();
    setBusy(true);
    setTranscript((t) => [...t, { q: myQ, a: myA }]);
    setAnswer(''); setQuestion(null);
    try {
      const r = await api.post('/founder/interview/answer', { message: myA });
      setCount(r.data.count || 0); setTarget(r.data.target || target);
      setCanFinish((r.data.count || 0) >= 2);
      if (r.data.done) {
        setProfile(r.data.profile); setQuestion(null);
        toast.success('Your profile is ready. The brain now advises you the way you actually operate.');
      } else {
        setQuestion(r.data.question);
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Something went wrong. Try again.');
      setQuestion(myQ); setAnswer(myA);
      setTranscript((t) => t.slice(0, -1));
    } finally { setBusy(false); }
  };

  const finish = async () => {
    setBusy(true);
    try {
      const r = await api.post('/founder/interview/finish');
      setProfile(r.data.profile); setQuestion(null);
      toast.success('Profile built from what you have shared so far.');
    } catch (e) { toast.error(e?.response?.data?.detail || 'Could not finish yet.'); }
    finally { setBusy(false); }
  };

  if (loading) {
    return (
      <div className="min-h-screen"><TopBar />
        <div className="flex items-center gap-2 justify-center text-sm text-muted-foreground py-24">
          <Loader2 className="animate-spin" size={16} /> Loading…
        </div>
      </div>
    );
  }

  if (noOrg || denied) {
    return (
      <div className="min-h-screen"><TopBar />
        <div data-testid="founder-profile-blocked" className="max-w-md mx-auto text-center py-24 px-6">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl border mb-4 text-muted-foreground">
            {noOrg ? <Building2 size={20} /> : <Lock size={20} />}
          </div>
          <h2 className="font-display text-xl">{noOrg ? 'Create your workspace first' : 'Only the founder sets this up'}</h2>
          <p className="text-sm text-muted-foreground mt-2">
            {noOrg ? 'The founder profile lives on your company workspace.' : 'This deep onboarding is for the workspace owner.'}
          </p>
          <Button className="rounded-xl mt-6" onClick={() => navigate(noOrg ? '/app/team' : '/app')}>{noOrg ? 'Go to Team' : 'Open Decision Brain'}</Button>
        </div>
      </div>
    );
  }

  const progressPct = Math.min(100, Math.round((count / Math.max(1, target)) * 100));

  return (
    <div className="min-h-screen"><TopBar />
      <main data-testid="founder-profile-page" className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 pb-28 pt-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center justify-center w-8 h-8 rounded-xl bg-[hsl(var(--accent))] text-[hsl(var(--ring))]"><UserCog size={16} /></span>
            <h1 className="font-display text-xl">Get to know me</h1>
          </div>
          <span className="inline-flex items-center gap-1.5 text-[11px] px-2 py-0.5 rounded-full border bg-card text-muted-foreground"><Lock size={11} /> Private to you</span>
        </div>
        <p className="text-sm text-muted-foreground mb-6">
          A short, real conversation so the brain learns how you operate and what your industry actually is. Then every answer it gives you fits you, not a generic founder.
        </p>

        {/* ---------- PROFILE VIEW (done) ---------- */}
        {profile ? (
          <div data-testid="fp-profile-card" className="space-y-4">
            <section className="rounded-2xl border bg-card p-6">
              <div className="flex items-center gap-2 text-[hsl(var(--success))] text-xs mb-2"><CheckCircle2 size={14} /> Profile active — the brain is tuned to you</div>
              <p data-testid="fp-summary" className="font-display text-lg sm:text-xl tracking-[-0.01em] leading-snug">{profile.summary}</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 mt-5">
                {Object.entries(FIELD_LABELS).map(([k, label]) => (
                  profile[k] ? (
                    <div key={k}>
                      <div className="text-[11px] uppercase tracking-[0.1em] text-muted-foreground">{label}</div>
                      <div className="text-sm mt-0.5">{profile[k]}</div>
                    </div>
                  ) : null
                ))}
              </div>
            </section>
            <div className="flex flex-wrap gap-2">
              <Button data-testid="fp-redo-btn" variant="secondary" onClick={start} disabled={busy} className="rounded-xl">
                <RotateCcw size={14} className="mr-1.5" /> Redo the conversation
              </Button>
              <Button onClick={() => navigate('/app')} className="rounded-xl">
                <Brain size={14} className="mr-1.5" /> Ask the brain now <ArrowRight size={14} className="ml-1.5" />
              </Button>
            </div>
          </div>
        ) : question ? (
          /* ---------- CONVERSATION ---------- */
          <div className="space-y-4">
            {/* progress */}
            <div data-testid="fp-progress" className="flex items-center gap-3">
              <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                <div className="h-full bg-primary transition-all duration-300" style={{ width: `${progressPct}%` }} />
              </div>
              <span className="text-[11px] text-muted-foreground whitespace-nowrap">{count} / {target}</span>
            </div>

            {/* transcript */}
            {transcript.map((t, i) => (
              <div key={i} className="space-y-2">
                <div className="flex gap-2"><span className="shrink-0 w-7 h-7 rounded-lg bg-[hsl(var(--accent))] text-[hsl(var(--ring))] flex items-center justify-center"><Brain size={14} /></span>
                  <div className="rounded-2xl rounded-tl-sm bg-secondary/50 px-4 py-2.5 text-sm">{t.q}</div>
                </div>
                <div className="flex justify-end"><div className="rounded-2xl rounded-tr-sm bg-primary text-primary-foreground px-4 py-2.5 text-sm max-w-[85%]">{t.a}</div></div>
              </div>
            ))}

            {/* current question */}
            <div className="flex gap-2"><span className="shrink-0 w-7 h-7 rounded-lg bg-[hsl(var(--accent))] text-[hsl(var(--ring))] flex items-center justify-center"><Brain size={14} /></span>
              <div data-testid="fp-question" className="rounded-2xl rounded-tl-sm bg-secondary/50 px-4 py-2.5 text-sm">{question}</div>
            </div>

            <div ref={endRef} />

            {/* answer box */}
            <div className="rounded-2xl border bg-card p-3 sticky bottom-4 shadow-sm">
              <Textarea data-testid="fp-answer-input" value={answer} onChange={(e) => setAnswer(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) send(); }}
                placeholder="Answer in your own words… (Cmd/Ctrl + Enter to send)" className="rounded-xl border-0 focus-visible:ring-0 min-h-[70px] resize-none" />
              <div className="flex items-center justify-between mt-2">
                <Button data-testid="fp-finish-btn" variant="ghost" size="sm" onClick={finish} disabled={busy || !canFinish}
                  className="rounded-lg text-muted-foreground text-xs">
                  {busy ? <Loader2 className="animate-spin" size={13} /> : 'Finish & build my profile'}
                </Button>
                <Button data-testid="fp-send-btn" size="sm" onClick={send} disabled={busy || !answer.trim()} className="rounded-xl">
                  {busy ? <Loader2 className="animate-spin" size={14} /> : <>Send <Send size={13} className="ml-1.5" /></>}
                </Button>
              </div>
            </div>
          </div>
        ) : (
          /* ---------- INTRO / START ---------- */
          <section className="rounded-2xl border bg-card p-6 sm:p-8 text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-[hsl(var(--accent))] text-[hsl(var(--ring))] mb-4"><Sparkles size={22} /></div>
            <h2 className="font-display text-2xl">A few minutes, once.</h2>
            <p className="text-sm text-muted-foreground mt-2 max-w-md mx-auto">
              The brain will ask you about your business, how you make calls, what you are great at, and where you get stuck. Then it remembers, so it never gives you generic advice again.
            </p>
            <Button data-testid="fp-start-btn" onClick={start} disabled={busy} className="rounded-xl mt-6">
              {busy ? <Loader2 className="animate-spin" size={15} /> : <>Start the conversation <ArrowRight size={15} className="ml-1.5" /></>}
            </Button>
          </section>
        )}
      </main>
    </div>
  );
}
