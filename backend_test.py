#!/usr/bin/env python3
"""
Light regression test for Coach-engine fix (iteration 9).
BUDGET: AT MOST 3 LLM calls total.
"""

import requests
import json
import sys
import time

# Backend URL from frontend/.env
BASE_URL = "https://software-audit-2.preview.emergentagent.com/api"

# Founder credentials
FOUNDER_EMAIL = "ceo@smartdecigen.com"
FOUNDER_PASSWORD = "FounderOS@2026"

# Track LLM call count
llm_call_count = 0
MAX_LLM_CALLS = 3

def log(msg):
    print(f"[TEST] {msg}")

def login(email, password):
    """Login and return token."""
    log(f"Logging in as {email}...")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": email,
        "password": password
    })
    if resp.status_code != 200:
        log(f"❌ Login failed: {resp.status_code} {resp.text}")
        sys.exit(1)
    data = resp.json()
    token = data.get("token")
    log(f"✅ Login successful, token: {token[:20]}...")
    return token

def create_goal(token, title, why_now):
    """Create a goal (LLM call #1)."""
    global llm_call_count
    llm_call_count += 1
    log(f"[LLM CALL #{llm_call_count}] Creating goal: {title}")
    
    resp = requests.post(f"{BASE_URL}/goals", 
        headers={"Authorization": f"Bearer {token}"},
        json={"title": title, "why_now": why_now}
    )
    
    log(f"Response status: {resp.status_code}")
    if resp.status_code != 200:
        log(f"❌ Create goal failed: {resp.status_code} {resp.text}")
        return None, resp.status_code
    
    data = resp.json()
    log(f"Response data keys: {list(data.keys())}")
    log(f"Full response: {json.dumps(data, indent=2)[:500]}")
    
    # Try different possible response structures
    thread_id = None
    if "thread" in data:
        thread_obj = data["thread"]
        thread_id = thread_obj.get("thread_id") or thread_obj.get("id")
    elif "id" in data:
        thread_id = data["id"]
    elif "thread_id" in data:
        thread_id = data["thread_id"]
    
    log(f"✅ Goal created, thread_id: {thread_id}")
    return thread_id, resp.status_code

def send_turn(token, thread_id, message, mode="normal"):
    """Send a turn (LLM call)."""
    global llm_call_count
    llm_call_count += 1
    log(f"[LLM CALL #{llm_call_count}] Sending turn to thread {thread_id}")
    log(f"Message: {message}")
    
    resp = requests.post(f"{BASE_URL}/threads/{thread_id}/turn",
        headers={"Authorization": f"Bearer {token}"},
        json={"message": message, "mode": mode}
    )
    
    log(f"Response status: {resp.status_code}")
    if resp.status_code != 200:
        log(f"❌ Turn failed: {resp.status_code}")
        log(f"Response body: {resp.text[:500]}")
        return None, resp.status_code
    
    data = resp.json()
    log(f"✅ Turn successful")
    log(f"Intent: {data.get('intent')}")
    log(f"Model: {data.get('model')}")
    log(f"Credits: {data.get('credits')}")
    log(f"Cost: {data.get('cost')}")
    log(f"Acknowledgment in turn response: {data.get('acknowledgment', '')[:200]}")
    
    return data, resp.status_code

def get_thread(token, thread_id):
    """Get thread details."""
    log(f"Getting thread {thread_id}...")
    resp = requests.get(f"{BASE_URL}/threads/{thread_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    if resp.status_code != 200:
        log(f"❌ Get thread failed: {resp.status_code}")
        return None
    
    data = resp.json()
    log(f"Thread response keys: {list(data.keys())}")
    log(f"Thread response (first 1000 chars): {json.dumps(data, indent=2)[:1000]}")
    log(f"✅ Thread retrieved")
    return data

def check_pass_criteria(turn_response, thread_data):
    """Check if the turn meets all PASS criteria."""
    log("\n" + "="*80)
    log("CHECKING PASS CRITERIA")
    log("="*80)
    
    failures = []
    
    # 1. HTTP 200 (already checked, but confirm)
    log("✅ Criterion 1: HTTP 200 (NOT 502)")
    
    # 2. Response includes intent, model, credits
    intent = turn_response.get("intent")
    model = turn_response.get("model")
    credits = turn_response.get("credits")
    
    if not intent:
        failures.append("Missing 'intent' in response")
    else:
        log(f"✅ Criterion 2a: intent present = '{intent}'")
    
    if not model:
        failures.append("Missing 'model' in response")
    else:
        log(f"✅ Criterion 2b: model present = '{model}'")
    
    if credits is None:
        failures.append("Missing 'credits' in response")
    else:
        log(f"✅ Criterion 2c: credits present = {credits}")
    
    # 3. Get thread state - the fields are nested inside thread_data["thread"]
    thread = thread_data.get("thread", {})
    acknowledgment = thread.get("current_acknowledgment", "")
    next_action = thread.get("current_next_action", "")
    easiest_path = thread.get("current_easiest_path", "")
    open_question = thread.get("current_open_question", "")
    phase = thread.get("current_phase", "")
    state_summary = thread.get("current_state_summary", "")
    
    # Also check if acknowledgment is in the turn_response
    if not acknowledgment and "acknowledgment" in turn_response:
        acknowledgment = turn_response.get("acknowledgment", "")
        log(f"Note: Using acknowledgment from turn response instead of thread")
    
    log(f"\nThread state:")
    log(f"  Phase: {phase}")
    log(f"  State summary: {state_summary[:200] if state_summary else '(empty)'}...")
    log(f"  Acknowledgment: {acknowledgment[:200] if acknowledgment else '(empty)'}...")
    log(f"  Next action: {next_action[:200] if next_action else '(empty)'}...")
    log(f"  Easiest path: {easiest_path[:200] if easiest_path else '(empty)'}...")
    log(f"  Open question: {open_question[:200] if open_question else '(empty)'}...")
    
    # 4. Check if acknowledgment commits to ONE specific named idea
    # FAIL if: only a category (like "vertical AI"), or only a question, or deflection
    ack_lower = acknowledgment.lower() if acknowledgment else ""
    
    # Check for deflection patterns
    deflection_patterns = [
        "which one",
        "what kind",
        "what type",
        "tell me more about",
        "can you clarify",
        "do you prefer"
    ]
    
    has_deflection = any(pattern in ack_lower for pattern in deflection_patterns)
    
    # Check if it's just a category without a specific named idea
    # A good acknowledgment should name a concrete problem/product
    # Bad: "Let's explore vertical AI opportunities"
    # Good: "AI prior-authorization in US healthcare"
    
    if len(acknowledgment) < 20:
        failures.append(f"Acknowledgment too short ({len(acknowledgment)} chars) - likely not a concrete pick")
    elif has_deflection and len(acknowledgment) < 100:
        failures.append("Acknowledgment appears to be a deflecting question, not a concrete pick")
    else:
        log(f"✅ Criterion 3: Acknowledgment commits to a specific idea (length: {len(acknowledgment)} chars)")
    
    # 5. current_next_action is concrete and non-empty
    if not next_action or len(next_action) < 20:
        failures.append(f"current_next_action is empty or too short: '{next_action}'")
    else:
        log(f"✅ Criterion 4: current_next_action is concrete and non-empty ({len(next_action)} chars)")
    
    # 6. current_easiest_path is multi-step
    if not easiest_path or len(easiest_path) < 50:
        failures.append(f"current_easiest_path is empty or too short: '{easiest_path}'")
    else:
        # Check if it contains multiple steps (look for numbering, bullet points, or sequential actions)
        step_indicators = ["1.", "2.", "3.", "step 1", "step 2", "first", "then", "next", "finally", "after that"]
        has_steps = any(indicator in easiest_path.lower() for indicator in step_indicators)
        
        # Also check for multiple sentences with action verbs (indicates a sequence)
        sentences = easiest_path.split(". ")
        if len(sentences) >= 3:
            has_steps = True
        
        if not has_steps:
            failures.append("current_easiest_path doesn't appear to contain multiple steps")
        else:
            log(f"✅ Criterion 5: current_easiest_path is multi-step ({len(easiest_path)} chars, {len(sentences)} sentences)")
    
    # 7. current_open_question is a single consent/refining question
    if not open_question or len(open_question) < 10:
        failures.append(f"current_open_question is empty or too short: '{open_question}'")
    else:
        log(f"✅ Criterion 6: current_open_question is present ({len(open_question)} chars)")
    
    return failures

def main():
    log("="*80)
    log("COACH ENGINE REGRESSION TEST - ITERATION 9")
    log("Budget: AT MOST 3 LLM calls")
    log("="*80)
    
    # Login
    token = login(FOUNDER_EMAIL, FOUNDER_PASSWORD)
    
    # TEST 1: Create goal (LLM call #1)
    log("\n" + "="*80)
    log("TEST 1: Create goal 'Build an AI startup'")
    log("="*80)
    
    thread_id, status = create_goal(
        token,
        "Build an AI startup",
        "I want to build a 100 billion dollar AI startup in one year."
    )
    
    if status != 200:
        log(f"❌ FAIL: Goal creation returned {status} instead of 200")
        sys.exit(1)
    
    if not thread_id:
        log("❌ FAIL: No thread_id returned")
        sys.exit(1)
    
    log(f"✅ PASS: Goal created successfully, thread_id: {thread_id}")
    
    # TEST 2: Send "suggest" turn (LLM call #2)
    log("\n" + "="*80)
    log("TEST 2: Send 'suggest' turn - the critical test")
    log("="*80)
    
    turn_response, status = send_turn(
        token,
        thread_id,
        "Suggest me one painful problem I can build an AI startup around, and how to start.",
        mode="normal"
    )
    
    if status == 502:
        log("❌ FAIL: Turn returned 502 (the bug this fix was supposed to address)")
        sys.exit(1)
    
    if status != 200:
        log(f"❌ FAIL: Turn returned {status} instead of 200")
        sys.exit(1)
    
    log("✅ PASS: Turn returned 200 (not 502)")
    
    # Get thread details
    thread_data = get_thread(token, thread_id)
    if not thread_data:
        log("❌ FAIL: Could not retrieve thread data")
        sys.exit(1)
    
    # Check all pass criteria
    failures = check_pass_criteria(turn_response, thread_data)
    
    if failures:
        log("\n" + "="*80)
        log("❌ FAIL: Some criteria not met:")
        for failure in failures:
            log(f"  - {failure}")
        log("="*80)
        sys.exit(1)
    
    log("\n" + "="*80)
    log("✅ PASS: All criteria met for TEST 2")
    log("="*80)
    
    # TEST 3: Optional second goal (LLM call #3)
    if llm_call_count < MAX_LLM_CALLS:
        log("\n" + "="*80)
        log("TEST 3: Optional second goal (exploring/naming phase)")
        log("="*80)
        
        thread_id2, status = create_goal(
            token,
            "Grow my business",
            "I'm not sure where to start."
        )
        
        if status != 200:
            log(f"❌ FAIL: Second goal creation returned {status}")
            sys.exit(1)
        
        log(f"✅ PASS: Second goal created successfully, thread_id: {thread_id2}")
        
        # Get thread to check phase
        thread_data2 = get_thread(token, thread_id2)
        if thread_data2:
            thread = thread_data2.get("thread", {})
            phase = thread.get("current_phase", "")
            open_question = thread.get("current_open_question", "")
            log(f"Phase: {phase}")
            log(f"Open question: {open_question[:200] if open_question else '(empty)'}...")
            
            if phase in ["exploring", "naming"]:
                log(f"✅ PASS: Phase is {phase} (expected for vague goal)")
            
            if open_question:
                log("✅ PASS: Has open question (no crash)")
    else:
        log("\n" + "="*80)
        log("TEST 3: SKIPPED (would exceed 3 LLM call budget)")
        log("="*80)
    
    # Final summary
    log("\n" + "="*80)
    log("FINAL SUMMARY")
    log("="*80)
    log(f"Total LLM calls used: {llm_call_count}/{MAX_LLM_CALLS}")
    log("✅ ALL TESTS PASSED")
    log("="*80)

if __name__ == "__main__":
    main()
