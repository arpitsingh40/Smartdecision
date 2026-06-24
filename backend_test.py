#!/usr/bin/env python3
"""
Backend test for Phase 3.0+4: Decision Ledger + execution endpoints + Founder Cockpit
BUDGET: AT MOST 1 call to POST /api/brain/ask total (everything else is FREE)
"""
import os
import sys
import json
import requests
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://expectation-checker.preview.emergentagent.com/api"

# Test credentials
FOUNDER_EMAIL = "ceo@smartdecigen.com"
FOUNDER_PASSWORD = "FounderOS@2026"
MEMBER_EMAIL = "priya@acmesolar.com"
MEMBER_PASSWORD = "Member1234!"

# Track LLM calls
llm_calls_made = 0
MAX_LLM_CALLS = 1

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def login(email, password):
    """Login and return token"""
    r = requests.post(f"{BACKEND_URL}/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        log(f"❌ Login failed for {email}: {r.status_code} {r.text}")
        return None
    data = r.json()
    log(f"✅ Logged in as {email}")
    return data.get("token")

def signup(email, password, name):
    """Signup new user"""
    r = requests.post(f"{BACKEND_URL}/auth/signup", json={"email": email, "password": password, "name": name})
    if r.status_code != 200:
        log(f"❌ Signup failed for {email}: {r.status_code} {r.text}")
        return None
    data = r.json()
    log(f"✅ Signed up as {email}")
    return data.get("token")

def check_org_state(founder_token):
    """Check if org 'Acme Solar' exists with North Star set"""
    headers = {"Authorization": f"Bearer {founder_token}"}
    r = requests.get(f"{BACKEND_URL}/org", headers=headers)
    if r.status_code == 404:
        return None, None
    if r.status_code != 200:
        log(f"❌ GET /org failed: {r.status_code}")
        return None, None
    org = r.json()
    log(f"✅ Org exists: {org.get('name')} (strategy_set={org.get('strategy_set')})")
    return org, org.get("id")

def create_org_and_strategy(founder_token):
    """Create org 'Acme Solar' and set North Star"""
    headers = {"Authorization": f"Bearer {founder_token}"}
    
    # Create org
    r = requests.post(f"{BACKEND_URL}/org", headers=headers, json={"name": "Acme Solar"})
    if r.status_code != 200:
        log(f"❌ POST /org failed: {r.status_code} {r.text}")
        return None
    org = r.json()
    org_id = org.get("id")
    log(f"✅ Created org: {org.get('name')} (id={org_id})")
    
    # Set strategy
    strategy = {
        "north_star": "Reach 100 crore annual revenue",
        "target": "100 Cr ARR",
        "deadline": "Mar 2027",
        "priorities": [
            "Win commercial & industrial rooftop deals",
            "Push EPC ticket sizes above 50L",
            "Protect 18% margins"
        ],
        "decision_rules": "Never quote below 18% margin. Prefer C&I over residential."
    }
    r = requests.put(f"{BACKEND_URL}/org/strategy", headers=headers, json=strategy)
    if r.status_code != 200:
        log(f"❌ PUT /org/strategy failed: {r.status_code} {r.text}")
        return None
    log(f"✅ Set North Star strategy")
    return org_id

def invite_and_join_member(founder_token, member_email, member_password):
    """Create invite and have member join"""
    headers = {"Authorization": f"Bearer {founder_token}"}
    
    # Create invite
    r = requests.post(f"{BACKEND_URL}/org/invites", headers=headers, json={})
    if r.status_code != 200:
        log(f"❌ POST /org/invites failed: {r.status_code} {r.text}")
        return None
    invite = r.json()
    code = invite.get("code")
    log(f"✅ Created invite code: {code}")
    
    # Check if member exists, if not signup
    member_token = login(member_email, member_password)
    if not member_token:
        member_token = signup(member_email, member_password, "Priya")
        if not member_token:
            return None
    
    # Join org
    headers_member = {"Authorization": f"Bearer {member_token}"}
    r = requests.post(f"{BACKEND_URL}/org/join", headers=headers_member, json={"code": code})
    if r.status_code == 409:
        log(f"✅ Member already in org")
        return member_token
    if r.status_code != 200:
        log(f"❌ POST /org/join failed: {r.status_code} {r.text}")
        return None
    log(f"✅ Member joined org")
    return member_token

def seed_member_decision(member_token):
    """Create one decision for member via /api/brain/ask"""
    global llm_calls_made
    if llm_calls_made >= MAX_LLM_CALLS:
        log(f"⚠️  Skipping seed decision (LLM budget exhausted)")
        return None
    
    headers = {"Authorization": f"Bearer {member_token}"}
    question = "A client wants a big discount on a residential install that would push margin to 8%. What should I do?"
    r = requests.post(f"{BACKEND_URL}/brain/ask", headers=headers, json={"question": question})
    if r.status_code != 200:
        log(f"❌ POST /brain/ask (seed) failed: {r.status_code} {r.text}")
        return None
    llm_calls_made += 1
    data = r.json()
    decision_id = data.get("decision_id")
    log(f"✅ Seeded decision: {decision_id} (LLM calls: {llm_calls_made}/{MAX_LLM_CALLS})")
    return decision_id

def test_1_member_decisions_no_alignment(member_token):
    """TEST 1 (FREE): Member GET /api/brain/decisions -> 200, NO strategic_alignment in any row"""
    log("\n=== TEST 1: Member decision history (NO strategic_alignment) ===")
    headers = {"Authorization": f"Bearer {member_token}"}
    r = requests.get(f"{BACKEND_URL}/brain/decisions", headers=headers)
    
    if r.status_code != 200:
        log(f"❌ FAIL: GET /brain/decisions returned {r.status_code}")
        return False
    
    data = r.json()
    decisions = data.get("decisions", [])
    log(f"✅ GET /brain/decisions -> 200, {len(decisions)} decisions")
    
    # CRITICAL: assert NO row contains strategic_alignment
    for i, d in enumerate(decisions):
        if "strategic_alignment" in d:
            log(f"❌ FAIL: Decision {i} contains 'strategic_alignment' key (MUST be stripped from member data)")
            return False
    
    log(f"✅ PASS: NO decision contains 'strategic_alignment' key (founder-only field correctly stripped)")
    return True

def test_2_execution_endpoints(member_token):
    """TEST 2 (FREE): Commit/status endpoints with validation"""
    log("\n=== TEST 2: Execution endpoints (commit/status) ===")
    headers = {"Authorization": f"Bearer {member_token}"}
    
    # Get member's decisions
    r = requests.get(f"{BACKEND_URL}/brain/decisions", headers=headers)
    if r.status_code != 200 or not r.json().get("decisions"):
        log(f"❌ FAIL: No decisions found for member")
        return False
    
    decision_id = r.json()["decisions"][0]["id"]
    log(f"Using decision_id: {decision_id}")
    
    # 2a. POST /decisions/{id}/commit -> 200
    action = "Send minimum-margin pricing and pivot to a referral."
    r = requests.post(f"{BACKEND_URL}/brain/decisions/{decision_id}/commit", 
                     headers=headers, json={"action": action})
    if r.status_code != 200:
        log(f"❌ FAIL: POST /decisions/{decision_id}/commit returned {r.status_code}")
        return False
    data = r.json()
    if data.get("committed_action") != action or data.get("status") != "open":
        log(f"❌ FAIL: commit response incorrect: {data}")
        return False
    log(f"✅ POST /decisions/{decision_id}/commit -> 200 (committed_action set, status=open)")
    
    # 2b. POST /decisions/{id}/status {"status":"done"} -> 200
    r = requests.post(f"{BACKEND_URL}/brain/decisions/{decision_id}/status",
                     headers=headers, json={"status": "done"})
    if r.status_code != 200:
        log(f"❌ FAIL: POST /decisions/{decision_id}/status done returned {r.status_code}")
        return False
    data = r.json()
    if data.get("status") != "done":
        log(f"❌ FAIL: status response incorrect: {data}")
        return False
    log(f"✅ POST /decisions/{decision_id}/status done -> 200")
    
    # 2c. Negative: {"status":"bogus"} -> 422
    r = requests.post(f"{BACKEND_URL}/brain/decisions/{decision_id}/status",
                     headers=headers, json={"status": "bogus"})
    if r.status_code != 422:
        log(f"❌ FAIL: POST /decisions/{decision_id}/status bogus returned {r.status_code} (expected 422)")
        return False
    log(f"✅ POST /decisions/{decision_id}/status bogus -> 422")
    
    # 2d. Negative: founder tries to commit member's decision -> 404
    founder_token = login(FOUNDER_EMAIL, FOUNDER_PASSWORD)
    headers_founder = {"Authorization": f"Bearer {founder_token}"}
    r = requests.post(f"{BACKEND_URL}/brain/decisions/{decision_id}/commit",
                     headers=headers_founder, json={"action": "test"})
    if r.status_code != 404:
        log(f"❌ FAIL: Founder commit on member decision returned {r.status_code} (expected 404)")
        return False
    log(f"✅ Founder POST /decisions/{decision_id}/commit -> 404 (not their decision)")
    
    log(f"✅ PASS: All execution endpoint tests passed")
    return True

def test_3_founder_cockpit(founder_token, member_token):
    """TEST 3 (FREE): Owner GET /api/org/cockpit -> 200 with all keys, member -> 403"""
    log("\n=== TEST 3: Founder Cockpit ===")
    
    # 3a. Owner GET /cockpit -> 200
    headers = {"Authorization": f"Bearer {founder_token}"}
    r = requests.get(f"{BACKEND_URL}/org/cockpit", headers=headers)
    if r.status_code != 200:
        log(f"❌ FAIL: GET /org/cockpit (owner) returned {r.status_code}")
        return False
    
    data = r.json()
    log(f"✅ GET /org/cockpit (owner) -> 200")
    
    # Assert required keys
    required_keys = ["north_star", "totals", "alignment", "execution", "per_member", "drift"]
    for key in required_keys:
        if key not in data:
            log(f"❌ FAIL: cockpit missing key '{key}'")
            return False
    log(f"✅ Cockpit has all required keys: {required_keys}")
    
    # Assert north_star structure
    ns = data["north_star"]
    if not ns.get("strategy_set") or not ns.get("north_star"):
        log(f"❌ FAIL: north_star structure incorrect: {ns}")
        return False
    log(f"✅ north_star: strategy_set={ns.get('strategy_set')}, north_star='{ns.get('north_star')[:50]}...'")
    
    # Assert totals
    totals = data["totals"]
    if not isinstance(totals.get("decisions"), int) or not isinstance(totals.get("members"), int):
        log(f"❌ FAIL: totals structure incorrect: {totals}")
        return False
    log(f"✅ totals: decisions={totals.get('decisions')}, last_7d={totals.get('last_7d')}, members={totals.get('members')}")
    
    # Assert alignment (avg is a number, scored count)
    alignment = data["alignment"]
    if not isinstance(alignment.get("scored"), int):
        log(f"❌ FAIL: alignment.scored not an int: {alignment}")
        return False
    if alignment.get("avg") is not None and not isinstance(alignment.get("avg"), int):
        log(f"❌ FAIL: alignment.avg not a number: {alignment}")
        return False
    log(f"✅ alignment: avg={alignment.get('avg')}, high={alignment.get('high')}, medium={alignment.get('medium')}, low={alignment.get('low')}, scored={alignment.get('scored')}")
    
    # Assert execution
    execution = data["execution"]
    if not isinstance(execution.get("committed"), int) or not isinstance(execution.get("done"), int):
        log(f"❌ FAIL: execution structure incorrect: {execution}")
        return False
    log(f"✅ execution: committed={execution.get('committed')}, open={execution.get('open')}, done={execution.get('done')}, dropped={execution.get('dropped')}, follow_through_pct={execution.get('follow_through_pct')}")
    
    # Assert per_member is a list
    per_member = data["per_member"]
    if not isinstance(per_member, list):
        log(f"❌ FAIL: per_member not a list: {per_member}")
        return False
    log(f"✅ per_member: {len(per_member)} members")
    for m in per_member:
        log(f"   - {m.get('email')}: decisions={m.get('decisions')}, avg_alignment={m.get('avg_alignment')}, done={m.get('done')}")
    
    # Assert drift is a list
    drift = data["drift"]
    if not isinstance(drift, list):
        log(f"❌ FAIL: drift not a list: {drift}")
        return False
    log(f"✅ drift: {len(drift)} low-alignment decisions")
    
    # 3b. Member GET /cockpit -> 403
    headers_member = {"Authorization": f"Bearer {member_token}"}
    r = requests.get(f"{BACKEND_URL}/org/cockpit", headers=headers_member)
    if r.status_code != 403:
        log(f"❌ FAIL: GET /org/cockpit (member) returned {r.status_code} (expected 403)")
        return False
    log(f"✅ GET /org/cockpit (member) -> 403")
    
    log(f"✅ PASS: Founder Cockpit tests passed")
    return data  # Return for test 4

def test_4_llm_alignment_capture(member_token, founder_token, cockpit_before):
    """TEST 4 (LLM, 1 call): Member ask -> NO strategic_alignment in response, but cockpit scored increases"""
    global llm_calls_made
    log("\n=== TEST 4: LLM alignment capture (1 call) ===")
    
    if llm_calls_made >= MAX_LLM_CALLS:
        log(f"❌ FAIL: LLM budget exhausted (already made {llm_calls_made} calls)")
        return False
    
    # Get alignment.scored before
    scored_before = cockpit_before["alignment"]["scored"]
    log(f"Alignment scored before: {scored_before}")
    
    # Member POST /brain/ask
    headers = {"Authorization": f"Bearer {member_token}"}
    question = "A client wants a big discount on a residential install that would push margin to 8%. What should I do?"
    r = requests.post(f"{BACKEND_URL}/brain/ask", headers=headers, json={"question": question})
    if r.status_code != 200:
        log(f"❌ FAIL: POST /brain/ask returned {r.status_code} {r.text}")
        return False
    llm_calls_made += 1
    
    data = r.json()
    log(f"✅ POST /brain/ask -> 200 (LLM calls: {llm_calls_made}/{MAX_LLM_CALLS})")
    
    # CRITICAL: assert response has decision_id and NO strategic_alignment
    if "decision_id" not in data:
        log(f"❌ FAIL: response missing 'decision_id': {data}")
        return False
    log(f"✅ Response has decision_id: {data.get('decision_id')}")
    
    if "strategic_alignment" in data:
        log(f"❌ FAIL: response contains 'strategic_alignment' key (MUST be stripped from member response)")
        return False
    log(f"✅ Response does NOT contain 'strategic_alignment' key")
    
    # Get cockpit again and check alignment.scored increased
    headers_founder = {"Authorization": f"Bearer {founder_token}"}
    r = requests.get(f"{BACKEND_URL}/org/cockpit", headers=headers_founder)
    if r.status_code != 200:
        log(f"❌ FAIL: GET /org/cockpit (after ask) returned {r.status_code}")
        return False
    
    cockpit_after = r.json()
    scored_after = cockpit_after["alignment"]["scored"]
    log(f"Alignment scored after: {scored_after}")
    
    if scored_after != scored_before + 1:
        log(f"❌ FAIL: alignment.scored did not increase by 1 (before={scored_before}, after={scored_after})")
        return False
    log(f"✅ alignment.scored increased by 1 (alignment WAS captured server-side even though member never saw it)")
    
    log(f"✅ PASS: LLM alignment capture test passed")
    return True

def main():
    log("=== Phase 3.0+4 Backend Test: Decision Ledger + Execution + Founder Cockpit ===")
    log(f"Backend URL: {BACKEND_URL}")
    log(f"LLM Budget: {MAX_LLM_CALLS} call(s)")
    
    # Login founder
    founder_token = login(FOUNDER_EMAIL, FOUNDER_PASSWORD)
    if not founder_token:
        log("❌ CRITICAL: Cannot login as founder")
        sys.exit(1)
    
    # Check org state
    org, org_id = check_org_state(founder_token)
    
    # If org doesn't exist or no strategy, recreate
    if not org or not org.get("strategy_set"):
        log("\n=== Setting up org state ===")
        org_id = create_org_and_strategy(founder_token)
        if not org_id:
            log("❌ CRITICAL: Cannot create org")
            sys.exit(1)
        
        # Invite and join member
        member_token = invite_and_join_member(founder_token, MEMBER_EMAIL, MEMBER_PASSWORD)
        if not member_token:
            log("❌ CRITICAL: Cannot setup member")
            sys.exit(1)
        
        # Seed one decision
        decision_id = seed_member_decision(member_token)
        if not decision_id:
            log("❌ CRITICAL: Cannot seed decision")
            sys.exit(1)
    else:
        log(f"✅ Org state exists, reusing")
        member_token = login(MEMBER_EMAIL, MEMBER_PASSWORD)
        if not member_token:
            log("❌ CRITICAL: Cannot login as member")
            sys.exit(1)
    
    # Run tests
    results = []
    
    # TEST 1 (FREE)
    results.append(("TEST 1: Member decisions NO alignment", test_1_member_decisions_no_alignment(member_token)))
    
    # TEST 2 (FREE)
    results.append(("TEST 2: Execution endpoints", test_2_execution_endpoints(member_token)))
    
    # TEST 3 (FREE)
    cockpit_before = test_3_founder_cockpit(founder_token, member_token)
    results.append(("TEST 3: Founder Cockpit", cockpit_before is not False))
    
    # TEST 4 (LLM, 1 call) - only if we haven't used LLM budget yet
    if llm_calls_made < MAX_LLM_CALLS and cockpit_before:
        results.append(("TEST 4: LLM alignment capture", test_4_llm_alignment_capture(member_token, founder_token, cockpit_before)))
    else:
        log("\n⚠️  Skipping TEST 4 (LLM budget exhausted during setup)")
        results.append(("TEST 4: LLM alignment capture", None))
    
    # Summary
    log("\n" + "="*80)
    log("=== TEST SUMMARY ===")
    log(f"LLM calls made: {llm_calls_made}/{MAX_LLM_CALLS}")
    log("")
    
    passed = 0
    failed = 0
    skipped = 0
    for name, result in results:
        if result is True:
            log(f"✅ PASS: {name}")
            passed += 1
        elif result is False:
            log(f"❌ FAIL: {name}")
            failed += 1
        else:
            log(f"⚠️  SKIP: {name}")
            skipped += 1
    
    log("")
    log(f"Total: {passed} passed, {failed} failed, {skipped} skipped")
    
    if failed > 0:
        sys.exit(1)
    else:
        log("\n🎉 ALL TESTS PASSED")
        sys.exit(0)

if __name__ == "__main__":
    main()
