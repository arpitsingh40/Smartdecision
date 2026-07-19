import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Navbar from '../components/landing/Navbar';
import HowItWorks from '../components/landing/HowItWorks';
import FeaturesSection from '../components/landing/FeaturesSection';
import TestimonialsCarousel from '../components/landing/TestimonialsCarousel';
import CTASection from '../components/landing/CTASection';
import PricingSection from '../components/landing/PricingSection';
import DemoSection from '../components/landing/DemoSection';
import Footer from '../components/landing/Footer';
import AnimateIn from '../components/AnimateIn';
import { Button } from '../components/ui/button';

function ParticleCanvas({ mousePos }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animId;
    let w, h;

    const resize = () => {
      w = canvas.width = window.innerWidth;
      h = canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener('resize', resize, { passive: true });

    const COUNT = 90;
    const particles = Array.from({ length: COUNT }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      r: Math.random() * 2 + 0.5,
      baseVx: (Math.random() - 0.5) * 0.3,
      baseVy: (Math.random() - 0.5) * 0.3,
    }));

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      const mx = mousePos?.current?.x ?? -1000;
      const my = mousePos?.current?.y ?? -1000;

      for (const p of particles) {
        const dx = p.x - mx;
        const dy = p.y - my;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 150) {
          p.vx += (dx / dist) * 0.04;
          p.vy += (dy / dist) * 0.04;
        }
        p.vx += (p.baseVx - p.vx) * 0.01;
        p.vy += (p.baseVy - p.vy) * 0.01;
        p.x += p.vx;
        p.y += p.vy;

        if (p.x < 0 || p.x > w) p.vx *= -1;
        if (p.y < 0 || p.y > h) p.vy *= -1;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(184, 145, 101, 0.3)';
        ctx.fill();

        for (const q of particles) {
          const dx2 = p.x - q.x;
          const dy2 = p.y - q.y;
          const dist2 = Math.sqrt(dx2 * dx2 + dy2 * dy2);
          if (dist2 < 160) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(q.x, q.y);
            ctx.strokeStyle = `rgba(47, 143, 138, ${0.05 * (1 - dist2 / 160)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
        if (dist < 250) {
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(mx, my);
          ctx.strokeStyle = `rgba(184, 145, 101, ${0.03 * (1 - dist / 250)})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
      animId = requestAnimationFrame(draw);
    };
    draw();
    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, [mousePos]);

  return (
    <canvas ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ opacity: 0.5 }}
    />
  );
}

function StatsBar() {
  // ponytail: honest commitments, not invented metrics
  const stats = [
    { num: '1', suffix: '', label: 'LLM call per turn. Zero-waste routing.' },
    { num: '170+', suffix: '', label: 'Book-derived reasoning lenses' },
    { num: '12', suffix: '', label: 'Autonomous executive agents' },
    { num: '1,403', suffix: '', label: 'Tools via execution runtime' },
  ];

  return (
    <section className="relative py-16 sm:py-20 bg-[#0f1117] border-y border-white/[0.04]">
      <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-14">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-8 sm:gap-12">
          {stats.map((s) => (
            <div key={s.label} className="text-center">
              <div className="font-display text-3xl sm:text-4xl text-white tracking-tight">
                {s.num}{s.suffix}
              </div>
              <div className="text-[11px] tracking-[0.15em] uppercase text-white/35 mt-2">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function FloatingOrbs() {
  return (
    <div className="fixed inset-0 pointer-events-none z-0">
      <div
        className="absolute top-[15%] -left-32 w-[600px] h-[600px] rounded-full"
        style={{
          background: 'radial-gradient(circle, rgba(184,145,101,0.06) 0%, transparent 70%)',
        }}
      />
      <div
        className="absolute top-[40%] -right-32 w-[500px] h-[500px] rounded-full"
        style={{
          background: 'radial-gradient(circle, rgba(47,143,138,0.05) 0%, transparent 70%)',
        }}
      />
    </div>
  );
}

function InfinitySymbol({ className }) {
  return (
    <svg width="24" height="24" viewBox="0 0 32 32" fill="none" className={className}>
      <path d="M22 8.5 A7 7 0 0 0 10 8.5 Q10 13 16 15.5 Q22 18 22 22.5 A7 7 0 0 1 10 22.5" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" fill="none" />
      <path d="M9 21 L11 22.7 L9 24.4" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  );
}

function AnimatedOrb() {
  return (
    <div
      className="hidden lg:block absolute right-14 top-1/2 -translate-y-1/2"
      style={{ transformStyle: 'preserve-3d' }}
    >
      <div className="relative w-[300px] h-[300px] animate-spin-slow">
        <div
          className="absolute inset-0 rounded-full cursor-pointer"
          onMouseMove={(e) => {
            const el = e.currentTarget;
            const r = el.getBoundingClientRect();
            const x = (e.clientX - r.left) / r.width - 0.5;
            const y = (e.clientY - r.top) / r.height - 0.5;
            el.style.transform = `perspective(1000px) rotateY(${x * 15}deg) rotateX(${-y * 15}deg)`;
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'perspective(1000px) rotateY(0deg) rotateX(0deg)';
          }}
          style={{ transformStyle: 'preserve-3d' }}
        >
          <div className="absolute inset-0 rounded-full"
            style={{
              background: 'conic-gradient(from 0deg, rgba(184,145,101,0.12), rgba(47,143,138,0.08), rgba(184,145,101,0.20), rgba(47,143,138,0.08), rgba(184,145,101,0.12))',
              filter: 'blur(50px)',
            }}
          />
          <div
            className="absolute inset-6 rounded-full border border-[#b89165]/15 animate-pulse-soft"
            style={{
              background: 'radial-gradient(circle at 35% 35%, rgba(184,145,101,0.08) 0%, transparent 60%)',
              boxShadow: 'inset 0 0 80px rgba(184,145,101,0.03)',
            }}
          />
          <div
            className="absolute inset-12 rounded-full border border-[#b89165]/10 animate-spin-reverse"
            style={{
              boxShadow: '0 0 40px rgba(184,145,101,0.05)',
            }}
          />
          <div className="absolute inset-[40%] flex items-center justify-center">
            <div className="animate-pulse-soft" style={{ animationDuration: '4s' }}>
              <InfinitySymbol className="w-10 h-10 text-[#b89165]/50" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LandingPage() {
  const navigate = useNavigate();
  const mousePos = useRef({ x: -1000, y: -1000 });

  useEffect(() => {
    const onMouse = (e) => {
      mousePos.current = { x: e.clientX, y: e.clientY };
    };
    window.addEventListener('mousemove', onMouse, { passive: true });
    return () => window.removeEventListener('mousemove', onMouse);
  }, []);

  return (
    <>
      <div className="fixed top-0 left-0 right-0 z-[60] h-[2px]"
        style={{
          background: 'linear-gradient(90deg, #b89165, #c9a86b, #2f8f8a, #b89165)',
          backgroundSize: '200% 100%',
        }}
      />
      <div className="bg-[#0f1117]">
        <Navbar />

        {/* Hero */}
        <section className="relative min-h-screen flex items-center overflow-hidden">
          <ParticleCanvas mousePos={mousePos} />

          <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
            <div className="absolute top-1/4 -left-32 w-[500px] h-[500px] rounded-full opacity-40"
              style={{ background: 'radial-gradient(circle, rgba(184,145,101,0.10) 0%, transparent 60%)' }} />
            <div className="absolute bottom-1/4 -right-32 w-[600px] h-[600px] rounded-full opacity-30"
              style={{ background: 'radial-gradient(circle, rgba(47,143,138,0.08) 0%, transparent 60%)' }} />
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full opacity-10"
              style={{ background: 'radial-gradient(circle, rgba(184,145,101,0.05) 0%, transparent 50%)' }} />
          </div>

          <div className="relative w-full max-w-7xl mx-auto px-6 sm:px-10 lg:px-14 pt-32 pb-20">
            <div className="max-w-3xl">
              <div>
                <span className="inline-flex items-center gap-2 text-[11px] tracking-[0.26em] uppercase text-[#b89165] font-semibold mb-6">
                  <span className="h-px bg-[#b89165] animate-pulse-width" />
                  AI Chief of Staff
                </span>
              </div>

              <h1 className="font-display text-6xl sm:text-7xl lg:text-[5.5rem] leading-[0.9] text-white tracking-tight">
                For founders who are<br />
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#b89165] via-[#c9a86b] to-[#b89165] bg-[length:200%_100%]"
                  style={{
                    animation: 'shimmer 3s ease-in-out infinite',
                  }}
                >
                  tired of guessing
                </span>
                .
              </h1>

              <p className="mt-6 text-lg sm:text-xl text-white/50 max-w-xl leading-relaxed">
                <span className="text-white/80 font-medium">SmartDeciGen</span> pressure-tests your assumptions and holds you
                accountable for the one decision that actually moves the needle.
              </p>

              <div className="mt-10 flex flex-col sm:flex-row items-start gap-4">
                <Button onClick={() => navigate('/auth')}
                  className="group rounded-xl h-14 px-8 text-base font-medium bg-[#b89165] hover:bg-[#a67d52] text-white shadow-xl shadow-[#b89165]/25 relative overflow-hidden">
                  <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent animate-shimmer-slide" />
                  <span className="relative z-10 flex items-center gap-2">
                    Try 50 decisions free
                    <svg className="animate-bounce-x" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
                  </span>
                </Button>
                <Button onClick={() => navigate('/auth')} variant="outline"
                  className="rounded-xl h-14 px-8 text-base font-medium text-white/70 hover:text-white border-white/20 hover:border-white/40 bg-white/5 hover:bg-white/10">
                  Sign in
                </Button>
              </div>

              <div className="mt-8 flex items-center gap-5 text-xs text-white/30">
                <span className="flex items-center gap-1.5">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#b89165]/60">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                  50 free decisions
                </span>
                <span className="w-1 h-1 rounded-full bg-white/20" />
                <span className="flex items-center gap-1.5">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#2f8f8a]/60">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                  No card
                </span>
                <span className="w-1 h-1 rounded-full bg-white/20" />
                <span className="flex items-center gap-1.5">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[#b89165]/60">
                    <circle cx="12" cy="12" r="10" />
                    <path d="M12 6v6l4 2" />
                  </svg>
                  Cancel anytime
                </span>
              </div>
            </div>

            <AnimatedOrb />
          </div>

          {/* Scroll indicator */}
          <div className="absolute bottom-8 left-1/2 -translate-x-1/2">
            <div className="w-5 h-8 rounded-full border border-white/20 flex items-start justify-center pt-2 animate-float">
              <div className="w-1 h-2 rounded-full bg-white/40 animate-bounce-y" />
            </div>
          </div>
        </section>

        <AnimateIn><StatsBar /></AnimateIn>
        <AnimateIn delay={0.1}><HowItWorks /></AnimateIn>
        <AnimateIn delay={0.2}><FeaturesSection /></AnimateIn>
        <AnimateIn delay={0.1}><DemoSection /></AnimateIn>
        <AnimateIn delay={0.2}><TestimonialsCarousel /></AnimateIn>
        <AnimateIn delay={0.1}><PricingSection /></AnimateIn>
        <AnimateIn delay={0.2}><CTASection /></AnimateIn>
        <Footer />
      </div>

      <style>{`
        @keyframes shimmer {
          0%, 100% { background-position: 0% center; }
          50% { background-position: 100% center; }
        }
      `}</style>
    </>
  );
}
