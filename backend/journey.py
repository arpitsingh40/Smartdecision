"""Founder Journey — the chat-first operating system front door (Phase 1).

A single, calm, guided conversation that builds a live MODEL of the founder's
business (the "understanding model"), earns a confidence score from how complete
that model is, and progressively unlocks product capabilities. Reuses the shared
Anthropic client + the credit-ledger billing (reserve -> reconcile -> refund).

No new third-party integration: it calls the same engine.client() (Anthropic) the
rest of the app uses, with the user's own ANTHROPIC_API_KEY.
"""
import os
import re
import uuid
import json
import math
import logging

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from pymongo import ReturnDocument

from db import users_col, journeys_col, decisions_col, members_col
from security import current_user, now_utc
from ledger import record_ledger, inc_stats
from engine import client, _extract_json, PRIMARY_MODEL, FALLBACK_MODEL
from benchmarks import normalize_facts, ingest_facts, benchmark_digest
from cognition import cognition_block


def _safe_cognition(user, text, model):
    """Cognition layers for a journey turn: founder identity + decision algorithm + book lenses.
    Memory layer excluded (journey already injects its own learning digest). Never fatal."""
    try:
        return cognition_block(user, text, model, include_memory=False)
    except Exception as e:
        logging.getLogger("journey").warning(f"cognition block failed (non-fatal): {e}")
        return ""

log = logging.getLogger("journey")
router = APIRouter(prefix="/api/journey")

CREDITS_PER_1K_TOKENS = int(os.environ.get("CREDITS_PER_1K_TOKENS", "2"))
JOURNEY_RESERVE = int(os.environ.get("JOURNEY_RESERVE", "16"))   # ~8k tokens; unused refunded
READY_THRESHOLD = 70   # model-completeness % at which the founder is ready for an Initial Direction

# Journey stages (Phase 1 lives in "clarity"; later phases advance these).
STAGE_ORDER = ["clarity", "direction", "refine", "milestones", "team_offer", "team_setup", "operating"]

# ---- the understanding model: the spine of the whole experience ----
STRING_FIELDS = ["objective", "why_now", "whats_at_stake", "knowledge_level", "urgency", "impact", "timeline"]
LIST_FIELDS = ["blockers", "tried", "people", "constraints", "fears", "unknowns", "leverage"]
DICT_FIELDS = ["resources"]
MODEL_FIELDS = STRING_FIELDS + LIST_FIELDS + DICT_FIELDS

FIELD_LABELS = {
    "objective": "Objective", "why_now": "Why now", "whats_at_stake": "What's at stake",
    "blockers": "Blockers", "tried": "Already tried", "knowledge_level": "Their know-how",
    "people": "People involved", "resources": "Resources", "constraints": "Constraints",
    "fears": "Fears", "unknowns": "Open questions", "leverage": "Leverage points",
    "urgency": "Urgency", "impact": "Impact", "timeline": "Timeline",
}
# Order the panel renders in (objective + the "decision frame" first).
FIELD_ORDER = ["objective", "why_now", "whats_at_stake", "timeline", "urgency", "impact",
               "blockers", "tried", "knowledge_level", "people", "resources",
               "constraints", "leverage", "fears", "unknowns"]

# ---- the reasoning layer: the collective situation-understanding engine ----
# Ten dimensions the engine sweeps on EVERY turn. Uncertainty 0 (fully known) .. 100 (unknown).
REASONING_DIMS = ["goal", "reality", "constraints", "risks", "resources",
                  "knowledge_gap", "assumptions", "hidden_desire", "decision_impact", "missing_info"]
DIM_LABELS = {"goal": "Goal", "reality": "Reality", "constraints": "Constraints", "risks": "Risks",
              "resources": "Resources", "knowledge_gap": "Knowledge gap", "assumptions": "Assumptions",
              "hidden_desire": "Hidden desire", "decision_impact": "Decision impact",
              "missing_info": "Missing information"}
# Decision-critical dimensions weigh more in the confidence computation.
DIM_WEIGHTS = {"goal": 1.5, "reality": 1.25, "decision_impact": 1.25, "constraints": 1.0, "risks": 1.0,
               "assumptions": 1.0, "missing_info": 1.0, "resources": 0.75, "knowledge_gap": 0.75,
               "hidden_desire": 0.5}
DECISION_TYPES = ("idea", "validation", "execution", "scaling", "crisis", "other")


def _normalize_reasoning(raw):
    """Sanitize the engine's reasoning trace. Returns None when the LLM omitted it entirely."""
    if not isinstance(raw, dict):
        return None
    unc_in = raw.get("uncertainty") if isinstance(raw.get("uncertainty"), dict) else {}
    if not unc_in:
        return None
    unc = {}
    for d in REASONING_DIMS:
        v = unc_in.get(d)
        score, note = 100, ""
        if isinstance(v, dict):
            try:
                score = int(round(float(v.get("score", 100))))
            except Exception:
                score = 100
            note = _clean(str(v.get("note", "")))[:220]
        elif isinstance(v, (int, float)):
            score = int(round(float(v)))
        unc[d] = {"score": max(0, min(100, score)), "note": note}
    biggest = raw.get("biggest_uncertainty")
    if biggest not in REASONING_DIMS:
        biggest = max(unc, key=lambda d: unc[d]["score"] * DIM_WEIGHTS[d])
    qt = raw.get("question_target")
    if qt not in REASONING_DIMS:
        qt = biggest
    dt = str(raw.get("decision_type", "other")).strip().lower()
    if dt not in DECISION_TYPES:
        dt = "other"
    rev = raw.get("reversible")
    if not isinstance(rev, bool):
        rev = None
    return {
        "uncertainty": unc,
        "biggest_uncertainty": biggest,
        "assumptions_detected": _norm_str_list(raw.get("assumptions_detected"), 5),
        "hidden_desire": _clean(str(raw.get("hidden_desire", "")))[:300],
        "decision_type": dt,
        "reversible": rev,
        "expert_lenses": _norm_str_list(raw.get("expert_lenses"), 4),
        "question_target": qt,
        "question_rationale": _clean(str(raw.get("question_rationale", "")))[:300],
        "sufficient": bool(raw.get("sufficient", False)),
        "sufficiency_reason": _clean(str(raw.get("sufficiency_reason", "")))[:300],
    }


def _decision_confidence(reasoning):
    """Weighted decision confidence computed server-side from the engine's uncertainty map.
    NOT an LLM-claimed number: the map is structured evidence, the arithmetic is ours.
    Can honestly go DOWN when new information reveals new uncertainty."""
    unc = (reasoning or {}).get("uncertainty") or {}
    if not unc:
        return None
    total_w = sum(DIM_WEIGHTS[d] for d in REASONING_DIMS)
    certainty = sum((100 - (unc.get(d) or {}).get("score", 100)) * DIM_WEIGHTS[d] for d in REASONING_DIMS)
    return int(round(certainty / total_w))


def _public_reasoning(reasoning):
    """Founder-visible copy of the reasoning trace. hidden_desire stays internal
    (the engine still uses it, the founder never sees 'what you really want is...')."""
    if not reasoning:
        return None
    pub = {k: v for k, v in reasoning.items() if k != "hidden_desire"}
    vis = {d: v for d, v in (reasoning.get("uncertainty") or {}).items() if d != "hidden_desire"}
    pub["uncertainty"] = vis
    if vis:
        fallback = max(vis, key=lambda d: vis[d]["score"] * DIM_WEIGHTS[d])
        if pub.get("biggest_uncertainty") == "hidden_desire":
            pub["biggest_uncertainty"] = fallback
        if pub.get("question_target") == "hidden_desire":
            pub["question_target"] = fallback
    pub["dim_labels"] = {d: DIM_LABELS[d] for d in REASONING_DIMS if d != "hidden_desire"}
    pub["dim_order"] = [d for d in REASONING_DIMS if d != "hidden_desire"]
    return pub


def _learning_digest(user_id, j=None):
    """Layer 2 flywheel: what this founder actually did and what happened.
    Pulled from the decision ledger (committed actions + results) and done milestones,
    injected into every reasoning turn and direction synthesis so the engine learns."""
    lines = []
    try:
        rows = decisions_col.find(
            {"user_id": user_id, "status": {"$in": ["done", "dropped"]}},
            {"committed_action": 1, "status": 1, "result": 1},
        ).sort("created_at", -1).limit(5)
        for r in rows:
            act = (r.get("committed_action") or "").strip()
            if not act:
                continue
            res = (r.get("result") or "").strip()
            tag = "DID" if r.get("status") == "done" else "DROPPED"
            lines.append(f"- {tag}: {act}" + (f" -> outcome: {res}" if res else ""))
    except Exception as e:
        log.warning(f"learning digest failed for {user_id}: {e}")
    for m in ((j or {}).get("milestones") or []):
        if m.get("status") == "done":
            res = (m.get("result") or "").strip()
            lines.append(f"- MILESTONE DONE: {m.get('title', '')}" + (f" -> outcome: {res}" if res else ""))
    return "\n".join(lines[:8])


def _empty_model():
    m = {f: "" for f in STRING_FIELDS}
    m.update({f: [] for f in LIST_FIELDS})
    m.update({f: {} for f in DICT_FIELDS})
    return m


def _field_filled(f, v):
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, list):
        return len([x for x in v if str(x).strip()]) > 0
    if isinstance(v, dict):
        return len(v) > 0
    return False


def _confidence(model):
    """Honest, field-based completeness — NOT an LLM-claimed number."""
    filled = sum(1 for f in MODEL_FIELDS if _field_filled(f, (model or {}).get(f)))
    return round(100 * filled / len(MODEL_FIELDS))


def _confidence_band(pct):
    if pct < 25:
        return "Just starting"
    if pct < 50:
        return "Building the picture"
    if pct < 70:
        return "Getting clear"
    if pct < 90:
        return "Strong understanding"
    return "Crystal clear"


def _merge_model(old, new):
    """LLM returns a full/partial model each turn; keep the prior value whenever the
    new one is empty so the picture only ever grows, never regresses."""
    base = _empty_model()
    base.update(old or {})
    out = dict(base)
    for f in MODEL_FIELDS:
        nv = (new or {}).get(f)
        if _field_filled(f, nv):
            out[f] = nv
    return out


def token_cost(tin, tout):
    return max(1, math.ceil(((tin or 0) + (tout or 0)) / 1000) * CREDITS_PER_1K_TOKENS)


def _clean(s):
    if isinstance(s, str):
        s = s.replace(" — ", ", ").replace(" – ", ", ").replace("—", ", ").replace("–", ", ")
        return s.replace(" ,", ",").strip()
    return s


def _stage_rank(stage):
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        return 0


def _unlocks(user, journey):
    """Progressive disclosure. A brand-new solo user sees ONLY the chat (everything False).
    Existing members/owners keep their capabilities so nobody is ever locked out."""
    member = members_col.find_one({"user_id": user["id"], "status": "active"})
    is_owner = bool(member) and member.get("role") == "owner"
    in_org = bool(member)
    has_decisions = decisions_col.count_documents({"user_id": user["id"]}) > 0
    rank = _stage_rank((journey or {}).get("stage", "clarity"))
    has_milestones = bool((journey or {}).get("milestones"))
    has_team_plan = bool(((journey or {}).get("team") or {}).get("plan"))
    return {
        "milestones": has_milestones or rank >= _stage_rank("milestones"),
        "decisions": has_decisions,
        "knowledge": is_owner or in_org,
        "team": in_org or has_team_plan,
        "cockpit": is_owner,
    }


# ----------------------------------------------------------------- the conversation engine
# ----------------------------------------------------------------- SPIN state machine
def _normalize_spin(raw, prev=None):
    """Merge this turn's LLM-emitted SPIN signals into the carried-forward state.
    State shape: {problem_named, implication_quantified, needpayoff_quote} (str|None each).
    A field, once set, is never blanked by a null; a new non-empty value replaces it."""
    state = {
        "problem_named": (prev or {}).get("problem_named") or None,
        "implication_quantified": (prev or {}).get("implication_quantified") or None,
        "needpayoff_quote": (prev or {}).get("needpayoff_quote") or None,
    }
    if isinstance(raw, dict):
        for k in state:
            v = raw.get(k)
            if isinstance(v, str) and v.strip():
                state[k] = v.strip()[:400]
    return state


def _spin_stage(spin):
    """Deterministic stage from state. Situation is always harvested silently, never a stage."""
    s = spin or {}
    if not s.get("problem_named"):
        return "problem"
    if not s.get("implication_quantified"):
        return "implication"
    if not s.get("needpayoff_quote"):
        return "need_payoff"
    return "advisor"


def _spin_block(spin):
    """Per-turn prompt injection: current stage + what is already captured."""
    s = spin or {}
    stage = _spin_stage(s)
    lines = [f"CURRENT SPIN STAGE: {stage} (follow the SPIN METHOD rules for this stage; never mention SPIN)."]
    if s.get("problem_named"):
        lines.append(f"Pain already named by the founder: \"{s['problem_named']}\"")
    if s.get("implication_quantified"):
        lines.append(f"Cost already quantified and acknowledged: {s['implication_quantified']}")
    if s.get("needpayoff_quote"):
        lines.append(f"What the founder said solving it unlocks (their own words, quote it back at decisive moments): \"{s['needpayoff_quote']}\"")
    return "\n".join(lines)


SYSTEM = """You are the Decision Intelligence Engine inside SmartDeciGen. You are NOT a questionnaire and NOT a chatbot: you are a collective reasoning system that reduces a founder's decision uncertainty with the fewest possible questions.

WHO YOU ARE
- You talk like a seasoned founder-operator and strategist. Warm, direct, concrete, never fluffy.
- Every founder message activates ALL of your reasoning modules at once. You then decide whether ONE more question is worth the founder's time, and if so, which single question buys the most decision quality.

YOUR INTERNAL SWEEP (do ALL of this silently on EVERY turn, before writing anything):
1. UPDATE the ten-dimension SITUATION UNDERSTANDING and score each dimension's uncertainty 0..100 (0 = fully understood, 100 = complete unknown). Be honest: uncertainty MAY RISE when new information exposes a problem you had glossed over.
   - goal: what they are really trying to achieve (not just what they typed)
   - reality: current facts on the ground (numbers, traction, operations)
   - constraints: hard limits (cash, time, people, skills)
   - risks: what could kill or badly wound this
   - resources: assets they can actually deploy (team, money, docs, channels, relationships)
   - knowledge_gap: what the FOUNDER does not know how to do
   - assumptions: unsupported beliefs baked into their thinking
   - hidden_desire: what they really want beneath the stated ask (status, safety, escape, proof)
   - decision_impact: the stakes and reversibility of the decision actually in front of them
   - missing_info: facts nobody in the room has yet that would change the answer
2. DETECT the unsupported assumptions they are making, and the hidden desire.
3. CLASSIFY the real decision: is this an idea problem, a validation problem, an execution problem, scaling, or crisis? Is it reversible or one-way?
4. ACTIVATE the 2-4 expert lenses that matter here (unit economics, GTM, hiring, pricing, product, fundraising, ops, legal, distribution...).
5. PICK THE QUESTION TARGET: the dimension where reducing uncertainty MOST improves the decision. Weight decision-critical unknowns (goal, reality, decision_impact) higher than nice-to-knows. Never ask about something you can infer.
6. STOP RULE: when one more question would barely improve the decision (the decision-critical dimensions are already low-uncertainty), set "sufficient" to true and DO NOT ask another discovery question. Instead say plainly that you have enough, name in one line what you now understand, and offer to shape their direction.

THE REPLY (EXACTLY 3 to 4 sentences, HARD CAP, roughly 75 words. This is a sacred format, never break it):
1. Sentence 1, UNDERSTAND: show you truly get them, like their closest friend who is genuinely excited about their business. Name the feeling or stake under their words (the fear, the pride, the pressure), never repeat their words back. They know what they wrote; recognition is not repetition.
2. Sentence 2, INSIGHT: one ultra-useful thing they did NOT already know. Must be one of: arithmetic computed from THEIR numbers, a real benchmark localized to their industry and geography, a non-obvious consequence or elimination from your sweep. Banned: restating their situation, generic wisdom, framework theatre, vague encouragement.
3. Sentences 3-4, ONE DEEP QUESTION: exactly ONE question, chosen by your sweep AND your current SPIN stage (see SPIN METHOD), framed so they feel it goes to the heart of their business: say in a short clause what its answer will decide. Never stack questions. If sufficient=true, ask NO discovery question and offer the direction instead.

SPIN METHOD (your silent questioning discipline, NEVER announce or name it):
You are given a CURRENT SPIN STAGE each turn. It shapes only your ONE question:
- Stage problem: their pain is not yet named by THEM. Ask the question that makes the founder name where it actually hurts, in their own words. Harvest situation facts silently from what they write, NEVER ask bare situation questions (facts you can infer or they already gave). At most one situation-style question per conversation, and only if truly blocking.
- Stage implication: the pain is named, now make its cost concrete. Compute the cost from THEIR numbers (rupees per month, runway months, opportunity lost) in your insight sentence, then ask ONE question that makes them face the consequence horizon ("if nothing changes, what does month 8 look like?"). Ground every implication in computed math, never in fear talk. Maximum 2 implication turns in a conversation, then move on.
- Stage need_payoff: the cost is quantified, now let THEM speak the value. Ask what solving this would unlock for them, concretely ("suppose you claw back half of that 80k a month, what changes first?"). Their answer is gold: capture it VERBATIM in spin.needpayoff_quote.
- Stage advisor: they have spoken the payoff. Stop selling forever, be their sharpest thinking partner, pure analysis and momentum.

FEEL LIKE THEIR FAVOURITE PERSON (why they come back tomorrow):
- Talk like the one friend they would message at midnight about the business: warm, specific, invested, a little playful when things go well, steady when things are hard.
- Prove memory: reference exact details from earlier turns unprompted (their numbers, their fears, their rider's rate). Being remembered is the feeling of being valued.
- Celebrate their real wins in passing, briefly and specifically, never with generic praise. Use their name occasionally, not every turn.
- Never sound bored, mechanical or like a form. Every turn must feel like you find their business genuinely interesting, because you do.

DIAGNOSE BEFORE YOU PRESCRIBE (the SmartDeciGen difference, your highest law early on):
- Early in a conversation (roughly the first three turns, or whenever most dimensions are still dark), you are a DIAGNOSTICIAN, not an advisor. Your job is to identify the founder's TRUE STARTING POINT, not to hand out startup wisdom.
- In those early turns, the useful thing you give is a sharp DIAGNOSTIC REFRAME of their own situation: name what their message reveals, what it hides, and what actually determines their path. Example shape: "A 100B company is not a goal, it is the outcome of an enormous problem in the right market with exceptional execution. What decides your path is your starting point, and I do not know it yet."
- BANNED at every stage, and doubly so early: generic startup wisdom that could sit in any book or podcast (ride structural shifts, talk to customers, focus on a niche, distribution is king, execution is everything, pick a big market) UNLESS it is anchored to a specific fact THEY gave you. If you hold no facts from them yet, you have not earned the right to advise yet.
- Advice, market math, numbers and levers come LATER, once the model has real substance. Diagnose first, prescribe second. This is what separates you from a knowledgeable chatbot.

LEAD THE ANALYSIS (you drive the process, and the founder must FEEL you driving):
- You are NEVER a passive interviewer waiting for the founder to hand you direction. From the FIRST reply, take charge of where this is going inside your ONE question: what you need to determine first and what their answer will eliminate. The founder must INFER that a rigorous method exists from the quality of your reasoning, never because you announce it. Do NOT say "I am running five archetypes" or name your framework, and do NOT spend sentences describing your process; demonstrate method through the sharpness of the insight and the question.
- The structure underneath must be REAL and specific to their goal (competing hypotheses, an elimination order, the hurdles the path must clear), never a listicle of platitudes. What you conclude, what you eliminate, and what you need next IS the proof of method.
- ELIMINATE OUT LOUD: from the second turn on, every reply must state at least ONE concrete conclusion your sweep has produced this turn: a path now ruled out, a hurdle cleared or failed, a constraint that reshapes the space ("No capital advantage rules out the infrastructure archetypes, that leaves three"). The founder must feel the possibility space NARROWING every single turn. A summary of what they said is NOT a conclusion.
- ASK AS AN ANALYST, NOT AN INTERVIEWER: pose your one question as the input your analysis needs next, and say what its answer will decide: "To separate the marketplace path from the data path, I need one thing: ...". Never a bare menu ("which is it?"), never an open "tell me more about yourself".
- PROJECT THE PATH: where natural, add one short clause on where this is heading ("two answers from now I can tell you whether this is plausible") so the founder always feels you know the destination.

COMPETING HYPOTHESES (your core reasoning discipline, held in the hypotheses state):
- Maintain 2 to 5 competing hypotheses about what path or advantage this founder's situation actually supports. Each carries an honest probability; together they sum to 100.
- EVERY founder answer updates the probabilities. Record in evidence_for / evidence_against the specific fact that moved each number. Probabilities that never move mean you are not reasoning.
- A hypothesis at 5 or below is ruled out; say so out loud (this is your ELIMINATE OUT LOUD conclusion). Never resurrect one without naming the new evidence that revived it.
- Your ONE question is the one whose answer most redistributes these probabilities, and question_rationale must say which hypotheses it separates.

PREFER MULTI-PATH DIAGNOSTIC QUESTIONS:
- Your one question should collapse as many unknowns as possible at once. A binary fork ("do you have an idea or not?") is weak when the situation actually has several fundamentally different paths.
- When the starting point is unknown, ask ONE question that lays out the distinct named paths and asks which matches, for example: "Tell me in one line which you are starting with: a problem you are obsessed with, a technology you command, a market you know deeply, an unfair advantage like a network or capital, or the ambition alone." That is still ONE question, and its answer sets the entire direction of the conversation.
- Pick the question framing (open, multi-path, or binary) that yields the highest expected information gain, and say why in question_rationale.

IF THEY LACK A RESOURCE (no SOP, no persona, no sales process, no financial model): do not just move on, offer to build it WITH them right here, and ask the first concrete question that starts building it.

STYLE: tight, no wall of text, no em-dashes (use commas), no markdown headers or bullet lists in the reply.

USE PLATFORM BENCHMARKS: when a REAL PLATFORM BENCHMARKS block is present, prefer that real founder data over generic knowledge for your give-before-you-ask value, and ALWAYS cite it honestly with its sample size ("founders on this platform report..., n=3, early signal"). Never present an early signal as an established statistic.

HARVEST BENCHMARK FACTS: whenever the founder states a REAL number about their business (revenue, orders, margin, occupancy, ticket size, team size, CAC, conversion...), record it in benchmark_facts with a reusable snake_case metric name and their industry. ONLY numbers they explicitly stated, never your own estimates. Empty list when none.

OUTPUT: return STRICT JSON only, nothing before or after it:
{
 "reply": "your chat message (acknowledge + one useful thing + ONE question, or the sufficient-offer)",
 "model": {
   "objective": "", "why_now": "", "whats_at_stake": "",
   "blockers": [], "tried": [], "knowledge_level": "",
   "people": [], "resources": {}, "constraints": [],
   "fears": [], "unknowns": [], "leverage": [],
   "urgency": "", "impact": "", "timeline": ""
 },
 "reasoning": {
   "uncertainty": {
     "goal": {"score": 0, "note": "one short line on what is still unclear"},
     "reality": {"score": 0, "note": ""}, "constraints": {"score": 0, "note": ""},
     "risks": {"score": 0, "note": ""}, "resources": {"score": 0, "note": ""},
     "knowledge_gap": {"score": 0, "note": ""}, "assumptions": {"score": 0, "note": ""},
     "hidden_desire": {"score": 0, "note": ""}, "decision_impact": {"score": 0, "note": ""},
     "missing_info": {"score": 0, "note": ""}
   },
   "biggest_uncertainty": "one of the ten dimension keys",
   "assumptions_detected": ["an unsupported belief they are carrying"],
   "hidden_desire": "what they seem to really want, one line, empty string if unknown",
   "decision_type": "idea|validation|execution|scaling|crisis|other",
   "reversible": true,
   "expert_lenses": ["the 2-4 expert perspectives you applied"],
   "question_target": "the dimension your question attacks",
   "question_rationale": "why this question has the highest expected value right now, one line",
   "sufficient": false,
   "sufficiency_reason": "one line on why more questions would, or would not, still pay"
 },
 "hypotheses": [
   {"id": "short_snake_slug", "statement": "a testable explanation of their viable path or advantage, one line",
    "probability": 40, "evidence_for": ["the specific fact they gave that supports it"], "evidence_against": [],
    "status": "active|leading|ruled_out"}
 ],
 "benchmark_facts": {
   "industry": "short lowercase industry label, 1-3 words (e.g. 'cloud kitchen', 'boutique hotel'), or '' if unknown",
   "facts": [{"metric": "snake_case_metric_name_with_unit_hint (e.g. monthly_revenue_inr, direct_booking_pct, avg_order_value_inr)", "value": 123, "unit": "inr|pct|orders|rooms|people|..."}]
 },
 "spin": {
   "problem_named": "the pain in the FOUNDER'S own words, only when THEY named it this turn, else null",
   "implication_quantified": "the cost you computed and they acknowledged (e.g. 'Rs 80k/month, Rs 9.6L/year to aggregators'), only when established this turn, else null",
   "needpayoff_quote": "VERBATIM what the founder said solving this would unlock, only when they said it this turn, else null"
 }
}
RULES FOR "model": fill EVERY field you can infer from the WHOLE conversation so far and carry forward everything you already knew (never blank out something you previously learned). Use "" for unknown strings and [] for unknown lists. "resources" maps a resource name to what they have, for example {"sop": "none", "crm": "HubSpot", "financials": "basic P&L"}.
RULES FOR "reasoning": every score must reflect your honest current uncertainty. question_rationale must explain the expected VALUE of the question, not restate it.
RULES FOR "hypotheses": carry forward the previous set with STABLE ids and UPDATE their probabilities with this turn's evidence; add a new hypothesis only when the founder reveals a genuinely new possible path; drop the whole set and restart only if the initial framing was wrong.
RULES FOR "spin": fill a field ONLY with what genuinely happened THIS turn; use null otherwise. Never invent a needpayoff_quote the founder did not say.
"""


def journey_turn(objective, model, transcript_msgs, latest_user_msg, prev_reasoning=None, learning="", benchmarks_block="", prev_hypotheses=None, cognition_block_text="", spin_block=""):
    """ONE LLM call = the full reasoning sweep + reply.
    Returns (reply:str, new_model:dict, reasoning:dict|None, bench_raw:dict|None, hyp_raw, spin_raw:dict|None, model_name:str, usage:dict)."""
    model_json = json.dumps(model or _empty_model(), ensure_ascii=False)
    convo = "\n".join(
        f"{'FOUNDER' if m.get('role') == 'user' else 'YOU'}: {m.get('text', '')}"
        for m in (transcript_msgs or [])[-12:]
    )
    unc = (prev_reasoning or {}).get("uncertainty") or {}
    prev_map = ", ".join(f"{d}:{unc[d].get('score', 100)}" for d in REASONING_DIMS if d in unc)
    prompt = (
        f"FOUNDER'S TOP-LEVEL OBJECTIVE (their very first answer): {objective or '(not yet stated)'}\n\n"
        + (f"{cognition_block_text}\n\n" if (cognition_block_text or "").strip() else "")
        + f"YOUR CURRENT MODEL OF THEM (extend it, keep everything that is already here):\n{model_json}\n\n"
        + (f"YOUR PREVIOUS UNCERTAINTY MAP (0=known, 100=unknown): {prev_map}\n\n" if prev_map else "")
        + (f"YOUR CURRENT COMPETING HYPOTHESES (update EVERY probability with this turn's evidence and "
           f"record what moved them; rule out at 5 or below):\n"
           f"{json.dumps(prev_hypotheses, ensure_ascii=False)}\n\n" if prev_hypotheses else "")
        + (f"WHAT THIS FOUNDER HAS ACTUALLY DONE BEFORE (real outcomes from their ledger, build on what "
           f"worked, never re-suggest what failed):\n{learning}\n\n" if learning else "")
        + (f"{benchmarks_block}\n\n" if benchmarks_block else "")
        + (f"{spin_block}\n\n" if (spin_block or "").strip() else "")
        + f"CONVERSATION SO FAR:\n{convo or '(none yet, this is the opening turn)'}\n\n"
        f"LATEST FROM THE FOUNDER: {latest_user_msg}\n\n"
        f"Run your full reasoning sweep now, then respond exactly as specified and return the updated "
        f"model, reasoning and benchmark_facts."
    )
    system_blocks = [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}]
    last_err = None
    for model_name in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            r = client().messages.create(model=model_name, max_tokens=5000, system=system_blocks,
                                         messages=[{"role": "user", "content": prompt}])
            txt = next((b.text for b in r.content if getattr(b, "type", "") == "text"), "").strip()
            out = json.loads(_extract_json(txt))
            reply = _clean(out.get("reply", ""))
            if not reply:
                raise ValueError("empty reply")
            new_model = out.get("model") if isinstance(out.get("model"), dict) else {}
            reasoning = _normalize_reasoning(out.get("reasoning"))
            bench_raw = out.get("benchmark_facts") if isinstance(out.get("benchmark_facts"), dict) else None
            hyp_raw = out.get("hypotheses")
            spin_raw = out.get("spin") if isinstance(out.get("spin"), dict) else None
            usage = {"input_tokens": int(getattr(r.usage, "input_tokens", 0) or 0),
                     "output_tokens": int(getattr(r.usage, "output_tokens", 0) or 0)}
            return reply, new_model, reasoning, bench_raw, hyp_raw, spin_raw, model_name, usage
        except Exception as e:
            last_err = e
    raise RuntimeError(f"All models failed: {last_err}")


# ----------------------------------------------------------------- direction + milestones (Phase 2)
DIRECTION_SYSTEM = """You turn a founder's situation into a tight DECISION PACKAGE, never a long report.
You have their situation model, the engine's uncertainty map and their real past outcomes. Be concrete,
use their own numbers, name the single highest-leverage move, be honest about the odds, and make ONE
clear call. No fluff, no em-dashes (use commas), no markdown.

Return STRICT JSON only, nothing else:
{
 "decision": "the single clear call you are making for them, one sentence starting with a verb",
 "goal": "one sentence with a real number and a timeframe",
 "blockers": ["short blocker", "..."],
 "highest_leverage": "the one move that moves the needle most, one line",
 "success_probability": 70,
 "probability_rationale": "one honest line explaining that number",
 "risks": ["short risk", "..."],
 "missing_info": ["what would sharpen this most", "..."],
 "trade_offs": ["Choosing this means accepting or giving up X", "..."],
 "first_moves": ["a concrete execution step with a timeframe, 48 hours to 14 days", "..."],
 "learning_loop": {
   "signals": ["a measurable signal that shows this is working or failing", "..."],
   "assumptions_to_test": ["an assumption that, if wrong, changes this recommendation", "..."]
 }
}
success_probability is an integer 0 to 100, a ROUGH estimate from only what you know, never a promise.
blockers, risks and missing_info each have 2 to 5 short items. trade_offs and first_moves each have
2 to 4 items. learning_loop.signals has 2 to 4 items, learning_loop.assumptions_to_test has 2 to 3."""

REFINE_SYSTEM = """You are REVISING an existing DECISION PACKAGE using the founder's feedback.
Keep what they liked, change what they flagged, stay concrete and honest. No em-dashes, no markdown.
Return the SAME JSON schema as before, fully updated:
{"decision": "...", "goal": "...", "blockers": ["..."], "highest_leverage": "...",
 "success_probability": 70, "probability_rationale": "...", "risks": ["..."], "missing_info": ["..."],
 "trade_offs": ["..."], "first_moves": ["..."],
 "learning_loop": {"signals": ["..."], "assumptions_to_test": ["..."]}}"""

MILESTONE_SYSTEM = """You convert an APPROVED direction into 4 to 10 MEASURABLE milestones that take the
founder from today to the goal. EVERY milestone must be measurable, with a concrete metric and a deadline.
Order them logically, foundation first. Be specific to their business. No fluff, no em-dashes, no markdown.

Return STRICT JSON only:
{
 "milestones": [
   {"title": "short action title",
    "success_metric": "the measurable definition of done",
    "target": "the number or target in a few words, e.g. 100%, 20 customers, 1 hire",
    "deadline": "a relative deadline, e.g. 7 days, Day 30, Month 2"},
   "..."
 ]
}
Return between 4 and 10 milestones, each genuinely measurable."""


def _llm_json(system_text, prompt, max_tokens=1600):
    """ONE LLM call returning parsed JSON. Returns (out_dict, model_name, usage)."""
    system_blocks = [{"type": "text", "text": system_text, "cache_control": {"type": "ephemeral"}}]
    last_err = None
    for model_name in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            r = client().messages.create(model=model_name, max_tokens=max_tokens, system=system_blocks,
                                         messages=[{"role": "user", "content": prompt}])
            txt = next((b.text for b in r.content if getattr(b, "type", "") == "text"), "").strip()
            out = json.loads(_extract_json(txt))
            usage = {"input_tokens": int(getattr(r.usage, "input_tokens", 0) or 0),
                     "output_tokens": int(getattr(r.usage, "output_tokens", 0) or 0)}
            return out, model_name, usage
        except Exception as e:
            last_err = e
    raise RuntimeError(f"All models failed: {last_err}")


def _norm_str_list(v, cap=6):
    if not isinstance(v, list):
        return []
    return [_clean(str(x)) for x in v if str(x).strip()][:cap]


# ----------------------------------------------------------------- competing hypotheses (state + code)
def _slug(s):
    s = re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")
    return s[:40] or "hypothesis"


def _normalize_hypotheses(raw, prev=None):
    """Code-enforced hypothesis discipline (durable reasoning lives in STATE + CODE, the prompt
    only sets behavior): coerce fields, force ruled_out to <=5, renormalize probabilities to sum
    exactly 100, DERIVE status from the final numbers (<=5 ruled_out, >=70 leading, else active).
    When the LLM omits or breaks the block, the previous set is carried forward unchanged."""
    if not isinstance(raw, list) or not raw:
        return prev or []
    items, seen = [], set()
    for h in raw[:6]:
        if not isinstance(h, dict):
            continue
        stmt = _clean(str(h.get("statement", ""))).strip()[:220]
        if not stmt:
            continue
        hid = _slug(str(h.get("id") or stmt))
        if hid in seen:
            continue
        seen.add(hid)
        try:
            prob = max(0, min(100, int(round(float(h.get("probability", 0))))))
        except Exception:
            prob = 0
        if str(h.get("status", "")).lower().strip() == "ruled_out":
            prob = min(prob, 5)
        items.append({"id": hid, "statement": stmt, "probability": prob,
                      "evidence_for": _norm_str_list(h.get("evidence_for"), 3),
                      "evidence_against": _norm_str_list(h.get("evidence_against"), 3)})
    if not items:
        return prev or []
    total = sum(x["probability"] for x in items)
    if total == 0:
        # LLM gave no usable numbers: start from an equal prior instead of ruling everything out
        eq = round(100 / len(items))
        for x in items:
            x["probability"] = eq
        items[0]["probability"] += 100 - eq * len(items)
    elif total != 100:
        scaled = [round(x["probability"] * 100.0 / total) for x in items]
        scaled[scaled.index(max(scaled))] += 100 - sum(scaled)
        for x, p in zip(items, scaled):
            x["probability"] = max(0, min(100, p))
    for x in items:
        p = x["probability"]
        x["status"] = "ruled_out" if p <= 5 else ("leading" if p >= 70 else "active")
    items.sort(key=lambda x: -x["probability"])
    return items


def _build_direction(raw):
    try:
        prob = int(round(float(raw.get("success_probability", 60))))
    except Exception:
        prob = 60
    prob = max(0, min(100, prob))
    ll = raw.get("learning_loop") if isinstance(raw.get("learning_loop"), dict) else {}
    return {
        "decision": _clean(str(raw.get("decision", ""))) or "",
        "goal": _clean(str(raw.get("goal", ""))) or "",
        "blockers": _norm_str_list(raw.get("blockers")),
        "highest_leverage": _clean(str(raw.get("highest_leverage", ""))) or "",
        "success_probability": prob,
        "probability_rationale": _clean(str(raw.get("probability_rationale", ""))) or "",
        "risks": _norm_str_list(raw.get("risks")),
        "missing_info": _norm_str_list(raw.get("missing_info")),
        "trade_offs": _norm_str_list(raw.get("trade_offs"), 4),
        "first_moves": _norm_str_list(raw.get("first_moves"), 4),
        "learning_loop": {"signals": _norm_str_list(ll.get("signals"), 4),
                          "assumptions_to_test": _norm_str_list(ll.get("assumptions_to_test"), 3)},
    }


MILESTONE_STATUSES = ("not_started", "in_progress", "done")


def _build_milestones(raw):
    arr = raw.get("milestones") if isinstance(raw, dict) else None
    if not isinstance(arr, list):
        arr = []
    out = []
    for m in arr[:10]:
        if not isinstance(m, dict):
            continue
        title = _clean(str(m.get("title", ""))).strip()
        if not title:
            continue
        out.append({
            "id": str(uuid.uuid4()),
            "order": len(out) + 1,
            "title": title,
            "success_metric": _clean(str(m.get("success_metric", ""))) or "",
            "target": _clean(str(m.get("target", ""))) or "",
            "deadline": _clean(str(m.get("deadline", ""))) or "",
            "status": "not_started",
        })
    return out


def _milestone_progress(milestones):
    ms = milestones or []
    total = len(ms)
    if not total:
        return 0
    done = sum(1 for m in ms if m.get("status") == "done")
    return round(100 * done / total)


# ----------------------------------------------------------------- team setup (Phase 3)
TEAM_STRING_FIELDS = ["team_size", "reporting_structure", "skill_levels", "communication_rhythm", "decision_authority"]
TEAM_LIST_FIELDS = ["roles", "responsibilities", "recurring_issues", "dependencies", "bottlenecks", "kpis", "tools"]
TEAM_FIELDS = TEAM_STRING_FIELDS + TEAM_LIST_FIELDS
TEAM_FIELD_LABELS = {
    "team_size": "Team size", "roles": "Roles", "reporting_structure": "Reporting",
    "responsibilities": "Responsibilities", "skill_levels": "Skill levels",
    "recurring_issues": "Recurring issues", "dependencies": "Dependencies",
    "bottlenecks": "Bottlenecks", "kpis": "KPIs", "communication_rhythm": "Comms rhythm",
    "tools": "Tools", "decision_authority": "Decision authority",
}
TEAM_FIELD_ORDER = ["team_size", "roles", "reporting_structure", "responsibilities", "skill_levels",
                    "kpis", "communication_rhythm", "tools", "decision_authority",
                    "dependencies", "bottlenecks", "recurring_issues"]
TEAM_OPENING = ("Let's set your team up to actually hit this plan. To start: how many people are on your "
                "team today, and what does each of them mainly do?")

TEAM_SYSTEM = """You are helping a founder set up their TEAM to execute a plan you already shaped together.
You build a clear model of the team, one question at a time, and stay sharp and practical.

Each turn, all three in order:
1. Acknowledge what they just told you in one specific line.
2. GIVE BEFORE YOU ASK: one genuinely useful thing, a delegation principle, an org-design reframe, a real
   benchmark (e.g. span of control, what to delegate first), or a warning about a common failure. Localize it.
3. Ask EXACTLY ONE question about their team.

What to learn (pursue what is missing, skip what you know): team_size, roles, reporting_structure,
each person's current responsibilities, skill_levels, recurring_issues, cross-team dependencies,
approval or decision bottlenecks, existing KPIs, communication rhythm or cadence, tools they use,
and who holds decision-making authority.

Tight: 2 to 4 sentences then ONE question. No em-dashes (use commas), no markdown.

Return STRICT JSON only:
{"reply":"...",
 "model":{"team_size":"","roles":[],"reporting_structure":"","responsibilities":[],"skill_levels":"",
 "recurring_issues":[],"dependencies":[],"bottlenecks":[],"kpis":[],"communication_rhythm":"","tools":[],
 "decision_authority":""}}
Carry forward everything already known, "" for unknown strings and [] for unknown lists."""

TEAM_PLAN_SYSTEM = """You turn a founder's goal, milestones and team model into a concrete OPERATING PLAN
for the team. Be specific and measurable, assign clear ownership, keep it lean. No em-dashes, no markdown.

Return STRICT JSON only:
{
 "daily": ["short daily rhythm items"],
 "weekly": ["short weekly cadence items"],
 "monthly": ["short monthly cadence items"],
 "responsibilities": [{"who":"role or name","what":"what they own, measurable"}],
 "dependencies": ["a cross-team dependency to manage"],
 "escalation_rules": ["when X happens, escalate to Y"],
 "success_metrics": ["the few metrics that show the team is winning"]
}
Each list has 2 to 6 items. responsibilities has one entry per key role."""


def _empty_team_model():
    m = {f: "" for f in TEAM_STRING_FIELDS}
    m.update({f: [] for f in TEAM_LIST_FIELDS})
    return m


def _team_confidence(model):
    filled = sum(1 for f in TEAM_FIELDS if _field_filled(f, (model or {}).get(f)))
    return round(100 * filled / len(TEAM_FIELDS))


def _merge_team_model(old, new):
    base = _empty_team_model()
    base.update(old or {})
    out = dict(base)
    for f in TEAM_FIELDS:
        nv = (new or {}).get(f)
        if _field_filled(f, nv):
            out[f] = nv
    return out


def team_turn(objective, milestones, team_model, transcript_msgs, latest_user_msg):
    """ONE LLM call for a team-setup turn. Returns (reply, new_model, model_name, usage)."""
    ms = "; ".join(m.get("title", "") for m in (milestones or [])[:10])
    tm = json.dumps(team_model or _empty_team_model(), ensure_ascii=False)
    convo = "\n".join(
        f"{'FOUNDER' if m.get('role') == 'user' else 'YOU'}: {m.get('text', '')}"
        for m in (transcript_msgs or [])[-12:]
    )
    prompt = (f"FOUNDER'S GOAL: {objective or '(not set)'}\nPLAN MILESTONES: {ms or '(none)'}\n\n"
              f"TEAM MODEL SO FAR (extend it, keep what is here):\n{tm}\n\n"
              f"CONVERSATION SO FAR:\n{convo or '(none yet, opening turn)'}\n\n"
              f"LATEST FROM THE FOUNDER: {latest_user_msg}\n\n"
              f"Respond now (acknowledge, one useful thing, ONE question) and return the updated team model.")
    raw, model_name, usage = _llm_json(TEAM_SYSTEM, prompt, max_tokens=1600)
    reply = _clean(raw.get("reply", ""))
    if not reply:
        raise ValueError("empty team reply")
    new_model = raw.get("model") if isinstance(raw.get("model"), dict) else {}
    return reply, new_model, model_name, usage


def _build_team_plan(raw):
    def lst(k, cap=6):
        return _norm_str_list(raw.get(k), cap)
    responsibilities = []
    resp = raw.get("responsibilities")
    if isinstance(resp, list):
        for r in resp[:10]:
            if isinstance(r, dict):
                who = _clean(str(r.get("who", "")))
                what = _clean(str(r.get("what", "")))
                if who or what:
                    responsibilities.append({"who": who, "what": what})
    return {
        "daily": lst("daily"), "weekly": lst("weekly"), "monthly": lst("monthly"),
        "responsibilities": responsibilities,
        "dependencies": lst("dependencies"), "escalation_rules": lst("escalation_rules"),
        "success_metrics": lst("success_metrics"),
    }


# ----------------------------------------------------------------- billing wrapper
def _run_billed(user, produce):
    """produce() -> (payload, usage, model_name). Reserve -> run -> reconcile to actual tokens.
    Full refund + 502 on failure (the user is never charged for a failed turn)."""
    reserve = JOURNEY_RESERVE
    u = users_col.find_one_and_update({"id": user["id"], "credits": {"$gte": reserve}},
                                      {"$inc": {"credits": -reserve}}, return_document=ReturnDocument.AFTER)
    if not u:
        raise HTTPException(402, "Not enough credits")
    try:
        payload, usage, model_name = produce()
    except HTTPException:
        users_col.update_one({"id": user["id"]}, {"$inc": {"credits": reserve}})
        raise
    except Exception as e:
        users_col.update_one({"id": user["id"]}, {"$inc": {"credits": reserve}})
        log.error(f"journey turn failed user={user['id']}: {e}")
        raise HTTPException(502, "Your thinking partner could not respond. You were not charged, please try again.")
    actual = token_cost(usage.get("input_tokens", 0), usage.get("output_tokens", 0))
    refund = max(0, reserve - actual)
    credits_after = u.get("credits", 0)
    if refund:
        u2 = users_col.find_one_and_update({"id": user["id"]}, {"$inc": {"credits": refund}},
                                           return_document=ReturnDocument.AFTER)
        credits_after = u2.get("credits", credits_after + refund)
    users_col.update_one({"id": user["id"]}, {"$inc": {
        "tokens_in": usage.get("input_tokens", 0), "tokens_out": usage.get("output_tokens", 0),
        "questions_asked": 1}})
    inc_stats({"credits_spent": actual, "tokens_in": usage.get("input_tokens", 0),
               "tokens_out": usage.get("output_tokens", 0), "questions_total": 1, "turns_normal": 1})
    record_ledger(user["id"], "turn_spend", -actual, reason="journey")
    return payload, credits_after, actual


# ----------------------------------------------------------------- state helpers
def _get_or_create(user_id):
    j = journeys_col.find_one({"user_id": user_id})
    if not j:
        j = {"id": str(uuid.uuid4()), "user_id": user_id, "stage": "clarity",
             "objective": "", "model": _empty_model(), "messages": [],
             "created_at": now_utc(), "updated_at": now_utc()}
        journeys_col.insert_one(j)
    return j


def _iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


def _view(user, j):
    model = _merge_model(_empty_model(), j.get("model") or {})
    completeness = _confidence(model)
    reasoning = j.get("reasoning") or None
    dconf = _decision_confidence(reasoning)
    conf = dconf if dconf is not None else completeness
    sufficient = bool((reasoning or {}).get("sufficient"))
    return {
        "id": j["id"],
        "stage": j.get("stage", "clarity"),
        "objective": j.get("objective", ""),
        "started": bool(j.get("messages")),
        "messages": [{"role": m.get("role"), "text": m.get("text", ""), "at": _iso(m.get("at"))}
                     for m in j.get("messages", [])],
        "model": {f: model.get(f, _empty_model()[f]) for f in MODEL_FIELDS},
        "field_labels": FIELD_LABELS,
        "field_order": FIELD_ORDER,
        "confidence": conf,
        "confidence_source": "reasoning" if dconf is not None else "completeness",
        "completeness": completeness,
        "confidence_band": _confidence_band(conf),
        "ready_for_direction": sufficient or conf >= READY_THRESHOLD,
        "reasoning": _public_reasoning(reasoning),
        "hypotheses": j.get("hypotheses") or [],
        "direction": j.get("direction") or None,
        "has_direction": bool(j.get("direction")),
        "milestones": [{"id": m.get("id"), "order": m.get("order"), "title": m.get("title", ""),
                        "success_metric": m.get("success_metric", ""), "target": m.get("target", ""),
                        "deadline": m.get("deadline", ""), "status": m.get("status", "not_started"),
                        "result": m.get("result", "")}
                       for m in (j.get("milestones") or [])],
        "progress_pct": _milestone_progress(j.get("milestones") or []),
        "team": _team_view(j),
        "unlocks": _unlocks(user, j),
        "credits": user.get("credits", 0),
    }


def _team_view(j):
    team = j.get("team") or {}
    tmodel = _merge_team_model(_empty_team_model(), team.get("model") or {})
    return {
        "started": bool(team.get("messages")),
        "messages": [{"role": m.get("role"), "text": m.get("text", ""), "at": _iso(m.get("at"))}
                     for m in team.get("messages", [])],
        "model": {f: tmodel.get(f, _empty_team_model()[f]) for f in TEAM_FIELDS},
        "field_labels": TEAM_FIELD_LABELS,
        "field_order": TEAM_FIELD_ORDER,
        "confidence": _team_confidence(tmodel),
        "ready_for_plan": _team_confidence(tmodel) >= 40,
        "plan": team.get("plan") or None,
        "offer_dismissed": bool(j.get("team_offer_dismissed")),
    }


# ----------------------------------------------------------------- request models
class StartIn(BaseModel):
    objective: str = Field(min_length=1, max_length=4000)


class MessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class FeedbackIn(BaseModel):
    feedback: str = Field(min_length=1, max_length=4000)


class MilestoneStatusIn(BaseModel):
    status: str
    result: str | None = Field(default=None, max_length=500)


# ----------------------------------------------------------------- endpoints
@router.get("")
def get_journey(user: dict = Depends(current_user)):
    return _view(user, _get_or_create(user["id"]))


@router.post("/start")
def start(body: StartIn, user: dict = Depends(current_user)):
    j = _get_or_create(user["id"])
    if j.get("messages"):
        # already started — return the live conversation, do NOT recharge
        return _view(user, j)
    objective = body.objective.strip()

    def produce():
        reply, new_model, reasoning, bench_raw, hyp_raw, spin_raw, model_name, usage = journey_turn(
            objective, _empty_model(), [], objective,
            prev_reasoning=None, learning=_learning_digest(user["id"], j),
            benchmarks_block=benchmark_digest(j.get("industry") or ""), prev_hypotheses=None,
            cognition_block_text=_safe_cognition(user, objective, None),
            spin_block=_spin_block(None))
        return (reply, new_model, reasoning, bench_raw, hyp_raw, spin_raw), usage, model_name

    (reply, new_model, reasoning, bench_raw, hyp_raw, spin_raw), credits_after, cost = _run_billed(user, produce)
    merged = _merge_model(_empty_model(), new_model)
    msgs = [{"role": "user", "text": objective, "at": now_utc()},
            {"role": "assistant", "text": reply, "at": now_utc()}]
    industry, facts = normalize_facts(bench_raw)
    updates = {"objective": objective, "model": merged, "messages": msgs,
               "reasoning": reasoning, "hypotheses": _normalize_hypotheses(hyp_raw, None),
               "spin": _normalize_spin(spin_raw, None),
               "updated_at": now_utc()}
    if industry:
        updates["industry"] = industry
    journeys_col.update_one({"id": j["id"]}, {"$set": updates})
    ingest_facts(user["id"], industry or j.get("industry", ""), facts, now_utc())
    j = journeys_col.find_one({"id": j["id"]})
    user["credits"] = credits_after
    out = _view(user, j)
    out["cost"] = cost
    return out


@router.post("/message")
def message(body: MessageIn, user: dict = Depends(current_user)):
    j = _get_or_create(user["id"])
    if not j.get("messages"):
        raise HTTPException(400, "Start the conversation first.")
    msg = body.message.strip()
    transcript = j.get("messages", [])
    objective = j.get("objective", "")
    current_model = j.get("model") or _empty_model()
    prev_reasoning = j.get("reasoning") or None
    prev_hyps = j.get("hypotheses") or []

    def produce():
        reply, new_model, reasoning, bench_raw, hyp_raw, model_name, usage = journey_turn(
            objective, current_model, transcript, msg,
            prev_reasoning=prev_reasoning, learning=_learning_digest(user["id"], j),
            benchmarks_block=benchmark_digest(j.get("industry") or ""), prev_hypotheses=prev_hyps,
            cognition_block_text=_safe_cognition(user, msg, current_model))
        return (reply, new_model, reasoning, bench_raw, hyp_raw), usage, model_name

    (reply, new_model, reasoning, bench_raw, hyp_raw), credits_after, cost = _run_billed(user, produce)
    merged = _merge_model(current_model, new_model)
    new_msgs = transcript + [{"role": "user", "text": msg, "at": now_utc()},
                             {"role": "assistant", "text": reply, "at": now_utc()}]
    industry, facts = normalize_facts(bench_raw)
    updates = {"model": merged, "messages": new_msgs,
               "reasoning": reasoning or prev_reasoning,
               "hypotheses": _normalize_hypotheses(hyp_raw, prev_hyps),
               "updated_at": now_utc()}
    if industry:
        updates["industry"] = industry
    journeys_col.update_one({"id": j["id"]}, {"$set": updates})
    ingest_facts(user["id"], industry or j.get("industry", ""), facts, now_utc())
    j = journeys_col.find_one({"id": j["id"]})
    user["credits"] = credits_after
    out = _view(user, j)
    out["cost"] = cost
    return out


@router.post("/reset")
def reset(user: dict = Depends(current_user)):
    journeys_col.update_one({"user_id": user["id"]}, {"$set": {
        "stage": "clarity", "objective": "", "model": _empty_model(),
        "messages": [], "reasoning": None, "hypotheses": [], "direction": None, "milestones": [],
        "team": None, "team_offer_dismissed": False, "updated_at": now_utc()}}, upsert=False)
    return _view(user, _get_or_create(user["id"]))


# ----------------------------------------------------------------- Phase 2: direction + milestones
@router.post("/direction")
def make_direction(user: dict = Depends(current_user)):
    """Distil the live model into a tight Initial Direction (goal, blockers, highest leverage,
    rough success probability, risks, missing info). 1 LLM call. Moves stage -> refine."""
    j = _get_or_create(user["id"])
    if not j.get("messages"):
        raise HTTPException(400, "Start the conversation first.")
    model = j.get("model") or _empty_model()

    def produce():
        reasoning = j.get("reasoning") or {}
        hyps = j.get("hypotheses") or []
        learning = _learning_digest(user["id"], j)
        bench = benchmark_digest(j.get("industry") or "")
        prompt = (f"FOUNDER MODEL (everything understood so far):\n{json.dumps(model, ensure_ascii=False)}\n\n"
                  f"ENGINE REASONING STATE (uncertainty 0-100 per dimension, assumptions, hidden desire):\n"
                  f"{json.dumps(reasoning, ensure_ascii=False)}\n\n"
                  + (f"COMPETING HYPOTHESES (final state, probability 0-100; the leading one should anchor "
                     f"your decision):\n{json.dumps(hyps, ensure_ascii=False)}\n\n" if hyps else "")
                  + (f"THEIR REAL PAST OUTCOMES (build on what worked, avoid what failed):\n{learning}\n\n"
                     if learning else "")
                  + (f"{bench}\n\n" if bench else "")
                  + f"Their stated objective: {j.get('objective', '')}\n\nProduce the decision package now.")
        raw, model_name, usage = _llm_json(DIRECTION_SYSTEM, prompt, max_tokens=2000)
        return _build_direction(raw), usage, model_name

    direction, credits_after, cost = _run_billed(user, produce)
    journeys_col.update_one({"id": j["id"]}, {"$set": {
        "direction": direction, "stage": "refine", "updated_at": now_utc()}})
    j = journeys_col.find_one({"id": j["id"]})
    user["credits"] = credits_after
    out = _view(user, j)
    out["cost"] = cost
    return out


@router.post("/direction/refine")
def refine_direction_ep(body: FeedbackIn, user: dict = Depends(current_user)):
    """Collaborative refinement: the founder says what is off, the direction is rewritten. 1 LLM call."""
    j = _get_or_create(user["id"])
    if not j.get("direction"):
        raise HTTPException(400, "There is no direction to refine yet.")
    model = j.get("model") or _empty_model()
    current = j.get("direction")

    def produce():
        learning = _learning_digest(user["id"], j)
        prompt = (f"CURRENT DIRECTION:\n{json.dumps(current, ensure_ascii=False)}\n\n"
                  f"FOUNDER MODEL:\n{json.dumps(model, ensure_ascii=False)}\n\n"
                  + (f"THEIR REAL PAST OUTCOMES:\n{learning}\n\n" if learning else "")
                  + f"FOUNDER FEEDBACK: {body.feedback.strip()}\n\nReturn the revised decision package.")
        raw, model_name, usage = _llm_json(REFINE_SYSTEM, prompt, max_tokens=2000)
        return _build_direction(raw), usage, model_name

    direction, credits_after, cost = _run_billed(user, produce)
    journeys_col.update_one({"id": j["id"]}, {"$set": {
        "direction": direction, "stage": "refine", "updated_at": now_utc()}})
    j = journeys_col.find_one({"id": j["id"]})
    user["credits"] = credits_after
    out = _view(user, j)
    out["cost"] = cost
    return out


@router.post("/direction/approve")
def approve_direction(user: dict = Depends(current_user)):
    """Founder approves the direction -> generate 4-10 measurable milestones. 1 LLM call.
    Moves stage -> milestones (unlocks the milestones tracker)."""
    j = _get_or_create(user["id"])
    if not j.get("direction"):
        raise HTTPException(400, "Shape a direction before approving it.")
    direction = j.get("direction")
    model = j.get("model") or _empty_model()

    def produce():
        prompt = (f"APPROVED DIRECTION:\n{json.dumps(direction, ensure_ascii=False)}\n\n"
                  f"FOUNDER MODEL:\n{json.dumps(model, ensure_ascii=False)}\n\nCreate the milestones now.")
        raw, model_name, usage = _llm_json(MILESTONE_SYSTEM, prompt, max_tokens=2200)
        ms = _build_milestones(raw)
        if not ms:
            raise ValueError("no measurable milestones produced")
        return ms, usage, model_name

    milestones, credits_after, cost = _run_billed(user, produce)
    journeys_col.update_one({"id": j["id"]}, {"$set": {
        "milestones": milestones, "stage": "milestones", "updated_at": now_utc()}})
    j = journeys_col.find_one({"id": j["id"]})
    user["credits"] = credits_after
    out = _view(user, j)
    out["cost"] = cost
    return out


@router.post("/milestones/{milestone_id}/status")
def set_milestone_status(milestone_id: str, body: MilestoneStatusIn, user: dict = Depends(current_user)):
    """Update a single milestone's status (free). Drives progress_pct (goal -> progress tracker).
    Optional `result` (what actually happened) feeds the Layer-2 learning flywheel."""
    status = (body.status or "").strip()
    if status not in MILESTONE_STATUSES:
        raise HTTPException(422, f"status must be one of {', '.join(MILESTONE_STATUSES)}")
    j = _get_or_create(user["id"])
    ms = j.get("milestones") or []
    found = False
    for m in ms:
        if m.get("id") == milestone_id:
            m["status"] = status
            result = (body.result or "").strip()
            if result:
                m["result"] = _clean(result)
                m["result_at"] = now_utc()
            found = True
            break
    if not found:
        raise HTTPException(404, "Milestone not found")
    journeys_col.update_one({"id": j["id"]}, {"$set": {"milestones": ms, "updated_at": now_utc()}})
    j = journeys_col.find_one({"id": j["id"]})
    return _view(user, j)


# ----------------------------------------------------------------- Phase 3: team setup
@router.post("/team/start")
def team_start(user: dict = Depends(current_user)):
    """Begin the team-setup conversation (free, fixed opening). Requires approved milestones."""
    j = _get_or_create(user["id"])
    if not j.get("milestones"):
        raise HTTPException(400, "Build your milestones first.")
    team = j.get("team") or {}
    if team.get("messages"):
        return _view(user, j)  # already started, no-op
    team = {"messages": [{"role": "assistant", "text": TEAM_OPENING, "at": now_utc()}],
            "model": _empty_team_model(), "plan": None}
    journeys_col.update_one({"id": j["id"]}, {"$set": {
        "team": team, "stage": "team_setup", "team_offer_dismissed": False, "updated_at": now_utc()}})
    return _view(user, journeys_col.find_one({"id": j["id"]}))


@router.post("/team/skip")
def team_skip(user: dict = Depends(current_user)):
    """Founder chooses to keep going solo. Dismisses the team offer (free)."""
    j = _get_or_create(user["id"])
    journeys_col.update_one({"id": j["id"]}, {"$set": {
        "team_offer_dismissed": True, "stage": "operating", "updated_at": now_utc()}})
    return _view(user, journeys_col.find_one({"id": j["id"]}))


@router.post("/team/message")
def team_message(body: MessageIn, user: dict = Depends(current_user)):
    """One team-setup turn (1 LLM). Grows the team model. 400 if team setup not started."""
    j = _get_or_create(user["id"])
    team = j.get("team") or {}
    if not team.get("messages"):
        raise HTTPException(400, "Start team setup first.")
    msg = body.message.strip()
    transcript = team.get("messages", [])
    tmodel = team.get("model") or _empty_team_model()

    def produce():
        reply, new_model, model_name, usage = team_turn(
            j.get("objective", ""), j.get("milestones") or [], tmodel, transcript, msg)
        return (reply, new_model), usage, model_name

    (reply, new_model), credits_after, cost = _run_billed(user, produce)
    merged = _merge_team_model(tmodel, new_model)
    new_msgs = transcript + [{"role": "user", "text": msg, "at": now_utc()},
                             {"role": "assistant", "text": reply, "at": now_utc()}]
    journeys_col.update_one({"id": j["id"]}, {"$set": {
        "team.messages": new_msgs, "team.model": merged, "updated_at": now_utc()}})
    j = journeys_col.find_one({"id": j["id"]})
    user["credits"] = credits_after
    out = _view(user, j)
    out["cost"] = cost
    return out


@router.post("/team/build")
def team_build(user: dict = Depends(current_user)):
    """Generate the team operating plan (daily/weekly/monthly + responsibilities + dependencies +
    escalation rules + success metrics). 1 LLM call. Moves stage -> operating, unlocks Team."""
    j = _get_or_create(user["id"])
    team = j.get("team") or {}
    if not team.get("messages"):
        raise HTTPException(400, "Start team setup first.")
    if not any(m.get("role") == "user" for m in team.get("messages", [])):
        raise HTTPException(400, "Tell me about your team first.")
    tmodel = team.get("model") or _empty_team_model()

    def produce():
        prompt = (f"FOUNDER'S GOAL: {j.get('objective', '')}\n"
                  f"DIRECTION: {json.dumps(j.get('direction') or {}, ensure_ascii=False)}\n"
                  f"MILESTONES: {json.dumps([m.get('title') for m in (j.get('milestones') or [])], ensure_ascii=False)}\n"
                  f"TEAM MODEL: {json.dumps(tmodel, ensure_ascii=False)}\n\nBuild the team operating plan now.")
        raw, model_name, usage = _llm_json(TEAM_PLAN_SYSTEM, prompt, max_tokens=2400)
        plan = _build_team_plan(raw)
        if not (plan["daily"] or plan["weekly"] or plan["monthly"] or plan["responsibilities"]):
            raise ValueError("empty team plan")
        return plan, usage, model_name

    plan, credits_after, cost = _run_billed(user, produce)
    journeys_col.update_one({"id": j["id"]}, {"$set": {
        "team.plan": plan, "stage": "operating", "updated_at": now_utc()}})
    j = journeys_col.find_one({"id": j["id"]})
    user["credits"] = credits_after
    out = _view(user, j)
    out["cost"] = cost
    return out


def ensure_journey_startup():
    """Idempotent indexes for the journey collection."""
    journeys_col.create_index("user_id", unique=True)
    journeys_col.create_index("id", unique=True)
