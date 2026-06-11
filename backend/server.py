import os, uuid, time, logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from pymongo import MongoClient, ReturnDocument
from passlib.context import CryptContext
import jwt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from engine import classify_intent, rolling_fields, compute_reengagement_line, llm_turn

mongo = MongoClient(os.environ["MONGO_URL"])
db = mongo[os.environ.get("DB_NAME", "test_database")]
users_col = db.users
threads_col = db.goal_threads
events_col = db.substrate_events
telemetry_col = db.telemetry_events

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
TURN_COST = int(os.environ.get("TURN_COST", "5"))
SIGNUP_CREDITS = int(os.environ.get("SIGNUP_CREDITS", "100"))

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

def make_token(user_id: str) -> str:
    return jwt.encode({"sub": user_id, "exp": now_utc() + timedelta(days=30)}, JWT_SECRET, algorithm="HS256")

def current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(authorization.split(" ", 1)[1], JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid or expired token")
    user = users_col.find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(401, "User not found")
    return user

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

class StatusIn(BaseModel):
    status: str  # active | paused | graduated | released

# ----------------------------------------------------------------- auth
@api.post("/auth/signup")
def signup(body: SignupIn):
    if users_col.find_one({"email": body.email.lower()}):
        raise HTTPException(409, "An account with this email already exists")
    user = {
        "id": str(uuid.uuid4()),
        "email": body.email.lower(),
        "name": body.name.strip(),
        "password_hash": pwd.hash(body.password),
        "credits": SIGNUP_CREDITS,
        "created_at": now_utc(),
    }
    users_col.insert_one(user)
    return {"token": make_token(user["id"]), "user": {"id": user["id"], "email": user["email"], "name": user["name"], "credits": user["credits"]}}

@api.post("/auth/login")
def login(body: LoginIn):
    user = users_col.find_one({"email": body.email.lower()})
    if not user or not pwd.verify(body.password, user["password_hash"]):
        raise HTTPException(401, "Incorrect email or password")
    return {"token": make_token(user["id"]), "user": {"id": user["id"], "email": user["email"], "name": user.get("name", ""), "credits": user.get("credits", 0)}}

@api.get("/auth/me")
def me(user: dict = Depends(current_user)):
    return {"id": user["id"], "email": user["email"], "name": user.get("name", ""), "credits": user.get("credits", 0)}

# ----------------------------------------------------------------- turn pipeline (6 steps, 1 LLM call)
def run_pipeline(thread: dict, user: dict, message: str):
    t0 = time.time()
    now = now_utc()
    last_at = as_aware(thread.get("last_turn_at")) or as_aware(thread["opened_at"])
    days_gap = (now - last_at).total_seconds() / 86400

    # step 2: substrate refresh (pure)
    events = list(events_col.find({"thread_id": thread["thread_id"]}))
    for e in events: e["at"] = as_aware(e["at"])
    substrate = rolling_fields(events, now)
    # streak: consecutive kept actions, most recent first (felt momentum, passed to engine voice)
    streak = 0
    for e in sorted(events, key=lambda x: x["at"], reverse=True):
        if e.get("action_done"): streak += 1
        else: break
    substrate["streak"] = streak
    # step 3: intent (pure)
    intent = classify_intent(message, days_gap)
    # step 4: single LLM call (Opus 4.8 -> Haiku 4.5)
    out, model = llm_turn(thread, substrate, message, intent)
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
            "current_easiest_path": out["refreshed_easiest_path"],
            "current_next_action": out["refreshed_next_action"],
            "current_mirror": out.get("mirror"),
            "skip_list": out.get("skip_list", []),
            "last_turn_at": now,
            "snapshot_at_last_turn": new_snapshot,
            "rolling": {k: new_snapshot[k] for k in ("emotional_temperature", "execution_consistency", "pace_calibration")},
        },
        "$push": {"messages": {"$each": new_msgs}},
    })
    # step 6: telemetry
    latency = round(time.time() - t0, 2)
    telemetry_col.insert_one({"id": str(uuid.uuid4()), "type": "discussion_turn", "user_id": user["id"],
                              "thread_id": thread["thread_id"], "intent": intent, "model": model,
                              "latency_s": latency, "response_len": len(out["acknowledgment"]), "at": now})
    return out, intent, model, latency

# ----------------------------------------------------------------- goals & threads
@api.post("/goals")
def create_goal(body: GoalIn, user: dict = Depends(current_user)):
    # atomic credit deduction (creation includes the first engine turn)
    u = users_col.find_one_and_update({"id": user["id"], "credits": {"$gte": TURN_COST}},
                                      {"$inc": {"credits": -TURN_COST}}, return_document=ReturnDocument.AFTER)
    if not u:
        raise HTTPException(402, "Not enough credits")
    now = now_utc()
    thread = {
        "thread_id": str(uuid.uuid4()), "user_id": user["id"],
        "goal": body.title.strip(), "why_now": body.why_now.strip(),
        "opened_at": now, "status": "active",
        "current_state_summary": "(opening)", "current_open_question": "(none yet)",
        "current_easiest_path": "(none yet)", "current_next_action": "(none yet)",
        "skip_list": [], "messages": [], "last_turn_at": None, "snapshot_at_last_turn": None,
        "rolling": {"emotional_temperature": 0.5, "execution_consistency": 0.5, "pace_calibration": "on-track"},
    }
    threads_col.insert_one(thread)
    try:
        out, intent, model, latency = run_pipeline(thread, user, body.why_now.strip())
    except Exception as e:
        users_col.update_one({"id": user["id"]}, {"$inc": {"credits": TURN_COST}})  # refund
        threads_col.delete_one({"thread_id": thread["thread_id"]})
        log.error(f"goal creation turn failed: {e}")
        raise HTTPException(502, "The engine could not open this thread. You were not charged — try again.")
    fresh = threads_col.find_one({"thread_id": thread["thread_id"]})
    return {"thread": serialize(fresh), "acknowledgment": out["acknowledgment"], "credits": u["credits"]}

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
            for e in events: e["at"] = as_aware(e["at"])
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
    t = threads_col.find_one({"thread_id": thread_id, "user_id": user["id"]})
    if not t:
        raise HTTPException(404, "Thread not found")
    if t["status"] != "active":
        raise HTTPException(400, f"This thread is {t['status']}. Reactivate it to continue.")
    u = users_col.find_one_and_update({"id": user["id"], "credits": {"$gte": TURN_COST}},
                                      {"$inc": {"credits": -TURN_COST}}, return_document=ReturnDocument.AFTER)
    if not u:
        raise HTTPException(402, "Not enough credits")
    try:
        out, intent, model, latency = run_pipeline(t, user, body.message.strip())
    except Exception as e:
        users_col.update_one({"id": user["id"]}, {"$inc": {"credits": TURN_COST}})  # refund
        log.error(f"turn failed: {e}")
        raise HTTPException(502, "The engine did not respond. You were not charged — try again.")
    fresh = threads_col.find_one({"thread_id": thread_id})
    return {"thread": serialize(fresh), "acknowledgment": out["acknowledgment"],
            "intent": intent, "credits": u["credits"]}

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
    return {"credits": user.get("credits", 0), "turn_cost": TURN_COST}

@api.get("/")
def root():
    return {"service": "SmartDecigen Deep Discussion Engine", "status": "ok"}

app.include_router(api)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
