import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Separator } from '../components/ui/separator';
import { Skeleton } from '../components/ui/skeleton';
import { TopBar } from '../components/TopBar';
import { api } from '../lib/api';

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

export default function DashboardPage() {
  const navigate = useNavigate();
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
        {goals?.length !== 0 && (
          <div className="flex items-center justify-between mb-8">
            <p className="text-sm text-muted-foreground">One thread per goal. Each holds where you are, and what comes next.</p>
            <Button data-testid="goals-new-goal-button" onClick={() => navigate('/new')}
              className="rounded-xl active:scale-[0.98] transition-colors">
              New goal
            </Button>
          </div>
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
                The goal you keep circling?
                <span className="block italic mt-1">Bring it here.</span>
              </h2>
              <p className="rise-3 text-sm sm:text-[15px] text-muted-foreground leading-relaxed max-w-md mx-auto mt-5">
                Not another chat that forgets you by morning. One thread holds your pursuit
                across weeks — and every reply ends in a single action you can finish in 48 hours.
              </p>
              <div className="rise-3 grid grid-cols-1 sm:grid-cols-3 gap-7 sm:gap-0 max-w-2xl mx-auto mt-11 sm:divide-x sm:divide-border/60">
                {[
                  ['01', 'Name it', 'The thing you keep postponing, in your own words.'],
                  ['02', 'Move in 48 hours', 'Every reply converges to one concrete next action.'],
                  ['03', 'Be remembered', 'Return anytime — it knows what changed while you were gone.'],
                ].map(([n, title, line]) => (
                  <div key={n} className="px-4">
                    <p className="font-mono-plex text-[11px] text-[hsl(var(--ring))] mb-1.5">{n}</p>
                    <p className="text-sm font-medium">{title}</p>
                    <p className="text-xs text-muted-foreground leading-relaxed mt-1">{line}</p>
                  </div>
                ))}
              </div>
              <div className="rise-4 mt-11">
                <Button data-testid="empty-state-new-goal-button" size="lg" onClick={() => navigate('/new')}
                  className="rounded-xl px-8 h-12 text-[15px] shadow-md hover:shadow-lg active:scale-[0.98] transition-all">
                  Open your first thread
                </Button>
                <p className="font-mono-plex text-[11px] text-muted-foreground mt-3.5">
                  2 minutes to start · 100 free credits — your first 20 moves
                </p>
              </div>
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
