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

  useEffect(() => {
    api.get('/goals').then((r) => setGoals(r.data.goals)).catch(() => setGoals([]));
  }, []);

  return (
    <div className="relative z-10 min-h-screen">
      <TopBar title="Your pursuits" />
      <main className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10">
        <div className="flex items-center justify-between mb-8">
          <p className="text-sm text-muted-foreground">One thread per goal. Each holds where you are, and what comes next.</p>
          <Button data-testid="goals-new-goal-button" onClick={() => navigate('/new')}
            className="rounded-xl active:scale-[0.98] transition-colors">
            New goal
          </Button>
        </div>

        {goals === null && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 lg:gap-6">
            <Skeleton className="h-44 rounded-2xl" />
            <Skeleton className="h-44 rounded-2xl" />
          </div>
        )}

        {goals !== null && goals.length === 0 && (
          <Card className="rounded-2xl border border-border/70 premium-lift">
            <CardContent className="p-12 text-center">
              <p className="font-display text-2xl mb-2">Nothing held yet.</p>
              <p className="text-sm text-muted-foreground mb-6 max-w-sm mx-auto">
                Name the one thing you keep circling. The engine will hold it with you, week after week.
              </p>
              <Button data-testid="empty-state-new-goal-button" onClick={() => navigate('/new')}
                className="rounded-xl active:scale-[0.98] transition-colors">
                Open your first thread
              </Button>
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
                  </div>
                  <Separator className="hairline mb-4" />
                  <p className="text-xs text-muted-foreground mb-1">Next action</p>
                  <p className="text-sm leading-5 line-clamp-2 mb-5">{g.next_action || '—'}</p>
                  <Button variant="secondary" data-testid="goal-card-open-button"
                    onClick={() => navigate(`/thread/${g.thread_id}`)}
                    className="rounded-xl border border-border/70 active:scale-[0.98] transition-colors w-full">
                    Open
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
