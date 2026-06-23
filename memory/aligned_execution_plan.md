# Aligned Execution — Plan (actions a + b + c)

Spine themes: FOUNDER CLARITY · DECISION ENGINE · EXECUTION · MEMORY MANAGEMENT.
No new API keys/integrations needed — alignment scoring rides inside the existing brain LLM call.

## Phase 3.0 — Foundation: Decision Ledger + silent alignment (BUILD FIRST)
- New org-scoped `decisions` collection: every brain decision persisted
  {id, org_id|null, user_id, user_name, session_id, question, mode, found_in_docs,
   answer, recommendation, plan, citations, model, cost, tokens, created_at,
   committed_action:null, status:"open"|"done"|"dropped",
   strategic_alignment:{score,reason}  # FOUNDER-ONLY, stripped from member response}
- Silent alignment: brain /ask LLM call (already carries hidden North Star) also emits a
  private strategic_alignment field -> stored server-side, NEVER returned to members. Zero extra LLM cost, zero leakage.
- Execution hooks: committed_action + status on each decision.
- Endpoints: GET /api/brain/decisions (member's own history). Indexes + ensure_brain_startup().
- TEST: ask -> decision row exists; alignment stored; alignment ABSENT from member payload; member 403 nowhere needed (own history only).

## Phase c — Engine depth: connected hook-questioning + commit-then-sharpen
- Both engines: commit best recommendation under a stated assumption, then ONE connected question
  that would most change it + a confidence read. Never shallow "anything else?".
- Brain becomes lightly multi-turn (session_id) so it can dig one level before locking in.

## Phase 3 (action a) — Member Decision Room + Execution
- Multi-turn brain sessions (session_id), decision history UI, commit-an-action + one-tap done/not-yet (reuse coach mechanic).
- Member-side memory: their past decisions + a per-member understanding trail extended to the brain.

## Phase 4 (action b) — Founder's Private Cockpit (founder clarity)
- Founder-only: North Star header, alignment distribution, drift radar (low-alignment decisions),
  execution/follow-through rates per member, momentum toward the dream. Members get 403.

## Memory layers (woven through)
- Knowledge memory (org KB, exists) · Decision memory (new ledger) ·
  Person memory (per-member understanding trail, extend coach->brain) · Strategy memory (North Star, exists).

## Build order (hard parts first, each shippable): 3.0 -> c -> 3 -> 4.
