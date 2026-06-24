#!/usr/bin/env python3
"""
Backend test for Connected Decision Session (Execution OS Sprint 1)
Testing /app/backend/decision_brain.py and /app/backend/organizations.py

CRITICAL: ANTHROPIC IS LIVE - HARD CAP: at most 3 LLM calls total
LLM endpoints: POST /api/brain/ask, POST /api/brain/decisions/{id}/next-step
All other endpoints are FREE
"""
import requests
import uuid
import json
import time

# Backend URL from frontend/.env
BASE_URL = "https://87accb52-51df-41be-9938-10ad721ed87e.preview.emergentagent.com/api"

# Credentials
FOUNDER_EMAIL = "ceo@smartdecigen.com"
FOUNDER_PASSWORD = "FounderOS@2026"

# Test state
founder_token = None
member_token = None
org_id = None
session_id = None
decision_id_1 = None
decision_id_2 = None
member_email = None
member_password = "Member1234!"

def log(msg):
    print(f"\n{'='*80}")
    print(f"  {msg}")
    print(f"{'='*80}")

def assert_field(response, field, expected=None, should_exist=True, should_not_exist=False):
    """Assert field presence/absence and optionally value"""
    data = response.json() if hasattr(response, 'json') else response
    
    if should_not_exist:
        if field in data:
            raise AssertionError(f"❌ Field '{field}' should NOT exist but found: {data.get(field)}")
        print(f"  ✓ Field '{field}' correctly NOT present")
        return
    
    if should_exist:
        if field not in data:
            raise AssertionError(f"❌ Field '{field}' missing from response: {json.dumps(data, indent=2)}")
        print(f"  ✓ Field '{field}' present: {data[field]}")
    
    if expected is not None:
        actual = data.get(field)
        if actual != expected:
            raise AssertionError(f"❌ Field '{field}' expected {expected}, got {actual}")
        print(f"  ✓ Field '{field}' = {expected}")
    
    return data.get(field)

def assert_non_empty_string(response, field):
    """Assert field is a non-empty string"""
    data = response.json() if hasattr(response, 'json') else response
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise AssertionError(f"❌ Field '{field}' should be non-empty string, got: {value}")
    print(f"  ✓ Field '{field}' is non-empty string: '{value[:100]}...'")
    return value

def assert_string_or_null(response, field):
    """Assert field is either a string or null"""
    data = response.json() if hasattr(response, 'json') else response
    value = data.get(field)
    if value is not None and not isinstance(value, str):
        raise AssertionError(f"❌ Field '{field}' should be string or null, got: {type(value).__name__}")
    print(f"  ✓ Field '{field}' is string or null: {value}")
    return value

def setup_org_and_member():
    """Setup: Login as founder, create org, set strategy, create member"""
    global founder_token, member_token, org_id, member_email
    
    log("SETUP: Login as founder")
    r = requests.post(f"{BASE_URL}/auth/login", json={
        "email": FOUNDER_EMAIL,
        "password": FOUNDER_PASSWORD
    })
    assert r.status_code == 200, f"Founder login failed: {r.status_code} {r.text}"
    founder_token = r.json()["token"]
    print(f"  ✓ Founder logged in, token: {founder_token[:20]}...")
    
    # Check if org already exists
    log("SETUP: Check if org exists")
    r = requests.get(f"{BASE_URL}/org", headers={"Authorization": f"Bearer {founder_token}"})
    if r.status_code == 200:
        org_id = r.json()["id"]
        print(f"  ✓ Org already exists: {r.json()['name']} (id: {org_id})")
        
        # Check if strategy is set
        r = requests.get(f"{BASE_URL}/org/strategy", headers={"Authorization": f"Bearer {founder_token}"})
        if r.status_code == 200 and r.json().get("north_star"):
            print(f"  ✓ Strategy already set: {r.json()['north_star'][:50]}...")
        else:
            log("SETUP: Set strategy")
            r = requests.put(f"{BASE_URL}/org/strategy", headers={"Authorization": f"Bearer {founder_token}"}, json={
                "north_star": "Reach 100 crore annual revenue in solar EPC",
                "target": "100 Cr ARR",
                "deadline": "Mar 2027",
                "priorities": [
                    "Win commercial & industrial rooftop deals",
                    "Push EPC ticket sizes above 50L",
                    "Protect 18% margins"
                ],
                "decision_rules": "Never quote below 18% margin. Prefer C&I over residential. Decline deals that squeeze margins below 18%."
            })
            assert r.status_code == 200, f"Set strategy failed: {r.status_code} {r.text}"
            print(f"  ✓ Strategy set")
    else:
        log("SETUP: Create org")
        r = requests.post(f"{BASE_URL}/org", headers={"Authorization": f"Bearer {founder_token}"}, json={
            "name": "Acme Solar"
        })
        assert r.status_code == 200, f"Create org failed: {r.status_code} {r.text}"
        org_id = r.json()["id"]
        print(f"  ✓ Org created: Acme Solar (id: {org_id})")
        
        log("SETUP: Set strategy")
        r = requests.put(f"{BASE_URL}/org/strategy", headers={"Authorization": f"Bearer {founder_token}"}, json={
            "north_star": "Reach 100 crore annual revenue in solar EPC",
            "target": "100 Cr ARR",
            "deadline": "Mar 2027",
            "priorities": [
                "Win commercial & industrial rooftop deals",
                "Push EPC ticket sizes above 50L",
                "Protect 18% margins"
            ],
            "decision_rules": "Never quote below 18% margin. Prefer C&I over residential. Decline deals that squeeze margins below 18%."
        })
        assert r.status_code == 200, f"Set strategy failed: {r.status_code} {r.text}"
        print(f"  ✓ Strategy set")
    
    # Create member
    log("SETUP: Create member and join org")
    member_email = f"member_{uuid.uuid4().hex[:8]}@acmesolar.com"
    
    # Create invite
    r = requests.post(f"{BASE_URL}/org/invites", headers={"Authorization": f"Bearer {founder_token}"}, json={})
    assert r.status_code == 200, f"Create invite failed: {r.status_code} {r.text}"
    invite_code = r.json()["code"]
    print(f"  ✓ Invite created: {invite_code}")
    
    # Signup member
    r = requests.post(f"{BASE_URL}/auth/signup", json={
        "name": "Test Member",
        "email": member_email,
        "password": member_password
    })
    assert r.status_code == 200, f"Member signup failed: {r.status_code} {r.text}"
    member_token = r.json()["token"]
    print(f"  ✓ Member signed up: {member_email}")
    
    # Join org
    r = requests.post(f"{BASE_URL}/org/join", headers={"Authorization": f"Bearer {member_token}"}, json={
        "code": invite_code
    })
    assert r.status_code == 200, f"Join org failed: {r.status_code} {r.text}"
    print(f"  ✓ Member joined org")

def test_1_llm_call_1():
    """LLM CALL 1 - POST /api/brain/ask with session_id"""
    global session_id, decision_id_1
    
    log("TEST 1: LLM CALL 1 - POST /api/brain/ask (first turn)")
    
    session_id = str(uuid.uuid4())
    print(f"  Generated session_id: {session_id}")
    
    r = requests.post(f"{BASE_URL}/brain/ask", headers={"Authorization": f"Bearer {member_token}"}, json={
        "question": "A walk-in customer wants a steep discount that drops our margin to about 9%. Should I take it?",
        "session_id": session_id
    })
    
    assert r.status_code == 200, f"Ask failed: {r.status_code} {r.text}"
    print(f"  ✓ Status: 200")
    
    data = r.json()
    
    # Assert required fields
    decision_id_1 = assert_field(data, "decision_id", should_exist=True)
    assert_field(data, "session_id", expected=session_id)
    
    # Assert next_action is non-empty string
    next_action = assert_non_empty_string(data, "next_action")
    
    # Assert hook is non-empty string
    hook = assert_non_empty_string(data, "hook")
    
    # Assert situation_read is present (may be empty string)
    assert_field(data, "situation_read", should_exist=True)
    
    # Assert sharpening_question is string or null
    assert_string_or_null(data, "sharpening_question")
    
    # CRITICAL: response MUST NOT contain "strategic_alignment"
    assert_field(data, "strategic_alignment", should_not_exist=True)
    
    print(f"\n  📊 Response summary:")
    print(f"     - decision_id: {decision_id_1}")
    print(f"     - session_id: {session_id}")
    print(f"     - next_action: {next_action[:80]}...")
    print(f"     - hook: {hook[:80]}...")
    print(f"     - mode: {data.get('mode')}")
    print(f"     - cost: {data.get('cost')} credits")
    
    return data

def test_2_llm_call_2():
    """LLM CALL 2 - POST /api/brain/ask with SAME session_id (multi-turn)"""
    global decision_id_2
    
    log("TEST 2: LLM CALL 2 - POST /api/brain/ask (second turn, SAME session)")
    
    print(f"  Using SAME session_id: {session_id}")
    
    r = requests.post(f"{BASE_URL}/brain/ask", headers={"Authorization": f"Bearer {member_token}"}, json={
        "question": "Okay, what if instead I offer them a referral deal to keep the margin healthy?",
        "session_id": session_id
    })
    
    assert r.status_code == 200, f"Ask failed: {r.status_code} {r.text}"
    print(f"  ✓ Status: 200")
    
    data = r.json()
    
    # Assert required fields
    decision_id_2 = assert_field(data, "decision_id", should_exist=True)
    assert_field(data, "session_id", expected=session_id)
    
    # Assert next_action is non-empty string
    next_action = assert_non_empty_string(data, "next_action")
    
    # Assert hook is non-empty string
    hook = assert_non_empty_string(data, "hook")
    
    # CRITICAL: response MUST NOT contain "strategic_alignment"
    assert_field(data, "strategic_alignment", should_not_exist=True)
    
    print(f"\n  📊 Response summary:")
    print(f"     - decision_id: {decision_id_2}")
    print(f"     - session_id: {session_id}")
    print(f"     - next_action: {next_action[:80]}...")
    print(f"     - hook: {hook[:80]}...")
    print(f"     - mode: {data.get('mode')}")
    print(f"     - cost: {data.get('cost')} credits")
    
    # Verify both decisions share same session_id
    log("TEST 2: Verify both decisions share same session_id")
    r = requests.get(f"{BASE_URL}/brain/decisions", headers={"Authorization": f"Bearer {member_token}"})
    assert r.status_code == 200, f"Get decisions failed: {r.status_code} {r.text}"
    
    decisions = r.json()["decisions"]
    d1 = next((d for d in decisions if d["id"] == decision_id_1), None)
    d2 = next((d for d in decisions if d["id"] == decision_id_2), None)
    
    assert d1 is not None, f"Decision 1 not found in history"
    assert d2 is not None, f"Decision 2 not found in history"
    
    assert d1["session_id"] == session_id, f"Decision 1 session_id mismatch"
    assert d2["session_id"] == session_id, f"Decision 2 session_id mismatch"
    
    print(f"  ✓ Both decisions share session_id: {session_id}")
    
    return data

def test_3_commit():
    """FREE - POST /api/brain/decisions/{id}/commit"""
    log("TEST 3: FREE - POST /api/brain/decisions/{id}/commit")
    
    r = requests.post(f"{BASE_URL}/brain/decisions/{decision_id_1}/commit", 
                     headers={"Authorization": f"Bearer {member_token}"}, 
                     json={
                         "action": "Call the customer and offer the referral deal",
                         "due_in_hours": 24
                     })
    
    assert r.status_code == 200, f"Commit failed: {r.status_code} {r.text}"
    print(f"  ✓ Status: 200")
    
    data = r.json()
    assert_field(data, "status", expected="open")
    assert_field(data, "due_at", should_exist=True)
    
    print(f"  ✓ Committed action: {data['committed_action']}")
    print(f"  ✓ Status: {data['status']}")
    print(f"  ✓ Due at: {data['due_at']}")
    
    # Test GET /api/brain/active
    log("TEST 3: FREE - GET /api/brain/active")
    r = requests.get(f"{BASE_URL}/brain/active", headers={"Authorization": f"Bearer {member_token}"})
    assert r.status_code == 200, f"Get active failed: {r.status_code} {r.text}"
    
    data = r.json()
    assert_field(data, "open_commitments", should_exist=True)
    assert data["open_commitments"] >= 1, f"Expected open_commitments >= 1, got {data['open_commitments']}"
    print(f"  ✓ open_commitments: {data['open_commitments']}")
    
    assert_field(data, "next", should_exist=True)
    next_item = data["next"]
    assert next_item["decision_id"] == decision_id_1, f"Expected next.decision_id == {decision_id_1}, got {next_item['decision_id']}"
    assert_field(next_item, "due_at", should_exist=True)
    assert_field(next_item, "overdue", expected=False)
    
    print(f"  ✓ next.decision_id: {next_item['decision_id']}")
    print(f"  ✓ next.due_at: {next_item['due_at']}")
    print(f"  ✓ next.overdue: {next_item['overdue']}")

def test_4_status():
    """FREE - POST /api/brain/decisions/{id}/status"""
    log("TEST 4: FREE - POST /api/brain/decisions/{id}/status")
    
    r = requests.post(f"{BASE_URL}/brain/decisions/{decision_id_1}/status", 
                     headers={"Authorization": f"Bearer {member_token}"}, 
                     json={
                         "status": "done",
                         "result": "Customer accepted the referral deal, margin protected at 18%"
                     })
    
    assert r.status_code == 200, f"Status update failed: {r.status_code} {r.text}"
    print(f"  ✓ Status: 200")
    
    data = r.json()
    assert_field(data, "status", expected="done")
    assert_field(data, "result", expected="Customer accepted the referral deal, margin protected at 18%")
    
    print(f"  ✓ Status: {data['status']}")
    print(f"  ✓ Result: {data['result']}")
    
    # Test GET /api/brain/active again
    log("TEST 4: FREE - GET /api/brain/active (after done)")
    r = requests.get(f"{BASE_URL}/brain/active", headers={"Authorization": f"Bearer {member_token}"})
    assert r.status_code == 200, f"Get active failed: {r.status_code} {r.text}"
    
    data = r.json()
    assert_field(data, "done_total", should_exist=True)
    assert data["done_total"] >= 1, f"Expected done_total >= 1, got {data['done_total']}"
    print(f"  ✓ done_total: {data['done_total']}")
    
    # The decision should no longer be the "next" one
    if data.get("next"):
        assert data["next"]["decision_id"] != decision_id_1, f"Decision {decision_id_1} should not be next after marking done"
        print(f"  ✓ Decision {decision_id_1} no longer the next (correctly decremented)")
    else:
        print(f"  ✓ No next commitment (open_commitments decremented to 0)")

def test_5_llm_call_3():
    """LLM CALL 3 - POST /api/brain/decisions/{id}/next-step"""
    log("TEST 5: LLM CALL 3 - POST /api/brain/decisions/{id}/next-step")
    
    r = requests.post(f"{BASE_URL}/brain/decisions/{decision_id_1}/next-step", 
                     headers={"Authorization": f"Bearer {member_token}"})
    
    assert r.status_code == 200, f"Next-step failed: {r.status_code} {r.text}"
    print(f"  ✓ Status: 200")
    
    data = r.json()
    
    # Assert returns a NEW decision with DIFFERENT decision_id
    new_decision_id = assert_field(data, "decision_id", should_exist=True)
    assert new_decision_id != decision_id_1, f"Expected NEW decision_id, got same: {new_decision_id}"
    print(f"  ✓ NEW decision_id: {new_decision_id} (different from {decision_id_1})")
    
    # Assert SAME session_id
    assert_field(data, "session_id", expected=session_id)
    print(f"  ✓ SAME session_id: {session_id}")
    
    # Assert non-empty next_action and hook
    next_action = assert_non_empty_string(data, "next_action")
    hook = assert_non_empty_string(data, "hook")
    
    # CRITICAL: NO "strategic_alignment" key
    assert_field(data, "strategic_alignment", should_not_exist=True)
    
    print(f"\n  📊 Response summary:")
    print(f"     - decision_id: {new_decision_id}")
    print(f"     - session_id: {session_id}")
    print(f"     - next_action: {next_action[:80]}...")
    print(f"     - hook: {hook[:80]}...")
    print(f"     - mode: {data.get('mode')}")
    print(f"     - cost: {data.get('cost')} credits")

def test_6_cockpit():
    """FREE - GET /api/org/cockpit (owner-only)"""
    log("TEST 6: FREE - GET /api/org/cockpit (owner)")
    
    r = requests.get(f"{BASE_URL}/org/cockpit", headers={"Authorization": f"Bearer {founder_token}"})
    assert r.status_code == 200, f"Cockpit failed: {r.status_code} {r.text}"
    print(f"  ✓ Status: 200")
    
    data = r.json()
    
    # Assert required keys
    assert_field(data, "north_star", should_exist=True)
    assert_field(data, "totals", should_exist=True)
    assert_field(data, "alignment", should_exist=True)
    assert_field(data, "execution", should_exist=True)
    assert_field(data, "per_member", should_exist=True)
    assert_field(data, "drift", should_exist=True)
    assert_field(data, "active_actions", should_exist=True)
    assert_field(data, "results", should_exist=True)
    
    # Check active_actions structure
    active_actions = data["active_actions"]
    assert isinstance(active_actions, list), f"active_actions should be array"
    print(f"  ✓ active_actions is array with {len(active_actions)} items")
    
    # Check results structure
    results = data["results"]
    assert isinstance(results, list), f"results should be array"
    print(f"  ✓ results is array with {len(results)} items")
    
    # Check execution.overdue
    execution = data["execution"]
    assert_field(execution, "overdue", should_exist=True)
    assert isinstance(execution["overdue"], int), f"execution.overdue should be number"
    print(f"  ✓ execution.overdue: {execution['overdue']}")
    
    # Check that results contain the done decision with result text
    if results:
        result_item = results[0]
        assert_field(result_item, "result", should_exist=True)
        print(f"  ✓ results[0].result: {result_item['result'][:50]}...")
    
    # Test member GET /api/org/cockpit -> 403
    log("TEST 6: FREE - GET /api/org/cockpit (member -> 403)")
    r = requests.get(f"{BASE_URL}/org/cockpit", headers={"Authorization": f"Bearer {member_token}"})
    assert r.status_code == 403, f"Expected 403 for member, got {r.status_code}"
    print(f"  ✓ Member correctly blocked with 403")
    
    # Test member-facing payloads do NOT contain strategic_alignment
    log("TEST 6: FREE - Verify NO strategic_alignment in member-facing payloads")
    
    # Check GET /api/brain/decisions
    r = requests.get(f"{BASE_URL}/brain/decisions", headers={"Authorization": f"Bearer {member_token}"})
    assert r.status_code == 200, f"Get decisions failed: {r.status_code} {r.text}"
    decisions = r.json()["decisions"]
    for d in decisions:
        if "strategic_alignment" in d:
            raise AssertionError(f"❌ strategic_alignment found in decision {d['id']}")
    print(f"  ✓ GET /api/brain/decisions: NO strategic_alignment in {len(decisions)} decisions")
    
    # Check GET /api/brain/active
    r = requests.get(f"{BASE_URL}/brain/active", headers={"Authorization": f"Bearer {member_token}"})
    assert r.status_code == 200, f"Get active failed: {r.status_code} {r.text}"
    active_data = r.json()
    if "strategic_alignment" in active_data:
        raise AssertionError(f"❌ strategic_alignment found in /active response")
    print(f"  ✓ GET /api/brain/active: NO strategic_alignment")

def test_7_validation():
    """FREE - Validation tests"""
    log("TEST 7: FREE - Validation tests")
    
    # Test commit with due_in_hours=0 -> 422
    print("\n  Test: commit with due_in_hours=0 -> 422")
    r = requests.post(f"{BASE_URL}/brain/decisions/{decision_id_2}/commit", 
                     headers={"Authorization": f"Bearer {member_token}"}, 
                     json={
                         "action": "Test action",
                         "due_in_hours": 0
                     })
    assert r.status_code == 422, f"Expected 422 for due_in_hours=0, got {r.status_code}"
    print(f"  ✓ due_in_hours=0 correctly rejected with 422")
    
    # Test commit with due_in_hours=99999 -> 422
    print("\n  Test: commit with due_in_hours=99999 -> 422")
    r = requests.post(f"{BASE_URL}/brain/decisions/{decision_id_2}/commit", 
                     headers={"Authorization": f"Bearer {member_token}"}, 
                     json={
                         "action": "Test action",
                         "due_in_hours": 99999
                     })
    assert r.status_code == 422, f"Expected 422 for due_in_hours=99999, got {r.status_code}"
    print(f"  ✓ due_in_hours=99999 correctly rejected with 422")
    
    # Test status with status="bogus" -> 422
    print("\n  Test: status with status='bogus' -> 422")
    r = requests.post(f"{BASE_URL}/brain/decisions/{decision_id_2}/status", 
                     headers={"Authorization": f"Bearer {member_token}"}, 
                     json={
                         "status": "bogus"
                     })
    assert r.status_code == 422, f"Expected 422 for status='bogus', got {r.status_code}"
    print(f"  ✓ status='bogus' correctly rejected with 422")
    
    # Test next-step on unknown decision -> 404
    print("\n  Test: next-step on unknown decision -> 404")
    fake_id = str(uuid.uuid4())
    r = requests.post(f"{BASE_URL}/brain/decisions/{fake_id}/next-step", 
                     headers={"Authorization": f"Bearer {member_token}"})
    assert r.status_code == 404, f"Expected 404 for unknown decision, got {r.status_code}"
    print(f"  ✓ Unknown decision correctly rejected with 404")
    
    # Test next-step on someone else's decision -> 404
    print("\n  Test: next-step on someone else's decision -> 404")
    # Use founder token to try to access member's decision
    r = requests.post(f"{BASE_URL}/brain/decisions/{decision_id_1}/next-step", 
                     headers={"Authorization": f"Bearer {founder_token}"})
    assert r.status_code == 404, f"Expected 404 for other user's decision, got {r.status_code}"
    print(f"  ✓ Other user's decision correctly rejected with 404")

def main():
    try:
        setup_org_and_member()
        
        # LLM CALLS (max 3)
        test_1_llm_call_1()  # LLM CALL 1
        test_2_llm_call_2()  # LLM CALL 2
        
        # FREE TESTS
        test_3_commit()
        test_4_status()
        
        # LLM CALL 3
        test_5_llm_call_3()  # LLM CALL 3
        
        # FREE TESTS
        test_6_cockpit()
        test_7_validation()
        
        log("✅ ALL TESTS PASSED")
        print("\n🎉 Connected Decision Session backend is working correctly!")
        print(f"\n📊 LLM calls used: 3 (within budget)")
        print(f"   - Call 1: POST /api/brain/ask (first turn)")
        print(f"   - Call 2: POST /api/brain/ask (second turn, multi-turn memory)")
        print(f"   - Call 3: POST /api/brain/decisions/{{id}}/next-step")
        
    except AssertionError as e:
        log(f"❌ TEST FAILED")
        print(f"\n{e}")
        raise
    except Exception as e:
        log(f"❌ UNEXPECTED ERROR")
        print(f"\n{e}")
        raise

if __name__ == "__main__":
    main()
