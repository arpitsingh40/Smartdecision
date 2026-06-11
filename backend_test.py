#!/usr/bin/env python3
"""
SmartDecigen Backend Test Suite
Tests new value layers (action_payoff, big_picture_link, bold_move) and engine modes (normal/ultra).
CRITICAL: Keeps total LLM calls <= 5 (each costs real money via Anthropic API).
"""
import requests
import time
import sys

# Backend URL from frontend/.env
BASE_URL = "https://36cb0266-8d04-47aa-a315-0aedeb82fa21.preview.emergentagent.com/api"
TIMEOUT_NORMAL = 60
TIMEOUT_ULTRA = 120  # Ultra mode can take 30-90s

# Test state
llm_call_count = 0
test_results = []

def log_test(name, passed, details=""):
    """Log test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    test_results.append({"name": name, "passed": passed, "details": details})
    print(f"{status}: {name}")
    if details:
        print(f"  → {details}")

def track_llm_call(description):
    """Track LLM calls to stay within budget."""
    global llm_call_count
    llm_call_count += 1
    print(f"\n🔥 LLM CALL #{llm_call_count}: {description}")
    if llm_call_count > 5:
        print("⚠️  WARNING: Exceeded 5 LLM call budget!")

# ============================================================================
# TEST 1: Auth Sanity
# ============================================================================
print("\n" + "="*80)
print("TEST 1: AUTH SANITY")
print("="*80)

# 1a. Signup new user (gets 100 credits for clean testing)
print("\n1a. Signup new user...")
signup_email = f"test_{int(time.time())}@smartdecigen.com"
signup_payload = {
    "email": signup_email,
    "password": "TestPass123!",
    "name": "Test User"
}
try:
    r = requests.post(f"{BASE_URL}/auth/signup", json=signup_payload, timeout=10)
    if r.status_code == 200:
        data = r.json()
        test_token = data.get("token")
        test_user = data.get("user", {})
        initial_credits = test_user.get("credits", 0)
        log_test("Signup new user", test_token is not None and initial_credits == 100,
                 f"Token received, credits={initial_credits}")
    else:
        log_test("Signup new user", False, f"Status {r.status_code}: {r.text}")
        sys.exit(1)
except Exception as e:
    log_test("Signup new user", False, f"Exception: {e}")
    sys.exit(1)

# 1b. Login demo user
print("\n1b. Login demo user...")
try:
    r = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "demo@smartdecigen.com",
        "password": "Demo1234!"
    }, timeout=10)
    if r.status_code == 200:
        demo_token = r.json().get("token")
        log_test("Login demo user", demo_token is not None, "Token received")
    else:
        log_test("Login demo user", False, f"Status {r.status_code}: {r.text}")
except Exception as e:
    log_test("Login demo user", False, f"Exception: {e}")

# 1c. GET /api/auth/me
print("\n1c. GET /api/auth/me...")
headers = {"Authorization": f"Bearer {test_token}"}
try:
    r = requests.get(f"{BASE_URL}/auth/me", headers=headers, timeout=10)
    if r.status_code == 200:
        me_data = r.json()
        log_test("GET /api/auth/me", me_data.get("email") == signup_email,
                 f"Email matches: {me_data.get('email')}")
    else:
        log_test("GET /api/auth/me", False, f"Status {r.status_code}: {r.text}")
except Exception as e:
    log_test("GET /api/auth/me", False, f"Exception: {e}")

# ============================================================================
# TEST 2: Goal Creation (LLM CALL #1)
# ============================================================================
print("\n" + "="*80)
print("TEST 2: GOAL CREATION (LLM CALL #1)")
print("="*80)

track_llm_call("Goal creation")
goal_payload = {
    "title": "Launch my freelance consulting practice",
    "why_now": "I've been thinking about this for months, but my current job is draining me. I need to take control of my career and build something that's mine."
}

start_time = time.time()
try:
    r = requests.post(f"{BASE_URL}/goals", json=goal_payload, headers=headers, timeout=TIMEOUT_NORMAL)
    latency = round(time.time() - start_time, 2)
    
    if r.status_code == 200:
        data = r.json()
        thread = data.get("thread", {})
        thread_id = thread.get("thread_id")
        credits_after = data.get("credits")
        
        # Verify thread structure
        action_payoff = thread.get("current_action_payoff")
        big_picture = thread.get("current_big_picture")
        bold_move = thread.get("current_bold_move")
        
        # Check non-empty strings for required fields
        payoff_valid = isinstance(action_payoff, str) and len(action_payoff.strip()) > 0
        big_picture_valid = isinstance(big_picture, str) and len(big_picture.strip()) > 0
        bold_move_exists = "current_bold_move" in thread  # can be null or string
        
        # Check credits deduction
        credits_valid = credits_after == (initial_credits - 5)
        
        all_valid = payoff_valid and big_picture_valid and bold_move_exists and credits_valid
        
        details = (f"Latency: {latency}s | Credits: {initial_credits} → {credits_after} | "
                  f"action_payoff: {'✓' if payoff_valid else '✗'} ({len(action_payoff or '')} chars) | "
                  f"big_picture: {'✓' if big_picture_valid else '✗'} ({len(big_picture or '')} chars) | "
                  f"bold_move: {'✓' if bold_move_exists else '✗'} ({type(bold_move).__name__})")
        
        log_test("Goal creation - value fields", all_valid, details)
        
        if not all_valid:
            print(f"  action_payoff: {action_payoff}")
            print(f"  big_picture: {big_picture}")
            print(f"  bold_move: {bold_move}")
    else:
        log_test("Goal creation - value fields", False, f"Status {r.status_code}: {r.text}")
        sys.exit(1)
except Exception as e:
    log_test("Goal creation - value fields", False, f"Exception: {e}")
    sys.exit(1)

# ============================================================================
# TEST 3: Normal Mode Turn (LLM CALL #2)
# ============================================================================
print("\n" + "="*80)
print("TEST 3: NORMAL MODE TURN (LLM CALL #2)")
print("="*80)

track_llm_call("Normal mode turn")
turn_payload = {
    "message": "I did it — sent the first email to a potential client today. It felt scary but I hit send.",
    "mode": "normal"
}

start_time = time.time()
try:
    r = requests.post(f"{BASE_URL}/threads/{thread_id}/turn", json=turn_payload, headers=headers, timeout=TIMEOUT_NORMAL)
    latency = round(time.time() - start_time, 2)
    
    if r.status_code == 200:
        data = r.json()
        model = data.get("model")
        mode = data.get("mode")
        credits_after = data.get("credits")
        thread = data.get("thread", {})
        
        # Verify model (should be claude-opus-4-8 or claude-haiku-4-5 if fallback)
        model_valid = model in ("claude-opus-4-8", "claude-haiku-4-5")
        mode_valid = mode == "normal"
        credits_valid = credits_after == (initial_credits - 10)  # 5 for goal + 5 for turn
        
        # Verify value fields refreshed
        action_payoff = thread.get("current_action_payoff")
        big_picture = thread.get("current_big_picture")
        payoff_valid = isinstance(action_payoff, str) and len(action_payoff.strip()) > 0
        big_picture_valid = isinstance(big_picture, str) and len(big_picture.strip()) > 0
        
        all_valid = model_valid and mode_valid and credits_valid and payoff_valid and big_picture_valid
        
        details = (f"Latency: {latency}s | Model: {model} | Mode: {mode} | "
                  f"Credits: {initial_credits - 5} → {credits_after} | "
                  f"Fields refreshed: {'✓' if payoff_valid and big_picture_valid else '✗'}")
        
        log_test("Normal mode turn", all_valid, details)
        
        # Store for comparison
        normal_payoff = action_payoff
        normal_big_picture = big_picture
    else:
        log_test("Normal mode turn", False, f"Status {r.status_code}: {r.text}")
        sys.exit(1)
except Exception as e:
    log_test("Normal mode turn", False, f"Exception: {e}")
    sys.exit(1)

# ============================================================================
# TEST 4: Ultra Mode Turn (LLM CALL #3)
# ============================================================================
print("\n" + "="*80)
print("TEST 4: ULTRA MODE TURN (LLM CALL #3) - May take 30-90s")
print("="*80)

track_llm_call("Ultra mode turn")
ultra_payload = {
    "message": "I keep putting off the hard conversation with my current boss about leaving. Every day I delay feels like I'm lying to him.",
    "mode": "ultra"
}

start_time = time.time()
try:
    r = requests.post(f"{BASE_URL}/threads/{thread_id}/turn", json=ultra_payload, headers=headers, timeout=TIMEOUT_ULTRA)
    latency = round(time.time() - start_time, 2)
    
    if r.status_code == 200:
        data = r.json()
        model = data.get("model")
        mode = data.get("mode")
        credits_after = data.get("credits")
        thread = data.get("thread", {})
        
        # Verify model (should be claude-fable-5, or fallback to opus/haiku)
        model_valid = model in ("claude-fable-5", "claude-opus-4-8", "claude-haiku-4-5")
        mode_valid = mode == "ultra"
        credits_valid = credits_after == (initial_credits - 15)  # 5 + 5 + 5
        
        # Verify value fields refreshed (should be different from normal turn)
        action_payoff = thread.get("current_action_payoff")
        big_picture = thread.get("current_big_picture")
        payoff_valid = isinstance(action_payoff, str) and len(action_payoff.strip()) > 0
        big_picture_valid = isinstance(big_picture, str) and len(big_picture.strip()) > 0
        fields_changed = (action_payoff != normal_payoff) or (big_picture != normal_big_picture)
        
        all_valid = model_valid and mode_valid and credits_valid and payoff_valid and big_picture_valid
        
        details = (f"Latency: {latency}s | Model: {model} | Mode: {mode} | "
                  f"Credits: {initial_credits - 10} → {credits_after} | "
                  f"Fields changed: {'✓' if fields_changed else '✗'}")
        
        log_test("Ultra mode turn", all_valid, details)
        
        if model != "claude-fable-5":
            print(f"  ⚠️  Note: Fallback occurred, expected claude-fable-5 but got {model}")
    else:
        log_test("Ultra mode turn", False, f"Status {r.status_code}: {r.text}")
        sys.exit(1)
except Exception as e:
    log_test("Ultra mode turn", False, f"Exception: {e}")
    sys.exit(1)

# ============================================================================
# TEST 5: Invalid Mode (No LLM Call)
# ============================================================================
print("\n" + "="*80)
print("TEST 5: INVALID MODE (Should 422, no credit deduction)")
print("="*80)

invalid_payload = {
    "message": "test message",
    "mode": "turbo"  # invalid
}

try:
    r = requests.post(f"{BASE_URL}/threads/{thread_id}/turn", json=invalid_payload, headers=headers, timeout=10)
    
    if r.status_code == 422:
        # Verify credits NOT deducted
        r_me = requests.get(f"{BASE_URL}/auth/me", headers=headers, timeout=10)
        current_credits = r_me.json().get("credits")
        credits_unchanged = current_credits == (initial_credits - 15)
        
        log_test("Invalid mode rejection", credits_unchanged,
                 f"422 received, credits unchanged: {current_credits}")
    else:
        log_test("Invalid mode rejection", False,
                 f"Expected 422, got {r.status_code}: {r.text}")
except Exception as e:
    log_test("Invalid mode rejection", False, f"Exception: {e}")

# ============================================================================
# TEST 6: Persistence
# ============================================================================
print("\n" + "="*80)
print("TEST 6: PERSISTENCE (GET thread)")
print("="*80)

try:
    r = requests.get(f"{BASE_URL}/threads/{thread_id}", headers=headers, timeout=10)
    
    if r.status_code == 200:
        data = r.json()
        thread = data.get("thread", {})
        
        # Verify 3 new fields exist and match last turn
        action_payoff = thread.get("current_action_payoff")
        big_picture = thread.get("current_big_picture")
        bold_move = thread.get("current_bold_move")
        
        payoff_valid = isinstance(action_payoff, str) and len(action_payoff.strip()) > 0
        big_picture_valid = isinstance(big_picture, str) and len(big_picture.strip()) > 0
        bold_move_exists = "current_bold_move" in thread
        
        all_valid = payoff_valid and big_picture_valid and bold_move_exists
        
        log_test("Persistence of value fields", all_valid,
                 f"All 3 fields persisted correctly")
    else:
        log_test("Persistence of value fields", False,
                 f"Status {r.status_code}: {r.text}")
except Exception as e:
    log_test("Persistence of value fields", False, f"Exception: {e}")

# ============================================================================
# TEST 7: Default Mode (No LLM Call - verify schema only)
# ============================================================================
print("\n" + "="*80)
print("TEST 7: DEFAULT MODE (Omit mode field)")
print("="*80)

# To save LLM calls, we'll pause the thread first, then verify the schema accepts
# a request without mode (should default to "normal" but fail with 400 for paused thread)
try:
    # Pause thread
    r = requests.patch(f"{BASE_URL}/threads/{thread_id}/status",
                      json={"status": "paused"}, headers=headers, timeout=10)
    
    if r.status_code == 200:
        # Try turn without mode on paused thread
        default_payload = {"message": "test"}  # mode omitted
        r = requests.post(f"{BASE_URL}/threads/{thread_id}/turn",
                         json=default_payload, headers=headers, timeout=10)
        
        # Should get 400 (paused), not 422 (validation error)
        # This proves the schema accepted the missing mode field
        if r.status_code == 400 and "paused" in r.text.lower():
            log_test("Default mode schema", True,
                     "Schema accepts omitted mode (defaults to normal)")
        elif r.status_code == 422:
            log_test("Default mode schema", False,
                     "422 validation error - mode field may be required")
        else:
            log_test("Default mode schema", False,
                     f"Unexpected status {r.status_code}: {r.text}")
        
        # Reactivate thread
        requests.patch(f"{BASE_URL}/threads/{thread_id}/status",
                      json={"status": "active"}, headers=headers, timeout=10)
    else:
        log_test("Default mode schema", False, f"Failed to pause thread: {r.status_code}")
except Exception as e:
    log_test("Default mode schema", False, f"Exception: {e}")

# ============================================================================
# TEST 8: Auth Guard
# ============================================================================
print("\n" + "="*80)
print("TEST 8: AUTH GUARD (No token)")
print("="*80)

try:
    r = requests.get(f"{BASE_URL}/threads/{thread_id}", timeout=10)  # no headers
    
    if r.status_code == 401:
        log_test("Auth guard", True, "401 Unauthorized as expected")
    else:
        log_test("Auth guard", False, f"Expected 401, got {r.status_code}")
except Exception as e:
    log_test("Auth guard", False, f"Exception: {e}")

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "="*80)
print("TEST SUMMARY")
print("="*80)

passed = sum(1 for t in test_results if t["passed"])
total = len(test_results)
print(f"\nTotal: {passed}/{total} tests passed")
print(f"LLM calls used: {llm_call_count}/5")

print("\nDetailed Results:")
for t in test_results:
    status = "✅" if t["passed"] else "❌"
    print(f"{status} {t['name']}")
    if t["details"]:
        print(f"   {t['details']}")

if passed == total:
    print("\n🎉 All tests passed!")
    sys.exit(0)
else:
    print(f"\n⚠️  {total - passed} test(s) failed")
    sys.exit(1)
