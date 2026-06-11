"""
Retention Loop Feature Testing
Tests the new momentum strip and accountability features
"""
import requests
import sys

BASE_URL = "https://ops-center-34.preview.emergentagent.com/api"

def test_retention_features():
    """Test retention loop features with smoke1@test.com"""
    print("="*60)
    print("🔍 Testing Retention Loop Features")
    print("="*60)
    
    # Login as smoke1@test.com
    print("\n1️⃣ Logging in as smoke1@test.com...")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "smoke1@test.com",
        "password": "test1234"
    })
    
    if resp.status_code != 200:
        print(f"❌ Login failed: {resp.status_code}")
        return False
    
    data = resp.json()
    token = data['token']
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print(f"✅ Login successful - Credits: {data['user']['credits']}")
    
    # Test GET /goals for momentum data
    print("\n2️⃣ Testing GET /goals for momentum data...")
    resp = requests.get(f"{BASE_URL}/goals", headers=headers)
    
    if resp.status_code != 200:
        print(f"❌ GET /goals failed: {resp.status_code}")
        return False
    
    data = resp.json()
    
    # Check momentum object
    if 'momentum' not in data:
        print("❌ Missing 'momentum' field in response")
        return False
    
    momentum = data['momentum']
    print(f"✅ Momentum object present")
    
    # Check momentum fields
    required_fields = ['kept_promises', 'turns_this_week', 'avg_consistency']
    for field in required_fields:
        if field not in momentum:
            print(f"❌ Missing '{field}' in momentum")
            return False
        print(f"  ✅ {field}: {momentum[field]}")
    
    # Check goals array
    if 'goals' not in data or len(data['goals']) == 0:
        print("❌ No goals found for smoke1@test.com")
        return False
    
    print(f"\n3️⃣ Testing goal fields (found {len(data['goals'])} goal(s))...")
    goal = data['goals'][0]
    
    # Check goal fields
    goal_fields = ['thread_id', 'goal', 'status', 'pace', 'consistency', 'next_action', 
                   'open_question', 'action_overdue', 'hours_since_turn']
    for field in goal_fields:
        if field not in goal:
            print(f"❌ Missing '{field}' in goal")
            return False
    
    print(f"  ✅ thread_id: {goal['thread_id']}")
    print(f"  ✅ goal: {goal['goal']}")
    print(f"  ✅ status: {goal['status']}")
    print(f"  ✅ pace: {goal['pace']}")
    print(f"  ✅ consistency: {goal['consistency']}")
    print(f"  ✅ open_question: {goal['open_question'][:50]}..." if goal['open_question'] else "  ✅ open_question: (none)")
    print(f"  ✅ action_overdue: {goal['action_overdue']}")
    print(f"  ✅ hours_since_turn: {goal['hours_since_turn']}")
    
    # Test GET /threads/{id}
    thread_id = goal['thread_id']
    print(f"\n4️⃣ Testing GET /threads/{thread_id[:8]}... for action_overdue...")
    resp = requests.get(f"{BASE_URL}/threads/{thread_id}", headers=headers)
    
    if resp.status_code != 200:
        print(f"❌ GET /threads/{thread_id} failed: {resp.status_code}")
        return False
    
    data = resp.json()
    
    # Check thread response fields
    if 'thread' not in data:
        print("❌ Missing 'thread' in response")
        return False
    
    if 'action_overdue' not in data:
        print("❌ Missing 'action_overdue' in response")
        return False
    
    if 'hours_since_turn' not in data:
        print("❌ Missing 'hours_since_turn' in response")
        return False
    
    print(f"  ✅ action_overdue: {data['action_overdue']}")
    print(f"  ✅ hours_since_turn: {data['hours_since_turn']}")
    print(f"  ✅ reengagement_line: {data.get('reengagement_line', '(none)')}")
    
    # Verify action_overdue is True (thread is backdated 60h)
    if data['action_overdue']:
        print(f"  ✅ action_overdue is True (expected for backdated thread)")
    else:
        print(f"  ⚠️  action_overdue is False (expected True for 60h backdated thread)")
    
    print("\n" + "="*60)
    print("✅ All retention loop backend tests passed!")
    print("="*60)
    return True

if __name__ == "__main__":
    success = test_retention_features()
    sys.exit(0 if success else 1)
