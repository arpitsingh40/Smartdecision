import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { Target, CheckCircle2, RefreshCw } from 'lucide-react';

const STEPS = [
  {
    num: '01', icon: Target, label: 'One goal',
    desc: 'Name the thing you keep avoiding. A decision, a project, a direction — we hold it for you across weeks.',
    accent: '#b89165',
  },
  {
    num: '02', icon: CheckCircle2, label: 'One action',
    desc: 'Every session surfaces the single easiest move for the next 48 hours. No overwhelm, just next steps.',
    accent: '#2f8f8a',
  },
  {
    num: '03', icon: RefreshCw, label: 'Real progress',
    desc: 'Return daily. Kept promises, not vibes. Weekly digests, benchmarks, and a coach that actually remembers.',
    accent: '#b89165',
  },
];

export default function HowItWorks() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section id="how-it-works" className="relative py-28 sm:py-36 bg-white overflow-hidden">
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[900px] rounded-full opacity-20"
          style={{ background: 'radial-gradient(circle, rgba(184,145,101,0.08) 0%, transparent 60%)' }} />
      </div>

      <div className="relative max-w-7xl mx-auto px-6 sm:px-10 lg:px-14">
        <div ref={ref} className="text-center max-w-2xl mx-auto mb-16 sm:mb-20">
          <motion.span
            initial={{ opacity: 0, y: 10 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 text-[11px] tracking-[0.26em] uppercase text-[#b89165] font-semibold mb-5"
          >
            <span className="w-7 h-px bg-[#b89165]" />
            How it works
          </motion.span>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="font-display text-4xl sm:text-5xl lg:text-[4rem] leading-[0.95] text-[#1a1a1a] tracking-tight"
          >
            Three moves. That&apos;s it.
          </motion.h2>
        </div>

        <div className="grid sm:grid-cols-3 gap-8 sm:gap-12 lg:gap-16 max-w-5xl mx-auto">
          {STEPS.map((s, i) => {
            const Icon = s.icon;
            return (
              <motion.div key={s.label}
                initial={{ opacity: 0, y: 40 }}
                animate={inView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.6, delay: 0.15 * i, ease: [0.25, 0.1, 0.25, 1] }}
                className="text-center"
              >
                <div className="w-16 h-16 rounded-2xl bg-[#f8f6f1] border border-[#e5dccf]/60 flex items-center justify-center mx-auto mb-6 relative">
                  <Icon size={22} strokeWidth={1.5} style={{ color: s.accent }} />
                  {i < STEPS.length - 1 && (
                    <div className="hidden sm:block absolute -right-[calc(50%+2rem)] top-1/2 -translate-y-1/2 w-[calc(100%-1rem)] h-px bg-gradient-to-r from-[#b89165]/30 to-transparent" />
                  )}
                </div>
                <div className="text-[10px] tracking-[0.3em] font-semibold mb-2" style={{ color: s.accent }}>
                  {s.num}
                </div>
                <h3 className="font-display text-2xl text-[#1a1a1a] mb-3">{s.label}.</h3>
                <p className="text-sm text-[#6b645c] leading-relaxed max-w-xs mx-auto">{s.desc}</p>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
