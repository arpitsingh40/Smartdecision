import { useRef, useState } from 'react';
import { motion, useInView } from 'framer-motion';
import { MessageCircle, Brain, Users, Shield, Sparkles, ArrowRight } from 'lucide-react';

const FEATURES = [
  {
    icon: MessageCircle,
    title: 'Deep Discussions',
    desc: 'Context that holds across weeks. Threaded conversations that don\'t vanish — your AI remembers every nuance.',
    accent: '#b89165',
    gradient: 'from-[#b89165]/10 to-transparent',
    details: ['Threaded session memory', 'Cross-week context', 'Decision lineage tracking'],
  },
  {
    icon: Brain,
    title: 'Decision Brain',
    desc: 'Company-wide knowledge base that remembers every file, decision, and insight. Query it like a second brain.',
    accent: '#2f8f8a',
    gradient: 'from-[#2f8f8a]/10 to-transparent',
    details: ['Semantic search', 'Decision graph', 'Insight mining'],
  },
  {
    icon: Users,
    title: 'Founder OS',
    desc: 'Team cockpit, benchmarks, release gates, and task tracking built for operators who actually ship.',
    accent: '#b89165',
    gradient: 'from-[#b89165]/10 to-transparent',
    details: ['Real-time progress board', 'Peer benchmarking', 'Release readiness'],
  },
  {
    icon: Shield,
    title: 'Privacy First',
    desc: 'Your data stays yours. Encrypted, never trained on, and built to be returned to — not to lock you in.',
    accent: '#2f8f8a',
    gradient: 'from-[#2f8f8a]/10 to-transparent',
    details: ['End-to-end encrypted', 'Zero training data', 'Full export anytime'],
  },
];

const container = { hidden: {}, visible: { transition: { staggerChildren: 0.1 } } };
const item = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.25, 0.1, 0.25, 1] } },
};

export default function FeaturesSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });
  const [activeIndex, setActiveIndex] = useState(null);

  return (
    <section id="features" className="relative py-28 sm:py-36 bg-[#f8f6f1] overflow-hidden">
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute -top-40 -right-40 w-[800px] h-[800px] rounded-full opacity-25"
          style={{ background: 'radial-gradient(circle, rgba(184,145,101,0.10) 0%, transparent 65%)' }} />
        <div className="absolute -bottom-40 -left-40 w-[600px] h-[600px] rounded-full opacity-20"
          style={{ background: 'radial-gradient(circle, rgba(47,143,138,0.08) 0%, transparent 60%)' }} />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1000px] h-[1000px] rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, rgba(184,145,101,0.04) 0%, transparent 50%)' }} />
      </div>

      <div className="relative max-w-7xl mx-auto px-6 sm:px-10 lg:px-14">
        <motion.div ref={ref} initial="hidden" animate={inView ? 'visible' : 'hidden'} variants={container}>
          <div className="text-center max-w-2xl mx-auto mb-16 sm:mb-20">
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
              Built for operators
            </motion.span>
            <motion.h2
              initial={{ opacity: 0, y: 20 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.1 }}
              className="font-display text-4xl sm:text-5xl lg:text-[4rem] leading-[0.95] text-[#1a1a1a] tracking-tight"
            >
              Everything you need to<br />move from knowing to doing.
            </motion.h2>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 sm:gap-6">
            {FEATURES.map((f, i) => {
              const Icon = f.icon;
              return (
                <motion.div
                  key={f.title}
                  variants={item}
                  onMouseEnter={() => setActiveIndex(i)}
                  onMouseLeave={() => setActiveIndex(null)}
                  className="group relative bg-white border border-[#e5dccf]/50 rounded-3xl p-7 transition-all duration-500 cursor-default overflow-hidden"
                  style={{
                    transformStyle: 'preserve-3d',
                    transition: 'transform 0.3s ease, box-shadow 0.3s ease',
                  }}
                  whileHover={{
                    y: -4,
                    boxShadow: '0 20px 60px rgba(184,145,101,0.08)',
                    borderColor: f.accent + '40',
                  }}
                >
                  <motion.div
                    className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-700"
                    style={{
                      background: `radial-gradient(ellipse at 50% 0%, ${f.accent}08 0%, transparent 70%)`,
                    }}
                  />

                  <div className="relative">
                    <motion.div
                      whileHover={{ scale: 1.1, rotate: [0, -5, 5, 0] }}
                      transition={{ duration: 0.4 }}
                      className="w-12 h-12 rounded-xl bg-[#f8f6f1] border border-[#e5dccf]/60 flex items-center justify-center mb-5 group-hover:border-[#b89165]/30 transition-colors duration-500"
                    >
                      <Icon size={20} strokeWidth={1.5} style={{ color: f.accent }} />
                    </motion.div>

                    <h3 className="font-display text-xl text-[#1a1a1a] mb-2.5 group-hover:text-[#b89165] transition-colors duration-300">{f.title}</h3>
                    <p className="text-sm text-[#6b645c] leading-relaxed">{f.desc}</p>

                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={activeIndex === i ? { height: 'auto', opacity: 1 } : { height: 0, opacity: 0 }}
                      transition={{ duration: 0.3 }}
                      className="overflow-hidden"
                    >
                      <div className="pt-4 mt-4 border-t border-[#e5dccf]/40 space-y-2">
                        {f.details.map((d) => (
                          <div key={d} className="flex items-center gap-2 text-xs text-[#6b645c]">
                            <div className="w-1 h-1 rounded-full" style={{ backgroundColor: f.accent }} />
                            {d}
                          </div>
                        ))}
                      </div>
                    </motion.div>

                    <motion.div
                      className="flex items-center gap-1.5 text-xs font-medium mt-4"
                      style={{ color: f.accent }}
                      initial={{ opacity: 0 }}
                      whileHover={{ opacity: 1 }}
                    >
                      <span>Learn more</span>
                      <ArrowRight size={12} strokeWidth={2} />
                    </motion.div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
