# SmartDecigen Deep Discussion Engine — PRD & Status

## Vision (founder's words)
The user walks away doing the one thing they already knew they needed to do but weren't doing. The ONE result no other AI gives: accountability — a kept promise to yourself. Goal = less distance between knowing and doing.

## Core Component: Goal-Anchored Thread
A thread holds the user's pursuit across weeks. Every turn refreshes "the easiest path forward" against updated reality. Every return after absence surfaces what changed about the user while they were gone.

## Architecture
- Stack: FastAPI + React + MongoDB. LLM: Claude Opus 4.8 (`claude-opus-4-8`) primary, Haiku 4.5 (`claude-haiku-4-5`) fallback. User's own ANTHROPIC_API_KEY in backend/.env.
- 4 LIVING FIELDS per thread (the primary UI): current_state_summary (3 lines), current_open_question (1 line, pinned above composer), current_easiest_path (1-2 lines), current_next_action (1 line, 24-48h, hero element).
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
- Phase 3 (pending, future): KPI dashboards from telemetry, felt-understood micro-prompt, Stripe credit top-ups, account deletion, email re-engagement nudges (needs SMTP/SendGrid key)

## Design rules (non-negotiable)
1. Memory felt, never announced. 2. Surface delta, not recap. 3. One open question always visible. 4. No chat-log primary UI. 5. Silence named after 14d. 6. Re-engagement may be NULL.

## Pricing decision (founder)
$1 = 10 credits. Turn cost 5 credits (~$0.50/turn revenue vs ~$0.04 API cost). Signup grant 100 credits (20 turns) — adjustable in .env.
