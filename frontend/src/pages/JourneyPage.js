import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../App';
import { api } from '../lib/api';
import { TopBar } from '../components/TopBar';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { toast } from 'sonner';
import {
  Send, Loader2, Sparkles, ArrowRight, Brain, ChevronDown, ChevronUp, CircleDot,
} from 'lucide-react';

const PLACEHOLDERS = [
  'Build my company…',
  'Launch a product…',
  'Grow revenue…',
  'Hire my first team…',
  'Expand internationally…',
  'Fix operations…',
  'Make an important decision…',
];

const STRING_FIELDS = ['objective', 'why_now', 'whats_at_stake', 'knowledge_level', 'urgency', 'impact', 'timeline'];

function fieldValue(field, value) {
  if (value === null || value === undefined) return '';
  if (Array.isArray(value)) return value.filter((v) => String(v).trim()).join(' · ');
  if (typeof value === 'object') {
    return Object.entries(value).map(([k, v]) => `${k}: ${v}`).join(' · ');
  }
  return String(value).trim();
}

function isFilled(field, value) {
  return fieldValue(field, value).length > 0;
}

export default function JourneyPage() {
  const { user, setCredits } = useAuth();
  const [journey, setJourney] = useState(null);
  const [loading, setLoading] = useState(true);
  const [objective, setObjective] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [phIdx, setPhIdx] = useState(0);
  const [panelOpen, setPanelOpen] = useState(false);
  const endRef = useRef(null);

  const load = useCallback(async () => {
    try {
      const r = await api.get('/journey');
      setJourney(r.data);
    } catch (_e) {
      /* noop */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // rotating placeholder on the landing
  useEffect(() => {
    if (journey?.started) return undefined;
    const id = setInterval(() => setPhIdx((i) => (i + 1) % PLACEHOLDERS.length), 2600);
    return () => clearInterval(id);
  }, [journey?.started]);

  useEffect(() => {
    if (journey?.started) endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [journey?.messages?.length, busy]);

  const handleError = (e) => {
    const status = e?.response?.status;
    if (status === 402) {
      toast.error('You are out of credits. Top up to keep going.');
    } else {
      toast.error('Your thinking partner could not respond. You were not charged, try again.');
    }
  };

  const start = useCallback(async () => {
    const obj = objective.trim();
    if (!obj || busy) return;
    setBusy(true);
    try {
      const r = await api.post('/journey/start', { objective: obj });
      setJourney(r.data);
      if (typeof r.data.credits === 'number') setCredits(r.data.credits);
      setPanelOpen(true);
    } catch (e) { handleError(e); } finally { setBusy(false); }
  }, [objective, busy, setCredits]);

  const send = useCallback(async () => {
    const msg = message.trim();
    if (!msg || busy) return;
    setBusy(true);
    // optimistic: show the user message immediately
    setJourney((j) => (j ? { ...j, messages: [...j.messages, { role: 'user', text: msg, at: null }] } : j));
    setMessage('');
    try {
      const r = await api.post('/journey/message', { message: msg });
      setJourney(r.data);
      if (typeof r.data.credits === 'number') setCredits(r.data.credits);
    } catch (e) {
      handleError(e);
      // roll back the optimistic message on failure
      setJourney((j) => (j ? { ...j, messages: j.messages.filter((m) => !(m.role === 'user' && m.text === msg && m.at === null)) } : j));
      setMessage(msg);
    } finally { setBusy(false); }
  }, [message, busy, setCredits]);

  const onKey = (e, fn) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); fn(); }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="animate-spin text-muted-foreground" size={22} />
      </div>
    );
  }

  // ---------------------------------------------------------------- LANDING (not started)
  if (!journey?.started) {
    return (
      <div className="min-h-screen flex flex-col">
        <TopBar />
        <main className="flex-1 flex items-center justify-center px-4">
          <div className="w-full max-w-2xl mx-auto -mt-10 text-center" data-testid="journey-landing">
            <div className="inline-flex items-center gap-2 text-xs text-muted-foreground mb-6 rounded-full border border-border/70 px-3 py-1">
              <Sparkles size={13} strokeWidth={2} /> Your founder thinking partner
            </div>
            <h1 className="font-display text-3xl sm:text-5xl tracking-[-0.02em] leading-[1.05]">
              What are you trying to accomplish?
            </h1>
            <p className="text-muted-foreground mt-4 text-sm sm:text-base">
              Tell me in your own words. We will think it through together, one step at a time.
            </p>

            <div className="mt-8 text-left">
              <Textarea
                data-testid="journey-objective-input"
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
                onKeyDown={(e) => onKey(e, start)}
                placeholder={PLACEHOLDERS[phIdx]}
                rows={4}
                className="text-base resize-none rounded-2xl border-border/70 focus-visible:ring-1 px-4 py-3.5 shadow-sm"
              />
              <div className="mt-4 flex justify-center">
                <Button
                  data-testid="journey-start-btn"
                  onClick={start}
                  disabled={!objective.trim() || busy}
                  className="rounded-full px-7 h-11 text-sm"
                >
                  {busy ? <Loader2 className="animate-spin mr-2" size={16} /> : null}
                  {busy ? 'Thinking' : 'Start Conversation'}
                  {!busy ? <ArrowRight size={16} strokeWidth={2} className="ml-2" /> : null}
                </Button>
              </div>
              <p className="text-center text-xs text-muted-foreground mt-3">
                {user?.credits ?? 0} credits · Cmd/Ctrl + Enter to start
              </p>
            </div>
          </div>
        </main>
      </div>
    );
  }

  // ---------------------------------------------------------------- CHAT (started)
  const model = journey.model || {};
  const order = journey.field_order || Object.keys(journey.field_labels || {});
  const labels = journey.field_labels || {};
  const filled = order.filter((f) => isFilled(f, model[f]));
  const empties = order.filter((f) => !isFilled(f, model[f]));
  const conf = journey.confidence ?? 0;

  const Panel = (
    <div className="space-y-5">
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">What I understand</span>
          <span data-testid="journey-confidence" className="font-mono-plex text-xs text-foreground">{conf}%</span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
          <div className="h-full rounded-full bg-primary transition-all duration-700" style={{ width: `${conf}%` }} />
        </div>
        <div className="text-xs text-muted-foreground mt-1.5">{journey.confidence_band}</div>
        {journey.ready_for_direction ? (
          <div className="mt-3 flex items-start gap-2 rounded-xl bg-secondary/70 px-3 py-2 text-xs text-foreground">
            <Sparkles size={13} className="mt-0.5 shrink-0" />
            <span>I have enough to shape an initial direction with you. Keep going, or ask me to lay it out.</span>
          </div>
        ) : null}
      </div>

      <div className="space-y-3">
        {filled.map((f) => (
          <div key={f} data-testid={`journey-field-${f}`}>
            <div className="text-[11px] uppercase tracking-wide text-muted-foreground">{labels[f] || f}</div>
            <div className="text-sm text-foreground leading-snug mt-0.5">{fieldValue(f, model[f])}</div>
          </div>
        ))}
        {filled.length === 0 ? (
          <div className="text-sm text-muted-foreground">Building your picture as we talk…</div>
        ) : null}
      </div>

      {empties.length ? (
        <div className="pt-2 border-t border-border/60">
          <div className="text-[11px] uppercase tracking-wide text-muted-foreground mb-2">Still exploring</div>
          <div className="flex flex-wrap gap-1.5">
            {empties.map((f) => (
              <span key={f} className="inline-flex items-center gap-1 text-[11px] text-muted-foreground rounded-full border border-dashed border-border/70 px-2 py-0.5">
                <CircleDot size={10} strokeWidth={2} className="opacity-50" /> {labels[f] || f}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );

  return (
    <div className="min-h-screen flex flex-col">
      <TopBar />
      <main className="flex-1 w-full max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 pb-4 grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
        {/* conversation */}
        <section className="flex flex-col min-h-[60vh]" data-testid="journey-chat">
          <div className="flex-1 space-y-5 py-4">
            {journey.messages.map((m, i) => (
              m.role === 'assistant' ? (
                <div key={i} className="flex gap-3 items-start" data-testid="journey-msg-assistant">
                  <span className="mt-0.5 inline-flex items-center justify-center w-7 h-7 rounded-lg bg-primary text-primary-foreground shrink-0">
                    <Brain size={15} strokeWidth={1.75} />
                  </span>
                  <div className="rounded-2xl rounded-tl-sm bg-card border border-border/70 px-4 py-3 text-[15px] leading-relaxed whitespace-pre-wrap max-w-[44rem]">
                    {m.text}
                  </div>
                </div>
              ) : (
                <div key={i} className="flex justify-end" data-testid="journey-msg-user">
                  <div className="rounded-2xl rounded-tr-sm bg-secondary px-4 py-3 text-[15px] leading-relaxed whitespace-pre-wrap max-w-[40rem]">
                    {m.text}
                  </div>
                </div>
              )
            ))}
            {busy ? (
              <div className="flex gap-3 items-center text-muted-foreground" data-testid="journey-thinking">
                <span className="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-primary/80 text-primary-foreground shrink-0">
                  <Brain size={15} strokeWidth={1.75} />
                </span>
                <Loader2 className="animate-spin" size={16} /> <span className="text-sm">Thinking…</span>
              </div>
            ) : null}
            <div ref={endRef} />
          </div>

          {/* mobile understanding toggle */}
          <button
            onClick={() => setPanelOpen((o) => !o)}
            className="lg:hidden flex items-center justify-between rounded-xl border border-border/70 px-3 py-2 text-sm text-muted-foreground mb-3"
            data-testid="journey-panel-toggle"
          >
            <span>What I understand · {conf}%</span>
            {panelOpen ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
          </button>
          {panelOpen ? <div className="lg:hidden rounded-2xl border border-border/70 bg-card/60 p-4 mb-3">{Panel}</div> : null}

          {/* composer */}
          <div className="sticky bottom-3">
            <div className="rounded-2xl border border-border/70 bg-card shadow-sm p-2 flex items-end gap-2">
              <Textarea
                data-testid="journey-message-input"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => onKey(e, send)}
                placeholder="Type your answer…"
                rows={1}
                className="min-h-[44px] max-h-40 resize-none border-0 focus-visible:ring-0 shadow-none text-[15px] px-2 py-2.5"
              />
              <Button
                data-testid="journey-send-btn"
                onClick={send}
                disabled={!message.trim() || busy}
                size="icon"
                className="rounded-xl h-10 w-10 shrink-0"
              >
                {busy ? <Loader2 className="animate-spin" size={16} /> : <Send size={16} strokeWidth={2} />}
              </Button>
            </div>
            <p className="text-center text-[11px] text-muted-foreground mt-2">
              {user?.credits ?? 0} credits · one focused step at a time
            </p>
          </div>
        </section>

        {/* understanding panel (desktop) */}
        <aside className="hidden lg:block">
          <div className="sticky top-4 rounded-2xl border border-border/70 bg-card/60 p-5" data-testid="journey-understanding-panel">
            {Panel}
          </div>
        </aside>
      </main>
    </div>
  );
}
