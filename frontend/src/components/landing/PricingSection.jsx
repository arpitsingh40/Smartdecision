import { useNavigate } from 'react-router-dom';
import { Check, Sparkles, Zap } from 'lucide-react';
import { Button } from '../ui/button';

const PLANS = [
  {
    id: 'trial',
    label: 'Trial',
    price: '₹99',
    period: '3 days',
    tokens: '1M tokens',
    model: 'DeepSeek Flash',
    popular: false,
    features: [
      '1M tokens (enough for ~150 turns)',
      'DeepSeek Flash reasoning',
      'Ultra thinking mode',
      '3-day access',
      'UPI mandate setup',
    ],
  },
  {
    id: 'standard',
    label: 'Standard',
    price: '₹4,999',
    period: '/month',
    tokens: '10M tokens / mo',
    model: 'DeepSeek Flash',
    popular: false,
    features: [
      '10 million tokens per month',
      'DeepSeek Flash reasoning',
      'Ultra thinking mode',
      'Priority support',
      'Cancel anytime',
    ],
  },
  {
    id: 'pro',
    label: 'Pro',
    price: '₹9,999',
    period: '/month',
    tokens: '10M tokens / mo',
    model: 'DeepSeek V4',
    popular: true,
    features: [
      '10 million tokens per month',
      'DeepSeek V4 — best model',
      'Ultra thinking mode',
      'Priority support',
      'Cancel anytime',
    ],
  },
];

export default function PricingSection() {
  const navigate = useNavigate();

  return (
    <section id="pricing" className="relative py-24 sm:py-32 bg-[#0f1117]">
      <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-14">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <span className="inline-flex items-center gap-2 text-[11px] tracking-[0.26em] uppercase text-[#b89165] font-semibold mb-5">
            <span className="h-px w-8 bg-[#b89165]" />
            Pricing
          </span>
          <h2 className="font-display text-4xl sm:text-5xl text-white tracking-tight leading-[1.1]">
            Pick the plan that matches<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#b89165] via-[#c9a86b] to-[#b89165]">
              how seriously you&apos;re pursuing this.
            </span>
          </h2>
          <p className="mt-4 text-sm text-white/50 max-w-md mx-auto">
            Monthly subscription via UPI autopay. Unused tokens expire at the end of each billing period.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-5 md:gap-6 items-start">
          {PLANS.map((p) => (
            <div key={p.id}
              className={`relative rounded-2xl p-7 flex flex-col transition-all ${
                p.popular
                  ? 'bg-white border border-foreground/40 shadow-[0_10px_40px_-12px_rgba(0,0,0,0.3)] md:scale-[1.03]'
                  : 'bg-white/5 border border-white/10'
              }`}>
              {p.popular && (
                <span className="absolute -top-3 left-7 inline-flex items-center gap-1 text-[10px] uppercase tracking-[0.16em] bg-foreground text-background rounded-full px-3 py-1">
                  <Sparkles size={11} /> Best Value
                </span>
              )}

              <p className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{p.label}</p>

              <div className="mt-5 flex items-baseline gap-1.5">
                <span className={`font-display text-4xl ${p.popular ? 'text-[#0f1117]' : 'text-white'}`}>
                  {p.price}
                </span>
                <span className={`text-xs ${p.popular ? 'text-[#0f1117]/60' : 'text-white/40'}`}>
                  {p.period}
                </span>
              </div>

              <p className={`font-mono-plex text-sm mt-1 ${p.popular ? 'text-[#0f1117]/80' : 'text-white/60'}`}>
                {p.tokens}
              </p>
              <p className={`mt-1 text-[11px] font-mono-plex ${p.popular ? 'text-[#0f1117]/50' : 'text-white/40'}`}>
                {p.model}
              </p>

              <ul className="mt-5 space-y-2.5 text-sm leading-5 flex-1">
                {p.features.map((f, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <Check size={14} strokeWidth={2}
                      className={`mt-0.5 shrink-0 ${p.popular ? 'text-[#0f1117]' : 'text-white/40'}`} />
                    <span className={`${p.popular ? 'text-[#0f1117]/85' : 'text-white/70'}`}>{f}</span>
                  </li>
                ))}
              </ul>

              <Button onClick={() => navigate('/auth')}
                className={`mt-6 rounded-xl w-full active:scale-[0.98] ${
                  p.id === 'trial'
                    ? 'bg-[#b89165] hover:bg-[#a67d52] text-white'
                    : p.popular
                      ? 'bg-[#0f1117] hover:bg-[#1a1c26] text-white'
                      : 'border border-white/20 bg-white/5 hover:bg-white/10 text-white/80 hover:text-white'
                }`}>
                {p.id === 'trial' ? (
                  <><Zap size={14} className="mr-2" /> Start Trial</>
                ) : (
                  `Subscribe — ${p.price}${p.period}`
                )}
              </Button>
            </div>
          ))}
        </div>

        <p className="mt-6 text-[11px] text-white/30 text-center max-w-xl mx-auto">
          All plans include <strong className="text-white/50">UPI autopay</strong> billing. Your mandate is set up once and charges recur monthly. Cancel anytime from your UPI app.
        </p>
      </div>
    </section>
  );
}
