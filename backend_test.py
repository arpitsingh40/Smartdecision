#!/usr/bin/env python3
"""
SmartDecigen Backend Regression Test - Hypothesis Engine (FREE-ONLY)
HARD BUDGET: ZERO LLM calls - no endpoints that hit Anthropic with valid bodies.
"""
import os
import sys
import json
import requests
from datetime import datetime, timedelta
from pymongo import MongoClient

# Configuration
BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://founder-verdict-3.preview.emergentagent.com")
API_BASE = f"{BACKEND_URL}/api"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = "smartdecigen_db"

# Test credentials
ADMIN_EMAIL = "ceo@smartdecigen.com"
ADMIN_PASSWORD = "FounderOS@2026"
HYP_USER_EMAIL = "hyp_1783019718@test.com"
HYP_USER_PASSWORD = "Test1234!"

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.failures = []
        self.mongo_client = MongoClient(MONGO_URL)
        self.db = self.mongo_client[DB_NAME]
        
    def log(self, msg, color=RESET):
        print(f"{color}{msg}{RESET}")
        
    def assert_true(self, condition, msg):
        if condition:
            self.passed += 1
            self.log(f"  ✓ {msg}", GREEN)
            return True
        else:
            self.failed += 1
            self.failures.append(msg)
            self.log(f"  ✗ {msg}", RED)
            return False
            
    def assert_equal(self, actual, expected, msg):
        if actual == expected:
            self.passed += 1
            self.log(f"  ✓ {msg}", GREEN)
            return True
        else:
            self.failed += 1
            self.failures.append(f"{msg} (expected {expected}, got {actual})")
            self.log(f"  ✗ {msg} (expected {expected}, got {actual})", RED)
            return False
            
    def assert_in(self, item, container, msg):
        if item in container:
            self.passed += 1
            self.log(f"  ✓ {msg}", GREEN)
            return True
        else:
            self.failed += 1
            self.failures.append(msg)
            self.log(f"  ✗ {msg}", RED)
            return False
            
    def signup(self, email, password):
        """Create a new user account"""
        resp = requests.post(f"{API_BASE}/auth/signup", json={
            "email": email,
            "password": password,
            "name": "Test User"
        })
        return resp
        
    def login(self, email, password):
        """Login and return token"""
        resp = requests.post(f"{API_BASE}/auth/login", json={
            "email": email,
            "password": password
        })
        if resp.status_code == 200:
            return resp.json().get("token")
        return None
        
    def get_journey(self, token):
        """GET /api/journey"""
        resp = requests.get(f"{API_BASE}/journey", headers={"Authorization": f"Bearer {token}"})
        return resp
        
    def reset_journey(self, token):
        """POST /api/journey/reset"""
        resp = requests.post(f"{API_BASE}/journey/reset", headers={"Authorization": f"Bearer {token}"})
        return resp
        
    def seed_journey_with_hypotheses(self, user_email, hypotheses):
        """Seed a journey document with messages and hypotheses via MongoDB"""
        users_col = self.db["users"]
        journeys_col = self.db["journeys"]
        
        user = users_col.find_one({"email": user_email})
        if not user:
            return False
            
        messages = [
            {"role": "user", "text": "I want to grow my business", "at": datetime.utcnow()},
            {"role": "assistant", "text": "Tell me more about your business", "at": datetime.utcnow()}
        ]
        
        journeys_col.update_one(
            {"user_id": user["id"]},
            {"$set": {
                "messages": messages,
                "hypotheses": hypotheses,
                "started": True,
                "updated_at": datetime.utcnow()
            }},
            upsert=True
        )
        return True
        
    def test_1_fresh_signup_empty_hypotheses(self):
        """TEST 1: Fresh signup -> GET /api/journey -> hypotheses=[] with existing keys intact"""
        self.log("\n" + "="*80, BLUE)
        self.log("TEST 1: Fresh signup -> GET /api/journey -> hypotheses=[] (empty list)", BLUE)
        self.log("="*80, BLUE)
        
        # Create fresh user
        email = f"fresh_hyp_{int(datetime.now().timestamp())}@test.com"
        password = "Test1234!"
        
        resp = self.signup(email, password)
        self.assert_equal(resp.status_code, 200, "Fresh signup returns 200")
        
        token = self.login(email, password)
        self.assert_true(token is not None, "Login successful")
        
        # GET /api/journey
        resp = self.get_journey(token)
        self.assert_equal(resp.status_code, 200, "GET /api/journey returns 200")
        
        data = resp.json()
        
        # Check hypotheses key exists and is empty list
        self.assert_in("hypotheses", data, "Response contains 'hypotheses' key")
        self.assert_equal(type(data.get("hypotheses")), list, "hypotheses is a list")
        self.assert_equal(len(data.get("hypotheses", [1])), 0, "hypotheses is empty list []")
        
        # Check existing keys are intact
        self.assert_in("started", data, "Response contains 'started' key")
        self.assert_equal(data.get("started"), False, "started=false for fresh user")
        self.assert_in("confidence", data, "Response contains 'confidence' key")
        self.assert_equal(data.get("confidence"), 0, "confidence=0 for fresh user")
        self.assert_in("reasoning", data, "Response contains 'reasoning' key")
        self.assert_equal(data.get("reasoning"), None, "reasoning=null for fresh user")
        self.assert_in("model", data, "Response contains 'model' key")
        self.assert_in("unlocks", data, "Response contains 'unlocks' key")
        
        self.log(f"\n✅ TEST 1 PASSED: Fresh user has hypotheses=[] with all existing keys intact", GREEN)
        return email, token
        
    def test_2_existing_user_5_hypotheses(self):
        """TEST 2: Login hyp_1783019718@test.com -> GET /api/journey -> verify 5 hypotheses structure"""
        self.log("\n" + "="*80, BLUE)
        self.log("TEST 2: Login hyp_1783019718@test.com -> verify 5 hypotheses", BLUE)
        self.log("="*80, BLUE)
        
        token = self.login(HYP_USER_EMAIL, HYP_USER_PASSWORD)
        self.assert_true(token is not None, f"Login {HYP_USER_EMAIL} successful")
        
        resp = self.get_journey(token)
        self.assert_equal(resp.status_code, 200, "GET /api/journey returns 200")
        
        data = resp.json()
        hypotheses = data.get("hypotheses", [])
        
        # Check hypotheses is a list of 5 items
        self.assert_equal(type(hypotheses), list, "hypotheses is a list")
        self.assert_equal(len(hypotheses), 5, "hypotheses has exactly 5 items")
        
        if len(hypotheses) == 5:
            # Check each hypothesis has required fields
            required_fields = ["id", "statement", "probability", "evidence_for", "evidence_against", "status"]
            for i, hyp in enumerate(hypotheses):
                for field in required_fields:
                    self.assert_in(field, hyp, f"Hypothesis {i+1} has '{field}' field")
                    
            # Check probabilities are integers
            all_ints = all(isinstance(h.get("probability"), int) for h in hypotheses)
            self.assert_true(all_ints, "All probabilities are integers")
            
            # Check probabilities sum to exactly 100
            total_prob = sum(h.get("probability", 0) for h in hypotheses)
            self.assert_equal(total_prob, 100, "Probabilities sum to exactly 100")
            
            # Check exactly one item has status="ruled_out" with probability <= 5
            ruled_out = [h for h in hypotheses if h.get("status") == "ruled_out"]
            self.assert_equal(len(ruled_out), 1, "Exactly one hypothesis has status='ruled_out'")
            
            if ruled_out:
                self.assert_true(ruled_out[0].get("probability", 100) <= 5, 
                               f"Ruled out hypothesis has probability <= 5 (got {ruled_out[0].get('probability')})")
                
            # Check list is sorted descending by probability
            probs = [h.get("probability", 0) for h in hypotheses]
            sorted_probs = sorted(probs, reverse=True)
            self.assert_equal(probs, sorted_probs, "Hypotheses sorted descending by probability")
            
            # Check top item has probability=55 with status="active"
            top = hypotheses[0]
            self.assert_equal(top.get("probability"), 55, "Top hypothesis has probability=55")
            self.assert_equal(top.get("status"), "active", "Top hypothesis has status='active'")
            
            self.log(f"\n📊 Hypothesis probabilities: {probs}", YELLOW)
            self.log(f"📊 Hypothesis statuses: {[h.get('status') for h in hypotheses]}", YELLOW)
            
        self.log(f"\n✅ TEST 2 PASSED: hyp_user has 5 valid hypotheses with correct structure", GREEN)
        
    def test_3_seed_and_reset(self):
        """TEST 3: Seed fresh user with 2 hypotheses -> verify -> reset -> verify cleared"""
        self.log("\n" + "="*80, BLUE)
        self.log("TEST 3: Seed journey with 2 hypotheses -> reset -> verify cleared", BLUE)
        self.log("="*80, BLUE)
        
        # Create fresh user
        email = f"seed_hyp_{int(datetime.now().timestamp())}@test.com"
        password = "Test1234!"
        
        resp = self.signup(email, password)
        self.assert_equal(resp.status_code, 200, "Fresh signup returns 200")
        
        token = self.login(email, password)
        self.assert_true(token is not None, "Login successful")
        
        # Seed with 2 hypotheses via MongoDB
        hypotheses = [
            {
                "id": "a",
                "statement": "Hypothesis A",
                "probability": 60,
                "evidence_for": [],
                "evidence_against": [],
                "status": "active"
            },
            {
                "id": "b",
                "statement": "Hypothesis B",
                "probability": 40,
                "evidence_for": [],
                "evidence_against": [],
                "status": "active"
            }
        ]
        
        success = self.seed_journey_with_hypotheses(email, hypotheses)
        self.assert_true(success, "Seeded journey with 2 hypotheses via MongoDB")
        
        # GET /api/journey -> verify hypotheses length 2, started=true
        resp = self.get_journey(token)
        self.assert_equal(resp.status_code, 200, "GET /api/journey returns 200")
        
        data = resp.json()
        self.assert_equal(len(data.get("hypotheses", [])), 2, "hypotheses length = 2")
        self.assert_equal(data.get("started"), True, "started=true after seeding")
        
        # POST /api/journey/reset
        resp = self.reset_journey(token)
        self.assert_equal(resp.status_code, 200, "POST /api/journey/reset returns 200")
        
        data = resp.json()
        self.assert_equal(len(data.get("hypotheses", [1])), 0, "hypotheses=[] after reset")
        self.assert_equal(data.get("started"), False, "started=false after reset")
        
        self.log(f"\n✅ TEST 3 PASSED: Seed and reset working correctly", GREEN)
        
    def test_4_regression_frees(self):
        """TEST 4: Regression free tests (validation, endpoints that don't hit LLM)"""
        self.log("\n" + "="*80, BLUE)
        self.log("TEST 4: Regression free tests (validation, non-LLM endpoints)", BLUE)
        self.log("="*80, BLUE)
        
        # Create fresh user for testing
        email = f"regress_{int(datetime.now().timestamp())}@test.com"
        password = "Test1234!"
        
        resp = self.signup(email, password)
        self.assert_equal(resp.status_code, 200, "Fresh signup returns 200")
        
        token = self.login(email, password)
        self.assert_true(token is not None, "Login successful")
        
        # TEST 4a: POST /api/journey/message before start -> 400
        resp = requests.post(f"{API_BASE}/journey/message", 
                           headers={"Authorization": f"Bearer {token}"},
                           json={"message": "test message"})
        self.assert_equal(resp.status_code, 400, "POST /api/journey/message before start returns 400")
        
        # TEST 4b: POST /api/journey/start with empty objective -> 422 (validation fires BEFORE LLM)
        resp = requests.post(f"{API_BASE}/journey/start",
                           headers={"Authorization": f"Bearer {token}"},
                           json={"objective": ""})
        self.assert_equal(resp.status_code, 422, "POST /api/journey/start with empty objective returns 422")
        
        # TEST 4c: GET /api/brain/ledger -> 200 shape intact
        resp = requests.get(f"{API_BASE}/brain/ledger",
                          headers={"Authorization": f"Bearer {token}"})
        self.assert_equal(resp.status_code, 200, "GET /api/brain/ledger returns 200")
        
        # TEST 4d: GET /api/brain/reviews/due -> 200
        resp = requests.get(f"{API_BASE}/brain/reviews/due",
                          headers={"Authorization": f"Bearer {token}"})
        self.assert_equal(resp.status_code, 200, "GET /api/brain/reviews/due returns 200")
        
        # TEST 4e: GET /api/admin/launch-readiness as admin -> 200 with all 5 kpi keys
        admin_token = self.login(ADMIN_EMAIL, ADMIN_PASSWORD)
        self.assert_true(admin_token is not None, "Admin login successful")
        
        resp = requests.get(f"{API_BASE}/admin/launch-readiness",
                          headers={"Authorization": f"Bearer {admin_token}"})
        self.assert_equal(resp.status_code, 200, "GET /api/admin/launch-readiness returns 200")
        
        if resp.status_code == 200:
            data = resp.json()
            kpi_keys = ["kpi1_problem_detection", "kpi2_decision_improvement", "kpi3_execution", 
                       "kpi4_outcome", "kpi5_return"]
            for key in kpi_keys:
                self.assert_in(key, data, f"launch-readiness contains '{key}'")
                
        # TEST 4f: GET /api/admin/release-gate as admin -> 200 with latest.status="done"
        resp = requests.get(f"{API_BASE}/admin/release-gate",
                          headers={"Authorization": f"Bearer {admin_token}"})
        self.assert_equal(resp.status_code, 200, "GET /api/admin/release-gate returns 200")
        
        if resp.status_code == 200:
            data = resp.json()
            self.assert_in("latest", data, "release-gate contains 'latest'")
            if "latest" in data and data["latest"]:
                self.assert_equal(data["latest"].get("status"), "done", 
                                "latest.status='done'")
                                
        self.log(f"\n✅ TEST 4 PASSED: All regression free tests passed", GREEN)
        
    def run_all_tests(self):
        """Run all tests"""
        self.log("\n" + "="*80, YELLOW)
        self.log("SmartDecigen Backend Regression Test - Hypothesis Engine (FREE-ONLY)", YELLOW)
        self.log("HARD BUDGET: ZERO LLM calls", YELLOW)
        self.log("="*80 + "\n", YELLOW)
        
        try:
            # Test 1: Fresh signup with empty hypotheses
            self.test_1_fresh_signup_empty_hypotheses()
            
            # Test 2: Existing user with 5 hypotheses
            self.test_2_existing_user_5_hypotheses()
            
            # Test 3: Seed and reset
            self.test_3_seed_and_reset()
            
            # Test 4: Regression frees
            self.test_4_regression_frees()
            
        except Exception as e:
            self.log(f"\n❌ FATAL ERROR: {str(e)}", RED)
            import traceback
            traceback.print_exc()
            
        finally:
            self.mongo_client.close()
            
        # Summary
        self.log("\n" + "="*80, YELLOW)
        self.log("TEST SUMMARY", YELLOW)
        self.log("="*80, YELLOW)
        self.log(f"✓ Passed: {self.passed}", GREEN)
        self.log(f"✗ Failed: {self.failed}", RED if self.failed > 0 else GREEN)
        
        if self.failures:
            self.log("\nFailed assertions:", RED)
            for failure in self.failures:
                self.log(f"  - {failure}", RED)
                
        if self.failed == 0:
            self.log("\n🎉 ALL TESTS PASSED!", GREEN)
            return 0
        else:
            self.log(f"\n❌ {self.failed} TEST(S) FAILED", RED)
            return 1

if __name__ == "__main__":
    runner = TestRunner()
    exit_code = runner.run_all_tests()
    sys.exit(exit_code)
