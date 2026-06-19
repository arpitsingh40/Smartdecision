import os
import uuid
import time
import math
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from pymongo import ReturnDocument

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from engine import classify_intent, rolling_fields, compute_reengagement_line, llm_turn, llm_complete_action
from db import users_col, threads_col, events_col, telemetry_col
from security import pwd, make_token, current_user
from ledger import record_ledger, inc_stats, ensure_startup
from tracking import router as tracking_router, client_ip, geo_lookup
from admin import router as admin_router
from payments import router as payments_router
from feedback import router as feedback_router
from questionnaire import router as questionnaire_router

TURN_COST = int(os.environ.get("TURN_COST", "5"))
ULTRA_TURN_COST = int(os.environ.get("ULTRA_TURN_COST", "10"))
SIGNUP_CREDITS = int(os.environ.get("SIGNUP_CREDITS", "100"))
# Token-based billing (founder spec): 2 credits per 1,000 tokens (input+output combined).
# Pre-reserve the maximum a turn could cost, run the LLM, then refund the unused portion.
CREDITS_PER_1K_TOKENS = int(os.environ.get("CREDITS_PER_1K_TOKENS", "2"))
TURN_RESERVE_NORMAL = int(os.environ.get("TURN_RESERVE_NORMAL", "8"))     # covers ~4k tokens (normal turn cap)
TURN_RESERVE_ULTRA = int(os.environ.get("TURN_RESERVE_ULTRA", "24"))      # covers ~12k tokens (ultra with thinking)
ASSIST_RESERVE = int(os.environ.get("ASSIST_RESERVE", "10"))              # covers ~5k tokens (complete-action cap)
TURN_RESERVE_VISION = int(os.environ.get("TURN_RESERVE_VISION", "40"))    # covers ~20k tokens (image + PDF + thinking)


def token_cost(tokens_in: int, tokens_out: int) -> int:
    """Actual credit cost from real token usage. Minimum 1 credit so trivial turns aren't free."""
    total = (tokens_in or 0) + (tokens_out or 0)
    return max(1, math.ceil(total / 1000) * CREDITS_PER_1K_TOKENS)

app = FastAPI(title="SmartDecigen Deep Discussion Engine")
api = APIRouter(prefix="/api")
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sdg")

# ----------------------------------------------------------------- helpers
def now_utc():
    return datetime.now(timezone.utc)

def serialize(doc):
    """Recursively convert Mongo doc to JSON-safe types."""
    if isinstance(doc, dict):
        return {k: serialize(v) for k, v in doc.items() if k != "_id"}
    if isinstance(doc, list):
        return [serialize(x) for x in doc]
    if isinstance(doc, datetime):
        return doc.isoformat()
    return doc

def as_aware(dt):
    if dt and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt

# ----------------------------------------------------------------- models
class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = ""

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class GoalIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    why_now: str = Field(min_length=3, max_length=2000)

class TurnIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    mode: str = "normal"  # normal (Opus 4.8) | ultra (Fable 5 ultra thinking)
    adjust: bool = False  # true = user is reshaping the current next action (obstacle / their version)
    # multi-modal: optional file / image attachment, base64-encoded (≤ 8 MB raw)
    attachment_base64: str | None = None
    attachment_filename: str | None = None
    attachment_mime: str | None = None

class StatusIn(BaseModel):
    status: str  # active | paused | graduated | released


# ----------------------------------------------------------------- public config
@api.get("/config")
def public_config():
    """Public, unauthenticated. Lets the marketing surfaces show the live signup grant."""
    return {"signup_credits": int(os.environ.get("SIGNUP_CREDITS", 100))}


# ----------------------------------------------------------------- auth
@api.post("/auth/signup")
def signup(body: SignupIn, request: Request):
    if users_col.find_one({"email": body.email.lower()}):
        raise HTTPException(409, "An account with this email already exists")
    ip = client_ip(request)
    geo = geo_lookup(ip)
    user = {
        "id": str(uuid.uuid4()),
        "email": body.email.lower(),
        "name": body.name.strip(),
        "password_hash": pwd.hash(body.password),
        "credits": SIGNUP_CREDITS,
        "created_at": now_utc(),
        "country": geo["country"], "city": geo["city"], "last_ip": ip,
        "questions_asked": 0, "tokens_in": 0, "tokens_out": 0,
        "credits_issued_free": SIGNUP_CREDITS, "credits_issued_paid": 0,
    }
    users_col.insert_one(user)
    record_ledger(user["id"], "free_grant", SIGNUP_CREDITS, reason="signup")
    inc_stats({"credits_issued_free": SIGNUP_CREDITS})
    return {"token": make_token(user["id"]), "user": {"id": user["id"], "email": user["email"], "name": user["name"], "credits": user["credits"], "is_admin": False, "questionnaire_completed": False}}

@api.post("/auth/login")
def login(body: LoginIn, request: Request):
    user = users_col.find_one({"email": body.email.lower()})
    if not user or not pwd.verify(body.password, user["password_hash"]):
        raise HTTPException(401, "Incorrect email or password")
    ip = client_ip(request)
    users_col.update_one({"id": user["id"]}, {"$set": {"last_login_at": now_utc(), "last_ip": ip}})
    if not user.get("country"):
        geo = geo_lookup(ip)
        users_col.update_one({"id": user["id"]}, {"$set": {"country": geo["country"], "city": geo["city"]}})
    return {"token": make_token(user["id"]), "user": {"id": user["id"], "email": user["email"], "name": user.get("name", ""), "credits": user.get("credits", 0), "is_admin": bool(user.get("is_admin")), "questionnaire_completed": bool(user.get("questionnaire_completed"))}}

@api.get("/auth/me")
def me(user: dict = Depends(current_user)):
    return {"id": user["id"], "email": user["email"], "name": user.get("name", ""), "credits": user.get("credits", 0), "is_admin": bool(user.get("is_admin")), "questionnaire_completed": bool(user.get("questionnaire_completed"))}

# ----------------------------------------------------------------- turn pipeline (6 steps, 1 LLM call)
def run_pipeline(thread: dict, user: dict, message: str, mode: str = "normal",
                 intent_override: str = None, attachment: dict | None = None):
    """Runs the full turn. Returns (out, intent, model, latency, usage).
    Credit deduction is handled by the caller (reserve-and-reconcile against real token usage).
    `attachment` (optional dict): {filename, mime, base64} — file/image the user uploaded with this turn."""
    t0 = time.time()
    now = now_utc()
    last_at = as_aware(thread.get("last_turn_at")) or as_aware(thread["opened_at"])
    days_gap = (now - last_at).total_seconds() / 86400

    # step 2: substrate refresh (pure)
    events = list(events_col.find({"thread_id": thread["thread_id"]}))
    for e in events:
        e["at"] = as_aware(e["at"])
    substrate = rolling_fields(events, now)
    # streak: consecutive kept actions, most recent first (felt momentum, passed to engine voice)
    streak = 0
    for e in sorted(events, key=lambda x: x["at"], reverse=True):
        if e.get("action_done"):
            streak += 1
        else:
            break
    substrate["streak"] = streak
    # step 3: intent (pure; explicit override wins - e.g. action_adjust from the next-action block)
    intent = intent_override or classify_intent(message, days_gap)
    # step 4: single LLM call (normal: Opus 4.8 -> Haiku 4.5 | ultra: Fable 5 -> Opus 4.8 -> Haiku 4.5)
    # Refresh the user doc so any newly-saved questionnaire answers are part of the system context.
    user_doc = users_col.find_one({"id": user["id"]}) or user
    out, model, usage = llm_turn(thread, substrate, message, intent, mode, attachment=attachment, user_doc=user_doc)
    sig = out["signals"]
    # step 5: state update
    events_col.insert_one({
        "id": str(uuid.uuid4()), "thread_id": thread["thread_id"], "user_id": user["id"], "at": now,
        "emotional_temperature": float(sig.get("emotional_temperature", 0.5)),
        "action_assigned": True, "action_done": bool(sig.get("action_done")),
        "contradiction": sig.get("contradiction"),
    })
    events.append({"at": now, "emotional_temperature": float(sig.get("emotional_temperature", 0.5)),
                   "action_assigned": True, "action_done": bool(sig.get("action_done")),
                   "contradiction": sig.get("contradiction")})
    new_snapshot = rolling_fields(events, now)
    new_snapshot["summary_line"] = out["state_summary"].split("\n")[0][:160]
    new_msgs = [
        {"role": "user", "text": message, "at": now, "intent": intent},
        {"role": "engine", "text": out["acknowledgment"], "mirror": out.get("mirror"), "at": now},
    ]
    threads_col.update_one({"thread_id": thread["thread_id"]}, {
        "$set": {
            "current_state_summary": out["state_summary"],
            "current_open_question": out["refreshed_open_question"],
            "current_easiest_path": out.get("refreshed_easiest_path") or thread.get("current_easiest_path") or "(still exploring)",
            "current_next_action": out.get("refreshed_next_action") or None,
            "current_phase": out.get("phase") or "exploring",
            "current_action_payoff": (out.get("action_payoff") or "").strip() or None,
            "current_big_picture": (out.get("big_picture_link") or "").strip() or None,
            "current_bold_move": (out.get("bold_move") or "").strip() or None,
            "current_requested_input": (out.get("requested_input") or "").strip() or None,
            "current_mirror": out.get("mirror"),
            "current_action_artifact": None,  # new action -> old "Do it for me" draft is stale
            "skip_list": out.get("skip_list", []),
            "last_turn_at": now,
            "snapshot_at_last_turn": new_snapshot,
            "rolling": {k: new_snapshot[k] for k in ("emotional_temperature", "execution_consistency", "pace_calibration")},
            # Persist file_facts ONLY when the engine produced a new one this turn (i.e. user
            # attached a file). On turns without an attachment, leave the prior snapshot intact
            # so the file effectively "stays in the room" across the conversation.
            **({"current_file_facts": (out.get("file_facts") or "").strip()} if (out.get("file_facts") or "").strip() else {}),
        },
        "$push": {"messages": {"$each": new_msgs}},
    })
    # step 6: telemetry + usage counters (pre-aggregated -> Founder OS reads stay O(1))
    latency = round(time.time() - t0, 2)
    actual_cost = token_cost(usage["input_tokens"], usage["output_tokens"])
    telemetry_col.insert_one({"id": str(uuid.uuid4()), "type": "discussion_turn", "user_id": user["id"],
                              "thread_id": thread["thread_id"], "intent": intent, "model": model,
                              "mode": mode, "cost": actual_cost,
                              "tokens_in": usage["input_tokens"], "tokens_out": usage["output_tokens"],
                              "latency_s": latency, "response_len": len(out["acknowledgment"]), "at": now})
    users_col.update_one({"id": user["id"]}, {
        "$inc": {"questions_asked": 1, "tokens_in": usage["input_tokens"], "tokens_out": usage["output_tokens"]},
        "$set": {"last_active_at": now}})
    inc_stats({"questions_total": 1, ("turns_ultra" if mode == "ultra" else "turns_normal"): 1,
               "tokens_in": usage["input_tokens"], "tokens_out": usage["output_tokens"]})
    return out, intent, model, latency, usage

# ----------------------------------------------------------------- goals & threads
@api.post("/goals")
def create_goal(body: GoalIn, user: dict = Depends(current_user)):
    # reserve the max a normal turn could cost; reconcile to actual after the LLM responds
    reserve = TURN_RESERVE_NORMAL
    u = users_col.find_one_and_update({"id": user["id"], "credits": {"$gte": reserve}},
                                      {"$inc": {"credits": -reserve}}, return_document=ReturnDocument.AFTER)
    if not u:
        raise HTTPException(402, "Not enough credits")
    now = now_utc()
    thread = {
        "thread_id": str(uuid.uuid4()), "user_id": user["id"],
        "goal": body.title.strip(), "why_now": body.why_now.strip(),
        "opened_at": now, "status": "active",
        "current_state_summary": "(opening)", "current_open_question": "(none yet)",
        "current_easiest_path": "(none yet)", "current_next_action": "(none yet)",
        "current_phase": "exploring",
        "current_action_payoff": None, "current_big_picture": None, "current_bold_move": None,
        "skip_list": [], "messages": [], "last_turn_at": None, "snapshot_at_last_turn": None,
        "rolling": {"emotional_temperature": 0.5, "execution_consistency": 0.5, "pace_calibration": "on-track"},
    }
    threads_col.insert_one(thread)
    try:
        out, intent, model, latency, usage = run_pipeline(thread, user, body.why_now.strip())
    except Exception as e:
        try:
            users_col.update_one({"id": user["id"]}, {"$inc": {"credits": reserve}})  # full refund
        except Exception as refund_err:
            log.error(f"CRITICAL: refund failed after goal-open LLM failure for user={user['id']} reserve={reserve}: {refund_err}")
        threads_col.delete_one({"thread_id": thread["thread_id"]})
        log.error(f"goal creation turn failed: {e}")
        raise HTTPException(502, "The engine could not open this thread. You were not charged — try again.")
    # reconcile: refund reserved - actual
    actual = token_cost(usage["input_tokens"], usage["output_tokens"])
    refund = max(0, reserve - actual)
    if refund:
        u = users_col.find_one_and_update({"id": user["id"]}, {"$inc": {"credits": refund}},
                                          return_document=ReturnDocument.AFTER)
    record_ledger(user["id"], "turn_spend", -actual, thread_id=thread["thread_id"], mode="normal",
                  tokens=usage["input_tokens"] + usage["output_tokens"], reason="goal_opening")
    inc_stats({"credits_spent": actual})
    fresh = threads_col.find_one({"thread_id": thread["thread_id"]})
    return {"thread": serialize(fresh), "acknowledgment": out["acknowledgment"], "credits": u["credits"],
            "cost": actual, "tokens": usage["input_tokens"] + usage["output_tokens"]}

@api.get("/goals")
def list_goals(user: dict = Depends(current_user)):
    now = now_utc()
    items = []
    for t in threads_col.find({"user_id": user["id"]}).sort("opened_at", -1):
        last_at = as_aware(t.get("last_turn_at"))
        hours_since = (now - last_at).total_seconds() / 3600 if last_at else None
        items.append({
            "thread_id": t["thread_id"], "goal": t["goal"], "status": t["status"],
            "pace": t.get("rolling", {}).get("pace_calibration", "on-track"),
            "consistency": t.get("rolling", {}).get("execution_consistency", 0.5),
            "next_action": t.get("current_next_action", ""),
            "open_question": t.get("current_open_question", ""),
            "action_overdue": bool(t["status"] == "active" and hours_since is not None and hours_since > 48),
            "hours_since_turn": round(hours_since) if hours_since is not None else None,
            "opened_at": t["opened_at"].isoformat() if isinstance(t.get("opened_at"), datetime) else t.get("opened_at"),
            "last_turn_at": t["last_turn_at"].isoformat() if isinstance(t.get("last_turn_at"), datetime) else t.get("last_turn_at"),
        })
    kept = events_col.count_documents({"user_id": user["id"], "action_done": True})
    week_ago = now - timedelta(days=7)
    turns_week = telemetry_col.count_documents({"user_id": user["id"], "type": "discussion_turn", "at": {"$gte": week_ago}})
    active = [g for g in items if g["status"] == "active"]
    avg_consistency = round(sum(g["consistency"] for g in active) / len(active), 2) if active else None
    return {"goals": items, "momentum": {"kept_promises": kept, "turns_this_week": turns_week,
                                         "avg_consistency": avg_consistency}}

@api.get("/threads/{thread_id}")
def get_thread(thread_id: str, user: dict = Depends(current_user)):
    t = threads_col.find_one({"thread_id": thread_id, "user_id": user["id"]})
    if not t:
        raise HTTPException(404, "Thread not found")
    now = now_utc()
    reengagement = None
    silence_days = None
    last_at = as_aware(t.get("last_turn_at"))
    if last_at and t["status"] == "active":
        days = int((now - last_at).total_seconds() // 86400)
        if days >= 7 and t.get("snapshot_at_last_turn"):
            events = list(events_col.find({"thread_id": thread_id}))
            for e in events:
                e["at"] = as_aware(e["at"])
            now_snap = rolling_fields(events, now)
            reengagement = compute_reengagement_line(t["snapshot_at_last_turn"], now_snap, days)
            if reengagement:
                telemetry_col.insert_one({"id": str(uuid.uuid4()), "type": "reengagement_shown",
                                          "user_id": user["id"], "thread_id": thread_id, "at": now})
        if days >= 14:
            silence_days = days
    hours_since = (now - last_at).total_seconds() / 3600 if last_at else None
    action_overdue = bool(t["status"] == "active" and hours_since is not None and hours_since > 48)
    return {"thread": serialize(t), "reengagement_line": reengagement, "silence_days": silence_days,
            "action_overdue": action_overdue,
            "hours_since_turn": round(hours_since) if hours_since is not None else None}

@api.post("/threads/{thread_id}/turn")
def turn(thread_id: str, body: TurnIn, user: dict = Depends(current_user)):
    if body.mode not in ("normal", "ultra"):
        raise HTTPException(422, "mode must be 'normal' or 'ultra'")
    # Attachment? Use a larger reserve (vision + extracted file text both inflate token usage).
    attachment = None
    if body.attachment_base64:
        if len(body.attachment_base64) > 12_000_000:  # ~9 MB raw cap to keep memory + token cost sane
            raise HTTPException(413, "Attachment too large. Keep files under 8 MB.")
        attachment = {"base64": body.attachment_base64,
                      "filename": body.attachment_filename or "attachment",
                      "mime": body.attachment_mime or ""}
    if attachment:
        reserve = TURN_RESERVE_VISION
    elif body.mode == "ultra":
        reserve = TURN_RESERVE_ULTRA
    else:
        reserve = TURN_RESERVE_NORMAL
    t = threads_col.find_one({"thread_id": thread_id, "user_id": user["id"]})
    if not t:
        raise HTTPException(404, "Thread not found")
    if t["status"] != "active":
        raise HTTPException(400, f"This thread is {t['status']}. Reactivate it to continue.")
    u = users_col.find_one_and_update({"id": user["id"], "credits": {"$gte": reserve}},
                                      {"$inc": {"credits": -reserve}}, return_document=ReturnDocument.AFTER)
    if not u:
        raise HTTPException(402, "Not enough credits")
    try:
        out, intent, model, latency, usage = run_pipeline(t, user, body.message.strip(), body.mode,
                                                   intent_override="action_adjust" if body.adjust else None,
                                                   attachment=attachment)
    except Exception as e:
        try:
            users_col.update_one({"id": user["id"]}, {"$inc": {"credits": reserve}})  # full refund
        except Exception as refund_err:
            log.error(f"CRITICAL: refund failed after turn LLM failure for user={user['id']} reserve={reserve}: {refund_err}")
        log.error(f"turn failed: {e}")
        raise HTTPException(502, "The engine did not respond. You were not charged — try again.")
    actual = token_cost(usage["input_tokens"], usage["output_tokens"])
    refund = max(0, reserve - actual)
    if refund:
        u = users_col.find_one_and_update({"id": user["id"]}, {"$inc": {"credits": refund}},
                                          return_document=ReturnDocument.AFTER)
    record_ledger(user["id"], "turn_spend", -actual, thread_id=thread_id, mode=body.mode,
                  tokens=usage["input_tokens"] + usage["output_tokens"],
                  reason="vision_turn" if attachment else None)
    inc_stats({"credits_spent": actual})
    fresh = threads_col.find_one({"thread_id": thread_id})
    return {"thread": serialize(fresh), "acknowledgment": out["acknowledgment"],
            "intent": intent, "credits": u["credits"], "model": model, "mode": body.mode,
            "cost": actual, "tokens": usage["input_tokens"] + usage["output_tokens"],
            "had_attachment": bool(attachment)}

# ----------------------------------------------------------------- "Do it for me": ship-ready artifact for the next action
# Token-based billing: 2 credits per 1,000 tokens (input+output). Reserve-and-reconcile so unused tokens are refunded.
@api.post("/threads/{thread_id}/complete-action")
def complete_action(thread_id: str, user: dict = Depends(current_user)):
    t = threads_col.find_one({"thread_id": thread_id, "user_id": user["id"]})
    if not t:
        raise HTTPException(404, "Thread not found")
    if t["status"] != "active":
        raise HTTPException(400, f"This thread is {t['status']}. Reactivate it to continue.")
    if not t.get("current_next_action") or t["current_next_action"].startswith("(none"):
        raise HTTPException(400, "No next action to complete yet.")
    reserve = ASSIST_RESERVE
    u = users_col.find_one_and_update({"id": user["id"], "credits": {"$gte": reserve}},
                                      {"$inc": {"credits": -reserve}}, return_document=ReturnDocument.AFTER)
    if not u:
        raise HTTPException(402, "Not enough credits")
    t0 = time.time()
    try:
        fresh_user = users_col.find_one({"id": user["id"]}) or user
        out, model, usage = llm_complete_action(t, user_doc=fresh_user)
    except Exception as e:
        users_col.update_one({"id": user["id"]}, {"$inc": {"credits": reserve}})  # full refund
        log.error(f"complete-action failed: {e}")
        raise HTTPException(502, "The engine could not prepare this. You were not charged — try again.")
    total_tokens = usage["input_tokens"] + usage["output_tokens"]
    cost = token_cost(usage["input_tokens"], usage["output_tokens"])
    refund = max(0, reserve - cost)
    if refund:
        u = users_col.find_one_and_update({"id": user["id"]}, {"$inc": {"credits": refund}},
                                          return_document=ReturnDocument.AFTER)
    now = now_utc()
    users_col.update_one({"id": user["id"]}, {
        "$inc": {"tokens_in": usage["input_tokens"], "tokens_out": usage["output_tokens"]},
        "$set": {"last_active_at": now}})
    artifact = {
        "kind": out.get("kind", "draft"), "title": out.get("title", "Your draft"),
        "channel": out.get("channel", "other"), "subject": out.get("subject"),
        "artifact": out["artifact"], "steps": out.get("steps", []),
        "handoff": out["handoff"], "time_estimate_min": out.get("time_estimate_min"),
        "generated_at": now, "model": model, "cost": cost, "tokens": total_tokens,
    }
    threads_col.update_one({"thread_id": thread_id}, {"$set": {"current_action_artifact": artifact}})
    record_ledger(user["id"], "action_assist", -cost, thread_id=thread_id,
                  tokens=total_tokens, reason="do_it_for_me")
    inc_stats({"credits_spent": cost, "assists_total": 1,
               "tokens_in": usage["input_tokens"], "tokens_out": usage["output_tokens"]})
    telemetry_col.insert_one({"id": str(uuid.uuid4()), "type": "action_assist", "user_id": user["id"],
                              "thread_id": thread_id, "model": model, "cost": cost,
                              "tokens_in": usage["input_tokens"], "tokens_out": usage["output_tokens"],
                              "latency_s": round(time.time() - t0, 2), "at": now})
    return {"artifact": serialize(artifact), "credits": u.get("credits", 0), "cost": cost,
            "tokens": total_tokens}

@api.patch("/threads/{thread_id}/status")
def set_status(thread_id: str, body: StatusIn, user: dict = Depends(current_user)):
    if body.status not in ("active", "paused", "graduated", "released"):
        raise HTTPException(422, "Invalid status")
    r = threads_col.update_one({"thread_id": thread_id, "user_id": user["id"]}, {"$set": {"status": body.status}})
    if r.matched_count == 0:
        raise HTTPException(404, "Thread not found")
    return {"ok": True, "status": body.status}

@api.get("/credits")
def credits(user: dict = Depends(current_user)):
    return {"credits": user.get("credits", 0),
            "turn_cost": TURN_COST, "ultra_turn_cost": ULTRA_TURN_COST,
            "credits_per_1k_tokens": CREDITS_PER_1K_TOKENS,
            "turn_reserve_normal": TURN_RESERVE_NORMAL,
            "turn_reserve_ultra": TURN_RESERVE_ULTRA,
            "assist_reserve": ASSIST_RESERVE}

@api.get("/")
def root():
    return {"service": "SmartDecigen Deep Discussion Engine", "status": "ok"}

app.include_router(api)
app.include_router(tracking_router)
app.include_router(admin_router)
app.include_router(payments_router)
app.include_router(feedback_router)
app.include_router(questionnaire_router)

@app.on_event("startup")
def _startup():
    ensure_startup()  # idempotent: indexes + founder account + one-time stats backfill

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
