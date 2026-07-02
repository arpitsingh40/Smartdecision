"""Backend test for SmartDecigen 3-layer batch build (Layer 1, 2, 3).

CRITICAL: ANTHROPIC_API_KEY is a PLACEHOLDER (environment was reset).
NO LLM call can succeed. Every LLM endpoint must return 502 AND fully refund credits.
LLM budget is ZERO.

Test scenarios:
(A) Journey view shape: fresh signup -> GET /api/journey
(B) 502+refund: POST /api/journey/start -> 502 and credits UNCHANGED (full refund)
(C) Milestone result capture: seed journey doc, test milestone status updates
(D) Referral: GET /api/referral, signup with ref code, invalid ref silently ignored
(E) Decision Cards: share direction, public GET, opinions, delete
(F) POST /api/share/direction for fresh user with no direction -> 400
"""
import os
import sys
import json
import uuid
import requests
from datetime import datetime, timezone
from pymongo import MongoClient

# Backend URL from frontend/.env
BACKEND_URL = "https://a60d8ec6-5fe4-4fd9-b382-0edaea73b42b.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
FOUNDER_EMAIL = "ceo@smartdecigen.com"
FOUNDER_PASSWORD = "FounderOS@2026"

# MongoDB connection
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
mongo = MongoClient(MONGO_URL)
db = mongo["test_database"]
users_col = db.users
journeys_col = db.journeys

def now_utc():
    return datetime.now(timezone.utc)

def log(msg):
    print(f"[TEST] {msg}")

def signup_user(email, password, name="", ref=""):
    """Create a fresh user account."""
    payload = {"email": email, "password": password, "name": name}
    if ref:
        payload["ref"] = ref
    r = requests.post(f"{BACKEND_URL}/auth/signup", json=payload)
    return r

def login_user(email, password):
    """Login and return token."""
    r = requests.post(f"{BACKEND_URL}/auth/login", json={"email": email, "password": password})
    if r.status_code == 200:
        return r.json()["token"]
    return None

def get_user_credits(token):
    """Get current user credits."""
    r = requests.get(f"{BACKEND_URL}/auth/me", headers={"Authorization": f"Bearer {token}"})
    if r.status_code == 200:
        return r.json()["credits"]
    return None

# ============================================================================
# TEST (A): Journey view shape
# ============================================================================
def test_a_journey_view_shape():
    log("=" * 80)
    log("TEST (A): Journey view shape - fresh signup -> GET /api/journey")
    log("=" * 80)
    
    # Fresh signup (100 credits)
    email = f"journey_test_{uuid.uuid4().hex[:8]}@test.com"
    r = signup_user(email, "Test@2026", name="Journey Tester")
    assert r.status_code == 200, f"Signup failed: {r.status_code} {r.text}"
    data = r.json()
    token = data["token"]
    user_data = data["user"]
    assert user_data["credits"] == 100, f"Expected 100 credits, got {user_data['credits']}"
    log(f"✓ Fresh signup: {email}, credits={user_data['credits']}")
    
    # GET /api/journey
    r = requests.get(f"{BACKEND_URL}/journey", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"GET /journey failed: {r.status_code} {r.text}"
    j = r.json()
    
    # CRITICAL ASSERTIONS
    assert j["reasoning"] is None, f"Expected reasoning=null, got {j['reasoning']}"
    assert j["confidence"] == 0, f"Expected confidence=0, got {j['confidence']}"
    assert j["confidence_source"] == "completeness", f"Expected confidence_source='completeness', got {j['confidence_source']}"
    assert j["completeness"] == 0, f"Expected completeness=0, got {j['completeness']}"
    assert j["ready_for_direction"] is False, f"Expected ready_for_direction=false, got {j['ready_for_direction']}"
    assert j["started"] is False, f"Expected started=false, got {j['started']}"
    
    log(f"✓ GET /api/journey -> 200 with reasoning=null, confidence=0, confidence_source='completeness', completeness=0, ready_for_direction=false, started=false")
    log(f"  Full response keys: {list(j.keys())}")
    log("")
    return token, email

# ============================================================================
# TEST (B): 502+refund guarantee
# ============================================================================
def test_b_502_refund():
    log("=" * 80)
    log("TEST (B): 502+refund - LLM endpoints return 502 and FULLY refund credits")
    log("=" * 80)
    
    # Fresh signup
    email = f"refund_test_{uuid.uuid4().hex[:8]}@test.com"
    r = signup_user(email, "Test@2026")
    assert r.status_code == 200, f"Signup failed: {r.status_code} {r.text}"
    token = r.json()["token"]
    credits_before = r.json()["user"]["credits"]
    assert credits_before == 100, f"Expected 100 credits, got {credits_before}"
    log(f"✓ Fresh signup: {email}, credits={credits_before}")
    
    # TEST B1: POST /api/journey/start with objective -> 502 and credits UNCHANGED
    log("TEST B1: POST /api/journey/start -> 502 and credits UNCHANGED (full refund)")
    r = requests.post(f"{BACKEND_URL}/journey/start", 
                     headers={"Authorization": f"Bearer {token}"},
                     json={"objective": "Grow my bakery to 12L"})
    assert r.status_code == 502, f"Expected 502, got {r.status_code} {r.text}"
    log(f"✓ POST /api/journey/start -> 502 (expected, ANTHROPIC_API_KEY is placeholder)")
    
    # Check credits UNCHANGED
    credits_after = get_user_credits(token)
    assert credits_after == credits_before, f"REFUND FAILED: credits before={credits_before}, after={credits_after}"
    log(f"✓ Credits UNCHANGED: {credits_before} -> {credits_after} (full refund guarantee working)")
    
    # TEST B2: POST /api/journey/message before start -> 400
    log("TEST B2: POST /api/journey/message before start -> 400")
    r = requests.post(f"{BACKEND_URL}/journey/message",
                     headers={"Authorization": f"Bearer {token}"},
                     json={"message": "test message"})
    assert r.status_code == 400, f"Expected 400, got {r.status_code} {r.text}"
    log(f"✓ POST /api/journey/message before start -> 400")
    
    # TEST B3: POST /api/journey/start with empty objective -> 422
    log("TEST B3: POST /api/journey/start with empty objective -> 422")
    r = requests.post(f"{BACKEND_URL}/journey/start",
                     headers={"Authorization": f"Bearer {token}"},
                     json={"objective": ""})
    assert r.status_code == 422, f"Expected 422, got {r.status_code} {r.text}"
    log(f"✓ POST /api/journey/start with empty objective -> 422")
    log("")

# ============================================================================
# TEST (C): Milestone result capture
# ============================================================================
def test_c_milestone_result():
    log("=" * 80)
    log("TEST (C): Milestone result capture - seed journey doc, test milestone status")
    log("=" * 80)
    
    # Fresh signup
    email = f"milestone_test_{uuid.uuid4().hex[:8]}@test.com"
    r = signup_user(email, "Test@2026")
    assert r.status_code == 200, f"Signup failed: {r.status_code} {r.text}"
    token = r.json()["token"]
    user_id = r.json()["user"]["id"]
    log(f"✓ Fresh signup: {email}, user_id={user_id}")
    
    # Seed a journey doc directly in Mongo with milestones
    journey_id = str(uuid.uuid4())
    milestone_id = "m1"
    journey_doc = {
        "id": journey_id,
        "user_id": user_id,
        "stage": "milestones",
        "objective": "Test objective",
        "model": {},
        "messages": [{"role": "user", "text": "test", "at": now_utc()}],
        "milestones": [{
            "id": milestone_id,
            "order": 1,
            "title": "Test milestone",
            "success_metric": "",
            "target": "",
            "deadline": "",
            "status": "not_started"
        }],
        "created_at": now_utc(),
        "updated_at": now_utc()
    }
    
    # Check if user already has a journey (unique index on user_id)
    existing = journeys_col.find_one({"user_id": user_id})
    if existing:
        log(f"  User already has journey, updating with $set")
        journeys_col.update_one({"user_id": user_id}, {"$set": journey_doc})
    else:
        log(f"  Inserting new journey doc")
        journeys_col.insert_one(journey_doc)
    log(f"✓ Seeded journey doc with milestone_id={milestone_id}")
    
    # TEST C1: POST /api/journey/milestones/{id}/status with status='done' and result
    log("TEST C1: POST milestone status='done' with result")
    r = requests.post(f"{BACKEND_URL}/journey/milestones/{milestone_id}/status",
                     headers={"Authorization": f"Bearer {token}"},
                     json={"status": "done", "result": "Hired 2 reps"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code} {r.text}"
    j = r.json()
    milestone = next((m for m in j["milestones"] if m["id"] == milestone_id), None)
    assert milestone is not None, "Milestone not found in response"
    assert milestone["result"] == "Hired 2 reps", f"Expected result='Hired 2 reps', got {milestone['result']}"
    assert milestone["status"] == "done", f"Expected status='done', got {milestone['status']}"
    assert j["progress_pct"] == 100, f"Expected progress_pct=100, got {j['progress_pct']}"
    log(f"✓ Milestone status='done', result='Hired 2 reps', progress_pct=100")
    
    # TEST C2: POST status='in_progress' (no result field) -> result PRESERVED
    log("TEST C2: POST status='in_progress' (no result) -> result PRESERVED")
    r = requests.post(f"{BACKEND_URL}/journey/milestones/{milestone_id}/status",
                     headers={"Authorization": f"Bearer {token}"},
                     json={"status": "in_progress"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code} {r.text}"
    j = r.json()
    milestone = next((m for m in j["milestones"] if m["id"] == milestone_id), None)
    assert milestone["result"] == "Hired 2 reps", f"Result NOT preserved: got {milestone['result']}"
    assert milestone["status"] == "in_progress", f"Expected status='in_progress', got {milestone['status']}"
    assert j["progress_pct"] == 0, f"Expected progress_pct=0, got {j['progress_pct']}"
    log(f"✓ Result PRESERVED: 'Hired 2 reps', status='in_progress', progress_pct=0")
    
    # TEST C3: POST status='bogus' -> 422
    log("TEST C3: POST status='bogus' -> 422")
    r = requests.post(f"{BACKEND_URL}/journey/milestones/{milestone_id}/status",
                     headers={"Authorization": f"Bearer {token}"},
                     json={"status": "bogus"})
    assert r.status_code == 422, f"Expected 422, got {r.status_code} {r.text}"
    log(f"✓ Invalid status -> 422")
    
    # TEST C4: Unknown milestone id -> 404
    log("TEST C4: Unknown milestone id -> 404")
    r = requests.post(f"{BACKEND_URL}/journey/milestones/unknown-id/status",
                     headers={"Authorization": f"Bearer {token}"},
                     json={"status": "done"})
    assert r.status_code == 404, f"Expected 404, got {r.status_code} {r.text}"
    log(f"✓ Unknown milestone id -> 404")
    
    # TEST C5: result of 501 chars -> 422
    log("TEST C5: result of 501 chars -> 422")
    long_result = "x" * 501
    r = requests.post(f"{BACKEND_URL}/journey/milestones/{milestone_id}/status",
                     headers={"Authorization": f"Bearer {token}"},
                     json={"status": "done", "result": long_result})
    assert r.status_code == 422, f"Expected 422, got {r.status_code} {r.text}"
    log(f"✓ result of 501 chars -> 422")
    log("")

# ============================================================================
# TEST (D): Referral
# ============================================================================
def test_d_referral():
    log("=" * 80)
    log("TEST (D): Referral - stable code, signup with ref, invalid ref ignored")
    log("=" * 80)
    
    # User1: GET /api/referral
    email1 = f"referrer_{uuid.uuid4().hex[:8]}@test.com"
    r = signup_user(email1, "Test@2026")
    assert r.status_code == 200, f"Signup failed: {r.status_code} {r.text}"
    token1 = r.json()["token"]
    user1_id = r.json()["user"]["id"]
    log(f"✓ User1 signup: {email1}")
    
    # GET /api/referral
    r = requests.get(f"{BACKEND_URL}/referral", headers={"Authorization": f"Bearer {token1}"})
    assert r.status_code == 200, f"GET /referral failed: {r.status_code} {r.text}"
    ref_data = r.json()
    code = ref_data["code"]
    assert len(code) == 8, f"Expected 8-char code, got {len(code)}"
    assert ref_data["path"] == f"/auth?ref={code}", f"Expected path=/auth?ref={code}, got {ref_data['path']}"
    assert ref_data["invited_count"] == 0, f"Expected invited_count=0, got {ref_data['invited_count']}"
    assert ref_data["credits_earned"] == 0, f"Expected credits_earned=0, got {ref_data['credits_earned']}"
    assert ref_data["bonus"] == 25, f"Expected bonus=25, got {ref_data['bonus']}"
    log(f"✓ GET /api/referral -> code={code}, invited_count=0, credits_earned=0, bonus=25")
    
    # Call again -> SAME code (stable)
    r = requests.get(f"{BACKEND_URL}/referral", headers={"Authorization": f"Bearer {token1}"})
    assert r.status_code == 200, f"GET /referral failed: {r.status_code} {r.text}"
    code2 = r.json()["code"]
    assert code2 == code, f"Code NOT stable: first={code}, second={code2}"
    log(f"✓ GET /api/referral again -> SAME code (stable)")
    
    # User2: Signup with ref code
    email2 = f"referred_{uuid.uuid4().hex[:8]}@test.com"
    r = signup_user(email2, "Test@2026", ref=code)
    assert r.status_code == 200, f"Signup with ref failed: {r.status_code} {r.text}"
    user2_credits = r.json()["user"]["credits"]
    assert user2_credits == 125, f"Expected 125 credits (100+25), got {user2_credits}"
    log(f"✓ User2 signup with ref={code} -> credits=125 (100+25 bonus)")
    
    # User1: Check credits increased by 25
    user1_credits = get_user_credits(token1)
    assert user1_credits == 125, f"Expected 125 credits (100+25), got {user1_credits}"
    log(f"✓ User1 credits increased by 25 -> {user1_credits}")
    
    # User1: GET /api/referral -> invited_count=1, credits_earned=25
    r = requests.get(f"{BACKEND_URL}/referral", headers={"Authorization": f"Bearer {token1}"})
    assert r.status_code == 200, f"GET /referral failed: {r.status_code} {r.text}"
    ref_data = r.json()
    assert ref_data["invited_count"] == 1, f"Expected invited_count=1, got {ref_data['invited_count']}"
    assert ref_data["credits_earned"] == 25, f"Expected credits_earned=25, got {ref_data['credits_earned']}"
    log(f"✓ GET /api/referral -> invited_count=1, credits_earned=25")
    
    # User3: Signup with invalid ref code -> 200 and credits=100 (invalid ref silently ignored)
    email3 = f"invalid_ref_{uuid.uuid4().hex[:8]}@test.com"
    r = signup_user(email3, "Test@2026", ref="garbagecode")
    assert r.status_code == 200, f"Signup with invalid ref failed: {r.status_code} {r.text}"
    user3_credits = r.json()["user"]["credits"]
    assert user3_credits == 100, f"Expected 100 credits (invalid ref ignored), got {user3_credits}"
    log(f"✓ User3 signup with ref='garbagecode' -> 200, credits=100 (invalid ref silently ignored, signup never blocked)")
    log("")

# ============================================================================
# TEST (E): Decision Cards
# ============================================================================
def test_e_decision_cards():
    log("=" * 80)
    log("TEST (E): Decision Cards - share, public GET, opinions, delete")
    log("=" * 80)
    
    # Setup: Create user with direction (seed journey doc with direction)
    email = f"card_owner_{uuid.uuid4().hex[:8]}@test.com"
    r = signup_user(email, "Test@2026", name="Card Owner")
    assert r.status_code == 200, f"Signup failed: {r.status_code} {r.text}"
    token = r.json()["token"]
    user_id = r.json()["user"]["id"]
    log(f"✓ Card owner signup: {email}, user_id={user_id}")
    
    # Seed journey doc with direction
    journey_id = str(uuid.uuid4())
    direction = {
        "decision": "Decline low-margin walk-ins",
        "goal": "12L monthly in 12 months",
        "highest_leverage": "Fix pricing",
        "success_probability": 60,
        "probability_rationale": "rough",
        "risks": ["r1", "r2"],
        "missing_info": [],
        "blockers": ["b1"],
        "trade_offs": ["Give up quick cash"],
        "first_moves": ["Call 5 customers in 48h"],
        "learning_loop": {
            "signals": ["weekly margin"],
            "assumptions_to_test": ["demand exists"]
        }
    }
    journey_doc = {
        "id": journey_id,
        "user_id": user_id,
        "stage": "milestones",
        "objective": "Grow my bakery to 12L",
        "model": {},
        "messages": [{"role": "user", "text": "test", "at": now_utc()}],
        "direction": direction,
        "milestones": [],
        "created_at": now_utc(),
        "updated_at": now_utc()
    }
    existing = journeys_col.find_one({"user_id": user_id})
    if existing:
        journeys_col.update_one({"user_id": user_id}, {"$set": journey_doc})
    else:
        journeys_col.insert_one(journey_doc)
    log(f"✓ Seeded journey doc with direction")
    
    # TEST E1: POST /api/share/direction -> 200 with share_id
    log("TEST E1: POST /api/share/direction -> 200 with share_id")
    r = requests.post(f"{BACKEND_URL}/share/direction", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code} {r.text}"
    share_data = r.json()
    share_id = share_data["share_id"]
    assert len(share_id) == 10, f"Expected 10-char share_id, got {len(share_id)}"
    assert share_data["path"] == f"/d/{share_id}", f"Expected path=/d/{share_id}, got {share_data['path']}"
    log(f"✓ POST /api/share/direction -> share_id={share_id}, path={share_data['path']}")
    
    # POST again -> SAME share_id (stable link)
    r = requests.post(f"{BACKEND_URL}/share/direction", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code} {r.text}"
    share_id2 = r.json()["share_id"]
    assert share_id2 == share_id, f"Share ID NOT stable: first={share_id}, second={share_id2}"
    log(f"✓ POST /api/share/direction again -> SAME share_id (stable link)")
    
    # TEST E2: GET /api/share/{share_id} WITH NO AUTH HEADER -> 200
    log("TEST E2: GET /api/share/{share_id} public (no auth) -> 200")
    r = requests.get(f"{BACKEND_URL}/share/{share_id}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code} {r.text}"
    card = r.json()
    
    # Check founder_name (first name only)
    assert "founder_name" in card, "Missing founder_name"
    assert card["founder_name"] == "Card", f"Expected first name 'Card', got {card['founder_name']}"
    log(f"✓ founder_name={card['founder_name']} (first name only)")
    
    # Check card contains required fields
    assert "card" in card, "Missing card"
    c = card["card"]
    assert c["decision"] == "Decline low-margin walk-ins", f"decision mismatch"
    assert c["goal"] == "12L monthly in 12 months", f"goal mismatch"
    assert c["trade_offs"] == ["Give up quick cash"], f"trade_offs mismatch"
    assert c["first_moves"] == ["Call 5 customers in 48h"], f"first_moves mismatch"
    assert c["success_probability"] == 60, f"success_probability mismatch"
    assert len(c["risks"]) <= 3, f"risks should be max 3, got {len(c['risks'])}"
    log(f"✓ Card contains decision/goal/trade_offs/first_moves/success_probability/risks")
    
    # Privacy check: response must NOT contain keys: model, messages, objective, hidden_desire
    forbidden_keys = ["model", "messages", "objective", "hidden_desire"]
    for key in forbidden_keys:
        assert key not in card, f"PRIVACY LEAK: response contains forbidden key '{key}'"
        assert key not in c, f"PRIVACY LEAK: card contains forbidden key '{key}'"
    log(f"✓ Privacy check: NO model/messages/objective/hidden_desire in response")
    
    # Call public GET twice -> views increments
    views1 = card["views"]
    r = requests.get(f"{BACKEND_URL}/share/{share_id}")
    assert r.status_code == 200, f"Expected 200, got {r.status_code} {r.text}"
    views2 = r.json()["views"]
    assert views2 > views1, f"Views did NOT increment: {views1} -> {views2}"
    log(f"✓ Views incremented: {views1} -> {views2}")
    
    # TEST E3: POST /api/share/{share_id}/opinion by card OWNER -> 400
    log("TEST E3: POST opinion by card OWNER -> 400")
    r = requests.post(f"{BACKEND_URL}/share/{share_id}/opinion",
                     headers={"Authorization": f"Bearer {token}"},
                     json={"text": "My own opinion"})
    assert r.status_code == 400, f"Expected 400, got {r.status_code} {r.text}"
    log(f"✓ Owner cannot leave opinion on own card -> 400")
    
    # TEST E4: POST opinion by SECOND signed-in user -> 200
    log("TEST E4: POST opinion by second user -> 200")
    email2 = f"opinion_user_{uuid.uuid4().hex[:8]}@test.com"
    r = signup_user(email2, "Test@2026", name="Opinion User")
    assert r.status_code == 200, f"Signup failed: {r.status_code} {r.text}"
    token2 = r.json()["token"]
    log(f"✓ Second user signup: {email2}")
    
    r = requests.post(f"{BACKEND_URL}/share/{share_id}/opinion",
                     headers={"Authorization": f"Bearer {token2}"},
                     json={"text": "Solid call, but test pricing first"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code} {r.text}"
    opinions = r.json()["opinions"]
    assert len(opinions) == 1, f"Expected 1 opinion, got {len(opinions)}"
    assert opinions[0]["text"] == "Solid call, but test pricing first", f"Opinion text mismatch"
    log(f"✓ Opinion added: {opinions[0]['text']}")
    
    # Same second user posts again with different text -> opinions STILL length 1 (replaced)
    log("TEST E5: Same user posts again -> opinion REPLACED (not appended)")
    r = requests.post(f"{BACKEND_URL}/share/{share_id}/opinion",
                     headers={"Authorization": f"Bearer {token2}"},
                     json={"text": "Actually, I changed my mind"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code} {r.text}"
    opinions = r.json()["opinions"]
    assert len(opinions) == 1, f"Expected 1 opinion (replaced), got {len(opinions)}"
    assert opinions[0]["text"] == "Actually, I changed my mind", f"Opinion NOT replaced"
    log(f"✓ Opinion replaced: {opinions[0]['text']}")
    
    # TEST E6: No auth opinion -> 401
    log("TEST E6: No auth opinion -> 401")
    r = requests.post(f"{BACKEND_URL}/share/{share_id}/opinion",
                     json={"text": "Anonymous opinion"})
    assert r.status_code == 401, f"Expected 401, got {r.status_code} {r.text}"
    log(f"✓ No auth opinion -> 401")
    
    # TEST E7: Empty text -> 422
    log("TEST E7: Empty text -> 422")
    r = requests.post(f"{BACKEND_URL}/share/{share_id}/opinion",
                     headers={"Authorization": f"Bearer {token2}"},
                     json={"text": ""})
    assert r.status_code == 422, f"Expected 422, got {r.status_code} {r.text}"
    log(f"✓ Empty text -> 422")
    
    # TEST E8: Opinion on unknown card id -> 404
    log("TEST E8: Opinion on unknown card id -> 404")
    r = requests.post(f"{BACKEND_URL}/share/unknownid/opinion",
                     headers={"Authorization": f"Bearer {token2}"},
                     json={"text": "test"})
    assert r.status_code == 404, f"Expected 404, got {r.status_code} {r.text}"
    log(f"✓ Opinion on unknown card -> 404")
    
    # TEST E9: DELETE by second user -> 404
    log("TEST E9: DELETE by second user -> 404")
    r = requests.delete(f"{BACKEND_URL}/share/{share_id}",
                       headers={"Authorization": f"Bearer {token2}"})
    assert r.status_code == 404, f"Expected 404, got {r.status_code} {r.text}"
    log(f"✓ DELETE by non-owner -> 404")
    
    # TEST E10: DELETE by owner -> 200
    log("TEST E10: DELETE by owner -> 200")
    r = requests.delete(f"{BACKEND_URL}/share/{share_id}",
                       headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"Expected 200, got {r.status_code} {r.text}"
    assert r.json()["removed"] is True, f"Expected removed=true"
    log(f"✓ DELETE by owner -> 200, removed=true")
    
    # TEST E11: Public GET after delete -> 404
    log("TEST E11: Public GET after delete -> 404")
    r = requests.get(f"{BACKEND_URL}/share/{share_id}")
    assert r.status_code == 404, f"Expected 404, got {r.status_code} {r.text}"
    log(f"✓ Public GET after delete -> 404")
    log("")

# ============================================================================
# TEST (F): POST /api/share/direction for fresh user with no direction -> 400
# ============================================================================
def test_f_share_no_direction():
    log("=" * 80)
    log("TEST (F): POST /api/share/direction for fresh user with no direction -> 400")
    log("=" * 80)
    
    # Fresh signup
    email = f"no_direction_{uuid.uuid4().hex[:8]}@test.com"
    r = signup_user(email, "Test@2026")
    assert r.status_code == 200, f"Signup failed: {r.status_code} {r.text}"
    token = r.json()["token"]
    log(f"✓ Fresh signup: {email}")
    
    # POST /api/share/direction -> 400
    r = requests.post(f"{BACKEND_URL}/share/direction", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 400, f"Expected 400, got {r.status_code} {r.text}"
    log(f"✓ POST /api/share/direction with no direction -> 400")
    log("")

# ============================================================================
# MAIN
# ============================================================================
def main():
    log("=" * 80)
    log("SmartDecigen Backend Test - 3-Layer Batch Build (Layer 1, 2, 3)")
    log("CRITICAL: ANTHROPIC_API_KEY is PLACEHOLDER -> LLM budget is ZERO")
    log("All LLM endpoints must return 502 AND fully refund credits")
    log("=" * 80)
    log("")
    
    try:
        # Run all tests
        test_a_journey_view_shape()
        test_b_502_refund()
        test_c_milestone_result()
        test_d_referral()
        test_e_decision_cards()
        test_f_share_no_direction()
        
        log("=" * 80)
        log("ALL TESTS PASSED ✓")
        log("=" * 80)
        return 0
    except AssertionError as e:
        log(f"TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        log(f"TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
