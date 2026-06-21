import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronDown, Wand2, Copy, Mail, MessageCircle, Paperclip, X as XIcon,
  ArrowRight, MapPin, Lightbulb, Sparkles, CheckCircle2, FileText,
} from 'lucide-react';
import { Textarea } from '../components/ui/textarea';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '../components/ui/dropdown-menu';
import { Skeleton } from '../components/ui/skeleton';
import { toast } from 'sonner';
import { TopBar } from '../components/TopBar';
import { api } from '../lib/api';
import { useAuth } from '../App';

const ACTION_WINDOW_MS = 48 * 3600 * 1000;
const MAX_ATTACH_BYTES = 8 * 1024 * 1024;
const ACCEPTED_TYPES = [
  'image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/gif',
  'application/pdf', '.pdf',
  '.xlsx', '.xls', '.csv', 'text/csv',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document', '.docx',
  'application/vnd.openxmlformats-officedocument.presentationml.presentation', '.pptx',
  'text/plain', '.txt', '.md', '.markdown', '.json', '.html', '.htm', '.log',
  '.py', '.js', '.ts', '.tsx', '.jsx', '.yaml', '.yml', '.sql',
].join(',');

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
const fmtTime = (iso) => {
  try { return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }); }
  catch { return ''; }
};

// ---------- subcomponents kept tiny on purpose ----------

const UserBubble = ({ text, at }) => (
  <div className="flex justify-end" data-testid="chat-bubble-user">
    <div className="max-w-[78%] rounded-2xl rounded-br-md bg-[hsl(var(--accent))] px-4 py-3 border border-border/60">
      <p className="text-[15px] leading-6 whitespace-pre-wrap text-foreground">{text}</p>
      <p className="text-[10px] text-muted-foreground mt-1.5 text-right font-mono-plex">{fmtTime(at)}</p>
    </div>
  </div>
);

const EngineBubble = ({ children, at }) => (
  <div className="flex justify-start" data-testid="chat-bubble-engine">
    <div className="max-w-[88%] rounded-2xl rounded-bl-md bg-white px-5 py-4 border border-border/70 shadow-sm">
      {children}
      {at && <p className="text-[10px] text-muted-foreground mt-2 font-mono-plex">{fmtTime(at)}</p>}
    </div>
  </div>
);

const ActionCard = ({ nextAction, payoff, bigPic, remainingMs, onDid, onAdjust, onDraft, thinking, inactive, drafting }) => (
  <div data-testid="action-card-inline"
    className="mt-4 rounded-xl bg-[hsl(var(--accent))]/55 border border-border/70 px-4 py-3.5">
    <div className="flex items-center justify-between gap-3 mb-1">
      <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Next move · 24-48h</p>
      {remainingMs !== null && (
        remainingMs > 0
          ? <span data-testid="action-countdown" className={`font-mono-plex text-[10px] whitespace-nowrap ${remainingMs < 12 * 3600000 ? 'text-[hsl(var(--warning))]' : 'text-muted-foreground'}`}>
              {fmtRemaining(remainingMs)} left
            </span>
          : <span data-testid="action-window-closed" className="font-mono-plex text-[10px] text-[hsl(var(--warning))]">window closed</span>
      )}
    </div>
    <p className="text-[15px] leading-6 font-medium">{nextAction}</p>
    {payoff && (
      <p className="mt-2 text-sm leading-5 text-foreground/80">
        <span className="text-muted-foreground">Payoff: </span>{payoff}
      </p>
    )}
    {bigPic && (
      <p className="mt-1 text-xs text-muted-foreground italic leading-5">{bigPic}</p>
    )}
    <div className="mt-3 flex flex-wrap items-center gap-2">
      <Button size="sm" data-testid="action-mark-done-button" disabled={thinking || inactive} onClick={onDid}
        className="rounded-lg h-8 px-3 text-xs active:scale-[0.98]">
        <CheckCircle2 size={12} strokeWidth={2} className="mr-1.5" /> I did it
      </Button>
      <Button size="sm" variant="secondary" data-testid="action-adjust-button" disabled={thinking || inactive} onClick={onAdjust}
        className="rounded-lg h-8 px-3 text-xs border border-border/70 active:scale-[0.98]">
        Adjust
      </Button>
      <Button size="sm" variant="secondary" data-testid="action-draft-button" disabled={drafting || thinking || inactive} onClick={onDraft}
        className="rounded-lg h-8 px-3 text-xs border border-border/70 active:scale-[0.98]">
        <Wand2 size={12} strokeWidth={2} className="mr-1.5" /> {drafting ? 'Drafting…' : 'Do it for me'}
      </Button>
    </div>
  </div>
);

const OutboxCard = ({ text }) => (
  <div data-testid="outbox-card"
    className="mt-3 rounded-xl border border-dashed border-[hsl(var(--ring))]/40 bg-[hsl(var(--ring))]/[0.04] px-4 py-3">
    <div className="flex items-baseline gap-2 mb-1">
      <Lightbulb size={12} strokeWidth={2} className="text-[hsl(var(--ring))] shrink-0 translate-y-0.5" />
      <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Or, the outside-the-box play</p>
    </div>
    <p className="text-sm leading-6 text-foreground/90">{text}</p>
  </div>
);

const Artifact = ({ artifact, text, onCopy, onShipped, mailtoHref, waHref, thinking }) => (
  <div data-testid="workbench-panel"
    className="mt-3 rounded-xl border border-border/70 bg-[hsl(var(--secondary))] px-4 py-3">
    <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground mb-2 flex items-center gap-1.5">
      <Sparkles size={12} strokeWidth={2} className="text-[hsl(var(--ring))]" /> Ready to ship
      {artifact.subject && <span className="text-foreground/85 normal-case tracking-normal ml-2">{artifact.subject}</span>}
    </p>
    <p className="text-sm leading-6 whitespace-pre-line">{text}</p>
    {artifact.handoff && (
      <p className="mt-2 text-xs italic text-muted-foreground border-l-2 border-[hsl(var(--ring))]/40 pl-3 leading-5">{artifact.handoff}</p>
    )}
    <div className="mt-3 flex flex-wrap items-center gap-2">
      <Button size="sm" variant="secondary" data-testid="workbench-copy" onClick={onCopy}
        className="rounded-lg h-8 px-3 text-xs border border-border/70 active:scale-[0.98]">
        <Copy size={12} strokeWidth={2} className="mr-1.5" /> Copy
      </Button>
      {(artifact.channel === 'email' || artifact.subject) && (
        <Button size="sm" variant="secondary" asChild className="rounded-lg h-8 px-3 text-xs border border-border/70 active:scale-[0.98]">
          <a data-testid="workbench-mailto" href={mailtoHref}>
            <Mail size={12} strokeWidth={2} className="mr-1.5" /> Email
          </a>
        </Button>
      )}
      {artifact.channel === 'whatsapp' && (
        <Button size="sm" variant="secondary" asChild className="rounded-lg h-8 px-3 text-xs border border-border/70 active:scale-[0.98]">
          <a data-testid="workbench-whatsapp" href={waHref} target="_blank" rel="noreferrer">
            <MessageCircle size={12} strokeWidth={2} className="mr-1.5" /> WhatsApp
          </a>
        </Button>
      )}
      <Button size="sm" data-testid="workbench-shipped-button" onClick={onShipped} disabled={thinking}
        className="rounded-lg h-8 px-3 text-xs ml-auto active:scale-[0.98]">
        <CheckCircle2 size={12} strokeWidth={2} className="mr-1.5" /> I shipped it
      </Button>
    </div>
  </div>
);

// ---------- main page ----------

export default function ThreadPage() {
  const { threadId } = useParams();
  const { setCredits } = useAuth();
  const [thread, setThread] = useState(null);
  const [reengagement, setReengagement] = useState(null);
  const [actionOverdue, setActionOverdue] = useState(false);
  const [message, setMessage] = useState('');
  const [mode, setMode] = useState('normal');
  const [thinking, setThinking] = useState(false);
  const [assistLoading, setAssistLoading] = useState(false);
  const [nowTick, setNowTick] = useState(() => Date.now());
  const [adjustOpen, setAdjustOpen] = useState(false);
  const [adjustChip, setAdjustChip] = useState(null);
  const [adjustText, setAdjustText] = useState('');
  const [artifactEdit, setArtifactEdit] = useState(null);
  const [attachment, setAttachment] = useState(null);
  const fileInputRef = useRef(null);
  const scrollEndRef = useRef(null);

  // load thread once
  useEffect(() => {
    try { localStorage.setItem('sdg_last_thread', threadId); } catch { /* */ }
    api.get(`/threads/${threadId}`).then((r) => {
      setThread(r.data.thread);
      setReengagement(r.data.reengagement_line);
      setActionOverdue(r.data.action_overdue);
    }).catch(() => toast.error('Thread not found.'));
  }, [threadId]);

  // countdown ticker
  useEffect(() => {
    const id = setInterval(() => setNowTick(Date.now()), 30000);
    return () => clearInterval(id);
  }, []);

  // auto-scroll to bottom when messages or thinking changes
  useEffect(() => {
    scrollEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [thread?.messages?.length, thinking]);

  const pickFile = (file) => {
    if (!file) return;
    if (file.size > MAX_ATTACH_BYTES) {
      toast.error('File is too large. Keep it under 8 MB.');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setAttachment({ name: file.name, mime: file.type || '', dataUrl: reader.result });
    reader.onerror = () => toast.error('Could not read that file.');
    reader.readAsDataURL(file);
  };

  const sendText = useCallback(async (text, adjust = false) => {
    const msg = (text || '').trim();
    if (!msg || thinking) return false;
    setThinking(true);
    try {
      const body = { message: msg, mode: adjust ? 'normal' : mode, adjust };
      if (attachment && !adjust) {
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
      if (r.data.had_attachment) {
        toast.success(`Read your file — ${r.data.cost} credit${r.data.cost > 1 ? 's' : ''} (${(r.data.tokens || 0).toLocaleString()} tokens).`);
      }
      return true;
    } catch (err) {
      toast.error(err.response?.status === 402 ? 'Not enough credits for this turn.'
        : err.response?.data?.detail || 'The engine did not respond. Try again.');
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

  const messages = thread.messages || [];
  // find index of the latest engine message — only it gets the structured trailer
  let lastEngineIdx = -1;
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === 'engine') { lastEngineIdx = i; break; }
  }
  const inactive = thread.status !== 'active';
  const deadline = thread.last_turn_at ? new Date(thread.last_turn_at).getTime() + ACTION_WINDOW_MS : null;
  const remainingMs = deadline ? deadline - nowTick : null;
  const windowClosed = remainingMs !== null ? remainingMs <= 0 : actionOverdue;
  const geoCity = thread.user_geo?.city;
  const geoCountry = thread.user_geo?.country;
  const showGeo = geoCity && geoCity !== 'Unknown' && geoCity !== 'Local';

  return (
    <div className="relative z-10 min-h-screen">
      <TopBar title={thread.goal} backTo="/" />
      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-8 flex flex-col" style={{ minHeight: 'calc(100vh - 64px)' }}>

        {/* status strip */}
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge data-testid="thread-status-badge"
              className="rounded-lg text-[11px] font-normal bg-[hsl(var(--accent))] text-foreground border border-border/70">
              {thread.status}
            </Badge>
            <span className="text-[11px] text-muted-foreground">{thread.rolling?.pace_calibration}</span>
            {showGeo && (
              <span data-testid="thread-geo-pill"
                className="inline-flex items-center gap-1 text-[10px] text-muted-foreground font-mono-plex">
                <MapPin size={10} strokeWidth={2} /> {geoCity}, {geoCountry}
              </span>
            )}
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

        {/* chat scroll feed — primary surface */}
        <div data-testid="chat-feed" className="flex-1 overflow-y-auto rounded-2xl border border-border/60 bg-[hsl(var(--background))]/30 px-3 sm:px-5 py-5 space-y-4 mb-3">
          {reengagement && (
            <div data-testid="reengagement-line" className="rounded-xl border border-border/60 bg-[hsl(var(--accent))]/40 px-4 py-3">
              <p className="text-sm text-muted-foreground leading-6">{reengagement}</p>
            </div>
          )}
          {windowClosed && !thinking && !inactive && (
            <div data-testid="accountability-prompt"
              className="rounded-xl border border-[hsl(var(--warning))]/30 bg-[hsl(var(--warning))]/5 px-4 py-3">
              <p className="text-sm leading-6 mb-3">The 48-hour window on this action closed. What is the result?</p>
              <div className="flex flex-wrap items-center gap-2">
                <Button size="sm" data-testid="accountability-done-button"
                  onClick={() => sendText('Done — I did it.')}
                  className="rounded-xl active:scale-[0.98]">I did it</Button>
                <Button size="sm" variant="secondary" data-testid="accountability-not-done-button"
                  onClick={() => sendText("I didn't do it yet — something got in the way.")}
                  className="rounded-xl border border-border/70 active:scale-[0.98]">Not yet</Button>
              </div>
            </div>
          )}

          {messages.length === 0 && (
            <p data-testid="empty-chat-hint" className="text-center text-sm text-muted-foreground py-8">
              Start typing below. The engine will read first, then ask one thing at a time.
            </p>
          )}

          <AnimatePresence initial={false}>
            {messages.map((m, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.22, ease: 'easeOut' }}>
                {m.role === 'user' ? (
                  <UserBubble text={m.text} at={m.at} />
                ) : (
                  <EngineBubble at={m.at}>
                    <p data-testid={i === lastEngineIdx ? 'engine-acknowledgment' : undefined}
                      className="text-[15px] leading-6 whitespace-pre-wrap">{m.text}</p>
                    {i === lastEngineIdx && thread.current_mirror && (
                      <p data-testid="engine-mirror"
                        className="mt-3 text-sm italic text-muted-foreground border-l-2 border-border pl-3 leading-6">
                        {thread.current_mirror}
                      </p>
                    )}
                    {i === lastEngineIdx && thread.current_next_action && (
                      <ActionCard
                        nextAction={thread.current_next_action}
                        payoff={thread.current_action_payoff}
                        bigPic={thread.current_big_picture}
                        remainingMs={remainingMs}
                        thinking={thinking}
                        drafting={assistLoading}
                        inactive={inactive}
                        onDid={() => sendText('Done — I did it.')}
                        onAdjust={() => setAdjustOpen((v) => !v)}
                        onDraft={doItForMe}
                      />
                    )}
                    {i === lastEngineIdx && thread.current_outbox && (
                      <OutboxCard text={thread.current_outbox} />
                    )}
                    {i === lastEngineIdx && adjustOpen && (
                      <div data-testid="adjust-panel"
                        className="mt-3 rounded-xl border border-border/70 bg-white px-4 py-3">
                        <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground mb-2">What is getting in the way?</p>
                        <div className="flex flex-wrap gap-1.5 mb-2">
                          {ADJUST_CHIPS.map((c) => (
                            <button key={c.id} type="button" data-testid={`adjust-chip-${c.id}`}
                              onClick={() => setAdjustChip((s) => s === c.id ? null : c.id)}
                              className={`px-2.5 py-1 rounded-lg text-[11px] border transition-colors ${adjustChip === c.id ? 'border-[hsl(var(--ring))] bg-[hsl(var(--ring))]/10' : 'border-border/60 bg-white hover:bg-[hsl(var(--accent))]/40'}`}>
                              {c.label}
                            </button>
                          ))}
                        </div>
                        <Textarea data-testid="adjust-text"
                          value={adjustText} onChange={(e) => setAdjustText(e.target.value)}
                          placeholder="Add anything specific (optional)…"
                          className="min-h-[64px] rounded-xl bg-white border-border/70 text-sm" />
                        <div className="mt-2 flex items-center justify-end gap-2">
                          <Button size="sm" variant="secondary" onClick={() => setAdjustOpen(false)}
                            className="rounded-lg h-8 px-3 text-xs border border-border/70">Cancel</Button>
                          <Button size="sm" data-testid="adjust-send-button" onClick={sendAdjust}
                            disabled={!adjustChip && !adjustText.trim()}
                            className="rounded-lg h-8 px-3 text-xs">Reshape it</Button>
                        </div>
                      </div>
                    )}
                    {i === lastEngineIdx && artifact && (
                      <Artifact artifact={artifact} text={artifactText}
                        onCopy={copyArtifact}
                        onShipped={() => sendText('Done — I shipped it.')}
                        mailtoHref={mailtoHref} waHref={waHref} thinking={thinking} />
                    )}
                    {i === lastEngineIdx && thread.current_open_question && thread.current_open_question !== '(none yet)' && (
                      <p data-testid="engine-open-question"
                        className="mt-4 text-sm italic text-foreground/80 border-l-2 border-[hsl(var(--ring))]/50 pl-3 leading-6">
                        {thread.current_open_question}
                      </p>
                    )}
                  </EngineBubble>
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          {thinking && (
            <div className="flex justify-start" data-testid="engine-thinking-state">
              <div className="rounded-2xl rounded-bl-md bg-white border border-border/70 px-5 py-3">
                <p className="text-sm text-muted-foreground italic">
                  {mode === 'ultra' ? 'Ultra thinking…' : 'Reading what you said…'}
                </p>
              </div>
            </div>
          )}
          <div ref={scrollEndRef} />
        </div>

        {/* composer */}
        <div className="rounded-2xl border border-border/70 bg-white p-3 sm:p-4 shadow-sm">
          <Textarea data-testid="composer-textarea"
            value={message} onChange={(e) => setMessage(e.target.value)} onKeyDown={onKeyDown}
            disabled={thinking || inactive}
            placeholder={inactive ? `This thread is ${thread.status}. Reactivate it to continue.` : 'Say where things actually are. Attach a file if it helps. Enter to send · Shift+Enter for a new line.'}
            className="min-h-[68px] rounded-xl bg-white border-border/60 text-[15px] leading-6 focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))]" />
          {attachment && (
            <div data-testid="attachment-preview"
              className="mt-2 flex items-center justify-between gap-3 px-3 py-2 rounded-xl bg-[hsl(var(--accent))]/40 border border-border/60">
              <div className="flex items-center gap-2 min-w-0">
                <FileText size={13} strokeWidth={1.75} className="text-muted-foreground shrink-0" />
                <span className="text-xs truncate text-foreground/85">{attachment.name}</span>
                <span className="text-[10px] text-muted-foreground shrink-0 font-mono-plex">
                  {(attachment.mime || '').split('/')[1]?.toUpperCase() || 'FILE'}
                </span>
              </div>
              <button type="button" data-testid="attachment-clear"
                onClick={() => { setAttachment(null); if (fileInputRef.current) fileInputRef.current.value = ''; }}
                className="text-muted-foreground hover:text-foreground p-1 -m-1 rounded" aria-label="Remove attachment">
                <XIcon size={13} strokeWidth={2} />
              </button>
            </div>
          )}
          <input ref={fileInputRef} type="file" data-testid="attachment-file-input"
            className="hidden" accept={ACCEPTED_TYPES}
            onChange={(e) => pickFile(e.target.files?.[0])} />
          <div className="flex items-center justify-between mt-2 gap-3">
            <div className="flex items-center gap-2 flex-wrap">
              <button type="button" data-testid="attachment-button"
                onClick={() => fileInputRef.current?.click()} disabled={thinking || inactive}
                title="Attach file, PDF, doc, sheet, image"
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border border-border/70 bg-white text-[11px] text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50">
                <Paperclip size={12} strokeWidth={1.75} />
                {attachment ? 'Replace' : 'Attach'}
              </button>
              <div data-testid="mode-toggle"
                className="flex items-center rounded-xl border border-border/70 bg-white p-0.5">
                <button type="button" data-testid="mode-normal-button" onClick={() => setMode('normal')} disabled={thinking}
                  className={`px-2.5 py-1 rounded-lg text-[11px] transition-colors ${mode === 'normal' ? 'bg-[hsl(var(--accent))] text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>Normal</button>
                <button type="button" data-testid="mode-ultra-button" onClick={() => setMode('ultra')} disabled={thinking}
                  className={`px-2.5 py-1 rounded-lg text-[11px] transition-colors ${mode === 'ultra' ? 'bg-[hsl(var(--accent))] text-foreground' : 'text-muted-foreground hover:text-foreground'}`}>Ultra thinking</button>
              </div>
            </div>
            <Button onClick={send} disabled={thinking || inactive || !message.trim()} data-testid="composer-send-button"
              className="rounded-xl h-10 px-4 active:scale-[0.98] transition-colors">
              {thinking ? 'Thinking…' : <><span>Send</span><ArrowRight size={14} strokeWidth={1.75} className="ml-1.5" /></>}
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
