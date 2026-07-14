import { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../App';
import { api } from '../lib/api';
import { TopBar } from '../components/TopBar';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '../components/ui/dialog';
import { toast } from 'sonner';
import {
  Send, Upload, FileText, X, SlidersHorizontal, Loader2, BookOpen,
  CheckCircle2, AlertCircle, Quote, Clock, ArrowRight, Target, Sparkles, Lock, Flag,
} from 'lucide-react';

const MODE_LABEL = { answer: 'Answer', decide: 'Decision', plan: 'Plan' };
const DUE_OPTIONS = [
  { label: 'Today', hours: 8 },
  { label: '24h', hours: 24 },
  { label: '48h', hours: 48 },
  { label: '3 days', hours: 72 },
  { label: '1 week', hours: 168 },
];
const newSessionId = () =>
  (typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : `s_${Date.now()}_${Math.random().toString(36).slice(2)}`);
const fmtLeft = (iso) => {
  if (!iso) return '';
  const ms = new Date(iso).getTime() - Date.now();
  const overdue = ms < 0;
  const m = Math.abs(Math.round(ms / 60000));
  const d = Math.floor(m / 1440); const h = Math.floor((m % 1440) / 60); const mm = m % 60;
  const txt = d > 0 ? `${d}d ${h}h` : h > 0 ? `${h}h ${mm}m` : `${mm}m`;
  return overdue ? `${txt} overdue` : `${txt} left`;
};

export default function BrainPage() {
  const { setCredits } = useAuth();
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [actionInput, setActionInput] = useState('');
  const [committed, setCommitted] = useState(null);
  const [decisionStatus, setDecisionStatus] = useState(null);
  const [execBusy, setExecBusy] = useState(false);
  const [sessionId, setSessionId] = useState(() => newSessionId());
  const [dueHours, setDueHours] = useState(48);
  const [dueAt, setDueAt] = useState(null);
  const [showResult, setShowResult] = useState(false);
  const [resultInput, setResultInput] = useState('');
  const [docs, setDocs] = useState([]);
  const [canTrain, setCanTrain] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [trainOpen, setTrainOpen] = useState(false);
  const [instructions, setInstructions] = useState('');
  const [savingRules, setSavingRules] = useState(false);
  const fileRef = useRef(null);

  // ---- Organ 1: outcome reviews due + launch-KPI one-tap signals ----
  const [reviewsDue, setReviewsDue] = useState([]);
  const [reviewBusy, setReviewBusy] = useState(false);
  const [reviewImpact, setReviewImpact] = useState('');
  const [reviewNote, setReviewNote] = useState('');
  const [kpiSent, setKpiSent] = useState({});

  const loadReviews = useCallback(async () => {
    try {
      const r = await api.get('/brain/reviews/due');
      setReviewsDue(r.data.due || []);
    } catch (_e) { /* noop */ }
  }, []);

  useEffect(() => { loadReviews(); }, [loadReviews]);

  const submitReview = useCallback(async (id, outcome) => {
    if (reviewBusy) return;
    setReviewBusy(true);
    try {
      const body = { outcome };
      if (reviewNote.trim()) body.actual = reviewNote.trim();
      const imp = parseInt(reviewImpact, 10);
      if (!Number.isNaN(imp)) body.impact_inr = imp;
      const r = await api.post(`/brain/decisions/${id}/review`, body);
      const cal = r.data?.calibration;
      toast.success(cal?.label ? `Outcome recorded. Calibration: ${cal.label}` : 'Outcome recorded.');
      setReviewImpact(''); setReviewNote('');
      loadReviews();
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not record the outcome.');
    } finally { setReviewBusy(false); }
  }, [reviewBusy, reviewNote, reviewImpact, loadReviews]);

  const sendKpi = useCallback(async (kind, value) => {
    if (!result?.decision_id) return;
    setKpiSent((s) => ({ ...s, [kind]: value }));
    try {
      await api.post('/kpi/signal', { kind, value, decision_id: result.decision_id });
    } catch (_e) { /* noop */ }
  }, [result]);

  const loadDocs = useCallback(async () => {
    try {
      const r = await api.get('/brain/documents');
      setDocs(r.data.documents || []);
      setCanTrain(r.data.can_train !== false);
    } catch (_e) { /* noop */ }
  }, []);

  useEffect(() => {
    loadDocs();
    api.get('/brain/settings').then((r) => setInstructions(r.data.instructions || '')).catch(() => {});
  }, [loadDocs]);

  // hand-off from My Decisions: seed the workspace with a freshly generated "next step"
  useEffect(() => {
    const seed = sessionStorage.getItem('sdg_workspace_seed');
    if (!seed) return;
    try {
      const d = JSON.parse(seed);
      setResult(d);
      if (d.session_id) setSessionId(d.session_id);
      setCommitted(null); setDecisionStatus(null);
      setActionInput(d.next_action || '');
    } catch (_e) { /* noop */ }
    sessionStorage.removeItem('sdg_workspace_seed');
  }, []);

  // poll only while a document is still indexing
  useEffect(() => {
    const hasProcessing = docs.some((d) => d.status === 'processing');
    if (!hasProcessing) return undefined;
    const id = setInterval(loadDocs, 4000);
    return () => clearInterval(id);
  }, [docs, loadDocs]);

  const runAsk = useCallback(async (q, sid) => {
    if (!q.trim() || loading) return;
    setLoading(true);
    setResult(null); setShowResult(false); setResultInput(''); setDueAt(null); setKpiSent({});
    try {
      const r = await api.post('/brain/ask', { question: q.trim(), session_id: sid });
      setResult(r.data);
      if (r.data.session_id) setSessionId(r.data.session_id);
      setCommitted(null); setDecisionStatus(null);
      setActionInput(r.data.next_action || '');
      if (r.data.credits != null) setCredits(r.data.credits);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not get an answer. Try again.');
    } finally {
      setLoading(false);
    }
  }, [loading, setCredits]);

  const ask = useCallback(() => runAsk(question, sessionId), [runAsk, question, sessionId]);

  const askNew = useCallback(() => {
    const sid = newSessionId();
    setSessionId(sid);
    runAsk(question, sid);
  }, [runAsk, question]);

  const goDeeper = useCallback(() => {
    if (!result?.sharpening_question) return;
    setQuestion(result.sharpening_question);
    runAsk(result.sharpening_question, sessionId);
  }, [result, runAsk, sessionId]);

  const findNextStep = useCallback(async () => {
    if (!result?.decision_id || execBusy) return;
    setExecBusy(true);
    try {
      const r = await api.post(`/brain/decisions/${result.decision_id}/next-step`);
      setResult(r.data);
      if (r.data.session_id) setSessionId(r.data.session_id);
      setCommitted(null); setDecisionStatus(null);
      setActionInput(r.data.next_action || '');
      setShowResult(false); setResultInput(''); setDueAt(null);
      if (r.data.credits != null) setCredits(r.data.credits);
      window.dispatchEvent(new Event('sdg-actions-changed'));
      toast.success('Here is your next step.');
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not find the next step.');
    } finally { setExecBusy(false); }
  }, [result, execBusy, setCredits]);

  const onFile = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 8 * 1024 * 1024) { toast.error('Keep files under 8 MB.'); return; }
    setUploading(true);
    const reader = new FileReader();
    reader.onload = async () => {
      const dataUrl = String(reader.result || '');
      const idx = dataUrl.indexOf(',');
      const b64 = idx >= 0 ? dataUrl.slice(idx + 1) : dataUrl;
      try {
        await api.post('/brain/upload', { filename: file.name, mime: file.type, base64: b64 });
        toast.success(`Indexing "${file.name}"`);
        loadDocs();
      } catch (err) {
        toast.error(err?.response?.data?.detail || 'Upload failed.');
      } finally {
        setUploading(false);
        if (fileRef.current) fileRef.current.value = '';
      }
    };
    reader.readAsDataURL(file);
  };

  const delDoc = async (id) => {
    try { await api.delete(`/brain/documents/${id}`); loadDocs(); }
    catch (_e) { toast.error('Could not remove document.'); }
  };

  const saveRules = async () => {
    setSavingRules(true);
    try {
      await api.post('/brain/settings', { instructions });
      toast.success('Company rules saved. The brain will follow them.');
      setTrainOpen(false);
    } catch (_e) { toast.error('Could not save.'); }
    finally { setSavingRules(false); }
  };

  const commitMove = async () => {
    if (!actionInput.trim() || !result?.decision_id || execBusy) return;
    setExecBusy(true);
    try {
      const r = await api.post(`/brain/decisions/${result.decision_id}/commit`,
        { action: actionInput.trim(), due_in_hours: dueHours });
      setCommitted(r.data.committed_action); setDecisionStatus('open');
      setDueAt(r.data.due_at || null);
      window.dispatchEvent(new Event('sdg-actions-changed'));
      toast.success('Locked in. The clock is running.');
    } catch (_e) { toast.error('Could not save your move.'); }
    finally { setExecBusy(false); }
  };

  const markStatus = async (status, resultText) => {
    if (!result?.decision_id || execBusy) return;
    setExecBusy(true);
    try {
      await api.post(`/brain/decisions/${result.decision_id}/status`,
        { status, result: resultText || null });
      setDecisionStatus(status);
      setShowResult(false);
      window.dispatchEvent(new Event('sdg-actions-changed'));
      toast.success(status === 'done' ? 'Done. Logged for your founder too.' : 'Noted.');
    } catch (_e) { toast.error('Could not update.'); }
    finally { setExecBusy(false); }
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(); }
  };

  const readyCount = docs.filter((d) => d.status === 'ready').length;

  return (
    <div className="min-h-screen">
      <TopBar />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-8 lg:gap-10">

          {/* ---------- main column: ask + answer ---------- */}
          <section className="min-w-0">
            <h2 className="font-display text-3xl sm:text-4xl tracking-[-0.02em] leading-[1.05]">
              Your company brain.
            </h2>
            <p className="mt-3 text-sm md:text-base text-muted-foreground leading-6 max-w-xl">
              Upload your documents — PDFs, slides, spreadsheets, whatever. The brain reads and indexes them,
              then answers your questions grounded in what your team actually knows. No more hunting for context.
            </p>

            {/* ask box */}
            <div className="mt-6 rounded-2xl bg-card border border-border/70 shadow-[0_1px_0_rgba(17,24,39,0.06),0_12px_30px_rgba(17,24,39,0.06)] p-3">
              <Textarea
                data-testid="brain-question-input"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder='e.g. "What did we decide about refund windows?" · "Summarise the Q3 plan deck." · "Should I approve this discount?"'
                className="min-h-[96px] border-0 bg-transparent focus-visible:ring-0 resize-none text-[15px] leading-6"
              />
              <div className="flex items-center justify-between px-1 pt-1 gap-2">
                <span className="text-xs text-muted-foreground min-w-0 truncate">
                  {readyCount > 0
                    ? `${readyCount} document${readyCount > 1 ? 's' : ''} in knowledge`
                    : (canTrain ? <span className="text-amber-600 font-medium">Upload documents on the right to ground answers in your data →</span> : 'Ask anything — backed by your team’s knowledge')}
                </span>
                <div className="flex items-center gap-2 shrink-0">
                  {result && (
                    <Button data-testid="brain-new-topic" variant="ghost" onClick={askNew}
                      disabled={loading || !question.trim()} className="rounded-xl text-muted-foreground">
                      New topic
                    </Button>
                  )}
                  <Button
                    data-testid="brain-ask-button"
                    onClick={ask}
                    disabled={loading || !question.trim()}
                    className="rounded-xl active:scale-[0.98]"
                  >
                    {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} strokeWidth={1.75} />}
                    <span className="ml-2">{loading ? 'Thinking' : (result ? 'Continue' : 'Ask')}</span>
                  </Button>
                </div>
              </div>
            </div>

            {/* Organ 1: outcome reviews due — close the loop on past decisions */}
            {reviewsDue.length > 0 && (
              <div data-testid="brain-review-banner" className="mt-6 rounded-2xl border border-amber-300/70 bg-amber-50/60 p-4 sm:p-5 space-y-3">
                <div className="text-[11px] uppercase tracking-[0.12em] text-amber-800 flex items-center gap-1.5">
                  <Clock size={12} /> Time to close the loop
                  {reviewsDue.length > 1 ? (
                    <span className="normal-case tracking-normal rounded-full bg-amber-100 px-2 py-0.5">{reviewsDue.length - 1} more waiting</span>
                  ) : null}
                </div>
                <div>
                  <p className="text-sm font-medium leading-snug">{reviewsDue[0].question}</p>
                  {reviewsDue[0].predicted_outcome?.claim ? (
                    <p className="text-xs text-muted-foreground mt-1 leading-snug">
                      The engine predicted: “{reviewsDue[0].predicted_outcome.claim}” ({reviewsDue[0].predicted_outcome.confidence}% confident).
                      How did it actually go?
                    </p>
                  ) : null}
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <input
                    data-testid="review-impact-input"
                    value={reviewImpact}
                    onChange={(e) => setReviewImpact(e.target.value.replace(/[^0-9-]/g, ''))}
                    placeholder="₹ impact (optional)"
                    inputMode="numeric"
                    className="w-36 rounded-xl border border-border/70 bg-background px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                  <input
                    data-testid="review-note-input"
                    value={reviewNote}
                    onChange={(e) => setReviewNote(e.target.value)}
                    placeholder="What actually happened? (optional)"
                    className="flex-1 min-w-[180px] rounded-xl border border-border/70 bg-background px-3 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                </div>
                <div className="flex flex-wrap gap-2">
                  <Button data-testid="review-worked-btn" size="sm" disabled={reviewBusy}
                    onClick={() => submitReview(reviewsDue[0].id, 'worked')}
                    className="rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white">
                    It worked
                  </Button>
                  <Button data-testid="review-partly-btn" size="sm" variant="outline" disabled={reviewBusy}
                    onClick={() => submitReview(reviewsDue[0].id, 'partly')} className="rounded-xl">
                    Partly
                  </Button>
                  <Button data-testid="review-didnt-btn" size="sm" variant="outline" disabled={reviewBusy}
                    onClick={() => submitReview(reviewsDue[0].id, 'didnt')}
                    className="rounded-xl text-red-600 border-red-200 hover:bg-red-50">
                    It didn’t
                  </Button>
                </div>
              </div>
            )}

            {/* thinking state */}
            {loading && (
              <div data-testid="brain-thinking" className="mt-6 text-sm text-muted-foreground flex items-center gap-2" aria-live="polite">
                <Loader2 size={14} className="animate-spin" />
                Reading your documents and working it out…
              </div>
            )}

            {/* answer card */}
            {result && !loading && (
              <article data-testid="brain-answer" className="mt-6 rounded-2xl bg-card border border-border/70 shadow-[0_1px_0_rgba(17,24,39,0.06)] p-5 sm:p-6 space-y-4">
                <div className="flex items-center gap-2">
                  <Badge data-testid="brain-mode-badge" variant="outline" className="rounded-lg border-border/70 text-foreground">
                    {MODE_LABEL[result.mode] || 'Answer'}
                  </Badge>
                  {result.mode === 'answer' && (
                    result.found_in_docs
                      ? <span className="flex items-center gap-1 text-xs text-[hsl(var(--success))]"><CheckCircle2 size={13} /> grounded in your documents</span>
                      : <span className="flex items-center gap-1 text-xs text-[hsl(var(--warning))]"><AlertCircle size={13} /> not found in your documents</span>
                  )}
                </div>

                {/* lead value line */}
                {result.key_takeaway && (
                  <p data-testid="brain-key-takeaway"
                    className="text-lg md:text-xl font-display tracking-[-0.01em] leading-snug text-foreground">
                    {result.key_takeaway}
                  </p>
                )}

                {/* clarity: what's really going on */}
                {result.situation_read && (
                  <p data-testid="brain-situation-read"
                    className="text-sm text-muted-foreground italic border-l-2 border-border pl-3">
                    {result.situation_read}
                  </p>
                )}

                {/* main answer */}
                <p className="text-[15px] md:text-base leading-7 whitespace-pre-wrap text-foreground">
                  {result.answer}
                </p>

                {/* decision recommendation */}
                {result.mode === 'decide' && result.recommendation && (
                  <div data-testid="brain-recommendation" className="rounded-xl bg-[hsl(var(--accent))]/60 border border-border/70 border-l-2 border-l-[hsl(var(--ring))] px-4 py-3">
                    <div className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground mb-1">Recommended</div>
                    <p className="text-[15px] leading-6 font-display tracking-[-0.01em]">{result.recommendation}</p>
                  </div>
                )}

                {/* plan steps */}
                {result.mode === 'plan' && Array.isArray(result.plan) && result.plan.length > 0 && (
                  <ol data-testid="brain-plan" className="space-y-2">
                    {result.plan.map((step, i) => (
                      <li
                        key={i}
                        className={`flex gap-3 rounded-xl px-4 py-3 border border-border/70 ${i === 0 ? 'bg-[hsl(var(--accent))]/60' : 'bg-secondary/40'}`}
                      >
                        <span className={`shrink-0 font-mono-plex text-xs mt-0.5 ${i === 0 ? 'text-[hsl(var(--ring))]' : 'text-muted-foreground'}`}>
                          {String(i + 1).padStart(2, '0')}
                        </span>
                        <span className={`text-[15px] leading-6 ${i === 0 ? 'font-medium' : ''}`}>{step}</span>
                      </li>
                    ))}
                  </ol>
                )}

                {/* NEXT ACTION — the hero, the hook to act now */}
                {result.next_action && (
                  <div data-testid="brain-next-action" className="rounded-xl bg-[hsl(var(--accent))]/60 border border-border/70 border-l-2 border-l-[hsl(var(--ring))] px-4 py-3">
                    <div className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground mb-1 flex items-center gap-1.5">
                      <Target size={12} /> Your next move (24-48h)
                    </div>
                    <p className="text-[15px] md:text-base leading-6 font-display tracking-[-0.01em]">{result.next_action}</p>
                    {result.hook && (
                      <p data-testid="brain-hook" className="text-sm text-muted-foreground mt-1.5">{result.hook}</p>
                    )}
                  </div>
                )}

                {/* Organ 1: the checkable prediction + when NOT to follow this */}
                {result.predicted_outcome?.claim && (
                  <div data-testid="brain-prediction" className="rounded-xl border border-border/60 bg-secondary/30 px-4 py-3">
                    <div className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground mb-1 flex items-center gap-1.5">
                      <Clock size={12} /> If you follow this
                      <span className="normal-case tracking-normal rounded-full bg-secondary px-2 py-0.5">
                        {result.predicted_outcome.confidence}% confident
                      </span>
                    </div>
                    <p className="text-sm leading-snug">{result.predicted_outcome.claim}</p>
                    <p className="text-[11px] text-muted-foreground mt-1">
                      We’ll check this together in {result.predicted_outcome.review_after_days} days. That’s how your track record gets built.
                    </p>
                  </div>
                )}
                {result.dont_follow_if && (
                  <div data-testid="brain-dont-follow" className="rounded-xl border border-amber-300/70 bg-amber-50/50 px-4 py-3">
                    <div className="text-[11px] uppercase tracking-[0.12em] text-amber-800 mb-1 flex items-center gap-1.5">
                      <AlertCircle size={12} /> Don’t follow this if
                    </div>
                    <p className="text-sm leading-snug text-foreground/90">{result.dont_follow_if}</p>
                  </div>
                )}

                {/* GOAL IMPACT — founder-only (members never receive this) */}
                {result.reasoning && (result.reasoning.assumptions_detected?.length || result.reasoning.question_rationale) ? (
                  <div data-testid="brain-reasoning" className="rounded-xl border border-border/60 bg-secondary/30 px-4 py-3 space-y-2">
                    <div className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
                      How the engine read this
                      {result.reasoning.decision_type && result.reasoning.decision_type !== 'other' ? (
                        <span className="ml-2 normal-case tracking-normal rounded-full bg-secondary px-2 py-0.5">{result.reasoning.decision_type} problem</span>
                      ) : null}
                      {result.reasoning.reversible === false ? (
                        <span className="ml-1.5 normal-case tracking-normal rounded-full bg-red-100 text-red-700 px-2 py-0.5">one-way door</span>
                      ) : result.reasoning.reversible === true ? (
                        <span className="ml-1.5 normal-case tracking-normal rounded-full bg-emerald-100 text-emerald-700 px-2 py-0.5">reversible</span>
                      ) : null}
                    </div>
                    {result.reasoning.assumptions_detected?.length ? (
                      <ul className="space-y-1">
                        {result.reasoning.assumptions_detected.slice(0, 3).map((a, i) => (
                          <li key={i} className="text-xs text-foreground/85 leading-snug">Assumption detected: {a}</li>
                        ))}
                      </ul>
                    ) : null}
                    {result.reasoning.question_rationale ? (
                      <p className="text-xs text-muted-foreground leading-snug">
                        Biggest unknown: {result.reasoning.dim_labels?.[result.reasoning.question_target] || result.reasoning.question_target}. {result.reasoning.question_rationale}
                      </p>
                    ) : null}
                  </div>
                ) : null}

                {result.goal_impact && (
                  <div data-testid="brain-goal-impact"
                    className={`rounded-xl border px-4 py-3 ${
                      result.goal_impact.band === 'high' ? 'border-emerald-300 bg-emerald-50/60'
                      : result.goal_impact.band === 'medium' ? 'border-amber-300 bg-amber-50/60'
                      : 'border-red-300 bg-red-50/60'}`}>
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <div className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground flex items-center gap-1.5">
                        <Flag size={12} /> Goal impact
                      </div>
                      <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded-full border bg-background text-muted-foreground">
                        <Lock size={10} /> Private to you
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span data-testid="brain-goal-impact-score" className={`font-display text-2xl leading-none ${
                        result.goal_impact.band === 'high' ? 'text-emerald-600'
                        : result.goal_impact.band === 'medium' ? 'text-amber-600' : 'text-red-600'}`}>
                        {result.goal_impact.score}
                      </span>
                      <span className="text-xs text-muted-foreground">/100</span>
                      <span className="text-sm font-medium ml-1">{result.goal_impact.label}</span>
                    </div>
                    {result.goal_impact.reason && (
                      <p className="text-xs text-muted-foreground mt-1.5">{result.goal_impact.reason}</p>
                    )}
                  </div>
                )}

                {/* citations */}
                {Array.isArray(result.citations) && result.citations.length > 0 && (
                  <div className="pt-1">
                    <div className="text-[11px] uppercase tracking-[0.12em] text-muted-foreground mb-2 flex items-center gap-1">
                      <Quote size={12} /> Sources
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {result.citations.map((c, i) => (
                        <span key={i} data-testid="brain-citation"
                          className="inline-flex items-center gap-1.5 rounded-lg bg-secondary/60 border border-border/70 px-2.5 py-1 text-xs text-muted-foreground">
                          <FileText size={12} strokeWidth={1.75} />
                          <span className="text-foreground/80">{c.doc}</span>
                          {c.chapter ? <span className="opacity-60">→ {c.chapter}</span> : null}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Launch KPI one-tap signals (KPI 1 + KPI 2) */}
                {result.decision_id && (
                  <div data-testid="brain-kpi-chips" className="flex flex-col gap-1.5 pt-1">
                    <div className="flex items-center gap-2 flex-wrap text-[11px] text-muted-foreground">
                      <span>Did this read your real problem right?</span>
                      {kpiSent.problem_detection === undefined ? (
                        <>
                          <button data-testid="kpi-problem-yes" onClick={() => sendKpi('problem_detection', true)}
                            className="rounded-full border border-border/70 px-2 py-0.5 hover:bg-secondary transition-colors">Yes</button>
                          <button data-testid="kpi-problem-no" onClick={() => sendKpi('problem_detection', false)}
                            className="rounded-full border border-border/70 px-2 py-0.5 hover:bg-secondary transition-colors">Not quite</button>
                        </>
                      ) : (
                        <span className="text-emerald-600">Noted, thank you.</span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 flex-wrap text-[11px] text-muted-foreground">
                      <span>Did this change or improve your decision?</span>
                      {kpiSent.decision_improvement === undefined ? (
                        <>
                          <button data-testid="kpi-improve-yes" onClick={() => sendKpi('decision_improvement', true)}
                            className="rounded-full border border-border/70 px-2 py-0.5 hover:bg-secondary transition-colors">Yes</button>
                          <button data-testid="kpi-improve-no" onClick={() => sendKpi('decision_improvement', false)}
                            className="rounded-full border border-border/70 px-2 py-0.5 hover:bg-secondary transition-colors">No</button>
                        </>
                      ) : (
                        <span className="text-emerald-600">Noted, thank you.</span>
                      )}
                    </div>
                  </div>
                )}

                <div className="pt-1 text-[11px] font-mono-plex text-muted-foreground/70">
                  {result.model} · {result.cost} credits · {result.tokens} tokens
                </div>

                {/* execution: commit with a deadline, track the timer, capture the result */}
                {result.decision_id && (
                  <div data-testid="brain-execution" className="pt-3 border-t border-border/60 space-y-3">
                    {!committed ? (
                      <>
                        <input
                          data-testid="brain-commit-input"
                          value={actionInput}
                          onChange={(e) => setActionInput(e.target.value)}
                          placeholder="Make it your move: the one thing you'll do next…"
                          className="w-full rounded-xl border border-border/70 bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                        />
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-[11px] uppercase tracking-wide text-muted-foreground flex items-center gap-1"><Clock size={12} /> Done by</span>
                          {DUE_OPTIONS.map((o) => (
                            <button key={o.hours} data-testid="brain-due-option"
                              onClick={() => setDueHours(o.hours)}
                              className={`text-xs rounded-full px-3 py-1 border transition-colors ${dueHours === o.hours ? 'bg-primary text-primary-foreground border-primary' : 'border-border/70 text-muted-foreground hover:text-foreground'}`}>
                              {o.label}
                            </button>
                          ))}
                          <Button data-testid="brain-commit-btn" onClick={commitMove}
                            disabled={execBusy || !actionInput.trim()} className="rounded-xl ml-auto shrink-0">
                            Commit it
                          </Button>
                        </div>
                      </>
                    ) : (
                      <div className="space-y-3">
                        <div className="flex items-center justify-between gap-3 flex-wrap">
                          <div className="text-sm min-w-0">
                            <span className="text-[11px] uppercase tracking-wide text-muted-foreground">Your move</span>
                            <p className={`${decisionStatus === 'done' ? 'line-through text-muted-foreground' : ''}`}>{committed}</p>
                          </div>
                          {decisionStatus !== 'done' && dueAt && (
                            <span data-testid="brain-countdown" className="text-xs font-mono-plex inline-flex items-center gap-1 text-[hsl(var(--ring))]">
                              <Clock size={12} /> {fmtLeft(dueAt)}
                            </span>
                          )}
                        </div>

                        {decisionStatus === 'done' ? (
                          <div className="rounded-xl border border-border/70 bg-secondary/40 px-4 py-3">
                            <span className="text-xs text-emerald-600 flex items-center gap-1 mb-2"><CheckCircle2 size={13} /> Achieved</span>
                            <Button data-testid="brain-next-step-btn" onClick={findNextStep} disabled={execBusy}
                              className="rounded-xl w-full sm:w-auto">
                              {execBusy ? <Loader2 size={15} className="animate-spin mr-2" /> : <ArrowRight size={15} className="mr-2" />}
                              Find my next step
                            </Button>
                          </div>
                        ) : showResult ? (
                          <div className="rounded-xl border border-border/70 bg-background px-3 py-3 space-y-2">
                            <textarea
                              data-testid="brain-result-input"
                              value={resultInput}
                              onChange={(e) => setResultInput(e.target.value)}
                              placeholder="What happened? The outcome in a line or two…"
                              className="w-full rounded-lg border border-border/70 bg-background px-3 py-2 text-sm min-h-[64px] focus:outline-none focus:ring-1 focus:ring-ring"
                            />
                            <div className="flex gap-2 justify-end">
                              <Button size="sm" variant="ghost" onClick={() => setShowResult(false)} disabled={execBusy} className="rounded-xl text-muted-foreground">Cancel</Button>
                              <Button data-testid="brain-result-save" size="sm" onClick={() => markStatus('done', resultInput)} disabled={execBusy} className="rounded-xl">Log result</Button>
                            </div>
                          </div>
                        ) : (
                          <div className="flex gap-2">
                            <Button data-testid="brain-mark-done" size="sm" onClick={() => setShowResult(true)} disabled={execBusy} className="rounded-xl">I did it</Button>
                            <Button size="sm" variant="ghost" onClick={() => markStatus('dropped')} disabled={execBusy} className="rounded-xl text-muted-foreground">Dropped it</Button>
                          </div>
                        )}
                      </div>
                    )}

                    {/* go deeper: continue the same connected session */}
                    {!committed && result.sharpening_question && (
                      <button data-testid="brain-sharpen" onClick={goDeeper}
                        className="text-sm text-[hsl(var(--ring))] hover:underline flex items-center gap-1.5 text-left">
                        <Sparkles size={13} /> {result.sharpening_question}
                      </button>
                    )}
                  </div>
                )}
              </article>
            )}
          </section>

          {/* ---------- sidebar: knowledge ---------- */}
          <aside className="lg:sticky lg:top-8 h-fit">
            <div className="rounded-2xl bg-card border border-border/70 p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <BookOpen size={15} strokeWidth={1.75} /> Knowledge
                </div>
                {canTrain && (
                  <button
                    data-testid="brain-train-button"
                    onClick={() => setTrainOpen(true)}
                    title="Set company rules"
                    className="text-muted-foreground hover:text-foreground transition-colors"
                  >
                    <SlidersHorizontal size={15} strokeWidth={1.75} />
                  </button>
                )}
              </div>

              {canTrain ? (
                <>
                  <input
                    ref={fileRef}
                    data-testid="brain-upload-input"
                    type="file"
                    className="hidden"
                    onChange={onFile}
                    accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.csv,.md,.markdown,.html,.htm,.json,.txt,.log"
                  />
                  <Button
                    data-testid="brain-upload-button"
                    variant="secondary"
                    onClick={() => fileRef.current?.click()}
                    disabled={uploading}
                    className="w-full rounded-xl border border-border/70 active:scale-[0.98]"
                  >
                    {uploading ? <Loader2 size={15} className="animate-spin" /> : <Upload size={15} strokeWidth={1.75} />}
                    <span className="ml-2">{uploading ? 'Uploading' : 'Add document'}</span>
                  </Button>
                  <p className="mt-2 text-[11px] text-muted-foreground leading-4">
                    PDF, Word, PowerPoint, Excel, CSV, text. It reads and indexes them so the brain can answer from them.
                  </p>
                </>
              ) : (
                <p data-testid="brain-member-note" className="text-[11px] text-muted-foreground leading-4">
                  This brain is trained by your workspace owner. Ask it anything on the left, the answers come from your team&apos;s knowledge.
                </p>
              )}

              <div className="mt-4 space-y-2">
                {docs.length === 0 && (
                  <p className="text-xs text-muted-foreground py-3 text-center">No documents yet.</p>
                )}
                {docs.map((d) => (
                  <div key={d.tree_id} data-testid="brain-doc-item"
                    className="group flex items-center gap-2 rounded-xl border border-border/70 px-3 py-2">
                    <FileText size={14} strokeWidth={1.75} className="shrink-0 text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <div className="text-xs truncate text-foreground/90" title={d.filename}>{d.filename}</div>
                      <div className="text-[10px] uppercase tracking-wide">
                        {d.status === 'processing' && <span className="text-[hsl(var(--warning))]">Indexing…</span>}
                        {d.status === 'ready' && <span className="text-[hsl(var(--success))]">Ready · {d.node_count} parts</span>}
                        {d.status === 'failed' && <span className="text-destructive">Failed</span>}
                      </div>
                    </div>
                    {canTrain && (
                      <button
                        onClick={() => delDoc(d.tree_id)}
                        className="shrink-0 text-muted-foreground/50 hover:text-destructive transition-colors opacity-0 group-hover:opacity-100"
                        title="Remove"
                      >
                        <X size={14} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </aside>
        </div>
      </main>

      {/* train dialog: admin sets company rules the brain must follow */}
      <Dialog open={trainOpen} onOpenChange={setTrainOpen}>
        <DialogContent className="rounded-2xl">
          <DialogHeader>
            <DialogTitle className="font-display">Train the brain</DialogTitle>
            <DialogDescription>
              Write the rules and priorities the brain must follow on every decision. No model training, no cost. It applies these instantly.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            data-testid="brain-rules-input"
            value={instructions}
            onChange={(e) => setInstructions(e.target.value)}
            placeholder={'e.g. Always follow our written refund policy. Never approve discounts above 10% without manager sign-off. Prioritise customer retention over a single sale.'}
            className="min-h-[140px] rounded-xl"
          />
          <DialogFooter>
            <Button variant="secondary" onClick={() => setTrainOpen(false)} className="rounded-xl border border-border/70">Cancel</Button>
            <Button data-testid="brain-rules-save" onClick={saveRules} disabled={savingRules} className="rounded-xl">
              {savingRules ? <Loader2 size={15} className="animate-spin mr-2" /> : null}
              Save rules
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
