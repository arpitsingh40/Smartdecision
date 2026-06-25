#!/usr/bin/env python3
"""
Backend test for Feature (c): founder-only goal_impact + founder/member/decision/achievement journey.
LLM BUDGET: max 3 brain asks (should only need 2).
"""
import os
import sys
import json
import time
import uuid
import requests
from datetime import datetime

# Backend URL from environment
BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://founder-goals.preview.emergentagent.com")
API_BASE = f"{BACKEND_URL}/api"

# Test credentials
FOUNDER_EMAIL = "ceo@smartdecigen.com"
FOUNDER_PASSWORD = "FounderOS@2026"

# Track LLM calls
llm_call_count = 0

def log(msg):
    print(f"[TEST] {msg}")

def login(email, password):
    """Login and return token + user info"""
    r = requests.post(f"{API_BASE}/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        log(f"❌ Login failed for {email}: {r.status_code} {r.text}")
        sys.exit(1)
    data = r.json()
    log(f"✅ Logged in as {email} (org_role: {data.get('org_role')})")
    return data["token"], data

def signup_fresh_member():
    """Create a fresh member account"""
    email = f"member_{uuid.uuid4().hex[:8]}@acmesolar.com"
    password = "TestMember@2026"
    r = requests.post(f"{API_BASE}/auth/signup", json={
        "email": email,
        "password": password,
        "name": f"Test Member {uuid.uuid4().hex[:4]}"
    })
    if r.status_code != 200:
        log(f"❌ Signup failed: {r.status_code} {r.text}")
        sys.exit(1)
    data = r.json()
    log(f"✅ Created fresh member: {email}")
    return data["token"], data, email, password

def create_invite(founder_token):
    """Founder creates an invite"""
    r = requests.post(f"{API_BASE}/org/invites", 
                     json={},
                     headers={"Authorization": f"Bearer {founder_token}"})
    if r.status_code != 200:
        log(f"❌ Create invite failed: {r.status_code} {r.text}")
        sys.exit(1)
    data = r.json()
    log(f"✅ Created invite with code: {data['code']}")
    return data["code"]

def join_org(member_token, code):
    """Member joins org via invite code"""
    r = requests.post(f"{API_BASE}/org/join",
                     json={"code": code},
                     headers={"Authorization": f"Bearer {member_token}"})
    if r.status_code != 200:
        log(f"❌ Join org failed: {r.status_code} {r.text}")
        sys.exit(1)
    log(f"✅ Member joined org: {r.json()['name']}")
    return r.json()

def brain_ask(token, question, session_id=None):
    """POST /api/brain/ask"""
    global llm_call_count
    llm_call_count += 1
    payload = {"question": question}
    if session_id:
        payload["session_id"] = session_id
    r = requests.post(f"{API_BASE}/brain/ask",
                     json=payload,
                     headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        log(f"❌ Brain ask failed: {r.status_code} {r.text}")
        sys.exit(1)
    log(f"✅ Brain ask returned 200 (LLM call #{llm_call_count})")
    return r.json()

def get_decisions(token):
    """GET /api/brain/decisions"""
    r = requests.get(f"{API_BASE}/brain/decisions",
                    headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        log(f"❌ Get decisions failed: {r.status_code} {r.text}")
        sys.exit(1)
    return r.json()["decisions"]

def commit_action(token, decision_id, action, due_in_hours=48):
    """POST /api/brain/decisions/{id}/commit"""
    r = requests.post(f"{API_BASE}/brain/decisions/{decision_id}/commit",
                     json={"action": action, "due_in_hours": due_in_hours},
                     headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        log(f"❌ Commit action failed: {r.status_code} {r.text}")
        sys.exit(1)
    log(f"✅ Committed action: {action[:50]}...")
    return r.json()

def set_status(token, decision_id, status, outcome=None, result=None):
    """POST /api/brain/decisions/{id}/status"""
    payload = {"status": status}
    if outcome:
        payload["outcome"] = outcome
    if result:
        payload["result"] = result
    r = requests.post(f"{API_BASE}/brain/decisions/{decision_id}/status",
                     json=payload,
                     headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        log(f"❌ Set status failed: {r.status_code} {r.text}")
        sys.exit(1)
    log(f"✅ Set status to {status}")
    return r.json()

def get_cockpit(token):
    """GET /api/org/cockpit"""
    r = requests.get(f"{API_BASE}/org/cockpit",
                    headers={"Authorization": f"Bearer {token}"})
    return r.status_code, r.json() if r.status_code == 200 else r.text

def get_progress(token):
    """GET /api/org/progress"""
    r = requests.get(f"{API_BASE}/org/progress",
                    headers={"Authorization": f"Bearer {token}"})
    return r.status_code, r.json() if r.status_code == 200 else r.text

def check_leakage(text, decision_obj=None):
    """Check for leakage of hidden strategy numbers"""
    forbidden = ["100 crore", "100 Cr", "Mar 2027"]
    text_str = json.dumps(text) if isinstance(text, dict) else str(text)
    if decision_obj:
        text_str += json.dumps(decision_obj)
    
    for phrase in forbidden:
        if phrase in text_str:
            log(f"❌ LEAKAGE DETECTED: Found '{phrase}' in response")
            return False
    return True

def get_org(token):
    """GET /api/org"""
    r = requests.get(f"{API_BASE}/org",
                    headers={"Authorization": f"Bearer {token}"})
    return r.status_code, r.json() if r.status_code == 200 else r.text

def main():
    log("=" * 80)
    log("FEATURE (c) TEST: founder-only goal_impact + achievement journey")
    log("=" * 80)
    
    # Login as founder
    founder_token, founder_data = login(FOUNDER_EMAIL, FOUNDER_PASSWORD)
    
    # Check if founder has an org
    org_status, org_data = get_org(founder_token)
    if org_status != 200:
        log(f"❌ Founder does not have an org (status {org_status}). Expected org 'Acme Solar' to exist.")
        log(f"Response: {org_data}")
        sys.exit(1)
    
    log(f"✅ Founder is in org: {org_data.get('name')} (role: {org_data.get('role')})")
    
    # Create fresh member
    member_token, member_data, member_email, member_password = signup_fresh_member()
    
    # Founder creates invite
    invite_code = create_invite(founder_token)
    
    # Member joins org
    join_org(member_token, invite_code)
    
    # Re-login member to get updated org_id/org_role
    member_token, member_data = login(member_email, member_password)
    
    log("\n" + "=" * 80)
    log("TEST 1: LLM CALL 1 - FOUNDER POST /api/brain/ask (decide question)")
    log("=" * 80)
    
    founder_question = "A walk-in residential customer wants a 2kW rooftop system but is pushing the price down to about a 9% margin. Should I take the deal?"
    founder_response = brain_ask(founder_token, founder_question)
    
    # CRITICAL ASSERTIONS for TEST 1
    test1_pass = True
    
    # Check mode=decide
    if founder_response.get("mode") != "decide":
        log(f"❌ TEST 1 FAIL: mode is '{founder_response.get('mode')}', expected 'decide'")
        test1_pass = False
    else:
        log(f"✅ mode=decide")
    
    # Check decision_id present
    if not founder_response.get("decision_id"):
        log(f"❌ TEST 1 FAIL: decision_id not present")
        test1_pass = False
    else:
        log(f"✅ decision_id present: {founder_response['decision_id']}")
    
    # CRITICAL: response CONTAINS "goal_impact"
    if "goal_impact" not in founder_response:
        log(f"❌ TEST 1 FAIL: 'goal_impact' key NOT found in founder response")
        test1_pass = False
    else:
        goal_impact = founder_response["goal_impact"]
        log(f"✅ 'goal_impact' key present in founder response")
        
        # Validate goal_impact structure
        required_keys = ["score", "band", "label", "reason"]
        for key in required_keys:
            if key not in goal_impact:
                log(f"❌ TEST 1 FAIL: goal_impact missing key '{key}'")
                test1_pass = False
            else:
                log(f"✅ goal_impact.{key} = {goal_impact[key]}")
        
        # Validate score is 0-100
        if not isinstance(goal_impact.get("score"), int) or not (0 <= goal_impact["score"] <= 100):
            log(f"❌ TEST 1 FAIL: goal_impact.score is not an int 0-100: {goal_impact.get('score')}")
            test1_pass = False
        
        # Validate band is high/medium/low
        if goal_impact.get("band") not in ["high", "medium", "low"]:
            log(f"❌ TEST 1 FAIL: goal_impact.band is not high/medium/low: {goal_impact.get('band')}")
            test1_pass = False
        
        # Check for leakage in goal_impact.reason
        if not check_leakage(goal_impact.get("reason", "")):
            log(f"❌ TEST 1 FAIL: goal_impact.reason contains forbidden phrases")
            test1_pass = False
        else:
            log(f"✅ goal_impact.reason does NOT leak hidden strategy numbers")
    
    # CRITICAL: response does NOT contain "strategic_alignment"
    if "strategic_alignment" in founder_response:
        log(f"❌ TEST 1 FAIL: 'strategic_alignment' key found in founder response (should be stripped)")
        test1_pass = False
    else:
        log(f"✅ 'strategic_alignment' key NOT in founder response (correctly stripped)")
    
    if test1_pass:
        log("\n✅ TEST 1 PASSED")
    else:
        log("\n❌ TEST 1 FAILED")
        sys.exit(1)
    
    founder_decision_id = founder_response["decision_id"]
    
    log("\n" + "=" * 80)
    log("TEST 2: LLM CALL 2 - MEMBER POST /api/brain/ask (decide question)")
    log("=" * 80)
    
    member_question = "A C&I customer wants a 50L rooftop system and is willing to pay for 18% margin. Should I take the deal?"
    member_response = brain_ask(member_token, member_question)
    
    # CRITICAL ASSERTIONS for TEST 2
    test2_pass = True
    
    # Check mode=decide
    if member_response.get("mode") != "decide":
        log(f"❌ TEST 2 FAIL: mode is '{member_response.get('mode')}', expected 'decide'")
        test2_pass = False
    else:
        log(f"✅ mode=decide")
    
    # Check decision_id present
    if not member_response.get("decision_id"):
        log(f"❌ TEST 2 FAIL: decision_id not present")
        test2_pass = False
    else:
        log(f"✅ decision_id present: {member_response['decision_id']}")
    
    # CRITICAL: response does NOT contain "goal_impact"
    if "goal_impact" in member_response:
        log(f"❌ TEST 2 FAIL: 'goal_impact' key found in member response (members should NEVER see this)")
        test2_pass = False
    else:
        log(f"✅ 'goal_impact' key NOT in member response (correctly hidden from members)")
    
    # CRITICAL: response does NOT contain "strategic_alignment"
    if "strategic_alignment" in member_response:
        log(f"❌ TEST 2 FAIL: 'strategic_alignment' key found in member response (should be stripped)")
        test2_pass = False
    else:
        log(f"✅ 'strategic_alignment' key NOT in member response (correctly stripped)")
    
    if test2_pass:
        log("\n✅ TEST 2 PASSED")
    else:
        log("\n❌ TEST 2 FAILED")
        sys.exit(1)
    
    member_decision_id = member_response["decision_id"]
    
    log("\n" + "=" * 80)
    log("TEST 3: FREE - MEMBER GET /api/brain/decisions (history check)")
    log("=" * 80)
    
    member_decisions = get_decisions(member_token)
    
    test3_pass = True
    
    if not member_decisions:
        log(f"❌ TEST 3 FAIL: No decisions returned")
        test3_pass = False
    else:
        log(f"✅ Retrieved {len(member_decisions)} decision(s)")
        
        # Check NO row contains goal_impact, strategic_alignment, or alignment_band
        for i, dec in enumerate(member_decisions):
            if "goal_impact" in dec:
                log(f"❌ TEST 3 FAIL: Decision {i} contains 'goal_impact' (should never be in history)")
                test3_pass = False
            if "strategic_alignment" in dec:
                log(f"❌ TEST 3 FAIL: Decision {i} contains 'strategic_alignment' (should be stripped)")
                test3_pass = False
            if "alignment_band" in dec:
                log(f"❌ TEST 3 FAIL: Decision {i} contains 'alignment_band' (founder-only field)")
                test3_pass = False
        
        if test3_pass:
            log(f"✅ NO decision contains goal_impact, strategic_alignment, or alignment_band")
    
    if test3_pass:
        log("\n✅ TEST 3 PASSED")
    else:
        log("\n❌ TEST 3 FAILED")
        sys.exit(1)
    
    log("\n" + "=" * 80)
    log("TEST 4: FREE - Achievement via decisions (commit -> status -> cockpit)")
    log("=" * 80)
    
    # 4a: Member commits action
    commit_response = commit_action(member_token, member_decision_id, 
                                    "Send the C&I proposal at 19% margin today", 
                                    due_in_hours=48)
    
    test4_pass = True
    
    if commit_response.get("status") != "open":
        log(f"❌ TEST 4a FAIL: status is '{commit_response.get('status')}', expected 'open'")
        test4_pass = False
    else:
        log(f"✅ Commit returned status=open")
    
    # 4b: Member marks as done with outcome
    status_response = set_status(member_token, member_decision_id, 
                                status="done", 
                                outcome="worked",
                                result="Closed a C&I deal at 19% margin")
    
    if status_response.get("status") != "done":
        log(f"❌ TEST 4b FAIL: status is '{status_response.get('status')}', expected 'done'")
        test4_pass = False
    else:
        log(f"✅ Status set to done")
    
    if status_response.get("outcome", {}).get("status") != "success":
        log(f"❌ TEST 4b FAIL: outcome.status is '{status_response.get('outcome', {}).get('status')}', expected 'success'")
        test4_pass = False
    else:
        log(f"✅ outcome.status=success (worked -> success)")
    
    # 4c: Founder gets cockpit
    cockpit_status, cockpit_data = get_cockpit(founder_token)
    
    if cockpit_status != 200:
        log(f"❌ TEST 4c FAIL: Founder cockpit returned {cockpit_status}")
        test4_pass = False
    else:
        log(f"✅ Founder GET /api/org/cockpit returned 200")
        
        # Check alignment.scored increased
        if "alignment" not in cockpit_data or "scored" not in cockpit_data["alignment"]:
            log(f"❌ TEST 4c FAIL: alignment.scored not present")
            test4_pass = False
        else:
            scored = cockpit_data["alignment"]["scored"]
            log(f"✅ alignment.scored = {scored} (should be >= 2 from founder + member asks)")
            if scored < 2:
                log(f"⚠️  WARNING: alignment.scored is {scored}, expected >= 2")
        
        # Check execution.done >= 1
        if "execution" not in cockpit_data or "done" not in cockpit_data["execution"]:
            log(f"❌ TEST 4c FAIL: execution.done not present")
            test4_pass = False
        else:
            done = cockpit_data["execution"]["done"]
            log(f"✅ execution.done = {done}")
            if done < 1:
                log(f"❌ TEST 4c FAIL: execution.done is {done}, expected >= 1")
                test4_pass = False
        
        # Check results[] contains member's result
        if "results" not in cockpit_data:
            log(f"❌ TEST 4c FAIL: results[] not present")
            test4_pass = False
        else:
            results = cockpit_data["results"]
            log(f"✅ results[] present with {len(results)} item(s)")
            found_result = False
            for res in results:
                if "Closed a C&I deal at 19% margin" in res.get("result", ""):
                    found_result = True
                    log(f"✅ Found member's result in results[]: {res['result']}")
                    break
            if not found_result:
                log(f"❌ TEST 4c FAIL: Member's result text not found in results[]")
                test4_pass = False
        
        # Check follow_through_pct present
        if "execution" not in cockpit_data or "follow_through_pct" not in cockpit_data["execution"]:
            log(f"❌ TEST 4c FAIL: follow_through_pct not present")
            test4_pass = False
        else:
            ft = cockpit_data["execution"]["follow_through_pct"]
            log(f"✅ follow_through_pct = {ft}")
        
        # Check goal_progress still present (features a/b intact)
        if "goal_progress" not in cockpit_data:
            log(f"❌ TEST 4c FAIL: goal_progress not present (features a/b should be intact)")
            test4_pass = False
        else:
            log(f"✅ goal_progress present (features a/b intact)")
        
        # Check pacing key still present
        if "pacing" not in cockpit_data:
            log(f"⚠️  WARNING: pacing key not present (may be None if no ARR set)")
        else:
            log(f"✅ pacing key present")
    
    if test4_pass:
        log("\n✅ TEST 4 PASSED")
    else:
        log("\n❌ TEST 4 FAILED")
        sys.exit(1)
    
    log("\n" + "=" * 80)
    log("TEST 5: FREE - Members are walled off (403 checks)")
    log("=" * 80)
    
    test5_pass = True
    
    # 5a: Member GET /api/org/cockpit -> 403
    cockpit_status, cockpit_data = get_cockpit(member_token)
    if cockpit_status != 403:
        log(f"❌ TEST 5a FAIL: Member cockpit returned {cockpit_status}, expected 403")
        test5_pass = False
    else:
        log(f"✅ Member GET /api/org/cockpit returned 403")
    
    # 5b: Member GET /api/org/progress -> 403
    progress_status, progress_data = get_progress(member_token)
    if progress_status != 403:
        log(f"❌ TEST 5b FAIL: Member progress returned {progress_status}, expected 403")
        test5_pass = False
    else:
        log(f"✅ Member GET /api/org/progress returned 403")
    
    if test5_pass:
        log("\n✅ TEST 5 PASSED")
    else:
        log("\n❌ TEST 5 FAILED")
        sys.exit(1)
    
    log("\n" + "=" * 80)
    log("SUMMARY")
    log("=" * 80)
    log(f"Total LLM calls used: {llm_call_count} (budget: 3)")
    log("")
    log("✅ TEST 1 PASSED: Founder POST /api/brain/ask contains goal_impact, NOT strategic_alignment")
    log("✅ TEST 2 PASSED: Member POST /api/brain/ask does NOT contain goal_impact or strategic_alignment")
    log("✅ TEST 3 PASSED: Member GET /api/brain/decisions has NO goal_impact/strategic_alignment/alignment_band")
    log("✅ TEST 4 PASSED: Achievement journey (commit->done->cockpit) working, features a/b intact")
    log("✅ TEST 5 PASSED: Members walled off from cockpit and progress")
    log("")
    log("=" * 80)
    log("🎉 ALL TESTS PASSED")
    log("=" * 80)

if __name__ == "__main__":
    main()
