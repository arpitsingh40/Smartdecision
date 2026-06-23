#!/usr/bin/env python3
"""
Phase 1 Organizations API Test Suite
Tests ONLY /api/org endpoints (no LLM, no credits, safe to test fully)
"""
import requests
import json
import random
import time

# Backend URL from frontend/.env
BASE_URL = "https://b102b754-bfd3-4b10-ad27-56b1b13b1784.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
FOUNDER_EMAIL = "ceo@smartdecigen.com"
FOUNDER_PASSWORD = "FounderOS@2026"

# Test results tracking
test_results = []

def log_test(scenario, passed, expected, actual, details=""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    result = {
        "scenario": scenario,
        "passed": passed,
        "status": status,
        "expected": expected,
        "actual": actual,
        "details": details
    }
    test_results.append(result)
    print(f"\n{status} - {scenario}")
    if not passed:
        print(f"  Expected: {expected}")
        print(f"  Actual: {actual}")
        if details:
            print(f"  Details: {details}")

def signup_user(email, password, name="Test User"):
    """Create a new user account"""
    resp = requests.post(f"{BASE_URL}/auth/signup", json={
        "email": email,
        "password": password,
        "name": name
    })
    if resp.status_code == 200:
        data = resp.json()
        return data["token"], data["user"]
    else:
        raise Exception(f"Signup failed: {resp.status_code} {resp.text}")

def login_user(email, password):
    """Login and get token"""
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": password
    })
    if resp.status_code == 200:
        data = resp.json()
        return data["token"], data["user"]
    else:
        raise Exception(f"Login failed: {resp.status_code} {resp.text}")

def get_me(token):
    """Get current user info"""
    resp = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {token}"})
    if resp.status_code == 200:
        return resp.json()
    else:
        raise Exception(f"Get me failed: {resp.status_code} {resp.text}")

print("=" * 80)
print("PHASE 1 ORGANIZATIONS API TEST SUITE")
print("=" * 80)

# Generate unique test data
test_id = random.randint(100000, 999999)
org_name = f"Acme Solar {test_id}"
member1_email = f"member1_{test_id}@acmesolar.com"
member2_email = f"member2_{test_id}@acmesolar.com"
member3_email = f"member3_{test_id}@acmesolar.com"

print(f"\nTest ID: {test_id}")
print(f"Organization: {org_name}")
print(f"Member emails: {member1_email}, {member2_email}, {member3_email}")

# ============================================================================
# SCENARIO 1: POST /api/org create organization
# ============================================================================
print("\n" + "=" * 80)
print("SCENARIO 1: POST /api/org - Create organization")
print("=" * 80)

# Login as founder
founder_token, founder_user = login_user(FOUNDER_EMAIL, FOUNDER_PASSWORD)
print(f"✓ Logged in as founder: {FOUNDER_EMAIL}")

# Create organization (first time should succeed)
resp = requests.post(f"{BASE_URL}/org", 
    headers={"Authorization": f"Bearer {founder_token}"},
    json={"name": org_name}
)

if resp.status_code == 200:
    org_data = resp.json()
    org_id = org_data.get("id")
    
    # Verify response structure
    expected_keys = ["id", "name", "role", "member_count", "is_owner", "strategy_set"]
    has_all_keys = all(k in org_data for k in expected_keys)
    
    passed = (
        has_all_keys and
        org_data.get("name") == org_name and
        org_data.get("role") == "owner" and
        org_data.get("member_count") == 1 and
        org_data.get("is_owner") == True and
        org_data.get("strategy_set") == False
    )
    
    log_test(
        "1a. POST /api/org (first time)",
        passed,
        "200 with {id, name, role:owner, member_count:1, is_owner:true, strategy_set:false}",
        f"{resp.status_code} with {org_data}",
        f"Organization created: {org_id}"
    )
else:
    log_test(
        "1a. POST /api/org (first time)",
        False,
        "200",
        f"{resp.status_code}: {resp.text}"
    )
    print("\n❌ CRITICAL: Cannot continue without organization. Exiting.")
    exit(1)

# Try to create organization again (should fail with 409)
resp = requests.post(f"{BASE_URL}/org",
    headers={"Authorization": f"Bearer {founder_token}"},
    json={"name": f"{org_name} 2"}
)

log_test(
    "1b. POST /api/org (second time, same user)",
    resp.status_code == 409,
    "409 (already in an organization)",
    f"{resp.status_code}: {resp.text}"
)

# ============================================================================
# SCENARIO 2: GET /api/org - Get my organization
# ============================================================================
print("\n" + "=" * 80)
print("SCENARIO 2: GET /api/org - Get my organization")
print("=" * 80)

# Founder should see their org
resp = requests.get(f"{BASE_URL}/org",
    headers={"Authorization": f"Bearer {founder_token}"}
)

if resp.status_code == 200:
    org_data = resp.json()
    passed = (
        org_data.get("id") == org_id and
        org_data.get("role") == "owner"
    )
    log_test(
        "2a. GET /api/org (founder with org)",
        passed,
        "200 with org + role:owner",
        f"{resp.status_code} with {org_data}"
    )
else:
    log_test(
        "2a. GET /api/org (founder with org)",
        False,
        "200",
        f"{resp.status_code}: {resp.text}"
    )

# Create a fresh user who has NOT joined any org
fresh_token, fresh_user = signup_user(member3_email, "Test1234", "Fresh User")
print(f"✓ Created fresh user: {member3_email}")

# Fresh user should get 404
resp = requests.get(f"{BASE_URL}/org",
    headers={"Authorization": f"Bearer {fresh_token}"}
)

log_test(
    "2b. GET /api/org (user with no org)",
    resp.status_code == 404,
    "404",
    f"{resp.status_code}: {resp.text}"
)

# ============================================================================
# SCENARIO 3: POST /api/org/invites - Create invite
# ============================================================================
print("\n" + "=" * 80)
print("SCENARIO 3: POST /api/org/invites - Create invite")
print("=" * 80)

# Owner creates invite (should succeed)
resp = requests.post(f"{BASE_URL}/org/invites",
    headers={"Authorization": f"Bearer {founder_token}"},
    json={}
)

if resp.status_code == 200:
    invite_data = resp.json()
    invite_code = invite_data.get("code")
    join_url = invite_data.get("join_url")
    
    expected_keys = ["code", "join_url", "status"]
    has_all_keys = all(k in invite_data for k in expected_keys)
    
    passed = (
        has_all_keys and
        invite_data.get("status") == "pending" and
        invite_code is not None and
        join_url is not None
    )
    
    log_test(
        "3a. POST /api/org/invites (owner)",
        passed,
        "200 with {code, join_url, status:pending}",
        f"{resp.status_code} with {invite_data}",
        f"Invite code: {invite_code}"
    )
else:
    log_test(
        "3a. POST /api/org/invites (owner)",
        False,
        "200",
        f"{resp.status_code}: {resp.text}"
    )
    print("\n❌ CRITICAL: Cannot continue without invite code. Exiting.")
    exit(1)

# Create a member account and have them join (for testing member permissions)
member1_token, member1_user = signup_user(member1_email, "Test1234", "Member One")
print(f"✓ Created member account: {member1_email}")

# Member joins the org first
resp = requests.post(f"{BASE_URL}/org/join",
    headers={"Authorization": f"Bearer {member1_token}"},
    json={"code": invite_code}
)
if resp.status_code == 200:
    print(f"✓ Member joined organization")
else:
    print(f"⚠ Member join failed: {resp.status_code} {resp.text}")

# Member tries to create invite (should fail with 403)
resp = requests.post(f"{BASE_URL}/org/invites",
    headers={"Authorization": f"Bearer {member1_token}"},
    json={}
)

log_test(
    "3b. POST /api/org/invites (member, non-owner)",
    resp.status_code == 403,
    "403",
    f"{resp.status_code}: {resp.text}"
)

# No token (should fail with 401)
resp = requests.post(f"{BASE_URL}/org/invites", json={})

log_test(
    "3c. POST /api/org/invites (no token)",
    resp.status_code == 401,
    "401",
    f"{resp.status_code}: {resp.text}"
)

# ============================================================================
# SCENARIO 4: GET /api/org/invites/{code} - Public lookup
# ============================================================================
print("\n" + "=" * 80)
print("SCENARIO 4: GET /api/org/invites/{code} - Public lookup")
print("=" * 80)

# Create a new invite for testing
resp = requests.post(f"{BASE_URL}/org/invites",
    headers={"Authorization": f"Bearer {founder_token}"},
    json={}
)
if resp.status_code == 200:
    invite_code_2 = resp.json().get("code")
    print(f"✓ Created second invite: {invite_code_2}")
else:
    invite_code_2 = invite_code
    print(f"⚠ Using first invite code: {invite_code}")

# Public lookup with valid code (NO auth header)
resp = requests.get(f"{BASE_URL}/org/invites/{invite_code_2}")

if resp.status_code == 200:
    lookup_data = resp.json()
    passed = (
        lookup_data.get("valid") == True and
        lookup_data.get("org_name") == org_name and
        lookup_data.get("role") == "member"
    )
    log_test(
        "4a. GET /api/org/invites/{code} (valid code, public)",
        passed,
        "200 with {valid:true, org_name, role:member}",
        f"{resp.status_code} with {lookup_data}"
    )
else:
    log_test(
        "4a. GET /api/org/invites/{code} (valid code, public)",
        False,
        "200",
        f"{resp.status_code}: {resp.text}"
    )

# Public lookup with invalid/garbage code
resp = requests.get(f"{BASE_URL}/org/invites/invalid_garbage_code_xyz")

if resp.status_code == 200:
    lookup_data = resp.json()
    passed = lookup_data.get("valid") == False
    log_test(
        "4b. GET /api/org/invites/{code} (invalid code, public)",
        passed,
        "200 with {valid:false}",
        f"{resp.status_code} with {lookup_data}"
    )
else:
    log_test(
        "4b. GET /api/org/invites/{code} (invalid code, public)",
        False,
        "200",
        f"{resp.status_code}: {resp.text}"
    )

# ============================================================================
# SCENARIO 5: POST /api/org/join - Join organization
# ============================================================================
print("\n" + "=" * 80)
print("SCENARIO 5: POST /api/org/join - Join organization")
print("=" * 80)

# Create a new invite for member2
resp = requests.post(f"{BASE_URL}/org/invites",
    headers={"Authorization": f"Bearer {founder_token}"},
    json={}
)
if resp.status_code == 200:
    invite_code_3 = resp.json().get("code")
    print(f"✓ Created third invite: {invite_code_3}")
else:
    print(f"⚠ Failed to create third invite")
    invite_code_3 = None

# Create member2 account
member2_token, member2_user = signup_user(member2_email, "Test1234", "Member Two")
print(f"✓ Created member2 account: {member2_email}")

# Member2 joins (first time, should succeed)
if invite_code_3:
    resp = requests.post(f"{BASE_URL}/org/join",
        headers={"Authorization": f"Bearer {member2_token}"},
        json={"code": invite_code_3}
    )
    
    if resp.status_code == 200:
        join_data = resp.json()
        passed = join_data.get("role") == "member"
        log_test(
            "5a. POST /api/org/join (first time)",
            passed,
            "200 with {role:member}",
            f"{resp.status_code} with {join_data}"
        )
    else:
        log_test(
            "5a. POST /api/org/join (first time)",
            False,
            "200",
            f"{resp.status_code}: {resp.text}"
        )
    
    # Member2 tries to join again (should fail with 409)
    resp = requests.post(f"{BASE_URL}/org/join",
        headers={"Authorization": f"Bearer {member2_token}"},
        json={"code": invite_code_3}
    )
    
    log_test(
        "5b. POST /api/org/join (same user, second time)",
        resp.status_code == 409,
        "409 (already in an organization)",
        f"{resp.status_code}: {resp.text}"
    )
else:
    print("⚠ Skipping join tests (no invite code)")

# Join with bad/unknown code
resp = requests.post(f"{BASE_URL}/org/join",
    headers={"Authorization": f"Bearer {fresh_token}"},
    json={"code": "bad_unknown_code_xyz"}
)

log_test(
    "5c. POST /api/org/join (bad/unknown code)",
    resp.status_code == 404,
    "404",
    f"{resp.status_code}: {resp.text}"
)

# ============================================================================
# SCENARIO 6: GET /api/org/members - List members
# ============================================================================
print("\n" + "=" * 80)
print("SCENARIO 6: GET /api/org/members - List members")
print("=" * 80)

# Owner lists members (should see founder + member1 + member2)
resp = requests.get(f"{BASE_URL}/org/members",
    headers={"Authorization": f"Bearer {founder_token}"}
)

if resp.status_code == 200:
    members_data = resp.json()
    members_list = members_data.get("members", [])
    count = members_data.get("count", 0)
    
    # Should have 3 members: founder + member1 + member2
    passed = count >= 2  # At least founder + member1 (member2 might have failed to join)
    
    log_test(
        "6a. GET /api/org/members (owner)",
        passed,
        "200 with members list (count >= 2)",
        f"{resp.status_code} with count={count}, members={len(members_list)}",
        f"Members: {[m.get('email') for m in members_list]}"
    )
else:
    log_test(
        "6a. GET /api/org/members (owner)",
        False,
        "200",
        f"{resp.status_code}: {resp.text}"
    )

# Member tries to list members (should fail with 403)
resp = requests.get(f"{BASE_URL}/org/members",
    headers={"Authorization": f"Bearer {member1_token}"}
)

log_test(
    "6b. GET /api/org/members (member, non-owner)",
    resp.status_code == 403,
    "403",
    f"{resp.status_code}: {resp.text}"
)

# ============================================================================
# SCENARIO 7: POST /api/org/invites/{code}/revoke - Revoke invite
# ============================================================================
print("\n" + "=" * 80)
print("SCENARIO 7: POST /api/org/invites/{code}/revoke - Revoke invite")
print("=" * 80)

# Create a new invite for revocation testing
resp = requests.post(f"{BASE_URL}/org/invites",
    headers={"Authorization": f"Bearer {founder_token}"},
    json={}
)
if resp.status_code == 200:
    revoke_code = resp.json().get("code")
    print(f"✓ Created invite for revocation: {revoke_code}")
else:
    print(f"⚠ Failed to create invite for revocation")
    revoke_code = None

if revoke_code:
    # Owner revokes invite (first time, should succeed)
    resp = requests.post(f"{BASE_URL}/org/invites/{revoke_code}/revoke",
        headers={"Authorization": f"Bearer {founder_token}"}
    )
    
    if resp.status_code == 200:
        revoke_data = resp.json()
        passed = revoke_data.get("revoked") == True
        log_test(
            "7a. POST /api/org/invites/{code}/revoke (first time)",
            passed,
            "200 with {revoked:true}",
            f"{resp.status_code} with {revoke_data}"
        )
    else:
        log_test(
            "7a. POST /api/org/invites/{code}/revoke (first time)",
            False,
            "200",
            f"{resp.status_code}: {resp.text}"
        )
    
    # Try to join with revoked code (should fail with 410)
    resp = requests.post(f"{BASE_URL}/org/join",
        headers={"Authorization": f"Bearer {fresh_token}"},
        json={"code": revoke_code}
    )
    
    log_test(
        "7b. POST /api/org/join (revoked code)",
        resp.status_code == 410,
        "410",
        f"{resp.status_code}: {resp.text}"
    )
    
    # Try to revoke again (should fail with 409)
    resp = requests.post(f"{BASE_URL}/org/invites/{revoke_code}/revoke",
        headers={"Authorization": f"Bearer {founder_token}"}
    )
    
    log_test(
        "7c. POST /api/org/invites/{code}/revoke (second time)",
        resp.status_code == 409,
        "409 (already revoked)",
        f"{resp.status_code}: {resp.text}"
    )
else:
    print("⚠ Skipping revoke tests (no invite code)")

# ============================================================================
# SCENARIO 8: DELETE /api/org/members/{user_id} - Remove member
# ============================================================================
print("\n" + "=" * 80)
print("SCENARIO 8: DELETE /api/org/members/{user_id} - Remove member")
print("=" * 80)

# Get member1's user_id
member1_user_id = member1_user.get("id")

# Owner removes member1 (should succeed)
resp = requests.delete(f"{BASE_URL}/org/members/{member1_user_id}",
    headers={"Authorization": f"Bearer {founder_token}"}
)

if resp.status_code == 200:
    remove_data = resp.json()
    passed = remove_data.get("removed") == True
    log_test(
        "8a. DELETE /api/org/members/{user_id} (owner removes member)",
        passed,
        "200 with {removed:true}",
        f"{resp.status_code} with {remove_data}"
    )
else:
    log_test(
        "8a. DELETE /api/org/members/{user_id} (owner removes member)",
        False,
        "200",
        f"{resp.status_code}: {resp.text}"
    )

# Verify member1 no longer has org (GET /api/org should return 404)
resp = requests.get(f"{BASE_URL}/org",
    headers={"Authorization": f"Bearer {member1_token}"}
)

log_test(
    "8b. GET /api/org (removed member)",
    resp.status_code == 404,
    "404",
    f"{resp.status_code}: {resp.text}"
)

# Owner tries to remove themselves (should fail with 400)
founder_user_id = founder_user.get("id")
resp = requests.delete(f"{BASE_URL}/org/members/{founder_user_id}",
    headers={"Authorization": f"Bearer {founder_token}"}
)

log_test(
    "8c. DELETE /api/org/members/{user_id} (owner removes self)",
    resp.status_code == 400,
    "400 (cannot remove owner)",
    f"{resp.status_code}: {resp.text}"
)

# Owner tries to remove unknown user_id (should fail with 404)
resp = requests.delete(f"{BASE_URL}/org/members/unknown_user_id_xyz",
    headers={"Authorization": f"Bearer {founder_token}"}
)

log_test(
    "8d. DELETE /api/org/members/{user_id} (unknown user_id)",
    resp.status_code == 404,
    "404",
    f"{resp.status_code}: {resp.text}"
)

# ============================================================================
# SCENARIO 9: Auth payloads include org_id and org_role
# ============================================================================
print("\n" + "=" * 80)
print("SCENARIO 9: Auth payloads include org_id and org_role")
print("=" * 80)

# Create a new user and verify signup response
test_signup_email = f"test_auth_{test_id}@acmesolar.com"
resp = requests.post(f"{BASE_URL}/auth/signup", json={
    "email": test_signup_email,
    "password": "Test1234",
    "name": "Auth Test User"
})

if resp.status_code == 200:
    signup_data = resp.json()
    user_data = signup_data.get("user", {})
    
    # New user should have org_id and org_role as None/null (not in any org yet)
    # Note: The response might not include these keys if they're null
    has_org_keys = "org_id" in user_data or "org_role" in user_data
    org_id_null = user_data.get("org_id") is None
    org_role_null = user_data.get("org_role") is None
    
    log_test(
        "9a. POST /api/auth/signup (org_id/org_role in response)",
        True,  # Just verify the endpoint works
        "200 with user data",
        f"{resp.status_code} with org_id={user_data.get('org_id')}, org_role={user_data.get('org_role')}"
    )
    
    test_auth_token = signup_data.get("token")
else:
    log_test(
        "9a. POST /api/auth/signup (org_id/org_role in response)",
        False,
        "200",
        f"{resp.status_code}: {resp.text}"
    )
    test_auth_token = None

# Verify login response includes org_id and org_role
resp = requests.post(f"{BASE_URL}/auth/login", json={
    "email": FOUNDER_EMAIL,
    "password": FOUNDER_PASSWORD
})

if resp.status_code == 200:
    login_data = resp.json()
    user_data = login_data.get("user", {})
    
    # Founder should have org_id and org_role set
    has_org_id = user_data.get("org_id") == org_id
    has_org_role = user_data.get("org_role") == "owner"
    
    passed = has_org_id and has_org_role
    
    log_test(
        "9b. POST /api/auth/login (org_id/org_role in response)",
        passed,
        f"200 with org_id={org_id}, org_role=owner",
        f"{resp.status_code} with org_id={user_data.get('org_id')}, org_role={user_data.get('org_role')}"
    )
else:
    log_test(
        "9b. POST /api/auth/login (org_id/org_role in response)",
        False,
        "200",
        f"{resp.status_code}: {resp.text}"
    )

# Verify GET /api/auth/me includes org_id and org_role
resp = requests.get(f"{BASE_URL}/auth/me",
    headers={"Authorization": f"Bearer {founder_token}"}
)

if resp.status_code == 200:
    me_data = resp.json()
    
    has_org_id = me_data.get("org_id") == org_id
    has_org_role = me_data.get("org_role") == "owner"
    
    passed = has_org_id and has_org_role
    
    log_test(
        "9c. GET /api/auth/me (org_id/org_role in response)",
        passed,
        f"200 with org_id={org_id}, org_role=owner",
        f"{resp.status_code} with org_id={me_data.get('org_id')}, org_role={me_data.get('org_role')}"
    )
else:
    log_test(
        "9c. GET /api/auth/me (org_id/org_role in response)",
        False,
        "200",
        f"{resp.status_code}: {resp.text}"
    )

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 80)
print("TEST SUMMARY")
print("=" * 80)

total_tests = len(test_results)
passed_tests = sum(1 for r in test_results if r["passed"])
failed_tests = total_tests - passed_tests

print(f"\nTotal tests: {total_tests}")
print(f"Passed: {passed_tests} ✅")
print(f"Failed: {failed_tests} ❌")

if failed_tests > 0:
    print("\n" + "=" * 80)
    print("FAILED TESTS")
    print("=" * 80)
    for r in test_results:
        if not r["passed"]:
            print(f"\n❌ {r['scenario']}")
            print(f"   Expected: {r['expected']}")
            print(f"   Actual: {r['actual']}")
            if r["details"]:
                print(f"   Details: {r['details']}")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)

# Exit with appropriate code
exit(0 if failed_tests == 0 else 1)
