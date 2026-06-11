import { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Button } from '../components/ui/button';
import { api } from '../lib/api';

/** TEST MODE ONLY — stands in for the Zoho hosted checkout until live keys are added. */
export default function TestCheckoutPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const orderId = params.get('order_id');
  const [order, setOrder] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!orderId) return;
    api.get(`/payments/status/${orderId}`).then((r) => setOrder(r.data)).catch(() => toast.error('Order not found.'));
  }, [orderId]);

  const complete = async (outcome) => {
    setBusy(true);
    try {
      await api.post('/payments/test-complete', { order_id: orderId, outcome });
      navigate(`/pay/result?order_id=${orderId}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Simulation failed.');
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div data-testid="test-checkout-banner" className="rounded-t-xl border border-b-0 border-[hsl(var(--warning))]/40 bg-[hsl(var(--warning))]/10 px-5 py-2 text-[11px] uppercase tracking-[0.12em] text-center">
          Simulated gateway — test mode
        </div>
        <div className="bg-white border border-border/70 rounded-b-xl p-6">
          <p className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground">SmartDecigen top-up</p>
          {order ? (
            <>
              <p className="font-display text-2xl mt-2">{order.credits_added} credits</p>
              <p className="font-mono-plex text-lg mt-1">₹{order.amount_inr}</p>
            </>
          ) : (
            <p className="text-sm text-muted-foreground mt-3">Loading order…</p>
          )}
          <div className="mt-6 space-y-2.5">
            <Button data-testid="simulate-success-button" onClick={() => complete('success')} disabled={busy || !order}
              className="w-full rounded-xl">
              Simulate successful payment
            </Button>
            <Button data-testid="simulate-failure-button" onClick={() => complete('failure')} disabled={busy || !order}
              variant="outline" className="w-full rounded-xl">
              Simulate failed payment
            </Button>
          </div>
          <p className="text-[11px] text-muted-foreground mt-4 text-center">In live mode this screen is the Zoho hosted checkout.</p>
        </div>
      </div>
    </div>
  );
}
