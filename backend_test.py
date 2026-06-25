#!/usr/bin/env python3
"""
Backend test for Goal Setup + Goal->Progress tracker (features a+b).
Tests GET/POST /api/org/progress and goal_progress in /api/org/cockpit.
NO LLM calls, fully free testing.
"""
import requests
import time

# Backend URL from frontend/.env
BASE_URL = "https://e0d30486-7fce-4935-8c1e-6768bee14aa5.preview.emergentagent.com/api"

# Test credentials
FOUNDER_EMAIL = "ceo@smartdecigen.com"
FOUNDER_PASSWORD = "FounderOS@2026"

# Track LLM calls (should be 0)
llm_calls_used = 0

def login(email, password):
    """Login and return token."""
    resp = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        print(f"❌ Login failed for {email}: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    return data.get("token")

def signup_and_join(org_code):
    """Create a fresh member account and join org."""
    import random
    email = f"member_{random.randint(10000, 99999)}@test.com"
    password = "Member1234!"
    
    # Signup
    resp = requests.post(f"{BASE_URL}/auth/signup", json={
        "name": "Test Member",
        "email": email,
        "password": password
    })
    if resp.status_code != 200:
        print(f"❌ Signup failed: {resp.status_code} {resp.text}")
        return None, None
    
    data = resp.json()
    token = data.get("token")
    
    # Join org
    resp = requests.post(f"{BASE_URL}/org/join", 
                        json={"code": org_code},
                        headers={"Authorization": f"Bearer {token}"})
    if resp.status_code != 200:
        print(f"❌ Join org failed: {resp.status_code} {resp.text}")
        return None, None
    
    return email, token

def test_1_get_progress_owner():
    """TEST 1: GET /api/org/progress (owner) -> 200 with goal_progress payload."""
    print("\n" + "="*80)
    print("TEST 1: GET /api/org/progress (owner)")
    print("="*80)
    
    token = login(FOUNDER_EMAIL, FOUNDER_PASSWORD)
    if not token:
        return False
    
    resp = requests.get(f"{BASE_URL}/org/progress", 
                       headers={"Authorization": f"Bearer {token}"})
    
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"❌ FAIL: Expected 200, got {resp.status_code}")
        print(f"Response: {resp.text}")
        return False
    
    data = resp.json()
    print(f"Response: {data}")
    
    # Check goal_progress key exists
    if "goal_progress" not in data:
        print("❌ FAIL: Missing 'goal_progress' key")
        return False
    
    gp = data["goal_progress"]
    if gp is None:
        print("❌ FAIL: goal_progress is None (org may not have target_arr set)")
        return False
    
    # Check required fields
    required_fields = ["north_star", "target", "deadline", "current_arr", "target_arr", 
                      "remaining", "progress_pct", "gap_pct", "status", "history", "note"]
    for field in required_fields:
        if field not in gp:
            print(f"❌ FAIL: Missing field '{field}' in goal_progress")
            return False
    
    # Check progress_pct calculation
    current_arr = gp["current_arr"]
    target_arr = gp["target_arr"]
    progress_pct = gp["progress_pct"]
    expected_pct = round(100 * current_arr / target_arr)
    
    print(f"current_arr: {current_arr}")
    print(f"target_arr: {target_arr}")
    print(f"progress_pct: {progress_pct}")
    print(f"expected_pct: {expected_pct}")
    print(f"status: {gp['status']}")
    
    if progress_pct != expected_pct:
        print(f"❌ FAIL: progress_pct mismatch. Expected {expected_pct}, got {progress_pct}")
        return False
    
    # Check status label for 25% progress
    if current_arr == 250000000 and target_arr == 1000000000:
        if gp["status"] != "Building momentum":
            print(f"❌ FAIL: Expected status 'Building momentum' for 25%, got '{gp['status']}'")
            return False
    
    print("✅ PASS: GET /api/org/progress returns correct goal_progress payload")
    return True

def test_2_post_progress_update():
    """TEST 2: POST /api/org/progress with new current_arr -> updates progress, history grows."""
    print("\n" + "="*80)
    print("TEST 2: POST /api/org/progress (update current_arr)")
    print("="*80)
    
    token = login(FOUNDER_EMAIL, FOUNDER_PASSWORD)
    if not token:
        return False
    
    # Get initial state
    resp = requests.get(f"{BASE_URL}/org/progress", 
                       headers={"Authorization": f"Bearer {token}"})
    if resp.status_code != 200:
        print(f"❌ FAIL: Could not get initial state")
        return False
    
    initial_data = resp.json()
    initial_gp = initial_data["goal_progress"]
    initial_history_len = len(initial_gp["history"])
    print(f"Initial history length: {initial_history_len}")
    print(f"Initial current_arr: {initial_gp['current_arr']}")
    print(f"Initial progress_pct: {initial_gp['progress_pct']}")
    
    # Update with a NEW distinct value
    new_current_arr = 400000000  # 40% of 1B
    resp = requests.post(f"{BASE_URL}/org/progress",
                        json={"current_arr": new_current_arr},
                        headers={"Authorization": f"Bearer {token}"})
    
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"❌ FAIL: Expected 200, got {resp.status_code}")
        print(f"Response: {resp.text}")
        return False
    
    data = resp.json()
    gp = data["goal_progress"]
    
    print(f"Updated current_arr: {gp['current_arr']}")
    print(f"Updated progress_pct: {gp['progress_pct']}")
    print(f"Updated status: {gp['status']}")
    print(f"Updated history length: {len(gp['history'])}")
    
    # Check current_arr updated
    if gp["current_arr"] != new_current_arr:
        print(f"❌ FAIL: current_arr not updated. Expected {new_current_arr}, got {gp['current_arr']}")
        return False
    
    # Check progress_pct recomputed (40% of 1B = 40%)
    expected_pct = round(100 * new_current_arr / gp["target_arr"])
    if gp["progress_pct"] != expected_pct:
        print(f"❌ FAIL: progress_pct not recomputed. Expected {expected_pct}, got {gp['progress_pct']}")
        return False
    
    # Check history grew by exactly 1
    new_history_len = len(gp["history"])
    if new_history_len != initial_history_len + 1:
        print(f"❌ FAIL: history length should grow by 1. Expected {initial_history_len + 1}, got {new_history_len}")
        return False
    
    # Check status updated (40% should be "Building momentum")
    if gp["status"] != "Building momentum":
        print(f"❌ FAIL: Expected status 'Building momentum' for 40%, got '{gp['status']}'")
        return False
    
    print("✅ PASS: POST /api/org/progress updates current_arr, progress_pct, history, and status")
    
    # TEST 2b: Post SAME value again -> history should NOT grow (idempotent)
    print("\n--- TEST 2b: Idempotent check (same value) ---")
    resp = requests.post(f"{BASE_URL}/org/progress",
                        json={"current_arr": new_current_arr},
                        headers={"Authorization": f"Bearer {token}"})
    
    if resp.status_code != 200:
        print(f"❌ FAIL: Expected 200, got {resp.status_code}")
        return False
    
    data = resp.json()
    gp = data["goal_progress"]
    
    print(f"History length after duplicate post: {len(gp['history'])}")
    
    if len(gp["history"]) != new_history_len:
        print(f"❌ FAIL: history should NOT grow on duplicate value. Expected {new_history_len}, got {len(gp['history'])}")
        return False
    
    print("✅ PASS: Idempotent - posting same value does NOT grow history")
    return True

def test_3_validation():
    """TEST 3: Validation - negative current_arr -> 422, missing current_arr -> 422."""
    print("\n" + "="*80)
    print("TEST 3: Validation tests")
    print("="*80)
    
    token = login(FOUNDER_EMAIL, FOUNDER_PASSWORD)
    if not token:
        return False
    
    # Test negative current_arr
    print("\n--- TEST 3a: Negative current_arr ---")
    resp = requests.post(f"{BASE_URL}/org/progress",
                        json={"current_arr": -5},
                        headers={"Authorization": f"Bearer {token}"})
    
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 422:
        print(f"❌ FAIL: Expected 422 for negative current_arr, got {resp.status_code}")
        return False
    
    print("✅ PASS: Negative current_arr returns 422")
    
    # Test missing current_arr
    print("\n--- TEST 3b: Missing current_arr ---")
    resp = requests.post(f"{BASE_URL}/org/progress",
                        json={},
                        headers={"Authorization": f"Bearer {token}"})
    
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 422:
        print(f"❌ FAIL: Expected 422 for missing current_arr, got {resp.status_code}")
        return False
    
    print("✅ PASS: Missing current_arr returns 422")
    return True

def test_4_authorization():
    """TEST 4: Authorization - member GET/POST -> 403, no token -> 401."""
    print("\n" + "="*80)
    print("TEST 4: Authorization tests")
    print("="*80)
    
    # First, get an invite code from founder
    founder_token = login(FOUNDER_EMAIL, FOUNDER_PASSWORD)
    if not founder_token:
        return False
    
    resp = requests.post(f"{BASE_URL}/org/invites",
                        json={},
                        headers={"Authorization": f"Bearer {founder_token}"})
    if resp.status_code != 200:
        print(f"❌ FAIL: Could not create invite: {resp.status_code}")
        return False
    
    invite_code = resp.json()["code"]
    print(f"Created invite code: {invite_code}")
    
    # Create and join as member
    member_email, member_token = signup_and_join(invite_code)
    if not member_token:
        return False
    
    print(f"Created member: {member_email}")
    
    # Test member GET /api/org/progress -> 403
    print("\n--- TEST 4a: Member GET /api/org/progress ---")
    resp = requests.get(f"{BASE_URL}/org/progress",
                       headers={"Authorization": f"Bearer {member_token}"})
    
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 403:
        print(f"❌ FAIL: Expected 403 for member GET, got {resp.status_code}")
        return False
    
    print("✅ PASS: Member GET /api/org/progress returns 403")
    
    # Test member POST /api/org/progress -> 403
    print("\n--- TEST 4b: Member POST /api/org/progress ---")
    resp = requests.post(f"{BASE_URL}/org/progress",
                        json={"current_arr": 500000000},
                        headers={"Authorization": f"Bearer {member_token}"})
    
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 403:
        print(f"❌ FAIL: Expected 403 for member POST, got {resp.status_code}")
        return False
    
    print("✅ PASS: Member POST /api/org/progress returns 403")
    
    # Test no token GET -> 401
    print("\n--- TEST 4c: No token GET /api/org/progress ---")
    resp = requests.get(f"{BASE_URL}/org/progress")
    
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 401:
        print(f"❌ FAIL: Expected 401 for no token GET, got {resp.status_code}")
        return False
    
    print("✅ PASS: No token GET /api/org/progress returns 401")
    
    # Test no token POST -> 401
    print("\n--- TEST 4d: No token POST /api/org/progress ---")
    resp = requests.post(f"{BASE_URL}/org/progress",
                        json={"current_arr": 500000000})
    
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 401:
        print(f"❌ FAIL: Expected 401 for no token POST, got {resp.status_code}")
        return False
    
    print("✅ PASS: No token POST /api/org/progress returns 401")
    return True

def test_5_cockpit_goal_progress():
    """TEST 5: GET /api/org/cockpit includes both goal_progress AND pacing keys."""
    print("\n" + "="*80)
    print("TEST 5: GET /api/org/cockpit (goal_progress + pacing)")
    print("="*80)
    
    token = login(FOUNDER_EMAIL, FOUNDER_PASSWORD)
    if not token:
        return False
    
    resp = requests.get(f"{BASE_URL}/org/cockpit",
                       headers={"Authorization": f"Bearer {token}"})
    
    print(f"Status: {resp.status_code}")
    
    if resp.status_code != 200:
        print(f"❌ FAIL: Expected 200, got {resp.status_code}")
        print(f"Response: {resp.text}")
        return False
    
    data = resp.json()
    
    # Check goal_progress key exists
    if "goal_progress" not in data:
        print("❌ FAIL: Missing 'goal_progress' key in cockpit")
        return False
    
    gp = data["goal_progress"]
    if gp is None:
        print("❌ FAIL: goal_progress is None")
        return False
    
    print(f"goal_progress present: {list(gp.keys())}")
    
    # Check pacing key exists (backward compatibility)
    if "pacing" not in data:
        print("❌ FAIL: Missing 'pacing' key in cockpit (backward compatibility)")
        return False
    
    pacing = data["pacing"]
    if pacing is None:
        print("❌ FAIL: pacing is None")
        return False
    
    print(f"pacing present: {list(pacing.keys())}")
    
    # Check pacing.gap_pct exists
    if "gap_pct" not in pacing:
        print("❌ FAIL: Missing 'gap_pct' in pacing")
        return False
    
    print(f"pacing.gap_pct: {pacing['gap_pct']}")
    
    print("✅ PASS: GET /api/org/cockpit includes both goal_progress and pacing keys")
    
    # Test member GET /api/org/cockpit -> 403
    print("\n--- TEST 5b: Member GET /api/org/cockpit ---")
    
    # Get member token (reuse from test 4 or create new)
    founder_token = login(FOUNDER_EMAIL, FOUNDER_PASSWORD)
    resp = requests.post(f"{BASE_URL}/org/invites",
                        json={},
                        headers={"Authorization": f"Bearer {founder_token}"})
    if resp.status_code == 200:
        invite_code = resp.json()["code"]
        member_email, member_token = signup_and_join(invite_code)
        if member_token:
            resp = requests.get(f"{BASE_URL}/org/cockpit",
                               headers={"Authorization": f"Bearer {member_token}"})
            
            print(f"Status: {resp.status_code}")
            
            if resp.status_code != 403:
                print(f"❌ FAIL: Expected 403 for member GET cockpit, got {resp.status_code}")
                return False
            
            print("✅ PASS: Member GET /api/org/cockpit returns 403")
    
    return True

def test_6_strategy_version_stability():
    """TEST 6: CRITICAL - strategy_version must NOT change after POST /api/org/progress."""
    print("\n" + "="*80)
    print("TEST 6: Strategy version stability")
    print("="*80)
    
    token = login(FOUNDER_EMAIL, FOUNDER_PASSWORD)
    if not token:
        return False
    
    # Get initial strategy_version
    print("\n--- TEST 6a: Capture initial strategy_version ---")
    resp = requests.get(f"{BASE_URL}/org/strategy",
                       headers={"Authorization": f"Bearer {token}"})
    
    if resp.status_code != 200:
        print(f"❌ FAIL: Could not get strategy: {resp.status_code}")
        return False
    
    initial_strategy = resp.json()
    initial_version = initial_strategy.get("strategy_version", 0)
    print(f"Initial strategy_version: {initial_version}")
    
    # POST /api/org/progress with changed current_arr
    print("\n--- TEST 6b: POST /api/org/progress (should NOT bump version) ---")
    import random
    new_arr = 300000000 + random.randint(1000, 9999)  # Ensure it's different
    resp = requests.post(f"{BASE_URL}/org/progress",
                        json={"current_arr": new_arr},
                        headers={"Authorization": f"Bearer {token}"})
    
    if resp.status_code != 200:
        print(f"❌ FAIL: POST /progress failed: {resp.status_code}")
        return False
    
    print(f"Posted new current_arr: {new_arr}")
    
    # Get strategy_version again
    resp = requests.get(f"{BASE_URL}/org/strategy",
                       headers={"Authorization": f"Bearer {token}"})
    
    if resp.status_code != 200:
        print(f"❌ FAIL: Could not get strategy after progress update: {resp.status_code}")
        return False
    
    after_progress_strategy = resp.json()
    after_progress_version = after_progress_strategy.get("strategy_version", 0)
    print(f"Strategy_version after POST /progress: {after_progress_version}")
    
    if after_progress_version != initial_version:
        print(f"❌ FAIL: strategy_version changed after POST /progress! Expected {initial_version}, got {after_progress_version}")
        return False
    
    print("✅ PASS: strategy_version unchanged after POST /api/org/progress")
    
    # TEST 6c: PUT /api/org/strategy with changed priority should still bump version
    print("\n--- TEST 6c: PUT /api/org/strategy (should bump version) ---")
    
    # Modify priorities
    current_priorities = initial_strategy.get("priorities", [])
    new_priorities = current_priorities + [f"New priority {random.randint(1000, 9999)}"]
    
    resp = requests.put(f"{BASE_URL}/org/strategy",
                       json={
                           "north_star": initial_strategy.get("north_star", ""),
                           "target": initial_strategy.get("target", ""),
                           "deadline": initial_strategy.get("deadline", ""),
                           "priorities": new_priorities,
                           "decision_rules": initial_strategy.get("decision_rules", ""),
                           "current_arr": initial_strategy.get("current_arr"),
                           "target_arr": initial_strategy.get("target_arr")
                       },
                       headers={"Authorization": f"Bearer {token}"})
    
    if resp.status_code != 200:
        print(f"❌ FAIL: PUT /strategy failed: {resp.status_code}")
        return False
    
    updated_strategy = resp.json()
    updated_version = updated_strategy.get("strategy_version", 0)
    print(f"Strategy_version after PUT /strategy with changed priority: {updated_version}")
    
    if updated_version <= after_progress_version:
        print(f"❌ FAIL: strategy_version should increment after PUT /strategy. Expected > {after_progress_version}, got {updated_version}")
        return False
    
    print("✅ PASS: strategy_version increments after PUT /api/org/strategy with changed priority")
    return True

def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("GOAL SETUP + GOAL->PROGRESS BACKEND TEST SUITE")
    print("Testing features (a)+(b) - NO LLM calls")
    print("="*80)
    
    results = []
    
    # Run all tests
    results.append(("TEST 1: GET /api/org/progress (owner)", test_1_get_progress_owner()))
    results.append(("TEST 2: POST /api/org/progress (update + idempotent)", test_2_post_progress_update()))
    results.append(("TEST 3: Validation (negative/missing current_arr)", test_3_validation()))
    results.append(("TEST 4: Authorization (member 403, no token 401)", test_4_authorization()))
    results.append(("TEST 5: GET /api/org/cockpit (goal_progress + pacing)", test_5_cockpit_goal_progress()))
    results.append(("TEST 6: Strategy version stability", test_6_strategy_version_stability()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print(f"LLM calls used: {llm_calls_used} (expected: 0)")
    
    if passed == total and llm_calls_used == 0:
        print("\n🎉 ALL TESTS PASSED! Features (a)+(b) working correctly.")
        return 0
    else:
        print("\n⚠️  SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    exit(main())
