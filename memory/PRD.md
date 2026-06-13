# SmartDecigen Deep Discussion Engine — PRD & Status

## Vision (founder's words)
The user walks away doing the one thing they already knew they needed to do but weren't doing. The ONE result no other AI gives: accountability — a kept promise to yourself. Goal = less distance between knowing and doing.

## Core Component: Goal-Anchored Thread
A thread holds the user's pursuit across weeks. Every turn refreshes "the easiest path forward" against updated reality. Every return after absence surfaces what changed about the user while they were gone.

## Architecture
- Stack: FastAPI + React + MongoDB. LLM: two modes per turn — NORMAL: Claude Opus 4.8 (`claude-opus-4-8`), ULTRA THINKING: Fable 5 (`claude-fable-5`, thinking={"type":"adaptive"} + extra_body output_config.effort=high, max_tokens 8000, text block must be extracted from content). Fallback chain: ultra: fable-5→opus-4-8→haiku-4-5; normal: opus-4-8→haiku-4-5. User's own ANTHROPIC_API_KEY in backend/.env.
- 4 LIVING FIELDS per thread (the primary UI): current_state_summary (3 lines), current_open_question (1 line, pinned above composer), current_easiest_path (1-2 lines), current_next_action (1 line, 24-48h, hero element).
- 3 VALUE LAYERS per turn (added after founder's "make it more worth it" feedback): current_action_payoff (benefit stated early — concrete thing held within 48h, vague banned), current_big_picture (concrete justification tying action to stated goal, quantified, generic glue banned; why_now passed in prompt as material), current_bold_move (out-of-box higher-leverage play, NULLABLE — never forced). Rendered: payoff+big-picture inside next-action box; bolder play beside easiest path (amber left border, 2-col grid).
- 4 ROLLING FIELDS computed deterministically from substrate_events (no LLM): emotional_temperature, execution_consistency (14d), pace_calibration, contradiction_history.
- TURN ENGINE: 6-step pipeline, ONE LLM call/turn. Substrate signals (emotional temp, action_done, contradiction) piggybacked on the same call.
- Intent classifier (pure regex): update|question|setback|acknowledgment|drift|silence_breaker (>=14d gap).
- RE-ENGAGEMENT: pure function, NO LLM, founder-locked PHRASE_BANK, fires on >=7d absence if substrate delta significant (exec >=0.15, emotional >=0.2, new contradiction), else None (silence-preserving).
- Credits: 100 on signup, 5/turn, atomic deduction, refund on LLM failure. Config in .env (TURN_COST, SIGNUP_CREDITS).
- Auth: email/password, bcrypt, JWT HS256 30d.
- Telemetry: discussion_turn + reengagement_shown events in telemetry_events collection.

## Key files
- /app/backend/engine.py — pure functions + LLM call (POC-proven)
- /app/backend/server.py — auth, goals, threads, turn pipeline, credits
- /app/backend/poc/test_core.py — Phase 1 POC (all 12 checks passed)
- /app/frontend/src/pages/ThreadPage.js — Situation Pane (core screen)
- /app/frontend/src/pages/{AuthPage,DashboardPage,NewGoalPage}.js
- /app/design_guidelines.md — premium minimal design system (Gloock + IBM Plex Sans)

## Status
- Phase 1 POC: DONE (12/12 checks)
- Phase 2 Full app: DONE, tested by testing agent — 100% backend (14/14), 100% frontend
- Retention Loop: DONE, tested (iteration_2, 100%) — momentum strip (kept promises / follow-through / moves this week), open-question pull lines + 48h overdue chips on goal cards, thread accountability prompt with one-tap "I did it"/"Not yet" (sends real turn)
- Conversational addictiveness: DONE, tested (iteration_3, 100%) — engine SYSTEM prompt upgraded: MIRROR line (names what user didn't say, stored as thread.current_mirror, rendered italic w/ left border), STICKY open questions (productive discomfort, generic banned), FELT MOMENTUM (streak of kept actions passed in substrate, woven into voice), BREVITY discipline. Still exactly 1 LLM call/turn.
- Value layers + dual engine modes: DONE, tested (iteration_4: backend 10/10, frontend 100%) — payoff early / big picture / bolder play in every turn; mode toggle Normal vs Ultra thinking in composer (TurnIn.mode, 422 on invalid, model+mode returned in turn response). Demo account: demo@smartdecigen.com / Demo1234! (seed: /app/scripts/seed_demo.py, idempotent). NOTE: env was restored this session (.env files recreated; user re-supplied ANTHROPIC_API_KEY).
- Founder OS + Zoho top-ups (this session): DONE, backend 100% tested (5/5 sections), frontend visually verified.
  * Founder OS at /admin for ceo@smartdecigen.com (FounderOS@2026, is_admin flag): Overview / Users (drilldown: Q&A pairs + ledger) / Traffic (IP, city, country, time spent via 60s heartbeat sessions, free ip-api.com geo cached per-IP forever) / Usage (summary-first then per-user).
  * Scale design: pre-aggregated counters in stats collection (id=global, $inc), per-user counters on user doc (questions_asked, tokens_in/out, credits_issued_free/paid), credit_ledger audit rows, indexes on every queried field, pagination everywhere. Admin reads are O(1)/O(page).
  * Token usage captured per Claude call (engine.llm_turn returns usage; telemetry rows carry mode/cost/tokens).
  * Ultra thinking costs DOUBLE: ULTRA_TURN_COST=10 vs TURN_COST=5 (.env). Refund-on-failure preserves exact cost.
  * Zoho Payments (India) top-ups: pack_100 = Rs399, pack_500 = Rs999 (one-time, NOT subscription). backend/payments.py: create-order -> hosted checkout (live) or /pay/test-checkout (simulated, ZOHO_TEST_MODE=true); idempotent fulfilment (status-guarded atomic update, double webhook cannot double-credit); HMAC webhook verification at POST /api/payments/webhook/zoho; status polling endpoint verifies against Zoho in live mode. GO LIVE: set ZOHO_ACCOUNT_ID/CLIENT_ID/CLIENT_SECRET/REFRESH_TOKEN/WEBHOOK_SECRET + ZOHO_TEST_MODE=false in backend/.env. ZERO code change.
  * Backend modules: db.py (shared client), security.py (JWT/admin gate), ledger.py (stats+ledger+startup ensure), tracking.py, admin.py, payments.py.
- Feedback loop (iteration 7, this session): DONE — backend feedback.py (POST /api/feedback rating 1-5 + category bug|idea|praise|other + message ≤2000; GET /api/admin/feedback summary+filters+pagination; PATCH /api/admin/feedback/{id} status new→reviewed→resolved; indexes in ledger.ensure_startup). Frontend: TopBar "Feedback" header link + dropdown item opens FeedbackDialog (stars/pills/textarea/sonner toast); Founder OS new Feedback tab (summary cards, status filter pills, table w/ stars + category badge + per-row status select, new rows amber-tinted). Backend tested 22/22. NOTE: .env files were reset before this session — recreated (JWT_SECRET regenerated, ANTHROPIC_API_KEY placeholder again).
- Adjust-this-step + ask-before-assume (iteration 8, this session): DONE, tested (backend 6/6, frontend 6/6 + feedback UI 9/9) — founder feedback: "engine only reacts to what user said, never asks; no way to put my opinion/obstacles into the next action". Fix A: "Adjust this step" button on next-action block (ThreadPage) → panel with 4 obstacle chips (No time / Blocked by someone / Not sure how / I have a different idea) + free-text line → sends turn with TurnIn.adjust=true → pipeline forces intent=action_adjust → engine recalibrates step around user input (must not mark done), cost = normal 5 credits, always mode normal. Fix B: SYSTEM prompt ASK BEFORE ASSUME rule — when turn hinges on unstated fact/second possibility, open question must become clarifying question naming the assumption. Still exactly 1 LLM call/turn.
- Live keys set (this session): real ANTHROPIC_API_KEY pasted — normal turn (Opus 4.8) and ultra turn (Fable 5) verified live, credits 5/10 deducted correctly. OPENAI_API_KEY stored in backend/.env (unused for now). Zoho Payments LIVE: ZOHO_TEST_MODE=false, ZOHO_ACCOUNT_ID=60061771134 (Payments account, not org id), client id/secret/refresh token verified (scopes ZohoPay.payments.CREATE+READ), webhook secret = ZOHO_PAY_WEBHOOK_SECRET value. FIXED payments.py per official spec: paymentsessions body uses amount (float) + currency (was currency_code string) + hosted_page_parameters (was hosted_checkout_parameters) + description/reference_number/meta_data; status poll reads payment_id from payments[] array. Live create-order returns real https://payments.zoho.in/hostedcheckout/<access_key>; status poll verified. Webhook URL to configure in Zoho dashboard: <app-domain>/api/payments/webhook/zoho (status-poll fulfilment works even without webhook).
- Token-based billing + ₹49 pack + stale-order auto-fail (iteration 4, Feb 2026): DONE, backend 13/13 tested.
  * **New pack**: `pack_10` = 10 credits for ₹49 ("Try it" tag) added to PACKS in payments.py; visible in /api/payments/packs and BillingPage 3-column grid.
  * **Token billing**: turn (`/api/threads/{id}/turn`) and "Do it for me" (`/api/threads/{id}/complete-action`) switched from flat 5/10 credits to `2 credits per 1,000 tokens` (input+output combined, min 1). Reserve-and-reconcile pattern: pre-deduct TURN_RESERVE_NORMAL=8 / TURN_RESERVE_ULTRA=24 / ASSIST_RESERVE=10, run LLM, refund `reserve − actual_cost`. Full refund on LLM failure (wrapped in try/except so a Mongo write error after a 502 logs CRITICAL but doesn't silently keep the user's credits).
  * **Stale-order auto-fail**: orders stuck in `created` longer than `ORDER_STALE_MINUTES=30` are automatically marked `failed` on any read of `/api/payments/status/{id}` or `/api/payments/history`. Prevents abandoned-checkout orders from showing "created" forever in purchase history.
  * **Webhook hardening**: `_verify_webhook_signature` now rejects signatures with timestamps older than 5 minutes (replay-attack protection).
  * **Token-saving**: Anthropic prompt caching (`cache_control: ephemeral`) added to SYSTEM blocks in `llm_turn` and `llm_complete_action` — repeated SYSTEM (the long persona prompt) reads at ~10% of normal cost from the 2nd turn onward. This is the single biggest cost reducer per active user.
  * Frontend BillingPage updated: 3-column pack grid, copy now reads "Pay for what you use — 2 credits per 1,000 tokens", failed orders show in red.
- OPEN ITEMS: Zoho webhook URL must be pointed at deployed domain in Zoho dashboard (user has webhook id 34562000000118002). Phase 3 future: felt-understood micro-prompt, account deletion, email re-engagement nudges (needs SMTP key).

## Design rules (non-negotiable)
1. Memory felt, never announced. 2. Surface delta, not recap. 3. One open question always visible. 4. No chat-log primary UI. 5. Silence named after 14d. 6. Re-engagement may be NULL.

## Pricing decision (founder)
$1 = 10 credits. Turn cost 5 credits (~$0.50/turn revenue vs ~$0.04 API cost). Signup grant 100 credits (20 turns) — adjustable in .env.
