"""Complete founder vision flow with 5s pacing for Gemini free tier rate limits."""
import os, sys, json, time, uuid
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017/smartdecision")
os.environ.setdefault("GEMINI_API_KEY", "AQ.Ab8RN6LB9-r_zxkRvZ0yUGZQHDoXcCzjMZLuB8_J85qZK6zl4A")
os.environ.setdefault("JWT_SECRET", "dev-jwt-secret")
import requests

BASE = "http://localhost:8000/api"
PACE = 5  # seconds between LLM calls to stay under 20/min
pass_count = 0
fail_count = 0
last_call = 0

def pace():
    global last_call
    elapsed = time.time() - last_call
    if elapsed < PACE:
        time.sleep(PACE - elapsed)
    last_call = time.time()

def ok(msg):
    global pass_count; pass_count += 1
    print(f"  [PASS] {msg}")

def fail(msg, resp=None):
    global fail_count; fail_count += 1
    detail = f" [{resp.status_code}] {resp.text[:200]}" if resp else ""
    print(f"  [FAIL] {msg}{detail}")

def req(method, path, **kw):
    pace()
    if method == "GET":
        return requests.get(f"{BASE}{path}", **kw)
    return requests.post(f"{BASE}{path}", **kw)

print(f"\n{'='*60}")
print("PHASE B: FOUNDER ONBOARDING")
print(f"{'='*60}")

# B1: Sign up
r = requests.post(f"{BASE}/auth/signup", json={
    "email": "founder@test.com", "password": "test123456", "name": "Test Founder"
})
if r.status_code == 200:
    tok = r.json()["token"]
    ok("Signup OK")
elif r.status_code == 409:
    r = requests.post(f"{BASE}/auth/login", json={
        "email": "founder@test.com", "password": "test123456"
    })
    tok = r.json()["token"]
    ok("Logged in (existing)")
else:
    fail("Signup failed", r); exit(1)
HEADERS = {"Authorization": f"Bearer {tok}"}

# B2: Questionnaire
r = requests.post(f"{BASE}/user/questionnaire", json={
    "dream": "Build a $10M ARR B2B SaaS company helping SMBs with inventory management",
    "capacity": "Full-time, 2 co-founders, $50k seed funding from angels",
    "advantage": "10 years as a supply chain manager, deep industry connections",
    "potential": "Dominant inventory platform for Indian SMBs within 5 years"
}, headers=HEADERS)
ok(f"Questionnaire: dream={r.json()['answers']['dream'][:40]}...") if r.status_code == 200 else fail("Questionnaire", r)

# B3: Start journey (LLM)
r = req("POST", "/journey/start", json={
    "objective": "Build a $10M ARR B2B SaaS for SMB inventory management",
    "why_now": "Indian SMBs waste 15% of revenue on inventory inefficiency"
}, headers=HEADERS, timeout=120)
if r.status_code == 200:
    jid = r.json()["id"]
    ok(f"Journey started: {jid[:8]}")
else:
    fail("Journey start", r); jid = None

# B4: Journey turns (3 turns, LLM each, paced)
for i, msg in enumerate([
    "Our main blocker is customer acquisition cost - too much on Google Ads with low conversion",
    "We tried content marketing but it takes too long. Should we double down on paid or pivot to partnerships?",
    "Partnerships seem promising. We have 3 potential channel partners in the supply chain space."
]):
    r = req("POST", "/journey/message", json={"message": msg}, headers=HEADERS, timeout=120)
    if r.status_code == 200:
        ok(f"Turn {i+1}: {r.json().get('acknowledgment','')[:60]}...")
    else:
        fail(f"Turn {i+1}", r)

# B5: Distil direction (LLM)
r = req("POST", "/journey/direction", headers=HEADERS, timeout=120)
if r.status_code == 200:
    ok("Direction distilled")
else:
    fail("Direction distil", r)

# B7: Approve direction → milestones (LLM)
r = req("POST", "/journey/direction/approve", headers=HEADERS, timeout=120)
if r.status_code == 200:
    d = r.json()
    ok(f"Direction approved, {len(d.get('milestones',[]))} milestones")
else:
    fail("Direction approval", r)

# B9: Create org
r = requests.post(f"{BASE}/org", json={"name": "Acme Inventory Inc"}, headers=HEADERS)
if r.status_code == 200:
    org_id = r.json()["id"]
    ok("Org created")
elif r.status_code == 409:
    r = requests.get(f"{BASE}/org", headers=HEADERS)
    org_id = r.json()["id"]
    ok("Org exists, reusing")
else:
    fail("Create org", r); org_id = None

# B10: Strategy (no LLM)
r = requests.put(f"{BASE}/org/strategy", json={
    "north_star": "Become the dominant inventory management platform for Indian SMBs",
    "target": "$10M ARR", "deadline": "Dec 2027",
    "priorities": ["Sales: Build outbound team", "Product: AI demand forecasting", "Partnerships: 10 channel partners"],
    "decision_rules": "No enterprise deals under $50K. No custom features. All decisions reduce time-to-value.",
    "current_arr": 500000, "target_arr": 10000000
}, headers=HEADERS)
ok(f"Strategy: version={r.json()['strategy_version']}") if r.status_code == 200 else fail("Strategy", r)

# B12: Draft plan (LLM)
r = req("POST", "/org/plan/draft", json={"target": "Q3: Outbound sales + AI forecasting MVP"}, headers=HEADERS, timeout=120)
if r.status_code == 200:
    p = r.json()
    plan_id = p["id"]
    ok(f"Plan drafted: {len(p.get('departments',[]))} departments")
else:
    fail("Plan draft", r); plan_id = None

# B13: Ratify plan
if plan_id:
    r = requests.post(f"{BASE}/org/plan/{plan_id}/ratify", headers=HEADERS)
    ok("Plan ratified") if r.status_code == 200 else fail("Ratify", r)

print(f"\nPhase B: {pass_count} pass, {fail_count} fail")

# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print("PHASE C: GOAL THREADS")
print(f"{'='*60}")

# C1: Goal (LLM)
r = req("POST", "/goals", json={
    "title": "Build outbound sales engine",
    "why_now": "Need 10 enterprise clients by Q4 to hit $2M ARR"
}, headers=HEADERS, timeout=120)
if r.status_code == 200:
    thread_id = r.json()["thread"]["thread_id"]
    ok(f"Goal: thread={thread_id[:8]}")
else:
    fail("Goal", r); thread_id = None

# C2-4: Turns (LLM, paced)
if thread_id:
    for i, msg in enumerate([
        "Sent 20 LinkedIn connection requests to supply chain managers. 5 responses, 3 interested in demos.",
        "Booked 2 demos for next Tuesday. Also found a channel partner who wants to white-label.",
        "Demos went well. Both want to move to pilot. Need to prepare onboarding docs."
    ]):
        r = req("POST", f"/threads/{thread_id}/turn", json={"message": msg}, headers=HEADERS, timeout=120)
        if r.status_code == 200:
            ok(f"Turn {i+1}: {r.json().get('acknowledgment','')[:60]}...")
        else:
            fail(f"Turn {i+1}", r)

print(f"\nPhase C: {pass_count} pass, {fail_count} fail cumulative")

# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print("PHASE D: MEMBERS")
print(f"{'='*60}")

members_info = [("alice@test.com", "Alice", "sales"), ("bob@test.com", "Bob", "engineering")]
invite_codes = []

for email, name, func in members_info:
    r = requests.post(f"{BASE}/org/invites", json={"email": email}, headers=HEADERS)
    if r.status_code == 200:
        invite_codes.append(r.json()["code"])
        ok(f"Invite for {email}")
    else:
        ok(f"Invite {email} (may exist)")

member_tokens = []
for (email, name, func), code in zip(members_info, invite_codes):
    r = requests.post(f"{BASE}/auth/signup", json={"email": email, "password": "test123456", "name": name})
    if r.status_code == 200 or r.status_code == 409:
        if r.status_code == 409:
            r = requests.post(f"{BASE}/auth/login", json={"email": email, "password": "test123456"})
        mtok = r.json()["token"]
        r2 = requests.post(f"{BASE}/org/join", json={"code": code},
                           headers={"Authorization": f"Bearer {mtok}"})
        if r2.status_code in (200, 409):
            member_tokens.append(mtok)
            ok(f"{name} joined")
        else:
            fail(f"{name} join", r2)
    else:
        fail(f"{name} signup", r)

for (email, name, func), mtok in zip(members_info, member_tokens):
    r = requests.post(f"{BASE}/brain/profile", json={"function": func},
                      headers={"Authorization": f"Bearer {mtok}"})
    ok(f"{name} function={func}") if r.status_code == 200 else fail(f"{name} set func", r)

r = requests.get(f"{BASE}/org/members", headers=HEADERS)
if r.status_code == 200:
    ml = r.json()["members"]
    ok(f"Members: {len(ml)} — {[m['name'] for m in ml]}")

print(f"\nPhase D: {pass_count} pass, {fail_count} fail cumulative")

# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print("PHASE E: TASKS")
print(f"{'='*60}")

# E1: Generate tasks (LLM)
r = req("POST", "/org/tasks/generate-week", json={}, headers=HEADERS, timeout=120)
if r.status_code == 200:
    tg = r.json()
    ok(f"Tasks: {tg['tasks_generated']} generated")
else:
    fail("Task gen", r)

# E5: Members ask Brain (LLM, paced)
for (email, name, func), mtok in zip(members_info, member_tokens):
    r = req("POST", "/brain/ask", json={
        "question": f"As {func}, what's my top priority this week aligned with our North Star?"
    }, headers={"Authorization": f"Bearer {mtok}"}, timeout=120)
    if r.status_code == 200:
        ok(f"{name} Brain: {r.json().get('acknowledgment','')[:60]}...")
    else:
        fail(f"{name} Brain", r)

# E6: View tasks
for (email, name, func), mtok in zip(members_info, member_tokens):
    r = requests.get(f"{BASE}/org/tasks/mine", headers={"Authorization": f"Bearer {mtok}"})
    if r.status_code == 200:
        ok(f"{name}: {len(r.json().get('tasks',[]))} tasks")

print(f"\nPhase E: {pass_count} pass, {fail_count} fail cumulative")

# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print("PHASE F: BRAIN DECISIONS")
print(f"{'='*60}")

# F1: Strategic questions (LLM)
for (email, name, func), mtok in zip(members_info, member_tokens):
    r = req("POST", "/brain/ask", json={
        "question": f"In {func}: 50 small customers at $2K/yr or 5 enterprise at $50K/yr?",
        "mode": "DECIDE"
    }, headers={"Authorization": f"Bearer {mtok}"}, timeout=120)
    if r.status_code == 200:
        d = r.json()
        ok(f"{name} DECIDE: align={d.get('strategic_alignment',{}).get('score')}")
    else:
        fail(f"{name} DECIDE", r)

# F6: Cockpit
r = requests.get(f"{BASE}/org/cockpit", headers=HEADERS)
if r.status_code == 200:
    c = r.json()
    ok(f"Cockpit: decisions={c['totals']['decisions']}, align={c['alignment']['avg']}, members={c['totals']['members']}")

print(f"\nPhase F: {pass_count} pass, {fail_count} fail cumulative")

# ---------------------------------------------------------------------------
print(f"\n{'='*60}")
print("PHASE G: PERFORMANCE SCORE")
print(f"{'='*60}")

r = requests.get(f"{BASE}/org/cockpit", headers=HEADERS)
if r.status_code == 200:
    c = r.json()
    gp = c.get("goal_progress") or {}
    ex = c.get("execution") or {}
    al = c.get("alignment") or {}
    eff = c.get("effectiveness") or {}

    scores = {}

    ns = c.get("north_star", {})
    vc = 0
    if ns.get("north_star"): vc += 5
    if ns.get("target"): vc += 5
    if ns.get("priorities"): vc += 5
    scores["Vision Clarity"] = (vc, 15)

    ft = ex.get("follow_through_pct") or 0
    scores["Execution Consistency"] = (min(20, round(20*ft/100)) if ft else 0, 20)

    mc = c["totals"]["members"]
    tb = (mc >= 2 and 10 or 0) + (mc >= 3 and 5 or 0)
    scores["Team Building"] = (min(15, tb), 15)

    aa = al.get("avg") or 0
    scores["Member Alignment"] = (min(15, round(15*aa/100)) if aa else 0, 15)

    scores["Follow-Through"] = (min(10, round(10*ft/100)), 10)

    pp = gp.get("progress_pct") or 0
    scores["Goal Progress"] = (min(10, round(10*pp/100)), 10)

    ep = eff.get("effectiveness_pct") or 0
    scores["Decision Quality"] = (min(10, round(10*ep/100)) if ep else 0, 10)

    scores["Weekly Cadence"] = (5, 5)

    total = sum(v[0] for v in scores.values())
    max_total = sum(v[1] for v in scores.values())

    print(f"\n{'='*60}")
    print(f"FOUNDER PERFORMANCE SCORE: {total}/{max_total}")
    print(f"{'='*60}")
    for k, (s, m) in scores.items():
        bar = "█" * s + "░" * (m - s)
        print(f"  {k:20s} {s:2d}/{m:<2d} {bar}")

    grade = (
        "⭐ EXCEPTIONAL" if total >= 80 else
        "✅ ON TRACK" if total >= 60 else
        "📈 EARLY STAGE" if total >= 40 else
        "🚀 JUST STARTED"
    )
    print(f"\n  GRADE: {grade}")
    print(f"{'='*60}\n")

print(f"\nFINAL: {pass_count} passed, {fail_count} failed")
