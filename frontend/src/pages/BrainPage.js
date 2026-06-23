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
  CheckCircle2, AlertCircle, Quote,
} from 'lucide-react';

const MODE_LABEL = { answer: 'Answer', decide: 'Decision', plan: 'Plan' };

export default function BrainPage() {
  const { setCredits } = useAuth();
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [docs, setDocs] = useState([]);
  const [canTrain, setCanTrain] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [trainOpen, setTrainOpen] = useState(false);
  const [instructions, setInstructions] = useState('');
  const [savingRules, setSavingRules] = useState(false);
  const fileRef = useRef(null);

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

  // poll only while a document is still indexing
  useEffect(() => {
    const hasProcessing = docs.some((d) => d.status === 'processing');
    if (!hasProcessing) return undefined;
    const id = setInterval(loadDocs, 4000);
    return () => clearInterval(id);
  }, [docs, loadDocs]);

  const ask = useCallback(async () => {
    if (!question.trim() || loading) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await api.post('/brain/ask', { question: question.trim() });
      setResult(r.data);
      if (r.data.credits != null) setCredits(r.data.credits);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Could not get an answer. Try again.');
    } finally {
      setLoading(false);
    }
  }, [question, loading, setCredits]);

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

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask(); }
  };

  const readyCount = docs.filter((d) => d.status === 'ready').length;

  return (
    <div className="min-h-screen">
      <TopBar title="Decision Brain" backTo="/" />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-8 lg:gap-10">

          {/* ---------- main column: ask + answer ---------- */}
          <section className="min-w-0">
            <h2 className="font-display text-3xl sm:text-4xl tracking-[-0.02em] leading-[1.05]">
              Ask your company&apos;s brain.
            </h2>
            <p className="mt-3 text-sm md:text-base text-muted-foreground leading-6 max-w-xl">
              Answers from your documents. Decisions in your favour. Plans that move the objective forward.
              Just type. It works out the rest.
            </p>

            {/* ask box */}
            <div className="mt-6 rounded-2xl bg-card border border-border/70 shadow-[0_1px_0_rgba(17,24,39,0.06),0_12px_30px_rgba(17,24,39,0.06)] p-3">
              <Textarea
                data-testid="brain-question-input"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="What's our refund window for damaged goods? · Should I approve this discount? · Plan our Q3 launch in Pune."
                className="min-h-[96px] border-0 bg-transparent focus-visible:ring-0 resize-none text-[15px] leading-6"
              />
              <div className="flex items-center justify-between px-1 pt-1">
                <span className="text-xs text-muted-foreground">
                  {readyCount > 0 ? `${readyCount} document${readyCount > 1 ? 's' : ''} in knowledge` : 'No documents yet — upload some on the right'}
                </span>
                <Button
                  data-testid="brain-ask-button"
                  onClick={ask}
                  disabled={loading || !question.trim()}
                  className="rounded-xl active:scale-[0.98]"
                >
                  {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} strokeWidth={1.75} />}
                  <span className="ml-2">{loading ? 'Thinking' : 'Ask'}</span>
                </Button>
              </div>
            </div>

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

                <div className="pt-1 text-[11px] font-mono-plex text-muted-foreground/70">
                  {result.model} · {result.cost} credits · {result.tokens} tokens
                </div>
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
