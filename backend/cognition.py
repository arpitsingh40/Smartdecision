"""Cognition Core — context-aware decision intelligence for SmartDecigen.

The moat is not the prompt; it is WHAT GOES INTO the prompt. This module assembles,
at runtime and at zero LLM cost, the layers that turn a generic LLM into a mentor
who knows THIS founder:

  L1 identity  — name, dream, capacity, unfair advantage (from the questionnaire)
  L5 memory    — this founder's past relevant decisions and their real outcomes
  L6 algorithm — the per-decision-category reasoning checklist
  L4 lenses    — the 3 most relevant book-derived reasoning modules (lenses.py)

classify_decision() is a pure keyword router into 9 founder decision categories.
cognition_block() returns one string ready to inject into any engine prompt.
"""

import logging
from db import users_col, decisions_col
from lenses import select_lenses

log = logging.getLogger("cognition")

# --------------------------------------------------------------- decision-type router
# category -> (trigger keywords, preferred lens ids, reasoning algorithm)
CATEGORIES = {
    "deal_negotiation": {
        "kw": ["distributor", "deal", "offer from", "contract", "terms", "exclusiv", "negotiat", "vendor",
               "supplier", "partnership", "agreement", "mou", "franchise", "counter offer", "listing fee",
               "wants 3", "wants 4", "margin they", "their offer"],
        "lenses": ["munger_incentives", "taleb_antifragile", "voss_negotiation", "thorndike_capital", "lafley_wwhtt"],
        "algo": ("DEAL/NEGOTIATION ALGORITHM: 1) Trace the counterparty's incentives: what do they gain, where "
                 "do interests diverge? 2) Price the optionality being traded: what flexibility does this deal "
                 "sell, is the payment worth years of it, can a pilot keep the option alive? 3) What would have "
                 "to be true for this deal to be right, and what is the cheapest test of the shakiest condition? "
                 "4) Restate the deal as three numbers: cash out date, cash back date, certainty. 5) Negotiation "
                 "posture: label their position, ask calibrated How/What questions, never split the difference, "
                 "trade non-monetary terms."),
    },
    "people_team": {
        "kw": ["hire", "hiring", "fire ", "firing", "cofounder", "co-founder", "employee", "team member",
               "cto", "salary", "quit", "resign", "underperform", "delegate", "first hire", "intern",
               "agency or in-house", "freelancer"],
        "lenses": ["grove_leverage", "horowitz_struggle", "dalio_principles", "bungay_action", "coyle_culture"],
        "algo": ("PEOPLE/TEAM ALGORITHM: 1) Wartime or peacetime? Survival pressure changes the right call. "
                 "2) Person or machine: is this individual failing, or is the design (role, incentives, "
                 "information) producing the failure? 3) Task-relevant maturity: does their freedom match their "
                 "experience at THIS task? 4) Hire for the spike this stage needs, not absence of weakness. "
                 "5) For delegation: give intent (outcome + why + constraints) and demand a back-brief. "
                 "6) Check the culture signals: safety, vulnerability, purpose."),
    },
    "growth_marketing": {
        "kw": ["grow", "customers", "marketing", "ads", "instagram", "sales dropped", "channel", "traffic",
               "leads", "awareness", "brand", "followers", "reach", "promotion", "campaign", "word of mouth",
               "referral"],
        "lenses": ["weinberg_traction", "sharp_growth", "ries_positioning", "berger_contagious", "cialdini_influence"],
        "algo": ("GROWTH/MARKETING ALGORITHM: 1) Penetration math first: does this reach NEW and light buyers, "
                 "or re-touch existing fans? 2) Channel discipline: test few channels cheaply with real numbers, "
                 "then concentrate on the one that works; hunt the underpriced channel others ignore. 3) Position "
                 "check: what one word or slot do they own, in whose mind? 4) Message check: concrete, internal "
                 "problem named, grunt-test clear. 5) Count results: every campaign carries a counted action."),
    },
    "pricing_offer": {
        "kw": ["price", "pricing", "discount", "premium", "charge", "subscription", "pack", "offer", "rate card",
               "underpricing", "raise prices", "mrp", "margin on"],
        "lenses": ["sutherland_alchemy", "cialdini_influence", "helmer_power", "meadows_systems"],
        "algo": ("PRICING/OFFER ALGORITHM: 1) Perceived value is real value: what signals (name, packaging, "
                 "story, ritual) justify the price before touching the number? 2) Choose the door: structurally "
                 "cheaper or provably worth more; the middle loses to both. 3) Second-order check: what does this "
                 "discount TEACH customers to expect? Shifting the burden onto discounts atrophies the brand. "
                 "4) Loss-framed true scarcity only; fake urgency destroys trust. 5) Anchor high with a premium "
                 "option; precise odd numbers read as calculated, round numbers as negotiable."),
    },
    "product_validation": {
        "kw": ["product idea", "feature", "mvp", "launch", "validate", "prototype", "build a", "new product",
               "feedback from customers", "beta", "app idea", "would they buy", "customer interview"],
        "lenses": ["fitzpatrick_momtest", "christensen_jtbd", "ries_leanstartup", "heath_wrap"],
        "algo": ("PRODUCT/VALIDATION ALGORITHM: 1) The Mom Test: collect past behavior and commitments, never "
                 "opinions about the idea; compliments are not data. 2) Find the job-to-be-done: what progress "
                 "is the customer hiring this for, in what circumstance, firing what? 3) Name the riskiest "
                 "assumption and design the smallest real-behavior experiment that tests it. 4) Define kill "
                 "criteria before building. 5) Shipped is not learned: measure cohort behavior, not applause."),
    },
    "crisis_survival": {
        "kw": ["runway", "cash crisis", "can't pay", "cannot pay", "losing money", "shut down", "survive",
               "emergency", "debt", "loan due", "salaries due", "out of money", "3 months left", "burn"],
        "lenses": ["horowitz_struggle", "taleb_swan", "rumelt_kernel", "bevelin_wisdom"],
        "algo": ("CRISIS/SURVIVAL ALGORITHM: 1) Wartime rules: exactly one priority; strip every peacetime "
                 "initiative. 2) Sacred-runway math: what cash is untouchable, what is the honest date, which "
                 "single dependency's failure is fatal? 3) The kernel: name the ONE critical obstacle between "
                 "here and safety; ignore everything else. 4) For each urgent-feeling move, run the do-nothing "
                 "test: what actually happens if we wait two weeks? 5) Normalize the Struggle, then produce the "
                 "next 48-hour move; hope lives in moves."),
    },
    "strategy_direction": {
        "kw": ["strategy", "direction", "pivot", "focus on what", "vision", "long term", "which market",
               "expand", "where to play", "next year plan", "diversify", "new city", "second location"],
        "lenses": ["rumelt_kernel", "helmer_power", "lafley_wwhtt", "moore_chasm", "kim_blueocean"],
        "algo": ("STRATEGY/DIRECTION ALGORITHM: 1) Build the kernel: diagnosis of the critical obstacle, a "
                 "guiding policy that rules options OUT, 2-3 coherent actions. 2) Where to play: which single "
                 "field can they WIN in 6-12 months, and who is deliberately not served? 3) Power check: which "
                 "durable advantage (benefit + barrier) does this path build, and is its window open at their "
                 "stage? 4) Convert the grand goal into the nearest proximate objective. 5) Beachhead before "
                 "ocean: dominate one narrow segment completely before adjacency."),
    },
    "money_allocation": {
        "kw": ["invest", "spend on", "budget", "surplus", "profit this", "savings", "allocate", "buy equipment",
               "capex", "extra cash", "where should the money", "reinvest"],
        "lenses": ["thorndike_capital", "taleb_antifragile", "munger_incentives"],
        "algo": ("CAPITAL ALLOCATION ALGORITHM: 1) Surplus is a decision: enumerate the uses (product, growth, "
                 "debt, buffer, new bets) and compare expected returns explicitly. 2) Compare against the best "
                 "alternative, never against doing nothing. 3) Barbell the risk: sacred core, small capped "
                 "experiments, nothing medium. 4) Three numbers per option: cash out date, cash back date, "
                 "certainty. 5) Denominator check: does this grow value per founder-hour and per rupee of risk, "
                 "or just size?"),
    },
    "ops_execution": {
        "kw": ["process", "operations", "inventory", "delivery", "quality issue", "bottleneck", "time management",
               "productivity", "overwhelmed with work", "systems", "sop", "automation", "supply"],
        "lenses": ["grove_leverage", "meadows_systems", "flyvbjerg_bigthings"],
        "algo": ("OPS/EXECUTION ALGORITHM: 1) Find the limiting step: map the stages, locate the constraint, "
                 "refuse to optimize anything else. 2) Structure over blame: recurring failures indict the "
                 "design (incentives, information, delays), not the people. 3) Fix problems at the lowest-value "
                 "stage. 4) Pair every quantity metric with its quality shadow. 5) For big builds: reference-"
                 "class the estimate, pilot the storyboard version, modularize so unit two learns from unit one."),
    },
}


def classify_decision(text: str) -> str | None:
    """Pure keyword router. Returns category id or None (generic)."""
    hay = (text or "").lower()
    best, best_score = None, 0
    for cat, spec in CATEGORIES.items():
        s = sum(1 for kw in spec["kw"] if kw in hay)
        if s > best_score:
            best, best_score = cat, s
    return best if best_score >= 1 else None


# --------------------------------------------------------------- L1 founder identity
def identity_block(user: dict) -> str:
    """Who this founder is — makes the engine a mentor who KNOWS them, not a fresh consultant.
    Built from the signup name + the 4-question questionnaire (dream/capacity/advantage/potential)."""
    if not user:
        return ""
    fresh = users_col.find_one({"id": user["id"]}, {"_id": 0, "name": 1, "questionnaire": 1}) or {}
    name = (fresh.get("name") or user.get("name") or "").strip()
    q = fresh.get("questionnaire") or {}
    parts = []
    if name:
        parts.append(f"- Name: {name}")
    if (q.get("dream") or "").strip():
        parts.append(f"- Their dream (their own words): {q['dream'].strip()[:400]}")
    if (q.get("capacity") or "").strip():
        parts.append(f"- Their capacity and constraints: {q['capacity'].strip()[:400]}")
    if (q.get("advantage") or "").strip():
        parts.append(f"- Their unfair advantage: {q['advantage'].strip()[:400]}")
    if (q.get("potential") or "").strip():
        parts.append(f"- What success would mean to them: {q['potential'].strip()[:400]}")
    if not parts:
        return ""
    return (
        "THE FOUNDER YOU ARE TALKING TO (you have worked with them before; sound like a mentor who knows them: "
        "use their first name naturally but sparingly, connect advice to their stated dream and constraints, "
        "and never recite this data back as a list):\n" + "\n".join(parts)
    )


# --------------------------------------------------------------- L5 past-decision memory
def past_decisions_block(user_id: str, text: str, category: str | None, limit: int = 3) -> str:
    """This founder's most relevant past decisions + real outcomes. Relevance = shared keywords
    with the current question; falls back to recency. Zero LLM, one indexed query."""
    try:
        rows = list(decisions_col.find(
            {"user_id": user_id},
            {"_id": 0, "question": 1, "key_takeaway": 1, "committed_action": 1, "status": 1,
             "outcome": 1, "impact_inr": 1, "created_at": 1},
        ).sort("created_at", -1).limit(25))
    except Exception as e:
        log.warning(f"past_decisions lookup failed: {e}")
        return ""
    if not rows:
        return ""
    words = {w for w in (text or "").lower().split() if len(w) > 4}

    def rel(r):
        qwords = set((r.get("question") or "").lower().split())
        return len(words & qwords)

    rows.sort(key=lambda r: (-rel(r),))
    chosen = [r for r in rows if rel(r) > 0][:limit] or rows[:1]
    lines = []
    for r in chosen:
        q = (r.get("question") or "")[:220]
        tk = (r.get("key_takeaway") or "")[:220]
        line = f"- They asked: {q}\n  You advised: {tk}"
        if (r.get("committed_action") or "").strip():
            line += f"\n  They committed: {str(r['committed_action'])[:200]}"
        oc = r.get("outcome") or {}
        if isinstance(oc, dict) and oc.get("status"):
            imp = r.get("impact_inr")
            line += f"\n  Real outcome: {oc.get('status')}" + (f", impact about Rs {imp}" if imp else "")
        lines.append(line)
    return (
        "YOUR SHARED HISTORY WITH THIS FOUNDER (real past decisions; build on them, never re-suggest what "
        "failed, and when today's situation rhymes with one of these, say so explicitly):\n" + "\n".join(lines)
    )


# --------------------------------------------------------------- assembled block
def cognition_block(user: dict, text: str, model: dict | None = None,
                    include_identity: bool = True, include_memory: bool = True) -> str:
    """One string with every cognition layer that applies to this turn. Lean by design:
    empty sections are omitted entirely so quiet turns stay cheap."""
    category = classify_decision(text)
    spec = CATEGORIES.get(category) if category else None
    sections = []
    if include_identity:
        ib = identity_block(user)
        if ib:
            sections.append(ib)
    if include_memory and user:
        pb = past_decisions_block(user["id"], text, category)
        if pb:
            sections.append(pb)
    if spec:
        sections.append("DECISION TYPE DETECTED: " + category.replace("_", " ").upper() + "\n" + spec["algo"])
    lens_block = select_lenses(text, model, boost_ids=(spec["lenses"] if spec else None))
    if lens_block:
        sections.append(lens_block)
    if sections:
        log.info(f"cognition: category={category} sections={len(sections)}")
    return "\n\n".join(sections)
