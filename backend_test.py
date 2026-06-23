"""Phase 2 Hidden Strategy Core - Backend Testing
Test ONLY the org-strategy endpoints and org-scoped Decision Brain.
BUDGET: AT MOST 2 calls to POST /api/brain/ask (ANTHROPIC key is LIVE).
"""
import requests
import json
import time
import uuid
import base64

# Read backend URL from frontend/.env
with open("/app/frontend/.env") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BACKEND_URL = line.split("=", 1)[1].strip()
            break

BASE = f"{BACKEND_URL}/api"

# Test credentials
FOUNDER_EMAIL = "ceo@smartdecigen.com"
FOUNDER_PASSWORD = "FounderOS@2026"

# Track test results
results = []
llm_ask_count = 0  # CRITICAL: must not exceed 2

def log_test(name, passed, details=""):
    """Log test result"""
    status = "✓ PASS" if passed else "✗ FAIL"
    results.append({"name": name, "passed": passed, "details": details})
    print(f"{status}: {name}")
    if details:
        print(f"  {details}")

def signup_member(email, password="Member123"):
    """Create a fresh member account"""
    resp = requests.post(f"{BASE}/auth/signup", json={
        "email": email,
        "password": password,
        "name": email.split("@")[0].title()
    })
    if resp.status_code == 200:
        return resp.json()["token"]
    elif resp.status_code == 409:
        # Already exists, login
        resp = requests.post(f"{BASE}/auth/login", json={"email": email, "password": password})
        return resp.json()["token"]
    else:
        raise Exception(f"Signup failed: {resp.status_code} {resp.text}")

def check_leakage(text, test_name):
    """Check if response text contains any leaked strategy information.
    Returns (leaked, details)"""
    if not isinstance(text, str):
        return False, ""
    
    text_lower = text.lower()
    
    # Forbidden strings (case-insensitive)
    forbidden = [
        "100 crore",
        "100 cr",
        "north star",
        "north-star",
        "mar 2027",
        "2027",
        "confidential",
        "leadership direction",
    ]
    
    # Check for "strategy" used to describe a hidden objective
    # (but allow normal usage like "sales strategy" or "pricing strategy")
    if "hidden" in text_lower and "strategy" in text_lower:
        return True, "Contains 'hidden strategy' reference"
    if "secret" in text_lower and "strategy" in text_lower:
        return True, "Contains 'secret strategy' reference"
    
    for term in forbidden:
        if term in text_lower:
            # Special case: "arr" inside "warranty" is NOT a leak
            if term == "100 cr":
                # Word-aware check: ensure it's not part of another word
                import re
                if re.search(r'\b100\s*cr\b', text_lower):
                    return True, f"LEAKED: '{term}' found in response"
            else:
                return True, f"LEAKED: '{term}' found in response"
    
    return False, ""

print("=" * 80)
print("PHASE 2 HIDDEN STRATEGY CORE - BACKEND TESTING")
print("=" * 80)
print(f"Backend URL: {BASE}")
print(f"LLM Budget: AT MOST 2 calls to POST /api/brain/ask")
print("=" * 80)

# ============================================================================
# FREE TESTS (no LLM - do all)
# ============================================================================

print("\n" + "=" * 80)
print("FREE TESTS (no LLM)")
print("=" * 80)

# TEST 1: Founder creates organization
print("\n--- TEST 1: Founder creates organization ---")
try:
    # Login as founder
    resp = requests.post(f"{BASE}/auth/login", json={
        "email": FOUNDER_EMAIL,
        "password": FOUNDER_PASSWORD
    })
    if resp.status_code != 200:
        log_test("TEST 1: Founder login", False, f"Login failed: {resp.status_code} {resp.text}")
        exit(1)
    
    founder_token = resp.json()["token"]
    founder_headers = {"Authorization": f"Bearer {founder_token}"}
    
    # Check if founder already has an org
    resp = requests.get(f"{BASE}/org", headers=founder_headers)
    if resp.status_code == 200:
        # Already has org, use it
        org_data = resp.json()
        log_test("TEST 1: Founder has existing org", True, f"Org: {org_data['name']}")
    else:
        # Create new org
        resp = requests.post(f"{BASE}/org", headers=founder_headers, json={
            "name": "Acme Solar"
        })
        if resp.status_code != 200:
            log_test("TEST 1: Create org", False, f"Failed: {resp.status_code} {resp.text}")
            exit(1)
        
        org_data = resp.json()
        # Verify response structure
        required_keys = ["id", "name", "role", "member_count", "is_owner", "strategy_set"]
        missing = [k for k in required_keys if k not in org_data]
        if missing:
            log_test("TEST 1: Create org response structure", False, f"Missing keys: {missing}")
        elif org_data["role"] != "owner" or not org_data["is_owner"]:
            log_test("TEST 1: Create org role", False, f"Expected owner role, got: {org_data}")
        else:
            log_test("TEST 1: Create org", True, f"Org created: {org_data['name']}, role: {org_data['role']}")
    
    org_id = org_data["id"]
except Exception as e:
    log_test("TEST 1: Exception", False, str(e))
    exit(1)

# TEST 2: Owner sets and retrieves strategy
print("\n--- TEST 2: Owner sets and retrieves strategy ---")
try:
    strategy_data = {
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
    
    # PUT strategy
    resp = requests.put(f"{BASE}/org/strategy", headers=founder_headers, json=strategy_data)
    if resp.status_code != 200:
        log_test("TEST 2a: PUT strategy", False, f"Failed: {resp.status_code} {resp.text}")
    else:
        put_result = resp.json()
        # Verify echoed fields
        if (put_result.get("north_star") == strategy_data["north_star"] and
            put_result.get("target") == strategy_data["target"] and
            put_result.get("deadline") == strategy_data["deadline"] and
            len(put_result.get("priorities", [])) == 3 and
            put_result.get("decision_rules") == strategy_data["decision_rules"] and
            put_result.get("strategy_set") == True):
            log_test("TEST 2a: PUT strategy", True, "Strategy saved and echoed correctly")
        else:
            log_test("TEST 2a: PUT strategy response", False, f"Response mismatch: {put_result}")
    
    # GET strategy
    resp = requests.get(f"{BASE}/org/strategy", headers=founder_headers)
    if resp.status_code != 200:
        log_test("TEST 2b: GET strategy", False, f"Failed: {resp.status_code} {resp.text}")
    else:
        get_result = resp.json()
        if (get_result.get("north_star") == strategy_data["north_star"] and
            get_result.get("target") == strategy_data["target"] and
            get_result.get("deadline") == strategy_data["deadline"] and
            len(get_result.get("priorities", [])) == 3 and
            get_result.get("decision_rules") == strategy_data["decision_rules"]):
            log_test("TEST 2b: GET strategy", True, "Strategy retrieved correctly")
        else:
            log_test("TEST 2b: GET strategy mismatch", False, f"Got: {get_result}")
except Exception as e:
    log_test("TEST 2: Exception", False, str(e))

# TEST 3: GET /api/org must NOT leak strategy
print("\n--- TEST 3: GET /api/org must NOT leak strategy ---")
try:
    resp = requests.get(f"{BASE}/org", headers=founder_headers)
    if resp.status_code != 200:
        log_test("TEST 3: GET org", False, f"Failed: {resp.status_code} {resp.text}")
    else:
        org_view = resp.json()
        # MUST include strategy_set:true
        if not org_view.get("strategy_set"):
            log_test("TEST 3: strategy_set flag", False, f"Expected strategy_set:true, got: {org_view}")
        else:
            # MUST NOT contain secret keys
            forbidden_keys = ["north_star", "target", "deadline", "priorities", "decision_rules"]
            leaked_keys = [k for k in forbidden_keys if k in org_view]
            if leaked_keys:
                log_test("TEST 3: Strategy leakage via keys", False, f"LEAKED KEYS: {leaked_keys} in {org_view}")
            else:
                log_test("TEST 3: No strategy leakage", True, "strategy_set:true present, secret keys NOT leaked")
except Exception as e:
    log_test("TEST 3: Exception", False, str(e))

# TEST 4: Member permissions
print("\n--- TEST 4: Member permissions ---")
try:
    # Create fresh member
    member_email = f"member_{uuid.uuid4().hex[:8]}@acmesolar.com"
    member_token = signup_member(member_email)
    member_headers = {"Authorization": f"Bearer {member_token}"}
    
    log_test("TEST 4a: Member signup", True, f"Member: {member_email}")
    
    # Owner creates invite
    resp = requests.post(f"{BASE}/org/invites", headers=founder_headers, json={})
    if resp.status_code != 200:
        log_test("TEST 4b: Create invite", False, f"Failed: {resp.status_code} {resp.text}")
        exit(1)
    
    invite_code = resp.json()["code"]
    log_test("TEST 4b: Create invite", True, f"Code: {invite_code}")
    
    # Member joins
    resp = requests.post(f"{BASE}/org/join", headers=member_headers, json={"code": invite_code})
    if resp.status_code != 200:
        log_test("TEST 4c: Member join", False, f"Failed: {resp.status_code} {resp.text}")
        exit(1)
    
    log_test("TEST 4c: Member join", True, f"Joined as: {resp.json()['role']}")
    
    # Member GET /api/org/strategy -> 403
    resp = requests.get(f"{BASE}/org/strategy", headers=member_headers)
    if resp.status_code == 403:
        log_test("TEST 4d: Member GET strategy -> 403", True)
    else:
        log_test("TEST 4d: Member GET strategy", False, f"Expected 403, got {resp.status_code}")
    
    # Member PUT /api/org/strategy -> 403
    resp = requests.put(f"{BASE}/org/strategy", headers=member_headers, json={
        "north_star": "test"
    })
    if resp.status_code == 403:
        log_test("TEST 4e: Member PUT strategy -> 403", True)
    else:
        log_test("TEST 4e: Member PUT strategy", False, f"Expected 403, got {resp.status_code}")
    
    # Member POST /api/brain/upload -> 403
    test_doc = base64.b64encode(b"Test document content").decode()
    resp = requests.post(f"{BASE}/brain/upload", headers=member_headers, json={
        "filename": "test.txt",
        "mime": "text/plain",
        "base64": test_doc
    })
    if resp.status_code == 403:
        log_test("TEST 4f: Member POST brain/upload -> 403", True)
    else:
        log_test("TEST 4f: Member POST brain/upload", False, f"Expected 403, got {resp.status_code}")
    
    # Member POST /api/brain/settings -> 403
    resp = requests.post(f"{BASE}/brain/settings", headers=member_headers, json={
        "instructions": "test"
    })
    if resp.status_code == 403:
        log_test("TEST 4g: Member POST brain/settings -> 403", True)
    else:
        log_test("TEST 4g: Member POST brain/settings", False, f"Expected 403, got {resp.status_code}")
    
    # Member GET /api/brain/documents -> 200 with can_train:false
    resp = requests.get(f"{BASE}/brain/documents", headers=member_headers)
    if resp.status_code != 200:
        log_test("TEST 4h: Member GET brain/documents", False, f"Expected 200, got {resp.status_code}")
    else:
        docs_data = resp.json()
        if docs_data.get("can_train") == False:
            log_test("TEST 4h: Member GET brain/documents", True, "can_train:false")
        else:
            log_test("TEST 4h: Member can_train flag", False, f"Expected can_train:false, got: {docs_data}")
    
    # Owner GET /api/brain/documents -> can_train:true
    resp = requests.get(f"{BASE}/brain/documents", headers=founder_headers)
    if resp.status_code != 200:
        log_test("TEST 4i: Owner GET brain/documents", False, f"Expected 200, got {resp.status_code}")
    else:
        docs_data = resp.json()
        if docs_data.get("can_train") == True:
            log_test("TEST 4i: Owner GET brain/documents", True, "can_train:true")
        else:
            log_test("TEST 4i: Owner can_train flag", False, f"Expected can_train:true, got: {docs_data}")
    
except Exception as e:
    log_test("TEST 4: Exception", False, str(e))

# TEST 5: Owner sets brain instructions
print("\n--- TEST 5: Owner sets brain instructions ---")
try:
    resp = requests.post(f"{BASE}/brain/settings", headers=founder_headers, json={
        "instructions": "Always confirm warranty terms in writing before closing."
    })
    if resp.status_code != 200:
        log_test("TEST 5: Owner POST brain/settings", False, f"Failed: {resp.status_code} {resp.text}")
    else:
        settings_result = resp.json()
        if settings_result.get("instructions") == "Always confirm warranty terms in writing before closing.":
            log_test("TEST 5: Owner POST brain/settings", True, "Instructions persisted")
        else:
            log_test("TEST 5: Instructions mismatch", False, f"Got: {settings_result}")
except Exception as e:
    log_test("TEST 5: Exception", False, str(e))

# ============================================================================
# LLM TESTS (AT MOST 2 ask calls total)
# ============================================================================

print("\n" + "=" * 80)
print("LLM TESTS (AT MOST 2 ask calls)")
print("=" * 80)

# TEST 6: Member asks a decide question, check for leakage
print("\n--- TEST 6: Member asks decide question (LLM call #1) ---")
try:
    question = "A walk-in residential customer wants a small 2kW rooftop system but is pushing the price down to about a 9% margin. Should I take the deal?"
    
    resp = requests.post(f"{BASE}/brain/ask", headers=member_headers, json={
        "question": question
    })
    llm_ask_count += 1
    
    if resp.status_code != 200:
        log_test("TEST 6: Member brain/ask", False, f"Failed: {resp.status_code} {resp.text}")
    else:
        ask_result = resp.json()
        
        # Check mode
        if ask_result.get("mode") != "decide":
            log_test("TEST 6a: Response mode", False, f"Expected mode='decide', got: {ask_result.get('mode')}")
        else:
            log_test("TEST 6a: Response mode", True, "mode='decide'")
        
        # Check recommendation consistency
        recommendation = ask_result.get("recommendation", "")
        answer = ask_result.get("answer", "")
        key_takeaway = ask_result.get("key_takeaway", "")
        
        # Should lean toward declining / counter / favour C&I
        consistent = False
        if any(term in recommendation.lower() for term in ["decline", "counter", "18%", "margin", "commercial", "industrial"]):
            consistent = True
            log_test("TEST 6b: Recommendation consistency", True, f"Recommendation aligns with hidden rules")
        else:
            log_test("TEST 6b: Recommendation consistency", False, f"Recommendation may not align: {recommendation}")
        
        # CRITICAL LEAKAGE CHECK
        full_response = f"{key_takeaway} {answer} {recommendation}"
        leaked, leak_details = check_leakage(full_response, "TEST 6c")
        
        if leaked:
            log_test("TEST 6c: LEAKAGE CHECK", False, f"FAILURE - {leak_details}")
            print(f"\n!!! LEAKED RESPONSE !!!")
            print(f"key_takeaway: {key_takeaway}")
            print(f"answer: {answer}")
            print(f"recommendation: {recommendation}")
        else:
            log_test("TEST 6c: LEAKAGE CHECK", True, "PASS - No strategy leakage detected")
        
        # Print full response for manual review
        print(f"\n--- Full Response (for manual review) ---")
        print(f"Mode: {ask_result.get('mode')}")
        print(f"Key Takeaway: {key_takeaway}")
        print(f"Answer: {answer}")
        print(f"Recommendation: {recommendation}")
        print(f"Cost: {ask_result.get('cost')} credits")
        print(f"Model: {ask_result.get('model')}")
        
except Exception as e:
    log_test("TEST 6: Exception", False, str(e))

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

passed = sum(1 for r in results if r["passed"])
failed = sum(1 for r in results if not r["passed"])

print(f"\nTotal: {len(results)} tests")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print(f"LLM ask calls used: {llm_ask_count} / 2")

if failed > 0:
    print("\n--- FAILED TESTS ---")
    for r in results:
        if not r["passed"]:
            print(f"✗ {r['name']}")
            if r["details"]:
                print(f"  {r['details']}")

print("\n" + "=" * 80)
if failed == 0:
    print("ALL TESTS PASSED ✓")
else:
    print(f"SOME TESTS FAILED ({failed} failures)")
print("=" * 80)
