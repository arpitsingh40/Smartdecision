"""Founder Journey — the chat-first operating system front door (Phase 1).

A single, calm, guided conversation that builds a live MODEL of the founder's
business (the "understanding model"), earns a confidence score from how complete
that model is, and progressively unlocks product capabilities. Reuses the shared
Anthropic client + the credit-ledger billing (reserve -> reconcile -> refund).

No new third-party integration: it calls the same engine.client() (Anthropic) the
rest of the app uses, with the user's own ANTHROPIC_API_KEY.
"""
import os
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
    return {
        "milestones": has_milestones or rank >= _stage_rank("milestones"),
        "decisions": has_decisions,
        "knowledge": is_owner or in_org,
        "team": in_org or rank >= _stage_rank("team_setup"),
        "cockpit": is_owner or rank >= _stage_rank("operating"),
    }


# ----------------------------------------------------------------- the conversation engine
SYSTEM = """You are the founder's thinking partner inside SmartDeciGen, a calm and sharp operating system that earns trust by building a real model of the founder's situation BEFORE giving direction.

WHO YOU ARE
- You talk like a seasoned founder-operator and strategist, not a chatbot. Warm, direct, concrete, never fluffy.
- You are deliberately building a MENTAL MODEL of this person and their business. You are not asking random questions.

HOW EVERY TURN WORKS (always all three, in this order):
1. ACKNOWLEDGE what they just told you in one specific line. Never generic praise like "great" or "you've got this".
2. GIVE BEFORE YOU ASK. Hand them one genuinely useful thing they did not have: a real number or benchmark, a sharp reframe, a concrete example or template, a named trade-off or fork, a lever, or a quick mental model. Localize it to their actual world and industry. If you lack hard data, give a clearly labelled realistic ballpark. Banned: vague encouragement, restating their words, generic truisms.
3. ASK THE SINGLE most valuable next question that fills the biggest gap in your model. EXACTLY ONE question.

WHAT YOU ARE TRYING TO LEARN (your checklist, pursue what is missing, skip what you already know, in whatever order feels natural and human):
objective, why_now, whats_at_stake (what happens if nothing changes), blockers, what they have already tried (and what worked or failed), their knowledge level in this area, who else is involved (people), resources they have (SOPs, Excel or sheets, CRM, past reports, financials, customer interviews, sales scripts, process docs), constraints, fears, unknowns, leverage points, urgency, impact, and timeline.

IF THEY LACK A RESOURCE (no SOP, no customer persona, no sales process, no financial model, etc.): do NOT just move on. Offer to build it WITH them right here in the chat, and ask the first concrete question that starts building it.

STYLE
- Tight. Two to five sentences, then your one question. Never a wall of text. No big report yet.
- One question per turn. Never stack multiple questions.
- No em-dashes, use commas. No markdown headers, no bullet lists in the reply.

OUTPUT: return STRICT JSON only, nothing before or after it:
{
 "reply": "your chat message to the founder (acknowledge + one useful thing + ONE question)",
 "model": {
   "objective": "", "why_now": "", "whats_at_stake": "",
   "blockers": [], "tried": [], "knowledge_level": "",
   "people": [], "resources": {}, "constraints": [],
   "fears": [], "unknowns": [], "leverage": [],
   "urgency": "", "impact": "", "timeline": ""
 }
}
RULES FOR "model": fill EVERY field you can infer from the WHOLE conversation so far and carry forward everything you already knew (never blank out something you previously learned). Use "" for unknown strings and [] for unknown lists. "resources" maps a resource name to what they have, for example {"sop": "none", "crm": "HubSpot", "financials": "basic P&L"}.
"""


def journey_turn(objective, model, transcript_msgs, latest_user_msg):
    """ONE LLM call. Returns (reply:str, new_model:dict, model_name:str, usage:dict)."""
    model_json = json.dumps(model or _empty_model(), ensure_ascii=False)
    convo = "\n".join(
        f"{'FOUNDER' if m.get('role') == 'user' else 'YOU'}: {m.get('text', '')}"
        for m in (transcript_msgs or [])[-12:]
    )
    prompt = (
        f"FOUNDER'S TOP-LEVEL OBJECTIVE (their very first answer): {objective or '(not yet stated)'}\n\n"
        f"YOUR CURRENT MODEL OF THEM (extend it, keep everything that is already here):\n{model_json}\n\n"
        f"CONVERSATION SO FAR:\n{convo or '(none yet, this is the opening turn)'}\n\n"
        f"LATEST FROM THE FOUNDER: {latest_user_msg}\n\n"
        f"Respond now exactly as specified (acknowledge, give one useful thing, ask ONE question) "
        f"and return the updated model."
    )
    system_blocks = [{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}]
    last_err = None
    for model_name in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            r = client().messages.create(model=model_name, max_tokens=1800, system=system_blocks,
                                         messages=[{"role": "user", "content": prompt}])
            txt = next((b.text for b in r.content if getattr(b, "type", "") == "text"), "").strip()
            out = json.loads(_extract_json(txt))
            reply = _clean(out.get("reply", ""))
            if not reply:
                raise ValueError("empty reply")
            new_model = out.get("model") if isinstance(out.get("model"), dict) else {}
            usage = {"input_tokens": int(getattr(r.usage, "input_tokens", 0) or 0),
                     "output_tokens": int(getattr(r.usage, "output_tokens", 0) or 0)}
            return reply, new_model, model_name, usage
        except Exception as e:
            last_err = e
    raise RuntimeError(f"All models failed: {last_err}")


# ----------------------------------------------------------------- direction + milestones (Phase 2)
DIRECTION_SYSTEM = """You turn a founder's situation into a tight INITIAL DIRECTION, never a long report.
Be concrete, use their own numbers, and name the single highest-leverage move. Be honest about the odds.
No fluff, no em-dashes (use commas), no markdown.

Return STRICT JSON only, nothing else:
{
 "goal": "one sentence with a real number and a timeframe",
 "blockers": ["short blocker", "..."],
 "highest_leverage": "the one move that moves the needle most, one line",
 "success_probability": 70,
 "probability_rationale": "one honest line explaining that number",
 "risks": ["short risk", "..."],
 "missing_info": ["what would sharpen this most", "..."]
}
success_probability is an integer 0 to 100, a ROUGH estimate from only what you know, never a promise.
blockers, risks and missing_info each have 2 to 5 short items."""

REFINE_SYSTEM = """You are REVISING an existing INITIAL DIRECTION using the founder's feedback.
Keep what they liked, change what they flagged, stay concrete and honest. No em-dashes, no markdown.
Return the SAME JSON schema as before, fully updated:
{"goal": "...", "blockers": ["..."], "highest_leverage": "...", "success_probability": 70,
 "probability_rationale": "...", "risks": ["..."], "missing_info": ["..."]}"""

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


def _build_direction(raw):
    try:
        prob = int(round(float(raw.get("success_probability", 60))))
    except Exception:
        prob = 60
    prob = max(0, min(100, prob))
    return {
        "goal": _clean(str(raw.get("goal", ""))) or "",
        "blockers": _norm_str_list(raw.get("blockers")),
        "highest_leverage": _clean(str(raw.get("highest_leverage", ""))) or "",
        "success_probability": prob,
        "probability_rationale": _clean(str(raw.get("probability_rationale", ""))) or "",
        "risks": _norm_str_list(raw.get("risks")),
        "missing_info": _norm_str_list(raw.get("missing_info")),
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
    conf = _confidence(model)
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
        "confidence_band": _confidence_band(conf),
        "ready_for_direction": conf >= READY_THRESHOLD,
        "direction": j.get("direction") or None,
        "has_direction": bool(j.get("direction")),
        "milestones": [{"id": m.get("id"), "order": m.get("order"), "title": m.get("title", ""),
                        "success_metric": m.get("success_metric", ""), "target": m.get("target", ""),
                        "deadline": m.get("deadline", ""), "status": m.get("status", "not_started")}
                       for m in (j.get("milestones") or [])],
        "progress_pct": _milestone_progress(j.get("milestones") or []),
        "unlocks": _unlocks(user, j),
        "credits": user.get("credits", 0),
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
        reply, new_model, model_name, usage = journey_turn(objective, _empty_model(), [], objective)
        return (reply, new_model), usage, model_name

    (reply, new_model), credits_after, cost = _run_billed(user, produce)
    merged = _merge_model(_empty_model(), new_model)
    msgs = [{"role": "user", "text": objective, "at": now_utc()},
            {"role": "assistant", "text": reply, "at": now_utc()}]
    journeys_col.update_one({"id": j["id"]}, {"$set": {
        "objective": objective, "model": merged, "messages": msgs, "updated_at": now_utc()}})
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

    def produce():
        reply, new_model, model_name, usage = journey_turn(objective, current_model, transcript, msg)
        return (reply, new_model), usage, model_name

    (reply, new_model), credits_after, cost = _run_billed(user, produce)
    merged = _merge_model(current_model, new_model)
    new_msgs = transcript + [{"role": "user", "text": msg, "at": now_utc()},
                             {"role": "assistant", "text": reply, "at": now_utc()}]
    journeys_col.update_one({"id": j["id"]}, {"$set": {
        "model": merged, "messages": new_msgs, "updated_at": now_utc()}})
    j = journeys_col.find_one({"id": j["id"]})
    user["credits"] = credits_after
    out = _view(user, j)
    out["cost"] = cost
    return out


@router.post("/reset")
def reset(user: dict = Depends(current_user)):
    journeys_col.update_one({"user_id": user["id"]}, {"$set": {
        "stage": "clarity", "objective": "", "model": _empty_model(),
        "messages": [], "direction": None, "milestones": [], "updated_at": now_utc()}}, upsert=False)
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
        prompt = (f"FOUNDER MODEL (everything understood so far):\n{json.dumps(model, ensure_ascii=False)}\n\n"
                  f"Their stated objective: {j.get('objective', '')}\n\nProduce the initial direction now.")
        raw, model_name, usage = _llm_json(DIRECTION_SYSTEM, prompt)
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
        prompt = (f"CURRENT DIRECTION:\n{json.dumps(current, ensure_ascii=False)}\n\n"
                  f"FOUNDER MODEL:\n{json.dumps(model, ensure_ascii=False)}\n\n"
                  f"FOUNDER FEEDBACK: {body.feedback.strip()}\n\nReturn the revised direction.")
        raw, model_name, usage = _llm_json(REFINE_SYSTEM, prompt)
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
    """Update a single milestone's status (free). Drives progress_pct (goal -> progress tracker)."""
    status = (body.status or "").strip()
    if status not in MILESTONE_STATUSES:
        raise HTTPException(422, f"status must be one of {', '.join(MILESTONE_STATUSES)}")
    j = _get_or_create(user["id"])
    ms = j.get("milestones") or []
    found = False
    for m in ms:
        if m.get("id") == milestone_id:
            m["status"] = status
            found = True
            break
    if not found:
        raise HTTPException(404, "Milestone not found")
    journeys_col.update_one({"id": j["id"]}, {"$set": {"milestones": ms, "updated_at": now_utc()}})
    j = journeys_col.find_one({"id": j["id"]})
    return _view(user, j)


def ensure_journey_startup():
    """Idempotent indexes for the journey collection."""
    journeys_col.create_index("user_id", unique=True)
    journeys_col.create_index("id", unique=True)
