#!/usr/bin/env python3
"""Decision Brain Backend Test Suite - Step 0 POC

Tests the new /api/brain router in isolation:
- Document upload and indexing
- Answer mode (grounded retrieval)
- Plan mode
- Decide mode with company rules
- Guardrail (no hallucination)
- Auth and validation guards
"""
import os
import sys
import time
import base64
import requests
from datetime import datetime

# Read base URL from frontend/.env
BASE_URL = None
with open("/app/frontend/.env", "r") as f:
    for line in f:
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip()
            break

if not BASE_URL:
    print("❌ REACT_APP_BACKEND_URL not found in /app/frontend/.env")
    sys.exit(1)

API_BASE = f"{BASE_URL}/api"
print(f"🔗 Testing against: {API_BASE}")

# Test credentials (founder account with 1000 credits)
FOUNDER_EMAIL = "ceo@smartdecigen.com"
FOUNDER_PASSWORD = "FounderOS@2026"

# Test state
token = None
credits_before = None
tree_id = None

def log_test(name):
    print(f"\n{'='*80}")
    print(f"TEST: {name}")
    print('='*80)

def log_pass(msg):
    print(f"✅ {msg}")

def log_fail(msg):
    print(f"❌ {msg}")
    sys.exit(1)

def log_info(msg):
    print(f"ℹ️  {msg}")

# ---------------------------------------------------------------- Auth
log_test("AUTH: Login as founder")
r = requests.post(f"{API_BASE}/auth/login", json={"email": FOUNDER_EMAIL, "password": FOUNDER_PASSWORD})
if r.status_code != 200:
    log_fail(f"Login failed: {r.status_code} {r.text}")
data = r.json()
token = data.get("token")
if not token:
    log_fail("No token in login response")
log_pass(f"Logged in as {FOUNDER_EMAIL}")

headers = {"Authorization": f"Bearer {token}"}

# Get initial credits
r = requests.get(f"{API_BASE}/credits", headers=headers)
if r.status_code != 200:
    log_fail(f"Failed to get credits: {r.status_code}")
credits_before = r.json().get("credits", 0)
log_info(f"Initial credits: {credits_before}")

# ---------------------------------------------------------------- TEST 1: Upload document
log_test("TEST 1: POST /api/brain/upload - Upload refund policy document")

# Create a small refund policy document
refund_policy = """# Company Refund Policy

Last updated: January 2026

## Standard Refunds
Refunds are accepted within 30 days of purchase for any reason. The customer must provide proof of purchase and return the item in its original condition.

## Damaged Goods
Damaged goods are eligible for a full refund within 45 days of purchase. The customer must provide photographic evidence of the damage and return the item.

## Non-Refundable Items
The following items are not eligible for refunds:
- Digital downloads after access has been granted
- Personalized or custom-made items
- Perishable goods

## Processing Time
Refunds are processed within 5-7 business days after we receive the returned item. The refund will be credited to the original payment method.

## Contact
For refund requests, contact support@company.com with your order number and reason for return.
"""

refund_b64 = base64.b64encode(refund_policy.encode()).decode()
upload_payload = {
    "filename": "refund_policy.md",
    "mime": "text/markdown",
    "base64": refund_b64
}

r = requests.post(f"{API_BASE}/brain/upload", headers=headers, json=upload_payload)
if r.status_code != 200:
    log_fail(f"Upload failed: {r.status_code} {r.text}")

data = r.json()
tree_id = data.get("tree_id")
status = data.get("status")

if not tree_id:
    log_fail("No tree_id in upload response")
if status != "processing":
    log_fail(f"Expected status 'processing', got '{status}'")

log_pass(f"Document uploaded: tree_id={tree_id}, status={status}")

# Poll for document to be ready
log_info("Polling GET /api/brain/documents until status='ready' (max 60s)...")
max_wait = 60
start = time.time()
doc_ready = False

while time.time() - start < max_wait:
    r = requests.get(f"{API_BASE}/brain/documents", headers=headers)
    if r.status_code != 200:
        log_fail(f"Failed to get documents: {r.status_code}")
    
    data = r.json()
    docs = data.get("documents", [])
    ready_count = data.get("ready_count", 0)
    
    # Find our document
    our_doc = None
    for doc in docs:
        if doc.get("tree_id") == tree_id:
            our_doc = doc
            break
    
    if our_doc and our_doc.get("status") == "ready":
        node_count = our_doc.get("node_count", 0)
        if node_count > 0:
            doc_ready = True
            log_pass(f"Document ready: node_count={node_count}, ready_count={ready_count}")
            break
    
    time.sleep(3)

if not doc_ready:
    log_fail(f"Document not ready after {max_wait}s")

# ---------------------------------------------------------------- TEST 2: Answer mode (grounded)
log_test("TEST 2: POST /api/brain/ask - Answer mode (grounded in uploaded doc)")

r = requests.get(f"{API_BASE}/credits", headers=headers)
credits_before_ask = r.json().get("credits", 0)
log_info(f"Credits before ask: {credits_before_ask}")

ask_payload = {"question": "What is our refund window for damaged goods?"}
r = requests.post(f"{API_BASE}/brain/ask", headers=headers, json=ask_payload)
if r.status_code != 200:
    log_fail(f"Ask failed: {r.status_code} {r.text}")

data = r.json()
mode = data.get("mode")
found_in_docs = data.get("found_in_docs")
answer = data.get("answer", "")
citations = data.get("citations", [])
cost = data.get("cost", 0)
credits_after = data.get("credits", 0)
model = data.get("model", "")
sources_found = data.get("sources_found", 0)

log_info(f"Response: mode={mode}, found_in_docs={found_in_docs}, cost={cost}, credits={credits_after}")
log_info(f"Answer: {answer[:200]}...")
log_info(f"Citations: {citations}")
log_info(f"Model: {model}, sources_found={sources_found}")

# Assertions
if mode != "answer":
    log_fail(f"Expected mode='answer', got '{mode}'")
if not found_in_docs:
    log_fail("Expected found_in_docs=true for grounded answer")
if "45" not in answer:
    log_fail(f"Expected answer to mention '45 days' for damaged goods, got: {answer}")
if not citations:
    log_fail("Expected citations to be non-empty")
if cost <= 0:
    log_fail(f"Expected cost > 0, got {cost}")
if cost > 16:
    log_fail(f"Expected cost <= 16 (reserve), got {cost}")
if credits_after >= credits_before_ask:
    log_fail(f"Expected credits to decrease, before={credits_before_ask}, after={credits_after}")

# Check citation references the uploaded doc
cited_doc = any("refund" in c.get("doc", "").lower() for c in citations)
if not cited_doc:
    log_fail(f"Expected citation to reference refund policy doc, got: {citations}")

log_pass(f"Answer mode working: found_in_docs=true, answer mentions 45 days, {len(citations)} citations, cost={cost}")

# ---------------------------------------------------------------- TEST 3: Plan mode
log_test("TEST 3: POST /api/brain/ask - Plan mode")

r = requests.get(f"{API_BASE}/credits", headers=headers)
credits_before_plan = r.json().get("credits", 0)

ask_payload = {"question": "Give me a plan to reduce refund requests next quarter."}
r = requests.post(f"{API_BASE}/brain/ask", headers=headers, json=ask_payload)
if r.status_code != 200:
    log_fail(f"Ask failed: {r.status_code} {r.text}")

data = r.json()
mode = data.get("mode")
plan = data.get("plan")
cost = data.get("cost", 0)
credits_after = data.get("credits", 0)

log_info(f"Response: mode={mode}, cost={cost}, credits={credits_after}")
log_info(f"Plan: {plan}")

# Assertions
if mode != "plan":
    log_fail(f"Expected mode='plan', got '{mode}'")
if not plan or not isinstance(plan, list) or len(plan) == 0:
    log_fail(f"Expected plan to be non-empty list, got: {plan}")
if cost <= 0:
    log_fail(f"Expected cost > 0, got {cost}")
if credits_after >= credits_before_plan:
    log_fail(f"Expected credits to decrease, before={credits_before_plan}, after={credits_after}")

log_pass(f"Plan mode working: mode='plan', plan has {len(plan)} steps, cost={cost}")

# ---------------------------------------------------------------- TEST 4: Decide mode + company rules
log_test("TEST 4a: POST /api/brain/settings - Set company rules")

settings_payload = {
    "instructions": "Never approve a refund after 45 days. Always prioritise the written refund policy."
}
r = requests.post(f"{API_BASE}/brain/settings", headers=headers, json=settings_payload)
if r.status_code != 200:
    log_fail(f"Settings failed: {r.status_code} {r.text}")

data = r.json()
if not data.get("ok"):
    log_fail("Expected ok=true in settings response")

log_pass("Company rules set successfully")

# Verify settings were saved
r = requests.get(f"{API_BASE}/brain/settings", headers=headers)
if r.status_code != 200:
    log_fail(f"Get settings failed: {r.status_code}")
saved_instructions = r.json().get("instructions", "")
if "45 days" not in saved_instructions:
    log_fail(f"Settings not saved correctly: {saved_instructions}")
log_pass("Settings verified via GET /api/brain/settings")

log_test("TEST 4b: POST /api/brain/ask - Decide mode with company rules")

r = requests.get(f"{API_BASE}/credits", headers=headers)
credits_before_decide = r.json().get("credits", 0)

ask_payload = {
    "question": "A customer wants a refund 60 days after purchase for a damaged item. What should I do?"
}
r = requests.post(f"{API_BASE}/brain/ask", headers=headers, json=ask_payload)
if r.status_code != 200:
    log_fail(f"Ask failed: {r.status_code} {r.text}")

data = r.json()
mode = data.get("mode")
recommendation = data.get("recommendation")
answer = data.get("answer", "")
cost = data.get("cost", 0)
credits_after = data.get("credits", 0)

log_info(f"Response: mode={mode}, cost={cost}, credits={credits_after}")
log_info(f"Answer: {answer}")
log_info(f"Recommendation: {recommendation}")

# Assertions
if mode != "decide":
    log_fail(f"Expected mode='decide', got '{mode}'")
if not recommendation:
    log_fail("Expected recommendation to be non-empty for decide mode")
if cost <= 0:
    log_fail(f"Expected cost > 0, got {cost}")
if credits_after >= credits_before_decide:
    log_fail(f"Expected credits to decrease, before={credits_before_decide}, after={credits_after}")

# Check that recommendation respects the 45-day rule (should NOT approve)
combined = (answer + " " + recommendation).lower()
if "approve" in combined and "not" not in combined and "don't" not in combined and "do not" not in combined:
    log_fail(f"Expected recommendation to NOT approve refund after 60 days (45-day rule), got: {recommendation}")

log_pass(f"Decide mode working: mode='decide', recommendation respects 45-day rule, cost={cost}")

# ---------------------------------------------------------------- TEST 5: Guardrail (no hallucination)
log_test("TEST 5: POST /api/brain/ask - Guardrail test (question not in docs)")

r = requests.get(f"{API_BASE}/credits", headers=headers)
credits_before_guard = r.json().get("credits", 0)

ask_payload = {"question": "What is our parental leave policy?"}
r = requests.post(f"{API_BASE}/brain/ask", headers=headers, json=ask_payload)
if r.status_code != 200:
    log_fail(f"Ask failed: {r.status_code} {r.text}")

data = r.json()
mode = data.get("mode")
found_in_docs = data.get("found_in_docs")
answer = data.get("answer", "")
cost = data.get("cost", 0)
credits_after = data.get("credits", 0)

log_info(f"Response: mode={mode}, found_in_docs={found_in_docs}, cost={cost}")
log_info(f"Answer: {answer}")

# Assertions
if mode == "answer" and found_in_docs:
    log_fail(f"Expected found_in_docs=false for answer mode when info not in docs, got found_in_docs={found_in_docs}")

# Check that answer doesn't invent a parental leave policy
answer_lower = answer.lower()
if "parental leave" in answer_lower and ("not found" not in answer_lower and "could not find" not in answer_lower and "no information" not in answer_lower and "not in" not in answer_lower):
    log_fail(f"HALLUCINATION DETECTED: Answer invents parental leave policy: {answer}")

if cost <= 0:
    log_fail(f"Expected cost > 0, got {cost}")
if credits_after >= credits_before_guard:
    log_fail(f"Expected credits to decrease, before={credits_before_guard}, after={credits_after}")

log_pass(f"Guardrail working: found_in_docs=false (or mode!=answer), answer does not hallucinate, cost={cost}")

# ---------------------------------------------------------------- TEST 6: Auth and validation guards
log_test("TEST 6a: POST /api/brain/ask - No auth token (401)")

r = requests.post(f"{API_BASE}/brain/ask", json={"question": "test"})
if r.status_code != 401:
    log_fail(f"Expected 401 without token, got {r.status_code}")
log_pass("No token -> 401 ✓")

log_test("TEST 6b: POST /api/brain/upload - No auth token (401)")

r = requests.post(f"{API_BASE}/brain/upload", json={"filename": "test.txt", "mime": "text/plain", "base64": "dGVzdA=="})
if r.status_code != 401:
    log_fail(f"Expected 401 without token, got {r.status_code}")
log_pass("No token -> 401 ✓")

log_test("TEST 6c: POST /api/brain/upload - Image mime (415)")

image_payload = {
    "filename": "test.png",
    "mime": "image/png",
    "base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
}
r = requests.post(f"{API_BASE}/brain/upload", headers=headers, json=image_payload)
if r.status_code != 415:
    log_fail(f"Expected 415 for image mime, got {r.status_code}")
log_pass("Image mime -> 415 ✓")

log_test("TEST 6d: DELETE /api/brain/documents/{tree_id} - Delete uploaded doc")

r = requests.delete(f"{API_BASE}/brain/documents/{tree_id}", headers=headers)
if r.status_code != 200:
    log_fail(f"Delete failed: {r.status_code} {r.text}")
log_pass(f"Document {tree_id} deleted successfully")

# Verify document no longer listed
r = requests.get(f"{API_BASE}/brain/documents", headers=headers)
if r.status_code != 200:
    log_fail(f"Failed to get documents: {r.status_code}")
docs = r.json().get("documents", [])
if any(d.get("tree_id") == tree_id for d in docs):
    log_fail(f"Document {tree_id} still listed after deletion")
log_pass("Document no longer listed after deletion ✓")

# ---------------------------------------------------------------- Summary
print("\n" + "="*80)
print("🎉 ALL DECISION BRAIN TESTS PASSED")
print("="*80)
print(f"\nTest Summary:")
print(f"✅ TEST 1: Document upload and indexing (status: processing -> ready)")
print(f"✅ TEST 2: Answer mode (grounded, found_in_docs=true, citations, 45-day fact)")
print(f"✅ TEST 3: Plan mode (non-empty ordered list)")
print(f"✅ TEST 4: Decide mode + company rules (respects 45-day rule)")
print(f"✅ TEST 5: Guardrail (no hallucination for parental leave)")
print(f"✅ TEST 6: Auth guards (401 no token), validation (415 image), delete (200)")
print(f"\nFinal credits: {credits_after}")
print(f"Total cost: ~{credits_before - credits_after} credits")
print("\nAll Decision Brain backend APIs working correctly! 🚀")
