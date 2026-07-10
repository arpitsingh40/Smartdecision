import { useState, useEffect, useRef } from 'react';
import { motion, useInView, AnimatePresence } from 'framer-motion';
import { Quote, ChevronLeft, ChevronRight, Star } from 'lucide-react';

const TESTIMONIALS = [
  {
    quote: 'I had been sitting on a pivot decision for 3 months. After two sessions with SmartDeciGen, I had clarity and a plan. It\'s like a coach that actually remembers what you said last week.',
    author: 'Ankit R.',
    role: 'Founder, B2B SaaS',
    result: 'Decision made in 2 sessions',
    rating: 5,
  },
  {
    quote: 'The daily check-in keeps me honest. I\'ve shipped more in the last 3 weeks than in the previous 3 months. The action timer is a killer feature.',
    author: 'Priya M.',
    role: 'Independent Consultant',
    result: '3x shipping velocity',
    rating: 5,
  },
  {
    quote: 'We use the Decision Brain for every company bet now. It\'s our collective memory — no more repeating conversations or losing context when someone\'s out.',
    author: 'Rahul S.',
    role: 'CTO, Series A',
    result: 'Team-wide context retention',
    rating: 5,
  },
  {
    quote: 'The weekly digests alone are worth it. I finally have a clear picture of where my decisions are taking me. The benchmarks against peers are eye-opening.',
    author: 'Neha K.',
    role: 'CEO, HealthTech',
    result: '40% faster decision velocity',
    rating: 5,
  },
];

export default function TestimonialsCarousel() {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-60px' });
  const [current, setCurrent] = useState(0);
  const [direction, setDirection] = useState(0);

  useEffect(() => {
    if (!inView) return;
    const timer = setInterval(() => {
      setDirection(1);
      setCurrent(prev => (prev + 1) % TESTIMONIALS.length);
    }, 5000);
    return () => clearInterval(timer);
  }, [inView]);

  const goTo = (i) => {
    setDirection(i > current ? 1 : -1);
    setCurrent(i);
  };

  const goNext = () => {
    setDirection(1);
    setCurrent(prev => (prev + 1) % TESTIMONIALS.length);
  };

  const goPrev = () => {
    setDirection(-1);
    setCurrent(prev => (prev - 1 + TESTIMONIALS.length) % TESTIMONIALS.length);
  };

  const variants = {
    enter: (dir) => ({ x: dir > 0 ? 200 : -200, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (dir) => ({ x: dir > 0 ? -200 : 200, opacity: 0 }),
  };

  const t = TESTIMONIALS[current];

  return (
    <section id="testimonials" className="relative py-28 sm:py-36 bg-white overflow-hidden">
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[900px] h-[900px] rounded-full opacity-15"
          style={{ background: 'radial-gradient(circle, rgba(184,145,101,0.06) 0%, transparent 60%)' }} />
      </div>

      <div ref={ref} className="max-w-7xl mx-auto px-6 sm:px-10 lg:px-14">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={inView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.5 }}
          className="text-center max-w-2xl mx-auto mb-16 sm:mb-20"
        >
          <span className="inline-flex items-center gap-2 text-[11px] tracking-[0.26em] uppercase text-[#b89165] font-semibold mb-5">
            <motion.span
              animate={{ width: ['1.75rem', '2.5rem', '1.75rem'] }}
              transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
              className="h-px bg-[#b89165]"
            />
            Real founders, real results
          </span>
          <h2 className="font-display text-4xl sm:text-5xl lg:text-[4rem] leading-[0.95] text-[#1a1a1a] tracking-tight">
            What operators say.
          </h2>
        </motion.div>

        <div className="max-w-3xl mx-auto">
          <div className="relative min-h-[280px] sm:min-h-[240px]">
            <AnimatePresence mode="wait" custom={direction}>
              <motion.div
                key={current}
                custom={direction}
                variants={variants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
                className="absolute inset-0"
              >
                <div className="bg-[#f8f6f1] border border-[#e5dccf]/60 rounded-3xl p-8 sm:p-10">
                  <div className="flex items-center justify-between mb-6">
                    <Quote size={24} className="text-[#b89165]/30" strokeWidth={1.5} />
                    <div className="flex items-center gap-1">
                      {Array.from({ length: t.rating }).map((_, i) => (
                        <Star key={i} size={14} className="text-[#b89165]" fill="#b89165" strokeWidth={0} />
                      ))}
                    </div>
                  </div>
                  <p className="text-base sm:text-lg text-[#4a443c] leading-relaxed">&ldquo;{t.quote}&rdquo;</p>
                  <div className="mt-6 pt-5 border-t border-[#e5dccf]/40 flex items-center justify-between">
                    <div>
                      <div className="font-medium text-sm text-[#1a1a1a]">{t.author}</div>
                      <div className="text-xs text-[#6b645c] mt-0.5">{t.role}</div>
                    </div>
                    <div className="inline-flex items-center gap-1.5 text-[11px] font-medium text-[#2f8f8a] bg-[#2f8f8a]/5 rounded-full px-3 py-1.5">
                      <motion.span
                        animate={{ scale: [1, 1.3, 1] }}
                        transition={{ duration: 2, repeat: Infinity }}
                        className="w-1.5 h-1.5 rounded-full bg-[#2f8f8a]"
                      />
                      {t.result}
                    </div>
                  </div>
                </div>
              </motion.div>
            </AnimatePresence>
          </div>

          <div className="flex items-center justify-center gap-4 mt-8">
            <button onClick={goPrev}
              className="w-9 h-9 rounded-full border border-[#e5dccf]/60 flex items-center justify-center hover:border-[#b89165]/40 hover:bg-[#b89165]/5 transition-all duration-300 group">
              <ChevronLeft size={16} className="text-[#6b645c] group-hover:text-[#b89165] transition-colors" strokeWidth={1.5} />
            </button>

            <div className="flex items-center gap-2">
              {TESTIMONIALS.map((_, i) => (
                <button key={i} onClick={() => goTo(i)}
                  className="relative h-2 rounded-full transition-all duration-500"
                  style={{
                    width: i === current ? '24px' : '8px',
                    backgroundColor: i === current ? '#b89165' : '#e5dccf',
                  }}
                >
                  {i === current && (
                    <motion.div
                      className="absolute inset-0 rounded-full bg-[#b89165]"
                      layoutId="activeDot"
                      transition={{ type: 'spring', stiffness: 300, damping: 25 }}
                    />
                  )}
                </button>
              ))}
            </div>

            <button onClick={goNext}
              className="w-9 h-9 rounded-full border border-[#e5dccf]/60 flex items-center justify-center hover:border-[#b89165]/40 hover:bg-[#b89165]/5 transition-all duration-300 group">
              <ChevronRight size={16} className="text-[#6b645c] group-hover:text-[#b89165] transition-colors" strokeWidth={1.5} />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
