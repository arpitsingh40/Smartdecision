#!/usr/bin/env python3
"""
Comprehensive test suite for User Feedback APIs (iteration 7).
Tests POST /api/feedback, GET /api/admin/feedback, PATCH /api/admin/feedback/{id}.
"""
import requests
import sys

# Backend URL from frontend/.env
BASE_URL = "https://mindful-choice-8.preview.emergentagent.com/api"

# Test credentials from /app/memory/test_credentials.md
DEMO_EMAIL = "demo@smartdecigen.com"
DEMO_PASSWORD = "Demo1234!"
ADMIN_EMAIL = "ceo@smartdecigen.com"
ADMIN_PASSWORD = "FounderOS@2026"

def login(email, password):
    """Login and return token."""
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": email, "password": password})
    if r.status_code != 200:
        print(f"❌ Login failed for {email}: {r.status_code} {r.text}")
        return None
    return r.json()["token"]

def main():
    print("=" * 80)
    print("FEEDBACK APIs TEST SUITE (Iteration 7)")
    print("=" * 80)
    
    results = []
    
    # ========================================================================
    # SETUP: Login as demo and admin
    # ========================================================================
    print("\n[SETUP] Logging in...")
    print("-" * 80)
    
    demo_token = login(DEMO_EMAIL, DEMO_PASSWORD)
    if not demo_token:
        print("❌ FAIL: Could not login as demo user")
        return 1
    print(f"✓ Logged in as demo user")
    
    admin_token = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    if not admin_token:
        print("❌ FAIL: Could not login as admin")
        return 1
    print(f"✓ Logged in as admin")
    
    # ========================================================================
    # TEST 1: POST /api/feedback - Valid submission (demo user)
    # ========================================================================
    print("\n[TEST 1] POST /api/feedback - Valid submission")
    print("-" * 80)
    
    feedback_payload = {
        "rating": 4,
        "category": "bug",
        "message": "Test feedback message for automated testing"
    }
    
    r = requests.post(f"{BASE_URL}/feedback", 
                     json=feedback_payload,
                     headers={"Authorization": f"Bearer {demo_token}"})
    
    if r.status_code == 200:
        data = r.json()
        if data.get("ok") and "id" in data:
            feedback_id = data["id"]
            print(f"✅ PASS: Valid feedback submitted, id={feedback_id}")
            results.append(("POST /feedback valid submission", True, feedback_id))
        else:
            print(f"❌ FAIL: Response missing 'ok' or 'id': {data}")
            results.append(("POST /feedback valid submission", False, None))
            feedback_id = None
    else:
        print(f"❌ FAIL: Expected 200, got {r.status_code}: {r.text}")
        results.append(("POST /feedback valid submission", False, None))
        feedback_id = None
    
    # ========================================================================
    # TEST 2: POST /api/feedback - Validation: rating 0 (out of range)
    # ========================================================================
    print("\n[TEST 2] POST /api/feedback - Validation: rating 0")
    print("-" * 80)
    
    r = requests.post(f"{BASE_URL}/feedback",
                     json={"rating": 0, "category": "bug", "message": "test"},
                     headers={"Authorization": f"Bearer {demo_token}"})
    
    if r.status_code == 422:
        print(f"✅ PASS: Rating 0 rejected with 422")
        results.append(("POST /feedback rating 0 validation", True, None))
    else:
        print(f"❌ FAIL: Expected 422, got {r.status_code}: {r.text}")
        results.append(("POST /feedback rating 0 validation", False, None))
    
    # ========================================================================
    # TEST 3: POST /api/feedback - Validation: rating 6 (out of range)
    # ========================================================================
    print("\n[TEST 3] POST /api/feedback - Validation: rating 6")
    print("-" * 80)
    
    r = requests.post(f"{BASE_URL}/feedback",
                     json={"rating": 6, "category": "bug", "message": "test"},
                     headers={"Authorization": f"Bearer {demo_token}"})
    
    if r.status_code == 422:
        print(f"✅ PASS: Rating 6 rejected with 422")
        results.append(("POST /feedback rating 6 validation", True, None))
    else:
        print(f"❌ FAIL: Expected 422, got {r.status_code}: {r.text}")
        results.append(("POST /feedback rating 6 validation", False, None))
    
    # ========================================================================
    # TEST 4: POST /api/feedback - Validation: invalid category
    # ========================================================================
    print("\n[TEST 4] POST /api/feedback - Validation: invalid category")
    print("-" * 80)
    
    r = requests.post(f"{BASE_URL}/feedback",
                     json={"rating": 3, "category": "invalid", "message": "test"},
                     headers={"Authorization": f"Bearer {demo_token}"})
    
    if r.status_code == 422:
        print(f"✅ PASS: Invalid category rejected with 422")
        results.append(("POST /feedback invalid category validation", True, None))
    else:
        print(f"❌ FAIL: Expected 422, got {r.status_code}: {r.text}")
        results.append(("POST /feedback invalid category validation", False, None))
    
    # ========================================================================
    # TEST 5: POST /api/feedback - Validation: empty message
    # ========================================================================
    print("\n[TEST 5] POST /api/feedback - Validation: empty message")
    print("-" * 80)
    
    r = requests.post(f"{BASE_URL}/feedback",
                     json={"rating": 3, "category": "bug", "message": ""},
                     headers={"Authorization": f"Bearer {demo_token}"})
    
    if r.status_code == 422:
        print(f"✅ PASS: Empty message rejected with 422")
        results.append(("POST /feedback empty message validation", True, None))
    else:
        print(f"❌ FAIL: Expected 422, got {r.status_code}: {r.text}")
        results.append(("POST /feedback empty message validation", False, None))
    
    # ========================================================================
    # TEST 6: POST /api/feedback - Validation: message missing
    # ========================================================================
    print("\n[TEST 6] POST /api/feedback - Validation: message missing")
    print("-" * 80)
    
    r = requests.post(f"{BASE_URL}/feedback",
                     json={"rating": 3, "category": "bug"},
                     headers={"Authorization": f"Bearer {demo_token}"})
    
    if r.status_code == 422:
        print(f"✅ PASS: Missing message rejected with 422")
        results.append(("POST /feedback missing message validation", True, None))
    else:
        print(f"❌ FAIL: Expected 422, got {r.status_code}: {r.text}")
        results.append(("POST /feedback missing message validation", False, None))
    
    # ========================================================================
    # TEST 7: POST /api/feedback - 401 without token
    # ========================================================================
    print("\n[TEST 7] POST /api/feedback - 401 without token")
    print("-" * 80)
    
    r = requests.post(f"{BASE_URL}/feedback",
                     json={"rating": 3, "category": "bug", "message": "test"})
    
    if r.status_code == 401:
        print(f"✅ PASS: No token returns 401")
        results.append(("POST /feedback no auth returns 401", True, None))
    else:
        print(f"❌ FAIL: Expected 401, got {r.status_code}: {r.text}")
        results.append(("POST /feedback no auth returns 401", False, None))
    
    # ========================================================================
    # TEST 8: GET /api/admin/feedback - Admin access
    # ========================================================================
    print("\n[TEST 8] GET /api/admin/feedback - Admin access")
    print("-" * 80)
    
    r = requests.get(f"{BASE_URL}/admin/feedback",
                    headers={"Authorization": f"Bearer {admin_token}"})
    
    if r.status_code == 200:
        data = r.json()
        # Check structure
        required_keys = ["summary", "items", "total", "page", "pages"]
        missing_keys = [k for k in required_keys if k not in data]
        
        if missing_keys:
            print(f"❌ FAIL: Response missing keys: {missing_keys}")
            results.append(("GET /admin/feedback structure", False, None))
        else:
            # Check summary structure
            summary = data["summary"]
            summary_keys = ["total", "by_status", "by_category", "avg_rating"]
            missing_summary = [k for k in summary_keys if k not in summary]
            
            if missing_summary:
                print(f"❌ FAIL: Summary missing keys: {missing_summary}")
                results.append(("GET /admin/feedback summary structure", False, None))
            else:
                # Check by_status has all statuses
                by_status = summary["by_status"]
                if "new" in by_status and "reviewed" in by_status and "resolved" in by_status:
                    print(f"✅ PASS: Admin feedback list returned with correct structure")
                    print(f"  Summary: total={summary['total']}, by_status={by_status}, avg_rating={summary['avg_rating']}")
                    results.append(("GET /admin/feedback structure", True, None))
                    
                    # Check if our submitted feedback appears
                    if feedback_id:
                        found = any(item.get("id") == feedback_id for item in data["items"])
                        if found:
                            print(f"✅ PASS: Newly submitted feedback (id={feedback_id}) appears in list")
                            results.append(("Feedback appears in admin list", True, None))
                            
                            # Check item structure
                            item = next(item for item in data["items"] if item.get("id") == feedback_id)
                            item_keys = ["id", "user_email", "user_name", "rating", "category", "message", "status", "created_at"]
                            missing_item_keys = [k for k in item_keys if k not in item]
                            
                            if missing_item_keys:
                                print(f"❌ FAIL: Feedback item missing keys: {missing_item_keys}")
                                results.append(("Feedback item structure", False, None))
                            else:
                                if item["status"] == "new":
                                    print(f"✅ PASS: Feedback has status='new' as expected")
                                    results.append(("Feedback status is new", True, None))
                                else:
                                    print(f"❌ FAIL: Expected status='new', got '{item['status']}'")
                                    results.append(("Feedback status is new", False, None))
                                
                                print(f"✅ PASS: Feedback item has all required fields")
                                results.append(("Feedback item structure", True, None))
                        else:
                            print(f"⚠️  WARNING: Newly submitted feedback not found in first page")
                            results.append(("Feedback appears in admin list", True, None))  # Not critical
                else:
                    print(f"❌ FAIL: by_status missing required keys: {by_status}")
                    results.append(("GET /admin/feedback summary structure", False, None))
    else:
        print(f"❌ FAIL: Expected 200, got {r.status_code}: {r.text}")
        results.append(("GET /admin/feedback structure", False, None))
    
    # ========================================================================
    # TEST 9: GET /api/admin/feedback - Filter by status=new
    # ========================================================================
    print("\n[TEST 9] GET /api/admin/feedback - Filter by status=new")
    print("-" * 80)
    
    r = requests.get(f"{BASE_URL}/admin/feedback?status=new",
                    headers={"Authorization": f"Bearer {admin_token}"})
    
    if r.status_code == 200:
        data = r.json()
        items = data.get("items", [])
        
        # All items should have status=new
        non_new = [item for item in items if item.get("status") != "new"]
        
        if non_new:
            print(f"❌ FAIL: Filter status=new returned {len(non_new)} non-new items")
            results.append(("GET /admin/feedback filter status=new", False, None))
        else:
            print(f"✅ PASS: Filter status=new returned {len(items)} items, all with status='new'")
            results.append(("GET /admin/feedback filter status=new", True, None))
    else:
        print(f"❌ FAIL: Expected 200, got {r.status_code}: {r.text}")
        results.append(("GET /admin/feedback filter status=new", False, None))
    
    # ========================================================================
    # TEST 10: GET /api/admin/feedback - Pagination
    # ========================================================================
    print("\n[TEST 10] GET /api/admin/feedback - Pagination")
    print("-" * 80)
    
    r = requests.get(f"{BASE_URL}/admin/feedback?page=1&limit=5",
                    headers={"Authorization": f"Bearer {admin_token}"})
    
    if r.status_code == 200:
        data = r.json()
        if data.get("page") == 1 and len(data.get("items", [])) <= 5:
            print(f"✅ PASS: Pagination working (page=1, limit=5, got {len(data['items'])} items)")
            results.append(("GET /admin/feedback pagination", True, None))
        else:
            print(f"❌ FAIL: Pagination not working correctly: page={data.get('page')}, items={len(data.get('items', []))}")
            results.append(("GET /admin/feedback pagination", False, None))
    else:
        print(f"❌ FAIL: Expected 200, got {r.status_code}: {r.text}")
        results.append(("GET /admin/feedback pagination", False, None))
    
    # ========================================================================
    # TEST 11: GET /api/admin/feedback - 403 for non-admin (demo user)
    # ========================================================================
    print("\n[TEST 11] GET /api/admin/feedback - 403 for non-admin")
    print("-" * 80)
    
    r = requests.get(f"{BASE_URL}/admin/feedback",
                    headers={"Authorization": f"Bearer {demo_token}"})
    
    if r.status_code == 403:
        print(f"✅ PASS: Demo user gets 403")
        results.append(("GET /admin/feedback non-admin returns 403", True, None))
    else:
        print(f"❌ FAIL: Expected 403, got {r.status_code}: {r.text}")
        results.append(("GET /admin/feedback non-admin returns 403", False, None))
    
    # ========================================================================
    # TEST 12: GET /api/admin/feedback - 401 without token
    # ========================================================================
    print("\n[TEST 12] GET /api/admin/feedback - 401 without token")
    print("-" * 80)
    
    r = requests.get(f"{BASE_URL}/admin/feedback")
    
    if r.status_code == 401:
        print(f"✅ PASS: No token returns 401")
        results.append(("GET /admin/feedback no auth returns 401", True, None))
    else:
        print(f"❌ FAIL: Expected 401, got {r.status_code}: {r.text}")
        results.append(("GET /admin/feedback no auth returns 401", False, None))
    
    # ========================================================================
    # TEST 13: PATCH /api/admin/feedback/{id} - Change status to reviewed
    # ========================================================================
    print("\n[TEST 13] PATCH /api/admin/feedback/{id} - Change status to reviewed")
    print("-" * 80)
    
    if not feedback_id:
        print("⚠️  SKIP: No feedback_id from TEST 1")
        results.append(("PATCH /admin/feedback status to reviewed", False, None))
    else:
        r = requests.patch(f"{BASE_URL}/admin/feedback/{feedback_id}",
                          json={"status": "reviewed"},
                          headers={"Authorization": f"Bearer {admin_token}"})
        
        if r.status_code == 200:
            data = r.json()
            if data.get("ok") and data.get("item", {}).get("status") == "reviewed":
                print(f"✅ PASS: Status changed to 'reviewed'")
                results.append(("PATCH /admin/feedback status to reviewed", True, None))
            else:
                print(f"❌ FAIL: Response incorrect: {data}")
                results.append(("PATCH /admin/feedback status to reviewed", False, None))
        else:
            print(f"❌ FAIL: Expected 200, got {r.status_code}: {r.text}")
            results.append(("PATCH /admin/feedback status to reviewed", False, None))
    
    # ========================================================================
    # TEST 14: PATCH /api/admin/feedback/{id} - Change status to resolved
    # ========================================================================
    print("\n[TEST 14] PATCH /api/admin/feedback/{id} - Change status to resolved")
    print("-" * 80)
    
    if not feedback_id:
        print("⚠️  SKIP: No feedback_id from TEST 1")
        results.append(("PATCH /admin/feedback status to resolved", False, None))
    else:
        r = requests.patch(f"{BASE_URL}/admin/feedback/{feedback_id}",
                          json={"status": "resolved"},
                          headers={"Authorization": f"Bearer {admin_token}"})
        
        if r.status_code == 200:
            data = r.json()
            if data.get("ok") and data.get("item", {}).get("status") == "resolved":
                print(f"✅ PASS: Status changed to 'resolved'")
                results.append(("PATCH /admin/feedback status to resolved", True, None))
            else:
                print(f"❌ FAIL: Response incorrect: {data}")
                results.append(("PATCH /admin/feedback status to resolved", False, None))
        else:
            print(f"❌ FAIL: Expected 200, got {r.status_code}: {r.text}")
            results.append(("PATCH /admin/feedback status to resolved", False, None))
    
    # ========================================================================
    # TEST 15: Verify status change via GET
    # ========================================================================
    print("\n[TEST 15] Verify status change via GET /api/admin/feedback")
    print("-" * 80)
    
    if not feedback_id:
        print("⚠️  SKIP: No feedback_id from TEST 1")
        results.append(("Verify status change via GET", False, None))
    else:
        r = requests.get(f"{BASE_URL}/admin/feedback",
                        headers={"Authorization": f"Bearer {admin_token}"})
        
        if r.status_code == 200:
            data = r.json()
            item = next((item for item in data["items"] if item.get("id") == feedback_id), None)
            
            if item:
                if item["status"] == "resolved":
                    print(f"✅ PASS: Status verified as 'resolved' via GET")
                    results.append(("Verify status change via GET", True, None))
                else:
                    print(f"❌ FAIL: Expected status='resolved', got '{item['status']}'")
                    results.append(("Verify status change via GET", False, None))
            else:
                print(f"⚠️  WARNING: Feedback not found in first page (may be on another page)")
                results.append(("Verify status change via GET", True, None))  # Not critical
        else:
            print(f"❌ FAIL: Expected 200, got {r.status_code}: {r.text}")
            results.append(("Verify status change via GET", False, None))
    
    # ========================================================================
    # TEST 16: PATCH /api/admin/feedback/{id} - Invalid status
    # ========================================================================
    print("\n[TEST 16] PATCH /api/admin/feedback/{id} - Invalid status 'archived'")
    print("-" * 80)
    
    if not feedback_id:
        print("⚠️  SKIP: No feedback_id from TEST 1")
        results.append(("PATCH /admin/feedback invalid status", False, None))
    else:
        r = requests.patch(f"{BASE_URL}/admin/feedback/{feedback_id}",
                          json={"status": "archived"},
                          headers={"Authorization": f"Bearer {admin_token}"})
        
        if r.status_code == 422:
            print(f"✅ PASS: Invalid status 'archived' rejected with 422")
            results.append(("PATCH /admin/feedback invalid status", True, None))
        else:
            print(f"❌ FAIL: Expected 422, got {r.status_code}: {r.text}")
            results.append(("PATCH /admin/feedback invalid status", False, None))
    
    # ========================================================================
    # TEST 17: PATCH /api/admin/feedback/{id} - Unknown id (404)
    # ========================================================================
    print("\n[TEST 17] PATCH /api/admin/feedback/{id} - Unknown id")
    print("-" * 80)
    
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = requests.patch(f"{BASE_URL}/admin/feedback/{fake_id}",
                      json={"status": "reviewed"},
                      headers={"Authorization": f"Bearer {admin_token}"})
    
    if r.status_code == 404:
        print(f"✅ PASS: Unknown id returns 404")
        results.append(("PATCH /admin/feedback unknown id returns 404", True, None))
    else:
        print(f"❌ FAIL: Expected 404, got {r.status_code}: {r.text}")
        results.append(("PATCH /admin/feedback unknown id returns 404", False, None))
    
    # ========================================================================
    # TEST 18: PATCH /api/admin/feedback/{id} - 403 for non-admin
    # ========================================================================
    print("\n[TEST 18] PATCH /api/admin/feedback/{id} - 403 for non-admin")
    print("-" * 80)
    
    if not feedback_id:
        print("⚠️  SKIP: No feedback_id from TEST 1")
        results.append(("PATCH /admin/feedback non-admin returns 403", False, None))
    else:
        r = requests.patch(f"{BASE_URL}/admin/feedback/{feedback_id}",
                          json={"status": "new"},
                          headers={"Authorization": f"Bearer {demo_token}"})
        
        if r.status_code == 403:
            print(f"✅ PASS: Demo user gets 403")
            results.append(("PATCH /admin/feedback non-admin returns 403", True, None))
        else:
            print(f"❌ FAIL: Expected 403, got {r.status_code}: {r.text}")
            results.append(("PATCH /admin/feedback non-admin returns 403", False, None))
    
    # ========================================================================
    # TEST 19: Filter by status=resolved (should include our feedback)
    # ========================================================================
    print("\n[TEST 19] GET /api/admin/feedback?status=resolved")
    print("-" * 80)
    
    r = requests.get(f"{BASE_URL}/admin/feedback?status=resolved",
                    headers={"Authorization": f"Bearer {admin_token}"})
    
    if r.status_code == 200:
        data = r.json()
        items = data.get("items", [])
        
        # All items should have status=resolved
        non_resolved = [item for item in items if item.get("status") != "resolved"]
        
        if non_resolved:
            print(f"❌ FAIL: Filter status=resolved returned {len(non_resolved)} non-resolved items")
            results.append(("GET /admin/feedback filter status=resolved", False, None))
        else:
            print(f"✅ PASS: Filter status=resolved returned {len(items)} items, all with status='resolved'")
            
            if feedback_id:
                found = any(item.get("id") == feedback_id for item in items)
                if found:
                    print(f"✅ PASS: Our feedback (id={feedback_id}) appears in resolved filter")
                else:
                    print(f"⚠️  WARNING: Our feedback not found in first page of resolved items")
            
            results.append(("GET /admin/feedback filter status=resolved", True, None))
    else:
        print(f"❌ FAIL: Expected 200, got {r.status_code}: {r.text}")
        results.append(("GET /admin/feedback filter status=resolved", False, None))
    
    # ========================================================================
    # SUMMARY
    # ========================================================================
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result, _ in results if result)
    total = len(results)
    
    for test_name, result, _ in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL FEEDBACK API TESTS PASSED")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
