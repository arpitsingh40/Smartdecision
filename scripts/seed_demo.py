"""Seed demo user + thread with the new value-layer fields for UI visualization.
Idempotent: deletes and recreates the demo user's data."""
import os, sys, uuid
from datetime import datetime, timedelta, timezone
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from pymongo import MongoClient
from passlib.context import CryptContext

# Wire up password hashing and demo DB connection
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = MongoClient(os.environ["MONGO_URL"])[os.environ.get("DB_NAME", "test_database")]

EMAIL = "demo@smartdecigen.com"
PASSWORD = "Demo1234!"
now = datetime.now(timezone.utc)

# Wipe any previously seeded demo user data
old = db.users.find_one({"email": EMAIL})
if old:
    db.goal_threads.delete_many({"user_id": old["id"]})
    db.substrate_events.delete_many({"user_id": old["id"]})
    db.telemetry_events.delete_many({"user_id": old["id"]})
    db.users.delete_one({"id": old["id"]})

# Insert the fresh demo user
user_id = str(uuid.uuid4())
db.users.insert_one({
    "id": user_id, "email": EMAIL, "name": "Demo",
    "password_hash": pwd.hash(PASSWORD), "credits": 85, "created_at": now - timedelta(days=12),
})

# Insert the demo thread with a full value-layer state
thread_id = str(uuid.uuid4())
t0 = now - timedelta(days=12)
t1 = now - timedelta(days=5)
t2 = now - timedelta(hours=20)

db.goal_threads.insert_one({
    "thread_id": thread_id, "user_id": user_id,
    "goal": "Launch my freelance design studio",
    "why_now": "I've been planning for a year. If I don't start now I never will.",
    "opened_at": t0, "status": "active",
    "current_state_summary": "You have two portfolio pieces ready and one warm lead from Sara.\nThe website has been 'almost done' for three weeks.\nYou haven't named a price out loud to anyone yet.",
    "current_open_question": "If the website isn't what's stopping you from sending the email — what is?",
    "current_easiest_path": "Skip the website. Send Sara the two finished pieces in a plain email and ask for a 20-minute call.",
    "current_next_action": "Tonight, write the 5-line email to Sara and send it before 10pm.",
    "current_action_payoff": "By Friday you either have a call booked or a clear no — both end three weeks of waiting.",
    "current_big_picture": "The studio doesn't exist until money changes hands once. This email is the shortest line between you and client #1 of the 3 you need to quit safely.",
    "current_bold_move": "Don't pitch Sara as a freelancer — propose a 3-month retainer at a fixed price. It flips you from vendor to partner before the market defines you.",
    "current_mirror": "I may be wrong, but the website sounds less like a task and more like a place to hide.",
    "skip_list": ["the website", "logo redesign"],
    "messages": [
        {"role": "user", "text": "I've been planning for a year. If I don't start now I never will.", "at": t0, "intent": "update"},
        {"role": "engine", "text": "A year of planning means the thinking is done. What's left is the first uncomfortable move.", "at": t0},
        {"role": "user", "text": "Finished the second portfolio piece. Still polishing the website before I reach out to anyone.", "at": t1, "intent": "update"},
        {"role": "engine", "text": "Two pieces done — that's real. But notice the order: polish first, contact later. Sara doesn't need your website.", "at": t1},
        {"role": "user", "text": "You're right, the site can wait. But I froze when I thought about actually emailing Sara.", "at": t2, "intent": "setback"},
        {"role": "engine", "text": "Three weeks of polish on a site no client has asked to see. The work is ready — you said so yourself. The freeze is the price tag, not the email.", "mirror": "I may be wrong, but the website sounds less like a task and more like a place to hide.", "at": t2},
    ],
    "last_turn_at": t2,
    "snapshot_at_last_turn": {"emotional_temperature": 0.62, "execution_consistency": 0.5, "pace_calibration": "on-track", "contradiction_history": [], "summary_line": "You have two portfolio pieces ready and one warm lead from Sara."},
    "rolling": {"emotional_temperature": 0.62, "execution_consistency": 0.5, "pace_calibration": "on-track"},
})

# Seed substrate events for the demo thread
for at, done, temp in [(t0, True, 0.5), (t1, True, 0.55), (t2, False, 0.62)]:
    db.substrate_events.insert_one({
        "id": str(uuid.uuid4()), "thread_id": thread_id, "user_id": user_id, "at": at,
        "emotional_temperature": temp, "action_assigned": True, "action_done": done, "contradiction": None,
    })

print(f"seeded: {EMAIL} / {PASSWORD}  thread={thread_id}")
