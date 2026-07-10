import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import { Quote } from 'lucide-react';

const TESTIMONIALS = [
  {
    quote: 'I had been sitting on a pivot decision for 3 months. After two sessions with SmartDeciGen, I had clarity and a plan. It\'s like a coach that actually remembers what you said last week.',
    author: 'Ankit R.',
    role: 'Founder, B2B SaaS',
    result: 'Decision made in 2 sessions',
  },
  {
    quote: 'The daily check-in keeps me honest. I\'ve shipped more in the last 3 weeks than in the previous 3 months. The action timer is a killer feature.',
    author: 'Priya M.',
    role: 'Independent Consultant',
    result: '3x shipping velocity',
  },
  {
    quote: 'We use the Decision Brain for every company bet now. It\'s our collective memory — no more repeating conversations or losing context when someone\'s out.',
    author: 'Rahul S.',
    role: 'CTO, Series A',
    result: 'Team-wide context retention',
  },
];

export default function TestimonialsCarousel() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });

  return (
    <section id="testimonials" className="relative py-28 sm:py-36 bg-[#f8f6f1] overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 sm:px-10 lg:px-14">
        <div ref={ref} className="text-center max-w-2xl mx-auto mb-16 sm:mb-20">
          <motion.span
            initial={{ opacity: 0, y: 10 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5 }}
            className="inline-flex items-center gap-2 text-[11px] tracking-[0.26em] uppercase text-[#b89165] font-semibold mb-5"
          >
            <span className="w-7 h-px bg-[#b89165]" />
            Real founders, real results
          </motion.span>
          <motion.h2
            initial={{ opacity: 0, y: 20 }}
            animate={inView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="font-display text-4xl sm:text-5xl lg:text-[4rem] leading-[0.95] text-[#1a1a1a] tracking-tight"
          >
            What operators say.
          </motion.h2>
        </div>

        <div className="grid sm:grid-cols-3 gap-5 sm:gap-6 max-w-5xl mx-auto">
          {TESTIMONIALS.map((t, i) => (
            <motion.div key={t.author}
              initial={{ opacity: 0, y: 30 }}
              animate={inView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.5, delay: 0.1 * i, ease: [0.25, 0.1, 0.25, 1] }}
              className="bg-white border border-[#e5dccf]/60 rounded-3xl p-7 flex flex-col"
            >
              <Quote size={20} className="text-[#b89165]/40 mb-4" strokeWidth={1.5} />
              <p className="text-sm text-[#4a443c] leading-relaxed flex-1">&ldquo;{t.quote}&rdquo;</p>
              <div className="mt-6 pt-5 border-t border-[#e5dccf]/40">
                <div className="font-medium text-sm text-[#1a1a1a]">{t.author}</div>
                <div className="text-xs text-[#6b645c] mt-0.5">{t.role}</div>
                <div className="mt-2 inline-flex items-center gap-1.5 text-[11px] font-medium text-[#2f8f8a] bg-[#2f8f8a]/5 rounded-full px-3 py-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#2f8f8a]" />
                  {t.result}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
