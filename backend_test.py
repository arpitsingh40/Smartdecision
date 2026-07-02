"""Backend testing for Sprint 2a: Brain reasoning port + cross-founder benchmarks.

Test plan:
1. LLM#1 - BENCHMARK AGGREGATION: Fresh signup -> journey/start -> verify Mongo benchmarks aggregation
2. LLM#2 - BRAIN REASONING PORT: Fresh signup -> brain/ask -> verify reasoning structure
3. FREE - HISTORY CLEAN: GET brain/decisions -> verify no reasoning/strategic_alignment keys
4. FREE - UNIT TESTS: Python unit tests for benchmarks.py functions

Total LLM budget: <= 3 calls (2 planned + 1 spare)
"""
import sys
import os
import json
import requests
from datetime import datetime, timezone
from pymongo import MongoClient

# Add backend to path for unit tests
sys.path.insert(0, '/app/backend')

# Backend URL from frontend/.env
BACKEND_URL = "https://founder-reasoning.preview.emergentagent.com/api"

# MongoDB connection
MONGO_URL = "mongodb://localhost:27017"
DB_NAME = "test_database"

def get_mongo():
    """Get MongoDB client and database."""
    client = MongoClient(MONGO_URL)
    return client, client[DB_NAME]

def signup_user(email):
    """Create a fresh user account."""
    url = f"{BACKEND_URL}/auth/signup"
    payload = {"email": email, "password": "TestPass123!", "name": "Test User"}
    resp = requests.post(url, json=payload)
    assert resp.status_code == 200, f"Signup failed: {resp.status_code} {resp.text}"
    data = resp.json()
    return data["token"], data["user"]["id"]

def test_benchmark_aggregation():
    """LLM#1 - BENCHMARK AGGREGATION ACROSS FOUNDERS.
    
    Fresh signup A -> POST /api/journey/start with cloud kitchen objective -> 200.
    Then inspect Mongo: at least one cloud-kitchen metric doc should have count=2 
    with TWO DISTINCT uid values (two founders aggregated, no double count).
    """
    print("\n" + "="*80)
    print("TEST 1: LLM#1 - BENCHMARK AGGREGATION ACROSS FOUNDERS")
    print("="*80)
    
    # Fresh signup
    email = f"benchmark_test_{int(datetime.now().timestamp())}@cloudkitchen.com"
    token, user_id = signup_user(email)
    print(f"✓ Fresh signup: {email}")
    
    # POST /api/journey/start with cloud kitchen objective
    url = f"{BACKEND_URL}/journey/start"
    headers = {"Authorization": f"Bearer {token}"}
    objective = "I run a cloud kitchen in Mumbai doing 900 orders a month at 320 rupees average order value and want to hit 15L monthly revenue in a year."
    payload = {"objective": objective}
    
    print(f"→ POST /api/journey/start with cloud kitchen objective...")
    resp = requests.post(url, json=payload, headers=headers)
    assert resp.status_code == 200, f"Journey start failed: {resp.status_code} {resp.text}"
    data = resp.json()
    print(f"✓ 200 response, cost={data.get('cost')}, credits={data.get('credits')}")
    
    # Inspect MongoDB benchmarks collection
    mongo_client, db = get_mongo()
    benchmarks_col = db.benchmarks
    
    print("\n→ Inspecting MongoDB benchmarks collection...")
    cloud_kitchen_docs = list(benchmarks_col.find({"industry": "cloud-kitchen"}))
    
    print(f"\nFound {len(cloud_kitchen_docs)} cloud-kitchen benchmark docs:")
    for doc in cloud_kitchen_docs:
        metric = doc.get("metric")
        count = doc.get("count", 0)
        samples = doc.get("samples", [])
        uid_values = [s.get("uid") for s in samples]
        distinct_uids = len(set(uid_values))
        
        print(f"  - metric: {metric}, count: {count}, distinct UIDs: {distinct_uids}")
        
        # Check for at least one metric with count >= 2 and TWO DISTINCT uids
        if count >= 2 and distinct_uids >= 2:
            print(f"    ✓ PASS: {metric} has count={count} with {distinct_uids} distinct UIDs (aggregation working)")
            # Verify the UIDs are actually different
            print(f"    UIDs: {uid_values[:5]}")  # Show first 5
    
    # Report all (industry, metric, count) rows
    print("\n→ All benchmark rows (industry, metric, count):")
    all_benchmarks = list(benchmarks_col.find({}, {"industry": 1, "metric": 1, "count": 1, "_id": 0}))
    for b in all_benchmarks:
        print(f"  ({b.get('industry')}, {b.get('metric')}, {b.get('count')})")
    
    # Verify at least one cloud-kitchen metric has count >= 2
    has_aggregation = any(
        doc.get("count", 0) >= 2 and len(set(s.get("uid") for s in doc.get("samples", []))) >= 2
        for doc in cloud_kitchen_docs
    )
    
    assert has_aggregation, "FAIL: No cloud-kitchen metric has count >= 2 with distinct UIDs"
    print("\n✅ TEST 1 PASSED: Benchmark aggregation working (count >= 2, distinct UIDs)")
    
    mongo_client.close()
    return token, user_id

def test_brain_reasoning_port(token=None, user_id=None):
    """LLM#2 - BRAIN REASONING PORT.
    
    Fresh signup B -> POST /api/brain/ask with cloud kitchen question -> 200.
    Assert ALL:
    - response HAS 'reasoning' object
    - reasoning.uncertainty has EXACTLY 9 keys (NO hidden_desire)
    - reasoning has NO 'hidden_desire' key at all
    - biggest_uncertainty + question_target among the 9
    - question_rationale non-empty
    - sufficient is bool
    - dim_order (9 items) + dim_labels present
    - assumptions_detected is a list
    - decision_type valid
    - response does NOT contain 'strategic_alignment'
    - existing contract intact: next_action, hook, key_takeaway, mode, sharpening_question, decision_id, session_id, cost >= 1
    """
    print("\n" + "="*80)
    print("TEST 2: LLM#2 - BRAIN REASONING PORT")
    print("="*80)
    
    # Fresh signup if not provided
    if not token:
        email = f"brain_test_{int(datetime.now().timestamp())}@cloudkitchen.com"
        token, user_id = signup_user(email)
        print(f"✓ Fresh signup: {email}")
    else:
        print(f"✓ Using existing user: {user_id}")
    
    # POST /api/brain/ask
    url = f"{BACKEND_URL}/brain/ask"
    headers = {"Authorization": f"Bearer {token}"}
    question = "Should I spend 50000 rupees a month on Swiggy ads to grow my cloud kitchen orders, margins are thin?"
    payload = {"question": question}
    
    print(f"→ POST /api/brain/ask with question...")
    resp = requests.post(url, json=payload, headers=headers)
    assert resp.status_code == 200, f"Brain ask failed: {resp.status_code} {resp.text}"
    data = resp.json()
    
    print(f"✓ 200 response, cost={data.get('cost')}, mode={data.get('mode')}")
    
    # CRITICAL ASSERTIONS
    print("\n→ Verifying reasoning structure...")
    
    # 1. Response HAS 'reasoning' object
    assert "reasoning" in data, "FAIL: response does NOT contain 'reasoning' key"
    reasoning = data["reasoning"]
    assert isinstance(reasoning, dict), "FAIL: reasoning is not a dict"
    print("  ✓ response HAS 'reasoning' object")
    
    # 2. reasoning.uncertainty has EXACTLY 9 keys (NO hidden_desire)
    assert "uncertainty" in reasoning, "FAIL: reasoning does NOT contain 'uncertainty'"
    uncertainty = reasoning["uncertainty"]
    assert isinstance(uncertainty, dict), "FAIL: uncertainty is not a dict"
    unc_keys = list(uncertainty.keys())
    print(f"  → uncertainty keys ({len(unc_keys)}): {unc_keys}")
    assert len(unc_keys) == 9, f"FAIL: uncertainty has {len(unc_keys)} keys, expected EXACTLY 9"
    assert "hidden_desire" not in unc_keys, "FAIL: uncertainty contains 'hidden_desire' (should be stripped)"
    print("  ✓ reasoning.uncertainty has EXACTLY 9 keys (NO hidden_desire)")
    
    # 3. reasoning has NO 'hidden_desire' key at all
    assert "hidden_desire" not in reasoning, "FAIL: reasoning contains 'hidden_desire' key (should be stripped)"
    print("  ✓ reasoning has NO 'hidden_desire' key at all")
    
    # 4. biggest_uncertainty + question_target among the 9
    biggest = reasoning.get("biggest_uncertainty")
    question_target = reasoning.get("question_target")
    assert biggest in unc_keys, f"FAIL: biggest_uncertainty '{biggest}' not in uncertainty keys"
    assert question_target in unc_keys, f"FAIL: question_target '{question_target}' not in uncertainty keys"
    print(f"  ✓ biggest_uncertainty='{biggest}' + question_target='{question_target}' among the 9")
    
    # 5. question_rationale non-empty
    question_rationale = reasoning.get("question_rationale", "")
    assert isinstance(question_rationale, str) and len(question_rationale) > 0, "FAIL: question_rationale is empty"
    print(f"  ✓ question_rationale non-empty (len={len(question_rationale)})")
    
    # 6. sufficient is bool
    sufficient = reasoning.get("sufficient")
    assert isinstance(sufficient, bool), f"FAIL: sufficient is not bool, got {type(sufficient)}"
    print(f"  ✓ sufficient is bool ({sufficient})")
    
    # 7. dim_order (9 items) + dim_labels present
    dim_order = reasoning.get("dim_order", [])
    dim_labels = reasoning.get("dim_labels", {})
    assert isinstance(dim_order, list) and len(dim_order) == 9, f"FAIL: dim_order has {len(dim_order)} items, expected 9"
    assert isinstance(dim_labels, dict) and len(dim_labels) >= 9, f"FAIL: dim_labels has {len(dim_labels)} items, expected >= 9"
    print(f"  ✓ dim_order has 9 items, dim_labels present")
    
    # 8. assumptions_detected is a list
    assumptions = reasoning.get("assumptions_detected")
    assert isinstance(assumptions, list), f"FAIL: assumptions_detected is not a list, got {type(assumptions)}"
    print(f"  ✓ assumptions_detected is a list (len={len(assumptions)})")
    
    # 9. decision_type valid
    decision_type = reasoning.get("decision_type")
    valid_types = ["idea", "validation", "execution", "scaling", "crisis", "other"]
    assert decision_type in valid_types, f"FAIL: decision_type '{decision_type}' not in {valid_types}"
    print(f"  ✓ decision_type='{decision_type}' (valid)")
    
    # 10. response does NOT contain 'strategic_alignment'
    assert "strategic_alignment" not in data, "FAIL: response contains 'strategic_alignment' (should be stripped)"
    print("  ✓ response does NOT contain 'strategic_alignment'")
    
    # 11. existing contract intact
    assert "next_action" in data and data["next_action"], "FAIL: next_action missing or empty"
    assert "hook" in data and data["hook"], "FAIL: hook missing or empty"
    assert "key_takeaway" in data and data["key_takeaway"], "FAIL: key_takeaway missing or empty"
    assert "mode" in data and data["mode"] in ["answer", "decide", "plan"], f"FAIL: mode '{data.get('mode')}' invalid"
    assert "sharpening_question" in data, "FAIL: sharpening_question missing"
    assert "decision_id" in data and data["decision_id"], "FAIL: decision_id missing or empty"
    assert "session_id" in data and data["session_id"], "FAIL: session_id missing or empty"
    assert "cost" in data and data["cost"] >= 1, f"FAIL: cost {data.get('cost')} < 1"
    print(f"  ✓ existing contract intact: next_action, hook, key_takeaway, mode={data['mode']}, decision_id, session_id, cost={data['cost']}")
    
    print("\n✅ TEST 2 PASSED: Brain reasoning port working correctly")
    
    return token, user_id, data["decision_id"]

def test_history_clean(token, user_id, decision_id):
    """FREE - HISTORY CLEAN.
    
    GET /api/brain/decisions for user -> rows do NOT contain keys 'reasoning' nor 'strategic_alignment'.
    Then check Mongo decisions doc for that decision_id: it DOES contain 'reasoning' (stored server-side).
    """
    print("\n" + "="*80)
    print("TEST 3: FREE - HISTORY CLEAN")
    print("="*80)
    
    # GET /api/brain/decisions
    url = f"{BACKEND_URL}/brain/decisions"
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"→ GET /api/brain/decisions...")
    resp = requests.get(url, headers=headers)
    assert resp.status_code == 200, f"Get decisions failed: {resp.status_code} {resp.text}"
    data = resp.json()
    
    decisions = data.get("decisions", [])
    print(f"✓ 200 response, {len(decisions)} decisions returned")
    
    # Verify NO decision contains 'reasoning' or 'strategic_alignment'
    for i, dec in enumerate(decisions):
        assert "reasoning" not in dec, f"FAIL: decision {i} contains 'reasoning' key (should be stripped from history)"
        assert "strategic_alignment" not in dec, f"FAIL: decision {i} contains 'strategic_alignment' key (should be stripped)"
    
    print(f"  ✓ All {len(decisions)} decisions do NOT contain 'reasoning' or 'strategic_alignment' keys")
    
    # Check Mongo: decision doc DOES contain 'reasoning'
    mongo_client, db = get_mongo()
    decisions_col = db.decisions
    
    print(f"\n→ Checking MongoDB decisions collection for decision_id={decision_id}...")
    mongo_doc = decisions_col.find_one({"id": decision_id})
    assert mongo_doc is not None, f"FAIL: decision {decision_id} not found in MongoDB"
    
    assert "reasoning" in mongo_doc, "FAIL: MongoDB decision doc does NOT contain 'reasoning' (should be stored server-side)"
    reasoning = mongo_doc["reasoning"]
    assert reasoning is not None, "FAIL: MongoDB decision doc has reasoning=None"
    print(f"  ✓ MongoDB decision doc DOES contain 'reasoning' (stored server-side, may include hidden_desire)")
    
    # Check if hidden_desire is present in the stored reasoning
    if isinstance(reasoning, dict) and "hidden_desire" in reasoning:
        print(f"  ✓ MongoDB reasoning contains 'hidden_desire' (full trace stored server-side)")
    
    print("\n✅ TEST 3 PASSED: History clean (reasoning stripped from API, stored in Mongo)")
    
    mongo_client.close()

def test_unit_tests():
    """FREE - UNIT TESTS (python, no HTTP).
    
    sys.path.insert(0,'/app/backend'); from benchmarks import ingest_facts, benchmark_digest, normalize_facts, _uid_hash.
    
    Call ingest_facts('unit-test-user','cloud-kitchen',[{'metric':'monthly-orders','value':500,'unit':'orders'}], now) 
    then AGAIN with value 600: the monthly-orders doc count must increase by exactly 1 total across both calls 
    (replace, not double count) and the sample for _uid_hash('unit-test-user') must show value 600.
    
    benchmark_digest('cloud-kitchen') must contain 'monthly-orders' with the correct n and the phrase 'EARLY SIGNAL' while n<5.
    
    normalize_facts({}) -> ("", []); normalize_facts({'industry':'X','facts':[{'metric':'','value':'abc'}]}) -> industry normalized, facts empty.
    
    CLEANUP after: pull the 'unit-test-user' sample from the monthly-orders doc and decrement its count so real data stays clean.
    """
    print("\n" + "="*80)
    print("TEST 4: FREE - UNIT TESTS (benchmarks.py)")
    print("="*80)
    
    from benchmarks import ingest_facts, benchmark_digest, normalize_facts, _uid_hash
    
    mongo_client, db = get_mongo()
    benchmarks_col = db.benchmarks
    
    test_user = "unit-test-user"
    test_uid = _uid_hash(test_user)
    industry = "cloud-kitchen"
    metric = "monthly-orders"
    now = datetime.now(timezone.utc)
    
    print(f"→ Testing ingest_facts with user='{test_user}', uid_hash='{test_uid}'...")
    
    # Get initial count
    doc_before = benchmarks_col.find_one({"industry": industry, "metric": metric})
    count_before = doc_before.get("count", 0) if doc_before else 0
    print(f"  Initial count for {metric}: {count_before}")
    
    # Call ingest_facts with value 500
    print(f"  → ingest_facts(value=500)...")
    written1 = ingest_facts(test_user, industry, [{"metric": metric, "value": 500, "unit": "orders"}], now)
    assert written1 == 1, f"FAIL: ingest_facts returned {written1}, expected 1"
    
    doc_after1 = benchmarks_col.find_one({"industry": industry, "metric": metric})
    count_after1 = doc_after1.get("count", 0)
    samples_after1 = doc_after1.get("samples", [])
    test_sample1 = next((s for s in samples_after1 if s.get("uid") == test_uid), None)
    
    assert test_sample1 is not None, f"FAIL: test user sample not found after first ingest"
    assert test_sample1.get("value") == 500, f"FAIL: test sample value is {test_sample1.get('value')}, expected 500"
    print(f"  ✓ After first ingest: count={count_after1}, test sample value=500")
    
    # Call ingest_facts AGAIN with value 600 (should REPLACE, not double count)
    print(f"  → ingest_facts(value=600) - should REPLACE, not double count...")
    written2 = ingest_facts(test_user, industry, [{"metric": metric, "value": 600, "unit": "orders"}], now)
    assert written2 == 1, f"FAIL: ingest_facts returned {written2}, expected 1"
    
    doc_after2 = benchmarks_col.find_one({"industry": industry, "metric": metric})
    count_after2 = doc_after2.get("count", 0)
    samples_after2 = doc_after2.get("samples", [])
    test_sample2 = next((s for s in samples_after2 if s.get("uid") == test_uid), None)
    
    # Count should increase by exactly 1 total (not 2)
    count_increase = count_after2 - count_before
    assert count_increase == 1, f"FAIL: count increased by {count_increase}, expected exactly 1 (replace, not double count)"
    assert test_sample2 is not None, f"FAIL: test user sample not found after second ingest"
    assert test_sample2.get("value") == 600, f"FAIL: test sample value is {test_sample2.get('value')}, expected 600 (replaced)"
    print(f"  ✓ After second ingest: count={count_after2} (increased by {count_increase}), test sample value=600 (REPLACED)")
    
    # Test benchmark_digest
    print(f"\n→ Testing benchmark_digest('{industry}')...")
    digest = benchmark_digest(industry)
    assert isinstance(digest, str) and len(digest) > 0, "FAIL: benchmark_digest returned empty string"
    assert metric in digest, f"FAIL: digest does not contain '{metric}'"
    
    # Check for 'EARLY SIGNAL' phrase when n < 5
    if count_after2 < 5:
        assert "EARLY SIGNAL" in digest, f"FAIL: digest does not contain 'EARLY SIGNAL' when n={count_after2} < 5"
        print(f"  ✓ digest contains '{metric}' with n={count_after2} and phrase 'EARLY SIGNAL' (n < 5)")
    else:
        print(f"  ✓ digest contains '{metric}' with n={count_after2}")
    
    print(f"\n  Digest preview:\n{digest[:500]}...")
    
    # Test normalize_facts
    print(f"\n→ Testing normalize_facts...")
    
    # Empty dict
    ind1, facts1 = normalize_facts({})
    assert ind1 == "" and facts1 == [], f"FAIL: normalize_facts({{}}) returned ({ind1}, {facts1}), expected ('', [])"
    print(f"  ✓ normalize_facts({{}}) -> ('', [])")
    
    # Invalid facts
    ind2, facts2 = normalize_facts({"industry": "X", "facts": [{"metric": "", "value": "abc"}]})
    assert ind2 == "x", f"FAIL: industry not normalized, got '{ind2}'"
    assert facts2 == [], f"FAIL: facts not empty, got {facts2}"
    print(f"  ✓ normalize_facts({{industry:'X', facts:[{{metric:'', value:'abc'}}]}}) -> ('{ind2}', [])")
    
    # Valid facts
    ind3, facts3 = normalize_facts({"industry": "Cloud Kitchen", "facts": [{"metric": "monthly-orders", "value": 700, "unit": "orders"}]})
    assert ind3 == "cloud-kitchen", f"FAIL: industry not normalized, got '{ind3}'"
    assert len(facts3) == 1, f"FAIL: facts length {len(facts3)}, expected 1"
    assert facts3[0]["metric"] == "monthly-orders", f"FAIL: metric not normalized"
    assert facts3[0]["value"] == 700, f"FAIL: value not preserved"
    print(f"  ✓ normalize_facts({{industry:'Cloud Kitchen', facts:[...]}}) -> ('{ind3}', [{facts3[0]}])")
    
    # CLEANUP: remove the test user sample
    print(f"\n→ CLEANUP: removing test user sample from {metric} doc...")
    doc_cleanup = benchmarks_col.find_one({"industry": industry, "metric": metric})
    if doc_cleanup:
        samples_cleanup = [s for s in doc_cleanup.get("samples", []) if s.get("uid") != test_uid]
        new_count = len(samples_cleanup)
        benchmarks_col.update_one(
            {"id": doc_cleanup["id"]},
            {"$set": {"samples": samples_cleanup, "count": new_count}}
        )
        print(f"  ✓ Removed test sample, count: {count_after2} -> {new_count}")
    
    print("\n✅ TEST 4 PASSED: All unit tests passed, cleanup complete")
    
    mongo_client.close()

def main():
    """Run all tests."""
    print("\n" + "="*80)
    print("BACKEND TESTING: Sprint 2a Brain reasoning port + cross-founder benchmarks")
    print("="*80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"MongoDB: {MONGO_URL}/{DB_NAME}")
    print(f"LLM Budget: <= 3 calls (2 planned + 1 spare)")
    
    llm_calls = 0
    
    try:
        # TEST 1: LLM#1 - Benchmark aggregation (1 LLM call)
        token1, user_id1 = test_benchmark_aggregation()
        llm_calls += 1
        print(f"\n→ LLM calls used: {llm_calls}/3")
        
        # TEST 2: LLM#2 - Brain reasoning port (1 LLM call)
        token2, user_id2, decision_id = test_brain_reasoning_port()
        llm_calls += 1
        print(f"\n→ LLM calls used: {llm_calls}/3")
        
        # TEST 3: FREE - History clean (0 LLM calls)
        test_history_clean(token2, user_id2, decision_id)
        
        # TEST 4: FREE - Unit tests (0 LLM calls)
        test_unit_tests()
        
        # SUMMARY
        print("\n" + "="*80)
        print("✅ ALL TESTS PASSED")
        print("="*80)
        print(f"Total LLM calls: {llm_calls}/3 (within budget)")
        print("\nSummary:")
        print("  ✅ TEST 1: Benchmark aggregation working (count >= 2, distinct UIDs)")
        print("  ✅ TEST 2: Brain reasoning port working (9 keys, no hidden_desire, all assertions)")
        print("  ✅ TEST 3: History clean (reasoning stripped from API, stored in Mongo)")
        print("  ✅ TEST 4: Unit tests passed (ingest_facts, benchmark_digest, normalize_facts)")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
