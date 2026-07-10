import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { MessageCircle, Brain, Users, Target, Shield, Sparkles } from 'lucide-react';

const FEATURES = [
  {
    icon: MessageCircle,
    title: 'Deep Discussions',
    desc: 'Engine that holds context across weeks. One goal, threaded conversations, real progress — not chat history that vanishes.',
    accent: '#b89165',
  },
  {
    icon: Brain,
    title: 'Decision Brain',
    desc: 'Company-wide knowledge base that remembers every file, decision, and insight. Query it like a second brain.',
    accent: '#2f8f8a',
  },
  {
    icon: Users,
    title: 'Founder OS',
    desc: 'Team cockpit, benchmarks, release gates, and task tracking built for operators who actually ship.',
    accent: '#b89165',
  },
  {
    icon: Shield,
    title: 'Privacy First',
    desc: 'Your data stays yours. Encrypted, never trained on, and built to be returned to — not to lock you in.',
    accent: '#2f8f8a',
  },
];

const container = { hidden: {}, visible: { transition: { staggerChildren: 0.12 } } };
const item = {
  hidden: { opacity: 0, y: 30 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.6, ease: [0.25, 0.1, 0.25, 1] } },
};

export default function FeaturesSection() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-80px' });

  return (
    <section id="features" className="relative py-28 sm:py-36 bg-[#f8f6f1] overflow-hidden">
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute -top-40 -right-40 w-[800px] h-[800px] rounded-full opacity-30"
          style={{ background: 'radial-gradient(circle, rgba(184,145,101,0.12) 0%, transparent 65%)' }} />
        <div className="absolute -bottom-40 -left-40 w-[600px] h-[600px] rounded-full opacity-20"
          style={{ background: 'radial-gradient(circle, rgba(47,143,138,0.10) 0%, transparent 60%)' }} />
      </div>

      <div className="relative max-w-7xl mx-auto px-6 sm:px-10 lg:px-14">
        <motion.div ref={ref} initial="hidden" animate={inView ? 'visible' : 'hidden'} variants={container}>
          <div className="text-center max-w-2xl mx-auto mb-16 sm:mb-20">
            <span className="inline-flex items-center gap-2 text-[11px] tracking-[0.26em] uppercase text-[#b89165] font-semibold mb-5">
              <span className="w-7 h-px bg-[#b89165]" />
              Built for operators
            </span>
            <h2 className="font-display text-4xl sm:text-5xl lg:text-[4rem] leading-[0.95] text-[#1a1a1a] tracking-tight">
              Everything you need to<br />move from knowing to doing.
            </h2>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 sm:gap-6">
            {FEATURES.map((f) => {
              const Icon = f.icon;
              return (
                <motion.div key={f.title} variants={item}
                  className="group relative bg-white/80 backdrop-blur-sm border border-[#e5dccf]/60 rounded-3xl p-7 hover:shadow-lg hover:shadow-[#b89165]/5 transition-all duration-500"
                  style={{ transformStyle: 'preserve-3d' }}
                  onMouseMove={(e) => {
                    const r = e.currentTarget.getBoundingClientRect();
                    const x = (e.clientX - r.left) / r.width - 0.5;
                    const y = (e.clientY - r.top) / r.height - 0.5;
                    e.currentTarget.style.transform = `perspective(800px) rotateY(${x * 6}deg) rotateX(${-y * 6}deg)`;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = 'perspective(800px) rotateY(0deg) rotateX(0deg)';
                  }}
                >
                  <div className="w-10 h-10 rounded-xl bg-[#f8f6f1] border border-[#e5dccf]/60 flex items-center justify-center mb-5">
                    <Icon size={18} strokeWidth={1.5} style={{ color: f.accent }} />
                  </div>
                  <h3 className="font-display text-xl text-[#1a1a1a] mb-2">{f.title}</h3>
                  <p className="text-sm text-[#6b645c] leading-relaxed">{f.desc}</p>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
