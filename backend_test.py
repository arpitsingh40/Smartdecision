#!/usr/bin/env python3
"""Comprehensive backend API tests for SmartDecigen.
Tests all admin APIs, payments (test mode), traffic tracking, turn economics, and auth.
"""
import requests
import time
import json
from typing import Optional

# Backend URL from frontend/.env
BASE_URL = "https://ops-center-34.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "ceo@smartdecigen.com"
ADMIN_PASSWORD = "FounderOS@2026"
DEMO_EMAIL = "demo@smartdecigen.com"
DEMO_PASSWORD = "Demo1234!"

# Test state
admin_token = None
demo_token = None
demo_user_id = None
test_session_id = None
test_order_id = None
test_thread_id = None
fresh_user_email = None
fresh_user_token = None


def log(msg: str, level: str = "INFO"):
    """Simple logger"""
    print(f"[{level}] {msg}")


def api_call(method: str, path: str, token: Optional[str] = None, json_data: Optional[dict] = None, 
             expect_status: int = 200, expect_fail: bool = False) -> dict:
    """Make API call and return response"""
    url = f"{BASE_URL}{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        if method == "GET":
            r = requests.get(url, headers=headers, timeout=15)
        elif method == "POST":
            r = requests.post(url, headers=headers, json=json_data, timeout=15)
        elif method == "PATCH":
            r = requests.patch(url, headers=headers, json=json_data, timeout=15)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if not expect_fail and r.status_code != expect_status:
            log(f"FAIL: {method} {path} returned {r.status_code}, expected {expect_status}", "ERROR")
            log(f"Response: {r.text[:500]}", "ERROR")
            return {"error": True, "status": r.status_code, "text": r.text}
        
        if expect_fail and r.status_code == expect_status:
            log(f"FAIL: {method} {path} returned {r.status_code}, expected failure", "ERROR")
            return {"error": True, "status": r.status_code}
        
        return {"status": r.status_code, "data": r.json() if r.text else {}}
    except Exception as e:
        log(f"EXCEPTION: {method} {path} - {e}", "ERROR")
        return {"error": True, "exception": str(e)}


def test_auth():
    """Test authentication endpoints"""
    global admin_token, demo_token, demo_user_id, fresh_user_email, fresh_user_token
    
    log("=" * 60)
    log("TESTING: Authentication")
    log("=" * 60)
    
    # Test admin login
    log("Testing admin login...")
    resp = api_call("POST", "/auth/login", json_data={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    if resp.get("error"):
        log("CRITICAL: Admin login failed", "ERROR")
        return False
    admin_token = resp["data"]["token"]
    is_admin = resp["data"]["user"].get("is_admin", False)
    if not is_admin:
        log("CRITICAL: Admin user does not have is_admin=true", "ERROR")
        return False
    log(f"✓ Admin login successful, is_admin={is_admin}")
    
    # Test demo login
    log("Testing demo user login...")
    resp = api_call("POST", "/auth/login", json_data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    if resp.get("error"):
        log("CRITICAL: Demo login failed", "ERROR")
        return False
    demo_token = resp["data"]["token"]
    demo_user_id = resp["data"]["user"]["id"]
    is_admin = resp["data"]["user"].get("is_admin", False)
    if is_admin:
        log("CRITICAL: Demo user has is_admin=true (should be false)", "ERROR")
        return False
    log(f"✓ Demo login successful, user_id={demo_user_id}, is_admin={is_admin}")
    
    # Test /auth/me
    log("Testing /auth/me...")
    resp = api_call("GET", "/auth/me", token=demo_token)
    if resp.get("error"):
        log("FAIL: /auth/me failed", "ERROR")
        return False
    if "is_admin" not in resp["data"]:
        log("FAIL: /auth/me response missing is_admin field", "ERROR")
        return False
    log(f"✓ /auth/me successful, is_admin={resp['data'].get('is_admin')}")
    
    # Test fresh signup
    log("Testing fresh signup...")
    fresh_user_email = f"test_{int(time.time())}@smartdecigen.com"
    resp = api_call("POST", "/auth/signup", json_data={
        "email": fresh_user_email,
        "password": "TestPass123!",
        "name": "Test User"
    })
    if resp.get("error"):
        log("FAIL: Fresh signup failed", "ERROR")
        return False
    fresh_user_token = resp["data"]["token"]
    fresh_credits = resp["data"]["user"]["credits"]
    fresh_is_admin = resp["data"]["user"].get("is_admin", False)
    if fresh_credits != 100:
        log(f"FAIL: Fresh signup should grant 100 credits, got {fresh_credits}", "ERROR")
        return False
    if fresh_is_admin:
        log("FAIL: Fresh signup user has is_admin=true (should be false)", "ERROR")
        return False
    log(f"✓ Fresh signup successful, email={fresh_user_email}, credits={fresh_credits}, is_admin={fresh_is_admin}")
    
    return True


def test_admin_apis():
    """Test all admin endpoints"""
    global admin_token, demo_token, demo_user_id
    
    log("=" * 60)
    log("TESTING: Admin APIs")
    log("=" * 60)
    
    # Test admin overview
    log("Testing GET /admin/overview...")
    resp = api_call("GET", "/admin/overview", token=admin_token)
    if resp.get("error"):
        log("FAIL: /admin/overview failed", "ERROR")
        return False
    data = resp["data"]
    required_keys = ["users", "engine", "credits", "tokens", "revenue", "traffic"]
    for key in required_keys:
        if key not in data:
            log(f"FAIL: /admin/overview missing key: {key}", "ERROR")
            return False
    log(f"✓ /admin/overview successful")
    log(f"  Users: total={data['users']['total']}, new_7d={data['users']['new_7d']}, active_24h={data['users']['active_24h']}")
    log(f"  Credits: issued_total={data['credits']['issued_total']}, issued_free={data['credits']['issued_free']}, issued_paid={data['credits']['issued_paid']}, spent={data['credits']['spent']}, outstanding={data['credits']['outstanding']}")
    log(f"  Revenue: total_inr={data['revenue']['total_inr']}, purchases={data['revenue']['purchases']}")
    
    # Test admin users list
    log("Testing GET /admin/users...")
    resp = api_call("GET", "/admin/users?page=1&limit=10", token=admin_token)
    if resp.get("error"):
        log("FAIL: /admin/users failed", "ERROR")
        return False
    data = resp["data"]
    if "items" not in data or "total" not in data:
        log("FAIL: /admin/users missing items or total", "ERROR")
        return False
    log(f"✓ /admin/users successful, total={data['total']}, items={len(data['items'])}")
    
    # Test admin users search
    log("Testing GET /admin/users with search...")
    resp = api_call("GET", "/admin/users?q=demo", token=admin_token)
    if resp.get("error"):
        log("FAIL: /admin/users search failed", "ERROR")
        return False
    log(f"✓ /admin/users search successful, found {len(resp['data']['items'])} users")
    
    # Test admin user activity
    log(f"Testing GET /admin/users/{demo_user_id}/activity...")
    resp = api_call("GET", f"/admin/users/{demo_user_id}/activity", token=admin_token)
    if resp.get("error"):
        log("FAIL: /admin/users/{id}/activity failed", "ERROR")
        return False
    data = resp["data"]
    if "user" not in data or "threads" not in data or "ledger" not in data:
        log("FAIL: /admin/users/{id}/activity missing required keys", "ERROR")
        return False
    log(f"✓ /admin/users/{demo_user_id}/activity successful")
    log(f"  Threads: {len(data['threads'])}, Ledger entries: {len(data['ledger'])}")
    
    # Test admin traffic
    log("Testing GET /admin/traffic...")
    resp = api_call("GET", "/admin/traffic?page=1&limit=10", token=admin_token)
    if resp.get("error"):
        log("FAIL: /admin/traffic failed", "ERROR")
        return False
    data = resp["data"]
    if "summary" not in data or "items" not in data:
        log("FAIL: /admin/traffic missing summary or items", "ERROR")
        return False
    log(f"✓ /admin/traffic successful")
    log(f"  Summary: sessions_total={data['summary']['sessions_total']}, unique_ips={data['summary']['unique_ips']}, avg_session_s={data['summary']['avg_session_s']}")
    
    # Test admin usage
    log("Testing GET /admin/usage...")
    resp = api_call("GET", "/admin/usage?page=1&limit=10", token=admin_token)
    if resp.get("error"):
        log("FAIL: /admin/usage failed", "ERROR")
        return False
    data = resp["data"]
    if "summary" not in data or "items" not in data:
        log("FAIL: /admin/usage missing summary or items", "ERROR")
        return False
    log(f"✓ /admin/usage successful")
    log(f"  Summary: credits={data['summary']['credits']}, tokens={data['summary']['tokens']}, turns={data['summary']['turns']}, revenue={data['summary']['revenue']}")
    
    # Test admin purchases
    log("Testing GET /admin/purchases...")
    resp = api_call("GET", "/admin/purchases?page=1&limit=10", token=admin_token)
    if resp.get("error"):
        log("FAIL: /admin/purchases failed", "ERROR")
        return False
    data = resp["data"]
    if "items" not in data or "total" not in data:
        log("FAIL: /admin/purchases missing items or total", "ERROR")
        return False
    log(f"✓ /admin/purchases successful, total={data['total']}")
    
    # Test admin auth: demo user should get 403
    log("Testing admin auth: demo user should get 403...")
    resp = api_call("GET", "/admin/overview", token=demo_token, expect_status=403, expect_fail=True)
    if resp.get("status") != 403:
        log("FAIL: Demo user should get 403 on /admin/overview", "ERROR")
        return False
    log("✓ Admin auth working: demo user got 403")
    
    # Test admin auth: no token should get 401
    log("Testing admin auth: no token should get 401...")
    resp = api_call("GET", "/admin/overview", expect_status=401, expect_fail=True)
    if resp.get("status") != 401:
        log("FAIL: No token should get 401 on /admin/overview", "ERROR")
        return False
    log("✓ Admin auth working: no token got 401")
    
    return True


def test_payments():
    """Test payment endpoints (test mode)"""
    global demo_token, test_order_id
    
    log("=" * 60)
    log("TESTING: Payments (Test Mode)")
    log("=" * 60)
    
    # Get initial credits
    log("Getting initial credits...")
    resp = api_call("GET", "/credits", token=demo_token)
    if resp.get("error"):
        log("FAIL: /credits failed", "ERROR")
        return False
    initial_credits = resp["data"]["credits"]
    turn_cost = resp["data"]["turn_cost"]
    ultra_turn_cost = resp["data"]["ultra_turn_cost"]
    log(f"✓ Initial credits: {initial_credits}, turn_cost={turn_cost}, ultra_turn_cost={ultra_turn_cost}")
    
    # Test packs endpoint
    log("Testing GET /payments/packs...")
    resp = api_call("GET", "/payments/packs")
    if resp.get("error"):
        log("FAIL: /payments/packs failed", "ERROR")
        return False
    data = resp["data"]
    if not data.get("test_mode"):
        log("FAIL: test_mode should be true", "ERROR")
        return False
    packs = data.get("packs", [])
    if len(packs) != 2:
        log(f"FAIL: Expected 2 packs, got {len(packs)}", "ERROR")
        return False
    pack_100 = next((p for p in packs if p["pack_id"] == "pack_100"), None)
    pack_500 = next((p for p in packs if p["pack_id"] == "pack_500"), None)
    if not pack_100 or pack_100["credits"] != 100 or pack_100["amount_inr"] != 399:
        log("FAIL: pack_100 incorrect", "ERROR")
        return False
    if not pack_500 or pack_500["credits"] != 500 or pack_500["amount_inr"] != 999:
        log("FAIL: pack_500 incorrect", "ERROR")
        return False
    log("✓ /payments/packs successful, test_mode=true, 2 packs found")
    
    # Test create-order
    log("Testing POST /payments/create-order (pack_500)...")
    resp = api_call("POST", "/payments/create-order", token=demo_token, json_data={"pack_id": "pack_500"})
    if resp.get("error"):
        log("FAIL: /payments/create-order failed", "ERROR")
        return False
    data = resp["data"]
    test_order_id = data.get("order_id")
    checkout_url = data.get("checkout_url")
    if not test_order_id or not checkout_url:
        log("FAIL: create-order missing order_id or checkout_url", "ERROR")
        return False
    if "/pay/test-checkout" not in checkout_url:
        log("FAIL: checkout_url should contain /pay/test-checkout in test mode", "ERROR")
        return False
    log(f"✓ /payments/create-order successful, order_id={test_order_id}")
    
    # Test invalid pack_id
    log("Testing POST /payments/create-order with invalid pack_id...")
    resp = api_call("POST", "/payments/create-order", token=demo_token, 
                   json_data={"pack_id": "invalid_pack"}, expect_status=422, expect_fail=True)
    if resp.get("status") != 422:
        log("FAIL: Invalid pack_id should return 422", "ERROR")
        return False
    log("✓ Invalid pack_id correctly returned 422")
    
    # Test create-order without auth
    log("Testing POST /payments/create-order without auth...")
    resp = api_call("POST", "/payments/create-order", json_data={"pack_id": "pack_100"}, 
                   expect_status=401, expect_fail=True)
    if resp.get("status") != 401:
        log("FAIL: create-order without auth should return 401", "ERROR")
        return False
    log("✓ create-order without auth correctly returned 401")
    
    # Test test-complete with success
    log("Testing POST /payments/test-complete (success)...")
    resp = api_call("POST", "/payments/test-complete", token=demo_token, 
                   json_data={"order_id": test_order_id, "outcome": "success"})
    if resp.get("error"):
        log("FAIL: /payments/test-complete failed", "ERROR")
        return False
    data = resp["data"]
    if data.get("status") != "paid":
        log(f"FAIL: Order status should be 'paid', got '{data.get('status')}'", "ERROR")
        return False
    new_credits = data.get("credits")
    if new_credits != initial_credits + 500:
        log(f"FAIL: Credits should be {initial_credits + 500}, got {new_credits}", "ERROR")
        return False
    log(f"✓ /payments/test-complete (success) successful, status=paid, credits={new_credits}")
    
    # Test idempotency: call test-complete again
    log("Testing idempotency: calling test-complete again...")
    resp = api_call("POST", "/payments/test-complete", token=demo_token, 
                   json_data={"order_id": test_order_id, "outcome": "success"})
    if resp.get("error"):
        log("FAIL: /payments/test-complete (idempotency) failed", "ERROR")
        return False
    idempotent_credits = resp["data"].get("credits")
    if idempotent_credits != new_credits:
        log(f"FAIL: Idempotency broken - credits changed from {new_credits} to {idempotent_credits}", "ERROR")
        return False
    log(f"✓ Idempotency verified: credits unchanged at {idempotent_credits}")
    
    # Test order status
    log("Testing GET /payments/status/{order_id}...")
    resp = api_call("GET", f"/payments/status/{test_order_id}", token=demo_token)
    if resp.get("error"):
        log("FAIL: /payments/status failed", "ERROR")
        return False
    data = resp["data"]
    if data.get("status") != "paid":
        log(f"FAIL: Order status should be 'paid', got '{data.get('status')}'", "ERROR")
        return False
    log(f"✓ /payments/status successful, status={data.get('status')}, balance={data.get('balance')}")
    
    # Test payment history
    log("Testing GET /payments/history...")
    resp = api_call("GET", "/payments/history", token=demo_token)
    if resp.get("error"):
        log("FAIL: /payments/history failed", "ERROR")
        return False
    items = resp["data"].get("items", [])
    if not any(o.get("order_id") == test_order_id for o in items):
        log("FAIL: Order not found in history", "ERROR")
        return False
    log(f"✓ /payments/history successful, found {len(items)} orders")
    
    # Test create-order + test-complete with failure
    log("Testing payment failure flow...")
    resp = api_call("POST", "/payments/create-order", token=demo_token, json_data={"pack_id": "pack_100"})
    if resp.get("error"):
        log("FAIL: create-order for failure test failed", "ERROR")
        return False
    fail_order_id = resp["data"]["order_id"]
    
    resp = api_call("GET", "/credits", token=demo_token)
    credits_before_fail = resp["data"]["credits"]
    
    resp = api_call("POST", "/payments/test-complete", token=demo_token, 
                   json_data={"order_id": fail_order_id, "outcome": "failure"})
    if resp.get("error"):
        log("FAIL: /payments/test-complete (failure) failed", "ERROR")
        return False
    if resp["data"].get("status") != "failed":
        log(f"FAIL: Order status should be 'failed', got '{resp['data'].get('status')}'", "ERROR")
        return False
    credits_after_fail = resp["data"].get("credits")
    if credits_after_fail != credits_before_fail:
        log(f"FAIL: Credits should be unchanged on failure, was {credits_before_fail}, now {credits_after_fail}", "ERROR")
        return False
    log(f"✓ Payment failure flow successful, status=failed, credits unchanged")
    
    return True


def test_traffic_tracking():
    """Test traffic tracking endpoints"""
    global demo_token, test_session_id, admin_token
    
    log("=" * 60)
    log("TESTING: Traffic Tracking")
    log("=" * 60)
    
    # Test session creation (no session_id, with auth)
    log("Testing POST /track/session (create)...")
    resp = api_call("POST", "/track/session", token=demo_token, json_data={})
    if resp.get("error"):
        log("FAIL: /track/session (create) failed", "ERROR")
        return False
    test_session_id = resp["data"].get("session_id")
    if not test_session_id:
        log("FAIL: /track/session should return session_id", "ERROR")
        return False
    log(f"✓ /track/session (create) successful, session_id={test_session_id}")
    
    # Wait a bit and send heartbeat
    time.sleep(2)
    
    # Test session heartbeat (same session_id)
    log("Testing POST /track/session (heartbeat)...")
    resp = api_call("POST", "/track/session", token=demo_token, json_data={"session_id": test_session_id})
    if resp.get("error"):
        log("FAIL: /track/session (heartbeat) failed", "ERROR")
        return False
    returned_session_id = resp["data"].get("session_id")
    if returned_session_id != test_session_id:
        log(f"FAIL: Heartbeat should return same session_id, got {returned_session_id}", "ERROR")
        return False
    log(f"✓ /track/session (heartbeat) successful, session_id={returned_session_id}")
    
    # Wait a bit more and send another heartbeat
    time.sleep(2)
    resp = api_call("POST", "/track/session", token=demo_token, json_data={"session_id": test_session_id})
    
    # Check admin traffic to verify session data
    log("Checking admin traffic for session data...")
    resp = api_call("GET", "/admin/traffic?page=1&limit=50", token=admin_token)
    if resp.get("error"):
        log("FAIL: /admin/traffic check failed", "ERROR")
        return False
    
    sessions = resp["data"].get("items", [])
    our_session = next((s for s in sessions if s.get("session_id") == test_session_id), None)
    if not our_session:
        log("FAIL: Session not found in admin traffic", "ERROR")
        return False
    
    duration_s = our_session.get("duration_s", 0)
    beats = our_session.get("beats", 0)
    user_email = our_session.get("user_email")
    
    if duration_s < 0:
        log(f"FAIL: duration_s should be >= 0, got {duration_s}", "ERROR")
        return False
    if beats < 2:
        log(f"FAIL: beats should be >= 2, got {beats}", "ERROR")
        return False
    if user_email != DEMO_EMAIL:
        log(f"FAIL: user_email should be {DEMO_EMAIL}, got {user_email}", "ERROR")
        return False
    
    log(f"✓ Admin traffic verified: duration_s={duration_s}, beats={beats}, user_email={user_email}")
    
    return True


def test_turn_economics():
    """Test turn economics with refunds on 502 errors"""
    global demo_token, test_thread_id
    
    log("=" * 60)
    log("TESTING: Turn Economics & Refunds")
    log("=" * 60)
    
    # Get demo user's threads
    log("Getting demo user's threads...")
    resp = api_call("GET", "/goals", token=demo_token)
    if resp.get("error"):
        log("FAIL: /goals failed", "ERROR")
        return False
    
    goals = resp["data"].get("goals", [])
    if not goals:
        log("WARNING: Demo user has no threads, skipping turn economics test", "WARN")
        return True
    
    test_thread_id = goals[0]["thread_id"]
    log(f"✓ Found thread: {test_thread_id}")
    
    # Get credits before turn
    resp = api_call("GET", "/credits", token=demo_token)
    if resp.get("error"):
        log("FAIL: /credits failed", "ERROR")
        return False
    credits_before = resp["data"]["credits"]
    turn_cost = resp["data"]["turn_cost"]
    ultra_turn_cost = resp["data"]["ultra_turn_cost"]
    log(f"Credits before turn: {credits_before}, turn_cost={turn_cost}, ultra_turn_cost={ultra_turn_cost}")
    
    # Test normal turn (should get 502 and refund)
    log("Testing POST /threads/{id}/turn (normal mode, expect 502 + refund)...")
    resp = api_call("POST", f"/threads/{test_thread_id}/turn", token=demo_token, 
                   json_data={"message": "What should I focus on next?", "mode": "normal"},
                   expect_status=502, expect_fail=True)
    if resp.get("status") != 502:
        log(f"FAIL: Expected 502 for normal turn, got {resp.get('status')}", "ERROR")
        return False
    log("✓ Normal turn returned 502 as expected (ANTHROPIC_API_KEY is placeholder)")
    
    # Check credits after normal turn (should be unchanged due to refund)
    resp = api_call("GET", "/credits", token=demo_token)
    if resp.get("error"):
        log("FAIL: /credits after normal turn failed", "ERROR")
        return False
    credits_after_normal = resp["data"]["credits"]
    if credits_after_normal != credits_before:
        log(f"FAIL: Credits should be unchanged after 502 (refund), was {credits_before}, now {credits_after_normal}", "ERROR")
        return False
    log(f"✓ Normal turn refund verified: credits unchanged at {credits_after_normal}")
    
    # Test ultra turn (should get 502 and refund)
    log("Testing POST /threads/{id}/turn (ultra mode, expect 502 + refund)...")
    resp = api_call("POST", f"/threads/{test_thread_id}/turn", token=demo_token, 
                   json_data={"message": "What should I focus on next?", "mode": "ultra"},
                   expect_status=502, expect_fail=True)
    if resp.get("status") != 502:
        log(f"FAIL: Expected 502 for ultra turn, got {resp.get('status')}", "ERROR")
        return False
    log("✓ Ultra turn returned 502 as expected")
    
    # Check credits after ultra turn (should be unchanged due to refund)
    resp = api_call("GET", "/credits", token=demo_token)
    if resp.get("error"):
        log("FAIL: /credits after ultra turn failed", "ERROR")
        return False
    credits_after_ultra = resp["data"]["credits"]
    if credits_after_ultra != credits_before:
        log(f"FAIL: Credits should be unchanged after 502 (refund), was {credits_before}, now {credits_after_ultra}", "ERROR")
        return False
    log(f"✓ Ultra turn refund verified: credits unchanged at {credits_after_ultra}")
    
    # Test invalid mode
    log("Testing POST /threads/{id}/turn with invalid mode...")
    resp = api_call("POST", f"/threads/{test_thread_id}/turn", token=demo_token, 
                   json_data={"message": "test", "mode": "turbo"},
                   expect_status=422, expect_fail=True)
    if resp.get("status") != 422:
        log(f"FAIL: Invalid mode should return 422, got {resp.get('status')}", "ERROR")
        return False
    log("✓ Invalid mode correctly returned 422")
    
    return True


def test_signup_ledger():
    """Test signup ledger and admin verification"""
    global fresh_user_email, fresh_user_token, admin_token
    
    log("=" * 60)
    log("TESTING: Signup Ledger")
    log("=" * 60)
    
    if not fresh_user_email or not fresh_user_token:
        log("WARNING: No fresh user created, skipping signup ledger test", "WARN")
        return True
    
    # Get fresh user's ID
    resp = api_call("GET", "/auth/me", token=fresh_user_token)
    if resp.get("error"):
        log("FAIL: /auth/me for fresh user failed", "ERROR")
        return False
    fresh_user_id = resp["data"]["id"]
    
    # Check admin overview for increased credits_issued_free
    log("Checking admin overview for credits_issued_free increase...")
    resp = api_call("GET", "/admin/overview", token=admin_token)
    if resp.get("error"):
        log("FAIL: /admin/overview failed", "ERROR")
        return False
    issued_free = resp["data"]["credits"]["issued_free"]
    log(f"✓ Admin overview shows credits_issued_free={issued_free}")
    
    # Check admin user activity for ledger entry
    log(f"Checking admin user activity for fresh user {fresh_user_id}...")
    resp = api_call("GET", f"/admin/users/{fresh_user_id}/activity", token=admin_token)
    if resp.get("error"):
        log("FAIL: /admin/users/{id}/activity for fresh user failed", "ERROR")
        return False
    
    ledger = resp["data"].get("ledger", [])
    free_grant_entry = next((e for e in ledger if e.get("type") == "free_grant"), None)
    if not free_grant_entry:
        log("FAIL: No free_grant entry found in fresh user's ledger", "ERROR")
        return False
    if free_grant_entry.get("credits") != 100:
        log(f"FAIL: free_grant should be 100 credits, got {free_grant_entry.get('credits')}", "ERROR")
        return False
    log(f"✓ Fresh user ledger verified: free_grant entry with 100 credits found")
    
    return True


def run_all_tests():
    """Run all tests"""
    log("=" * 60)
    log("SmartDecigen Backend API Tests")
    log("=" * 60)
    log(f"Backend URL: {BASE_URL}")
    log("")
    
    results = {}
    
    # Run tests in order
    results["auth"] = test_auth()
    if not results["auth"]:
        log("CRITICAL: Auth tests failed, stopping", "ERROR")
        return results
    
    results["admin_apis"] = test_admin_apis()
    results["payments"] = test_payments()
    results["traffic_tracking"] = test_traffic_tracking()
    results["turn_economics"] = test_turn_economics()
    results["signup_ledger"] = test_signup_ledger()
    
    # Summary
    log("")
    log("=" * 60)
    log("TEST SUMMARY")
    log("=" * 60)
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        log(f"{status}: {test_name}")
    
    all_passed = all(results.values())
    log("")
    if all_passed:
        log("=" * 60)
        log("ALL TESTS PASSED ✓")
        log("=" * 60)
    else:
        log("=" * 60)
        log("SOME TESTS FAILED ✗")
        log("=" * 60)
    
    return results


if __name__ == "__main__":
    run_all_tests()
