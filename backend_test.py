#!/usr/bin/env python3
"""
Targeted test for iteration 8: "file stays in the room" fix.
Tests that current_file_facts persists across turns without attachments.
"""
import requests
import base64
import json
import time
import random

BASE_URL = "http://localhost:8001/api"

def log(msg):
    print(f"[TEST] {msg}")

def signup_fresh_user():
    """Sign up a fresh test user."""
    email = f"test_file_persist_{random.randint(100000, 999999)}@test.com"
    password = "TestPass123!"
    name = "File Persist Test User"
    
    log(f"Signing up fresh user: {email}")
    r = requests.post(f"{BASE_URL}/auth/signup", json={
        "email": email,
        "password": password,
        "name": name
    })
    assert r.status_code == 200, f"Signup failed: {r.status_code} {r.text}"
    data = r.json()
    token = data["token"]
    credits = data["user"]["credits"]
    log(f"✓ Signup successful. Credits: {credits}, Token: {token[:20]}...")
    return token, email

def create_goal(token):
    """POST /api/goals with a solar subsidy goal."""
    log("Creating goal: solar subsidy paperwork analysis")
    headers = {"Authorization": f"Bearer {token}"}
    goal_data = {
        "title": "Solar subsidy paperwork analysis",
        "why_now": "I run solar subsidy paperwork; I have 70 applications in a sheet and need to figure out my rupees-per-disbursed-case."
    }
    
    r = requests.post(f"{BASE_URL}/goals", json=goal_data, headers=headers)
    assert r.status_code == 200, f"Goal creation failed: {r.status_code} {r.text}"
    data = r.json()
    thread_id = data["thread"]["thread_id"]
    cost = data.get("cost", 0)
    log(f"✓ Goal created. Thread ID: {thread_id}, Cost: {cost} credits")
    return thread_id

def create_csv_attachment():
    """Create a small CSV with 2 Disbursed, 3 Pending rows."""
    csv_content = """Name,Status,Amount
Ravi,Disbursed,2400
Sita,Disbursed,2400
Amit,Pending,
Neha,Pending,
Vikas,Pending,"""
    
    csv_bytes = csv_content.encode('utf-8')
    csv_b64 = base64.b64encode(csv_bytes).decode('utf-8')
    return csv_b64, "applications.csv", "text/csv"

def post_turn_with_attachment(token, thread_id):
    """POST /api/turn with CSV attachment."""
    log("Posting turn with CSV attachment (5 rows: 2 Disbursed, 3 Pending)")
    headers = {"Authorization": f"Bearer {token}"}
    
    csv_b64, filename, mime = create_csv_attachment()
    
    turn_data = {
        "message": "Here's my sheet. What should I do next?",
        "mode": "normal",
        "attachment_base64": csv_b64,
        "attachment_filename": filename,
        "attachment_mime": mime
    }
    
    r = requests.post(f"{BASE_URL}/threads/{thread_id}/turn", json=turn_data, headers=headers)
    assert r.status_code == 200, f"Turn with attachment failed: {r.status_code} {r.text}"
    data = r.json()
    cost = data.get("cost", 0)
    log(f"✓ Turn with attachment successful. Cost: {cost} credits")
    return data

def get_thread(token, thread_id):
    """GET /api/threads/{thread_id}."""
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(f"{BASE_URL}/threads/{thread_id}", headers=headers)
    assert r.status_code == 200, f"Get thread failed: {r.status_code} {r.text}"
    return r.json()["thread"]

def post_turn_no_attachment(token, thread_id, message):
    """POST /api/turn without attachment."""
    log(f"Posting turn WITHOUT attachment: '{message}'")
    headers = {"Authorization": f"Bearer {token}"}
    
    turn_data = {
        "message": message,
        "mode": "normal"
    }
    
    r = requests.post(f"{BASE_URL}/threads/{thread_id}/turn", json=turn_data, headers=headers)
    assert r.status_code == 200, f"Turn without attachment failed: {r.status_code} {r.text}"
    data = r.json()
    cost = data.get("cost", 0)
    log(f"✓ Turn without attachment successful. Cost: {cost} credits")
    return data

def complete_action(token, thread_id):
    """POST /api/complete-action."""
    log("Calling complete-action to generate artifact")
    headers = {"Authorization": f"Bearer {token}"}
    
    r = requests.post(f"{BASE_URL}/threads/{thread_id}/complete-action", headers=headers)
    assert r.status_code == 200, f"Complete action failed: {r.status_code} {r.text}"
    data = r.json()
    cost = data.get("cost", 0)
    log(f"✓ Complete action successful. Cost: {cost} credits")
    return data

def test_file_stays_in_room():
    """Main test: file facts persist across turns without attachments."""
    log("=" * 80)
    log("ITERATION 8 TEST: File stays in the room")
    log("=" * 80)
    
    # Step 1: Sign up fresh user
    token, email = signup_fresh_user()
    
    # Step 2: Create goal
    thread_id = create_goal(token)
    
    # Small delay to ensure backend processing
    time.sleep(1)
    
    # Step 3: POST turn with CSV attachment
    turn1_response = post_turn_with_attachment(token, thread_id)
    
    # Get thread after turn 1
    thread_after_turn1 = get_thread(token, thread_id)
    
    log("\n" + "=" * 80)
    log("ASSERTION (a): thread.current_file_facts is present and non-empty")
    log("=" * 80)
    
    file_facts_turn1 = thread_after_turn1.get("current_file_facts")
    if file_facts_turn1 and file_facts_turn1.strip():
        log(f"✓ PASS: current_file_facts is present and non-empty")
        log(f"  File facts (turn 1): {file_facts_turn1}")
    else:
        log(f"✗ FAIL: current_file_facts is empty or missing")
        log(f"  Value: {file_facts_turn1}")
        return False
    
    log("\n" + "=" * 80)
    log("ASSERTION (b): state_summary/big_picture mentions disbursed count")
    log("=" * 80)
    
    state_summary = thread_after_turn1.get("current_state_summary", "")
    big_picture = thread_after_turn1.get("current_big_picture", "")
    combined_text = f"{state_summary} {big_picture}".lower()
    
    # Check if the engine mentions the disbursed count (2 or "two")
    mentions_count = any(word in combined_text for word in ["2 disbursed", "two disbursed", "disbursed: 2", "disbursed (2"])
    
    if mentions_count or "disbursed" in combined_text:
        log(f"✓ PASS: Engine mentions disbursed data")
        log(f"  State summary: {state_summary[:200]}...")
        log(f"  Big picture: {big_picture}")
    else:
        log(f"⚠ PARTIAL: Engine may not explicitly state disbursed count")
        log(f"  State summary: {state_summary}")
        log(f"  Big picture: {big_picture}")
    
    log("\n" + "=" * 80)
    log("ASSERTION (c): requested_input doesn't ask user to recount")
    log("=" * 80)
    
    requested_input = thread_after_turn1.get("current_requested_input", "")
    if requested_input:
        # Check if it asks to count/filter/recount
        clerical_words = ["count", "filter", "find the column", "open your sheet", "how many"]
        asks_to_count = any(word in requested_input.lower() for word in clerical_words)
        
        if asks_to_count:
            log(f"✗ FAIL: requested_input asks user to do clerical work")
            log(f"  Requested input: {requested_input}")
            return False
        else:
            log(f"✓ PASS: requested_input asks for missing data (not clerical work)")
            log(f"  Requested input: {requested_input}")
    else:
        log(f"✓ PASS: No requested_input (engine has what it needs)")
    
    # Step 4: POST turn WITHOUT attachment
    log("\n" + "=" * 80)
    log("STEP 4: Second turn WITHOUT attachment")
    log("=" * 80)
    
    turn2_response = post_turn_no_attachment(token, thread_id, "thanks — anything else I should keep in mind?")
    
    # Get thread after turn 2
    thread_after_turn2 = get_thread(token, thread_id)
    
    log("\n" + "=" * 80)
    log("ASSERTION (d): current_file_facts STILL present (not cleared)")
    log("=" * 80)
    
    file_facts_turn2 = thread_after_turn2.get("current_file_facts")
    
    if file_facts_turn2 and file_facts_turn2.strip():
        if file_facts_turn2 == file_facts_turn1:
            log(f"✓ PASS: current_file_facts persisted unchanged")
            log(f"  File facts (turn 2): {file_facts_turn2}")
        else:
            log(f"⚠ PARTIAL: current_file_facts present but changed")
            log(f"  Turn 1: {file_facts_turn1}")
            log(f"  Turn 2: {file_facts_turn2}")
    else:
        log(f"✗ FAIL: current_file_facts was cleared/nulled")
        log(f"  Turn 1: {file_facts_turn1}")
        log(f"  Turn 2: {file_facts_turn2}")
        return False
    
    # Step 5: Complete action
    log("\n" + "=" * 80)
    log("STEP 5: Complete action (generate artifact)")
    log("=" * 80)
    
    action_response = complete_action(token, thread_id)
    artifact_text = action_response.get("artifact", {}).get("artifact", "")
    
    log("\n" + "=" * 80)
    log("ASSERTION (e): Artifact doesn't contain clerical instructions")
    log("=" * 80)
    
    # Check if artifact asks user to count/filter rows
    clerical_phrases = [
        "open your sheet",
        "count the rows",
        "filter the status column",
        "find the disbursed",
        "count disbursed rows",
        "look at your sheet"
    ]
    
    artifact_lower = artifact_text.lower()
    has_clerical = any(phrase in artifact_lower for phrase in clerical_phrases)
    
    if has_clerical:
        log(f"✗ FAIL: Artifact contains clerical instructions")
        log(f"  Artifact (first 400 chars): {artifact_text[:400]}")
        return False
    else:
        log(f"✓ PASS: Artifact does NOT contain clerical instructions")
        log(f"  Artifact (first 400 chars): {artifact_text[:400]}")
    
    log("\n" + "=" * 80)
    log("ALL ASSERTIONS PASSED ✓")
    log("=" * 80)
    log(f"\nTest user: {email}")
    log(f"Thread ID: {thread_id}")
    log(f"\nFile facts captured (verbatim):")
    log(f"  After turn 1: {file_facts_turn1}")
    log(f"  After turn 2: {file_facts_turn2}")
    log(f"\nArtifact text (first 400 chars):")
    log(f"  {artifact_text[:400]}")
    
    return True

if __name__ == "__main__":
    try:
        success = test_file_stays_in_room()
        if success:
            print("\n✓ TEST PASSED")
            exit(0)
        else:
            print("\n✗ TEST FAILED")
            exit(1)
    except Exception as e:
        print(f"\n✗ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
