import { Target, CheckCircle2, RefreshCw } from 'lucide-react';

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
    desc: 'Return daily. Kept promises, not vibes. Weekly digests, benchmarks, and an operator that actually remembers.',
    accent: '#b89165',
    detail: 'Track decisions over weeks, not days. Get benchmarked against peers, celebrate wins, and build compound clarity.',
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="relative py-28 sm:py-36 bg-white overflow-hidden">
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1200px] h-[800px] rounded-full opacity-15"
          style={{ background: 'radial-gradient(circle at 50% 0%, rgba(184,145,101,0.10) 0%, transparent 60%)' }} />
        <div className="absolute bottom-0 right-0 w-[600px] h-[600px] rounded-full opacity-10"
          style={{ background: 'radial-gradient(circle, rgba(47,143,138,0.08) 0%, transparent 60%)' }} />
      </div>

      <div className="relative max-w-7xl mx-auto px-6 sm:px-10 lg:px-14">
        <div className="text-center max-w-2xl mx-auto mb-16 sm:mb-20">
          <span className="inline-flex items-center gap-2 text-[11px] tracking-[0.26em] uppercase text-[#b89165] font-semibold mb-5">
            <span className="h-px bg-[#b89165] animate-pulse-width" />
            How it works
          </span>
          <h2 className="font-display text-4xl sm:text-5xl lg:text-[4rem] leading-[0.95] text-[#1a1a1a] tracking-tight">
            Three moves. That&apos;s it.
          </h2>
          <p className="mt-4 text-[#6b645c] text-sm sm:text-base max-w-sm mx-auto">
            From confusion to clarity in three deliberate steps
          </p>
        </div>

        <div className="relative max-w-5xl mx-auto">
          <div className="hidden sm:block absolute left-[calc(50%-0.5px)] top-12 bottom-12 w-px bg-gradient-to-b from-[#b89165] via-[#2f8f8a] to-[#b89165]" />

          <div className="grid sm:grid-cols-3 gap-8 sm:gap-12 lg:gap-16">
            {STEPS.map((s, i) => {
              const Icon = s.icon;
              return (
                <div key={s.label} className="relative text-center group">
                  <div className="relative inline-block">
                    <div className="w-20 h-20 rounded-2xl bg-[#f8f6f1] border border-[#e5dccf]/60 flex items-center justify-center mx-auto mb-6 relative transition-all duration-300 hover:scale-105"
                      style={{ borderColor: s.accent }}
                    >
                      <div>
                        <Icon size={24} strokeWidth={1.5} style={{ color: s.accent }} />
                      </div>
                      {i < STEPS.length - 1 && (
                        <div className="hidden sm:block absolute -right-[calc(50%+2.5rem)] top-1/2 -translate-y-1/2">
                          <div className="w-[calc(100%-1rem)] h-px bg-gradient-to-r from-[#b89165]/40 to-transparent" />
                        </div>
                      )}
                      <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-white border border-[#e5dccf]/60 flex items-center justify-center">
                        <RefreshCw size={10} className="text-[#6b645c]" strokeWidth={2.5} />
                      </div>
                    </div>
                  </div>

                  <div
                    className="text-[10px] tracking-[0.3em] font-semibold mb-2.5"
                    style={{ color: s.accent }}
                  >
                    {s.num}
                  </div>

                  <h3 className="font-display text-2xl text-[#1a1a1a] mb-3">
                    {s.label}.
                  </h3>

                  <p className="text-sm text-[#6b645c] leading-relaxed max-w-xs mx-auto">
                    {s.desc}
                  </p>

                  <p className="text-xs text-[#b89165]/70 leading-relaxed max-w-xs mx-auto mt-3 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    {s.detail}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
