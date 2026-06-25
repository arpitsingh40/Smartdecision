#!/usr/bin/env python3
"""
Complete End-to-End Journey Test: Founder → Team Member → Goal → Achievement Progress
This is FULLY FREE: NO LLM, NO credits. LLM BUDGET = 0.
"""

import requests
import json
import random
import string
from typing import Dict, Any, Optional

# Backend URL
BASE_URL = "https://founder-goals.preview.emergentagent.com/api"

# Test credentials
FOUNDER_EMAIL = "ceo@smartdecigen.com"
FOUNDER_PASSWORD = "FounderOS@2026"

# Test results tracking
test_results = []
phase_results = {
    "A": [],
    "B": [],
    "C": [],
    "D": []
}

def log_test(phase: str, step: str, passed: bool, message: str, data: Any = None):
    """Log test result"""
    result = {
        "phase": phase,
        "step": step,
        "passed": passed,
        "message": message,
        "data": data
    }
    test_results.append(result)
    phase_results[phase].append(result)
    
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status} - {phase}{step}: {message}")
    if data and not passed:
        print(f"  Data: {json.dumps(data, indent=2)}")

def generate_random_email():
    """Generate random email for new member"""
    rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"member_{rand}@acmesolar.com"

class TestSession:
    def __init__(self):
        self.founder_token = None
        self.member_token = None
        self.member_email = None
        self.invite_code = None
        self.org_id = None
        self.initial_strategy_version = None
        
    def login_founder(self) -> bool:
        """A1. Login as founder"""
        try:
            response = requests.post(
                f"{BASE_URL}/auth/login",
                json={"email": FOUNDER_EMAIL, "password": FOUNDER_PASSWORD}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.founder_token = data.get("token")
                user = data.get("user", {})
                self.org_id = user.get("org_id")
                org_role = user.get("org_role")
                
                if self.founder_token and org_role == "owner":
                    log_test("A", "1", True, 
                            f"Login as founder -> 200, token has org_id={self.org_id} + org_role=owner",
                            {"org_id": self.org_id, "org_role": org_role})
                    return True
                else:
                    log_test("A", "1", False, 
                            f"Login succeeded but missing token or org_role != owner",
                            data)
                    return False
            else:
                log_test("A", "1", False, 
                        f"Login failed with status {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("A", "1", False, f"Exception during login: {str(e)}")
            return False
    
    def get_org_as_founder(self) -> bool:
        """A2. GET /api/org (founder)"""
        try:
            response = requests.get(
                f"{BASE_URL}/org",
                headers={"Authorization": f"Bearer {self.founder_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                is_owner = data.get("is_owner")
                strategy_set = data.get("strategy_set")
                
                if is_owner and strategy_set:
                    log_test("A", "2", True,
                            f"GET /api/org (founder) -> 200 is_owner=true, strategy_set=true",
                            {"name": data.get("name"), "is_owner": is_owner, "strategy_set": strategy_set})
                    return True
                else:
                    log_test("A", "2", False,
                            f"GET /api/org returned but is_owner={is_owner}, strategy_set={strategy_set}",
                            data)
                    return False
            else:
                log_test("A", "2", False,
                        f"GET /api/org failed with status {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("A", "2", False, f"Exception: {str(e)}")
            return False
    
    def set_strategy(self) -> bool:
        """A3. PUT /api/org/strategy as founder"""
        try:
            strategy_data = {
                "north_star": "Reach 100 crore annual revenue and be the top C&I solar EPC in North India",
                "target": "100 Cr ARR",
                "deadline": "Mar 2027",
                "priorities": [
                    "Win C&I rooftop deals",
                    "Push EPC ticket above 50L",
                    "Protect 18% margins"
                ],
                "decision_rules": "Never quote below 18% margin. Prefer C&I over residential.",
                "current_arr": 200000000,
                "target_arr": 1000000000
            }
            
            response = requests.put(
                f"{BASE_URL}/org/strategy",
                headers={"Authorization": f"Bearer {self.founder_token}"},
                json=strategy_data
            )
            
            if response.status_code == 200:
                data = response.json()
                self.initial_strategy_version = data.get("strategy_version")
                
                log_test("A", "3", True,
                        f"PUT /api/org/strategy -> 200. Captured strategy_version={self.initial_strategy_version}",
                        {"strategy_version": self.initial_strategy_version,
                         "current_arr": data.get("current_arr"),
                         "target_arr": data.get("target_arr")})
                return True
            else:
                log_test("A", "3", False,
                        f"PUT /api/org/strategy failed with status {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("A", "3", False, f"Exception: {str(e)}")
            return False
    
    def get_strategy(self) -> bool:
        """A4. GET /api/org/strategy"""
        try:
            response = requests.get(
                f"{BASE_URL}/org/strategy",
                headers={"Authorization": f"Bearer {self.founder_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                current_arr = data.get("current_arr")
                target_arr = data.get("target_arr")
                
                if current_arr == 200000000 and target_arr == 1000000000:
                    log_test("A", "4", True,
                            f"GET /api/org/strategy -> 200 returns same values, current_arr=200000000, target_arr=1000000000",
                            {"current_arr": current_arr, "target_arr": target_arr})
                    return True
                else:
                    log_test("A", "4", False,
                            f"GET /api/org/strategy returned different values: current_arr={current_arr}, target_arr={target_arr}",
                            data)
                    return False
            else:
                log_test("A", "4", False,
                        f"GET /api/org/strategy failed with status {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("A", "4", False, f"Exception: {str(e)}")
            return False
    
    def create_invite(self) -> bool:
        """B1. POST /api/org/invites (founder)"""
        try:
            response = requests.post(
                f"{BASE_URL}/org/invites",
                headers={"Authorization": f"Bearer {self.founder_token}"},
                json={}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.invite_code = data.get("code")
                join_url = data.get("join_url")
                
                if self.invite_code and join_url:
                    log_test("B", "1", True,
                            f"POST /api/org/invites (founder) -> 200 returns code={self.invite_code}, join_url",
                            {"code": self.invite_code, "join_url": join_url})
                    return True
                else:
                    log_test("B", "1", False,
                            f"POST /api/org/invites succeeded but missing code or join_url",
                            data)
                    return False
            else:
                log_test("B", "1", False,
                        f"POST /api/org/invites failed with status {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("B", "1", False, f"Exception: {str(e)}")
            return False
    
    def lookup_invite_public(self) -> bool:
        """B2. GET /api/org/invites/{code} with NO auth (public)"""
        try:
            response = requests.get(f"{BASE_URL}/org/invites/{self.invite_code}")
            
            if response.status_code == 200:
                data = response.json()
                valid = data.get("valid")
                org_name = data.get("org_name")
                role = data.get("role")
                
                if valid and org_name and role == "member":
                    log_test("B", "2", True,
                            f"GET /api/org/invites/{self.invite_code} with NO auth (public) -> 200 valid=true, org_name={org_name}, role=member",
                            data)
                    return True
                else:
                    log_test("B", "2", False,
                            f"Public invite lookup returned unexpected data: valid={valid}, role={role}",
                            data)
                    return False
            else:
                log_test("B", "2", False,
                        f"Public invite lookup failed with status {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("B", "2", False, f"Exception: {str(e)}")
            return False
    
    def signup_member(self) -> bool:
        """B3. Fresh member signup"""
        try:
            self.member_email = generate_random_email()
            
            response = requests.post(
                f"{BASE_URL}/auth/signup",
                json={
                    "email": self.member_email,
                    "password": "Member@2026",
                    "name": "Test Member"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.member_token = data.get("token")
                user = data.get("user", {})
                org_id = user.get("org_id")
                
                if self.member_token and org_id is None:
                    log_test("B", "3", True,
                            f"Fresh member signup (POST /api/auth/signup, {self.member_email}) -> 200, org_id is null initially",
                            {"email": self.member_email, "org_id": org_id})
                    return True
                else:
                    log_test("B", "3", False,
                            f"Signup succeeded but org_id is not null: {org_id}",
                            data)
                    return False
            else:
                log_test("B", "3", False,
                        f"Member signup failed with status {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("B", "3", False, f"Exception: {str(e)}")
            return False
    
    def member_join_org(self) -> bool:
        """B4. POST /api/org/join {code} as the new member"""
        try:
            response = requests.post(
                f"{BASE_URL}/org/join",
                headers={"Authorization": f"Bearer {self.member_token}"},
                json={"code": self.invite_code}
            )
            
            if response.status_code == 200:
                data = response.json()
                role = data.get("role")
                
                if role == "member":
                    log_test("B", "4", True,
                            f"POST /api/org/join (code) as new member -> 200 role=member",
                            data)
                    return True
                else:
                    log_test("B", "4", False,
                            f"Join succeeded but role != member: {role}",
                            data)
                    return False
            else:
                log_test("B", "4", False,
                        f"POST /api/org/join failed with status {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("B", "4", False, f"Exception: {str(e)}")
            return False
    
    def get_org_as_member(self) -> bool:
        """B5. GET /api/org (member)"""
        try:
            response = requests.get(
                f"{BASE_URL}/org",
                headers={"Authorization": f"Bearer {self.member_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                is_owner = data.get("is_owner")
                role = data.get("role")
                name = data.get("name")
                
                if not is_owner and role == "member" and name == "Acme Solar":
                    log_test("B", "5", True,
                            f"GET /api/org (member) -> 200 is_owner=false, role=member, name=Acme Solar",
                            data)
                    return True
                else:
                    log_test("B", "5", False,
                            f"GET /api/org (member) returned unexpected data: is_owner={is_owner}, role={role}, name={name}",
                            data)
                    return False
            else:
                log_test("B", "5", False,
                        f"GET /api/org (member) failed with status {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("B", "5", False, f"Exception: {str(e)}")
            return False
    
    def get_members_roster(self) -> bool:
        """B6. GET /api/org/members (founder)"""
        try:
            response = requests.get(
                f"{BASE_URL}/org/members",
                headers={"Authorization": f"Bearer {self.founder_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                members = data.get("members", [])
                
                if len(members) >= 2:
                    # Check for founder and new member
                    has_founder = any(m.get("role") == "owner" for m in members)
                    has_member = any(m.get("email") == self.member_email for m in members)
                    
                    if has_founder and has_member:
                        log_test("B", "6", True,
                                f"GET /api/org/members (founder) -> 200 roster contains founder(owner) + new member (count={len(members)})",
                                {"member_count": len(members)})
                        return True
                    else:
                        log_test("B", "6", False,
                                f"Roster missing founder or new member",
                                {"members": members})
                        return False
                else:
                    log_test("B", "6", False,
                            f"Roster has less than 2 members: {len(members)}",
                            data)
                    return False
            else:
                log_test("B", "6", False,
                        f"GET /api/org/members failed with status {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("B", "6", False, f"Exception: {str(e)}")
            return False
    
    def test_member_strategy_403(self) -> bool:
        """C1. Member GET /api/org/strategy -> 403"""
        try:
            response = requests.get(
                f"{BASE_URL}/org/strategy",
                headers={"Authorization": f"Bearer {self.member_token}"}
            )
            
            if response.status_code == 403:
                log_test("C", "1", True, "Member GET /api/org/strategy -> 403")
                return True
            else:
                log_test("C", "1", False,
                        f"Expected 403, got {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("C", "1", False, f"Exception: {str(e)}")
            return False
    
    def test_member_progress_get_403(self) -> bool:
        """C2. Member GET /api/org/progress -> 403"""
        try:
            response = requests.get(
                f"{BASE_URL}/org/progress",
                headers={"Authorization": f"Bearer {self.member_token}"}
            )
            
            if response.status_code == 403:
                log_test("C", "2", True, "Member GET /api/org/progress -> 403")
                return True
            else:
                log_test("C", "2", False,
                        f"Expected 403, got {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("C", "2", False, f"Exception: {str(e)}")
            return False
    
    def test_member_cockpit_403(self) -> bool:
        """C3. Member GET /api/org/cockpit -> 403"""
        try:
            response = requests.get(
                f"{BASE_URL}/org/cockpit",
                headers={"Authorization": f"Bearer {self.member_token}"}
            )
            
            if response.status_code == 403:
                log_test("C", "3", True, "Member GET /api/org/cockpit -> 403")
                return True
            else:
                log_test("C", "3", False,
                        f"Expected 403, got {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("C", "3", False, f"Exception: {str(e)}")
            return False
    
    def test_member_progress_post_403(self) -> bool:
        """C4. Member POST /api/org/progress {current_arr:999} -> 403"""
        try:
            response = requests.post(
                f"{BASE_URL}/org/progress",
                headers={"Authorization": f"Bearer {self.member_token}"},
                json={"current_arr": 999}
            )
            
            if response.status_code == 403:
                log_test("C", "4", True, "Member POST /api/org/progress -> 403")
                return True
            else:
                log_test("C", "4", False,
                        f"Expected 403, got {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("C", "4", False, f"Exception: {str(e)}")
            return False
    
    def test_no_token_progress_401(self) -> bool:
        """C5. No-token GET /api/org/progress -> 401"""
        try:
            response = requests.get(f"{BASE_URL}/org/progress")
            
            if response.status_code == 401:
                log_test("C", "5", True, "No-token GET /api/org/progress -> 401")
                return True
            else:
                log_test("C", "5", False,
                        f"Expected 401, got {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("C", "5", False, f"Exception: {str(e)}")
            return False
    
    def test_progress_initial(self) -> Dict[str, Any]:
        """D1. GET /api/org/progress -> progress_pct should be 20"""
        try:
            response = requests.get(
                f"{BASE_URL}/org/progress",
                headers={"Authorization": f"Bearer {self.founder_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                goal_progress = data.get("goal_progress", {})
                progress_pct = goal_progress.get("progress_pct")
                status = goal_progress.get("status")
                
                if progress_pct == 20 and status == "Just getting started":
                    log_test("D", "1", True,
                            f"GET /api/org/progress -> progress_pct=20 (200M/1B), status='Just getting started'",
                            {"progress_pct": progress_pct, "status": status})
                    return goal_progress
                else:
                    log_test("D", "1", False,
                            f"Expected progress_pct=20, status='Just getting started', got progress_pct={progress_pct}, status={status}",
                            goal_progress)
                    return goal_progress
            else:
                log_test("D", "1", False,
                        f"GET /api/org/progress failed with status {response.status_code}",
                        response.text)
                return {}
        except Exception as e:
            log_test("D", "1", False, f"Exception: {str(e)}")
            return {}
    
    def test_progress_update(self, current_arr: int, expected_pct: int, expected_status: str, step: str) -> Dict[str, Any]:
        """Update progress and verify"""
        try:
            response = requests.post(
                f"{BASE_URL}/org/progress",
                headers={"Authorization": f"Bearer {self.founder_token}"},
                json={"current_arr": current_arr}
            )
            
            if response.status_code == 200:
                data = response.json()
                goal_progress = data.get("goal_progress", {})
                progress_pct = goal_progress.get("progress_pct")
                status = goal_progress.get("status")
                history = goal_progress.get("history", [])
                
                if progress_pct == expected_pct and status == expected_status:
                    log_test("D", step, True,
                            f"POST /api/org/progress current_arr={current_arr} -> progress_pct={progress_pct}, status='{status}', history length={len(history)}",
                            {"progress_pct": progress_pct, "status": status, "history_length": len(history)})
                    return goal_progress
                else:
                    log_test("D", step, False,
                            f"Expected progress_pct={expected_pct}, status='{expected_status}', got progress_pct={progress_pct}, status={status}",
                            goal_progress)
                    return goal_progress
            else:
                log_test("D", step, False,
                        f"POST /api/org/progress failed with status {response.status_code}",
                        response.text)
                return {}
        except Exception as e:
            log_test("D", step, False, f"Exception: {str(e)}")
            return {}
    
    def test_idempotency(self, current_arr: int, expected_history_length: int) -> bool:
        """D6. Idempotency test"""
        try:
            response = requests.post(
                f"{BASE_URL}/org/progress",
                headers={"Authorization": f"Bearer {self.founder_token}"},
                json={"current_arr": current_arr}
            )
            
            if response.status_code == 200:
                data = response.json()
                goal_progress = data.get("goal_progress", {})
                history = goal_progress.get("history", [])
                
                if len(history) == expected_history_length:
                    log_test("D", "6", True,
                            f"Idempotency: POST /api/org/progress current_arr={current_arr} AGAIN -> history length={len(history)} (unchanged, identical to last value)",
                            {"history_length": len(history)})
                    return True
                else:
                    log_test("D", "6", False,
                            f"Idempotency FAILED: history length changed from {expected_history_length} to {len(history)}",
                            {"history": history})
                    return False
            else:
                log_test("D", "6", False,
                        f"POST /api/org/progress failed with status {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("D", "6", False, f"Exception: {str(e)}")
            return False
    
    def test_strategy_version_unchanged(self) -> bool:
        """D7. CRITICAL: strategy_version MUST still equal initial version"""
        try:
            response = requests.get(
                f"{BASE_URL}/org/strategy",
                headers={"Authorization": f"Bearer {self.founder_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                strategy_version = data.get("strategy_version")
                
                if strategy_version == self.initial_strategy_version:
                    log_test("D", "7", True,
                            f"CRITICAL: GET /api/org/strategy -> strategy_version={strategy_version} (unchanged from initial V{self.initial_strategy_version})",
                            {"strategy_version": strategy_version})
                    return True
                else:
                    log_test("D", "7", False,
                            f"CRITICAL FAILURE: strategy_version changed from {self.initial_strategy_version} to {strategy_version}",
                            data)
                    return False
            else:
                log_test("D", "7", False,
                        f"GET /api/org/strategy failed with status {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("D", "7", False, f"Exception: {str(e)}")
            return False
    
    def test_cockpit_final(self) -> bool:
        """D8. GET /api/org/cockpit (founder)"""
        try:
            response = requests.get(
                f"{BASE_URL}/org/cockpit",
                headers={"Authorization": f"Bearer {self.founder_token}"}
            )
            
            if response.status_code == 200:
                data = response.json()
                goal_progress = data.get("goal_progress", {})
                pacing = data.get("pacing", {})
                totals = data.get("totals", {})
                
                progress_pct = goal_progress.get("progress_pct")
                status = goal_progress.get("status")
                members = totals.get("members", 0)
                
                has_pacing = "gap_pct" in pacing
                
                if progress_pct == 100 and status == "Goal reached" and has_pacing and members >= 2:
                    log_test("D", "8", True,
                            f"GET /api/org/cockpit (founder) -> 200, goal_progress.progress_pct=100, status='Goal reached', pacing key present (backward compat), totals.members={members}",
                            {"progress_pct": progress_pct, "status": status, "members": members, "has_pacing": has_pacing})
                    return True
                else:
                    log_test("D", "8", False,
                            f"Cockpit data incomplete: progress_pct={progress_pct}, status={status}, has_pacing={has_pacing}, members={members}",
                            data)
                    return False
            else:
                log_test("D", "8", False,
                        f"GET /api/org/cockpit failed with status {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("D", "8", False, f"Exception: {str(e)}")
            return False
    
    def test_reset_to_mid_value(self) -> bool:
        """D9. Reset to realistic mid value"""
        try:
            response = requests.post(
                f"{BASE_URL}/org/progress",
                headers={"Authorization": f"Bearer {self.founder_token}"},
                json={"current_arr": 300000000}
            )
            
            if response.status_code == 200:
                data = response.json()
                goal_progress = data.get("goal_progress", {})
                progress_pct = goal_progress.get("progress_pct")
                
                if progress_pct == 30:
                    log_test("D", "9", True,
                            f"Reset to mid value: POST /api/org/progress current_arr=300000000 -> progress_pct=30 (org left in this state)",
                            {"progress_pct": progress_pct})
                    return True
                else:
                    log_test("D", "9", False,
                            f"Reset failed: expected progress_pct=30, got {progress_pct}",
                            goal_progress)
                    return False
            else:
                log_test("D", "9", False,
                        f"POST /api/org/progress failed with status {response.status_code}",
                        response.text)
                return False
        except Exception as e:
            log_test("D", "9", False, f"Exception: {str(e)}")
            return False

def print_summary():
    """Print test summary"""
    print("\n" + "="*80)
    print("COMPLETE END-TO-END JOURNEY TEST SUMMARY")
    print("="*80)
    
    for phase in ["A", "B", "C", "D"]:
        results = phase_results[phase]
        passed = sum(1 for r in results if r["passed"])
        total = len(results)
        
        phase_names = {
            "A": "PHASE A — FOUNDER SETS UP THE GOAL",
            "B": "PHASE B — FOUNDER INVITES, MEMBER JOINS",
            "C": "PHASE C — MEMBER IS PROPERLY WALLED OFF",
            "D": "PHASE D — GOAL -> ACHIEVEMENT PROGRESS"
        }
        
        print(f"\n{phase_names[phase]}")
        print(f"  Result: {passed}/{total} tests passed")
        
        for result in results:
            status = "✅ PASS" if result["passed"] else "❌ FAIL"
            print(f"  {status} - {result['phase']}{result['step']}: {result['message']}")
    
    total_passed = sum(1 for r in test_results if r["passed"])
    total_tests = len(test_results)
    
    print("\n" + "="*80)
    print(f"FINAL VERDICT: {total_passed}/{total_tests} tests passed")
    print(f"LLM CALLS USED: 0 (as required, fully free)")
    print("="*80)
    
    if total_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED - Journey is production-ready!")
    else:
        print(f"\n⚠️  {total_tests - total_passed} test(s) failed - see details above")

def main():
    print("="*80)
    print("COMPLETE END-TO-END JOURNEY TEST")
    print("Founder → Team Member → Goal → Achievement Progress")
    print("FULLY FREE: NO LLM, NO credits. LLM BUDGET = 0")
    print("="*80)
    print()
    
    session = TestSession()
    
    # PHASE A — FOUNDER SETS UP THE GOAL
    print("\n=== PHASE A — FOUNDER SETS UP THE GOAL ===")
    if not session.login_founder():
        print("ABORT: Cannot proceed without founder login")
        print_summary()
        return
    
    session.get_org_as_founder()
    session.set_strategy()
    session.get_strategy()
    
    # PHASE B — FOUNDER INVITES, MEMBER JOINS
    print("\n=== PHASE B — FOUNDER INVITES, MEMBER JOINS ===")
    session.create_invite()
    session.lookup_invite_public()
    session.signup_member()
    session.member_join_org()
    session.get_org_as_member()
    session.get_members_roster()
    
    # PHASE C — MEMBER IS PROPERLY WALLED OFF
    print("\n=== PHASE C — MEMBER IS PROPERLY WALLED OFF FROM FOUNDER-ONLY DATA ===")
    session.test_member_strategy_403()
    session.test_member_progress_get_403()
    session.test_member_cockpit_403()
    session.test_member_progress_post_403()
    session.test_no_token_progress_401()
    
    # PHASE D — GOAL -> ACHIEVEMENT PROGRESS (the climb)
    print("\n=== PHASE D — GOAL -> ACHIEVEMENT PROGRESS (the climb) ===")
    
    # D1
    initial_progress = session.test_progress_initial()
    initial_history_length = len(initial_progress.get("history", []))
    
    # D2
    progress_d2 = session.test_progress_update(300000000, 30, "Building momentum", "2")
    history_d2 = len(progress_d2.get("history", []))
    
    # D3
    progress_d3 = session.test_progress_update(650000000, 65, "Closing in", "3")
    
    # D4
    progress_d4 = session.test_progress_update(950000000, 95, "Almost there", "4")
    
    # D5
    progress_d5 = session.test_progress_update(1000000000, 100, "Goal reached", "5")
    history_d5 = len(progress_d5.get("history", []))
    
    # D6 - Idempotency
    session.test_idempotency(1000000000, history_d5)
    
    # D7 - Strategy version unchanged
    session.test_strategy_version_unchanged()
    
    # D8 - Cockpit final
    session.test_cockpit_final()
    
    # D9 - Reset to mid value
    session.test_reset_to_mid_value()
    
    # Print summary
    print_summary()

if __name__ == "__main__":
    main()
