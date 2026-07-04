# SmartDeciGen — Genuine-User Evaluation (July 4, 2026)

Method: full hands-on walkthrough as a realistic persona — "Arjun", a Bengaluru cloud-kitchen
founder (BrewKadak) with real unit economics — using only the live UI, exactly as a paying user
would. Live Anthropic key (claude-opus-4-8). 7 live LLM calls, ~60 credits burned end-to-end.
Admin experience tested as ceo@smartdecigen.com. No code was changed during this evaluation.

Persona account: arjun@brewkadak.com / Arjun@2026 (journey + direction + milestones + 1 brain
decision + 1 open commitment left in place as live fixture data).

---

## VERDICT IN ONE LINE
The AI brain is genuinely world-class for the price of a chai — but the shop around it has a
broken till (payments 502), silent failures at the two highest-intent moments, and its best
rooms (Brain, Ultra, Questionnaire) are behind doors users cannot find.

---

## STRENGTHS

### S1. The AI reasoning quality is the real deal (core product value: excellent)
- Turn 1 instantly computed 1100 x Rs260 ≈ Rs2.86L and REFRAMED my "revenue goal" as a margin
  problem — flagged it under "Assumptions I am hearing". This is what a great advisor does.
- Turn 2 ran the full unit-economics chain correctly (Rs187 post-commission − Rs110 COGS = Rs77
  contribution × 1100 = Rs85K − Rs55K fixed = Rs30K ≈ 6% net). All arithmetic verified correct.
- Eliminates out loud: COGS-cutting hypothesis publicly RULED OUT (40%→5%→3% with strikethrough).
- One sharp, hypothesis-separating question per turn, each with a stated rationale.
- Direction package: named trade-offs, 4 time-boxed first moves (48h/7d/10d/14d), signals to
  watch, assumptions to test.
- Milestones: 8 measurable milestones with metric + deadline derived from MY numbers
  ("275 direct orders/month, margin 15%, Month 6").
- Brain answer (corporate-park deal): working-capital lock math (Rs2L at 45-day terms), a
  ready-to-send 3-line WhatsApp counter-proposal, predicted outcome with 78% confidence and a
  3-day review clock, plus a "don't follow this if..." caveat.

### S2. Cross-feature memory
The Brain answer referenced my journey context unprompted ("your Rs 4 lakh reserve... since we
last spoke", "the WhatsApp migration needs more focus"). Journey ↔ Brain share one model of me.

### S3. Transparent reasoning UI (trust-building, rare in AI products)
Live decision-confidence %, competing hypotheses with probabilities, 9-dimension clarity bars,
"WHY I ASKED THAT", "ASSUMPTIONS I AM HEARING", structured "WHAT I UNDERSTAND" ledger.

### S4. Accountability loop delivers the landing-page promise
Commit-a-move → DONE-BY chips (Today/24h/48h/3d/1w) → global countdown timer in the header
("2d 0h") → "I did it / Dropped it" → feeds admin Execution-Rate KPI. "Kept promises. Not vibes."

### S5. Frictionless entry
Signup truly ~30 seconds, no email verification, name optional, straight into "What are you
trying to accomplish?" with 50 credits visible.

### S6. Distinctive, coherent design; solid mobile
Editorial typography, consistent across pages; 390px mobile renders cleanly (stacked milestones,
sticky composer, collapsible confidence).

### S7. Honest admin instrumentation
Users/Traffic/Usage/Launch tabs show real per-user tokens/credits/country; Launch KPIs show
honest zeros and picked up my 1 committed action; purchase history labels failures FAILED.

### S8. Graceful locked states + working referral
Cockpit lock page explains itself and offers a next step. "Give 25, get 25" invite link copies
correctly (?ref=code).

---

## WEAKNESSES (ordered by severity)

### W1. CRITICAL — Payments are broken: nobody can pay
POST /api/payments/create-order → 502. Backend log:
`zoho session create failed: Zoho OAuth refresh failed: {'error': 'invalid_code'}`
The ZOHO_REFRESH_TOKEN is invalid/expired (live mode). Every pack purchase fails.
ACTION: regenerate the Zoho refresh token (Zoho API console, accounts.zoho.in) and update .env.

### W2. CRITICAL — Silent failures at the two highest-intent moments
- Clicking "Get Starter" (payment) fails with NO error toast, no message. Button just does nothing.
- "Approve & build milestones" with low credits → 402 Payment Required, and the UI shows NOTHING.
  I was out of credits, primed to pay, and the app stayed silent. This is where conversion dies.
ACTION: catch 402/5xx globally; show "You need N credits — top up" modal wired to /billing.

### W3. HIGH — A paid Brain answer can be lost forever (UI-side)
Brain generation takes 60–100s. I navigated away mid-generation (real users will too): 10 credits
were charged, the decision was recorded, but the ANSWER is not viewable anywhere afterwards —
My Decisions shows only the question + "Commit a move". The full answer exists in MongoDB only.
ACTION: decision detail view rendering stored answer/plan/prediction; show generation state on return.

### W4. HIGH — Discoverability: the best features are unreachable
- /brain has ZERO entry points in the UI until you've already used it (nav unlocks on first
  decision — chicken-and-egg). I only found it by typing the URL.
- "Ultra thinking" exists only on ThreadPage (/thread/:id) — no path leads a solo founder there.
- QuestionnairePage.js exists (+100 bonus credits configured) but has NO ROUTE in App.js — orphaned.
  Users who run out of free credits have no earn path, and payments are down (W1) — dead end.
ACTION: permanent nav entry for the Decision Workspace; route the questionnaire; expose ultra mode.

### W5. MEDIUM — Pricing copy contradicts real costs
Observed real costs: journey turns 8 / 12 / 14 credits (token-based), direction 10, milestones 6,
brain ask 10. One happy path = 60 credits — MORE than the 50-credit free grant.
Billing page claims "10 credits (~3 normal turns)" — in reality 10 credits ≈ 1 turn. Starter ₹49
buys roughly one question. This mismatch will generate churn and refund complaints.
ACTION: either state per-turn credit ranges honestly, or price turns flat.

### W6. MEDIUM — Admin cost/margin telemetry is dead
"Cost & margin per model" shows "No LLM calls yet" despite 6 turns / ~25K tokens recorded
elsewhere. Root cause: telemetry_events collection is EMPTY — journey.py / decision_brain.py
never write LLM-call telemetry; admin /usage/models reads only types
[discussion_turn, action_assist]. The founder cannot see API cost vs revenue.
ACTION: emit telemetry docs from journey/brain paths (or widen the aggregation).

### W7. MEDIUM — Counter drift & implausible traffic numbers
- Admin "credits spent" = 56, but persona balance actually moved 60 (8+12+14+10+6+10).
- "Active now: 13" with 3 total users; avg session 37s (bot/automation sessions counted).
ACTION: reconcile stats counters against credit_ledger; de-dupe session heartbeats.

### W8. LOW — Long waits with thin feedback
Opus turns take 30–100s. There is a loading state, but no streaming, no progress, no
"this usually takes a minute" copy. Combined with W3 the wait actively costs money.

### W9. LOW — Observations
- No "forgot password" affordance on the auth card.
- Landing page has no product proof (screenshot/demo/social proof) — the promise is strong but unshown.
- Country detection put my container in "United States" (GeoIP; fine, but verify for real users).

---

## WHAT I DID NOT TEST
- Completing a REAL Zoho payment (live mode; create-order fails anyway per W1).
- Team/org flows, doc upload to Knowledge, Ultra thinking turn (unreachable per W4),
  48h thread accountability prompt, release-gate run (costs 2 LLM calls per scenario).

## SUGGESTED FIX ORDER
P0: W1 (Zoho refresh token) → W2 (surface 402/5xx) → W3 (persist/render answers)
P1: W4 (navigation + questionnaire route) → W5 (pricing copy)
P2: W6, W7 (telemetry + counters), W8 polish

## FIXTURE DATA LEFT IN PLACE
- arjun@brewkadak.com: full journey (3 turns), direction, 8 milestones, 1 brain decision with
  open 48h commitment, 190 credits (includes +200 evaluator grant recorded in credit_ledger).
- Real organic signup observed during testing: arpitkumarsingh40@gmail.com (untouched).
