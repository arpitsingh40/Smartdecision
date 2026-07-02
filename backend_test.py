#!/usr/bin/env python3
"""
Backend test for Founder Journey Phase 2 endpoints.
Tests: /api/journey/direction, /direction/refine, /direction/approve, /milestones/{id}/status

STRICT LLM BUDGET: <= 5 LLM-spending calls total
"""
import requests
import json
import time
import sys

# Base URL from frontend/.env
BASE_URL = "https://founder-strategy-3.preview.emergentagent.com/api"

# Track LLM calls
llm_call_count = 0
max_llm_calls = 5

def log(msg):
    print(f"[TEST] {msg}")

def signup_fresh_user():
    """Create a fresh signup user (50 credits)."""
    email = f"journey_phase2_{int(time.time())}@cloudkitchen.com"
    password = "TestJourney@2026"
    
    resp = requests.post(f"{BASE_URL}/auth/signup", json={
        "email": email,
        "password": password,
        "name": "Pune Kitchen Owner"
    })
    
    if resp.status_code != 200:
        log(f"❌ Signup failed: {resp.status_code} {resp.text}")
        sys.exit(1)
    
    data = resp.json()
    token = data["token"]
    credits = data["user"]["credits"]
    
    log(f"✅ Fresh signup: {email}, credits={credits}")
    
    # Save credentials to test_credentials.md
    with open("/app/memory/test_credentials.md", "a") as f:
        f.write(f"\n## Journey Phase 2 Test User\n")
        f.write(f"- Email: {email}\n")
        f.write(f"- Password: {password}\n")
        f.write(f"- Created: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    return token, email, credits

def get_credits(token):
    """Get current credit balance."""
    resp = requests.get(f"{BASE_URL}/journey", headers={"Authorization": f"Bearer {token}"})
    if resp.status_code == 200:
        return resp.json().get("credits", 0)
    return None

def test_setup(token):
    """SETUP (2 LLM): start journey + message."""
    global llm_call_count
    
    log("\n=== SETUP PHASE (2 LLM calls) ===")
    
    # LLM CALL #1: POST /api/journey/start
    log("LLM CALL #1: POST /api/journey/start")
    credits_before = get_credits(token)
    
    resp = requests.post(f"{BASE_URL}/journey/start", 
        headers={"Authorization": f"Bearer {token}"},
        json={
            "objective": "Grow my Pune cloud kitchen from 6L to 25L monthly in 12 months, I run all ops myself, no marketing, no SOPs, cash is tight."
        })
    
    if resp.status_code != 200:
        log(f"❌ /journey/start failed: {resp.status_code} {resp.text}")
        return False
    
    data = resp.json()
    llm_call_count += 1
    credits_after = data.get("credits", 0)
    cost = data.get("cost", 0)
    
    log(f"✅ Journey started: cost={cost}, credits {credits_before} -> {credits_after}")
    log(f"   Stage: {data.get('stage')}, Started: {data.get('started')}, Confidence: {data.get('confidence')}")
    
    # LLM CALL #2: POST /api/journey/message
    log("\nLLM CALL #2: POST /api/journey/message")
    credits_before = credits_after
    
    resp = requests.post(f"{BASE_URL}/journey/message",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "I do about 700 orders a month at ~350 average order value, mostly on Swiggy and Zomato, and I'm scared to spend on ads."
        })
    
    if resp.status_code != 200:
        log(f"❌ /journey/message failed: {resp.status_code} {resp.text}")
        return False
    
    data = resp.json()
    llm_call_count += 1
    credits_after = data.get("credits", 0)
    cost = data.get("cost", 0)
    
    log(f"✅ Message sent: cost={cost}, credits {credits_before} -> {credits_after}")
    log(f"   Confidence: {data.get('confidence')}, Messages: {len(data.get('messages', []))}")
    
    log(f"\n📊 LLM calls used: {llm_call_count}/{max_llm_calls}")
    return True

def test_direction(token):
    """DIRECTION (1 LLM): POST /api/journey/direction."""
    global llm_call_count
    
    log("\n=== DIRECTION PHASE (1 LLM call) ===")
    log("LLM CALL #3: POST /api/journey/direction")
    
    credits_before = get_credits(token)
    
    resp = requests.post(f"{BASE_URL}/journey/direction",
        headers={"Authorization": f"Bearer {token}"})
    
    if resp.status_code != 200:
        log(f"❌ /journey/direction failed: {resp.status_code} {resp.text}")
        return False, None
    
    data = resp.json()
    llm_call_count += 1
    credits_after = data.get("credits", 0)
    cost = data.get("cost", 0)
    
    log(f"✅ Direction created: cost={cost}, credits {credits_before} -> {credits_after}")
    
    # Validate response structure
    direction = data.get("direction")
    if not direction:
        log(f"❌ No direction in response")
        return False, None
    
    # Check all required fields
    required_fields = ["goal", "blockers", "highest_leverage", "success_probability", 
                      "probability_rationale", "risks", "missing_info"]
    
    missing = [f for f in required_fields if f not in direction]
    if missing:
        log(f"❌ Missing fields in direction: {missing}")
        return False, None
    
    # Validate field types and values
    goal = direction.get("goal", "")
    blockers = direction.get("blockers", [])
    highest_leverage = direction.get("highest_leverage", "")
    success_probability = direction.get("success_probability")
    probability_rationale = direction.get("probability_rationale", "")
    risks = direction.get("risks", [])
    missing_info = direction.get("missing_info", [])
    
    log(f"   Goal: {goal[:80]}...")
    log(f"   Blockers: {len(blockers)} items")
    log(f"   Highest leverage: {highest_leverage[:60]}...")
    log(f"   Success probability: {success_probability}%")
    log(f"   Probability rationale: {probability_rationale[:60]}...")
    log(f"   Risks: {len(risks)} items")
    log(f"   Missing info: {len(missing_info)} items")
    
    # Assertions
    errors = []
    
    if not goal:
        errors.append("goal is empty")
    
    if not isinstance(blockers, list) or len(blockers) < 2 or len(blockers) > 5:
        errors.append(f"blockers must be list of 2-5 items, got {len(blockers)}")
    
    if not highest_leverage:
        errors.append("highest_leverage is empty")
    
    if not isinstance(success_probability, int) or success_probability < 0 or success_probability > 100:
        errors.append(f"success_probability must be int 0-100, got {success_probability}")
    
    if not probability_rationale:
        errors.append("probability_rationale is empty")
    
    if not isinstance(risks, list) or len(risks) < 2 or len(risks) > 5:
        errors.append(f"risks must be list of 2-5 items, got {len(risks)}")
    
    if not isinstance(missing_info, list) or len(missing_info) < 2 or len(missing_info) > 5:
        errors.append(f"missing_info must be list of 2-5 items, got {len(missing_info)}")
    
    # Check stage and has_direction
    stage = data.get("stage")
    has_direction = data.get("has_direction")
    
    if stage != "refine":
        errors.append(f"stage should be 'refine', got '{stage}'")
    
    if not has_direction:
        errors.append("has_direction should be true")
    
    # Check cost >= 1
    if cost < 1:
        errors.append(f"cost should be >= 1, got {cost}")
    
    # Check credits dropped
    if credits_after >= credits_before:
        errors.append(f"credits should have dropped, {credits_before} -> {credits_after}")
    
    if errors:
        log(f"❌ Direction validation errors:")
        for err in errors:
            log(f"   - {err}")
        return False, None
    
    log(f"✅ All direction assertions passed")
    log(f"\n📊 LLM calls used: {llm_call_count}/{max_llm_calls}")
    
    return True, data

def test_refine(token):
    """REFINE (1 LLM): POST /api/journey/direction/refine."""
    global llm_call_count
    
    log("\n=== REFINE PHASE (1 LLM call) ===")
    log("LLM CALL #4: POST /api/journey/direction/refine")
    
    credits_before = get_credits(token)
    
    resp = requests.post(f"{BASE_URL}/journey/direction/refine",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "feedback": "Margins are tighter than you think, closer to 12 percent, and I genuinely cannot hire for at least 3 months."
        })
    
    if resp.status_code != 200:
        log(f"❌ /journey/direction/refine failed: {resp.status_code} {resp.text}")
        return False, None
    
    data = resp.json()
    llm_call_count += 1
    credits_after = data.get("credits", 0)
    cost = data.get("cost", 0)
    
    log(f"✅ Direction refined: cost={cost}, credits {credits_before} -> {credits_after}")
    
    # Validate response
    direction = data.get("direction")
    if not direction:
        log(f"❌ No direction in response")
        return False, None
    
    # Check all required fields still present
    required_fields = ["goal", "blockers", "highest_leverage", "success_probability", 
                      "probability_rationale", "risks", "missing_info"]
    
    missing = [f for f in required_fields if f not in direction]
    if missing:
        log(f"❌ Missing fields after refine: {missing}")
        return False, None
    
    # Check stage stays "refine"
    stage = data.get("stage")
    if stage != "refine":
        log(f"❌ Stage should stay 'refine', got '{stage}'")
        return False, None
    
    # Check credits dropped again
    if credits_after >= credits_before:
        log(f"❌ Credits should have dropped, {credits_before} -> {credits_after}")
        return False, None
    
    log(f"✅ All refine assertions passed")
    log(f"   Stage: {stage}, Cost: {cost}")
    log(f"\n📊 LLM calls used: {llm_call_count}/{max_llm_calls}")
    
    return True, data

def test_approve(token):
    """APPROVE (1 LLM): POST /api/journey/direction/approve."""
    global llm_call_count
    
    log("\n=== APPROVE PHASE (1 LLM call) ===")
    log("LLM CALL #5: POST /api/journey/direction/approve")
    
    credits_before = get_credits(token)
    
    resp = requests.post(f"{BASE_URL}/journey/direction/approve",
        headers={"Authorization": f"Bearer {token}"})
    
    if resp.status_code != 200:
        log(f"❌ /journey/direction/approve failed: {resp.status_code} {resp.text}")
        return False, None
    
    data = resp.json()
    llm_call_count += 1
    credits_after = data.get("credits", 0)
    cost = data.get("cost", 0)
    
    log(f"✅ Direction approved: cost={cost}, credits {credits_before} -> {credits_after}")
    
    # Validate milestones
    milestones = data.get("milestones", [])
    if not milestones:
        log(f"❌ No milestones in response")
        return False, None
    
    milestone_count = len(milestones)
    log(f"   Milestones: {milestone_count} items")
    
    # Check milestone count (4-10)
    if milestone_count < 4 or milestone_count > 10:
        log(f"❌ Milestone count should be 4-10, got {milestone_count}")
        return False, None
    
    # Validate each milestone structure
    required_milestone_fields = ["id", "order", "title", "success_metric", "target", "deadline", "status"]
    
    for i, m in enumerate(milestones):
        missing = [f for f in required_milestone_fields if f not in m]
        if missing:
            log(f"❌ Milestone {i+1} missing fields: {missing}")
            return False, None
        
        # Check status is "not_started"
        if m.get("status") != "not_started":
            log(f"❌ Milestone {i+1} status should be 'not_started', got '{m.get('status')}'")
            return False, None
        
        log(f"   M{i+1}: {m.get('title')[:50]}... (status={m.get('status')})")
    
    # Check stage is "milestones"
    stage = data.get("stage")
    if stage != "milestones":
        log(f"❌ Stage should be 'milestones', got '{stage}'")
        return False, None
    
    # Check unlocks.milestones is true
    unlocks = data.get("unlocks", {})
    if not unlocks.get("milestones"):
        log(f"❌ unlocks.milestones should be true")
        return False, None
    
    # Check progress_pct is 0
    progress_pct = data.get("progress_pct", -1)
    if progress_pct != 0:
        log(f"❌ progress_pct should be 0, got {progress_pct}")
        return False, None
    
    # Check cost >= 1
    if cost < 1:
        log(f"❌ cost should be >= 1, got {cost}")
        return False, None
    
    log(f"✅ All approve assertions passed")
    log(f"   Stage: {stage}, Unlocks.milestones: {unlocks.get('milestones')}, Progress: {progress_pct}%")
    log(f"\n📊 LLM calls used: {llm_call_count}/{max_llm_calls}")
    
    return True, data

def test_free_milestone_status(token, milestones):
    """FREE TESTS: milestone status updates."""
    log("\n=== FREE TESTS: Milestone Status (0 LLM) ===")
    
    if not milestones or len(milestones) == 0:
        log(f"❌ No milestones to test")
        return False
    
    first_milestone = milestones[0]
    milestone_id = first_milestone.get("id")
    total_milestones = len(milestones)
    
    log(f"Testing with milestone: {first_milestone.get('title')[:50]}...")
    
    # TEST 1: Set status to "done"
    log("\nTEST 1: POST /milestones/{id}/status with status='done'")
    
    resp = requests.post(f"{BASE_URL}/journey/milestones/{milestone_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "done"})
    
    if resp.status_code != 200:
        log(f"❌ Failed: {resp.status_code} {resp.text}")
        return False
    
    data = resp.json()
    progress_pct = data.get("progress_pct", 0)
    expected_progress = round(100 / total_milestones)
    
    # Find the milestone in response
    updated_milestone = None
    for m in data.get("milestones", []):
        if m.get("id") == milestone_id:
            updated_milestone = m
            break
    
    if not updated_milestone:
        log(f"❌ Milestone not found in response")
        return False
    
    if updated_milestone.get("status") != "done":
        log(f"❌ Milestone status should be 'done', got '{updated_milestone.get('status')}'")
        return False
    
    if progress_pct <= 0:
        log(f"❌ progress_pct should be > 0, got {progress_pct}")
        return False
    
    log(f"✅ Status set to 'done': progress_pct={progress_pct}% (expected ~{expected_progress}%)")
    
    # TEST 2: Set status to "in_progress"
    log("\nTEST 2: POST /milestones/{id}/status with status='in_progress'")
    
    resp = requests.post(f"{BASE_URL}/journey/milestones/{milestone_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "in_progress"})
    
    if resp.status_code != 200:
        log(f"❌ Failed: {resp.status_code} {resp.text}")
        return False
    
    data = resp.json()
    progress_pct = data.get("progress_pct", -1)
    
    # Find the milestone
    updated_milestone = None
    for m in data.get("milestones", []):
        if m.get("id") == milestone_id:
            updated_milestone = m
            break
    
    if updated_milestone.get("status") != "in_progress":
        log(f"❌ Milestone status should be 'in_progress', got '{updated_milestone.get('status')}'")
        return False
    
    if progress_pct != 0:
        log(f"❌ progress_pct should be 0 (no done milestones), got {progress_pct}")
        return False
    
    log(f"✅ Status set to 'in_progress': progress_pct={progress_pct}%")
    
    # TEST 3: Invalid status "bogus"
    log("\nTEST 3: POST /milestones/{id}/status with status='bogus' (should 422)")
    
    resp = requests.post(f"{BASE_URL}/journey/milestones/{milestone_id}/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "bogus"})
    
    if resp.status_code != 422:
        log(f"❌ Should return 422, got {resp.status_code}")
        return False
    
    log(f"✅ Invalid status correctly rejected with 422")
    
    # TEST 4: Non-existent milestone ID
    log("\nTEST 4: POST /milestones/does-not-exist/status (should 404)")
    
    resp = requests.post(f"{BASE_URL}/journey/milestones/does-not-exist/status",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "done"})
    
    if resp.status_code != 404:
        log(f"❌ Should return 404, got {resp.status_code}")
        return False
    
    log(f"✅ Non-existent milestone correctly rejected with 404")
    
    log(f"\n✅ All free milestone status tests passed")
    return True

def test_free_fresh_user_validations():
    """FREE TESTS: Fresh user without journey started."""
    log("\n=== FREE TESTS: Fresh User Validations (0 LLM) ===")
    
    # Create a separate fresh user
    email = f"journey_fresh_{int(time.time())}@test.com"
    password = "TestFresh@2026"
    
    resp = requests.post(f"{BASE_URL}/auth/signup", json={
        "email": email,
        "password": password,
        "name": "Fresh User"
    })
    
    if resp.status_code != 200:
        log(f"❌ Fresh user signup failed: {resp.status_code}")
        return False
    
    token = resp.json()["token"]
    log(f"✅ Created fresh user: {email}")
    
    # TEST 1: POST /direction without journey started (should 400)
    log("\nTEST 1: POST /journey/direction without journey started (should 400)")
    
    resp = requests.post(f"{BASE_URL}/journey/direction",
        headers={"Authorization": f"Bearer {token}"})
    
    if resp.status_code != 400:
        log(f"❌ Should return 400, got {resp.status_code}")
        return False
    
    log(f"✅ Correctly rejected with 400")
    
    # TEST 2: POST /direction/refine without journey started (should 400)
    log("\nTEST 2: POST /journey/direction/refine without journey started (should 400)")
    
    resp = requests.post(f"{BASE_URL}/journey/direction/refine",
        headers={"Authorization": f"Bearer {token}"},
        json={"feedback": "test"})
    
    if resp.status_code != 400:
        log(f"❌ Should return 400, got {resp.status_code}")
        return False
    
    log(f"✅ Correctly rejected with 400")
    
    # TEST 3: POST /direction/approve without journey started (should 400)
    log("\nTEST 3: POST /journey/direction/approve without journey started (should 400)")
    
    resp = requests.post(f"{BASE_URL}/journey/direction/approve",
        headers={"Authorization": f"Bearer {token}"})
    
    if resp.status_code != 400:
        log(f"❌ Should return 400, got {resp.status_code}")
        return False
    
    log(f"✅ Correctly rejected with 400")
    
    log(f"\n✅ All fresh user validation tests passed")
    return True

def test_free_refine_validation(token):
    """FREE TEST: POST /direction/refine with empty feedback (should 422)."""
    log("\n=== FREE TEST: Refine Validation (0 LLM) ===")
    log("TEST: POST /journey/direction/refine with empty feedback (should 422)")
    
    resp = requests.post(f"{BASE_URL}/journey/direction/refine",
        headers={"Authorization": f"Bearer {token}"},
        json={"feedback": ""})
    
    if resp.status_code != 422:
        log(f"❌ Should return 422, got {resp.status_code}")
        return False
    
    log(f"✅ Empty feedback correctly rejected with 422")
    return True

def main():
    log("=" * 80)
    log("FOUNDER JOURNEY PHASE 2 BACKEND TEST")
    log("LLM BUDGET: <= 5 calls")
    log("=" * 80)
    
    # Create fresh user
    token, email, initial_credits = signup_fresh_user()
    log(f"Initial credits: {initial_credits}")
    
    # SETUP (2 LLM)
    if not test_setup(token):
        log("\n❌ SETUP FAILED")
        sys.exit(1)
    
    # DIRECTION (1 LLM)
    success, direction_data = test_direction(token)
    if not success:
        log("\n❌ DIRECTION FAILED")
        sys.exit(1)
    
    # REFINE (1 LLM)
    success, refine_data = test_refine(token)
    if not success:
        log("\n❌ REFINE FAILED")
        sys.exit(1)
    
    # APPROVE (1 LLM)
    success, approve_data = test_approve(token)
    if not success:
        log("\n❌ APPROVE FAILED")
        sys.exit(1)
    
    # Get milestones for free tests
    milestones = approve_data.get("milestones", [])
    
    # FREE TESTS: Milestone status
    if not test_free_milestone_status(token, milestones):
        log("\n❌ FREE MILESTONE STATUS TESTS FAILED")
        sys.exit(1)
    
    # FREE TESTS: Fresh user validations
    if not test_free_fresh_user_validations():
        log("\n❌ FREE FRESH USER TESTS FAILED")
        sys.exit(1)
    
    # FREE TEST: Refine validation
    if not test_free_refine_validation(token):
        log("\n❌ FREE REFINE VALIDATION TEST FAILED")
        sys.exit(1)
    
    # Final summary
    log("\n" + "=" * 80)
    log("FINAL SUMMARY")
    log("=" * 80)
    
    final_credits = get_credits(token)
    credits_used = initial_credits - final_credits
    
    log(f"✅ ALL TESTS PASSED")
    log(f"📊 Total LLM calls: {llm_call_count}/{max_llm_calls}")
    log(f"💰 Credits: {initial_credits} -> {final_credits} (used {credits_used})")
    log(f"👤 Test user: {email}")
    
    # Check for 502 errors (would have failed earlier, but confirm)
    log(f"✅ NO 502 errors occurred (live Anthropic key working)")
    
    log("\n" + "=" * 80)
    log("TEST COMPLETE")
    log("=" * 80)

if __name__ == "__main__":
    main()
