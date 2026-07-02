#!/usr/bin/env python3
"""Backend test for SmartDecigen - Three NEW features (Organ 1, KPI, Release Gate).

HARD LLM BUDGET: EXACTLY 1 LLM call total (one POST /api/brain/ask).
Everything else must be FREE (Mongo seeding + free endpoints).
"""
import os
import sys
import json
import time
import uuid
from datetime import datetime, timezone, timedelta
import requests

# Backend URL from frontend/.env
BACKEND_URL = "https://founder-intel-4.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "ceo@smartdecigen.com"
ADMIN_PASSWORD = "FounderOS@2026"

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def log(msg, color=RESET):
    print(f"{color}{msg}{RESET}")

def log_success(msg):
    log(f"✅ {msg}", GREEN)

def log_error(msg):
    log(f"❌ {msg}", RED)

def log_info(msg):
    log(f"ℹ️  {msg}", BLUE)

def log_warning(msg):
    log(f"⚠️  {msg}", YELLOW)

class TestRunner:
    def __init__(self):
        self.admin_token = None
        self.fresh_user_token = None
        self.fresh_user_id = None
        self.fresh_user_email = None
        self.llm_calls_used = 0
        self.failures = []
        self.successes = []
        
    def signup_fresh_user(self, email_prefix="test"):
        """Create a fresh signup user (50 credits)."""
        email = f"{email_prefix}_{int(time.time())}@smartdecigen.com"
        password = "Test@2026"
        
        resp = requests.post(f"{BACKEND_URL}/auth/signup", json={
            "email": email,
            "password": password,
            "name": "Test User"
        })
        
        if resp.status_code != 200:
            raise Exception(f"Signup failed: {resp.status_code} {resp.text}")
        
        data = resp.json()
        return data["token"], data["user"]["id"], email
    
    def login_admin(self):
        """Login as admin."""
        resp = requests.post(f"{BACKEND_URL}/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        })
        
        if resp.status_code != 200:
            raise Exception(f"Admin login failed: {resp.status_code} {resp.text}")
        
        data = resp.json()
        self.admin_token = data["token"]
        log_success(f"Admin logged in: {ADMIN_EMAIL}")
        return self.admin_token
    
    def headers(self, token):
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # ================================================================
    # FEATURE 1: Organ 1 Decision Record + outcome loop
    # ================================================================
    
    def test_feature_1_test_a(self):
        """TEST A (THE 1 LLM CALL - new response contract): Fresh signup -> POST /api/brain/ask."""
        log_info("\n" + "="*80)
        log_info("FEATURE 1 - TEST A: Decision Record + predicted_outcome (1 LLM CALL)")
        log_info("="*80)
        
        # Create fresh signup user (50 credits)
        token, user_id, email = self.signup_fresh_user("organ1_test_a")
        self.fresh_user_token = token
        self.fresh_user_id = user_id
        self.fresh_user_email = email
        log_success(f"Fresh user created: {email} (user_id: {user_id})")
        
        # Check initial credits
        resp = requests.get(f"{BACKEND_URL}/auth/me", headers=self.headers(token))
        initial_credits = resp.json()["credits"]
        log_info(f"Initial credits: {initial_credits}")
        
        # POST /api/brain/ask with D2C tea brand question
        question = "I run a small D2C tea brand doing 3 lakh a month. A distributor offers to put me in 40 retail stores if I give 35 percent margin plus 90 day credit. Should I take it?"
        
        log_info(f"Calling POST /api/brain/ask (LLM CALL #1)...")
        resp = requests.post(f"{BACKEND_URL}/brain/ask", 
                            headers=self.headers(token),
                            json={"question": question})
        
        if resp.status_code != 200:
            self.failures.append(f"TEST A: POST /api/brain/ask failed: {resp.status_code} {resp.text}")
            log_error(f"POST /api/brain/ask failed: {resp.status_code}")
            return False
        
        self.llm_calls_used += 1
        data = resp.json()
        log_success(f"POST /api/brain/ask returned 200")
        
        # CRITICAL ASSERTIONS
        errors = []
        
        # Check predicted_outcome
        predicted_outcome = data.get("predicted_outcome")
        if predicted_outcome is None:
            # null is acceptable ONLY if mode=answer with no recommendation
            if data.get("mode") == "answer" and not data.get("recommendation"):
                log_info("predicted_outcome is null (acceptable for pure answer mode)")
            else:
                errors.append("predicted_outcome is null but mode is not pure answer")
        else:
            # Validate predicted_outcome structure
            if not isinstance(predicted_outcome, dict):
                errors.append(f"predicted_outcome is not a dict: {type(predicted_outcome)}")
            else:
                claim = predicted_outcome.get("claim")
                confidence = predicted_outcome.get("confidence")
                review_after_days = predicted_outcome.get("review_after_days")
                
                if not (isinstance(claim, str) and claim.strip()):
                    errors.append(f"predicted_outcome.claim is not a non-empty string: {claim}")
                else:
                    log_success(f"predicted_outcome.claim: '{claim[:100]}...'")
                
                if not isinstance(confidence, int) or not (0 <= confidence <= 100):
                    errors.append(f"predicted_outcome.confidence is not int 0-100: {confidence}")
                else:
                    log_success(f"predicted_outcome.confidence: {confidence}")
                
                if not isinstance(review_after_days, int) or not (1 <= review_after_days <= 90):
                    errors.append(f"predicted_outcome.review_after_days is not int 1-90: {review_after_days}")
                else:
                    log_success(f"predicted_outcome.review_after_days: {review_after_days}")
        
        # Check dont_follow_if
        dont_follow_if = data.get("dont_follow_if")
        if dont_follow_if is not None:
            if not isinstance(dont_follow_if, str) or not dont_follow_if.strip():
                errors.append(f"dont_follow_if is not a non-empty string: {dont_follow_if}")
            else:
                log_success(f"dont_follow_if: '{dont_follow_if[:100]}...'")
        else:
            log_info("dont_follow_if is null (acceptable)")
        
        # Check existing contract intact
        decision_id = data.get("decision_id")
        session_id = data.get("session_id")
        mode = data.get("mode")
        key_takeaway = data.get("key_takeaway")
        next_action = data.get("next_action")
        hook = data.get("hook")
        cost = data.get("cost")
        
        if not decision_id:
            errors.append("decision_id is missing")
        else:
            log_success(f"decision_id: {decision_id}")
        
        if not session_id:
            errors.append("session_id is missing")
        else:
            log_success(f"session_id: {session_id}")
        
        if mode not in ("answer", "decide", "plan"):
            errors.append(f"mode is invalid: {mode}")
        else:
            log_success(f"mode: {mode}")
        
        if not (isinstance(key_takeaway, str) and key_takeaway.strip()):
            errors.append("key_takeaway is empty")
        else:
            log_success(f"key_takeaway: '{key_takeaway[:100]}...'")
        
        if not (isinstance(next_action, str) and next_action.strip()):
            errors.append("next_action is empty")
        else:
            log_success(f"next_action: '{next_action[:100]}...'")
        
        if not (isinstance(hook, str) and hook.strip()):
            errors.append("hook is empty")
        else:
            log_success(f"hook: '{hook[:100]}...'")
        
        if not isinstance(cost, int) or cost < 1:
            errors.append(f"cost is not >= 1: {cost}")
        else:
            log_success(f"cost: {cost} credits")
        
        # Check reasoning object
        reasoning = data.get("reasoning")
        if not isinstance(reasoning, dict):
            errors.append("reasoning is not a dict")
        else:
            uncertainty = reasoning.get("uncertainty")
            if not isinstance(uncertainty, dict):
                errors.append("reasoning.uncertainty is not a dict")
            else:
                # Should have 9 keys (NO hidden_desire in public view)
                expected_keys = ["goal", "reality", "constraints", "risks", "resources", 
                               "knowledge_gap", "assumptions", "decision_impact", "missing_info"]
                actual_keys = list(uncertainty.keys())
                if len(actual_keys) != 9:
                    errors.append(f"reasoning.uncertainty has {len(actual_keys)} keys, expected 9: {actual_keys}")
                else:
                    log_success(f"reasoning.uncertainty has 9 keys (NO hidden_desire)")
                
                # Check NO hidden_desire key anywhere in reasoning
                if "hidden_desire" in uncertainty:
                    errors.append("reasoning.uncertainty contains hidden_desire (should be stripped)")
                else:
                    log_success("reasoning.uncertainty does NOT contain hidden_desire ✓")
        
        # Check NO strategic_alignment in response
        if "strategic_alignment" in data:
            errors.append("strategic_alignment is present in response (should be stripped)")
        else:
            log_success("strategic_alignment is NOT in response ✓")
        
        # Mongo check: decision doc has predicted_outcome, dont_follow_if, review_at, reviewed_at=null, impact_inr=null
        log_info("Checking MongoDB decision document...")
        from pymongo import MongoClient
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        client = MongoClient(mongo_url)
        db = client.smartdecigen_db
        
        decision_doc = db.decisions.find_one({"id": decision_id})
        if not decision_doc:
            errors.append(f"Decision doc not found in MongoDB: {decision_id}")
        else:
            # Check predicted_outcome in doc
            doc_predicted = decision_doc.get("predicted_outcome")
            if doc_predicted != predicted_outcome:
                errors.append(f"MongoDB predicted_outcome mismatch: {doc_predicted} != {predicted_outcome}")
            else:
                log_success("MongoDB: predicted_outcome matches response")
            
            # Check dont_follow_if in doc
            doc_dont_follow = decision_doc.get("dont_follow_if")
            if doc_dont_follow != dont_follow_if:
                errors.append(f"MongoDB dont_follow_if mismatch: {doc_dont_follow} != {dont_follow_if}")
            else:
                log_success("MongoDB: dont_follow_if matches response")
            
            # Check review_at (should be created_at + review_after_days)
            review_at = decision_doc.get("review_at")
            if review_at is None:
                if predicted_outcome is not None:
                    errors.append("MongoDB: review_at is null but predicted_outcome exists")
            else:
                log_success(f"MongoDB: review_at is set: {review_at}")
            
            # Check reviewed_at is null
            reviewed_at = decision_doc.get("reviewed_at")
            if reviewed_at is not None:
                errors.append(f"MongoDB: reviewed_at should be null: {reviewed_at}")
            else:
                log_success("MongoDB: reviewed_at is null ✓")
            
            # Check impact_inr is null
            impact_inr = decision_doc.get("impact_inr")
            if impact_inr is not None:
                errors.append(f"MongoDB: impact_inr should be null: {impact_inr}")
            else:
                log_success("MongoDB: impact_inr is null ✓")
        
        client.close()
        
        if errors:
            for err in errors:
                log_error(err)
            self.failures.append(f"TEST A: {len(errors)} assertion failures")
            return False
        else:
            log_success("TEST A: ALL ASSERTIONS PASSED ✅")
            self.successes.append("TEST A: Decision Record + predicted_outcome")
            return True
    
    def test_feature_1_test_b(self):
        """TEST B (FREE - review loop with seeded data)."""
        log_info("\n" + "="*80)
        log_info("FEATURE 1 - TEST B: Review loop with seeded data (FREE)")
        log_info("="*80)
        
        # Use the same fresh user from TEST A
        token = self.fresh_user_token
        user_id = self.fresh_user_id
        
        # Insert seeded decision directly into MongoDB
        from pymongo import MongoClient
        mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
        client = MongoClient(mongo_url)
        db = client.smartdecigen_db
        
        now = datetime.now(timezone.utc)
        created_at = now - timedelta(days=15)
        review_at = now - timedelta(days=1)  # Due yesterday
        
        seeded_doc = {
            "id": "rev-test-1",
            "user_id": user_id,
            "org_id": None,
            "user_name": "T",
            "session_id": "s1",
            "question": "seeded review test",
            "mode": "decide",
            "answer": "x",
            "next_action": "do y",
            "status": "open",
            "committed_action": "do y",
            "created_at": created_at,
            "predicted_outcome": {
                "claim": "sales will rise 20 pct",
                "confidence": 70,
                "review_after_days": 14
            },
            "dont_follow_if": "cash below 1L",
            "review_at": review_at,
            "reviewed_at": None,
            "impact_inr": None,
            "outcome": {"status": "unknown", "score": None, "source": None, "at": None}
        }
        
        db.decisions.insert_one(seeded_doc)
        log_success("Seeded decision 'rev-test-1' inserted into MongoDB")
        
        errors = []
        
        # 1. GET /api/brain/reviews/due
        log_info("1. GET /api/brain/reviews/due")
        resp = requests.get(f"{BACKEND_URL}/brain/reviews/due", headers=self.headers(token))
        if resp.status_code != 200:
            errors.append(f"GET /api/brain/reviews/due failed: {resp.status_code}")
        else:
            data = resp.json()
            count = data.get("count", 0)
            due = data.get("due", [])
            
            if count < 1:
                errors.append(f"reviews/due count is {count}, expected >= 1")
            else:
                log_success(f"reviews/due count: {count}")
            
            # Check if rev-test-1 is in the list
            found = any(d.get("id") == "rev-test-1" for d in due)
            if not found:
                errors.append("rev-test-1 not found in reviews/due")
            else:
                log_success("rev-test-1 found in reviews/due ✓")
                # Check structure
                rev = next(d for d in due if d.get("id") == "rev-test-1")
                if not rev.get("predicted_outcome"):
                    errors.append("rev-test-1 missing predicted_outcome")
                if not rev.get("review_at"):
                    errors.append("rev-test-1 missing review_at")
                if not rev.get("question"):
                    errors.append("rev-test-1 missing question")
                log_success(f"rev-test-1 structure: predicted_outcome={rev.get('predicted_outcome')}, review_at={rev.get('review_at')}")
        
        # 2. POST /api/brain/decisions/rev-test-1/review
        log_info("2. POST /api/brain/decisions/rev-test-1/review")
        resp = requests.post(f"{BACKEND_URL}/brain/decisions/rev-test-1/review",
                            headers=self.headers(token),
                            json={
                                "outcome": "worked",
                                "actual": "Sales rose 24 percent",
                                "impact_inr": 50000
                            })
        if resp.status_code != 200:
            errors.append(f"POST review failed: {resp.status_code} {resp.text}")
        else:
            data = resp.json()
            outcome = data.get("outcome", {})
            impact_inr = data.get("impact_inr")
            calibration = data.get("calibration", {})
            
            if outcome.get("status") != "success":
                errors.append(f"outcome.status is {outcome.get('status')}, expected 'success'")
            else:
                log_success(f"outcome.status: success ✓")
            
            if outcome.get("source") != "review":
                errors.append(f"outcome.source is {outcome.get('source')}, expected 'review'")
            else:
                log_success(f"outcome.source: review ✓")
            
            if impact_inr != 50000:
                errors.append(f"impact_inr is {impact_inr}, expected 50000")
            else:
                log_success(f"impact_inr: 50000 ✓")
            
            # Check calibration object
            if not isinstance(calibration, dict):
                errors.append("calibration is not a dict")
            else:
                n = calibration.get("n")
                avg_predicted = calibration.get("avg_predicted_confidence")
                actual_win = calibration.get("actual_win_rate")
                gap = calibration.get("calibration_gap")
                label = calibration.get("label")
                
                if not isinstance(n, int) or n < 1:
                    errors.append(f"calibration.n is {n}, expected >= 1")
                else:
                    log_success(f"calibration.n: {n}")
                
                if not isinstance(avg_predicted, int):
                    errors.append(f"calibration.avg_predicted_confidence is not int: {avg_predicted}")
                else:
                    log_success(f"calibration.avg_predicted_confidence: {avg_predicted}")
                
                if not isinstance(actual_win, int):
                    errors.append(f"calibration.actual_win_rate is not int: {actual_win}")
                else:
                    log_success(f"calibration.actual_win_rate: {actual_win}")
                
                if not isinstance(gap, int):
                    errors.append(f"calibration.calibration_gap is not int: {gap}")
                else:
                    log_success(f"calibration.calibration_gap: {gap}")
                
                if not isinstance(label, str):
                    errors.append(f"calibration.label is not string: {label}")
                else:
                    log_success(f"calibration.label: '{label}'")
        
        # 3. GET /api/brain/reviews/due (rev-test-1 should be GONE)
        log_info("3. GET /api/brain/reviews/due (rev-test-1 should be gone)")
        resp = requests.get(f"{BACKEND_URL}/brain/reviews/due", headers=self.headers(token))
        if resp.status_code != 200:
            errors.append(f"GET /api/brain/reviews/due failed: {resp.status_code}")
        else:
            data = resp.json()
            due = data.get("due", [])
            found = any(d.get("id") == "rev-test-1" for d in due)
            if found:
                errors.append("rev-test-1 still in reviews/due (should be gone)")
            else:
                log_success("rev-test-1 is GONE from reviews/due ✓")
        
        # 4. GET /api/brain/ledger
        log_info("4. GET /api/brain/ledger")
        resp = requests.get(f"{BACKEND_URL}/brain/ledger", headers=self.headers(token))
        if resp.status_code != 200:
            errors.append(f"GET /api/brain/ledger failed: {resp.status_code}")
        else:
            data = resp.json()
            totals = data.get("totals", {})
            outcomes = data.get("outcomes", {})
            impact = data.get("impact", {})
            calibration = data.get("calibration", {})
            recent_reviews = data.get("recent_reviews", [])
            
            reviewed = totals.get("reviewed", 0)
            if reviewed < 1:
                errors.append(f"totals.reviewed is {reviewed}, expected >= 1")
            else:
                log_success(f"totals.reviewed: {reviewed}")
            
            success_count = outcomes.get("success", 0)
            if success_count < 1:
                errors.append(f"outcomes.success is {success_count}, expected >= 1")
            else:
                log_success(f"outcomes.success: {success_count}")
            
            total_inr = impact.get("total_inr", 0)
            if total_inr < 50000:
                errors.append(f"impact.total_inr is {total_inr}, expected >= 50000")
            else:
                log_success(f"impact.total_inr: {total_inr}")
            
            cal_n = calibration.get("n", 0)
            if cal_n < 1:
                errors.append(f"calibration.n is {cal_n}, expected >= 1")
            else:
                log_success(f"calibration.n: {cal_n}")
            
            # Check recent_reviews contains rev-test-1
            found_review = any(r.get("id") == "rev-test-1" for r in recent_reviews)
            if not found_review:
                errors.append("rev-test-1 not found in recent_reviews")
            else:
                log_success("rev-test-1 found in recent_reviews ✓")
                rev = next(r for r in recent_reviews if r.get("id") == "rev-test-1")
                review_note = rev.get("review_note")
                if review_note != "Sales rose 24 percent":
                    errors.append(f"review_note mismatch: '{review_note}'")
                else:
                    log_success(f"review_note: '{review_note}' ✓")
        
        # 5. Validation tests
        log_info("5. Validation tests")
        
        # POST review with outcome "bogus" -> 422
        resp = requests.post(f"{BACKEND_URL}/brain/decisions/rev-test-1/review",
                            headers=self.headers(token),
                            json={"outcome": "bogus", "actual": "test"})
        if resp.status_code != 422:
            errors.append(f"POST review with bogus outcome returned {resp.status_code}, expected 422")
        else:
            log_success("POST review with bogus outcome -> 422 ✓")
        
        # Review on unknown id -> 404
        resp = requests.post(f"{BACKEND_URL}/brain/decisions/unknown-id-999/review",
                            headers=self.headers(token),
                            json={"outcome": "worked", "actual": "test"})
        if resp.status_code != 404:
            errors.append(f"POST review on unknown id returned {resp.status_code}, expected 404")
        else:
            log_success("POST review on unknown id -> 404 ✓")
        
        # Review on ANOTHER user's decision -> 404
        # Create second fresh user
        token2, user_id2, email2 = self.signup_fresh_user("organ1_test_b_user2")
        log_info(f"Created second user: {email2}")
        
        resp = requests.post(f"{BACKEND_URL}/brain/decisions/rev-test-1/review",
                            headers=self.headers(token2),
                            json={"outcome": "worked", "actual": "test"})
        if resp.status_code != 404:
            errors.append(f"POST review on another user's decision returned {resp.status_code}, expected 404")
        else:
            log_success("POST review on another user's decision -> 404 ✓")
        
        # 6. POST /api/brain/decisions/rev-test-1/status with negative impact_inr
        log_info("6. POST /api/brain/decisions/rev-test-1/status with negative impact_inr")
        resp = requests.post(f"{BACKEND_URL}/brain/decisions/rev-test-1/status",
                            headers=self.headers(token),
                            json={"status": "done", "outcome": "partly", "impact_inr": -2000})
        if resp.status_code != 200:
            errors.append(f"POST status with negative impact_inr failed: {resp.status_code}")
        else:
            data = resp.json()
            impact_inr = data.get("impact_inr")
            if impact_inr != -2000:
                errors.append(f"impact_inr is {impact_inr}, expected -2000")
            else:
                log_success("impact_inr=-2000 accepted (negative allowed) ✓")
        
        # Cleanup
        db.decisions.delete_one({"id": "rev-test-1"})
        log_info("Cleaned up seeded decision")
        client.close()
        
        if errors:
            for err in errors:
                log_error(err)
            self.failures.append(f"TEST B: {len(errors)} assertion failures")
            return False
        else:
            log_success("TEST B: ALL ASSERTIONS PASSED ✅")
            self.successes.append("TEST B: Review loop with seeded data")
            return True
    
    # ================================================================
    # FEATURE 2: Launch KPI signals + admin aggregator
    # ================================================================
    
    def test_feature_2(self):
        """TEST FEATURE 2: KPI signals + admin aggregator (all FREE)."""
        log_info("\n" + "="*80)
        log_info("FEATURE 2: Launch KPI signals + admin aggregator (FREE)")
        log_info("="*80)
        
        # Create fresh user for KPI tests
        token, user_id, email = self.signup_fresh_user("kpi_test")
        log_success(f"Fresh user created: {email}")
        
        errors = []
        
        # 1. No token POST /api/kpi/signal -> 401/403
        log_info("1. No token POST /api/kpi/signal -> 401/403")
        resp = requests.post(f"{BACKEND_URL}/kpi/signal", json={"kind": "problem_detection", "value": True})
        if resp.status_code not in (401, 403):
            errors.append(f"No token POST /api/kpi/signal returned {resp.status_code}, expected 401/403")
        else:
            log_success(f"No token POST /api/kpi/signal -> {resp.status_code} ✓")
        
        # 2. POST /api/kpi/signal as fresh user
        log_info("2. POST /api/kpi/signal with problem_detection")
        resp = requests.post(f"{BACKEND_URL}/kpi/signal",
                            headers=self.headers(token),
                            json={"kind": "problem_detection", "value": True, "decision_id": "rev-test-1"})
        if resp.status_code != 200:
            errors.append(f"POST /api/kpi/signal failed: {resp.status_code} {resp.text}")
        else:
            data = resp.json()
            if not data.get("ok"):
                errors.append("POST /api/kpi/signal did not return ok:true")
            else:
                log_success("POST /api/kpi/signal -> 200 {ok:true} ✓")
        
        # 3. IDEMPOTENCY: same call again with value:false
        log_info("3. IDEMPOTENCY: same call with value:false")
        resp = requests.post(f"{BACKEND_URL}/kpi/signal",
                            headers=self.headers(token),
                            json={"kind": "problem_detection", "value": False, "decision_id": "rev-test-1"})
        if resp.status_code != 200:
            errors.append(f"POST /api/kpi/signal (idempotent) failed: {resp.status_code}")
        else:
            log_success("POST /api/kpi/signal (idempotent) -> 200 ✓")
            
            # Check MongoDB: should be EXACTLY 1 row with value=false
            from pymongo import MongoClient
            mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
            client = MongoClient(mongo_url)
            db = client.smartdecigen_db
            
            count = db.kpi_events.count_documents({
                "user_id": user_id,
                "kind": "problem_detection",
                "dedupe": "rev-test-1"
            })
            
            if count != 1:
                errors.append(f"kpi_events count is {count}, expected EXACTLY 1 (idempotent)")
            else:
                log_success(f"kpi_events count: 1 (idempotent) ✓")
                
                # Check value is false (replaced)
                doc = db.kpi_events.find_one({
                    "user_id": user_id,
                    "kind": "problem_detection",
                    "dedupe": "rev-test-1"
                })
                if doc.get("value") != False:
                    errors.append(f"kpi_events value is {doc.get('value')}, expected False (replaced)")
                else:
                    log_success("kpi_events value: False (replaced, not appended) ✓")
            
            client.close()
        
        # 4. POST with decision_improvement (no decision_id, day-bucket dedupe)
        log_info("4. POST /api/kpi/signal with decision_improvement (day-bucket dedupe)")
        resp = requests.post(f"{BACKEND_URL}/kpi/signal",
                            headers=self.headers(token),
                            json={"kind": "decision_improvement", "value": True})
        if resp.status_code != 200:
            errors.append(f"POST /api/kpi/signal (decision_improvement) failed: {resp.status_code}")
        else:
            log_success("POST /api/kpi/signal (decision_improvement) -> 200 ✓")
        
        # 5. Invalid kind -> 422
        log_info("5. Invalid kind -> 422")
        resp = requests.post(f"{BACKEND_URL}/kpi/signal",
                            headers=self.headers(token),
                            json={"kind": "invalid_kind", "value": True})
        if resp.status_code != 422:
            errors.append(f"POST /api/kpi/signal with invalid kind returned {resp.status_code}, expected 422")
        else:
            log_success("POST /api/kpi/signal with invalid kind -> 422 ✓")
        
        # 6. GET /api/admin/launch-readiness as NON-admin -> 403
        log_info("6. GET /api/admin/launch-readiness as non-admin -> 403")
        resp = requests.get(f"{BACKEND_URL}/admin/launch-readiness", headers=self.headers(token))
        if resp.status_code != 403:
            errors.append(f"GET /api/admin/launch-readiness as non-admin returned {resp.status_code}, expected 403")
        else:
            log_success("GET /api/admin/launch-readiness as non-admin -> 403 ✓")
        
        # 7. No token -> 401/403
        log_info("7. GET /api/admin/launch-readiness no token -> 401/403")
        resp = requests.get(f"{BACKEND_URL}/admin/launch-readiness")
        if resp.status_code not in (401, 403):
            errors.append(f"GET /api/admin/launch-readiness no token returned {resp.status_code}, expected 401/403")
        else:
            log_success(f"GET /api/admin/launch-readiness no token -> {resp.status_code} ✓")
        
        # 8. GET /api/admin/launch-readiness as admin
        log_info("8. GET /api/admin/launch-readiness as admin")
        admin_token = self.login_admin()
        resp = requests.get(f"{BACKEND_URL}/admin/launch-readiness", headers=self.headers(admin_token))
        if resp.status_code != 200:
            errors.append(f"GET /api/admin/launch-readiness as admin failed: {resp.status_code} {resp.text}")
        else:
            data = resp.json()
            log_success("GET /api/admin/launch-readiness as admin -> 200 ✓")
            
            # Check all required keys
            required_keys = ["kpi1_problem_detection", "kpi2_decision_improvement", 
                           "kpi3_execution", "kpi4_outcome", "kpi5_return", 
                           "release_gate", "generated_at"]
            
            for key in required_keys:
                if key not in data:
                    errors.append(f"Missing key in launch-readiness: {key}")
            
            if not errors:
                log_success("All required keys present in launch-readiness ✓")
                
                # Check kpi1 structure
                kpi1 = data.get("kpi1_problem_detection", {})
                if not all(k in kpi1 for k in ["yes", "no", "n", "pct"]):
                    errors.append("kpi1_problem_detection missing keys")
                else:
                    log_success(f"kpi1_problem_detection: yes={kpi1['yes']}, no={kpi1['no']}, n={kpi1['n']}, pct={kpi1['pct']}")
                    if kpi1["n"] < 1:
                        errors.append(f"kpi1.n is {kpi1['n']}, expected >= 1")
                
                # Check kpi2 structure
                kpi2 = data.get("kpi2_decision_improvement", {})
                if not all(k in kpi2 for k in ["yes", "no", "n", "pct"]):
                    errors.append("kpi2_decision_improvement missing keys")
                else:
                    log_success(f"kpi2_decision_improvement: yes={kpi2['yes']}, no={kpi2['no']}, n={kpi2['n']}, pct={kpi2['pct']}")
                
                # Check kpi3 structure
                kpi3 = data.get("kpi3_execution", {})
                required_kpi3 = ["committed", "done", "dropped", "open", "completion_pct", "follow_through_pct"]
                if not all(k in kpi3 for k in required_kpi3):
                    errors.append("kpi3_execution missing keys")
                else:
                    log_success(f"kpi3_execution: committed={kpi3['committed']}, done={kpi3['done']}, completion_pct={kpi3['completion_pct']}, follow_through_pct={kpi3['follow_through_pct']}")
                
                # Check kpi4 structure
                kpi4 = data.get("kpi4_outcome", {})
                required_kpi4 = ["outcomes", "n", "positive_pct", "impact_inr_total", "impact_reports", "calibration"]
                if not all(k in kpi4 for k in required_kpi4):
                    errors.append("kpi4_outcome missing keys")
                else:
                    log_success(f"kpi4_outcome: n={kpi4['n']}, positive_pct={kpi4['positive_pct']}, impact_inr_total={kpi4['impact_inr_total']}")
                    
                    # Check impact_inr_total reflects reviewed impacts (>= 40000 from TEST B: 50000 + (-2000))
                    # Note: This depends on TEST B running first
                    impact_total = kpi4.get("impact_inr_total", 0)
                    log_info(f"kpi4.impact_inr_total: {impact_total} (should reflect reviewed impacts)")
                
                # Check kpi5 structure
                kpi5 = data.get("kpi5_return", {})
                required_kpi5 = ["eligible", "returned", "return_pct", "active_7d"]
                if not all(k in kpi5 for k in required_kpi5):
                    errors.append("kpi5_return missing keys")
                else:
                    log_success(f"kpi5_return: eligible={kpi5['eligible']}, returned={kpi5['returned']}, return_pct={kpi5['return_pct']}, active_7d={kpi5['active_7d']}")
                
                # Check release_gate (object or null)
                release_gate = data.get("release_gate")
                if release_gate is not None and not isinstance(release_gate, dict):
                    errors.append("release_gate is not object or null")
                else:
                    log_success(f"release_gate: {release_gate}")
        
        if errors:
            for err in errors:
                log_error(err)
            self.failures.append(f"FEATURE 2: {len(errors)} assertion failures")
            return False
        else:
            log_success("FEATURE 2: ALL ASSERTIONS PASSED ✅")
            self.successes.append("FEATURE 2: Launch KPI signals + admin aggregator")
            return True
    
    # ================================================================
    # FEATURE 3: Release Gate (READ-ONLY, DO NOT RUN)
    # ================================================================
    
    def test_feature_3(self):
        """TEST FEATURE 3: Release Gate READ-ONLY (all FREE, DO NOT RUN)."""
        log_info("\n" + "="*80)
        log_info("FEATURE 3: Release Gate READ-ONLY (FREE, DO NOT RUN)")
        log_info("="*80)
        
        errors = []
        
        # 1. GET /api/admin/release-gate as admin
        log_info("1. GET /api/admin/release-gate as admin")
        admin_token = self.admin_token or self.login_admin()
        resp = requests.get(f"{BACKEND_URL}/admin/release-gate", headers=self.headers(admin_token))
        if resp.status_code != 200:
            errors.append(f"GET /api/admin/release-gate as admin failed: {resp.status_code} {resp.text}")
        else:
            data = resp.json()
            log_success("GET /api/admin/release-gate as admin -> 200 ✓")
            
            # Check latest run exists
            latest = data.get("latest")
            if not latest:
                log_warning("No previous release-gate run found (expected from smoke test)")
            else:
                log_success("Previous release-gate run found ✓")
                
                # Check latest.status should be "done"
                status = latest.get("status")
                if status != "done":
                    log_warning(f"latest.status is '{status}', expected 'done' (from previous smoke run)")
                else:
                    log_success(f"latest.status: 'done' ✓")
                
                # Check overall.gate_avgs
                overall = latest.get("overall", {})
                gate_avgs = overall.get("gate_avgs", {})
                
                expected_gates = ["truth", "reasoning", "actionability", "impact"]
                for gate in expected_gates:
                    if gate not in gate_avgs:
                        errors.append(f"Missing gate in overall.gate_avgs: {gate}")
                    elif not isinstance(gate_avgs[gate], int):
                        errors.append(f"gate_avgs.{gate} is not int: {gate_avgs[gate]}")
                
                if not errors:
                    log_success(f"overall.gate_avgs: {gate_avgs} ✓")
                
                # Check scenarios[0]
                scenarios = latest.get("scenarios", [])
                if not scenarios:
                    log_warning("No scenarios in latest run")
                else:
                    sc0 = scenarios[0]
                    sc0_name = sc0.get("name")
                    if sc0_name != "cloud-kitchen-discount":
                        log_warning(f"scenarios[0].name is '{sc0_name}', expected 'cloud-kitchen-discount'")
                    else:
                        log_success(f"scenarios[0].name: 'cloud-kitchen-discount' ✓")
                    
                    # Check gates structure
                    gates = sc0.get("gates", {})
                    for gate in expected_gates:
                        if gate not in gates:
                            errors.append(f"Missing gate in scenarios[0].gates: {gate}")
                        else:
                            g = gates[gate]
                            if not all(k in g for k in ["score", "note", "passed"]):
                                errors.append(f"scenarios[0].gates.{gate} missing keys")
                            else:
                                log_success(f"scenarios[0].gates.{gate}: score={g['score']}, passed={g['passed']}")
                    
                    # Check better_decision
                    better_decision = sc0.get("better_decision")
                    if not isinstance(better_decision, bool):
                        errors.append(f"scenarios[0].better_decision is not bool: {better_decision}")
                    else:
                        log_success(f"scenarios[0].better_decision: {better_decision} ✓")
            
            # Check history
            history = data.get("history")
            if not isinstance(history, list):
                errors.append("history is not a list")
            else:
                log_success(f"history is a list with {len(history)} runs ✓")
        
        # 2. GET /api/admin/release-gate as non-admin -> 403
        log_info("2. GET /api/admin/release-gate as non-admin -> 403")
        # Create fresh user
        token, user_id, email = self.signup_fresh_user("release_gate_test")
        resp = requests.get(f"{BACKEND_URL}/admin/release-gate", headers=self.headers(token))
        if resp.status_code != 403:
            errors.append(f"GET /api/admin/release-gate as non-admin returned {resp.status_code}, expected 403")
        else:
            log_success("GET /api/admin/release-gate as non-admin -> 403 ✓")
        
        # 3. POST /api/admin/release-gate/run validation ONLY (DO NOT send valid body)
        log_info("3. POST /api/admin/release-gate/run validation ONLY")
        
        # limit=0 -> 422
        resp = requests.post(f"{BACKEND_URL}/admin/release-gate/run",
                            headers=self.headers(admin_token),
                            json={"limit": 0})
        if resp.status_code != 422:
            errors.append(f"POST /api/admin/release-gate/run with limit=0 returned {resp.status_code}, expected 422")
        else:
            log_success("POST /api/admin/release-gate/run with limit=0 -> 422 ✓")
        
        # limit=9 -> 422
        resp = requests.post(f"{BACKEND_URL}/admin/release-gate/run",
                            headers=self.headers(admin_token),
                            json={"limit": 9})
        if resp.status_code != 422:
            errors.append(f"POST /api/admin/release-gate/run with limit=9 returned {resp.status_code}, expected 422")
        else:
            log_success("POST /api/admin/release-gate/run with limit=9 -> 422 ✓")
        
        log_warning("DO NOT send valid body to POST /api/admin/release-gate/run (each scenario costs 2 LLM calls)")
        
        if errors:
            for err in errors:
                log_error(err)
            self.failures.append(f"FEATURE 3: {len(errors)} assertion failures")
            return False
        else:
            log_success("FEATURE 3: ALL ASSERTIONS PASSED ✅")
            self.successes.append("FEATURE 3: Release Gate READ-ONLY")
            return True
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        log_info("\n" + "="*80)
        log_info("SMARTDECIGEN BACKEND TEST - THREE NEW FEATURES")
        log_info("="*80)
        log_info(f"Backend URL: {BACKEND_URL}")
        log_info(f"LLM Budget: EXACTLY 1 LLM call (one POST /api/brain/ask)")
        log_info("="*80 + "\n")
        
        # Run tests
        self.test_feature_1_test_a()
        self.test_feature_1_test_b()
        self.test_feature_2()
        self.test_feature_3()
        
        # Summary
        log_info("\n" + "="*80)
        log_info("TEST SUMMARY")
        log_info("="*80)
        log_info(f"LLM calls used: {self.llm_calls_used}/1")
        log_info(f"Successes: {len(self.successes)}")
        log_info(f"Failures: {len(self.failures)}")
        
        if self.successes:
            log_success("\nPASSED:")
            for s in self.successes:
                log_success(f"  ✅ {s}")
        
        if self.failures:
            log_error("\nFAILED:")
            for f in self.failures:
                log_error(f"  ❌ {f}")
        
        log_info("="*80 + "\n")
        
        if self.failures:
            sys.exit(1)
        else:
            log_success("ALL TESTS PASSED ✅")
            sys.exit(0)

if __name__ == "__main__":
    runner = TestRunner()
    runner.run_all_tests()
