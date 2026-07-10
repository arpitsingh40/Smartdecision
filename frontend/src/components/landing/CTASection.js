import { useNavigate } from 'react-router-dom';
import { ArrowRight, Sparkles } from 'lucide-react';
import { Button } from '../ui/button';

export default function CTASection() {
  const navigate = useNavigate();

  return (
    <section className="relative py-28 sm:py-36 bg-[#0f1117] overflow-hidden">
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[1000px] rounded-full opacity-30"
          style={{ background: 'radial-gradient(circle at 30% 40%, rgba(184,145,101,0.15) 0%, rgba(47,143,138,0.08) 40%, transparent 65%)' }} />
        <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[#b89165]/30 to-transparent" />
      </div>

      <div className="relative max-w-3xl mx-auto px-6 text-center">
        <div className="inline-flex items-center gap-2 text-[11px] tracking-[0.26em] uppercase text-[#b89165] font-semibold mb-6">
          <Sparkles size={13} />
          Start your journey
        </div>

        <h2 className="font-display text-4xl sm:text-5xl lg:text-[4.5rem] leading-[0.92] text-white tracking-tight">
          Stop deciding.<br />Start doing.
        </h2>

        <p className="mt-6 text-lg text-white/50 max-w-lg mx-auto leading-relaxed">
          One goal. One action. Real progress — held across weeks.<br />
          Join the founders who stopped overthinking and started shipping.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Button onClick={() => navigate('/auth')}
            className="rounded-xl h-14 px-8 text-base font-medium bg-[#b89165] hover:bg-[#a67d52] text-white shadow-xl shadow-[#b89165]/25 group">
            Start your free trial
            <ArrowRight size={16} className="ml-2 group-hover:translate-x-0.5 transition-transform" strokeWidth={2} />
          </Button>
          <Button onClick={() => navigate('/auth')} variant="outline"
            className="rounded-xl h-14 px-8 text-base font-medium text-white/80 hover:text-white border-white/20 hover:border-white/40 bg-white/5 hover:bg-white/10">
            Sign in
          </Button>
        </div>

        <p className="mt-5 text-xs text-white/30 flex items-center justify-center gap-1.5">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="opacity-50">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
            <path d="M7 11V7a5 5 0 0 1 10 0v4" />
          </svg>
          No credit card required · Cancel anytime
        </p>
      </div>
    </section>
  );
}
