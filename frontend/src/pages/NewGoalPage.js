import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { TopBar } from '../components/TopBar';
import { api } from '../lib/api';
import { useAuth } from '../App';

export default function NewGoalPage() {
  const navigate = useNavigate();
  const { setCredits } = useAuth();
  const [params] = useSearchParams();
  const [title, setTitle] = useState('');
  const [whyNow, setWhyNow] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const t = params.get('title');
    const w = params.get('why');
    if (t) setTitle(decodeURIComponent(t));
    if (w) setWhyNow(decodeURIComponent(w));
  }, [params]);

  const create = async (e) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      const r = await api.post('/goals', { title, why_now: whyNow });
      setCredits(r.data.credits);
      navigate(`/thread/${r.data.thread.thread_id}`);
    } catch (err) {
      const msg = err.response?.status === 402
        ? 'Not enough credits to open a new thread.'
        : err.response?.data?.detail || 'Could not open the thread. Try again.';
      toast.error(msg);
      setBusy(false);
    }
  };

  return (
    <div className="relative z-10 min-h-screen">
      <TopBar title="New goal" backTo="/" />
      <main className="max-w-xl mx-auto px-4 sm:px-6 py-8 sm:py-10">
        <Card className="rounded-2xl border border-border/70 premium-lift">
          <CardContent className="p-8 sm:p-10">
            <h2 className="font-display text-3xl mb-2">Name it plainly.</h2>
            <p className="text-sm text-muted-foreground mb-8">
              Not the ideal version. The real one — the thing you keep circling.
            </p>
            <form onSubmit={create} className="space-y-6">
              <div className="space-y-1.5">
                <Label htmlFor="goal-title" className="text-xs">The goal</Label>
                <Input id="goal-title" required minLength={3} data-testid="new-goal-title-input"
                  value={title} onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Get my first paying client" className="rounded-xl" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="goal-why" className="text-xs">Why now — and what keeps getting in the way?</Label>
                <Textarea id="goal-why" required minLength={3} data-testid="new-goal-why-textarea"
                  value={whyNow} onChange={(e) => setWhyNow(e.target.value)}
                  placeholder="Say it the way you'd say it to yourself. The engine starts from your reality, not a plan."
                  className="rounded-xl min-h-[140px]" />
              </div>
              <Button type="submit" disabled={busy} data-testid="new-goal-create-button"
                className="w-full rounded-xl active:scale-[0.98] transition-colors">
                {busy ? 'Opening the thread… the engine is reading your situation' : 'Open the thread'}
              </Button>
              {busy && (
                <p aria-live="polite" className="text-xs text-muted-foreground text-center thinking-field">
                  This takes a few seconds — your first easiest path is being drawn.
                </p>
              )}
            </form>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
