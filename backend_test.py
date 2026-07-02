#!/usr/bin/env python3
"""
Backend test for SmartDecigen Layer 1-3 batch build (LIVE ANTHROPIC KEY).
STRICT LLM BUDGET: <= 4 calls total (3 planned + 1 spare for genuine retry).
"""
import requests
import json
import uuid
import sys
from datetime import datetime

BASE_URL = "https://founder-reasoning.preview.emergentagent.com/api"

# Track LLM calls globally
LLM_CALLS_USED = 0
MAX_LLM_CALLS = 4

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def assert_eq(actual, expected, msg):
    if actual != expected:
        raise AssertionError(f"{msg}: expected {expected}, got {actual}")

def assert_in(item, container, msg):
    if item not in container:
        raise AssertionError(f"{msg}: {item} not in {container}")

def assert_true(condition, msg):
    if not condition:
        raise AssertionError(f"{msg}: condition is False")

def assert_range(value, min_val, max_val, msg):
    if not (min_val <= value <= max_val):
        raise AssertionError(f"{msg}: {value} not in range [{min_val}, {max_val}]")

def fresh_signup():
    """Create a fresh user account with SIGNUP_CREDITS (50)."""
    email = f"journey_live_{uuid.uuid4().hex[:8]}@test.com"
    password = "TestPass123!"
    resp = requests.post(f"{BASE_URL}/auth/signup", json={
        "email": email,
        "password": password,
        "name": "Test User"
    })
    assert_eq(resp.status_code, 200, "Signup failed")
    data = resp.json()
    token = data["token"]
    user = data["user"]
    log(f"✓ Fresh signup: {email}, credits={user['credits']}")
    return token, user

def test_layer1_live_loop():
    """
    LIVE TEST: Full Layer-1 Decision Intelligence Engine loop with REAL ANTHROPIC KEY.
    LLM BUDGET: 3 calls (start, message, direction).
    """
    global LLM_CALLS_USED
    
    log("\n=== LAYER 1: DECISION INTELLIGENCE ENGINE (LIVE) ===")
    
    # Fresh signup
    token, user = fresh_signup()
    headers = {"Authorization": f"Bearer {token}"}
    initial_credits = user["credits"]
    assert_eq(initial_credits, 50, "SIGNUP_CREDITS should be 50")
    
    # LLM CALL #1: POST /api/journey/start
    log("\n--- LLM CALL #1: POST /api/journey/start ---")
    objective = "Grow my Jaipur boutique hotel from 40% to 75% occupancy in 9 months, I depend fully on OTAs and their 22% commission is killing me."
    resp = requests.post(f"{BASE_URL}/journey/start", headers=headers, json={"objective": objective})
    assert_eq(resp.status_code, 200, "journey/start should return 200")
    LLM_CALLS_USED += 1
    log(f"✓ LLM CALL #{LLM_CALLS_USED} completed (journey/start)")
    
    turn1 = resp.json()
    
    # CRITICAL ASSERTIONS FOR TURN 1
    log("\n--- Turn 1 Assertions ---")
    
    # 1. reasoning is an object
    assert_true(isinstance(turn1.get("reasoning"), dict), "reasoning must be an object")
    reasoning = turn1["reasoning"]
    log(f"✓ reasoning is an object")
    
    # 2. reasoning.uncertainty has EXACTLY 9 keys (NO hidden_desire)
    uncertainty = reasoning.get("uncertainty", {})
    assert_eq(len(uncertainty), 9, "reasoning.uncertainty must have EXACTLY 9 keys (hidden_desire stripped)")
    assert_true("hidden_desire" not in uncertainty, "hidden_desire must NOT be in public uncertainty map")
    log(f"✓ reasoning.uncertainty has EXACTLY 9 keys (hidden_desire stripped)")
    log(f"  Keys: {list(uncertainty.keys())}")
    
    # 3. Every dim has int score 0..100 + note
    for dim, val in uncertainty.items():
        assert_true(isinstance(val, dict), f"{dim} must be a dict")
        assert_true(isinstance(val.get("score"), int), f"{dim}.score must be int")
        assert_range(val["score"], 0, 100, f"{dim}.score must be 0-100")
        assert_true(isinstance(val.get("note"), str), f"{dim}.note must be str")
    log(f"✓ Every dim has int score 0..100 + note")
    
    # Log exact scores for reporting
    log("\n  Turn 1 Uncertainty Scores:")
    for dim, val in uncertainty.items():
        log(f"    {dim}: {val['score']} - {val['note'][:50]}...")
    
    # 4. biggest_uncertainty and question_target are among the 9 dims
    biggest = reasoning.get("biggest_uncertainty")
    question_target = reasoning.get("question_target")
    assert_in(biggest, uncertainty, "biggest_uncertainty must be one of the 9 dims")
    assert_in(question_target, uncertainty, "question_target must be one of the 9 dims")
    log(f"✓ biggest_uncertainty={biggest}, question_target={question_target} (both in 9 dims)")
    
    # 5. question_rationale non-empty
    question_rationale = reasoning.get("question_rationale", "")
    assert_true(len(question_rationale) > 0, "question_rationale must be non-empty")
    log(f"✓ question_rationale non-empty: '{question_rationale[:60]}...'")
    
    # 6. sufficient is boolean
    sufficient = reasoning.get("sufficient")
    assert_true(isinstance(sufficient, bool), "sufficient must be boolean")
    log(f"✓ sufficient is boolean: {sufficient}")
    
    # 7. assumptions_detected is list
    assumptions = reasoning.get("assumptions_detected", [])
    assert_true(isinstance(assumptions, list), "assumptions_detected must be list")
    log(f"✓ assumptions_detected is list with {len(assumptions)} items")
    
    # 8. decision_type in allowed values
    decision_type = reasoning.get("decision_type")
    allowed_types = ["idea", "validation", "execution", "scaling", "crisis", "other"]
    assert_in(decision_type, allowed_types, "decision_type must be in allowed values")
    log(f"✓ decision_type={decision_type} (valid)")
    
    # 9. reversible is true/false/null
    reversible = reasoning.get("reversible")
    assert_true(reversible in [True, False, None], "reversible must be true/false/null")
    log(f"✓ reversible={reversible}")
    
    # 10. expert_lenses is list
    expert_lenses = reasoning.get("expert_lenses", [])
    assert_true(isinstance(expert_lenses, list), "expert_lenses must be list")
    log(f"✓ expert_lenses is list: {expert_lenses}")
    
    # 11. dim_order (9) + dim_labels present
    dim_order = reasoning.get("dim_order", [])
    dim_labels = reasoning.get("dim_labels", {})
    assert_eq(len(dim_order), 9, "dim_order must have 9 items")
    assert_true(len(dim_labels) >= 9, "dim_labels must have at least 9 items")
    log(f"✓ dim_order has 9 items, dim_labels present")
    
    # 12. confidence int > 0
    confidence = turn1.get("confidence")
    assert_true(isinstance(confidence, int), "confidence must be int")
    assert_true(confidence > 0, "confidence must be > 0")
    log(f"✓ confidence={confidence} (int > 0)")
    
    # 13. confidence_source == "reasoning"
    confidence_source = turn1.get("confidence_source")
    assert_eq(confidence_source, "reasoning", "confidence_source must be 'reasoning'")
    log(f"✓ confidence_source='reasoning'")
    
    # 14. cost >= 1
    cost1 = turn1.get("cost")
    assert_true(cost1 >= 1, "cost must be >= 1")
    log(f"✓ cost={cost1} (>= 1)")
    
    # 15. credits dropped from 50
    credits_after_turn1 = turn1.get("credits")
    assert_true(credits_after_turn1 < 50, "credits must have dropped from 50")
    log(f"✓ credits dropped: 50 -> {credits_after_turn1}")
    
    # LLM CALL #2: POST /api/journey/message
    log("\n--- LLM CALL #2: POST /api/journey/message ---")
    message = "I get 900 room-nights a month, ADR 4200, direct bookings are only 8%, I have 6 staff, 3L cash buffer, and honestly I do not know digital marketing at all."
    resp = requests.post(f"{BASE_URL}/journey/message", headers=headers, json={"message": message})
    assert_eq(resp.status_code, 200, "journey/message should return 200")
    LLM_CALLS_USED += 1
    log(f"✓ LLM CALL #{LLM_CALLS_USED} completed (journey/message)")
    
    turn2 = resp.json()
    
    # CRITICAL ASSERTIONS FOR TURN 2
    log("\n--- Turn 2 Assertions ---")
    
    # 1. confidence CHANGED vs turn 1 (any direction)
    confidence2 = turn2.get("confidence")
    assert_true(confidence2 != confidence, "confidence must have CHANGED from turn 1")
    log(f"✓ confidence CHANGED: {confidence} -> {confidence2}")
    
    # 2. reasoning updated (at least one uncertainty dim score differs)
    reasoning2 = turn2.get("reasoning", {})
    uncertainty2 = reasoning2.get("uncertainty", {})
    changed_dims = []
    for dim in uncertainty:
        if dim in uncertainty2:
            if uncertainty[dim]["score"] != uncertainty2[dim]["score"]:
                changed_dims.append(dim)
    assert_true(len(changed_dims) > 0, "At least one uncertainty dim score must differ from turn 1")
    log(f"✓ Uncertainty map updated: {len(changed_dims)} dims changed: {changed_dims}")
    
    # Log turn 2 scores
    log("\n  Turn 2 Uncertainty Scores:")
    for dim, val in uncertainty2.items():
        log(f"    {dim}: {val['score']} (was {uncertainty.get(dim, {}).get('score', 'N/A')})")
    
    # 3. messages length 4 (2 from start + 2 from message)
    messages = turn2.get("messages", [])
    assert_eq(len(messages), 4, "messages must have length 4")
    log(f"✓ messages length=4")
    
    # 4. credits dropped again
    credits_after_turn2 = turn2.get("credits")
    assert_true(credits_after_turn2 < credits_after_turn1, "credits must have dropped again")
    cost2 = turn2.get("cost")
    log(f"✓ credits dropped again: {credits_after_turn1} -> {credits_after_turn2} (cost={cost2})")
    
    # LLM CALL #3: POST /api/journey/direction
    log("\n--- LLM CALL #3: POST /api/journey/direction ---")
    resp = requests.post(f"{BASE_URL}/journey/direction", headers=headers)
    assert_eq(resp.status_code, 200, "journey/direction should return 200")
    LLM_CALLS_USED += 1
    log(f"✓ LLM CALL #{LLM_CALLS_USED} completed (journey/direction)")
    
    turn3 = resp.json()
    
    # CRITICAL ASSERTIONS FOR TURN 3
    log("\n--- Turn 3 (Direction) Assertions ---")
    
    direction = turn3.get("direction")
    assert_true(isinstance(direction, dict), "direction must be an object")
    log(f"✓ direction is an object")
    
    # 1. decision (non-empty string)
    decision = direction.get("decision", "")
    assert_true(len(decision) > 0, "direction.decision must be non-empty")
    log(f"✓ decision: '{decision[:80]}...'")
    
    # 2. goal
    goal = direction.get("goal", "")
    assert_true(len(goal) > 0, "direction.goal must be non-empty")
    log(f"✓ goal: '{goal[:80]}...'")
    
    # 3. blockers (2-5)
    blockers = direction.get("blockers", [])
    assert_range(len(blockers), 2, 5, "direction.blockers must have 2-5 items")
    log(f"✓ blockers: {len(blockers)} items")
    
    # 4. highest_leverage
    highest_leverage = direction.get("highest_leverage", "")
    assert_true(len(highest_leverage) > 0, "direction.highest_leverage must be non-empty")
    log(f"✓ highest_leverage: '{highest_leverage[:80]}...'")
    
    # 5. success_probability (int 0-100)
    success_probability = direction.get("success_probability")
    assert_true(isinstance(success_probability, int), "success_probability must be int")
    assert_range(success_probability, 0, 100, "success_probability must be 0-100")
    log(f"✓ success_probability: {success_probability}")
    
    # 6. probability_rationale
    probability_rationale = direction.get("probability_rationale", "")
    assert_true(len(probability_rationale) > 0, "probability_rationale must be non-empty")
    log(f"✓ probability_rationale: '{probability_rationale[:80]}...'")
    
    # 7. risks (2-5)
    risks = direction.get("risks", [])
    assert_range(len(risks), 2, 5, "direction.risks must have 2-5 items")
    log(f"✓ risks: {len(risks)} items")
    
    # 8. missing_info (2-5)
    missing_info = direction.get("missing_info", [])
    assert_range(len(missing_info), 2, 5, "direction.missing_info must have 2-5 items")
    log(f"✓ missing_info: {len(missing_info)} items")
    
    # 9. trade_offs (2-4 non-empty)
    trade_offs = direction.get("trade_offs", [])
    assert_range(len(trade_offs), 2, 4, "direction.trade_offs must have 2-4 items")
    for i, to in enumerate(trade_offs):
        assert_true(len(to) > 0, f"trade_offs[{i}] must be non-empty")
    log(f"✓ trade_offs: {len(trade_offs)} items (all non-empty)")
    
    # 10. first_moves (2-4 non-empty)
    first_moves = direction.get("first_moves", [])
    assert_range(len(first_moves), 2, 4, "direction.first_moves must have 2-4 items")
    for i, fm in enumerate(first_moves):
        assert_true(len(fm) > 0, f"first_moves[{i}] must be non-empty")
    log(f"✓ first_moves: {len(first_moves)} items (all non-empty)")
    
    # 11. learning_loop.signals (2-4)
    learning_loop = direction.get("learning_loop", {})
    signals = learning_loop.get("signals", [])
    assert_range(len(signals), 2, 4, "learning_loop.signals must have 2-4 items")
    log(f"✓ learning_loop.signals: {len(signals)} items")
    
    # 12. learning_loop.assumptions_to_test (2-3)
    assumptions_to_test = learning_loop.get("assumptions_to_test", [])
    assert_range(len(assumptions_to_test), 2, 3, "learning_loop.assumptions_to_test must have 2-3 items")
    log(f"✓ learning_loop.assumptions_to_test: {len(assumptions_to_test)} items")
    
    # 13. stage == "refine"
    stage = turn3.get("stage")
    assert_eq(stage, "refine", "stage must be 'refine'")
    log(f"✓ stage='refine'")
    
    # 14. has_direction == true
    has_direction = turn3.get("has_direction")
    assert_eq(has_direction, True, "has_direction must be true")
    log(f"✓ has_direction=true")
    
    # 15. cost >= 1, credits dropped
    cost3 = turn3.get("cost")
    assert_true(cost3 >= 1, "cost must be >= 1")
    credits_after_turn3 = turn3.get("credits")
    assert_true(credits_after_turn3 < credits_after_turn2, "credits must have dropped")
    log(f"✓ cost={cost3}, credits: {credits_after_turn2} -> {credits_after_turn3}")
    
    log("\n✅ LAYER 1 LIVE LOOP: ALL ASSERTIONS PASSED")
    log(f"   Total LLM calls used: {LLM_CALLS_USED}/{MAX_LLM_CALLS}")
    log(f"   Credits used: {initial_credits - credits_after_turn3} (50 -> {credits_after_turn3})")
    
    return token, direction, turn3

def test_layer3_share_and_reset(token, direction, journey_view):
    """
    FREE TESTS: Share direction, public GET, reset.
    NO LLM CALLS.
    """
    global LLM_CALLS_USED
    
    log("\n=== LAYER 3: VIRALITY (FREE) ===")
    headers = {"Authorization": f"Bearer {token}"}
    
    # FREE: POST /api/share/direction
    log("\n--- FREE: POST /api/share/direction ---")
    resp = requests.post(f"{BASE_URL}/share/direction", headers=headers)
    assert_eq(resp.status_code, 200, "share/direction should return 200")
    share_data = resp.json()
    
    share_id = share_data.get("share_id")
    path = share_data.get("path")
    assert_true(len(share_id) > 0, "share_id must be non-empty")
    assert_eq(path, f"/d/{share_id}", "path must be /d/<share_id>")
    log(f"✓ share_id={share_id}, path={path}")
    
    # FREE: Public GET /api/share/{id} (NO AUTH)
    log("\n--- FREE: Public GET /api/share/{id} (no auth) ---")
    resp = requests.get(f"{BASE_URL}/share/{share_id}")
    assert_eq(resp.status_code, 200, "public share GET should return 200")
    card_data = resp.json()
    
    card = card_data.get("card", {})
    
    # 1. card.decision == direction.decision
    card_decision = card.get("decision", "")
    assert_eq(card_decision, direction.get("decision"), "card.decision must match direction.decision")
    log(f"✓ card.decision matches direction.decision")
    
    # 2. card.confidence is int
    card_confidence = card.get("confidence")
    assert_true(isinstance(card_confidence, int), "card.confidence must be int")
    log(f"✓ card.confidence={card_confidence} (int)")
    
    # 3. card.trade_offs and card.first_moves present
    assert_true("trade_offs" in card, "card must have trade_offs")
    assert_true("first_moves" in card, "card must have first_moves")
    log(f"✓ card.trade_offs and card.first_moves present")
    
    # 4. Privacy check: NO model/messages/objective/hidden_desire
    assert_true("model" not in card_data, "card must NOT contain 'model'")
    assert_true("messages" not in card_data, "card must NOT contain 'messages'")
    assert_true("objective" not in card_data, "card must NOT contain 'objective'")
    assert_true("hidden_desire" not in card_data, "card must NOT contain 'hidden_desire'")
    log(f"✓ Privacy check: NO model/messages/objective/hidden_desire in response")
    
    # FREE: POST /api/journey/reset
    log("\n--- FREE: POST /api/journey/reset ---")
    resp = requests.post(f"{BASE_URL}/journey/reset", headers=headers)
    assert_eq(resp.status_code, 200, "journey/reset should return 200")
    reset_data = resp.json()
    
    # 1. reasoning null
    reset_reasoning = reset_data.get("reasoning")
    assert_eq(reset_reasoning, None, "reasoning must be null after reset")
    log(f"✓ reasoning=null")
    
    # 2. confidence 0
    reset_confidence = reset_data.get("confidence")
    assert_eq(reset_confidence, 0, "confidence must be 0 after reset")
    log(f"✓ confidence=0")
    
    # 3. confidence_source "completeness"
    reset_confidence_source = reset_data.get("confidence_source")
    assert_eq(reset_confidence_source, "completeness", "confidence_source must be 'completeness' after reset")
    log(f"✓ confidence_source='completeness'")
    
    # 4. started false
    reset_started = reset_data.get("started")
    assert_eq(reset_started, False, "started must be false after reset")
    log(f"✓ started=false")
    
    log("\n✅ LAYER 3 SHARE & RESET: ALL ASSERTIONS PASSED")
    log(f"   Total LLM calls used: {LLM_CALLS_USED}/{MAX_LLM_CALLS} (no additional calls)")

def main():
    try:
        log("=" * 80)
        log("SMARTDECIGEN BACKEND TEST - LAYER 1-3 BATCH BUILD (LIVE)")
        log("STRICT LLM BUDGET: <= 4 calls total")
        log("=" * 80)
        
        # Test Layer 1 (3 LLM calls)
        token, direction, journey_view = test_layer1_live_loop()
        
        # Test Layer 3 (0 LLM calls)
        test_layer3_share_and_reset(token, direction, journey_view)
        
        log("\n" + "=" * 80)
        log("✅ ALL TESTS PASSED")
        log(f"   Total LLM calls used: {LLM_CALLS_USED}/{MAX_LLM_CALLS}")
        log("=" * 80)
        
        return 0
        
    except AssertionError as e:
        log(f"\n❌ TEST FAILED: {e}")
        log(f"   LLM calls used before failure: {LLM_CALLS_USED}/{MAX_LLM_CALLS}")
        return 1
    except Exception as e:
        log(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        log(f"   LLM calls used before error: {LLM_CALLS_USED}/{MAX_LLM_CALLS}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
