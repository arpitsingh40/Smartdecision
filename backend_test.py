"""
Founder Profile Deep-Onboarding Test Suite
Tests all 4 numbered items from the review request:
1. FREE - GATING: member 403 on all /api/founder/* endpoints, no-auth 401
2. FREE - DIRECT PROFILE: PUT/GET /api/founder/profile (no LLM)
3. LLM (~4 calls) - INTERVIEW FLOW: start->answer x2->finish
4. LLM (1 call) - INJECTION: founder /ask still returns goal_impact, no strategic_alignment

CRITICAL: ANTHROPIC_API_KEY is LIVE (real money). Keep LLM budget <= 6 calls total.
"""
import requests
import json
import time
import uuid

BASE_URL = "https://founder-goals.preview.emergentagent.com/api"

# Test credentials from test_credentials.md
FOUNDER_EMAIL = "ceo@smartdecigen.com"
FOUNDER_PASSWORD = "FounderOS@2026"

# Track LLM calls
llm_call_count = 0

def log(msg):
    print(f"[TEST] {msg}")

def track_llm_call(endpoint):
    global llm_call_count
    llm_call_count += 1
    log(f"LLM CALL #{llm_call_count} - {endpoint}")

def login(email, password):
    """Login and return token + user info"""
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        log(f"Login failed for {email}: {r.status_code} {r.text}")
        return None, None
    data = r.json()
    return data["token"], data["user"]

def signup_fresh_member():
    """Create a fresh member account"""
    email = f"member_test_{uuid.uuid4().hex[:8]}@acmesolar.com"
    password = "TestMember@2026"
    r = requests.post(f"{BASE_URL}/auth/signup", json={
        "email": email,
        "password": password,
        "name": "Test Member"
    })
    if r.status_code != 200:
        log(f"Signup failed: {r.status_code} {r.text}")
        return None, None, None
    data = r.json()
    return data["token"], data["user"], email

def create_invite(founder_token):
    """Founder creates an invite"""
    r = requests.post(f"{BASE_URL}/org/invites",
                     json={},  # Empty body is valid (email is optional)
                     headers={"Authorization": f"Bearer {founder_token}"})
    if r.status_code != 200:
        log(f"Create invite failed: {r.status_code} {r.text}")
        return None
    return r.json()["code"]

def join_org(member_token, code):
    """Member joins org via invite code"""
    r = requests.post(f"{BASE_URL}/org/join", 
                     json={"code": code},
                     headers={"Authorization": f"Bearer {member_token}"})
    if r.status_code != 200:
        log(f"Join org failed: {r.status_code} {r.text}")
        return False
    return True

# ============================================================================
# TEST 1: FREE - GATING (member 403, no-auth 401)
# ============================================================================
def test_1_gating():
    log("\n" + "="*80)
    log("TEST 1: FREE - GATING (member 403 on all /api/founder/*, no-auth 401)")
    log("="*80)
    
    # Login as founder
    founder_token, founder_user = login(FOUNDER_EMAIL, FOUNDER_PASSWORD)
    if not founder_token:
        log("❌ TEST 1 FAILED: Could not login as founder")
        return False
    
    log(f"✓ Founder logged in: {founder_user['email']}, org_id={founder_user.get('org_id')}")
    
    # Create fresh member
    member_token, member_user, member_email = signup_fresh_member()
    if not member_token:
        log("❌ TEST 1 FAILED: Could not create member account")
        return False
    
    log(f"✓ Fresh member created: {member_email}")
    
    # Founder creates invite
    invite_code = create_invite(founder_token)
    if not invite_code:
        log("❌ TEST 1 FAILED: Could not create invite")
        return False
    
    log(f"✓ Invite created: {invite_code}")
    
    # Member joins org
    if not join_org(member_token, invite_code):
        log("❌ TEST 1 FAILED: Member could not join org")
        return False
    
    log(f"✓ Member joined org")
    
    # Test all endpoints with member token (should all be 403)
    endpoints = [
        ("GET", "/founder/profile", None),
        ("POST", "/founder/interview/start", None),
        ("POST", "/founder/interview/answer", {"message": "test"}),
        ("POST", "/founder/interview/finish", None),
        ("PUT", "/founder/profile", {"summary": "test"}),
        ("DELETE", "/founder/profile", None),
    ]
    
    all_403 = True
    for method, path, payload in endpoints:
        if method == "GET":
            r = requests.get(f"{BASE_URL}{path}", headers={"Authorization": f"Bearer {member_token}"})
        elif method == "POST":
            r = requests.post(f"{BASE_URL}{path}", json=payload, headers={"Authorization": f"Bearer {member_token}"})
        elif method == "PUT":
            r = requests.put(f"{BASE_URL}{path}", json=payload, headers={"Authorization": f"Bearer {member_token}"})
        elif method == "DELETE":
            r = requests.delete(f"{BASE_URL}{path}", headers={"Authorization": f"Bearer {member_token}"})
        
        if r.status_code == 403:
            log(f"✓ {method} {path} -> 403 (member correctly blocked)")
        else:
            log(f"❌ {method} {path} -> {r.status_code} (expected 403)")
            all_403 = False
    
    # Test no-auth 401 on GET /founder/profile
    r = requests.get(f"{BASE_URL}/founder/profile")
    if r.status_code == 401:
        log(f"✓ GET /founder/profile (no auth) -> 401")
    else:
        log(f"❌ GET /founder/profile (no auth) -> {r.status_code} (expected 401)")
        all_403 = False
    
    if all_403:
        log("✅ TEST 1 PASSED: All gating checks passed")
        return True
    else:
        log("❌ TEST 1 FAILED: Some gating checks failed")
        return False

# ============================================================================
# TEST 2: FREE - DIRECT PROFILE (no LLM)
# ============================================================================
def test_2_direct_profile():
    log("\n" + "="*80)
    log("TEST 2: FREE - DIRECT PROFILE (PUT/GET /api/founder/profile, no LLM)")
    log("="*80)
    
    founder_token, founder_user = login(FOUNDER_EMAIL, FOUNDER_PASSWORD)
    if not founder_token:
        log("❌ TEST 2 FAILED: Could not login as founder")
        return False
    
    # PUT profile with all fields
    profile_data = {
        "summary": "Technical introverted solar-EPC founder",
        "personality": "introverted, conflict-averse",
        "industry_summary": "C&I rooftop solar EPC in North India"
    }
    
    r = requests.put(f"{BASE_URL}/founder/profile", 
                    json=profile_data,
                    headers={"Authorization": f"Bearer {founder_token}"})
    
    if r.status_code != 200:
        log(f"❌ PUT /founder/profile failed: {r.status_code} {r.text}")
        return False
    
    data = r.json()
    if not data.get("has_profile"):
        log(f"❌ PUT response has_profile is not true")
        return False
    
    profile = data.get("profile", {})
    if profile.get("summary") != profile_data["summary"]:
        log(f"❌ PUT response summary mismatch: {profile.get('summary')}")
        return False
    
    log(f"✓ PUT /founder/profile -> 200, has_profile=true, summary echoed correctly")
    
    # GET profile
    r = requests.get(f"{BASE_URL}/founder/profile",
                    headers={"Authorization": f"Bearer {founder_token}"})
    
    if r.status_code != 200:
        log(f"❌ GET /founder/profile failed: {r.status_code} {r.text}")
        return False
    
    data = r.json()
    if not data.get("has_profile"):
        log(f"❌ GET response has_profile is not true")
        return False
    
    profile = data.get("profile", {})
    if profile.get("summary") != profile_data["summary"]:
        log(f"❌ GET response summary mismatch: {profile.get('summary')}")
        return False
    if profile.get("personality") != profile_data["personality"]:
        log(f"❌ GET response personality mismatch: {profile.get('personality')}")
        return False
    if profile.get("industry_summary") != profile_data["industry_summary"]:
        log(f"❌ GET response industry_summary mismatch: {profile.get('industry_summary')}")
        return False
    
    log(f"✓ GET /founder/profile -> 200, has_profile=true, all values echoed correctly")
    
    # Test validation: empty summary should be 422
    r = requests.put(f"{BASE_URL}/founder/profile",
                    json={"summary": ""},
                    headers={"Authorization": f"Bearer {founder_token}"})
    
    if r.status_code == 422:
        log(f"✓ PUT /founder/profile with empty summary -> 422")
    else:
        log(f"❌ PUT /founder/profile with empty summary -> {r.status_code} (expected 422)")
        return False
    
    log("✅ TEST 2 PASSED: Direct profile PUT/GET working correctly")
    return True

# ============================================================================
# TEST 3: LLM (~4 calls) - INTERVIEW FLOW
# ============================================================================
def test_3_interview_flow():
    log("\n" + "="*80)
    log("TEST 3: LLM (~4 calls) - INTERVIEW FLOW (start->answer x2->finish)")
    log("="*80)
    
    founder_token, founder_user = login(FOUNDER_EMAIL, FOUNDER_PASSWORD)
    if not founder_token:
        log("❌ TEST 3 FAILED: Could not login as founder")
        return False
    
    # Clear any existing profile first
    requests.delete(f"{BASE_URL}/founder/profile",
                   headers={"Authorization": f"Bearer {founder_token}"})
    log("✓ Cleared any existing profile")
    
    # POST /interview/start (no LLM)
    r = requests.post(f"{BASE_URL}/founder/interview/start",
                     headers={"Authorization": f"Bearer {founder_token}"})
    
    if r.status_code != 200:
        log(f"❌ POST /interview/start failed: {r.status_code} {r.text}")
        return False
    
    data = r.json()
    if data.get("done") != False:
        log(f"❌ POST /interview/start done should be false: {data.get('done')}")
        return False
    
    question = data.get("question", "")
    if not question or len(question) < 10:
        log(f"❌ POST /interview/start question is empty or too short: {question}")
        return False
    
    count = data.get("count", -1)
    if count != 0:
        log(f"❌ POST /interview/start count should be 0: {count}")
        return False
    
    target = data.get("target")
    log(f"✓ POST /interview/start -> 200, done=false, question='{question[:60]}...', count=0, target={target}")
    
    # POST /interview/answer #1 (LLM call)
    track_llm_call("POST /founder/interview/answer #1")
    answer1 = "We do C&I rooftop solar EPC in North India, early stage, hardest part is closing big deals because I hate cold sales."
    r = requests.post(f"{BASE_URL}/founder/interview/answer",
                     json={"message": answer1},
                     headers={"Authorization": f"Bearer {founder_token}"})
    
    if r.status_code != 200:
        log(f"❌ POST /interview/answer #1 failed: {r.status_code} {r.text}")
        return False
    
    data = r.json()
    if data.get("done") != False:
        log(f"❌ POST /interview/answer #1 done should be false: {data.get('done')}")
        return False
    
    question2 = data.get("question", "")
    if not question2 or len(question2) < 10:
        log(f"❌ POST /interview/answer #1 question is empty or too short: {question2}")
        return False
    
    if question2 == question:
        log(f"❌ POST /interview/answer #1 question should be different from opening: {question2}")
        return False
    
    count = data.get("count", -1)
    if count != 1:
        log(f"❌ POST /interview/answer #1 count should be 1: {count}")
        return False
    
    log(f"✓ POST /interview/answer #1 -> 200, done=false, NEW question='{question2[:60]}...', count=1")
    
    # POST /interview/answer #2 (LLM call)
    track_llm_call("POST /founder/interview/answer #2")
    answer2 = "I make decisions slowly with data, I avoid confrontation, my strength is technical design but I'm weak at negotiation."
    r = requests.post(f"{BASE_URL}/founder/interview/answer",
                     json={"message": answer2},
                     headers={"Authorization": f"Bearer {founder_token}"})
    
    if r.status_code != 200:
        log(f"❌ POST /interview/answer #2 failed: {r.status_code} {r.text}")
        return False
    
    data = r.json()
    count = data.get("count", -1)
    if count != 2:
        log(f"❌ POST /interview/answer #2 count should be 2: {count}")
        return False
    
    log(f"✓ POST /interview/answer #2 -> 200, count=2")
    
    # POST /interview/finish (LLM call - distill)
    track_llm_call("POST /founder/interview/finish (distill)")
    r = requests.post(f"{BASE_URL}/founder/interview/finish",
                     headers={"Authorization": f"Bearer {founder_token}"})
    
    if r.status_code != 200:
        log(f"❌ POST /interview/finish failed: {r.status_code} {r.text}")
        return False
    
    data = r.json()
    if data.get("done") != True:
        log(f"❌ POST /interview/finish done should be true: {data.get('done')}")
        return False
    
    profile = data.get("profile", {})
    summary = profile.get("summary", "")
    industry_summary = profile.get("industry_summary", "")
    
    if not summary or len(summary) < 10:
        log(f"❌ POST /interview/finish profile.summary is empty or too short: {summary}")
        return False
    
    if not industry_summary or len(industry_summary) < 10:
        log(f"❌ POST /interview/finish profile.industry_summary is empty or too short: {industry_summary}")
        return False
    
    log(f"✓ POST /interview/finish -> 200, done=true, profile.summary='{summary[:60]}...', profile.industry_summary='{industry_summary[:60]}...'")
    
    # GET /profile should now show has_profile=true
    r = requests.get(f"{BASE_URL}/founder/profile",
                    headers={"Authorization": f"Bearer {founder_token}"})
    
    if r.status_code != 200:
        log(f"❌ GET /founder/profile after finish failed: {r.status_code} {r.text}")
        return False
    
    data = r.json()
    if not data.get("has_profile"):
        log(f"❌ GET /founder/profile has_profile should be true after finish")
        return False
    
    log(f"✓ GET /founder/profile -> has_profile=true")
    
    # Negative test: start fresh interview, then immediately finish (should be 422, needs >= 2 answers)
    requests.delete(f"{BASE_URL}/founder/profile",
                   headers={"Authorization": f"Bearer {founder_token}"})
    
    r = requests.post(f"{BASE_URL}/founder/interview/start",
                     headers={"Authorization": f"Bearer {founder_token}"})
    
    # Try to finish immediately (0 answers)
    r = requests.post(f"{BASE_URL}/founder/interview/finish",
                     headers={"Authorization": f"Bearer {founder_token}"})
    
    if r.status_code == 422:
        log(f"✓ POST /interview/finish with 0 answers -> 422 (needs >= 2)")
    else:
        log(f"❌ POST /interview/finish with 0 answers -> {r.status_code} (expected 422)")
        return False
    
    log("✅ TEST 3 PASSED: Interview flow working correctly")
    return True

# ============================================================================
# TEST 4: LLM (1 call) - INJECTION DID NOT BREAK THE CONTRACT
# ============================================================================
def test_4_injection():
    log("\n" + "="*80)
    log("TEST 4: LLM (1 call) - INJECTION (founder /ask returns goal_impact, no strategic_alignment)")
    log("="*80)
    
    founder_token, founder_user = login(FOUNDER_EMAIL, FOUNDER_PASSWORD)
    if not founder_token:
        log("❌ TEST 4 FAILED: Could not login as founder")
        return False
    
    # Founder asks a decide question
    track_llm_call("POST /brain/ask (founder)")
    question = "A client is unhappy about a delay and wants to talk penalties, how should I handle it?"
    r = requests.post(f"{BASE_URL}/brain/ask",
                     json={"question": question},
                     headers={"Authorization": f"Bearer {founder_token}"})
    
    if r.status_code != 200:
        log(f"❌ POST /brain/ask failed: {r.status_code} {r.text}")
        return False
    
    data = r.json()
    
    # Check mode=decide
    mode = data.get("mode")
    if mode != "decide":
        log(f"❌ POST /brain/ask mode should be 'decide': {mode}")
        return False
    
    log(f"✓ POST /brain/ask -> 200, mode=decide")
    
    # Check response CONTAINS goal_impact
    goal_impact = data.get("goal_impact")
    if not goal_impact:
        log(f"❌ POST /brain/ask response missing 'goal_impact' key")
        return False
    
    # Validate goal_impact structure
    required_keys = ["score", "band", "label", "reason"]
    for key in required_keys:
        if key not in goal_impact:
            log(f"❌ goal_impact missing required key '{key}'")
            return False
    
    log(f"✓ Response CONTAINS 'goal_impact' with all required keys: {goal_impact}")
    
    # Check response does NOT contain strategic_alignment
    if "strategic_alignment" in data:
        log(f"❌ POST /brain/ask response should NOT contain 'strategic_alignment' key")
        return False
    
    log(f"✓ Response does NOT contain 'strategic_alignment' (correctly stripped)")
    
    log("✅ TEST 4 PASSED: Injection did not break the contract")
    return True

# ============================================================================
# MAIN
# ============================================================================
def main():
    log("\n" + "="*80)
    log("FOUNDER PROFILE DEEP-ONBOARDING TEST SUITE")
    log("CRITICAL: ANTHROPIC_API_KEY is LIVE. Keep LLM budget <= 6 calls.")
    log("="*80)
    
    results = []
    
    # Test 1: FREE - GATING
    results.append(("TEST 1 (FREE - GATING)", test_1_gating()))
    
    # Test 2: FREE - DIRECT PROFILE
    results.append(("TEST 2 (FREE - DIRECT PROFILE)", test_2_direct_profile()))
    
    # Test 3: LLM (~4 calls) - INTERVIEW FLOW
    results.append(("TEST 3 (LLM ~4 calls - INTERVIEW FLOW)", test_3_interview_flow()))
    
    # Test 4: LLM (1 call) - INJECTION
    results.append(("TEST 4 (LLM 1 call - INJECTION)", test_4_injection()))
    
    # Summary
    log("\n" + "="*80)
    log("TEST SUMMARY")
    log("="*80)
    
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        log(f"{status} - {name}")
    
    log(f"\nTotal LLM calls used: {llm_call_count} (budget: <= 6)")
    
    if llm_call_count > 6:
        log(f"⚠️  WARNING: LLM call count exceeded budget!")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        log("\n🎉 ALL TESTS PASSED")
    else:
        log("\n❌ SOME TESTS FAILED")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
