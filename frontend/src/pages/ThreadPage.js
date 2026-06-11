import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp } from 'lucide-react';
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

const Field = ({ label, children, testId, refreshKey }) => (
  <div>
    <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground mb-1.5">{label}</p>
    <AnimatePresence mode="wait">
      <motion.div key={refreshKey} {...fieldAnim} data-testid={testId}>
        {children}
      </motion.div>
    </AnimatePresence>
  </div>
);

export default function ThreadPage() {
  const { threadId } = useParams();
  const { setCredits } = useAuth();
  const [thread, setThread] = useState(null);
  const [reengagement, setReengagement] = useState(null);
  const [actionOverdue, setActionOverdue] = useState(false);
  const [message, setMessage] = useState('');
  const [thinking, setThinking] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const [historyOpen, setHistoryOpen] = useState(false);
  const composerRef = useRef(null);

  useEffect(() => {
    api.get(`/threads/${threadId}`).then((r) => {
      setThread(r.data.thread);
      setReengagement(r.data.reengagement_line);
      setActionOverdue(r.data.action_overdue);
    }).catch(() => toast.error('Thread not found.'));
  }, [threadId]);

  const sendText = useCallback(async (text) => {
    const msg = (text || '').trim();
    if (!msg || thinking) return;
    setThinking(true);
    try {
      const r = await api.post(`/threads/${threadId}/turn`, { message: msg });
      setThread(r.data.thread);
      setCredits(r.data.credits);
      setMessage('');
      setReengagement(null);
      setActionOverdue(false);
      setRefreshKey((k) => k + 1);
    } catch (err) {
      const msg402 = err.response?.status === 402;
      toast.error(msg402 ? 'Not enough credits for this turn.' : err.response?.data?.detail || 'The engine did not respond. Try again.');
    } finally {
      setThinking(false);
    }
  }, [thinking, threadId, setCredits]);

  const send = useCallback(() => sendText(message), [sendText, message]);

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
              <DropdownMenuItem data-testid="status-graduate" onClick={() => setStatus('graduated')}>Graduate — it's done</DropdownMenuItem>
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

            {actionOverdue && !thinking && !inactive && (
              <div data-testid="accountability-prompt"
                className="rounded-xl border border-[hsl(var(--warning))]/30 bg-[hsl(var(--warning))]/5 px-4 py-3">
                <p className="text-sm leading-6 mb-3">
                  The 48-hour window on your last action has passed. Did it happen?
                </p>
                <div className="flex gap-2">
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
                </div>
              </div>
            )}

            {lastEngineMsg && (
              <AnimatePresence mode="wait">
                <motion.p key={refreshKey + '-ack'} {...fieldAnim} data-testid="engine-acknowledgment"
                  className="font-display text-lg sm:text-xl leading-relaxed text-foreground">
                  {lastEngineMsg.text}
                </motion.p>
              </AnimatePresence>
            )}

            <Separator className="hairline" />

            <div className={thinking ? 'space-y-6 thinking-field' : 'space-y-6'}>
              <Field label="Current state" testId="situation-current-state" refreshKey={refreshKey}>
                <p className="text-sm md:text-base leading-6 whitespace-pre-line">{thread.current_state_summary}</p>
              </Field>

              <Field label="Easiest path" testId="situation-easiest-path" refreshKey={refreshKey}>
                <p className="text-sm md:text-base leading-6">{thread.current_easiest_path}</p>
              </Field>

              <Field label="Next action · 24–48h" testId="situation-next-action" refreshKey={refreshKey}>
                <div className="rounded-xl bg-[hsl(var(--accent))]/60 border border-border/70 px-4 py-3">
                  <p className="font-display text-base md:text-lg leading-snug">{thread.current_next_action}</p>
                </div>
              </Field>

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
                  Processing… the situation is being re-read.
                </p>
              )}
              <Textarea ref={composerRef} data-testid="composer-textarea"
                value={message} onChange={(e) => setMessage(e.target.value)} onKeyDown={onKeyDown}
                disabled={thinking || inactive}
                placeholder={inactive ? `This thread is ${thread.status}. Reactivate it to continue.` : 'Say where things actually are. Enter to send · Shift+Enter for a new line.'}
                className="min-h-[96px] rounded-xl bg-white border border-border/70 focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))]" />
              <div className="flex justify-end mt-3">
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
