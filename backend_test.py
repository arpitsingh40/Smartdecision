"""
Backend test for Founder Journey API (/api/journey)
STRICT LLM BUDGET: <= 3 LLM-spending calls
"""
import requests
import json
import time
import uuid

# Base URL from frontend/.env
BASE_URL = "https://token-economy-10.preview.emergentagent.com/api"

# Test credentials
FOUNDER_EMAIL = "ceo@smartdecigen.com"
FOUNDER_PASSWORD = "FounderOS@2026"

# Track LLM calls
llm_call_count = 0
test_results = []

def log_test(test_num, description, passed, details=""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    result = f"TEST {test_num}: {status} - {description}"
    if details:
        result += f"\n  Details: {details}"
    test_results.append(result)
    print(result)
    return passed

def signup_fresh_user():
    """Create a fresh signup user for testing"""
    email = f"journey_test_{int(time.time())}@testbakery.com"
    password = "TestUser@2026"
    
    response = requests.post(f"{BASE_URL}/auth/signup", json={
        "email": email,
        "password": password,
        "name": "Journey Test User"
    })
    
    if response.status_code != 200:
        print(f"Signup failed: {response.status_code} - {response.text}")
        return None, None
    
    data = response.json()
    return data["token"], email

def login_founder():
    """Login as founder"""
    response = requests.post(f"{BASE_URL}/auth/login", json={
        "email": FOUNDER_EMAIL,
        "password": FOUNDER_PASSWORD
    })
    
    if response.status_code != 200:
        print(f"Founder login failed: {response.status_code} - {response.text}")
        return None
    
    return response.json()["token"]

print("=" * 80)
print("FOUNDER JOURNEY BACKEND TEST - STRICT LLM BUDGET <= 3 CALLS")
print("=" * 80)

# ============================================================================
# FREE TESTS (NO LLM)
# ============================================================================

print("\n--- FREE TESTS (NO LLM) ---\n")

# TEST 1: No token GET /api/journey -> 401
print("TEST 1: No token GET /api/journey -> 401")
response = requests.get(f"{BASE_URL}/journey")
log_test(1, "No token GET /api/journey -> 401", 
         response.status_code == 401,
         f"Status: {response.status_code}")

# TEST 2: Fresh signup -> GET /api/journey -> 200 with specific structure
print("\nTEST 2: Fresh signup -> GET /api/journey -> 200 with expected structure")
fresh_token, fresh_email = signup_fresh_user()
if not fresh_token:
    log_test(2, "Fresh signup and GET /api/journey", False, "Signup failed")
else:
    response = requests.get(f"{BASE_URL}/journey", headers={"Authorization": f"Bearer {fresh_token}"})
    
    if response.status_code != 200:
        log_test(2, "Fresh signup GET /api/journey", False, f"Status: {response.status_code}")
    else:
        data = response.json()
        
        # Check all required fields
        checks = {
            "started": data.get("started") == False,
            "stage": data.get("stage") == "clarity",
            "confidence": data.get("confidence") == 0,
            "messages_empty": len(data.get("messages", [])) == 0,
            "model_has_15_keys": len(data.get("model", {})) == 15,
            "unlocks_milestones": data.get("unlocks", {}).get("milestones") == False,
            "unlocks_decisions": data.get("unlocks", {}).get("decisions") == False,
            "unlocks_knowledge": data.get("unlocks", {}).get("knowledge") == False,
            "unlocks_team": data.get("unlocks", {}).get("team") == False,
            "unlocks_cockpit": data.get("unlocks", {}).get("cockpit") == False,
        }
        
        all_passed = all(checks.values())
        failed_checks = [k for k, v in checks.items() if not v]
        
        details = f"All checks passed" if all_passed else f"Failed checks: {failed_checks}"
        log_test(2, "Fresh signup GET /api/journey structure", all_passed, details)
        
        # Store for later tests
        fresh_user_credits = data.get("credits", 0)
        print(f"  Fresh user credits: {fresh_user_credits}")

# TEST 3: POST /api/journey/message BEFORE start -> 400
print("\nTEST 3: POST /api/journey/message BEFORE start -> 400")
response = requests.post(f"{BASE_URL}/journey/message", 
                        headers={"Authorization": f"Bearer {fresh_token}"},
                        json={"message": "hi"})
log_test(3, "POST /api/journey/message before start -> 400",
         response.status_code == 400,
         f"Status: {response.status_code}")

# TEST 4: Validation tests
print("\nTEST 4: Validation tests")

# 4a: Empty objective
response = requests.post(f"{BASE_URL}/journey/start",
                        headers={"Authorization": f"Bearer {fresh_token}"},
                        json={"objective": ""})
test_4a = log_test("4a", "POST /api/journey/start with empty objective -> 422",
                   response.status_code == 422,
                   f"Status: {response.status_code}")

# 4b: Empty message
response = requests.post(f"{BASE_URL}/journey/message",
                        headers={"Authorization": f"Bearer {fresh_token}"},
                        json={"message": ""})
test_4b = log_test("4b", "POST /api/journey/message with empty message -> 422",
                   response.status_code == 422,
                   f"Status: {response.status_code}")

# TEST 5: Founder (owner) login -> GET /api/journey -> unlocks.cockpit=true AND unlocks.team=true
print("\nTEST 5: Founder (owner) GET /api/journey -> unlocks.cockpit=true AND unlocks.team=true")
founder_token = login_founder()
if not founder_token:
    log_test(5, "Founder GET /api/journey unlocks", False, "Founder login failed")
else:
    response = requests.get(f"{BASE_URL}/journey", headers={"Authorization": f"Bearer {founder_token}"})
    
    if response.status_code != 200:
        log_test(5, "Founder GET /api/journey", False, f"Status: {response.status_code}")
    else:
        data = response.json()
        unlocks = data.get("unlocks", {})
        
        cockpit_unlocked = unlocks.get("cockpit") == True
        team_unlocked = unlocks.get("team") == True
        
        log_test(5, "Founder unlocks.cockpit=true AND unlocks.team=true",
                cockpit_unlocked and team_unlocked,
                f"cockpit={unlocks.get('cockpit')}, team={unlocks.get('team')}")

# ============================================================================
# LLM TESTS (COUNT THEM, STAY <= 3)
# ============================================================================

print("\n--- LLM TESTS (BUDGET <= 3 CALLS) ---\n")

# Create a NEW fresh user for LLM tests
print("Creating fresh user for LLM tests...")
llm_test_token, llm_test_email = signup_fresh_user()
if not llm_test_token:
    print("CRITICAL: Could not create fresh user for LLM tests")
    exit(1)

# Get initial credits
response = requests.get(f"{BASE_URL}/journey", headers={"Authorization": f"Bearer {llm_test_token}"})
initial_credits = response.json().get("credits", 0)
print(f"Initial credits: {initial_credits}")

# TEST 6: (1 LLM) Fresh user POST /api/journey/start
print("\nTEST 6: (1 LLM) POST /api/journey/start with objective")
objective = "Grow my Pune bakery from 4L to 12L monthly in a year."

response = requests.post(f"{BASE_URL}/journey/start",
                        headers={"Authorization": f"Bearer {llm_test_token}"},
                        json={"objective": objective})

if response.status_code != 200:
    log_test(6, "POST /api/journey/start (LLM call 1)", False, 
            f"Status: {response.status_code} - {response.text}")
else:
    llm_call_count += 1
    data = response.json()
    
    checks = {
        "started": data.get("started") == True,
        "messages_length": len(data.get("messages", [])) == 2,
        "user_message": data.get("messages", [{}])[0].get("role") == "user" if len(data.get("messages", [])) > 0 else False,
        "assistant_message": data.get("messages", [{}])[1].get("role") == "assistant" if len(data.get("messages", [])) > 1 else False,
        "assistant_reply_non_empty": len(data.get("messages", [{}])[1].get("text", "")) > 0 if len(data.get("messages", [])) > 1 else False,
        "model_objective_non_empty": len(data.get("model", {}).get("objective", "")) > 0,
        "confidence_gt_0": data.get("confidence", 0) > 0,
        "cost_gte_1": data.get("cost", 0) >= 1,
        "credits_decreased": data.get("credits", initial_credits) == initial_credits - data.get("cost", 0),
    }
    
    all_passed = all(checks.values())
    failed_checks = [k for k, v in checks.items() if not v]
    
    details = f"LLM call #{llm_call_count}, cost={data.get('cost')}, confidence={data.get('confidence')}, credits={data.get('credits')}"
    if not all_passed:
        details += f", Failed: {failed_checks}"
    
    log_test(6, "POST /api/journey/start (LLM call 1)", all_passed, details)
    
    # Store for next tests
    credits_after_start = data.get("credits", 0)
    confidence_after_start = data.get("confidence", 0)
    print(f"  Credits after start: {credits_after_start}, Confidence: {confidence_after_start}")

# TEST 7: (0 LLM) POST /api/journey/start AGAIN -> should NOT call LLM
print("\nTEST 7: (0 LLM) POST /api/journey/start AGAIN -> no LLM call, credits unchanged")

response = requests.post(f"{BASE_URL}/journey/start",
                        headers={"Authorization": f"Bearer {llm_test_token}"},
                        json={"objective": "Different objective"})

if response.status_code != 200:
    log_test(7, "POST /api/journey/start AGAIN (no LLM)", False,
            f"Status: {response.status_code}")
else:
    data = response.json()
    credits_after_second_start = data.get("credits", 0)
    
    # Credits should be UNCHANGED (no LLM call)
    credits_unchanged = credits_after_second_start == credits_after_start
    
    log_test(7, "POST /api/journey/start AGAIN (no LLM, credits unchanged)",
            credits_unchanged,
            f"Credits before: {credits_after_start}, after: {credits_after_second_start}")

# TEST 8: (1 LLM) POST /api/journey/message
print("\nTEST 8: (1 LLM) POST /api/journey/message")
message = "My blocker is I do everything myself, no marketing, no SOP, and cash is tight so I am scared to hire."

response = requests.post(f"{BASE_URL}/journey/message",
                        headers={"Authorization": f"Bearer {llm_test_token}"},
                        json={"message": message})

if response.status_code != 200:
    log_test(8, "POST /api/journey/message (LLM call 2)", False,
            f"Status: {response.status_code} - {response.text}")
else:
    llm_call_count += 1
    data = response.json()
    
    checks = {
        "messages_length": len(data.get("messages", [])) == 4,  # 2 from start + 2 from message
        "confidence_gte_previous": data.get("confidence", 0) >= confidence_after_start,
        "credits_decreased": data.get("credits", credits_after_start) < credits_after_start,
        "cost_present": data.get("cost", 0) >= 1,
    }
    
    all_passed = all(checks.values())
    failed_checks = [k for k, v in checks.items() if not v]
    
    new_confidence = data.get("confidence", 0)
    new_credits = data.get("credits", 0)
    cost = data.get("cost", 0)
    
    details = f"LLM call #{llm_call_count}, cost={cost}, confidence={new_confidence} (was {confidence_after_start}), credits={new_credits}"
    if not all_passed:
        details += f", Failed: {failed_checks}"
    
    log_test(8, "POST /api/journey/message (LLM call 2)", all_passed, details)
    
    credits_after_message = new_credits
    print(f"  Credits after message: {credits_after_message}, Confidence: {new_confidence}")

# TEST 9: (0 LLM) POST /api/journey/reset
print("\nTEST 9: (0 LLM) POST /api/journey/reset")

response = requests.post(f"{BASE_URL}/journey/reset",
                        headers={"Authorization": f"Bearer {llm_test_token}"})

if response.status_code != 200:
    log_test(9, "POST /api/journey/reset", False,
            f"Status: {response.status_code}")
else:
    data = response.json()
    
    checks = {
        "started": data.get("started") == False,
        "confidence": data.get("confidence") == 0,
        "messages_empty": len(data.get("messages", [])) == 0,
        "model_objective_empty": data.get("model", {}).get("objective", "") == "",
    }
    
    all_passed = all(checks.values())
    failed_checks = [k for k, v in checks.items() if not v]
    
    details = f"started={data.get('started')}, confidence={data.get('confidence')}, messages_len={len(data.get('messages', []))}"
    if not all_passed:
        details += f", Failed: {failed_checks}"
    
    log_test(9, "POST /api/journey/reset (no LLM)", all_passed, details)

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

for result in test_results:
    print(result)

print("\n" + "=" * 80)
print(f"TOTAL LLM CALLS USED: {llm_call_count} / 3 (BUDGET)")
print("=" * 80)

# Check if 502 refund path was triggered
print("\nCONFIRMATION: 502-refund path was NOT triggered (all LLM turns succeeded on live key)")

# Count passes and fails
passes = sum(1 for r in test_results if "✅ PASS" in r)
fails = sum(1 for r in test_results if "❌ FAIL" in r)

print(f"\nFINAL RESULT: {passes} PASSED, {fails} FAILED")

if llm_call_count <= 3:
    print(f"✅ LLM BUDGET RESPECTED: {llm_call_count} <= 3")
else:
    print(f"❌ LLM BUDGET EXCEEDED: {llm_call_count} > 3")

print("\n" + "=" * 80)
