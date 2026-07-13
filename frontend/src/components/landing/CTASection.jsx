import { useNavigate } from 'react-router-dom';
import { ArrowRight, Sparkles, Shield } from 'lucide-react';
import { Button } from '../ui/button';

export default function CTASection() {
  const navigate = useNavigate();

  return (
    <section className="relative py-32 sm:py-40 bg-[#0f1117] overflow-hidden">
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1200px] h-[1200px] rounded-full opacity-40"
          style={{ background: 'radial-gradient(circle at 30% 40%, rgba(184,145,101,0.12) 0%, rgba(47,143,138,0.06) 40%, transparent 65%)' }} />

        <div
          className="absolute -top-40 -right-40 w-[600px] h-[600px] rounded-full animate-scale-pulse"
          style={{
            background: 'radial-gradient(circle, rgba(184,145,101,0.04) 0%, transparent 60%)',
          }}
        />
        <div
          className="absolute -bottom-40 -left-40 w-[500px] h-[500px] rounded-full animate-scale-pulse-2"
          style={{
            background: 'radial-gradient(circle, rgba(47,143,138,0.04) 0%, transparent 60%)',
          }}
        />

        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[#b89165]/20 to-transparent" />
        <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[#b89165]/20 to-transparent" />

        <div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full border border-[#b89165]/5 animate-spin-slow"
        />
        <div
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full border border-[#2f8f8a]/5 animate-spin-reverse"
        />
      </div>

      <div className="relative max-w-3xl mx-auto px-6 text-center">
        <div
          className="inline-flex items-center gap-2 text-[11px] tracking-[0.26em] uppercase text-[#b89165] font-semibold mb-6"
        >
          <span className="animate-shake">
            <Sparkles size={13} />
          </span>
          Start your journey
        </div>

        <h2
          className="font-display text-5xl sm:text-6xl lg:text-[4.5rem] leading-[0.92] text-white tracking-tight"
        >
          Stop deciding.<br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#b89165] via-[#c9a86b] to-[#b89165]">
            Start doing.
          </span>
        </h2>

        <p
          className="mt-6 text-lg text-white/50 max-w-lg mx-auto leading-relaxed"
        >
          One goal. One action. Real progress — held across weeks.<br />
          Join the founders who stopped overthinking and started shipping.
        </p>

        <div
          className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <Button onClick={() => navigate('/auth')}
            className="group rounded-xl h-14 px-8 text-base font-medium bg-[#b89165] hover:bg-[#a67d52] text-white shadow-xl shadow-[#b89165]/25 relative overflow-hidden">
            <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer-slide" />
            <span className="relative z-10 flex items-center gap-2">
              Start your free trial
              <div className="animate-bounce-x">
                <ArrowRight size={16} strokeWidth={2} />
              </div>
            </span>
          </Button>
          <Button onClick={() => navigate('/auth')} variant="outline"
            className="rounded-xl h-14 px-8 text-base font-medium text-white/80 hover:text-white border-white/20 hover:border-white/40 bg-white/5 hover:bg-white/10">
            Sign in
          </Button>
        </div>

        <p
          className="mt-6 text-xs text-white/30 flex items-center justify-center gap-1.5"
        >
          <Shield size={14} className="opacity-50" />
          No credit card required · Cancel anytime
        </p>
      </div>
    </section>
  );
}
