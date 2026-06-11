import { useState, useEffect, useRef } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { api } from '../lib/api';
import { useAuth } from '../App';

export default function PaymentResultPage() {
  const [params] = useSearchParams();
  const orderId = params.get('order_id');
  const { setCredits } = useAuth();
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const attempts = useRef(0);
  const missingRef = !orderId;

  useEffect(() => {
    if (!orderId) return undefined;
    let timer;
    const check = async () => {
      try {
        const r = await api.get(`/payments/status/${orderId}`);
        if (r.data.status === 'paid') {
          setResult(r.data);
          setCredits(r.data.balance);
        } else if (r.data.status === 'failed') {
          setResult(r.data);
        } else if (attempts.current < 6) {
          attempts.current += 1;
          timer = setTimeout(check, 2500); // live mode: gateway confirmation can lag
        } else {
          setResult(r.data);
        }
      } catch {
        setError('Could not verify the payment. Your order history has the latest status.');
      }
    };
    check();
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId]);

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md bg-white border border-border/70 rounded-xl p-8 text-center">
        {missingRef && <p data-testid="payment-error" className="text-sm text-muted-foreground">Missing order reference.</p>}
        {!missingRef && error && <p data-testid="payment-error" className="text-sm text-muted-foreground">{error}</p>}
        {!missingRef && !error && !result && (
          <div data-testid="payment-verifying">
            <Loader2 size={28} strokeWidth={1.5} className="mx-auto animate-spin text-muted-foreground" />
            <p className="text-sm text-muted-foreground mt-4">Verifying your payment…</p>
          </div>
        )}
        {result && result.status === 'paid' && (
          <div data-testid="payment-success">
            <CheckCircle2 size={32} strokeWidth={1.5} className="mx-auto text-[hsl(var(--success))]" />
            <h1 className="font-display text-2xl mt-4">Credits added</h1>
            <p className="text-sm text-muted-foreground mt-2">
              <span className="font-mono-plex text-foreground">+{result.credits_added}</span> credits ·
              new balance <span data-testid="payment-new-balance" className="font-mono-plex text-foreground">{result.balance}</span>
            </p>
            <Button asChild className="mt-6 rounded-xl w-full"><Link to="/" data-testid="payment-back-home">Back to your pursuits</Link></Button>
          </div>
        )}
        {result && result.status !== 'paid' && (
          <div data-testid="payment-failed">
            <XCircle size={32} strokeWidth={1.5} className="mx-auto text-[hsl(var(--destructive))]" />
            <h1 className="font-display text-2xl mt-4">Payment not completed</h1>
            <p className="text-sm text-muted-foreground mt-2">You were not charged. No credits were added.</p>
            <Button asChild variant="outline" className="mt-6 rounded-xl w-full"><Link to="/billing" data-testid="payment-retry">Try again</Link></Button>
          </div>
        )}
      </div>
    </div>
  );
}
