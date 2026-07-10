import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import Navbar from '../components/landing/Navbar';
import HowItWorks from '../components/landing/HowItWorks';
import FeaturesSection from '../components/landing/FeaturesSection';
import TestimonialsCarousel from '../components/landing/TestimonialsCarousel';
import CTASection from '../components/landing/CTASection';
import Footer from '../components/landing/Footer';
import { Button } from '../components/ui/button';

function ParticleCanvas() {
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

    const COUNT = 60;
    const particles = Array.from({ length: COUNT }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      r: Math.random() * 1.5 + 0.5,
    }));

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > w) p.vx *= -1;
        if (p.y < 0 || p.y > h) p.vy *= -1;

        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(184, 145, 101, 0.3)';
        ctx.fill();

        for (const q of particles) {
          const dx = p.x - q.x;
          const dy = p.y - q.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 150) {
            ctx.beginPath();
            ctx.moveTo(p.x, p.y);
            ctx.lineTo(q.x, q.y);
            ctx.strokeStyle = `rgba(47, 143, 138, ${0.06 * (1 - dist / 150)})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }
      animId = requestAnimationFrame(draw);
    };
    draw();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', resize);
    };
  }, []);

  return (
    <canvas ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ opacity: 0.6 }}
    />
  );
}

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="bg-[#0f1117]">
      <Navbar />

      {/* Hero */}
      <section className="relative min-h-screen flex items-center overflow-hidden">
        <ParticleCanvas />

        <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
          <div className="absolute top-1/4 -left-32 w-[500px] h-[500px] rounded-full opacity-40"
            style={{ background: 'radial-gradient(circle, rgba(184,145,101,0.12) 0%, transparent 60%)' }} />
          <div className="absolute bottom-1/4 -right-32 w-[600px] h-[600px] rounded-full opacity-30"
            style={{ background: 'radial-gradient(circle, rgba(47,143,138,0.10) 0%, transparent 60%)' }} />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] rounded-full opacity-20"
            style={{ background: 'radial-gradient(circle, rgba(184,145,101,0.06) 0%, transparent 50%)' }} />
        </div>

        <div className="relative w-full max-w-7xl mx-auto px-6 sm:px-10 lg:px-14 pt-32 pb-20">
          <div className="max-w-3xl">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, ease: [0.25, 0.1, 0.25, 1] }}
            >
              <span className="inline-flex items-center gap-2 text-[11px] tracking-[0.26em] uppercase text-[#b89165] font-semibold mb-6">
                <span className="w-7 h-px bg-[#b89165]" />
                AI Chief of Staff
              </span>
            </motion.div>

            <motion.h1
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1, ease: [0.25, 0.1, 0.25, 1] }}
              className="font-display text-6xl sm:text-7xl lg:text-[5.5rem] leading-[0.9] text-white tracking-tight"
            >
              For founders who are<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#b89165] via-[#c9a86b] to-[#b89165]">
                tired of guessing
              </span>
              .
            </motion.h1>

            <motion.p
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.2, ease: [0.25, 0.1, 0.25, 1] }}
              className="mt-6 text-lg sm:text-xl text-white/50 max-w-xl leading-relaxed"
            >
              <span className="text-white/80 font-medium">SmartDeciGen</span> pressure-tests your assumptions and holds you
              accountable for the one decision that actually moves the needle.
            </motion.p>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
              className="mt-10 flex flex-col sm:flex-row items-start gap-4"
            >
              <Button onClick={() => navigate('/auth')}
                className="rounded-xl h-14 px-8 text-base font-medium bg-[#b89165] hover:bg-[#a67d52] text-white shadow-xl shadow-[#b89165]/25 group">
                Try 50 decisions free
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="ml-2 group-hover:translate-x-0.5 transition-transform">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </Button>
              <Button onClick={() => navigate('/auth')} variant="outline"
                className="rounded-xl h-14 px-8 text-base font-medium text-white/70 hover:text-white border-white/20 hover:border-white/40 bg-white/5 hover:bg-white/10">
                Sign in
              </Button>
            </motion.div>

            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.6, delay: 0.5 }}
              className="mt-8 flex items-center gap-5 text-xs text-white/30"
            >
              <span>50 free decisions</span>
              <span className="w-1 h-1 rounded-full bg-white/20" />
              <span>No card</span>
              <span className="w-1 h-1 rounded-full bg-white/20" />
              <span>Cancel anytime</span>
            </motion.div>
          </div>

          {/* 3D floating orb */}
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 1, delay: 0.4 }}
            className="hidden lg:block absolute right-14 top-1/2 -translate-y-1/2"
            style={{ transformStyle: 'preserve-3d' }}
          >
            <div className="relative w-[280px] h-[280px]"
              onMouseMove={(e) => {
                const el = e.currentTarget;
                const r = el.getBoundingClientRect();
                const x = (e.clientX - r.left) / r.width - 0.5;
                const y = (e.clientY - r.top) / r.height - 0.5;
                el.style.transform = `perspective(800px) rotateY(${x * 10}deg) rotateX(${-y * 10}deg)`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'perspective(800px) rotateY(0deg) rotateX(0deg)';
              }}
            >
              <div className="absolute inset-0 rounded-full"
                style={{
                  background: 'conic-gradient(from 0deg, rgba(184,145,101,0.15), rgba(47,143,138,0.10), rgba(184,145,101,0.20), rgba(47,143,138,0.10), rgba(184,145,101,0.15))',
                  filter: 'blur(40px)',
                }}
              />
              <div className="absolute inset-8 rounded-full border border-[#b89165]/20"
                style={{
                  background: 'radial-gradient(circle at 30% 30%, rgba(184,145,101,0.10) 0%, transparent 60%)',
                  boxShadow: 'inset 0 0 60px rgba(184,145,101,0.05)',
                }}
              />
              <div className="absolute inset-16 flex items-center justify-center">
                <svg width="80" height="80" viewBox="0 0 32 32" fill="none" className="opacity-40">
                  <path d="M22 8.5 A7 7 0 0 0 10 8.5 Q10 13 16 15.5 Q22 18 22 22.5 A7 7 0 0 1 10 22.5" stroke="#b89165" strokeWidth="1.2" strokeLinecap="round" fill="none" />
                  <path d="M9 21 L11 22.7 L9 24.4" stroke="#b89165" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                </svg>
              </div>
            </div>
          </motion.div>
        </div>

        {/* Scroll indicator */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1.2 }}
          className="absolute bottom-8 left-1/2 -translate-x-1/2"
        >
          <motion.div
            animate={{ y: [0, 6, 0] }}
            transition={{ duration: 2, repeat: Infinity }}
            className="w-5 h-8 rounded-full border border-white/20 flex items-start justify-center pt-2"
          >
            <div className="w-1 h-2 rounded-full bg-white/40" />
          </motion.div>
        </motion.div>
      </section>

      <HowItWorks />
      <FeaturesSection />
      <TestimonialsCarousel />
      <CTASection />
      <Footer />
    </div>
  );
}
