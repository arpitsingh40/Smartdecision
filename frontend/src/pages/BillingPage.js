import { useState, useEffect } from 'react';
import { toast } from 'sonner';
import { TopBar } from '../components/TopBar';
import { Button } from '../components/ui/button';
import { api } from '../lib/api';

const fmtDate = (iso) => {
  if (!iso) return '—';
  const d = new Date(iso.endsWith('Z') || iso.includes('+') ? iso : iso + 'Z');
  return d.toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
};

export default function BillingPage() {
  const [packs, setPacks] = useState([]);
  const [testMode, setTestMode] = useState(false);
  const [history, setHistory] = useState([]);
  const [buying, setBuying] = useState(null);

  useEffect(() => {
    api.get('/payments/packs').then((r) => { setPacks(r.data.packs); setTestMode(r.data.test_mode); }).catch(() => {});
    api.get('/payments/history').then((r) => setHistory(r.data.items)).catch(() => {});
  }, []);

  const buy = async (packId) => {
    setBuying(packId);
    try {
      const r = await api.post('/payments/create-order', { pack_id: packId });
      window.location.assign(r.data.checkout_url);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not start the payment. Try again.');
      setBuying(null);
    }
  };

  return (
    <div className="min-h-screen pb-16">
      <TopBar title="Buy credits" backTo="/" />
      <main className="max-w-3xl mx-auto px-4 sm:px-6 pt-8">
        {testMode && (
          <div data-testid="billing-test-banner" className="mb-6 rounded-xl border border-[hsl(var(--warning))]/40 bg-[hsl(var(--warning))]/10 px-4 py-2.5 text-xs text-foreground">
            Test mode — payments are simulated until the live gateway is connected. No money moves.
          </div>
        )}
        <p className="text-sm text-muted-foreground">One-time top-up, no subscription. A normal turn costs <span className="font-mono-plex">5</span> credits, ultra thinking costs <span className="font-mono-plex">10</span>.</p>
        <div className="grid sm:grid-cols-2 gap-4 mt-6">
          {packs.map((p) => (
            <div key={p.pack_id} data-testid={`pack-card-${p.pack_id}`}
              className={`relative bg-white border rounded-xl p-6 ${p.tag ? 'border-[hsl(var(--ring))]/50' : 'border-border/70'}`}>
              {p.tag && <span className="absolute -top-2.5 right-4 text-[10px] uppercase tracking-wider bg-[hsl(var(--accent))] border border-border/60 rounded-full px-2.5 py-0.5">{p.tag}</span>}
              <p className="font-display text-2xl">{p.credits} credits</p>
              <p className="font-mono-plex text-lg mt-2">₹{p.amount_inr}</p>
              <p className="text-[11px] text-muted-foreground mt-1">
                {Math.floor(p.credits / 5)} normal turns · {Math.floor(p.credits / 10)} ultra
              </p>
              <Button data-testid={`buy-${p.pack_id}`} onClick={() => buy(p.pack_id)} disabled={buying !== null}
                className="w-full mt-5 rounded-xl active:scale-[0.98]">
                {buying === p.pack_id ? 'Opening checkout…' : `Buy for ₹${p.amount_inr}`}
              </Button>
            </div>
          ))}
        </div>
        {history.length > 0 && (
          <div className="mt-10">
            <h2 className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground mb-3">Purchase history</h2>
            <div className="bg-white border border-border/70 rounded-xl divide-y divide-border/40" data-testid="purchase-history">
              {history.map((o) => (
                <div key={o.order_id} className="flex items-center justify-between px-4 py-3 text-[13px]">
                  <div>
                    <span>{o.credits} credits · ₹{o.amount_inr}</span>
                    <span className="block font-mono-plex text-[10px] text-muted-foreground">{fmtDate(o.created_at)}{o.test ? ' · test' : ''}</span>
                  </div>
                  <span className={`text-[11px] uppercase tracking-wider ${o.status === 'paid' ? 'text-[hsl(var(--success))]' : o.status === 'failed' ? 'text-[hsl(var(--destructive))]' : 'text-muted-foreground'}`}>{o.status}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
