import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { toast } from 'sonner';
import { Sparkles, Check } from 'lucide-react';
import { Button } from '../components/ui/button';
import { TopBar } from '../components/TopBar';
import { api } from '../lib/api';
import { trackPixel } from '../lib/pixel';

export default function BillingPage() {
  const [packs, setPacks] = useState([]);
  const [history, setHistory] = useState([]);
  const [busy, setBusy] = useState(null);
  const navigate = useNavigate();
  const [params] = useSearchParams();

  useEffect(() => {
    api.get('/payments/packs').then((r) => setPacks(r.data.packs)).catch(() => {});
    api.get('/payments/history').then((r) => setHistory(r.data.items)).catch(() => {});
  }, []);

  useEffect(() => {
    if (params.get('canceled') === '1') {
      toast.message('Checkout cancelled. No charge made.');
      navigate('/billing', { replace: true });
    }
  }, [params, navigate]);

  const buy = async (packId) => {
    if (busy) return;
    setBusy(packId);
    // Meta Pixel: InitiateCheckout — fires the moment user commits to a pack, before redirect.
    try {
      const pack = packs.find((p) => p.pack_id === packId);
      trackPixel('InitiateCheckout', {
        value: Number(pack?.amount_inr || 0),
        currency: 'INR',
        content_ids: [packId],
        content_type: 'product',
        num_items: 1,
      });
    } catch (_e) { /* noop */ }
    try {
      const r = await api.post('/payments/create-order', { pack_id: packId });
      window.location.assign(r.data.checkout_url);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not start checkout. Try again.');
      setBusy(null);
    }
  };

  return (
    <div className="relative z-10 min-h-screen">
      <TopBar title="Plans & credits" backTo="/" />
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-10">
        <div className="max-w-2xl">
          <p className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">Pricing</p>
          <h1 data-testid="billing-title" className="font-display text-3xl sm:text-4xl leading-tight">
            Pick the plan that matches how seriously you&apos;re pursuing this.
          </h1>
          <p className="mt-4 text-sm md:text-base text-muted-foreground leading-6">
            One-time top-ups, no subscription. Credits cover every conversation, every &ldquo;do it for me&rdquo; draft, and every file the engine reads with you.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-5 md:gap-6 mt-10">
          {packs.map((p) => {
            const isBest = p.tag === 'Best Value';
            return (
              <div key={p.pack_id} data-testid={`pack-card-${p.pack_id}`}
                className={`relative bg-white border rounded-2xl p-7 flex flex-col transition-all ${
                  isBest
                    ? 'border-foreground/40 shadow-[0_10px_40px_-12px_rgba(0,0,0,0.25)] md:scale-[1.03]'
                    : 'border-border/70'
                }`}>
                {isBest && (
                  <span data-testid={`pack-tag-${p.pack_id}`}
                    className="absolute -top-3 left-7 inline-flex items-center gap-1 text-[10px] uppercase tracking-[0.16em] bg-foreground text-background border border-foreground rounded-full px-3 py-1">
                    <Sparkles size={11} strokeWidth={2} /> {p.tag}
                  </span>
                )}
                <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{p.label}</p>
                <p className="text-xs text-muted-foreground mt-1">{p.headline}</p>
                <div className="mt-5 flex items-baseline gap-1.5">
                  <span className="font-display text-4xl">₹{p.amount_inr}</span>
                  <span className="text-xs text-muted-foreground">one-time</span>
                </div>
                <p data-testid={`pack-credits-${p.pack_id}`} className="font-mono-plex text-sm mt-1 text-foreground/80">
                  {p.credits} credits
                </p>

                <ul className="mt-5 space-y-2.5 text-sm leading-5 text-foreground/85 flex-1">
                  {(p.features || []).map((f, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <Check size={14} strokeWidth={2}
                        className={`mt-0.5 shrink-0 ${isBest ? 'text-foreground' : 'text-muted-foreground'}`} />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>

                <Button onClick={() => buy(p.pack_id)} disabled={busy === p.pack_id}
                  data-testid={`pack-buy-${p.pack_id}`}
                  className={`mt-6 rounded-xl w-full active:scale-[0.98] transition-colors ${
                    isBest ? '' : 'bg-white text-foreground border border-border/70 hover:bg-[hsl(var(--accent))]'
                  }`}>
                  {busy === p.pack_id ? 'Opening checkout…' : `Get ${p.label}`}
                </Button>
              </div>
            );
          })}
        </div>

        <p className="mt-6 text-[11px] text-muted-foreground/80 max-w-3xl">
          The Elite plan gives <span className="text-foreground font-mono-plex">10× the credits of Pro for 2.5× the price</span> — built for users who run multiple goals and attach files (PDFs, sheets, screenshots) to every turn.
        </p>

        {history.length > 0 && (
          <div className="mt-14">
            <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-3">Purchase history</p>
            <div data-testid="billing-history" className="bg-white border border-border/70 rounded-2xl divide-y divide-border/60">
              {history.map((o) => (
                <div key={o.order_id} data-testid={`history-row-${o.order_id}`} className="px-5 py-3 flex items-center justify-between text-sm">
                  <div className="flex flex-col">
                    <span className="font-mono-plex text-xs">{o.pack_id}</span>
                    <span className="text-[10px] text-muted-foreground">{new Date(o.created_at).toLocaleString()}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="font-mono-plex text-xs">+{o.credits} cr</span>
                    <span className="font-mono-plex text-xs">₹{o.amount_inr}</span>
                    <span data-testid={`history-status-${o.order_id}`}
                      className={`text-[10px] uppercase tracking-[0.14em] px-2 py-0.5 rounded-full border ${
                        o.status === 'paid' ? 'border-[hsl(var(--success))]/30 text-[hsl(var(--success))]'
                        : o.status === 'failed' ? 'border-[hsl(var(--destructive))]/30 text-[hsl(var(--destructive))]'
                        : 'border-border/70 text-muted-foreground'}`}>
                      {o.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
