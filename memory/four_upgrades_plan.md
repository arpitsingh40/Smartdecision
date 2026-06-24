# Four Upgrades — Implementation Plan (Execution + Outcome Control)

> Owner: main agent. Scope: take "Aligned Execution" from working MVP to BEST value.
> Source of these 4: the value assessment after full-app testing (founder clarity, decision engine, execution, memory).
> No new API keys/integrations. Anthropic (Claude) is LIVE = real money. Zoho is LIVE = never complete real payments.

## Codebase anchors (do not relearn from scratch)
- Backend: /app/backend/{server.py, engine.py, decision_brain.py, organizations.py, db.py, ledger.py, security.py}
- Collections (db.py): users, organizations(orgs_col), org_members(members_col), org_invites(invites_col),
  decisions(decisions_col), doc_trees, doc_nodes, goal_threads, credit_ledger, stats.
- decisions_col row: {id, org_id|null, user_id, user_name, session_id, question, mode, found_in_docs,
  answer, recommendation, plan, citations, model, cost, tokens, created_at, committed_action, status(open|done|dropped),
  committed_at, status_at, strategic_alignment:{score,reason}}  # strategic_alignment is FOUNDER-ONLY
- Brain ask: POST /api/brain/ask (AskIn{question, session_id?}) -> 1 LLM call; alignment stripped from member response.
- Cockpit: GET /api/org/cockpit (owner-only). Strategy: GET/PUT /api/org/strategy (owner-only).
- Frontend: /app/frontend/src/pages/{CockpitPage,BrainPage,TeamPage,JoinPage}.js ; components/TopBar.js ; lib/api.js
- Charts: CHECK /app/frontend/package.json before adding any lib. Prefer lightweight inline SVG bars; only use a
  chart lib (e.g. recharts) IF already present. Do NOT add heavy deps for v1.

## GLOBAL GUARDRAILS (apply to every upgrade)
- THE MOAT IS SACRED: never return the founder strategy or strategic_alignment (score/reason/confidence/basis)
  to a member in any payload (ask response, /decisions history, member pages). Enforce server-side. /cockpit stays owner-only (403).
- LLM budget per test run: state an explicit cap and instruct deep_testing_backend_v2 / auto_frontend_testing_agent.
  Free (no-LLM) features must be tested fully; LLM features capped at <=3 calls/run.
- Never trigger real Zoho checkout. Never delete .git/.emergent. Use search_replace for existing files, bulk/create for new.
- Definition of DONE (every upgrade): lint clean (py + js) -> backend tested via deep_testing_backend_v2 ->
  frontend screenshot self-verify -> (ask user before auto_frontend_testing_agent) -> update PRD.md + test_result.md.

## RECOMMENDED BUILD ORDER (each independently shippable; reorder allowed)
1) Upgrade 1 (Cockpit Momentum) — highest founder "wow", free, no LLM.
2) Upgrade 3 (Calibrate Alignment) — small, rides existing call, makes clarity trustworthy.
3) Upgrade 4 (Member Decision Room) — free, surfaces existing ledger, closes execution loop for members.
4) Upgrade 2 (Multi-turn Brain Depth) — biggest engine change, do last with care + LLM budget.

============================================================
## UPGRADE 1 — COCKPIT MOMENTUM OVER TIME  (spine: FOUNDER CLARITY)
============================================================
GOAL: founder sees the gap to the dream CLOSING week over week — alignment trend, decision velocity,
follow-through trend, plus delta vs previous period. This is the emotional payoff of the cockpit.

DATA: no new collection for v1 — compute weekly buckets on the fly from decisions_col (created_at, strategic_alignment.score, status).
  (Future v2: nightly `cockpit_snapshots` for cheap historical reads at scale; NOT needed now.)

BACKEND (organizations.py):
- New GET /api/org/cockpit/trend?weeks=8 (owner-only via _require_owner).
  Returns {weeks:[{week_start(ISO date, Monday), decisions, avg_alignment(int|null), done, committed,
  follow_through_pct(int|null)}], deltas:{avg_alignment, follow_through_pct, decisions} (current vs previous week, signed int|null)}.
  Implementation: bucket org decisions by ISO week for the last `weeks` (cap 1..26). avg_alignment from scored rows in week.
- Keep existing /cockpit unchanged; trend is a separate call so the page can lazy-load it.

FRONTEND (CockpitPage.js):
- Add a "Momentum" section under the top stat cards. Fetch /org/cockpit/trend on mount.
- Render: (a) a simple inline-SVG bar/line of avg_alignment per week (height = score/100), (b) delta chips:
  "Alignment {+/-N} vs last week", "Follow-through {+/-N}%", "Decisions {+/-N}". Color +green / -red / 0 muted.
- Empty/É1-week state: "Not enough history yet — momentum appears as your team makes decisions over weeks."
- testids: cockpit-momentum, cockpit-trend-bar, cockpit-delta-alignment, cockpit-delta-followthrough.

EXECUTION CONTROL (build + test steps):
1. Implement trend endpoint; lint py.
2. TEST (FREE, no LLM): seed via a script that inserts ~6 decisions across 3 backdated weeks (set created_at,
   strategic_alignment.score, status) into decisions_col for the Acme Solar org; call /org/cockpit/trend as owner;
   assert weeks array length, avg_alignment per week correct, deltas signed correctly. Member -> 403.
   (Clean up the seeded backdated rows after, OR keep as demo.)
3. Build CockpitPage momentum section; lint js; restart frontend; screenshot owner cockpit shows the trend + deltas.
4. deep_testing_backend_v2 task (LLM cap 0): verify trend endpoint shape, owner-gating, delta math, weeks clamp (weeks=0->min1, weeks=999->cap26).

OUTCOME CONTROL (success criteria + metrics):
- SUCCESS: with >=2 weeks of data the founder sees a non-flat trend + correct signed deltas; with <2 weeks sees the empty state; member 403.
- METRIC: trend endpoint returns N weekly buckets; avg_alignment and follow_through_pct recomputed match a manual count on seeded data.
- ABORT/ROLLBACK: if weekly bucketing is wrong or slow on larger data, fall back to a simple "last 7d vs prior 7d" two-number delta only (still ships founder clarity) and defer the chart.

============================================================
## UPGRADE 2 — MULTI-TURN BRAIN DEPTH  (spine: DECISION ENGINE)
============================================================
GOAL: the brain digs before it commits. A member can go 2-3 turns on one decision; each turn uses prior turns as context;
when a decision hinges on a missing fact the brain still commits a provisional call AND offers ONE connected sharpening question
that, when answered, continues the SAME session and tightens the recommendation. Higher-reliability decisions.

DATA: reuse decisions_col.session_id (already captured). A "session" = decisions sharing (user_id, session_id), ordered by created_at.

BACKEND (decision_brain.py):
- ask(): if body.session_id present, load prior decisions of THIS user in that session (last K=4, oldest->newest);
  build SESSION_HISTORY block (Q + the recommendation/answer given) and inject into brain_answer prompt BEFORE the new USER MESSAGE.
- brain_answer(): add optional output field `sharpening_question` (string|null): the ONE connected question that would most
  change/tighten the recommendation (per the commit-then-sharpen rule already in SYSTEM). Parser: out["sharpening_question"]=_clean(...) or null.
  Keep all existing fields. Do NOT make it required.
- Return sharpening_question in the member response (it is NOT secret — it's the engine asking the member). Strategic_alignment still stripped.
- Cost note: each extra turn = 1 LLM call (user-initiated, billed via existing reserve-and-reconcile). Cap session history injection size.

FRONTEND (BrainPage.js):
- Generate a session_id (uuid) when a NEW question is started; keep it while the user is sharpening; reset on "Ask something new".
- Render the session as a short thread: prior Q + answer cards stacked (most recent at bottom), not just the last one.
- If result.sharpening_question present: show it as a tappable "Sharpen this ->" prompt that prefills/sends a follow-up /ask with the SAME session_id.
- testids: brain-session-thread, brain-sharpen-question, brain-sharpen-send, brain-new-question.

EXECUTION CONTROL:
1. Backend: session history injection + sharpening_question field; lint.
2. TEST (LLM cap 2): same session_id, ask Q1 (underspecified, e.g. "should we discount this deal?"), expect a provisional
   recommendation + a non-null sharpening_question. Ask Q2 in same session answering it; assert Q2 response references/uses Q1 context
   (more specific) and credits decreased. Verify strategic_alignment NOT in either member response. Two decision rows share session_id.
3. Frontend: session thread + sharpen control; lint; restart; screenshot a 2-turn session.
4. Ask user before auto_frontend_testing_agent (LLM cap 2).

OUTCOME CONTROL:
- SUCCESS: turn-2 answer is demonstrably more specific than turn-1 and reflects the user's clarification; sharpening_question
  appears only when a real fact is missing (not on already-complete asks); both turns stored under one session_id; no alignment leak.
- METRIC: in the 2-turn test, turn-2 recommendation contains a concrete detail introduced only in turn-2's user message.
- ABORT/ROLLBACK: if multi-turn context causes drift/hallucination or cost spikes, cap history to the single previous turn,
  or ship sharpening_question WITHOUT history injection (still adds value), and revisit.

============================================================
## UPGRADE 3 — CALIBRATE & EXPOSE THE ALIGNMENT SIGNAL  (spine: FOUNDER CLARITY / TRUST)
============================================================
GOAL: the founder must trust the alignment number. Add a confidence + basis so a single un-calibrated score isn't over-trusted,
and surface "needs your eyes" = confidently-off-strategy AND unsure-but-impactful decisions.

DATA: extend strategic_alignment from {score,reason} to {score, reason, confidence(high|medium|low), basis(short)}.
  Backward compatible: old rows without confidence treated as confidence=null.

BACKEND:
- decision_brain.py _strategy_block: extend the private telemetry instruction to also emit confidence + basis inside strategic_alignment.
- _sanitize_alignment: accept + clamp confidence to {high,medium,low} else null; basis str[:200].
- organizations.py /cockpit: add `low_confidence_count` (scored rows with confidence in {low} OR null) and include confidence
  in each drift item. Add a `needs_attention` list = decisions where (score<40) OR (confidence=='low' AND score<70), recent, limit 10.
- Still FOUNDER-ONLY; never returned to members.

FRONTEND (CockpitPage.js):
- Show a confidence chip on each drift/needs-attention item (High/Med/Low). Add a "Needs your eyes" section (needs_attention list).
- Avg alignment card: add a small subtext like "{low_confidence_count} low-confidence" so the founder weighs the average.
- testids: cockpit-needs-attention, cockpit-conf-chip.

EXECUTION CONTROL:
1. Backend changes; lint.
2. TEST (LLM cap 1): one member ask with strategy set; verify stored strategic_alignment now has confidence+basis;
   cockpit returns low_confidence_count + needs_attention + confidence on drift; member never sees any of it.
3. Frontend chips + needs-attention; lint; restart; screenshot.

OUTCOME CONTROL:
- SUCCESS: every new scored decision carries confidence+basis; founder can distinguish "confidently off-strategy" from "unsure";
  needs_attention surfaces the right rows; zero member leakage (re-verify).
- METRIC: a low-margin/odd decision yields confidence!=null; a clearly off-strategy decision appears in needs_attention.
- ABORT/ROLLBACK: if confidence is noisy/unhelpful, keep storing it but hide the chip; or replace with a simple heuristic
  (found_in_docs + score band) instead of model self-report.

============================================================
## UPGRADE 4 — MEMBER DECISION ROOM  (spine: EXECUTION + MEMORY)
============================================================
GOAL: a member has a home for their decisions + commitments. They see open commitments first (things they said they'd do
but haven't), can mark done/dropped, and browse history. Closes the knowing->doing loop on the member side; feeds the cockpit.

DATA: no schema change — decisions_col already has question, recommendation, committed_action, status, created_at, session_id.

BACKEND (decision_brain.py):
- GET /api/brain/decisions already returns member's own history (no alignment). Add optional ?status= filter and ensure
  committed_action/status/committed_at/status_at are present (they are). Add GET /api/brain/decisions/stats (member self):
  {open_commitments, done, dropped, total}. (open_commitments = committed_action!=null AND status=='open'.)
- Reuse existing commit + status endpoints (owner-scoped to self already via user_id match).

FRONTEND (new page DecisionsPage.js, route /decisions; TopBar item "My decisions" for ALL logged-in users):
- Top: self-stats row (Open commitments / Done / Total). "Open commitments" highlighted.
- List: each decision = question + mode badge + (if committed) the committed_action with done/dropped controls + date.
  Open-but-uncommitted decisions show a "commit a move" inline (reuse commit endpoint). Filter pills: Open / Done / All.
- testids: decisions-page, decisions-stats, decision-row, decision-commit-input, decision-mark-done, decisions-filter.

EXECUTION CONTROL:
1. Backend stats endpoint + filter; lint.
2. TEST (FREE, no LLM): member with existing decisions -> /decisions list + /decisions/stats correct; commit on an
   uncommitted decision -> open_commitments increments; mark done -> done increments, open decrements; status filter works;
   NO alignment in any payload; cannot act on another user's decision (404).
3. Frontend page + TopBar entry; lint; restart; screenshot member /decisions.

OUTCOME CONTROL:
- SUCCESS: member sees open commitments and can close them; cockpit follow-through reflects member actions; no alignment leak.
- METRIC: stats numbers match decisions_col counts for that user; marking done updates both /decisions/stats and owner /cockpit.
- ABORT/ROLLBACK: if a full page is too much, ship as a "My decisions" tab/section on BrainPage reusing the same data.

============================================================
## CROSS-UPGRADE OUTCOME DASHBOARD (how we know we reached BEST value)
============================================================
- Founder clarity: cockpit shows momentum trend (U1) + trustworthy alignment with confidence (U3). Founder can answer
  "are we getting closer to the dream?" in <10s.
- Decision engine: multi-turn depth (U2) — turn-2 decisions measurably more specific; commit-then-sharpen never deflects.
- Execution: member decision room (U4) + cockpit follow-through trend — open commitments get closed; follow_through_pct trends up.
- Memory: decision ledger powers all four; session memory (U2) compounds within a decision; KB + North Star unchanged.
- The MOAT re-verified after EACH upgrade: members never receive strategy or alignment; /cockpit 403 for members.
- BUSINESS proof (beyond code): get 3-5 real teams; watch decisions->done->alignment trend over 2-4 weeks. No test substitutes for this.
