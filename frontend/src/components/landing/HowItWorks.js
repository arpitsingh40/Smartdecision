import { useRef, useState, useEffect } from 'react';
import { motion, useInView } from 'framer-motion';
import { Target, CheckCircle2, RefreshCw, ArrowDown } from 'lucide-react';

const STEPS = [
  {
    num: '01', icon: Target, label: 'One goal',
    desc: 'Name the thing you keep avoiding. A decision, a project, a direction — we hold it for you across weeks.',
    accent: '#b89165',
    detail: 'Define the decision that\'s been haunting you. We build a persistent goal that travels with you across every session — no context lost, ever.',
  },
  {
    num: '02', icon: CheckCircle2, label: 'One action',
    desc: 'Every session surfaces the single easiest move for the next 48 hours. No overwhelm, just next steps.',
    accent: '#2f8f8a',
    detail: 'Your AI Chief of Staff analyzes your goal, your momentum, and your blockers — then serves the one action that unsticks you.',
  },
  {
    num: '03', icon: RefreshCw, label: 'Real progress',
    desc: 'Return daily. Kept promises, not vibes. Weekly digests, benchmarks, and a coach that actually remembers.',
    accent: '#b89165',
    detail: 'Track decisions over weeks, not days. Get benchmarked against peers, celebrate wins, and build compound clarity.',
  },
];

function ConnectorLine({ progress }) {
  return (
    <svg className="absolute top-0 left-1/2 -translate-x-1/2 w-px sm:hidden" height="100%" width="2">
      <line x1="1" y1="0" x2="1" y2="100%" stroke="#e5dccf" strokeWidth="1" />
      <line x1="1" y1="0" x2="1" y2={`${progress * 100}%`} stroke="#b89165" strokeWidth="1.5" />
    </svg>
  );
}

export default function HowItWorks() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const timer = setTimeout(() => {
      const interval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 1) { clearInterval(interval); return 1; }
          return prev + 0.02;
        });
      }, 40);
      return () => clearInterval(interval);
    }, 300);
    return () => clearTimeout(timer);
  }, [inView]);

  return (
    <section id="how-it-works" className="relative py-28 sm:py-36 bg-white overflow-hidden">
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1200px] h-[800px] rounded-full opacity-15"
          style={{ background: 'radial-gradient(circle at 50% 0%, rgba(184,145,101,0.10) 0%, transparent 60%)' }} />
        <div className="absolute bottom-0 right-0 w-[600px] h-[600px] rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, rgba(47,143,138,0.08) 0%, transparent 60%)' }} />
      </div>

      <div ref={ref} className="relative max-w-7xl mx-auto px-6 sm:px-10 lg:px-14">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-center max-w-2xl mx-auto mb-16 sm:mb-20"
        >
          <motion.span
            initial={{ opacity: 0, y: 10 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 text-[11px] tracking-[0.26em] uppercase text-[#b89165] font-semibold mb-5"
          >
            <motion.span
              animate={{ width: ['1.75rem', '2.5rem', '1.75rem'] }}
              transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
              className="h-px bg-[#b89165]"
            />
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
          <motion.p
            initial={{ opacity: 0 }}
            animate={inView ? { opacity: 1 } : {}}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mt-4 text-[#6b645c] text-sm sm:text-base max-w-sm mx-auto"
          >
            From confusion to clarity in three deliberate steps
          </motion.p>
        </motion.div>

        <div className="relative max-w-5xl mx-auto">
          <ConnectorLine progress={progress} />

          <div className="hidden sm:block absolute left-[calc(50%-0.5px)] top-12 bottom-12 w-px bg-[#e5dccf]/60">
            <motion.div
              className="w-full bg-gradient-to-b from-[#b89165] via-[#2f8f8a] to-[#b89165]"
              style={{ height: `${progress * 100}%` }}
            />
          </div>

          <div className="grid sm:grid-cols-3 gap-8 sm:gap-12 lg:gap-16">
            {STEPS.map((s, i) => {
              const Icon = s.icon;
              return (
                <motion.div key={s.label}
                  initial={{ opacity: 0, y: 40 }}
                  animate={inView ? { opacity: 1, y: 0 } : {}}
                  transition={{ duration: 0.7, delay: 0.2 + 0.15 * i, ease: [0.25, 0.1, 0.25, 1] }}
                  className="relative text-center group"
                >
                  <div className="relative inline-block">
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={inView ? { scale: 1 } : {}}
                      transition={{ duration: 0.5, delay: 0.3 + 0.15 * i, type: 'spring', stiffness: 200 }}
                      className="w-20 h-20 rounded-2xl bg-[#f8f6f1] border border-[#e5dccf]/60 flex items-center justify-center mx-auto mb-6 relative"
                      whileHover={{ scale: 1.05, borderColor: s.accent, boxShadow: `0 0 30px ${s.accent}15` }}
                    >
                      <motion.div
                        animate={inView ? { rotate: [0, 5, 0] } : {}}
                        transition={{ duration: 0.8, delay: 0.6 + 0.15 * i }}
                      >
                        <Icon size={24} strokeWidth={1.5} style={{ color: s.accent }} />
                      </motion.div>
                      {i < STEPS.length - 1 && (
                        <div className="hidden sm:block absolute -right-[calc(50%+2.5rem)] top-1/2 -translate-y-1/2">
                          <motion.div
                            initial={{ scaleX: 0 }}
                            animate={inView ? { scaleX: 1 } : {}}
                            transition={{ duration: 0.6, delay: 0.5 + 0.15 * i }}
                            className="w-[calc(100%-1rem)] h-px bg-gradient-to-r from-[#b89165]/40 to-transparent origin-left"
                          />
                        </div>
                      )}
                      <motion.div
                        className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-white border border-[#e5dccf]/60 flex items-center justify-center"
                        initial={{ scale: 0 }}
                        animate={inView ? { scale: 1 } : {}}
                        transition={{ delay: 0.5 + 0.15 * i, type: 'spring' }}
                      >
                        <ArrowDown size={10} className="text-[#6b645c]" strokeWidth={2.5} />
                      </motion.div>
                    </motion.div>
                  </div>

                  <motion.div
                    className="text-[10px] tracking-[0.3em] font-semibold mb-2.5"
                    style={{ color: s.accent }}
                    initial={{ opacity: 0 }}
                    animate={inView ? { opacity: 1 } : {}}
                    transition={{ delay: 0.4 + 0.15 * i }}
                  >
                    {s.num}
                  </motion.div>

                  <motion.h3
                    className="font-display text-2xl text-[#1a1a1a] mb-3"
                    initial={{ opacity: 0 }}
                    animate={inView ? { opacity: 1 } : {}}
                    transition={{ delay: 0.5 + 0.15 * i }}
                  >
                    {s.label}.
                  </motion.h3>

                  <motion.p
                    className="text-sm text-[#6b645c] leading-relaxed max-w-xs mx-auto"
                    initial={{ opacity: 0 }}
                    animate={inView ? { opacity: 1 } : {}}
                    transition={{ delay: 0.6 + 0.15 * i }}
                  >
                    {s.desc}
                  </motion.p>

                  <motion.p
                    className="text-xs text-[#b89165]/70 leading-relaxed max-w-xs mx-auto mt-3 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                    initial={{ opacity: 0, y: 5 }}
                    whileHover={{ opacity: 1, y: 0 }}
                  >
                    {s.detail}
                  </motion.p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
