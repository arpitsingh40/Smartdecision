#!/usr/bin/env python3
"""
Focused regression test for POST /api/threads/{thread_id}/complete-action endpoint.
Tests the "Do it for me" feature with emphasis on no-charge guarantee on failure.
"""
import requests
import sys

# Backend URL from frontend/.env
BASE_URL = "https://context-persist-ai.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
DEMO_EMAIL = "demo@smartdecigen.com"
DEMO_PASSWORD = "Demo1234!"
ADMIN_EMAIL = "ceo@smartdecigen.com"
ADMIN_PASSWORD = "FounderOS@2026"

def login(email, password):
    """Login and return token + user info."""
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        print(f"❌ Login failed for {email}: {r.status_code} {r.text}")
        return None, None
    data = r.json()
    return data["token"], data["user"]

def get_me(token):
    """Get current user info including credits."""
    r = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        print(f"❌ GET /auth/me failed: {r.status_code} {r.text}")
        return None
    return r.json()

def get_goals(token):
    """Get user's goals/threads."""
    r = requests.get(f"{BASE_URL}/goals", headers={"Authorization": f"Bearer {token}"})
    if r.status_code != 200:
        print(f"❌ GET /goals failed: {r.status_code} {r.text}")
        return None
    return r.json()

def get_thread(thread_id, token):
    """Get thread details."""
    r = requests.get(f"{BASE_URL}/threads/{thread_id}", headers={"Authorization": f"Bearer {token}"})
    return r

def complete_action(thread_id, token):
    """Call POST /api/threads/{thread_id}/complete-action."""
    r = requests.post(f"{BASE_URL}/threads/{thread_id}/complete-action", 
                     headers={"Authorization": f"Bearer {token}"})
    return r

def get_user_activity(user_id, token):
    """Get user activity (admin only) to check ledger entries."""
    r = requests.get(f"{BASE_URL}/admin/users/{user_id}/activity", 
                    headers={"Authorization": f"Bearer {token}"})
    return r

def get_admin_overview(token):
    """Smoke test: GET /admin/overview."""
    r = requests.get(f"{BASE_URL}/admin/overview", headers={"Authorization": f"Bearer {token}"})
    return r

def main():
    print("=" * 80)
    print("REGRESSION TEST: POST /api/threads/{thread_id}/complete-action")
    print("=" * 80)
    
    results = []
    
    # ========================================================================
    # TEST 1: Demo user - 502 error with no charge guarantee
    # ========================================================================
    print("\n[TEST 1] Demo user: 502 error with no charge guarantee")
    print("-" * 80)
    
    demo_token, demo_user = login(DEMO_EMAIL, DEMO_PASSWORD)
    if not demo_token:
        print("❌ FAIL: Could not login as demo user")
        results.append(("Demo login", False))
        return 1
    
    print(f"✓ Logged in as {demo_user['email']}")
    demo_user_id = demo_user['id']
    
    # Get initial credits
    me = get_me(demo_token)
    if not me:
        print("❌ FAIL: Could not get user info")
        results.append(("Get user info", False))
        return 1
    
    credits_before = me['credits']
    print(f"✓ Initial credits: {credits_before}")
    
    # Get demo's thread
    goals_data = get_goals(demo_token)
    if not goals_data or not goals_data.get('goals'):
        print("❌ FAIL: Demo user has no threads")
        results.append(("Get demo thread", False))
        return 1
    
    demo_thread_id = goals_data['goals'][0]['thread_id']
    print(f"✓ Found demo thread: {demo_thread_id}")
    
    # Verify thread has next_action
    thread_r = get_thread(demo_thread_id, demo_token)
    if thread_r.status_code != 200:
        print(f"❌ FAIL: Could not get thread details: {thread_r.status_code}")
        results.append(("Get thread details", False))
        return 1
    
    thread_data = thread_r.json()
    next_action = thread_data['thread'].get('current_next_action', '')
    print(f"✓ Thread next action: {next_action[:60]}...")
    
    # Call complete-action - expect 502
    print(f"\n→ Calling POST /threads/{demo_thread_id}/complete-action...")
    ca_r = complete_action(demo_thread_id, demo_token)
    
    if ca_r.status_code != 502:
        print(f"❌ FAIL: Expected 502, got {ca_r.status_code}: {ca_r.text}")
        results.append(("Complete-action returns 502", False))
    else:
        try:
            detail = ca_r.json().get('detail', '')
            print(f"✓ Got expected 502 error: {detail}")
        except:
            print(f"✓ Got expected 502 error (no JSON body)")
        results.append(("Complete-action returns 502", True))
    
    # Verify credits unchanged
    me_after = get_me(demo_token)
    if not me_after:
        print("❌ FAIL: Could not get user info after complete-action")
        results.append(("Get user info after", False))
        return 1
    
    credits_after = me_after['credits']
    print(f"✓ Credits after: {credits_after}")
    
    if credits_before == credits_after:
        print(f"✅ PASS: Credits unchanged ({credits_before} → {credits_after}) - no charge on failure")
        results.append(("No charge on 502 failure", True))
    else:
        print(f"❌ FAIL: Credits changed ({credits_before} → {credits_after}) - user was charged!")
        results.append(("No charge on 502 failure", False))
    
    # ========================================================================
    # TEST 2: No auth → 401
    # ========================================================================
    print("\n[TEST 2] No auth → 401")
    print("-" * 80)
    
    r = requests.post(f"{BASE_URL}/threads/{demo_thread_id}/complete-action")
    if r.status_code == 401:
        print(f"✅ PASS: No auth returns 401")
        results.append(("No auth returns 401", True))
    else:
        print(f"❌ FAIL: Expected 401, got {r.status_code}")
        results.append(("No auth returns 401", False))
    
    # ========================================================================
    # TEST 3: Nonexistent thread_id → 404
    # ========================================================================
    print("\n[TEST 3] Nonexistent thread_id → 404")
    print("-" * 80)
    
    fake_thread_id = "00000000-0000-0000-0000-000000000000"
    r = complete_action(fake_thread_id, demo_token)
    if r.status_code == 404:
        print(f"✅ PASS: Nonexistent thread returns 404")
        results.append(("Nonexistent thread returns 404", True))
    else:
        print(f"❌ FAIL: Expected 404, got {r.status_code}")
        results.append(("Nonexistent thread returns 404", False))
    
    # ========================================================================
    # TEST 4: Thread ownership - admin calls demo's thread → 404
    # ========================================================================
    print("\n[TEST 4] Thread ownership: admin calls demo's thread → 404")
    print("-" * 80)
    
    admin_token, admin_user = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not admin_token:
        print("❌ FAIL: Could not login as admin")
        results.append(("Admin login", False))
        return 1
    
    print(f"✓ Logged in as admin: {admin_user['email']}")
    
    # Admin tries to call complete-action on demo's thread
    r = complete_action(demo_thread_id, admin_token)
    if r.status_code == 404:
        print(f"✅ PASS: Admin calling demo's thread returns 404 (ownership check)")
        results.append(("Thread ownership check", True))
    else:
        print(f"❌ FAIL: Expected 404, got {r.status_code}: {r.text}")
        results.append(("Thread ownership check", False))
    
    # ========================================================================
    # TEST 5: Verify no 'action_assist' ledger entries for demo
    # ========================================================================
    print("\n[TEST 5] Verify no 'action_assist' ledger entries created during failures")
    print("-" * 80)
    
    activity_r = get_user_activity(demo_user_id, admin_token)
    if activity_r.status_code != 200:
        print(f"❌ FAIL: Could not get user activity: {activity_r.status_code}")
        results.append(("Get user activity", False))
    else:
        activity_data = activity_r.json()
        ledger = activity_data.get('ledger', [])
        
        # Check for action_assist entries from today
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date()
        action_assist_today = [
            entry for entry in ledger 
            if entry.get('type') == 'action_assist' 
            and datetime.fromisoformat(entry['at'].replace('Z', '+00:00')).date() == today
        ]
        
        if len(action_assist_today) == 0:
            print(f"✅ PASS: No 'action_assist' ledger entries from today (expected)")
            results.append(("No action_assist ledger on failure", True))
        else:
            print(f"❌ FAIL: Found {len(action_assist_today)} action_assist entries from today:")
            for entry in action_assist_today:
                print(f"  - {entry}")
            results.append(("No action_assist ledger on failure", False))
    
    # ========================================================================
    # TEST 6: Smoke test existing endpoints
    # ========================================================================
    print("\n[TEST 6] Smoke test existing endpoints")
    print("-" * 80)
    
    # GET /goals as demo
    goals_r = requests.get(f"{BASE_URL}/goals", headers={"Authorization": f"Bearer {demo_token}"})
    if goals_r.status_code == 200:
        print(f"✅ PASS: GET /goals (demo) returns 200")
        results.append(("Smoke: GET /goals", True))
    else:
        print(f"❌ FAIL: GET /goals returned {goals_r.status_code}")
        results.append(("Smoke: GET /goals", False))
    
    # GET /admin/overview as admin
    overview_r = get_admin_overview(admin_token)
    if overview_r.status_code == 200:
        print(f"✅ PASS: GET /admin/overview (admin) returns 200")
        results.append(("Smoke: GET /admin/overview", True))
    else:
        print(f"❌ FAIL: GET /admin/overview returned {overview_r.status_code}")
        results.append(("Smoke: GET /admin/overview", False))
    
    # ========================================================================
    # TEST 7: Verify thread document not modified
    # ========================================================================
    print("\n[TEST 7] Verify thread document not modified by failed complete-action")
    print("-" * 80)
    
    thread_r2 = get_thread(demo_thread_id, demo_token)
    if thread_r2.status_code == 200:
        thread_data2 = thread_r2.json()
        # Check that thread still has its fields intact
        if 'thread' in thread_data2 and 'current_next_action' in thread_data2['thread']:
            print(f"✅ PASS: GET /threads/{demo_thread_id} still returns 200 with fields intact")
            results.append(("Thread document intact", True))
        else:
            print(f"❌ FAIL: Thread document missing expected fields")
            results.append(("Thread document intact", False))
    else:
        print(f"❌ FAIL: GET /threads/{demo_thread_id} returned {thread_r2.status_code}")
        results.append(("Thread document intact", False))
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
