"""Reasoning Lenses — the applied layer of the 20-book decision-science knowledge base.

Each of the 20 dossiers in /app/backend/knowledge/ is distilled here into a compact,
imperative reasoning MODULE. select_lenses() scores modules against the founder's
latest message + situation model and returns the top matches as a prompt block, so
the engine APPLIES frameworks (Munger, Tetlock, Rumelt, Meadows, Klein...) silently
instead of summarizing books. Pure functions, zero LLM cost, ~600 extra tokens/turn max.
"""

import json

# (id, book label, [(trigger substring, weight)], lens instruction text)
MODULES = [
    {
        "id": "kahneman_bias", "book": "Thinking, Fast and Slow (Kahneman)",
        "triggers": [("confident", 2), ("sure it will", 3), ("i know it", 2), ("projection", 2),
                     ("forecast", 2), ("estimate", 2), ("already spent", 3), ("already invested", 3),
                     ("sunk", 3), ("gut says", 2), ("feels right", 2), ("timeline", 1), ("my plan", 1)],
        "lens": ("Their confidence may be story-coherence, not evidence. Check which easier question they might "
                 "be answering instead of the hard one. If already-spent money is steering them, force the "
                 "zero-based reframe: would you start this today? If they forecast from their own plan, demand "
                 "the outside view: what did this take for others like them? Confidence without a reference "
                 "class gets discounted."),
    },
    {
        "id": "tetlock_forecast", "book": "Superforecasting (Tetlock)",
        "triggers": [("will it work", 3), ("chances", 2), ("probability", 3), ("odds", 2), ("predict", 2),
                     ("expect to", 2), ("how likely", 3), ("base rate", 3), ("target of", 1), ("next year", 1),
                     ("in 6 months", 1), ("in a year", 1)],
        "lens": ("Any prediction must carry: reference class, base rate, case-specific adjustment, a precise "
                 "probability, and a pre-declared what-would-change-my-mind condition. Decompose compound "
                 "outcomes Fermi-style into 3-5 measurable drivers and estimate each. Treat vivid news as "
                 "deserving a small proportional update, never a whiplash reversal."),
    },
    {
        "id": "heath_wrap", "book": "Decisive (Heath brothers)",
        "triggers": [("should i", 3), ("or not", 2), ("tempted", 3), ("deciding between", 3), ("either", 1),
                     ("everyone says", 3), ("everyone tells", 3), ("sign the", 2), ("commit to", 2),
                     ("offer from", 2), ("take the deal", 3), ("yes or no", 3)],
        "lens": ("Watch for narrow framing: if the question is binary (should I do X?), generate the missing "
                 "third option and restate as 'best use of the resources X consumes'. If emotion is loud, add "
                 "distance: what would they tell their best friend to do? Before anything irreversible, design "
                 "an ooch, the smallest real-world test of the load-bearing assumption, and attach a tripwire "
                 "(a metric or date that forces re-decision) to whatever gets committed."),
    },
    {
        "id": "klein_rpd", "book": "Sources of Power (Klein)",
        "triggers": [("instinct", 3), ("gut feel", 3), ("intuition", 3), ("something feels off", 4),
                     ("uneasy", 3), ("done this before", 3), ("experience tells", 3), ("smells wrong", 4),
                     ("can't explain", 2)],
        "lens": ("Judge whether their gut has real repetitions in THIS exact class of decision (regular "
                 "environment, many reps, fast feedback). If yes, stress-test the instinct by walking the "
                 "mental movie forward in concrete detail; where the movie goes vague is where the plan breaks. "
                 "If the situation is novel to them, say plainly that their gut is untrained here and route to "
                 "base rates. If they report wordless unease, hunt the anomaly: what expected signal is missing?"),
    },
    {
        "id": "taleb_swan", "book": "The Black Swan (Taleb)",
        "triggers": [("stable", 2), ("steady", 2), ("always worked", 3), ("biggest client", 3),
                     ("one client", 3), ("anchor client", 3), ("depends on", 2), ("viral", 2),
                     ("worked for them", 3), ("big bet", 2), ("all in", 3), ("concentration", 2)],
        "lens": ("Check the domain first: can one event dominate outcomes here? Then averages lie; reason in "
                 "exposures and survival, not point predictions. Hunt turkey setups: the steady stream whose "
                 "sudden loss is fatal, and ask what the morning it breaks looks like. When a success story is "
                 "cited as proof, demand the graveyard: name failures who ran the same playbook. Cash rule: "
                 "sacred runway plus small capped bets, nothing in the mushy middle."),
    },
    {
        "id": "taleb_antifragile", "book": "Antifragile (Taleb)",
        "triggers": [("exclusiv", 4), ("lock-in", 3), ("lock in", 3), ("long-term contract", 3), ("lease", 2),
                     ("2 year", 2), ("3 year", 2), ("downside", 2), ("hedge", 2), ("experiment", 2),
                     ("add a", 1), ("new tool", 2), ("minimum commitment", 3)],
        "lens": ("Price every commitment as an option bought or sold: exclusivity, locks and long terms SELL "
                 "the founder's optionality; ask whether the fee is worth years of it, and whether a pilot "
                 "structure keeps the option alive. Run the plus-minus-50% shock test on the plan's key "
                 "variable; accelerating pain means fragility found. Before recommending any addition, propose "
                 "the removal (via negativa) that could achieve more with less."),
    },
    {
        "id": "munger_incentives", "book": "Poor Charlie's Almanack (Munger)",
        "triggers": [("distributor", 3), ("investor", 2), ("partner", 2), ("agent", 2), ("broker", 2),
                     ("advisor", 2), ("commission", 3), ("everyone is", 3), ("everyone's doing", 3),
                     ("hot right now", 3), ("deal with", 2), ("negotiat", 2), ("middleman", 3)],
        "lens": ("Trace every counterparty's incentives explicitly: what do they gain, when do interests "
                 "diverge? Strip social proof: evaluate the move as if no one else on earth were doing it. "
                 "Invert: what would guarantee failure here, and are they doing any of it? Compare against "
                 "their best available alternative, never against doing nothing. If several forces push the "
                 "same way (charming authority + scarcity + herd), name the lollapalooza and slow it down."),
    },
    {
        "id": "bevelin_wisdom", "book": "Seeking Wisdom (Bevelin)",
        "triggers": [("urgent", 3), ("deadline", 2), ("today only", 4), ("expires", 3), ("must decide now", 4),
                     ("pressure", 2), ("act fast", 3), ("do something", 3), ("can't just sit", 3),
                     ("same mistake", 4), ("happened again", 3)],
        "lens": ("Ask whether the urgent action buys progress or relieves anxiety: what actually happens if "
                 "they do nothing for two weeks? Counterparty-imposed urgency is manufactured scarcity, a tell. "
                 "Force one piece of contrary evidence into the record before accepting their first conclusion. "
                 "Weight cost-of-being-wrong above probability-of-being-right whenever failure is fatal. If "
                 "this repeats a past pattern from their ledger, quote their own previous outcome back to them."),
    },
    {
        "id": "parrish_models", "book": "The Great Mental Models (Parrish)",
        "triggers": [("suddenly dropped", 3), ("spike", 2), ("no idea why", 3), ("root cause", 3),
                     ("industry standard", 3), ("industry norm", 3), ("that's how it works", 3),
                     ("always done", 2), ("why is this", 2)],
        "lens": ("Pick the lens deliberately and say why it fits the terrain: simple mechanics first (Occam and "
                 "Hanlon: checkout bug before market shift, incompetence before malice), then incentives, then "
                 "systems, then first principles. When they cite an industry norm as a law, decompose it: which "
                 "part is physics, which part is habit? Run one 'and then what?' pass beyond the first-order "
                 "effect before endorsing anything."),
    },
    {
        "id": "rumelt_kernel", "book": "Good Strategy/Bad Strategy (Rumelt)",
        "triggers": [("strategy", 3), ("grow to", 2), ("revenue goal", 3), ("my goal is", 3), ("reach 1", 1),
                     ("double", 2), ("triple", 2), ("3x", 2), ("plan for the year", 3), ("priorities", 2),
                     ("too many things", 3), ("spread thin", 3), ("focus on", 1)],
        "lens": ("A goal is not a plan. Build the kernel: diagnose the ONE critical obstacle, set a guiding "
                 "policy that rules options OUT, then 2-3 mutually reinforcing actions. If their effort is "
                 "spread, find the pivot point where focused force is amplified and force-rank the rest away. "
                 "Convert grand targets into the nearest proximate objective whose achievement changes what is "
                 "possible. Find the weakest link in their chain and refuse to optimize the strong links."),
    },
    {
        "id": "helmer_power", "book": "7 Powers (Helmer)",
        "triggers": [("competitor", 3), ("moat", 4), ("advantage", 2), ("copy us", 3), ("copycat", 3),
                     ("big player", 3), ("incumbent", 3), ("differentiat", 2), ("compete with", 3),
                     ("amazon", 2), ("flipkart", 2), ("blinkit", 2), ("zepto", 2)],
        "lens": ("Their claimed advantage must pass BOTH tests: a benefit AND a barrier. If a competitor can "
                 "copy it, it is operational excellence, not a moat, and will be competed away. Diagnose stage: "
                 "an early founder can realistically hold counter-positioning (the move a big player refuses to "
                 "copy because it hurts them) and cornered resources (what only they have); network and scale "
                 "powers get built during takeoff or never. Flag any deal that sells a future power, exclusivity, "
                 "customer data or brand control, for short-term volume."),
    },
    {
        "id": "lafley_wwhtt", "book": "Playing to Win (Lafley & Martin)",
        "triggers": [("which market", 3), ("segment", 2), ("expand to", 3), ("new city", 2), ("new channel", 3),
                     ("positioning", 2), ("target customer", 3), ("where to play", 4), ("go after", 2),
                     ("both options", 3), ("two options", 3)],
        "lens": ("Convert 'should I do X' into 'what would have to be true for X to be the right choice': list "
                 "the conditions, isolate the least certain one, and design its cheapest test before money "
                 "moves. Force the where-to-play choice: which single field can they WIN in the next 6-12 "
                 "months, and who are they deliberately NOT serving? How-to-win has exactly two doors: "
                 "structurally cheaper, or provably worth paying more for. Stuck in the middle loses to both."),
    },
    {
        "id": "bungay_action", "book": "The Art of Action (Bungay)",
        "triggers": [("delegate", 3), ("my team", 2), ("hired", 2), ("hiring", 2), ("didn't follow", 3),
                     ("didn't execute", 3), ("plan failed", 4), ("didn't work out", 2), ("miscommunicat", 3),
                     ("roadmap", 2), ("detailed plan", 3)],
        "lens": ("When a plan failed, diagnose WHICH gap ate it: knowledge (they could not have known; act to "
                 "learn), alignment (people understood differently; give intent, the what and why, and demand a "
                 "back-brief), or effects (reality responded; shorten the feedback loop). Never prescribe 'plan "
                 "harder'. Every delegation carries intent plus constraints plus freedoms, and the receiver "
                 "explains it back before executing. Plan in detail only to the next feedback event."),
    },
    {
        "id": "horowitz_struggle", "book": "The Hard Thing About Hard Things (Horowitz)",
        "triggers": [("scared", 3), ("afraid", 3), ("terrified", 4), ("overwhelmed", 3), ("burning out", 3),
                     ("burnt out", 3), ("hopeless", 4), ("fire him", 3), ("fire her", 3), ("layoff", 3),
                     ("crisis", 3), ("losing sleep", 4), ("failing", 2), ("shut down", 3), ("give up", 3)],
        "lens": ("If despair or fear is in their words, name the Struggle as normal before any analysis, reduce "
                 "isolation, then produce the single next move inside 48 hours; hope lives in moves, not "
                 "reassurance. Runway under six months means wartime: one priority, speed over elegance, strip "
                 "all peacetime advice. If they propose a clever pivot around a core weakness, ask what "
                 "lead-bullet work is being avoided. Script the honest version of bad news; the team already knows."),
    },
    {
        "id": "grove_leverage", "book": "High Output Management (Grove)",
        "triggers": [("no time", 3), ("doing everything myself", 4), ("bottleneck", 3), ("productivity", 2),
                     ("too many meetings", 3), ("process", 1), ("kpi", 2), ("metrics", 2), ("capacity", 2),
                     ("overloaded", 3), ("wearing all hats", 4), ("one-man", 3), ("solo founder", 3)],
        "lens": ("Map their engine as production stages and find the limiting step; refuse to optimize anything "
                 "else until it moves. Audit founder-hours by leverage: which single act (training someone, one "
                 "delegation, one early no) multiplies output most? Pair every quantity metric with its quality "
                 "shadow before celebrating. Convert vague goals into one objective plus 2-3 verifiable key "
                 "results with a fixed review date."),
    },
    {
        "id": "thorndike_capital", "book": "The Outsiders (Thorndike)",
        "triggers": [("surplus", 3), ("profit this", 2), ("extra cash", 3), ("where to invest", 3),
                     ("reinvest", 3), ("allocate", 3), ("spend it on", 2), ("buy a", 1), ("acquire", 2),
                     ("savings", 2), ("what to do with", 2)],
        "lens": ("Surplus cash or freed capacity is a DECISION, not a residue: enumerate the possible uses "
                 "(product, growth, debt, buffer, new bets) and compare expected returns explicitly. Evaluate "
                 "growth by owner-value per rupee of risk and per founder-hour, not by size; bigger and more "
                 "valuable are different directions surprisingly often. Restate any deal as three numbers: when "
                 "cash leaves, when it returns, how certain the return. When the industry stampedes one way, "
                 "ask what the rush misprices for a patient player."),
    },
    {
        "id": "dalio_principles", "book": "Principles (Dalio)",
        "triggers": [("lesson", 2), ("went wrong", 3), ("mistake", 2), ("post-mortem", 3), ("postmortem", 3),
                     ("review", 1), ("keeps happening", 4), ("second time", 3), ("disagree", 2),
                     ("conflicting advice", 4), ("opinions differ", 3)],
        "lens": ("After any outcome lands, extract the if-then principle for their written rulebook and reuse "
                 "it the next time the pattern appears. If the same problem has occurred twice, ban "
                 "instance-fixing: redesign the machine (the process, role or rule) that produces it. Before "
                 "big calls, put the strongest believable dissenting view on the record. Weight advice by "
                 "domain track record and causal reasoning, never by confidence or seniority."),
    },
    {
        "id": "meadows_systems", "book": "Thinking in Systems (Meadows)",
        "triggers": [("recurring", 3), ("cycle", 2), ("every month same", 4), ("oscillat", 3), ("inventory", 2),
                     ("stockout", 3), ("overstock", 3), ("delay", 2), ("lag", 2), ("churn", 2),
                     ("growth stalled", 3), ("plateau", 3), ("discount to hit", 3), ("keeps coming back", 3)],
        "lens": ("Diagnose structure, not events: name the stock, the flows, the delay, and the feedback loop "
                 "generating the pattern; if a classic trap is present (shifting the burden onto discounts, "
                 "escalation, eroding goals, rule-beating), name it and its standard exit. State the expected "
                 "delay before judging any action, to prevent panic reversals mid-delay. Climb the leverage "
                 "ladder: prefer changing information flows and rules over tweaking prices and budgets."),
    },
    {
        "id": "senge_learning", "book": "The Fifth Discipline (Senge)",
        "triggers": [("market is bad", 3), ("economy", 2), ("team doesn't", 3), ("nobody cares", 3),
                     ("culture", 2), ("morale", 3), ("they agreed but", 4), ("blame", 2), ("vision", 2),
                     ("slowly getting worse", 4), ("gradual", 2)],
        "lens": ("Check which learning disability blocks their read: 'the enemy is out there' (externalizing "
                 "internally-generated problems), event-fixation, boiled-frog drift (gradual decline never "
                 "triggering alarm), or identity fused to a role. Walk their conclusion down the ladder of "
                 "inference to the raw observations underneath. If growth stalls despite pushing harder, find "
                 "what is pushing back and invest there. Protect the tension between dream and reality; never "
                 "let them shrink the vision silently to feel better."),
    },
    {
        "id": "flyvbjerg_bigthings", "book": "How Big Things Get Done (Flyvbjerg)",
        "triggers": [("launch", 2), ("build a", 2), ("big project", 3), ("how long will", 3), ("months to", 2),
                     ("expansion", 2), ("scale up", 3), ("roll out", 3), ("rollout", 3), ("new factory", 3),
                     ("new product line", 3), ("website redesign", 2), ("app development", 2)],
        "lens": ("Anchor every estimate on the reference class: what did the last ten who tried this actually "
                 "spend and take? Their case is not different. Demand the storyboard version, the cheapest full "
                 "rehearsal (pilot batch, landing page, pre-orders), before capital commits. Convert big moves "
                 "into repeatable modules where unit two learns from unit one. Compress the delivery window: "
                 "every week a project stays open is another spin of the black-swan wheel. Define done and dead "
                 "in numbers, now, while no ego is invested."),
    },
]

# Books whose lessons apply so broadly they get a small tie-break boost
_TIER1_BOOST = {"kahneman_bias", "heath_wrap", "taleb_swan", "munger_incentives", "rumelt_kernel"}


def select_lenses(latest_msg: str, model: dict | None = None, max_lenses: int = 3, min_score: int = 2):
    """Pure function: pick the most relevant reasoning modules for this turn.
    Returns a prompt block string, or "" when nothing scores (keeps prompts lean)."""
    hay = (latest_msg or "").lower()
    if model:
        try:
            hay += " " + json.dumps(model, ensure_ascii=False, default=str).lower()
        except Exception:
            pass
    scored = []
    for m in MODULES:
        s = sum(w for kw, w in m["triggers"] if kw in hay)
        if s >= min_score:
            scored.append((s + (0.5 if m["id"] in _TIER1_BOOST else 0.0), m))
    if not scored:
        return ""
    scored.sort(key=lambda t: -t[0])
    chosen = [m for _, m in scored[:max_lenses]]
    lines = "\n".join(f"- [{m['book']}] {m['lens']}" for m in chosen)
    return (
        "REASONING LENSES (from the decision-science knowledge base; the frameworks most relevant to this "
        "turn). Apply them SILENTLY inside your reasoning sweep and weave the conclusions naturally into your "
        "reply. Never lecture, never list frameworks, never mention 'lenses'; you may credit a thinker by name "
        "at most once per reply and only when it genuinely adds weight:\n" + lines
    )
