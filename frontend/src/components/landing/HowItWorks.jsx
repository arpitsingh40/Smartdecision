import { MessageCircle, Target, CheckCircle2, Users, GitCommitHorizontal } from 'lucide-react';

const STEPS = [
  {
    num: '01', icon: MessageCircle, label: 'One conversation',
    desc: 'Tell us your company vision. The engine builds a living model — your industry, constraints, fears, strategic forks — in one sitting.',
    accent: '#b89165',
    detail: 'The journey engine asks 5-7 sharp questions, not 50. It builds your digital twin, then shapes a direction with trade-offs, milestones, and success probability.',
  },
  {
    num: '02', icon: Target, label: 'One direction',
    desc: 'Your AI Chief of Staff produces a decision package: the call, the trade-offs, the first moves, and what to measure — updated every check-in.',
    accent: '#2f8f8a',
    detail: 'Not generic advice. Specific to your industry, stage, constraints. The engine applies 170+ decision-science lenses from the best founder books ever written.',
  },
  {
    num: '03', icon: CheckCircle2, label: 'Daily action',
    desc: 'Every day, one concrete next move for the next 48 hours. The engine tracks consistency, detects stalling, and re-engages you after silence.',
    accent: '#b89165',
    detail: 'The Situation Pane — 4 living fields updated with a single LLM call. No chat bubbles. Emotion tracking. Pace calibration. The accountability founders actually use.',
  },
  {
    num: '04', icon: Users, label: 'Your team runs',
    desc: 'Deploy executives for every function. Strategy. Growth. Ops. They detect signals, propose actions, escalate to you — on their own schedule.',
    accent: '#2f8f8a',
    detail: '12 autonomous agents with authority levels (L0-L5). Budget caps. Kill switch. Verified execution. Your company operates while you sleep.',
  },
  {
    num: '05', icon: GitCommitHorizontal, label: 'Compound clarity',
    desc: 'Every decision, every outcome, every file you upload — the Decision Brain remembers it all. Query your company like a database.',
    accent: '#b89165',
    detail: 'RAPTOR document retrieval. Business system health scan every week. OKRs auto-updated from execution data. Your company gets smarter every turn.',
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="relative py-28 sm:py-36 bg-white overflow-hidden">
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1200px] h-[800px] rounded-full opacity-15"
          style={{ background: 'radial-gradient(circle at 50% 0%, rgba(184,145,101,0.10) 0%, transparent 60%)' }} />
      </div>

      <div className="relative max-w-7xl mx-auto px-6 sm:px-10 lg:px-14">
        <div className="text-center max-w-2xl mx-auto mb-16 sm:mb-20">
          <span className="inline-flex items-center gap-2 text-[11px] tracking-[0.26em] uppercase text-[#b89165] font-semibold mb-5">
            <span className="h-px bg-[#b89165] w-8" />
            How it works
          </span>
          <h2 className="font-display text-4xl sm:text-5xl lg:text-[4rem] leading-[0.95] text-[#1a1a1a] tracking-tight">
            You steer.<br />The organization runs.
          </h2>
          <p className="mt-4 text-[#6b645c] text-sm sm:text-base max-w-sm mx-auto">
            From first conversation to autonomous company — five steps
          </p>
        </div>

        <div className="relative max-w-4xl mx-auto">
          <div className="hidden sm:block absolute left-8 top-0 bottom-0 w-px bg-gradient-to-b from-[#b89165]/30 via-[#2f8f8a]/30 to-[#b89165]/30" />

          <div className="space-y-12 sm:space-y-16">
            {STEPS.map((s) => {
              const Icon = s.icon;
              return (
                <div key={s.label} className="relative flex gap-6 sm:gap-8 items-start">
                  <div className="relative shrink-0">
                    <div className="w-16 h-16 rounded-2xl bg-white border border-[#e5dccf]/60 flex items-center justify-center shadow-sm"
                      style={{ borderColor: s.accent + '40' }}
                    >
                      <Icon size={22} strokeWidth={1.5} style={{ color: s.accent }} />
                    </div>
                  </div>
                  <div className="pt-2">
                    <div className="text-[10px] tracking-[0.3em] font-semibold mb-1" style={{ color: s.accent }}>
                      {s.num}
                    </div>
                    <h3 className="font-display text-2xl text-[#1a1a1a] mb-2">{s.label}.</h3>
                    <p className="text-sm text-[#6b645c] leading-relaxed max-w-lg">{s.desc}</p>
                    <p className="text-xs text-[#b89165]/70 leading-relaxed max-w-lg mt-2">{s.detail}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
