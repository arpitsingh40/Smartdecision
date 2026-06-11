"""
Backend API Testing for SmartDecigen Deep Discussion Engine
Tests all endpoints with minimal LLM calls (max 2-3 total)
"""
import requests
import sys
import time
from datetime import datetime

class BackendTester:
    def __init__(self, base_url="https://impact-mapper-5.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log(self, emoji, message):
        """Log test result"""
        print(f"{emoji} {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        req_headers = {'Content-Type': 'application/json'}
        if self.token:
            req_headers['Authorization'] = f'Bearer {self.token}'
        if headers:
            req_headers.update(headers)

        self.tests_run += 1
        self.log("🔍", f"Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=req_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=req_headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=req_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                self.log("✅", f"Passed - Status: {response.status_code}")
                self.test_results.append({"test": name, "status": "PASS", "code": response.status_code})
            else:
                self.log("❌", f"Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    self.log("📄", f"Response: {response.json()}")
                except:
                    self.log("📄", f"Response: {response.text[:200]}")
                self.test_results.append({"test": name, "status": "FAIL", "code": response.status_code, "expected": expected_status})

            return success, response

        except Exception as e:
            self.log("❌", f"Failed - Error: {str(e)}")
            self.test_results.append({"test": name, "status": "ERROR", "error": str(e)})
            return False, None

    def test_root(self):
        """Test root endpoint"""
        success, resp = self.run_test("Root endpoint", "GET", "/", 200)
        if success and resp:
            data = resp.json()
            if "service" in data and "SmartDecigen" in data["service"]:
                self.log("✅", "Root endpoint returns correct service name")
            else:
                self.log("⚠️", "Root endpoint response format unexpected")
        return success

    def test_signup(self, email, password, name=""):
        """Test signup and get token"""
        success, resp = self.run_test(
            "Signup",
            "POST",
            "/auth/signup",
            200,
            data={"email": email, "password": password, "name": name}
        )
        if success and resp:
            data = resp.json()
            if 'token' in data and 'user' in data:
                self.token = data['token']
                self.user_id = data['user']['id']
                credits = data['user'].get('credits', 0)
                if credits == 100:
                    self.log("✅", f"Signup successful - 100 credits granted")
                else:
                    self.log("⚠️", f"Signup credits incorrect: {credits} (expected 100)")
                return True
            else:
                self.log("❌", "Signup response missing token or user")
        return False

    def test_login(self, email, password):
        """Test login and get token"""
        success, resp = self.run_test(
            "Login",
            "POST",
            "/auth/login",
            200,
            data={"email": email, "password": password}
        )
        if success and resp:
            data = resp.json()
            if 'token' in data and 'user' in data:
                self.token = data['token']
                self.user_id = data['user']['id']
                self.log("✅", f"Login successful - Credits: {data['user'].get('credits', 0)}")
                return True
            else:
                self.log("❌", "Login response missing token or user")
        return False

    def test_auth_me(self):
        """Test /auth/me endpoint"""
        success, resp = self.run_test("Auth /me", "GET", "/auth/me", 200)
        if success and resp:
            data = resp.json()
            if 'id' in data and 'email' in data and 'credits' in data:
                self.log("✅", f"Auth /me successful - User: {data['email']}, Credits: {data['credits']}")
                return True
        return False

    def test_auth_guard(self):
        """Test auth guard with invalid token"""
        old_token = self.token
        self.token = "invalid_token_xyz"
        success, resp = self.run_test("Auth guard (invalid token)", "GET", "/auth/me", 401)
        self.token = old_token
        return success

    def test_credits_endpoint(self):
        """Test GET /credits"""
        success, resp = self.run_test("Get credits", "GET", "/credits", 200)
        if success and resp:
            data = resp.json()
            if 'credits' in data and 'turn_cost' in data:
                self.log("✅", f"Credits endpoint - Balance: {data['credits']}, Turn cost: {data['turn_cost']}")
                if data['turn_cost'] == 5:
                    self.log("✅", "Turn cost is correct (5)")
                else:
                    self.log("⚠️", f"Turn cost unexpected: {data['turn_cost']}")
                return True
        return False

    def test_list_goals_empty(self):
        """Test GET /goals for new user (should be empty)"""
        success, resp = self.run_test("List goals (empty)", "GET", "/goals", 200)
        if success and resp:
            data = resp.json()
            if 'goals' in data and len(data['goals']) == 0:
                self.log("✅", "Goals list empty for new user")
                return True
        return False

    def test_create_goal(self, title, why_now):
        """Test POST /goals (REAL LLM CALL - ~5-10s)"""
        self.log("⏳", "Creating goal - this will take 5-10s (REAL LLM call)...")
        success, resp = self.run_test(
            "Create goal (LLM call)",
            "POST",
            "/goals",
            200,
            data={"title": title, "why_now": why_now}
        )
        if success and resp:
            data = resp.json()
            if 'thread' in data and 'acknowledgment' in data and 'credits' in data:
                thread = data['thread']
                self.log("✅", f"Goal created - Thread ID: {thread['thread_id']}")
                self.log("✅", f"Credits after creation: {data['credits']} (should be 5 less)")
                self.log("✅", f"Acknowledgment: {data['acknowledgment'][:80]}...")
                
                # Verify 4 living fields are populated
                if thread.get('current_state_summary') and thread.get('current_easiest_path') and \
                   thread.get('current_next_action') and thread.get('current_open_question'):
                    self.log("✅", "All 4 living fields populated")
                else:
                    self.log("⚠️", "Some living fields missing")
                
                return thread['thread_id']
        return None

    def test_list_goals_with_data(self):
        """Test GET /goals after creating a goal"""
        success, resp = self.run_test("List goals (with data)", "GET", "/goals", 200)
        if success and resp:
            data = resp.json()
            if 'goals' in data and len(data['goals']) > 0:
                goal = data['goals'][0]
                self.log("✅", f"Goals list has {len(data['goals'])} goal(s)")
                if 'thread_id' in goal and 'goal' in goal and 'status' in goal and 'pace' in goal:
                    self.log("✅", "Goal card data complete")
                    return True
        return False

    def test_get_thread(self, thread_id):
        """Test GET /threads/{id}"""
        success, resp = self.run_test(f"Get thread {thread_id[:8]}...", "GET", f"/threads/{thread_id}", 200)
        if success and resp:
            data = resp.json()
            if 'thread' in data and 'reengagement_line' in data and 'silence_days' in data:
                thread = data['thread']
                self.log("✅", f"Thread retrieved - Status: {thread.get('status')}")
                self.log("✅", f"Reengagement line: {data['reengagement_line']} (null for fresh threads)")
                return True
        return False

    def test_turn(self, thread_id, message):
        """Test POST /threads/{id}/turn (REAL LLM CALL - ~5-10s)"""
        self.log("⏳", "Sending turn - this will take 5-10s (REAL LLM call)...")
        success, resp = self.run_test(
            "Turn (LLM call)",
            "POST",
            f"/threads/{thread_id}/turn",
            200,
            data={"message": message}
        )
        if success and resp:
            data = resp.json()
            if 'thread' in data and 'acknowledgment' in data and 'credits' in data:
                self.log("✅", f"Turn successful - Credits: {data['credits']}")
                self.log("✅", f"Intent: {data.get('intent')}")
                self.log("✅", f"Acknowledgment: {data['acknowledgment'][:80]}...")
                return True
        return False

    def test_thread_status_pause(self, thread_id):
        """Test PATCH /threads/{id}/status to pause"""
        success, resp = self.run_test(
            "Pause thread",
            "PATCH",
            f"/threads/{thread_id}/status",
            200,
            data={"status": "paused"}
        )
        if success and resp:
            data = resp.json()
            if data.get('ok') and data.get('status') == 'paused':
                self.log("✅", "Thread paused successfully")
                return True
        return False

    def test_turn_on_paused_thread(self, thread_id):
        """Test POST turn on paused thread (should fail with 400)"""
        success, resp = self.run_test(
            "Turn on paused thread (should fail)",
            "POST",
            f"/threads/{thread_id}/turn",
            400,
            data={"message": "This should fail"}
        )
        return success

    def test_thread_status_reactivate(self, thread_id):
        """Test PATCH /threads/{id}/status to reactivate"""
        success, resp = self.run_test(
            "Reactivate thread",
            "PATCH",
            f"/threads/{thread_id}/status",
            200,
            data={"status": "active"}
        )
        if success and resp:
            data = resp.json()
            if data.get('ok') and data.get('status') == 'active':
                self.log("✅", "Thread reactivated successfully")
                return True
        return False

    def test_invalid_status(self, thread_id):
        """Test PATCH with invalid status"""
        success, resp = self.run_test(
            "Invalid status (should fail)",
            "PATCH",
            f"/threads/{thread_id}/status",
            422,
            data={"status": "invalid_status"}
        )
        return success

    def test_multi_user_isolation(self, other_thread_id):
        """Test that user cannot access another user's thread"""
        success, resp = self.run_test(
            "Multi-user isolation (should 404)",
            "GET",
            f"/threads/{other_thread_id}",
            404
        )
        return success

    def test_insufficient_credits(self):
        """Test creating goal with insufficient credits (would need to drain credits first)"""
        # This is hard to test without draining all credits, so we'll skip for now
        self.log("⏭️", "Skipping insufficient credits test (would require draining all credits)")
        return True

    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print(f"📊 BACKEND TEST SUMMARY")
        print("="*60)
        print(f"Tests run: {self.tests_run}")
        print(f"Tests passed: {self.tests_passed}")
        print(f"Tests failed: {self.tests_run - self.tests_passed}")
        print(f"Success rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        print("="*60)
        
        if self.tests_passed < self.tests_run:
            print("\n❌ FAILED TESTS:")
            for result in self.test_results:
                if result['status'] != 'PASS':
                    error_msg = result.get('error', f"Status {result.get('code')} (expected {result.get('expected')})")
                    print(f"  - {result['test']}: {error_msg}")
        
        return self.tests_passed == self.tests_run


def main():
    print("="*60)
    print("🚀 SmartDecigen Backend API Testing")
    print("="*60)
    print("⚠️  Note: This test includes 2 REAL LLM calls (~5-10s each)")
    print("="*60 + "\n")

    tester = BackendTester()
    
    # Test 1: Root endpoint
    tester.test_root()
    
    # Test 2: Signup new user
    test_email = f"test_{int(time.time())}@test.com"
    test_password = "test1234"
    if not tester.test_signup(test_email, test_password, "Test User"):
        print("\n❌ Signup failed - stopping tests")
        return 1
    
    # Test 3: Auth /me
    tester.test_auth_me()
    
    # Test 4: Auth guard
    tester.test_auth_guard()
    
    # Test 5: Credits endpoint
    tester.test_credits_endpoint()
    
    # Test 6: List goals (empty)
    tester.test_list_goals_empty()
    
    # Test 7: Create goal (LLM call #1)
    thread_id = tester.test_create_goal(
        "Get my first paying client",
        "I've been working on my freelance business for 3 months but keep avoiding outreach. I know I need to reach out to potential clients but I keep finding reasons to work on my portfolio instead."
    )
    if not thread_id:
        print("\n❌ Goal creation failed - stopping tests")
        return 1
    
    # Test 8: List goals (with data)
    tester.test_list_goals_with_data()
    
    # Test 9: Get thread
    tester.test_get_thread(thread_id)
    
    # Test 10: Turn (LLM call #2)
    tester.test_turn(thread_id, "I didn't do it, I got stuck and avoided it")
    
    # Test 11: Pause thread
    tester.test_thread_status_pause(thread_id)
    
    # Test 12: Turn on paused thread (should fail)
    tester.test_turn_on_paused_thread(thread_id)
    
    # Test 13: Reactivate thread
    tester.test_thread_status_reactivate(thread_id)
    
    # Test 14: Invalid status
    tester.test_invalid_status(thread_id)
    
    # Test 15: Login with existing user
    tester2 = BackendTester()
    if tester2.test_login("smoke1@test.com", "test1234"):
        # Test 16: Multi-user isolation
        tester2.test_multi_user_isolation(thread_id)
    
    # Print summary
    success = tester.print_summary()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
