const SCREENS = [
  {
    id: 'journey',
    title: 'Strategy Room',
    heading: 'Your AI chief of staff',
    desc: 'A persistent conversation that remembers everything. Set a goal, explore options, get a decision package with confidence scores.',
    lines: [
      { align: 'left', text: 'We need to decide on the Q3 hiring plan. Should we hire a senior backend engineer or double down on contractors?', meta: 'You · 2 days ago' },
      { align: 'right', text: 'Let me analyze that against your current constraints...', meta: 'Thinking' },
    ],
  },
  {
    id: 'thread',
    title: 'Daily Check-in',
    heading: 'One action, 48 hours',
    desc: 'Every session surfaces your single next action. No overwhelm, no task bloat — just the one thing that moves the needle.',
    lines: [
      { align: 'left', text: 'Yesterday\'s action: "Review backend contractor proposals." Done?', meta: 'SmartDeciGen · Today' },
      { align: 'right', text: 'Shared my feedback in the thread. Drafting contracts now.', meta: 'You · 2h ago' },
    ],
  },
  {
    id: 'cockpit',
    title: 'Cockpit',
    heading: 'Ship velocity at a glance',
    desc: 'North star progress, team alignment, follow-through rates, and drift detection — all in one dashboard.',
    lines: [
      { align: 'left', text: 'North star: 10 paying customers by Oct', meta: 'Goal' },
      { align: 'right', text: 'Momentum: +2 this week · 40% to target', meta: 'On track' },
    ],
  },
];

export default function DemoSection() {
  return (
    <section className="relative py-24 sm:py-32 bg-[#f8f6f1]">
      <div className="max-w-6xl mx-auto px-6 sm:px-10 lg:px-14">
        <div className="text-center max-w-2xl mx-auto mb-16">
          <span className="inline-flex items-center gap-2 text-[11px] tracking-[0.26em] uppercase text-[#b89165] font-semibold mb-5">
            <span className="h-px w-8 bg-[#b89165]" />
            See it in action
          </span>
          <h2 className="font-display text-4xl sm:text-5xl text-[#1a1a1a] tracking-tight leading-[1.1]">
            What you&apos;ll see when you<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#b89165] via-[#c9a86b] to-[#b89165]">
              sign up.
            </span>
          </h2>
        </div>

        <div className="space-y-8">
          {SCREENS.map((screen) => (
            <div key={screen.id}
              className="bg-white rounded-2xl border border-[#e5dccf]/60 overflow-hidden shadow-sm hover:shadow-md transition-shadow">
              <div className="flex items-center gap-2 px-5 py-3 border-b border-[#e5dccf]/40 bg-[#faf9f7]">
                <span className="w-3 h-3 rounded-full bg-[#e5dccf]" />
                <span className="w-3 h-3 rounded-full bg-[#e5dccf]" />
                <span className="w-3 h-3 rounded-full bg-[#e5dccf]" />
                <span className="ml-3 text-[11px] text-[#6b645c] font-medium">{screen.title}</span>
              </div>
              <div className="p-5 sm:p-6 flex flex-col lg:flex-row gap-6">
                <div className="lg:w-2/5">
                  <h3 className="font-display text-2xl text-[#1a1a1a] mb-2">{screen.heading}</h3>
                  <p className="text-sm text-[#6b645c] leading-relaxed">{screen.desc}</p>
                </div>
                <div className="lg:w-3/5 space-y-3">
                  {screen.lines.map((line, i) => (
                    <div key={i} className={`flex ${line.align === 'right' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                        line.align === 'right'
                          ? 'bg-[#b89165] text-white rounded-tr-sm'
                          : 'bg-[#f8f6f1] text-[#4a443c] border border-[#e5dccf]/60 rounded-tl-sm'
                      }`}>
                        <p className="text-sm leading-relaxed">{line.text}</p>
                        <p className={`text-[10px] mt-1.5 ${line.align === 'right' ? 'text-white/60' : 'text-[#6b645c]'}`}>
                          {line.meta}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
