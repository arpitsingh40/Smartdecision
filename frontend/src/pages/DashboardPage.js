import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { Skeleton } from '../components/ui/skeleton';
import { Textarea } from '../components/ui/textarea';
import { ArrowRight } from 'lucide-react';
import { toast } from 'sonner';
import { TopBar } from '../components/TopBar';
import { api } from '../lib/api';
import { useAuth } from '../App';

const paceStyle = {
  ahead: 'text-[hsl(var(--success))]',
  'on-track': 'text-[hsl(var(--info))]',
  behind: 'text-[hsl(var(--warning))]',
};
const statusStyle = {
  active: 'bg-[hsl(var(--accent))] text-foreground border border-border/70',
  paused: 'bg-muted text-muted-foreground border border-border/70',
  graduated: 'bg-secondary text-foreground border border-border/70',
  released: 'bg-transparent text-muted-foreground border border-border/70',
};

// Derive a short title from the user's first message: first sentence (or first 60 chars).
const deriveTitle = (text) => {
  const t = (text || '').trim();
  if (!t) return '';
  const firstStop = t.search(/[.!?\n]/);
  const head = firstStop > 0 ? t.slice(0, firstStop) : t;
  return head.length > 60 ? head.slice(0, 57).trimEnd() + '…' : head;
};

function DirectComposer({ variant = 'inline', autoFocus = false }) {
  const navigate = useNavigate();
  const { setCredits } = useAuth();
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const taRef = useRef(null);

  useEffect(() => {
    if (autoFocus && taRef.current) taRef.current.focus();
  }, [autoFocus]);

  const submit = async (e) => {
    e?.preventDefault?.();
    if (busy) return;
    const msg = text.trim();
    if (msg.length < 3) {
      toast.error('Give it a sentence — even a rough one.');
      return;
    }
    setBusy(true);
    try {
      const title = deriveTitle(msg) || 'New thread';
      const r = await api.post('/goals', { title, why_now: msg });
      setCredits(r.data.credits);
      navigate(`/thread/${r.data.thread.thread_id}`);
    } catch (err) {
      const m = err.response?.status === 402
        ? 'Not enough credits to start.'
        : err.response?.data?.detail || 'Could not open. Try again.';
      toast.error(m);
      setBusy(false);
    }
  };

  const onKey = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') submit(e);
  };

  if (variant === 'hero') {
    return (
      <form onSubmit={submit} data-testid="direct-composer-hero" className="rise-4 mt-10 max-w-xl mx-auto text-left">
        <Textarea
          ref={taRef}
          data-testid="direct-composer-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKey}
          disabled={busy}
          maxLength={4000}
          placeholder="What's on your mind. Just start typing."
          className="rounded-xl min-h-[120px] text-[15px] leading-6 bg-white border-border/70 shadow-sm focus-visible:ring-[hsl(var(--ring))]"
        />
        <div className="mt-3 flex items-center justify-between gap-3">
          <p className="text-[11px] text-muted-foreground tracking-wide">
            One sentence is enough. The engine will ask the next question.
          </p>
          <Button
            type="submit"
            data-testid="direct-composer-submit"
            disabled={busy || text.trim().length < 3}
            className="rounded-xl h-11 px-5 active:scale-[0.98] transition-colors"
          >
            {busy ? 'Reading…' : (<><span>Start</span><ArrowRight size={15} strokeWidth={1.75} className="ml-1.5" /></>)}
          </Button>
        </div>
      </form>
    );
  }

  return (
    <form onSubmit={submit} data-testid="direct-composer-inline" className="mb-8 rounded-2xl border border-border/70 bg-white p-4 sm:p-5 premium-lift">
      <Textarea
        ref={taRef}
        data-testid="direct-composer-input"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={onKey}
        disabled={busy}
        maxLength={4000}
        placeholder="What's on your mind right now. Just start typing."
        className="rounded-xl min-h-[88px] text-[15px] leading-6 border-border/60 focus-visible:ring-[hsl(var(--ring))]"
      />
      <div className="mt-3 flex items-center justify-between gap-3">
        <p className="text-[11px] text-muted-foreground tracking-wide">
          Press ⌘/Ctrl + Enter to send.
        </p>
        <Button
          type="submit"
          data-testid="direct-composer-submit"
          disabled={busy || text.trim().length < 3}
          className="rounded-xl h-10 px-4 active:scale-[0.98] transition-colors"
        >
          {busy ? 'Reading…' : (<><span>Start new thread</span><ArrowRight size={14} strokeWidth={1.75} className="ml-1.5" /></>)}
        </Button>
      </div>
    </form>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [goals, setGoals] = useState(null);
  const [momentum, setMomentum] = useState(null);

  useEffect(() => {
    api.get('/goals').then((r) => { setGoals(r.data.goals); setMomentum(r.data.momentum); }).catch(() => setGoals([]));
  }, []);

  return (
    <div className="relative z-10 min-h-screen">
      <TopBar title="Your pursuits" />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
        {momentum && goals?.length > 0 && (
          <div data-testid="momentum-strip" className="flex flex-wrap items-baseline gap-x-8 gap-y-2 mb-8 pb-6 border-b border-border/70">
            <div>
              <span className="font-display text-3xl">{momentum.kept_promises}</span>
              <span className="text-xs text-muted-foreground ml-2">promises kept</span>
            </div>
            {momentum.avg_consistency !== null && (
              <div>
                <span className="font-display text-3xl">{Math.round(momentum.avg_consistency * 100)}%</span>
                <span className="text-xs text-muted-foreground ml-2">follow-through, last 14 days</span>
              </div>
            )}
            <div>
              <span className="font-display text-3xl">{momentum.turns_this_week}</span>
              <span className="text-xs text-muted-foreground ml-2">moves this week</span>
            </div>
          </div>
        )}

        {/* Inline composer above the existing threads list — direct entry, no form page. */}
        {goals !== null && goals.length > 0 && (
          <>
            <DirectComposer variant="inline" />
            <p className="text-sm text-muted-foreground mb-4">One thread per goal. Each holds where you are, and what comes next.</p>
          </>
        )}

        {goals === null && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 lg:gap-6">
            <Skeleton className="h-44 rounded-2xl" />
            <Skeleton className="h-44 rounded-2xl" />
          </div>
        )}

        {goals !== null && goals.length === 0 && (
          <Card data-testid="empty-state" className="relative overflow-hidden rounded-2xl border border-border/70 premium-lift">
            <div aria-hidden="true" className="pointer-events-none absolute inset-0">
              <div className="absolute -top-28 -right-24 w-96 h-96 rounded-full bg-[hsl(var(--accent))]/60 blur-3xl" />
              <div className="absolute -bottom-36 -left-24 w-80 h-80 rounded-full bg-[hsl(var(--warning))]/[0.07] blur-3xl" />
            </div>
            <CardContent className="relative px-6 py-14 sm:px-14 sm:py-16 text-center">
              <svg viewBox="0 0 240 24" className="rise-1 mx-auto mb-8 w-52 sm:w-60 text-[hsl(var(--ring))]" fill="none" aria-hidden="true">
                <path className="thread-draw" d="M4 12 Q 62 -2 120 12 T 236 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                <circle cx="4" cy="12" r="2.5" fill="currentColor" opacity="0.35" />
                <circle className="thread-node" cx="120" cy="12" r="3.5" fill="currentColor" />
                <circle cx="236" cy="12" r="2.5" fill="currentColor" opacity="0.35" />
              </svg>
              <p className="rise-1 text-[11px] uppercase tracking-[0.24em] text-muted-foreground mb-4">Your first thread</p>
              <h2 className="rise-2 font-display text-3xl sm:text-[40px] leading-[1.12] max-w-xl mx-auto">
                The thing on your mind?
                <span className="block italic mt-1">Just type it.</span>
              </h2>
              <p className="rise-3 text-sm sm:text-[15px] text-muted-foreground leading-relaxed max-w-md mx-auto mt-5">
                Not a form. Not a plan. Whatever you would say to a friend who actually listens,
                start there. The engine takes it from there with one question at a time.
              </p>
              <DirectComposer variant="hero" autoFocus />
              <p className="text-[11px] text-muted-foreground mt-4 tracking-wide">
                {typeof user?.credits === 'number' ? `${user.credits.toLocaleString()} tokens available` : ''}
              </p>
            </CardContent>
          </Card>
        )}

        {goals !== null && goals.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 lg:gap-6">
            {goals.map((g) => (
              <Card key={g.thread_id} data-testid="goal-card"
                className="rounded-2xl border border-border/70 premium-lift hover:shadow-lg transition-shadow">
                <CardContent className="p-6">
                  <h3 className="font-display text-lg leading-snug mb-3">{g.goal}</h3>
                  <div className="flex items-center gap-3 mb-4">
                    <Badge className={`rounded-lg text-[11px] font-normal ${statusStyle[g.status] || statusStyle.active}`}>
                      {g.status}
                    </Badge>
                    <span className={`text-[11px] ${paceStyle[g.pace] || paceStyle['on-track']}`}>{g.pace}</span>
                    {g.action_overdue && (
                      <span data-testid="overdue-chip" className="text-[11px] text-[hsl(var(--warning))]">
                        48h window passed — did it happen?
                      </span>
                    )}
                  </div>
                  <Separator className="hairline mb-4" />
                  <p className="text-xs text-muted-foreground mb-1">Next action</p>
                  <p className="text-sm leading-5 line-clamp-2 mb-3">{g.next_action || '—'}</p>
                  {g.open_question && g.open_question !== '(none yet)' && (
                    <p data-testid="card-open-question" className="text-xs text-muted-foreground italic leading-5 line-clamp-2 mb-5">
                      Still open: {g.open_question}
                    </p>
                  )}
                  <Button variant="secondary" data-testid="goal-card-open-button"
                    onClick={() => navigate(`/thread/${g.thread_id}`)}
                    className="rounded-xl border border-border/70 active:scale-[0.98] transition-colors w-full">
                    {g.action_overdue ? 'Answer it' : 'Open'}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
