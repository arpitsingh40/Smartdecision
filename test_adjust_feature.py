#!/usr/bin/env python3
"""
Backend test for SmartDecigen adjust-this-step turn feature.
CRITICAL: ANTHROPIC_API_KEY is REAL - limit to MAX 2 real LLM turns.
"""
import os
import requests
from dotenv import load_dotenv

# Load backend URL from frontend/.env
load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") + "/api"

# Test credentials
DEMO_EMAIL = "demo@smartdecigen.com"
DEMO_PASSWORD = "Demo1234!"
DEMO_THREAD_ID = "5da96480-6c43-49b7-990b-e0c76de387da"

def login():
    """Login and return token."""
    r = requests.post(f"{BASE_URL}/auth/login", json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD})
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    return r.json()["token"]

def get_credits(token):
    """Get current credits."""
    r = requests.get(f"{BASE_URL}/credits", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, f"Get credits failed: {r.status_code} {r.text}"
    return r.json()["credits"]

def test_adjust_turn_with_valid_mode():
    """Test 1: adjust:true with mode=normal -> intent=action_adjust, cost=5, credits decrease by 5."""
    print("\n=== Test 1: adjust:true with mode=normal ===")
    token = login()
    credits_before = get_credits(token)
    print(f"Credits before: {credits_before}")
    
    # Real LLM turn #1
    r = requests.post(
        f"{BASE_URL}/threads/{DEMO_THREAD_ID}/turn",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "About the next action you gave me: I'm blocked by someone else on this step. My collaborator has the source files.",
            "mode": "normal",
            "adjust": True
        }
    )
    
    print(f"Status: {r.status_code}")
    if r.status_code != 200:
        print(f"Response: {r.text}")
        assert False, f"Expected 200, got {r.status_code}"
    
    data = r.json()
    print(f"Intent: {data.get('intent')}")
    print(f"Cost: {data.get('cost')}")
    print(f"Credits after: {data.get('credits')}")
    print(f"Next action (first 100 chars): {data.get('thread', {}).get('current_next_action', '')[:100]}")
    
    # Assertions
    assert data["intent"] == "action_adjust", f"Expected intent=action_adjust, got {data['intent']}"
    assert data["cost"] == 5, f"Expected cost=5, got {data['cost']}"
    assert data["credits"] == credits_before - 5, f"Expected credits to decrease by 5, got {credits_before} -> {data['credits']}"
    assert data["thread"]["current_next_action"], "Expected non-empty current_next_action"
    assert len(data["thread"]["current_next_action"]) > 10, "Expected substantial next action text"
    
    print("✅ Test 1 PASSED")

def test_adjust_omitted():
    """Test 2: adjust omitted -> intent is NOT action_adjust."""
    print("\n=== Test 2: adjust omitted (normal turn) ===")
    token = login()
    credits_before = get_credits(token)
    print(f"Credits before: {credits_before}")
    
    # Real LLM turn #2
    r = requests.post(
        f"{BASE_URL}/threads/{DEMO_THREAD_ID}/turn",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "Quick update: still moving, nothing new today.",
            "mode": "normal"
        }
    )
    
    print(f"Status: {r.status_code}")
    if r.status_code != 200:
        print(f"Response: {r.text}")
        assert False, f"Expected 200, got {r.status_code}"
    
    data = r.json()
    print(f"Intent: {data.get('intent')}")
    print(f"Cost: {data.get('cost')}")
    print(f"Credits after: {data.get('credits')}")
    
    # Assertions
    assert data["intent"] != "action_adjust", f"Expected intent NOT to be action_adjust, got {data['intent']}"
    assert data["intent"] in ["update", "question", "setback", "acknowledgment", "drift"], f"Unexpected intent: {data['intent']}"
    assert data["cost"] == 5, f"Expected cost=5, got {data['cost']}"
    
    print("✅ Test 2 PASSED")

def test_adjust_with_invalid_mode():
    """Test 3: adjust:true with mode=turbo -> 422."""
    print("\n=== Test 3: adjust:true with invalid mode=turbo ===")
    token = login()
    
    r = requests.post(
        f"{BASE_URL}/threads/{DEMO_THREAD_ID}/turn",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "Test message",
            "mode": "turbo",
            "adjust": True
        }
    )
    
    print(f"Status: {r.status_code}")
    assert r.status_code == 422, f"Expected 422, got {r.status_code}"
    print("✅ Test 3 PASSED")

def test_adjust_with_unknown_thread():
    """Test 4: unknown thread with adjust:true -> 404."""
    print("\n=== Test 4: adjust:true with unknown thread ===")
    token = login()
    fake_thread_id = "00000000-0000-0000-0000-000000000000"
    
    r = requests.post(
        f"{BASE_URL}/threads/{fake_thread_id}/turn",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "message": "Test message",
            "mode": "normal",
            "adjust": True
        }
    )
    
    print(f"Status: {r.status_code}")
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"
    print("✅ Test 4 PASSED")

def test_adjust_without_token():
    """Test 5: no token -> 401."""
    print("\n=== Test 5: adjust:true without token ===")
    
    r = requests.post(
        f"{BASE_URL}/threads/{DEMO_THREAD_ID}/turn",
        json={
            "message": "Test message",
            "mode": "normal",
            "adjust": True
        }
    )
    
    print(f"Status: {r.status_code}")
    assert r.status_code == 401, f"Expected 401, got {r.status_code}"
    print("✅ Test 5 PASSED")

def test_adjust_as_string():
    """Test 6: adjust as string 'yes' -> 422 or coerced."""
    print("\n=== Test 6: adjust as string 'yes' ===")
    token = login()
    
    # Send raw JSON with adjust as string
    r = requests.post(
        f"{BASE_URL}/threads/{DEMO_THREAD_ID}/turn",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        data='{"message": "Test", "mode": "normal", "adjust": "yes"}'
    )
    
    print(f"Status: {r.status_code}")
    if r.status_code == 422:
        print("Behavior: Pydantic rejects string as boolean -> 422 ✅")
    elif r.status_code == 200:
        data = r.json()
        print(f"Behavior: Coerced to boolean. Intent: {data.get('intent')}")
        # If coerced, "yes" would be truthy -> action_adjust
        if data.get("intent") == "action_adjust":
            print("String 'yes' was coerced to True")
        else:
            print("String 'yes' was coerced to False or ignored")
    else:
        print(f"Unexpected status: {r.status_code} {r.text}")
    
    print("✅ Test 6 COMPLETED (behavior documented)")

if __name__ == "__main__":
    print(f"Testing against: {BASE_URL}")
    print(f"Demo thread: {DEMO_THREAD_ID}")
    print("=" * 60)
    
    # Guard tests (no LLM cost)
    test_adjust_with_invalid_mode()
    test_adjust_with_unknown_thread()
    test_adjust_without_token()
    test_adjust_as_string()
    
    # Real LLM turns (MAX 2)
    print("\n" + "=" * 60)
    print("REAL LLM TURNS (costs real API money)")
    print("=" * 60)
    test_adjust_turn_with_valid_mode()  # LLM turn #1
    test_adjust_omitted()  # LLM turn #2
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED ✅")
    print("=" * 60)
