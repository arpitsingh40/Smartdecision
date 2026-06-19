import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Wand2, Copy, Mail, MessageCircle, SlidersHorizontal, Paperclip, X as XIcon } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Textarea } from '../components/ui/textarea';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { ScrollArea } from '../components/ui/scroll-area';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '../components/ui/collapsible';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { Skeleton } from '../components/ui/skeleton';
import { toast } from 'sonner';
import { TopBar } from '../components/TopBar';
import { api } from '../lib/api';
import { useAuth } from '../App';

const fieldAnim = {
  initial: { opacity: 0, y: 4, filter: 'blur(2px)' },
  animate: { opacity: 1, y: 0, filter: 'blur(0px)' },
  transition: { duration: 0.32, ease: 'easeOut' },
};

const Field = ({ label, right, children, testId, refreshKey }) => (
  <div>
    <div className="flex items-baseline justify-between gap-3 mb-1.5">
      <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">{label}</p>
      {right}
    </div>
    <AnimatePresence mode="wait">
      <motion.div key={refreshKey} {...fieldAnim} data-testid={testId}>
        {children}
      </motion.div>
    </AnimatePresence>
  </div>
);

const ACTION_WINDOW_MS = 48 * 3600 * 1000;

const ADJUST_CHIPS = [
  { id: 'no-time', label: 'No time', phrase: "I don't have time for this step as written." },
  { id: 'blocked', label: 'Blocked by someone', phrase: "I'm blocked by someone else on this step." },
  { id: 'not-sure-how', label: 'Not sure how', phrase: "I'm not sure how to actually do this step." },
  { id: 'different-idea', label: 'I have a different idea', phrase: 'I have a different idea for this step.' },
];

const fmtRemaining = (ms) => {
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
};

export default function ThreadPage() {
  const { threadId } = useParams();
  const { setCredits } = useAuth();
  const [thread, setThread] = useState(null);
  const [reengagement, setReengagement] = useState(null);
  const [actionOverdue, setActionOverdue] = useState(false);
  const [message, setMessage] = useState('');
  const [mode, setMode] = useState('normal');
  const [thinking, setThinking] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [nowTick, setNowTick] = useState(() => Date.now());
  const [assistLoading, setAssistLoading] = useState(false);
  const [workbenchOpen, setWorkbenchOpen] = useState(false);
  const [adjustOpen, setAdjustOpen] = useState(false);
  const [adjustChip, setAdjustChip] = useState(null);
  const [adjustText, setAdjustText] = useState('');
  const [artifactEdit, setArtifactEdit] = useState(null); // { key, text } — local edits per generated artifact
  const [attachment, setAttachment] = useState(null); // { file, dataUrl, name, mime } | null
  const composerRef = useRef(null);
  const fileInputRef = useRef(null);

  const MAX_ATTACH_BYTES = 8 * 1024 * 1024; // 8 MB hard cap matches backend
  const ACCEPTED_TYPES = 'image/png,image/jpeg,image/jpg,image/webp,image/gif,application/pdf,.pdf,.xlsx,.xls,.csv,text/csv,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/plain,.txt';

  const pickFile = (file) => {
    if (!file) return;
    if (file.size > MAX_ATTACH_BYTES) {
      toast.error('File is too large. Keep it under 8 MB.');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setAttachment({
      name: file.name, mime: file.type || '', dataUrl: reader.result,
    });
    reader.onerror = () => toast.error('Could not read that file.');
    reader.readAsDataURL(file);
  };

  // live ticker for the action countdown (1-minute resolution)
  useEffect(() => {
    const id = setInterval(() => setNowTick(Date.now()), 30000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    // remember the most recently opened thread so post-payment redirect can take the user back here
    try { localStorage.setItem('sdg_last_thread', threadId); } catch { /* storage disabled — non-fatal */ }
    api.get(`/threads/${threadId}`).then((r) => {
      setThread(r.data.thread);
      setReengagement(r.data.reengagement_line);
      setActionOverdue(r.data.action_overdue);
    }).catch(() => toast.error('Thread not found.'));
  }, [threadId]);

  const sendText = useCallback(async (text, adjust = false) => {
    const msg = (text || '').trim();
    if (!msg || thinking) return false;
    setThinking(true);
    try {
      const body = { message: msg, mode: adjust ? 'normal' : mode, adjust };
      if (attachment && !adjust) {
        // strip the data URL prefix so the backend gets the raw base64
        const idx = (attachment.dataUrl || '').indexOf(',');
        body.attachment_base64 = idx >= 0 ? attachment.dataUrl.slice(idx + 1) : attachment.dataUrl;
        body.attachment_filename = attachment.name;
        body.attachment_mime = attachment.mime;
      }
      const r = await api.post(`/threads/${threadId}/turn`, body);
      setThread(r.data.thread);
      setCredits(r.data.credits);
      setMessage('');
      setAttachment(null);
      if (fileInputRef.current) fileInputRef.current.value = '';
      setReengagement(null);
      setActionOverdue(false);
      setRefreshKey((k) => k + 1);
      if (r.data.had_attachment) {
        toast.success(`Read your file — ${r.data.cost} credit${r.data.cost > 1 ? 's' : ''} (${(r.data.tokens || 0).toLocaleString()} tokens).`);
      }
      return true;
    } catch (err) {
      const msg402 = err.response?.status === 402;
      toast.error(msg402 ? 'Not enough credits for this turn.' : err.response?.data?.detail || 'The engine did not respond. Try again.');
      return false;
    } finally {
      setThinking(false);
    }
  }, [thinking, threadId, setCredits, mode, attachment]);

  const send = useCallback(() => sendText(message), [sendText, message]);

  const sendAdjust = useCallback(async () => {
    const chip = ADJUST_CHIPS.find((c) => c.id === adjustChip);
    const extra = adjustText.trim();
    if (!chip && !extra) return;
    const composed = `About the next action you gave me: ${chip ? chip.phrase + ' ' : ''}${extra}`.trim();
    const ok = await sendText(composed, true);
    if (ok) {
      setAdjustOpen(false);
      setAdjustChip(null);
      setAdjustText('');
      toast.success('Step reshaped around your input.');
    }
  }, [adjustChip, adjustText, sendText]);

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  const setStatus = async (status) => {
    try {
      await api.patch(`/threads/${threadId}/status`, { status });
      setThread((t) => ({ ...t, status }));
      toast.success(`Thread ${status}.`);
    } catch {
      toast.error('Could not update status.');
    }
  };

  // ---- "Do it for me": ship-ready artifact for the next action (1 credit / 1k tokens)
  const artifact = thread?.current_action_artifact || null;
  const artifactKey = artifact?.generated_at || null;
  const artifactText = (artifactEdit && artifactEdit.key === artifactKey) ? artifactEdit.text : (artifact?.artifact || '');

  const doItForMe = async () => {
    if (assistLoading || thinking) return;
    setAssistLoading(true);
    try {
      const r = await api.post(`/threads/${threadId}/complete-action`);
      setThread((t) => ({ ...t, current_action_artifact: r.data.artifact }));
      setCredits(r.data.credits);
      setWorkbenchOpen(true);
      toast.success(`Ready — ${r.data.cost} credit${r.data.cost > 1 ? 's' : ''} for ${(r.data.artifact.tokens || 0).toLocaleString()} tokens.`);
    } catch (err) {
      toast.error(err.response?.status === 402 ? 'Not enough credits.' : err.response?.data?.detail || 'Could not prepare this. Try again.');
    } finally {
      setAssistLoading(false);
    }
  };

  const copyArtifact = async () => {
    try {
      await navigator.clipboard.writeText(artifactText);
      toast.success('Copied — paste it where it needs to go.');
    } catch {
      toast.error('Copy failed — select the text and copy manually.');
    }
  };

  const mailtoHref = `mailto:?subject=${encodeURIComponent(artifact?.subject || artifact?.title || '')}&body=${encodeURIComponent(artifactText)}`;
  const waHref = `https://wa.me/?text=${encodeURIComponent(artifactText)}`;

  if (!thread) {
    return (
      <div className="relative z-10 min-h-screen">
        <TopBar title="…" backTo="/" />
        <main className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
          <Skeleton className="h-[420px] rounded-2xl" />
        </main>
      </div>
    );
  }

  const lastEngineMsg = [...(thread.messages || [])].reverse().find((m) => m.role === 'engine');
  const inactive = thread.status !== 'active';

  // countdown: arms automatically when an action is issued (each turn re-arms it)
  const deadline = thread.last_turn_at ? new Date(thread.last_turn_at).getTime() + ACTION_WINDOW_MS : null;
  const remainingMs = deadline ? deadline - nowTick : null;
  const windowClosed = remainingMs !== null ? remainingMs <= 0 : actionOverdue;

  return (
    <div className="relative z-10 min-h-screen">
      <TopBar title={thread.goal} backTo="/" />
      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Badge className="rounded-lg text-[11px] font-normal bg-[hsl(var(--accent))] text-foreground border border-border/70">
              {thread.status}
            </Badge>
            <span className="text-[11px] text-muted-foreground">{thread.rolling?.pace_calibration}</span>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" data-testid="thread-status-menu" className="rounded-xl text-xs text-muted-foreground">
                Manage <ChevronDown size={14} strokeWidth={1.75} className="ml-1" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="rounded-xl">
              {thread.status !== 'active' && <DropdownMenuItem data-testid="status-activate" onClick={() => setStatus('active')}>Reactivate</DropdownMenuItem>}
              {thread.status === 'active' && <DropdownMenuItem data-testid="status-pause" onClick={() => setStatus('paused')}>Pause</DropdownMenuItem>}
              <DropdownMenuItem data-testid="status-graduate" onClick={() => setStatus('graduated')}>{"Graduate — it's done"}</DropdownMenuItem>
              <DropdownMenuItem data-testid="status-release" onClick={() => setStatus('released')}>Release — let it go</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <Card className="rounded-2xl border border-border/70 premium-lift">
          <CardContent className="p-6 sm:p-8 space-y-6">
            {reengagement && (
              <p data-testid="reengagement-line"
                className="text-sm text-muted-foreground border-l-2 border-[hsl(var(--ring))]/40 pl-3 leading-6">
                {reengagement}
              </p>
            )}

            {windowClosed && !thinking && !inactive && (
              <div data-testid="accountability-prompt"
                className="rounded-xl border border-[hsl(var(--warning))]/30 bg-[hsl(var(--warning))]/5 px-4 py-3">
                <p className="text-sm leading-6 mb-3">
                  {"The 48-hour window on this action closed. What's the result?"}
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <Button size="sm" data-testid="accountability-done-button"
                    onClick={() => sendText('Done — I did it.')}
                    className="rounded-xl active:scale-[0.98] transition-colors">
                    I did it
                  </Button>
                  <Button size="sm" variant="secondary" data-testid="accountability-not-done-button"
                    onClick={() => sendText("I didn't do it yet — something got in the way.")}
                    className="rounded-xl border border-border/70 active:scale-[0.98] transition-colors">
                    Not yet
                  </Button>
                  <span className="text-xs text-muted-foreground">or type what actually happened below.</span>
                </div>
              </div>
            )}

            {lastEngineMsg && (
              <AnimatePresence mode="wait">
                <motion.div key={refreshKey + '-ack'} {...fieldAnim}>
                  <p data-testid="engine-acknowledgment"
                    className="font-display text-lg sm:text-xl leading-relaxed text-foreground">
                    {lastEngineMsg.text}
                  </p>
                  {thread.current_mirror && (
                    <p data-testid="engine-mirror"
                      className="mt-3 text-sm italic text-muted-foreground border-l-2 border-border pl-3 leading-6">
                      {thread.current_mirror}
                    </p>
                  )}
                </motion.div>
              </AnimatePresence>
            )}

            <Separator className="hairline" />

            <div className={thinking ? 'space-y-6 thinking-field' : 'space-y-6'}>
              <Field label="Current state" testId="situation-current-state" refreshKey={refreshKey}>
                <p className="text-sm md:text-base leading-6 whitespace-pre-line">{thread.current_state_summary}</p>
              </Field>

              <div className={thread.current_bold_move ? 'grid sm:grid-cols-2 gap-5 sm:gap-6' : ''}>
                <Field label="Easiest path" testId="situation-easiest-path" refreshKey={refreshKey}>
                  <p className="text-sm md:text-base leading-6">{thread.current_easiest_path}</p>
                </Field>
                {thread.current_bold_move && (
                  <Field label="The bolder play" testId="situation-bold-move" refreshKey={refreshKey}>
                    <p className="text-sm md:text-base leading-6 border-l-2 border-[hsl(var(--warning))]/50 pl-3">
                      {thread.current_bold_move}
                    </p>
                  </Field>
                )}
              </div>

              <Field label="Next action · 24–48h" testId="situation-next-action" refreshKey={refreshKey}
                right={!inactive && thread.current_next_action && remainingMs !== null ? (
                  remainingMs > 0 ? (
                    <span data-testid="action-countdown"
                      className={`font-mono-plex text-[11px] tabular-nums whitespace-nowrap ${remainingMs < 12 * 3600000 ? 'text-[hsl(var(--warning))]' : 'text-muted-foreground'}`}>
                      result due in {fmtRemaining(remainingMs)}
                    </span>
                  ) : (
                    <span data-testid="action-window-closed"
                      className="font-mono-plex text-[11px] whitespace-nowrap text-[hsl(var(--warning))]">
                      window closed
                    </span>
                  )
                ) : null}>
                {!thread.current_next_action ? (
                  <div data-testid="next-action-pending"
                    className="rounded-xl bg-[hsl(var(--accent))]/40 border border-border/50 border-dashed px-4 py-3">
                    <p className="text-sm leading-6 text-muted-foreground italic">
                      Still finding the real shape of this. No action locked in yet, keep talking.
                    </p>
                  </div>
                ) : (
                <div className="rounded-xl bg-[hsl(var(--accent))]/60 border border-border/70 px-4 py-3">
                  <p className={`leading-snug ${(thread.current_next_action || '').length > 80
                    ? 'text-[15px] md:text-base font-medium text-foreground'
                    : 'font-display text-base md:text-lg'}`}>
                    {thread.current_next_action}
                  </p>
                  {thread.current_action_payoff && (
                    <p data-testid="action-payoff" className="mt-2 text-sm leading-6 text-foreground/85">
                      <span className="text-[hsl(var(--ring))] mr-1.5" aria-hidden="true">↳</span>
                      {thread.current_action_payoff}
                    </p>
                  )}
                  {thread.current_big_picture && (
                    <p data-testid="action-big-picture" className="mt-2.5 pt-2.5 border-t border-border/60 text-xs leading-5 text-muted-foreground">
                      <span className="uppercase tracking-[0.12em] text-[10px] mr-2">Big picture</span>
                      {thread.current_big_picture}
                    </p>
                  )}
                  {thread.current_requested_input && (
                    <p data-testid="action-requested-input"
                      className="mt-2.5 pt-2.5 border-t border-border/60 text-xs leading-5 text-foreground/85 flex items-start gap-2">
                      <Paperclip size={11} strokeWidth={2} className="mt-0.5 shrink-0 text-[hsl(var(--ring))]" />
                      <span>
                        <span className="uppercase tracking-[0.12em] text-[10px] mr-2 text-[hsl(var(--ring))]">Bring back</span>
                        {thread.current_requested_input}
                      </span>
                    </p>
                  )}
                  {!inactive && (
                    <div className="mt-3 pt-3 border-t border-border/60 flex flex-wrap items-center justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Button size="sm" variant="secondary" data-testid="do-it-for-me-button"
                          onClick={artifact ? () => setWorkbenchOpen((o) => !o) : doItForMe}
                          disabled={assistLoading || thinking}
                          className="rounded-xl border border-border/70 bg-white active:scale-[0.98] transition-colors">
                          <Wand2 size={14} strokeWidth={1.75} className="mr-1.5" />
                          {assistLoading ? 'Preparing your draft…' : artifact ? (workbenchOpen ? 'Hide the draft' : 'Open the draft') : 'Do it for me'}
                        </Button>
                        <Button size="sm" variant="secondary" data-testid="adjust-step-button"
                          onClick={() => setAdjustOpen((o) => !o)} disabled={thinking}
                          aria-expanded={adjustOpen}
                          className="rounded-xl border border-border/70 bg-white active:scale-[0.98] transition-colors">
                          <SlidersHorizontal size={14} strokeWidth={1.75} className="mr-1.5" />
                          Adjust this step
                        </Button>
                      </div>
                    </div>
                  )}
                  {adjustOpen && !inactive && (
                    <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}
                      data-testid="adjust-panel" className="mt-3 pt-3 border-t border-border/60">
                      <p className="text-xs text-muted-foreground mb-2">
                        {"What's in the way — or what's your version of this step? The engine will reshape it around you."}
                      </p>
                      <div className="flex flex-wrap gap-1.5 mb-2.5">
                        {ADJUST_CHIPS.map((c) => (
                          <button key={c.id} type="button" data-testid={`adjust-chip-${c.id}`}
                            onClick={() => setAdjustChip((cur) => (cur === c.id ? null : c.id))}
                            disabled={thinking}
                            className={`px-2.5 py-1.5 rounded-lg text-[11px] border transition-colors ${
                              adjustChip === c.id
                                ? 'bg-foreground text-background border-transparent'
                                : 'bg-white border-border/70 text-muted-foreground hover:text-foreground'}`}>
                            {c.label}
                          </button>
                        ))}
                      </div>
                      <div className="flex items-center gap-2">
                        <input data-testid="adjust-input" value={adjustText}
                          onChange={(e) => setAdjustText(e.target.value)}
                          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); sendAdjust(); } }}
                          disabled={thinking} maxLength={300}
                          placeholder="Your obstacle, or your version of the step…"
                          className="flex-1 bg-white border border-border/70 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(var(--ring))]" />
                        <Button size="sm" data-testid="adjust-send-button"
                          onClick={sendAdjust} disabled={thinking || (!adjustChip && !adjustText.trim())}
                          className="rounded-xl shrink-0 active:scale-[0.98] transition-colors">
                          {thinking ? 'Reshaping…' : 'Reshape · 5'}
                        </Button>
                      </div>
                    </motion.div>
                  )}
                </div>
                )}
              </Field>

              {artifact && workbenchOpen && !inactive && (
                <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}
                  data-testid="action-workbench"
                  className="rounded-xl border border-[hsl(var(--ring))]/30 bg-white p-4 sm:p-5">
                  <div className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
                    <div className="flex items-baseline gap-2.5">
                      <p className="font-display text-base">{artifact.title}</p>
                      <span className="text-[10px] uppercase tracking-[0.12em] text-[hsl(var(--ring))]">
                        {artifact.kind === 'kit' ? '10-minute kit' : 'ship-ready draft'}
                      </span>
                    </div>
                    <span className="font-mono-plex text-[10px] text-muted-foreground">
                      {artifact.time_estimate_min ? `~${artifact.time_estimate_min} min` : ''}{artifact.cost ? ` · ${artifact.cost} cr` : ''}
                    </span>
                  </div>
                  <Textarea data-testid="workbench-artifact" value={artifactText}
                    onChange={(e) => setArtifactEdit({ key: artifactKey, text: e.target.value })}
                    className="min-h-[180px] rounded-xl bg-secondary/40 border border-border/70 text-sm leading-6 focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))]" />
                  {artifact.steps?.length > 0 && (
                    <ol className="mt-3 space-y-1">
                      {artifact.steps.map((s, i) => (
                        <li key={i} className="text-xs text-muted-foreground leading-5">
                          <span className="font-mono-plex text-[10px] text-[hsl(var(--ring))] mr-2">{String(i + 1).padStart(2, '0')}</span>{s}
                        </li>
                      ))}
                    </ol>
                  )}
                  <p className="mt-3 text-xs italic text-muted-foreground border-l-2 border-[hsl(var(--ring))]/40 pl-3 leading-5">
                    {artifact.handoff}
                  </p>
                  <div className="mt-4 flex flex-wrap items-center gap-2">
                    <Button size="sm" variant="secondary" data-testid="workbench-copy" onClick={copyArtifact}
                      className="rounded-xl border border-border/70 active:scale-[0.98]">
                      <Copy size={13} strokeWidth={1.75} className="mr-1.5" /> Copy
                    </Button>
                    {(artifact.channel === 'email' || artifact.subject) && (
                      <Button size="sm" variant="secondary" asChild className="rounded-xl border border-border/70 active:scale-[0.98]">
                        <a data-testid="workbench-mailto" href={mailtoHref}>
                          <Mail size={13} strokeWidth={1.75} className="mr-1.5" /> Open in email
                        </a>
                      </Button>
                    )}
                    {artifact.channel === 'whatsapp' && (
                      <Button size="sm" variant="secondary" asChild className="rounded-xl border border-border/70 active:scale-[0.98]">
                        <a data-testid="workbench-whatsapp" href={waHref} target="_blank" rel="noreferrer">
                          <MessageCircle size={13} strokeWidth={1.75} className="mr-1.5" /> Send on WhatsApp
                        </a>
                      </Button>
                    )}
                    <Button size="sm" data-testid="workbench-shipped-button"
                      onClick={() => { setWorkbenchOpen(false); sendText('Done — I shipped it.'); }}
                      disabled={thinking}
                      className="rounded-xl ml-auto active:scale-[0.98]">
                      I shipped it
                    </Button>
                  </div>
                </motion.div>
              )}

              {thread.skip_list?.length > 0 && (
                <Field label="Ignore for now" testId="situation-skip-list" refreshKey={refreshKey}>
                  <p className="text-xs text-muted-foreground leading-5">{thread.skip_list.join(' · ')}</p>
                </Field>
              )}
            </div>

            <Separator className="hairline" />

            <div>
              <p data-testid="situation-open-question" className="text-sm text-muted-foreground italic mb-3">
                {thread.current_open_question}
              </p>
              {thinking && (
                <p data-testid="engine-thinking-state" aria-live="polite"
                  className="text-xs text-muted-foreground mb-2 thinking-field">
                  {mode === 'ultra' ? 'Ultra thinking… going deeper before answering.' : 'Processing… the situation is being re-read.'}
                </p>
              )}
              <Textarea ref={composerRef} data-testid="composer-textarea"
                value={message} onChange={(e) => setMessage(e.target.value)} onKeyDown={onKeyDown}
                disabled={thinking || inactive}
                placeholder={inactive ? `This thread is ${thread.status}. Reactivate it to continue.` : 'Say where things actually are. Attach a file, photo, or screenshot if it helps. Enter to send · Shift+Enter for a new line.'}
                className="min-h-[96px] rounded-xl bg-white border border-border/70 focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))]" />

              {attachment && (
                <div data-testid="attachment-preview"
                  className="mt-2 flex items-center justify-between gap-3 px-3 py-2 rounded-xl bg-[hsl(var(--accent))]/40 border border-border/60">
                  <div className="flex items-center gap-2 min-w-0">
                    <Paperclip size={13} strokeWidth={1.75} className="text-muted-foreground shrink-0" />
                    <span className="text-xs truncate text-foreground/85">{attachment.name}</span>
                    <span className="text-[10px] text-muted-foreground shrink-0 font-mono-plex">
                      {(attachment.mime || '').split('/')[1]?.toUpperCase() || 'FILE'}
                    </span>
                  </div>
                  <button type="button" data-testid="attachment-clear"
                    onClick={() => { setAttachment(null); if (fileInputRef.current) fileInputRef.current.value = ''; }}
                    className="text-muted-foreground hover:text-foreground transition-colors p-1 -m-1 rounded"
                    aria-label="Remove attachment">
                    <XIcon size={13} strokeWidth={2} />
                  </button>
                </div>
              )}

              <input ref={fileInputRef} type="file" data-testid="attachment-file-input"
                className="hidden" accept={ACCEPTED_TYPES}
                onChange={(e) => pickFile(e.target.files?.[0])} />

              <div className="flex items-center justify-between mt-3 gap-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <button type="button" data-testid="attachment-button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={thinking || inactive}
                    title="Attach file, photo, PDF or spreadsheet"
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border border-border/70 bg-white text-[11px] text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50">
                    <Paperclip size={12} strokeWidth={1.75} />
                    {attachment ? 'Replace file' : 'Attach file or photo'}
                  </button>
                  <div data-testid="mode-toggle"
                    className="flex items-center rounded-xl border border-border/70 bg-white p-0.5">
                    <button type="button" data-testid="mode-normal-button"
                      onClick={() => setMode('normal')} disabled={thinking}
                      className={`px-2.5 py-1 rounded-lg text-[11px] transition-colors ${mode === 'normal' ? 'bg-[hsl(var(--accent))] text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>
                      Normal
                    </button>
                    <button type="button" data-testid="mode-ultra-button"
                      onClick={() => setMode('ultra')} disabled={thinking}
                      className={`px-2.5 py-1 rounded-lg text-[11px] transition-colors ${mode === 'ultra' ? 'bg-[hsl(var(--accent))] text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>
                      Ultra thinking
                    </button>
                  </div>
                </div>
                <Button onClick={send} disabled={thinking || inactive || !message.trim()}
                  data-testid="composer-send-button" className="rounded-xl active:scale-[0.98] transition-colors">
                  {thinking ? 'Thinking…' : 'Send'}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Collapsible open={historyOpen} onOpenChange={setHistoryOpen} className="mt-6">
          <CollapsibleTrigger asChild>
            <Button variant="secondary" data-testid="history-toggle-button" aria-expanded={historyOpen}
              className="rounded-xl border border-border/70 w-full text-xs text-muted-foreground active:scale-[0.98] transition-colors">
              {historyOpen ? <ChevronUp size={14} strokeWidth={1.75} className="mr-2" /> : <ChevronDown size={14} strokeWidth={1.75} className="mr-2" />}
              {historyOpen ? 'Hide history' : 'Show history'}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <Card className="mt-3 rounded-2xl border border-border/70">
              <ScrollArea data-testid="history-scroll-area" className="max-h-96 overflow-y-auto">
                <div className="p-6 space-y-5">
                  {(thread.messages || []).map((m, i) => (
                    <div key={i}>
                      <p className="font-mono-plex text-[10px] text-muted-foreground mb-1">
                        {m.role === 'user' ? 'you' : 'engine'} · {new Date(m.at).toLocaleString()}
                      </p>
                      <p className="text-sm leading-6">{m.text}</p>
                    </div>
                  ))}
                  {(!thread.messages || thread.messages.length === 0) && (
                    <p className="text-xs text-muted-foreground">No history yet.</p>
                  )}
                </div>
              </ScrollArea>
            </Card>
          </CollapsibleContent>
        </Collapsible>
      </main>
    </div>
  );
}
