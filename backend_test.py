#!/usr/bin/env python3
"""
FULL END-TO-END PERSONA EVALUATION — Founder OS
Strict LLM budget: <= 18 LLM-spending calls total
Zoho Payments LIVE: only call /payments/create-order ONCE
"""
import requests
import json
import time
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://be836756-4ed3-49fb-aa0b-56db7cb7d2df.preview.emergentagent.com/api"

# Test credentials
FOUNDER_EMAIL = "ceo@smartdecigen.com"
FOUNDER_PASSWORD = "FounderOS@2026"

# LLM call counter (HARD BUDGET: <= 18)
llm_call_count = 0

# Test results storage
results = []

def log_result(step, status, details=""):
    """Log a test result"""
    global results
    result = {
        "step": step,
        "status": status,
        "details": details,
        "timestamp": datetime.now().isoformat()
    }
    results.append(result)
    status_icon = "✅" if status == "PASS" else "❌"
    print(f"{status_icon} Step {step}: {status} - {details}")

def count_llm_call(endpoint, description=""):
    """Track LLM-spending calls"""
    global llm_call_count
    llm_call_count += 1
    print(f"  💰 LLM CALL #{llm_call_count}: {endpoint} {description}")
    if llm_call_count > 18:
        print(f"  ⚠️  WARNING: EXCEEDED LLM BUDGET (18 calls max)")

def api_call(method, endpoint, headers=None, json_data=None, expect_status=200):
    """Make an API call and return response"""
    url = f"{BASE_URL}{endpoint}"
    try:
        if method == "GET":
            resp = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            resp = requests.post(url, headers=headers, json=json_data, timeout=30)
        elif method == "PUT":
            resp = requests.put(url, headers=headers, json=json_data, timeout=30)
        elif method == "DELETE":
            resp = requests.delete(url, headers=headers, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if resp.status_code != expect_status:
            print(f"  ⚠️  Expected {expect_status}, got {resp.status_code}: {resp.text[:200]}")
        
        return resp
    except Exception as e:
        print(f"  ❌ API call failed: {e}")
        return None

def verify_keys(data, required_keys, context=""):
    """Verify required keys are present in response"""
    missing = [k for k in required_keys if k not in data]
    if missing:
        print(f"  ❌ Missing keys in {context}: {missing}")
        return False
    return True

def verify_no_keys(data, forbidden_keys, context=""):
    """Verify forbidden keys are NOT present"""
    found = [k for k in forbidden_keys if k in data]
    if found:
        print(f"  ❌ Forbidden keys found in {context}: {found}")
        return False
    return True

def verify_no_leakage(text, forbidden_phrases, context=""):
    """Verify text doesn't contain forbidden phrases"""
    if not isinstance(text, str):
        return True
    text_lower = text.lower()
    found = [p for p in forbidden_phrases if p.lower() in text_lower]
    if found:
        print(f"  ❌ LEAKAGE in {context}: found {found}")
        return False
    return True

print("=" * 80)
print("FOUNDER OS — FULL END-TO-END PERSONA EVALUATION")
print("=" * 80)
print(f"Base URL: {BASE_URL}")
print(f"LLM Budget: 18 calls max")
print(f"Started: {datetime.now().isoformat()}")
print("=" * 80)

# =================== PERSONA 1 — BIG-COMPANY FOUNDER ===================
print("\n" + "=" * 80)
print("PERSONA 1 — BIG-COMPANY FOUNDER (headline use case)")
print("=" * 80)

# Login as founder
print("\n--- Logging in as founder ---")
resp = api_call("POST", "/auth/login", json_data={
    "email": FOUNDER_EMAIL,
    "password": FOUNDER_PASSWORD
})
if not resp or resp.status_code != 200:
    log_result("SETUP", "FAIL", "Founder login failed")
    exit(1)

founder_data = resp.json()
founder_token = founder_data["token"]
founder_headers = {"Authorization": f"Bearer {founder_token}"}
founder_user = founder_data["user"]
print(f"  ✓ Logged in as {founder_user['email']}, credits: {founder_user['credits']}")

# (A) PERSONAL CLARITY
print("\n" + "-" * 80)
print("(A) PERSONAL CLARITY — founder as a consumer for himself")
print("-" * 80)

# Step 1: POST /api/founder/interview/start (no LLM)
print("\n[Step 1] POST /api/founder/interview/start (no LLM)")
resp = api_call("POST", "/founder/interview/start", headers=founder_headers)
if resp and resp.status_code == 200:
    data = resp.json()
    if (data.get("done") == False and 
        data.get("count") == 0 and 
        data.get("question") and 
        "genuinely fits you" in data.get("question", "")):
        log_result(1, "PASS", f"Fixed opening question returned, done=false, count=0")
    else:
        log_result(1, "FAIL", f"Unexpected response: {data}")
else:
    log_result(1, "FAIL", "Interview start failed")

# Step 2: POST /api/founder/interview/answer x2 (2 LLM)
print("\n[Step 2] POST /api/founder/interview/answer x2 (2 LLM)")

# Answer 1
answer1 = "We run a fast-growing solar EPC company focused on C&I rooftop installations in North India. We're at early growth stage, around 12 crore ARR. The hardest part of my week is closing big commercial deals because I'm introverted and hate confrontational sales conversations."
resp = api_call("POST", "/founder/interview/answer", headers=founder_headers, json_data={"message": answer1})
if resp and resp.status_code == 200:
    data = resp.json()
    count_llm_call("/founder/interview/answer", "answer 1")
    if data.get("done") == False and data.get("count") == 1 and data.get("question"):
        q1 = data.get("question", "")
        if q1 != "To give you advice that genuinely fits you":  # Different from opening
            log_result("2a", "PASS", f"Connected follow-up question received: {q1[:80]}...")
        else:
            log_result("2a", "FAIL", "Question not connected to answer")
    else:
        log_result("2a", "FAIL", f"Unexpected response: {data}")
else:
    log_result("2a", "FAIL", "Answer 1 failed")

# Answer 2
answer2 = "I make decisions slowly, always need data before committing. I avoid confrontation at all costs. My strength is technical design and system optimization, but I'm weak at negotiation and pushing back on unreasonable customer demands."
resp = api_call("POST", "/founder/interview/answer", headers=founder_headers, json_data={"message": answer2})
if resp and resp.status_code == 200:
    data = resp.json()
    count_llm_call("/founder/interview/answer", "answer 2")
    if data.get("count") == 2:
        log_result("2b", "PASS", f"Answer 2 recorded, count=2")
    else:
        log_result("2b", "FAIL", f"Unexpected count: {data.get('count')}")
else:
    log_result("2b", "FAIL", "Answer 2 failed")

# Step 3: POST /api/founder/interview/finish (1 LLM)
print("\n[Step 3] POST /api/founder/interview/finish (1 LLM)")
resp = api_call("POST", "/founder/interview/finish", headers=founder_headers)
if resp and resp.status_code == 200:
    data = resp.json()
    count_llm_call("/founder/interview/finish", "distill profile")
    profile = data.get("profile", {})
    summary = profile.get("summary", "")
    industry_summary = profile.get("industry_summary", "")
    if data.get("done") and len(summary) > 10 and len(industry_summary) > 10:
        log_result(3, "PASS", f"Profile distilled: summary={summary[:60]}..., industry={industry_summary[:60]}...")
    else:
        log_result(3, "FAIL", f"Profile incomplete: {profile}")
else:
    log_result(3, "FAIL", "Interview finish failed")

# Step 4: POST /api/org {name:"Helios Solar"}
print("\n[Step 4] POST /api/org (create organization)")
resp = api_call("POST", "/org", headers=founder_headers, json_data={"name": "Helios Solar"})
if resp and resp.status_code == 200:
    data = resp.json()
    org_id = data.get("id")
    if data.get("role") == "owner" and data.get("is_owner") == True:
        log_result(4, "PASS", f"Org created, founder is owner, org_id={org_id}")
    else:
        log_result(4, "FAIL", f"Unexpected org response: {data}")
else:
    log_result(4, "FAIL", "Org creation failed")

# Step 5: PUT /api/org/strategy + GET /api/org/strategy + GET /api/org
print("\n[Step 5] PUT /api/org/strategy (hidden dream)")
strategy_data = {
    "north_star": "Reach 100 crore annual revenue and be the top C&I solar EPC in North India",
    "target": "100 Cr ARR",
    "deadline": "Mar 2027",
    "priorities": [
        "Win commercial & industrial rooftop deals",
        "Push EPC ticket sizes above 50L",
        "Protect 18% margins"
    ],
    "decision_rules": "Never quote below 18% margin. Prefer C&I over residential.",
    "current_arr": 12000000,  # 1.2 crore
    "target_arr": 1000000000  # 100 crore
}
resp = api_call("PUT", "/org/strategy", headers=founder_headers, json_data=strategy_data)
if resp and resp.status_code == 200:
    data = resp.json()
    if data.get("north_star") == strategy_data["north_star"]:
        log_result("5a", "PASS", "Strategy set successfully")
    else:
        log_result("5a", "FAIL", f"Strategy mismatch: {data}")
else:
    log_result("5a", "FAIL", "Strategy PUT failed")

# GET /api/org/strategy confirms it
resp = api_call("GET", "/org/strategy", headers=founder_headers)
if resp and resp.status_code == 200:
    data = resp.json()
    if (data.get("north_star") == strategy_data["north_star"] and
        data.get("target") == strategy_data["target"] and
        data.get("deadline") == strategy_data["deadline"]):
        log_result("5b", "PASS", "Strategy GET confirms values")
    else:
        log_result("5b", "FAIL", f"Strategy GET mismatch: {data}")
else:
    log_result("5b", "FAIL", "Strategy GET failed")

# GET /api/org confirms strategy_set=true but does NOT leak north_star
resp = api_call("GET", "/org", headers=founder_headers)
if resp and resp.status_code == 200:
    data = resp.json()
    if (data.get("strategy_set") == True and
        "north_star" not in data and
        "target" not in data and
        "deadline" not in data):
        log_result("5c", "PASS", "GET /org shows strategy_set=true, no leakage")
    else:
        log_result("5c", "FAIL", f"GET /org leaks strategy or missing flag: {data}")
else:
    log_result("5c", "FAIL", "GET /org failed")

# Step 6: Founder POST /api/brain/ask (1 LLM) - PERSONAL decision
print("\n[Step 6] Founder POST /api/brain/ask (1 LLM) - PERSONAL decision")
question = "A potential client is offering us a large 2 crore deal, but they're pushing the margin down to 9%. It would be our biggest deal ever. Should I take it?"
resp = api_call("POST", "/brain/ask", headers=founder_headers, json_data={"question": question})
if resp and resp.status_code == 200:
    data = resp.json()
    count_llm_call("/brain/ask", "founder personal decision")
    
    # VERIFY response contains clarity fields
    required = ["situation_read", "next_action", "hook", "sharpening_question"]
    has_clarity = verify_keys(data, required, "founder brain response")
    
    # VERIFY founder-only goal_impact present
    has_goal_impact = "goal_impact" in data
    if has_goal_impact:
        gi = data["goal_impact"]
        gi_valid = verify_keys(gi, ["score", "band", "label", "reason"], "goal_impact")
    else:
        gi_valid = False
    
    # VERIFY strategic_alignment is NOT in response
    no_strategic = verify_no_keys(data, ["strategic_alignment"], "founder response")
    
    if has_clarity and has_goal_impact and gi_valid and no_strategic:
        log_result(6, "PASS", f"Founder decision: clarity fields ✓, goal_impact ✓ (score={gi['score']}, band={gi['band']}), no strategic_alignment ✓")
    else:
        log_result(6, "FAIL", f"Missing fields or leakage: clarity={has_clarity}, goal_impact={has_goal_impact}, no_strategic={no_strategic}")
else:
    log_result(6, "FAIL", "Founder brain ask failed")

# Step 7: POST /api/brain/decisions/{id}/commit + POST /api/brain/decisions/{id}/status
print("\n[Step 7] Commit and complete decision")
if resp and resp.status_code == 200:
    decision_id = data.get("decision_id")
    
    # Commit
    resp_commit = api_call("POST", f"/brain/decisions/{decision_id}/commit", headers=founder_headers,
                          json_data={"action": "Decline the 9% deal politely, focus on finding C&I deals at 18%+ margin", "due_in_hours": 24})
    if resp_commit and resp_commit.status_code == 200:
        log_result("7a", "PASS", "Decision committed")
    else:
        log_result("7a", "FAIL", "Commit failed")
    
    # Mark done
    resp_status = api_call("POST", f"/brain/decisions/{decision_id}/status", headers=founder_headers,
                          json_data={"status": "done", "outcome": "worked", "result": "Declined the low-margin deal, found a better C&I prospect at 19% margin"})
    if resp_status and resp_status.status_code == 200:
        log_result("7b", "PASS", "Decision marked done with outcome=worked")
    else:
        log_result("7b", "FAIL", "Status update failed")
else:
    log_result(7, "FAIL", "No decision_id from step 6")

# (B) TEAM WORKS ON HIS DREAM
print("\n" + "-" * 80)
print("(B) TEAM WORKS ON HIS DREAM")
print("-" * 80)

# Step 8: Create 3 members (SALES, MARKETING, OPERATIONS)
print("\n[Step 8] Create 3 members and set functions")
members = []
functions = ["sales", "marketing", "operations"]

for i, func in enumerate(functions):
    # Create member account
    member_email = f"member_{func}_{int(time.time())}@heliossolar.com"
    member_password = "TestMember@2026"
    
    print(f"\n  Creating {func.upper()} member: {member_email}")
    
    # Signup
    resp = api_call("POST", "/auth/signup", json_data={
        "email": member_email,
        "password": member_password,
        "name": f"{func.capitalize()} Lead"
    })
    if not resp or resp.status_code != 200:
        log_result(f"8{chr(97+i)}", "FAIL", f"Signup failed for {func}")
        continue
    
    member_data = resp.json()
    member_token = member_data["token"]
    member_headers = {"Authorization": f"Bearer {member_token}"}
    
    # Founder creates invite
    resp_invite = api_call("POST", "/org/invites", headers=founder_headers, json_data={})
    if not resp_invite or resp_invite.status_code != 200:
        log_result(f"8{chr(97+i)}", "FAIL", f"Invite creation failed for {func}")
        continue
    
    invite_code = resp_invite.json()["code"]
    
    # Member joins
    resp_join = api_call("POST", "/org/join", headers=member_headers, json_data={"code": invite_code})
    if not resp_join or resp_join.status_code != 200:
        log_result(f"8{chr(97+i)}", "FAIL", f"Join failed for {func}")
        continue
    
    # Set function
    resp_func = api_call("POST", "/brain/profile", headers=member_headers, json_data={"function": func})
    if resp_func and resp_func.status_code == 200:
        members.append({
            "email": member_email,
            "password": member_password,
            "token": member_token,
            "headers": member_headers,
            "function": func
        })
        log_result(f"8{chr(97+i)}", "PASS", f"{func.upper()} member created and joined")
        
        # Append to test_credentials.md
        with open("/app/memory/test_credentials.md", "a") as f:
            f.write(f"\n## {func.capitalize()} Lead (Persona 1 test)\n")
            f.write(f"- Email: {member_email}\n")
            f.write(f"- Password: {member_password}\n")
            f.write(f"- Function: {func}\n")
    else:
        log_result(f"8{chr(97+i)}", "FAIL", f"Function set failed for {func}")

print(f"\n  ✓ Created {len(members)} members")

# Step 9: Each member POST /api/brain/ask ONE decision (3 LLM)
print("\n[Step 9] Each member asks ONE realistic domain decision (3 LLM)")

member_questions = {
    "sales": "We have a lead for a 1.5 crore C&I rooftop deal, but they want a 15% margin. Should I push for 18% or take it?",
    "marketing": "Should we invest 2 lakhs in Google Ads for C&I solar keywords, or focus on LinkedIn outreach to facility managers?",
    "operations": "A supplier is offering us panels at 8% discount if we commit to 6-month inventory. Should we take it?"
}

forbidden_phrases = ["100 crore", "100 Cr", "Mar 2027", "north star", "north-star", "strategy", "confidential", "leadership direction"]

for member in members:
    func = member["function"]
    question = member_questions.get(func, "What should I focus on this week?")
    
    print(f"\n  {func.upper()} member asks: {question[:60]}...")
    resp = api_call("POST", "/brain/ask", headers=member["headers"], json_data={"question": question})
    
    if resp and resp.status_code == 200:
        data = resp.json()
        count_llm_call("/brain/ask", f"{func} member decision")
        
        # CRITICAL ASSERTIONS
        # 1. Must NOT contain goal_impact
        no_goal_impact = verify_no_keys(data, ["goal_impact"], f"{func} response")
        
        # 2. Must NOT contain strategic_alignment
        no_strategic = verify_no_keys(data, ["strategic_alignment"], f"{func} response")
        
        # 3. Answer text must NOT leak strategy
        answer_text = str(data.get("answer", "")) + str(data.get("recommendation", "")) + str(data.get("next_action", ""))
        no_leakage = verify_no_leakage(answer_text, forbidden_phrases, f"{func} answer")
        
        # 4. Should be sensibly steered (check for margin/priorities mentions)
        is_steered = any(word in answer_text.lower() for word in ["margin", "c&i", "commercial", "industrial", "18%"])
        
        if no_goal_impact and no_strategic and no_leakage:
            if is_steered:
                log_result(f"9{chr(97+members.index(member))}", "PASS", 
                          f"{func.upper()}: no goal_impact ✓, no strategic_alignment ✓, no leakage ✓, sensibly steered ✓")
            else:
                log_result(f"9{chr(97+members.index(member))}", "PASS", 
                          f"{func.upper()}: no goal_impact ✓, no strategic_alignment ✓, no leakage ✓ (steering unclear)")
        else:
            log_result(f"9{chr(97+members.index(member))}", "FAIL", 
                      f"{func.upper()}: goal_impact={not no_goal_impact}, strategic={not no_strategic}, leakage={not no_leakage}")
        
        # Store decision_id for step 10
        member["decision_id"] = data.get("decision_id")
    else:
        log_result(f"9{chr(97+members.index(member))}", "FAIL", f"{func} brain ask failed")

# Step 10: >=2 members commit + mark done (free)
print("\n[Step 10] >=2 members commit and mark done")
for i, member in enumerate(members[:2]):  # First 2 members
    func = member["function"]
    decision_id = member.get("decision_id")
    
    if not decision_id:
        log_result(f"10{chr(97+i)}", "FAIL", f"{func} no decision_id")
        continue
    
    # Commit
    action = f"Execute the {func} plan within 48 hours"
    resp_commit = api_call("POST", f"/brain/decisions/{decision_id}/commit", headers=member["headers"],
                          json_data={"action": action, "due_in_hours": 48})
    
    # Mark done
    result = f"Completed {func} action successfully, aligned with company priorities"
    resp_status = api_call("POST", f"/brain/decisions/{decision_id}/status", headers=member["headers"],
                          json_data={"status": "done", "outcome": "worked", "result": result})
    
    if resp_commit and resp_commit.status_code == 200 and resp_status and resp_status.status_code == 200:
        log_result(f"10{chr(97+i)}", "PASS", f"{func.upper()} committed and marked done")
    else:
        log_result(f"10{chr(97+i)}", "FAIL", f"{func} commit/status failed")

# Step 11: Founder GET /api/org/cockpit
print("\n[Step 11] Founder GET /api/org/cockpit")
resp = api_call("GET", "/org/cockpit", headers=founder_headers)
if resp and resp.status_code == 200:
    data = resp.json()
    
    # Verify presence of required keys
    required_top = ["north_star", "totals", "alignment", "execution", "per_member", "team_alignment", 
                    "drift", "contradictions", "pacing", "goal_progress", "active_actions", "results"]
    has_keys = verify_keys(data, required_top, "cockpit")
    
    # Check specific values
    totals = data.get("totals", {})
    alignment = data.get("alignment", {})
    execution = data.get("execution", {})
    
    print(f"  Cockpit data:")
    print(f"    Totals: decisions={totals.get('decisions')}, last_7d={totals.get('last_7d')}, members={totals.get('members')}")
    print(f"    Alignment: avg={alignment.get('avg')}, scored={alignment.get('scored')}, high={alignment.get('high')}")
    print(f"    Execution: done={execution.get('done')}, follow_through_pct={execution.get('follow_through_pct')}, overdue={execution.get('overdue')}")
    print(f"    Per-member entries: {len(data.get('per_member', []))}")
    print(f"    Team alignment entries: {len(data.get('team_alignment', []))}")
    print(f"    Active actions: {len(data.get('active_actions', []))}")
    print(f"    Results: {len(data.get('results', []))}")
    
    if has_keys and alignment.get("scored", 0) >= 4:  # At least founder + 3 members
        log_result(11, "PASS", f"Cockpit returned with all keys, scored={alignment.get('scored')}, avg_alignment={alignment.get('avg')}")
    else:
        log_result(11, "FAIL", f"Cockpit missing keys or insufficient data: scored={alignment.get('scored')}")
else:
    log_result(11, "FAIL", "Cockpit GET failed")

# Step 12: Founder POST /api/org/progress multiple times
print("\n[Step 12] Founder POST /api/org/progress (climb progress)")
progress_values = [25000000, 40000000, 60000000]  # 2.5 Cr, 4 Cr, 6 Cr

for i, arr_value in enumerate(progress_values):
    resp = api_call("POST", "/org/progress", headers=founder_headers, json_data={"current_arr": arr_value})
    if resp and resp.status_code == 200:
        data = resp.json()
        gp = data.get("goal_progress", {})
        progress_pct = gp.get("progress_pct")
        status = gp.get("status")
        print(f"  Progress update {i+1}: current_arr={arr_value/10000000:.1f}Cr, progress_pct={progress_pct}%, status={status}")
    else:
        log_result(f"12{chr(97+i)}", "FAIL", f"Progress update {i+1} failed")

# Verify strategy_version did NOT change
resp = api_call("GET", "/org/strategy", headers=founder_headers)
if resp and resp.status_code == 200:
    data = resp.json()
    strategy_version = data.get("strategy_version")
    if strategy_version == 1:  # Should still be 1 (initial set)
        log_result(12, "PASS", f"Progress climbed, strategy_version unchanged ({strategy_version})")
    else:
        log_result(12, "FAIL", f"Strategy version changed unexpectedly: {strategy_version}")
else:
    log_result(12, "FAIL", "Strategy GET failed")

# Step 13: Founder POST /api/org/plan/draft (1 LLM)
print("\n[Step 13] Founder POST /api/org/plan/draft (1 LLM)")
resp = api_call("POST", "/org/plan/draft", headers=founder_headers, json_data={
    "target": "Scale to 50 Cr ARR in 12 months"
})
if resp and resp.status_code == 200:
    data = resp.json()
    count_llm_call("/org/plan/draft", "autonomous plan draft")
    
    if verify_keys(data, ["company_objective", "departments"], "plan draft"):
        plan_id = data.get("id")
        print(f"  Plan drafted: {data.get('company_objective')[:80]}...")
        print(f"  Departments: {len(data.get('departments', []))}")
        
        # GET /api/org/plan shows draft
        resp_get = api_call("GET", "/org/plan", headers=founder_headers)
        if resp_get and resp_get.status_code == 200:
            plan_data = resp_get.json()
            if plan_data.get("draft"):
                log_result("13a", "PASS", "Plan draft created and visible in GET /org/plan")
            else:
                log_result("13a", "FAIL", "Draft not visible in GET /org/plan")
        
        # POST /api/org/plan/{id}/ratify
        resp_ratify = api_call("POST", f"/org/plan/{plan_id}/ratify", headers=founder_headers)
        if resp_ratify and resp_ratify.status_code == 200:
            log_result("13b", "PASS", "Plan ratified successfully")
        else:
            log_result("13b", "FAIL", "Plan ratify failed")
    else:
        log_result(13, "FAIL", "Plan draft incomplete")
else:
    log_result(13, "FAIL", "Plan draft failed")

# Step 14: GATING (free) - members cannot access owner-only endpoints
print("\n[Step 14] GATING - members walled off from owner-only endpoints")
if members:
    member = members[0]
    func = member["function"]
    
    # GET /api/org/strategy -> 403
    resp1 = api_call("GET", "/org/strategy", headers=member["headers"], expect_status=403)
    
    # GET /api/org/progress -> 403
    resp2 = api_call("GET", "/org/progress", headers=member["headers"], expect_status=403)
    
    # GET /api/org/cockpit -> 403
    resp3 = api_call("GET", "/org/cockpit", headers=member["headers"], expect_status=403)
    
    # GET /api/org/plan -> 403
    resp4 = api_call("GET", "/org/plan", headers=member["headers"], expect_status=403)
    
    # No-token GET /api/org/strategy -> 401
    resp5 = api_call("GET", "/org/strategy", expect_status=401)
    
    all_gated = all([
        resp1 and resp1.status_code == 403,
        resp2 and resp2.status_code == 403,
        resp3 and resp3.status_code == 403,
        resp4 and resp4.status_code == 403,
        resp5 and resp5.status_code == 401
    ])
    
    if all_gated:
        log_result(14, "PASS", "All member gating working correctly (403/401)")
    else:
        log_result(14, "FAIL", f"Gating failed: strategy={resp1.status_code if resp1 else 'N/A'}, progress={resp2.status_code if resp2 else 'N/A'}, cockpit={resp3.status_code if resp3 else 'N/A'}, plan={resp4.status_code if resp4 else 'N/A'}, no-token={resp5.status_code if resp5 else 'N/A'}")
else:
    log_result(14, "FAIL", "No members to test gating")

# =================== PERSONA 2 — LOCAL SMALL BUSINESS (solo, no org) ===================
print("\n" + "=" * 80)
print("PERSONA 2 — LOCAL SMALL BUSINESS (solo, no org)")
print("=" * 80)

# Step 15: Fresh signup
print("\n[Step 15] Fresh signup (solo small business)")
solo_email = f"bakery_owner_{int(time.time())}@localbakery.com"
solo_password = "BakeryOwner@2026"

resp = api_call("POST", "/auth/signup", json_data={
    "email": solo_email,
    "password": solo_password,
    "name": "Local Bakery Owner"
})
if resp and resp.status_code == 200:
    solo_data = resp.json()
    solo_token = solo_data["token"]
    solo_headers = {"Authorization": f"Bearer {solo_token}"}
    solo_credits = solo_data["user"]["credits"]
    log_result(15, "PASS", f"Solo signup successful: {solo_email}, credits={solo_credits}")
    
    # Append to test_credentials.md
    with open("/app/memory/test_credentials.md", "a") as f:
        f.write(f"\n## Local Bakery Owner (Persona 2 test)\n")
        f.write(f"- Email: {solo_email}\n")
        f.write(f"- Password: {solo_password}\n")
        f.write(f"- Type: Solo small business (no org)\n")
else:
    log_result(15, "FAIL", "Solo signup failed")
    solo_headers = None

# Step 16: POST /api/goals (1 LLM)
print("\n[Step 16] POST /api/goals (1 LLM)")
if solo_headers:
    resp = api_call("POST", "/goals", headers=solo_headers, json_data={
        "title": "Grow my neighborhood bakery",
        "why_now": "I run a single-outlet bakery in Meerut. Sales are flat, and I want to double revenue in the next year without opening a second location."
    })
    if resp and resp.status_code == 200:
        data = resp.json()
        count_llm_call("/goals", "solo goal creation")
        thread_id = data.get("thread", {}).get("thread_id")
        if thread_id:
            log_result(16, "PASS", f"Goal created, thread_id={thread_id}")
        else:
            log_result(16, "FAIL", "No thread_id returned")
    else:
        log_result(16, "FAIL", "Goal creation failed")
        thread_id = None
else:
    log_result(16, "FAIL", "No solo headers")
    thread_id = None

# Step 17: POST /api/threads/{id}/turn (1 LLM)
print("\n[Step 17] POST /api/threads/{id}/turn (1 LLM)")
if thread_id and solo_headers:
    credits_before = solo_credits
    
    resp = api_call("POST", f"/threads/{thread_id}/turn", headers=solo_headers, json_data={
        "message": "What's the single best way to increase sales without opening a new location?",
        "mode": "normal"
    })
    if resp and resp.status_code == 200:
        data = resp.json()
        count_llm_call("/threads/{id}/turn", "solo turn")
        
        credits_after = data.get("credits")
        cost = data.get("cost")
        
        # Verify acknowledgment and next_action present
        ack = data.get("acknowledgment")
        thread_data = data.get("thread", {})
        next_action = thread_data.get("current_next_action")
        
        if ack and next_action and credits_after < credits_before:
            log_result(17, "PASS", f"Turn successful, cost={cost}, credits decreased ({credits_before} -> {credits_after})")
        else:
            log_result(17, "FAIL", f"Turn incomplete: ack={bool(ack)}, next_action={bool(next_action)}, credits={credits_after}")
    else:
        log_result(17, "FAIL", f"Turn failed: {resp.status_code if resp else 'no response'}")
else:
    log_result(17, "FAIL", "No thread_id or solo headers")

# Step 18: POST /api/threads/{id}/complete-action (1 LLM)
print("\n[Step 18] POST /api/threads/{id}/complete-action (1 LLM)")
if thread_id and solo_headers:
    resp = api_call("POST", f"/threads/{thread_id}/complete-action", headers=solo_headers)
    if resp and resp.status_code == 200:
        data = resp.json()
        count_llm_call("/threads/{id}/complete-action", "solo artifact")
        
        artifact = data.get("artifact", {})
        cost = data.get("cost")
        credits = data.get("credits")
        
        if artifact and artifact.get("artifact"):
            log_result(18, "PASS", f"Artifact generated, cost={cost}, credits={credits}")
        else:
            log_result(18, "FAIL", "No artifact returned")
    else:
        log_result(18, "FAIL", f"Complete-action failed: {resp.status_code if resp else 'no response'}")
else:
    log_result(18, "FAIL", "No thread_id or solo headers")

# Step 19: POST /api/brain/ask (1 LLM) - solo decision
print("\n[Step 19] POST /api/brain/ask (1 LLM) - solo decision")
if solo_headers:
    resp = api_call("POST", "/brain/ask", headers=solo_headers, json_data={
        "question": "A supplier is offering me a 20% discount on flour if I buy 6 months of inventory upfront. Should I take it?"
    })
    if resp and resp.status_code == 200:
        data = resp.json()
        count_llm_call("/brain/ask", "solo decision")
        
        mode = data.get("mode")
        
        # VERIFY no founder-only fields (no goal_impact, no strategic_alignment)
        no_goal_impact = verify_no_keys(data, ["goal_impact"], "solo brain response")
        no_strategic = verify_no_keys(data, ["strategic_alignment"], "solo brain response")
        
        # Verify credits decreased
        credits = data.get("credits")
        cost = data.get("cost")
        
        if mode in ["answer", "decide", "plan"] and no_goal_impact and no_strategic and cost:
            log_result(19, "PASS", f"Solo decision: mode={mode}, no founder-only fields ✓, cost={cost}, credits={credits}")
        else:
            log_result(19, "FAIL", f"Solo decision incomplete: mode={mode}, goal_impact={not no_goal_impact}, strategic={not no_strategic}")
    else:
        log_result(19, "FAIL", f"Solo brain ask failed: {resp.status_code if resp else 'no response'}")
else:
    log_result(19, "FAIL", "No solo headers")

# Step 20: (optional, 0 LLM) POST /api/payments/create-order
print("\n[Step 20] POST /api/payments/create-order (optional, 0 LLM)")
if solo_headers:
    resp = api_call("POST", "/payments/create-order", headers=solo_headers, json_data={
        "pack_id": "pack_100"
    })
    if resp and resp.status_code == 200:
        data = resp.json()
        checkout_url = data.get("checkout_url")
        if checkout_url:
            log_result(20, "PASS", f"Payment order created, checkout_url returned (NOT completing payment)")
        else:
            log_result(20, "FAIL", "No checkout_url returned")
    else:
        log_result(20, "FAIL", f"Payment create-order failed: {resp.status_code if resp else 'no response'}")
else:
    log_result(20, "FAIL", "No solo headers")

# =================== REPORT ===================
print("\n" + "=" * 80)
print("FINAL REPORT")
print("=" * 80)

print(f"\nTotal LLM calls used: {llm_call_count} / 18")
if llm_call_count > 18:
    print("  ⚠️  EXCEEDED LLM BUDGET")
else:
    print("  ✅ Within LLM budget")

print("\n" + "-" * 80)
print("STEP-BY-STEP RESULTS:")
print("-" * 80)

pass_count = sum(1 for r in results if r["status"] == "PASS")
fail_count = sum(1 for r in results if r["status"] == "FAIL")

for result in results:
    status_icon = "✅" if result["status"] == "PASS" else "❌"
    print(f"{status_icon} Step {result['step']}: {result['status']} - {result['details']}")

print("\n" + "-" * 80)
print(f"SUMMARY: {pass_count} PASS, {fail_count} FAIL out of {len(results)} tests")
print("-" * 80)

print("\n" + "=" * 80)
print("FOUNDER'S VERDICT")
print("=" * 80)

print("\n(1) Does it give the founder personal clarity?")
founder_clarity_steps = [1, 2, 3, 6, 7]
founder_clarity_pass = sum(1 for r in results if any(str(r["step"]).startswith(str(s)) for s in founder_clarity_steps) and r["status"] == "PASS")
print(f"    {founder_clarity_pass}/{len([r for r in results if any(str(r['step']).startswith(str(s)) for s in founder_clarity_steps)])} personal clarity tests passed")

print("\n(2) Does it let his team execute on his hidden dream with silent alignment + working cockpit?")
team_steps = [8, 9, 10, 11, 12, 13, 14]
team_pass = sum(1 for r in results if any(str(r["step"]).startswith(str(s)) for s in team_steps) and r["status"] == "PASS")
print(f"    {team_pass}/{len([r for r in results if any(str(r['step']).startswith(str(s)) for s in team_steps)])} team execution tests passed")

print("\n(3) Does the solo small-business flow work?")
solo_steps = [15, 16, 17, 18, 19, 20]
solo_pass = sum(1 for r in results if any(str(r["step"]).startswith(str(s)) for s in solo_steps) and r["status"] == "PASS")
print(f"    {solo_pass}/{len([r for r in results if any(str(r['step']).startswith(str(s)) for s in solo_steps)])} solo flow tests passed")

print("\n" + "-" * 80)
print("ISSUES, MISSING, OR SURPRISING:")
print("-" * 80)

failed_steps = [r for r in results if r["status"] == "FAIL"]
if failed_steps:
    for r in failed_steps:
        print(f"  ❌ Step {r['step']}: {r['details']}")
else:
    print("  ✅ No critical failures detected")

print("\n" + "=" * 80)
print(f"Test completed: {datetime.now().isoformat()}")
print(f"Total LLM calls: {llm_call_count} / 18")
print("=" * 80)
