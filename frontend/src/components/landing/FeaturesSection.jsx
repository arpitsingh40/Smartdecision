import { Brain, Target, Users, BookOpen, Radar, ShieldCheck, ArrowRight } from 'lucide-react';

const FEATURES = [
  {
    icon: Target,
    title: 'Journey Engine',
    desc: 'One conversation builds your company model — industry, constraints, fears, strategic forks. The engine shapes a direction with milestones, trade-offs, and success odds.',
    accent: '#b89165',
    details: ['Digital twin extraction', 'Hypothesis tracking with probability updates', 'Milestone progress auto-detected'],
  },
  {
    icon: Brain,
    title: 'Decision Brain',
    desc: 'Upload your documents. Ask any question. The Brain retrieves from your company\'s own files using RAPTOR tree search — grounded answers with citations, never guesses.',
    accent: '#2f8f8a',
    details: ['Semantic document retrieval', 'Source-cited answers', 'Company-wide knowledge base'],
  },
  {
    icon: BookOpen,
    title: '170+ Book Lenses',
    desc: 'Every turn, the cognition engine selects the most relevant reasoning modules from the best business books — applied silently before the LLM call, zero extra cost.',
    accent: '#b89165',
    details: ['Kahneman · Tetlock · Munger · Taleb', 'Greene · Berry-Dee · Kishimi', 'Category-specific reasoning algorithms'],
  },
  {
    icon: Users,
    title: 'Executive Agents',
    desc: '12 autonomous agents — Strategy, Growth, Ops, Customer Success, Finance — running on schedules, detecting signals, escalating to you within authority boundaries.',
    accent: '#2f8f8a',
    details: ['L0-L5 authority gradient', 'Budget caps + kill switch', 'Verified execution evidence'],
  },
  {
    icon: Radar,
    title: 'Business System',
    desc: '15-function dependency graph with health scores. Weekly signal scan. Root cause walker that traces symptoms through the function chain to find the real problem.',
    accent: '#b89165',
    details: ['Vision → Strategy → Product → Sales', 'OKR auto-progress from execution data', 'At-risk function task generation'],
  },
  {
    icon: ShieldCheck,
    title: 'Execution Runtime',
    desc: '1,403 MCP tools — email, calendar, CRM, payments, dev tools. Every action gated by authority level, budget, and verification. Reversible or irreversible declared upfront.',
    accent: '#2f8f8a',
    details: ['Composio integration', 'Permission gates per action', 'Evidence collected for every outcome'],
  },
];

export default function FeaturesSection() {
  return (
    <section id="features" className="relative py-28 sm:py-36 bg-[#f8f6f1] overflow-hidden">
      <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
        <div className="absolute -top-40 -right-40 w-[800px] h-[800px] rounded-full opacity-25"
          style={{ background: 'radial-gradient(circle, rgba(184,145,101,0.10) 0%, transparent 65%)' }} />
        <div className="absolute -bottom-40 -left-40 w-[600px] h-[600px] rounded-full opacity-20"
          style={{ background: 'radial-gradient(circle, rgba(47,143,138,0.08) 0%, transparent 60%)' }} />
      </div>

      <div className="relative max-w-7xl mx-auto px-6 sm:px-10 lg:px-14">
        <div className="text-center max-w-2xl mx-auto mb-16 sm:mb-20">
          <span className="inline-flex items-center gap-2 text-[11px] tracking-[0.26em] uppercase text-[#b89165] font-semibold mb-5">
            <span className="h-px bg-[#b89165] w-8" />
            Not a chatbot
          </span>
          <h2 className="font-display text-4xl sm:text-5xl lg:text-[4rem] leading-[0.95] text-[#1a1a1a] tracking-tight">
            An organization<br />that happens to run on AI.
          </h2>
          <p className="mt-4 text-[#6b645c] text-sm max-w-md mx-auto">
            Six engines. One company. The AI is the means — the organization is the product.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5 sm:gap-6">
          {FEATURES.map((f) => {
            const Icon = f.icon;
            return (
              <div
                key={f.title}
                className="group relative bg-white border border-[#e5dccf]/50 rounded-3xl p-7 transition-all duration-500 cursor-default overflow-hidden hover:-translate-y-1 hover:shadow-lg"
              >
                <div
                  className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-700"
                  style={{ background: `radial-gradient(ellipse at 50% 0%, ${f.accent}08 0%, transparent 70%)` }}
                />

                <div className="relative">
                  <div className="w-12 h-12 rounded-xl bg-[#f8f6f1] border border-[#e5dccf]/60 flex items-center justify-center mb-5">
                    <Icon size={20} strokeWidth={1.5} style={{ color: f.accent }} />
                  </div>

                  <h3 className="font-display text-xl text-[#1a1a1a] mb-2.5">{f.title}</h3>
                  <p className="text-sm text-[#6b645c] leading-relaxed">{f.desc}</p>

                  <div className="overflow-hidden max-h-0 opacity-0 group-hover:max-h-40 group-hover:opacity-100 transition-all duration-300">
                    <div className="pt-4 mt-4 border-t border-[#e5dccf]/40 space-y-2">
                      {f.details.map((d) => (
                        <div key={d} className="flex items-center gap-2 text-xs text-[#6b645c]">
                          <div className="w-1 h-1 rounded-full" style={{ backgroundColor: f.accent }} />
                          {d}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 text-xs font-medium mt-4 opacity-0 group-hover:opacity-100 transition-opacity duration-300"
                    style={{ color: f.accent }}>
                    <span>Details</span>
                    <ArrowRight size={12} strokeWidth={2} />
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
