"""Reasoning Lenses — the applied layer of the 20-book decision-science knowledge base.

Each of the 20 dossiers in /app/backend/knowledge/ is distilled here into a compact,
imperative reasoning MODULE. select_lenses() scores modules against the founder's
latest message + situation model and returns the top matches as a prompt block, so
the engine APPLIES frameworks (Munger, Tetlock, Rumelt, Meadows, Klein...) silently
instead of summarizing books. Pure functions, zero LLM cost, ~600 extra tokens/turn max.
"""

import json
from typing import Optional

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
    # ---------------- demand-creation corpus (brand / psychology / sales / growth / product) ----------------
    {
        "id": "ries_positioning", "book": "Positioning + 22 Laws (Ries & Trout) + Obviously Awesome (Dunford)",
        "triggers": [("positioning", 4), ("brand name", 3), ("tagline", 3), ("category", 2), ("stand out", 3),
                     ("differentiate", 2), ("known for", 3), ("second product", 3), ("new product line", 2),
                     ("rebrand", 4), ("me-too", 3), ("crowded", 2)],
        "lens": ("Marketing is a battle of perceptions: ask what ONE word or slot they can own FIRST in a "
                 "definable mind, and what they must sacrifice to own it. If a leader exists, position as the "
                 "OPPOSITE, never a cheaper copy; if no slot is winnable, create a narrower category where they "
                 "are honestly first. Set positioning by context: competitive alternative (what would customers "
                 "do without you?), unique attribute, proof, best-fit segment, category frame. Guard against "
                 "line extension: a name stretched across products stands for nothing."),
    },
    {
        "id": "miller_storybrand", "book": "StoryBrand (Miller) + Made to Stick (Heath)",
        "triggers": [("website", 2), ("landing page", 3), ("pitch", 2), ("messaging", 3), ("copy", 2),
                     ("confusing", 3), ("don't get it", 4), ("explain what we do", 4), ("conversion", 2),
                     ("bounce", 2), ("nobody responds", 3)],
        "lens": ("If they confuse, they lose: the customer is the hero, the brand only the guide (empathy + "
                 "authority proof). Find the INTERNAL problem (the feeling before they search) beneath the "
                 "external one, and sell its resolution. Run the grunt test: what do you offer, how does my "
                 "life improve, how do I buy, answerable in five seconds. Make every line concrete (scenes, "
                 "numbers, names, never adjectives), open a curiosity gap before facts, add stakes (what is "
                 "lost by not acting) and a 3-step plan with one loud direct CTA."),
    },
    {
        "id": "sharp_growth", "book": "How Brands Grow (Sharp)",
        "triggers": [("loyalty", 3), ("retention program", 3), ("repeat customer", 2), ("awareness", 3),
                     ("reach", 2), ("light buyers", 4), ("penetration", 4), ("ads not working", 3),
                     ("grow the brand", 3), ("more customers", 2)],
        "lens": ("Brands grow by PENETRATION, recruiting new and light buyers, not by deepening loyalty of a "
                 "small base; loyalty follows size. Growth = mental availability (links between the brand and "
                 "many buying situations, refreshed continuously) + physical availability (easy to find and buy "
                 "wherever the category is bought). Distinctiveness beats differentiation: freeze the colors, "
                 "logo, tagline and repeat for years. Check reach math before engagement metrics: marketing "
                 "that only speaks to existing fans preaches to the converted."),
    },
    {
        "id": "ogilvy_ads", "book": "Ogilvy on Advertising",
        "triggers": [("ad copy", 3), ("advertising", 2), ("creative", 2), ("campaign", 2), ("headline", 4),
                     ("instagram ad", 3), ("facebook ad", 3), ("google ads", 2), ("ctr", 3)],
        "lens": ("If it doesn't sell, it isn't creative: define the counted action before admiring the ad. The "
                 "headline is 80% of the money: benefit + specificity + audience in the first line; write "
                 "twenty, test two. Replace every adjective with a number, a name, or a demonstration; "
                 "specifics are believed, superlatives are wallpaper. Mine reviews and chats for the customer's "
                 "own phrases; the best copy is assembled from their words. Keep one repeatable brand device "
                 "and reuse winning ads until fatigue is proven, not felt."),
    },
    {
        "id": "cialdini_influence", "book": "Influence + Pre-Suasion (Cialdini)",
        "triggers": [("convert", 2), ("persuade", 3), ("trust us", 2), ("testimonial", 3), ("social proof", 4),
                     ("urgency", 3), ("free sample", 3), ("abandoned cart", 3), ("follow up", 2),
                     ("they're pressuring", 3), ("limited time", 3)],
        "lens": ("Map the seven levers ethically: give first (reciprocity debt does the selling), build ladders "
                 "of small public commitments, show proof from PEOPLE LIKE THEM at the decision point, admit a "
                 "weakness before the strength (trustworthy authority), use only TRUE scarcity framed as loss, "
                 "and invoke shared identity (unity). Sequence the moment BEFORE the message: whatever is focal "
                 "seems causal, so choose the opening question or image deliberately. In defense mode: when a "
                 "counterparty uses deadlines, favors or 'everyone signed', name the lever and re-examine bare merits."),
    },
    {
        "id": "berger_contagious", "book": "Contagious (Berger)",
        "triggers": [("word of mouth", 4), ("viral", 3), ("referral", 3), ("share", 2), ("buzz", 3),
                     ("organic growth", 3), ("tell their friends", 4), ("reels", 2), ("shareable", 3)],
        "lens": ("Engineer STEPPS, not luck: Social Currency (does sharing this make the sharer look good? find "
                 "the inner remarkability), Triggers (link the product to a frequent cue in daily life; "
                 "top-of-mind is tip-of-tongue), Emotion (high-arousal awe, amusement or useful anger; sadness "
                 "kills sharing), Public (make usage visible, leave behavioral residue), Practical Value "
                 "(genuinely useful content spreads; frame deals by the rule of 100), Stories (a narrative "
                 "Trojan horse that cannot be retold WITHOUT the brand)."),
    },
    {
        "id": "sutherland_alchemy", "book": "Alchemy (Sutherland)",
        "triggers": [("perceived value", 4), ("premium", 3), ("packaging", 3), ("feels cheap", 4),
                     ("price perception", 3), ("luxury", 2), ("commodity", 3), ("irrational", 3),
                     ("why won't they pay", 3)],
        "lens": ("Perceived value IS real value: the problem may be psychological, not functional, and the fix "
                 "may cost nothing (naming, framing, ritual, story, packaging). The opposite of a good idea can "
                 "be another good idea; test the counterintuitive cheaply. Costly signals build trust (visible "
                 "effort, guarantees, craftsmanship details). Small semantic changes move big behavior: rename "
                 "the thing, reframe the moment, redesign the default. Don't design for the average customer; "
                 "solve for a vivid extreme and the middle follows."),
    },
    {
        "id": "rackham_spin", "book": "SPIN Selling (Rackham) + Challenger Sale (Dixon)",
        "triggers": [("sales call", 3), ("b2b", 3), ("corporate client", 3), ("enterprise", 2), ("demo", 2),
                     ("proposal", 2), ("lead went cold", 4), ("follow-up", 2), ("close the deal", 3),
                     ("procurement", 3), ("big client", 2)],
        "lens": ("In complex sales, questions outsell pitches: Situation (minimal), Problem (uncover "
                 "dissatisfaction), IMPLICATION (grow the cost of the problem until inaction hurts), Need-payoff "
                 "(let the buyer state the value themselves). Sell benefits tied to EXPLICIT needs, not "
                 "features. Teach, don't just relate: bring an insight that reframes their business and leads "
                 "uniquely to you; take control of next steps. Every call must end in an ADVANCE (a specific "
                 "commitment: date, stakeholder, pilot), never a vague continuation."),
    },
    {
        "id": "voss_negotiation", "book": "Never Split the Difference (Voss)",
        "triggers": [("negotiate", 4), ("negotiation", 4), ("counter offer", 4), ("counteroffer", 4),
                     ("they want 4", 2), ("asking for a discount", 3), ("payment terms", 3), ("haggle", 3),
                     ("their final offer", 4), ("walk away", 3), ("bargain", 3)],
        "lens": ("Negotiation is tactical empathy, not argument: label their position ('it seems like margin "
                 "risk worries you'), mirror their last words to draw them out, run an accusation audit (name "
                 "their objections before they do). Aim for 'that's right', not 'yes'. Use calibrated How/What "
                 "questions ('How am I supposed to fund 60-day terms?') to make THEM solve your constraint. "
                 "'No' is safety; invite it. Never split the difference: trade non-monetary items instead. "
                 "Anchor with ranges, use precise odd numbers, and hunt the black swan, the hidden fact that "
                 "changes the whole deal."),
    },
    {
        "id": "pink_selling", "book": "To Sell Is Human (Pink) + Psychology of Selling (Tracy)",
        "triggers": [("rejection", 3), ("cold call", 3), ("cold outreach", 3), ("hate selling", 4),
                     ("not a salesperson", 4), ("keep getting no", 4), ("door to door", 3), ("dms", 2)],
        "lens": ("Selling is moving humans, and buoyancy is trainable: before outreach use interrogative "
                 "self-talk ('can I move this person, and how?'), after rejection use a non-permanent, "
                 "non-personal explanatory style. Attune: take their perspective (their inbox, their boss, "
                 "their week), mimic their language. Clarity beats charisma: the best sellers are problem "
                 "FINDERS, surfacing the problem the buyer didn't name. People buy from people they trust; "
                 "listening builds trust faster than talking. Fear of loss moves more than desire for gain, "
                 "frame honestly. Volume desensitizes: prescribe the hundred-conversations discipline."),
    },
    {
        "id": "weinberg_traction", "book": "Traction (Weinberg & Mares)",
        "triggers": [("acquisition", 3), ("marketing channel", 4), ("where to find customers", 4),
                     ("get customers", 3), ("cac", 2), ("growth channel", 4), ("distribution", 2),
                     ("seo", 2), ("influencer", 2), ("try everything", 3)],
        "lens": ("Channels are found by Bullseye, not by fashion: brainstorm across ALL nineteen traction "
                 "channels (including unsexy ones like offline ads, community, engineering-as-marketing), rank "
                 "into three rings, cheaply test the middle three in parallel with real numbers, then focus "
                 "EVERYTHING on the single channel that works until saturation. Spend 50% of effort on product "
                 "and 50% on traction from day one. The underused channel in their industry is usually the "
                 "arbitrage: crowded channels are expensive, boring ones convert."),
    },
    {
        "id": "moore_chasm", "book": "Crossing the Chasm (Moore)",
        "triggers": [("early adopters", 4), ("mainstream", 3), ("beachhead", 4), ("niche first", 3),
                     ("scale beyond", 3), ("first customers loved", 3), ("growth stalled after", 3),
                     ("referenceable", 3), ("pragmatist", 3)],
        "lens": ("Visionary early customers and mainstream pragmatists buy DIFFERENTLY: pragmatists need "
                 "references from other pragmatists, a whole product (everything required to get the full "
                 "benefit), and a market leader to bet on. The chasm strategy is D-Day: dominate ONE narrow "
                 "beachhead segment completely (their whole problem, end to end) before adjacent niches. Use "
                 "the positioning formula: for [target] who [need], our product is a [category] that [benefit]; "
                 "unlike [alternative], we [key differentiation]."),
    },
    {
        "id": "kim_blueocean", "book": "Blue Ocean Strategy (Kim & Mauborgne)",
        "triggers": [("saturated", 3), ("price war", 4), ("too much competition", 4), ("red ocean", 4),
                     ("everyone is fighting", 3), ("undercutting", 3), ("commoditized", 3), ("new market", 2)],
        "lens": ("Escape bloody competition through value innovation: pursue differentiation AND lower cost "
                 "simultaneously by redrawing the factors of competition. Run the Four Actions grid: which "
                 "industry-standard factors can be ELIMINATED entirely, REDUCED well below standard, RAISED "
                 "well above, CREATED for the first time? Look at the three tiers of NON-customers (soon-to-be, "
                 "refusing, unexplored) rather than fighting over existing ones. A good strategic profile has "
                 "focus, divergence from rivals, and a compelling tagline."),
    },
    {
        "id": "fitzpatrick_momtest", "book": "The Mom Test (Fitzpatrick)",
        "triggers": [("customer interview", 4), ("validate", 3), ("survey", 2), ("would they buy", 4),
                     ("asked my customers", 3), ("everyone loves the idea", 4), ("positive feedback", 3),
                     ("user research", 3), ("talk to customers", 3)],
        "lens": ("Opinions about your idea are worthless; only past behavior and commitments are data. Ask "
                 "about their LIFE, not your idea: when did this problem last happen, what did it cost, what "
                 "did they try, what did they pay? 'Would you buy?' invites polite lies; compliments are the "
                 "most dangerous data. Deflect fluff ('I usually/I would/I might') to concrete past specifics. "
                 "Real validation = they give up something: money (pre-order), reputation (intro to their "
                 "boss), or significant time. No commitment extracted = the meeting failed politely."),
    },
    {
        "id": "christensen_jtbd", "book": "Competing Against Luck (Christensen, Jobs-to-be-Done)",
        "triggers": [("why do customers buy", 4), ("use case", 2), ("churned", 3), ("stopped buying", 3),
                     ("feature request", 3), ("what job", 3), ("switching from", 3), ("competitor's product", 2)],
        "lens": ("Customers don't buy products; they HIRE them to make progress in a specific circumstance, "
                 "functional, social and emotional at once. Find the job: what were they doing the moment they "
                 "sought a solution, what were they firing, what anxieties held them back, what habits pulled "
                 "them back? The real competition is whatever else gets hired for the job (a milkshake competes "
                 "with bananas and boredom). Design around the job's full journey, and measure progress the way "
                 "the CUSTOMER measures it."),
    },
    {
        "id": "ries_leanstartup", "book": "The Lean Startup (Eric Ries) + Inspired (Cagan) + Continuous Discovery (Torres)",
        "triggers": [("mvp", 4), ("launch fast", 3), ("build first", 3), ("prototype", 3), ("pivot", 3),
                     ("new feature", 2), ("test the idea", 3), ("experiment", 2), ("waiting to launch", 3),
                     ("perfect before launch", 4)],
        "lens": ("A startup's output is validated LEARNING, not features: state the riskiest assumption "
                 "(usually value or demand, rarely technology), design the smallest experiment that tests it "
                 "with real behavior, measure actionable cohort metrics, then persevere or pivot on evidence. "
                 "Beware vanity metrics and the build trap: shipped is not learned. Test four risks before "
                 "building: valuable (will they buy), usable, feasible, viable. Make discovery continuous: "
                 "weekly small customer touchpoints beat quarterly big research."),
    },
    {
        "id": "coyle_culture", "book": "The Culture Code (Coyle)",
        "triggers": [("culture", 3), ("team morale", 4), ("trust within", 3), ("team is quiet", 3),
                     ("nobody speaks up", 4), ("conflict in team", 3), ("silos", 3), ("blame culture", 4),
                     ("first employees", 3)],
        "lens": ("Culture is built from skills, not slogans: (1) SAFETY, dense small signals of belonging, "
                 "listening, gratitude, inclusion, that say 'you are safe here, we share a future'; (2) shared "
                 "VULNERABILITY, the leader admits fallibility FIRST ('what am I missing?'), unlocking honest "
                 "risk-taking and the vulnerability loop; (3) PURPOSE, flood the environment with simple vivid "
                 "narratives linking today's work to the goal ('we exist so that...'). Diagnose team problems "
                 "in that order: is it a safety gap, a vulnerability gap, or a purpose gap?"),
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


def select_lenses(latest_msg: str, model: Optional[dict] = None, max_lenses: int = 3, min_score: int = 2,
                  boost_ids: Optional[list] = None):
    """Pure function: pick the most relevant reasoning modules for this turn.
    boost_ids: module ids preferred by the detected decision category (get +3).
    Returns a prompt block string, or "" when nothing scores (keeps prompts lean)."""
    hay = (latest_msg or "").lower()
    if model:
        try:
            hay += " " + json.dumps(model, ensure_ascii=False, default=str).lower()
        except Exception:
            pass
    boosts = set(boost_ids or [])
    scored = []
    for m in MODULES:
        s = sum(w for kw, w in m["triggers"] if kw in hay)
        if m["id"] in boosts:
            s += 3
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
