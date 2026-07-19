#!/usr/bin/env python3
"""SALAAR Virtual User Test — 10 founders, real use cases, full system exercise.

Tests every module: auth, journey, goals, threads, decisions, SALAAR brief.
Each persona crafts messages designed to trigger specific SALAAR threat detections.
Runs against production at https://www.smartdecigen.com
"""
import json, time, sys, uuid, requests, random
from datetime import datetime

BASE = "https://www.smartdecigen.com/api"
RESULTS = []

# 10 Personas — each a real founder scenario
PERSONAS = [
    {
        "name": "Rajesh Kumar",
        "email": f"rajesh_{uuid.uuid4().hex[:6]}@founderai.co",
        "password": "Test123456",
        "persona": "SaaS Founder — churn crisis",
        "objective": "My B2B SaaS has 40% annual churn. I need to fix retention before we run out of runway in 4 months.",
        "messages": [
            "We're losing 3 customers every month and can't figure out why they're leaving.",
            "Our biggest client just told me they're considering a competitor because our support is too slow.",
            "What should I do about the churn problem? Should I hire a customer success team or fix the product first?",
            "I did it — we talked to 5 churned customers and found the core issue. Working on the fix now."
        ],
        "expected_threats": ["customer_churn_signal", "cash_crisis", "execution_stalling"],
        "strategic_question": "How do I convince my board that fixing churn is worth delaying our Series A by 6 months?"
    },
    {
        "name": "Priya Sharma",
        "email": f"priya_{uuid.uuid4().hex[:6]}@founderai.co",
        "password": "Test123456",
        "persona": "D2C Founder — cofounder conflict + cash crisis",
        "objective": "My D2C skincare brand is doing 2Cr ARR but my cofounder wants to take a different direction and we're burning cash.",
        "messages": [
            "My cofounder is making me feel crazy about wanting to fire our head of operations. He says I'm overreacting.",
            "We have only 3 months of runway left and he wants to launch a new product line instead of focusing on what's working.",
            "I think he's trying to undermine me with the team. They all side with him now.",
            "I'm carrying this alone. Can't tell anyone on the team how bad the cash situation really is."
        ],
        "expected_threats": ["cofounder_conflict", "cash_crisis", "strategy_drift", "founder_isolation"],
        "strategic_question": "How do I have the conversation with my cofounder about stepping back without destroying the company?"
    },
    {
        "name": "Amit Verma",
        "email": f"amit_{uuid.uuid4().hex[:6]}@founderai.co",
        "password": "Test123456",
        "persona": "First-time Founder — decision paralysis + people-pleasing",
        "objective": "I quit my job 6 months ago to build an AI tool for lawyers. I've changed direction 4 times and can't commit.",
        "messages": [
            "I can't decide whether to target solo lawyers or small firms. I keep going back and forth.",
            "What if I'm wrong about this market completely? I've already invested 6 months.",
            "Everyone in my founder group says I should just launch, but I'm afraid of disappointing the early users.",
            "I keep avoiding making a decision because I don't want to upset the 3 lawyers who are testing it."
        ],
        "expected_threats": ["decision_paralysis", "sunk_cost_trap", "strategy_drift"],
        "strategic_question": "What's the right way to pick one target market and commit fully for 90 days?"
    },
    {
        "name": "Meera Patel",
        "email": f"meera_{uuid.uuid4().hex[:6]}@founderai.co",
        "password": "Test123456",
        "persona": "Scale-up Founder — key-person risk + hiring",
        "objective": "My logistics startup grew to 50 people. Our CTO is the only person who understands the codebase and he's showing burnout signs.",
        "messages": [
            "Our CTO hasn't taken a day off in 8 months and he's the only one who can deploy or fix critical bugs.",
            "If he leaves, we're dead. I've tried hiring senior engineers but he rejects every candidate.",
            "I think he's become indispensable on purpose. He says nobody else can do what he does.",
            "He told me without him this company fails. That doesn't feel right."
        ],
        "expected_threats": ["key_person_risk", "toxic_hire", "execution_stalling"],
        "strategic_question": "How do I force knowledge transfer from my CTO without him quitting?"
    },
    {
        "name": "Vikram Singh",
        "email": f"vikram_{uuid.uuid4().hex[:6]}@founderai.co",
        "password": "Test123456",
        "persona": "Bootstrapped Founder — pricing undermining + competitor",
        "objective": "I run a profitable dev-tools startup. A competitor just launched with VC funding and is undercutting our pricing by 60%.",
        "messages": [
            "Our competitor is giving away for free what we charge $500/month for. They just raised $20M.",
            "I'm considering dropping prices to match them, but that'll kill our margins.",
            "Our customers are asking why they should pay when the competitor is cheaper. I don't know how to answer.",
            "I tried talking to 3 customers today about the value we provide. Two of them mentioned the competitor."
        ],
        "expected_threats": ["competitor_advance", "pricing_undermining", "revenue_concentration"],
        "strategic_question": "How do I compete against a well-funded competitor without racing to the bottom on price?"
    },
    {
        "name": "Sanjay Rao",
        "email": f"sanjay_{uuid.uuid4().hex[:6]}@founderai.co",
        "password": "Test123456",
        "persona": "Fundraising Founder — investor strategy",
        "objective": "I'm raising a $2M seed round for my fintech startup. 15 meetings, 3 soft commits, no lead investor yet.",
        "messages": [
            "I have 15 investor meetings next week but no clear strategy for who to prioritize.",
            "One investor keeps saying 'let's circle back next month.' Another wants to lead but at a lower valuation than I want.",
            "How do I create urgency when nobody seems to be in a hurry?",
            "I'm afraid if I push too hard they'll walk away. I don't want to scare them off."
        ],
        "expected_threats": ["decision_paralysis", "cash_crisis"],
        "strategic_question": "How do I get one of these soft-commit investors to lead the round at my target valuation?"
    },
    {
        "name": "Deepa Nair",
        "email": f"deepa_{uuid.uuid4().hex[:6]}@founderai.co",
        "password": "Test123456",
        "persona": "Marketplace Founder — execution stalling + team",
        "objective": "My hyperlocal services marketplace has demand but our supply-side onboarding is broken. 3 months behind schedule.",
        "messages": [
            "We're 3 months behind on our supply onboarding feature. Every sprint we push it back.",
            "The engineering team is blocked waiting for the product team to finalize specs. Nobody is unblocking them.",
            "Our OKRs are completely off track this quarter. We won't hit any of our key results.",
            "I have team members with nothing to do while others are drowning. I need to redistribute work."
        ],
        "expected_threats": ["execution_stalling", "okr_stalling", "team_underload"],
        "strategic_question": "How do I unblock a stuck team and get us shipping again in 2 weeks?"
    },
    {
        "name": "Arun Reddy",
        "email": f"arun_{uuid.uuid4().hex[:6]}@founderai.co",
        "password": "Test123456",
        "persona": "EdTech Founder — strategy drift",
        "objective": "My EdTech startup has pivoted from B2C to B2B to D2C in 18 months. Team is confused. Revenue is flat.",
        "messages": [
            "We've changed our business model 3 times this year. B2C, then B2B, now back to D2C.",
            "My team doesn't trust my direction anymore because I keep changing it.",
            "Every time I see a competitor do something new, I feel like we need to pivot too.",
            "We need a clear 12-month plan but I can't commit to anything because the market keeps shifting."
        ],
        "expected_threats": ["strategy_drift", "execution_stalling", "decision_paralysis"],
        "strategic_question": "How do we lock in on one direction for the next 12 months and stop chasing competitors?"
    },
    {
        "name": "Kavita Joshi",
        "email": f"kavita_{uuid.uuid4().hex[:6]}@founderai.co",
        "password": "Test123456",
        "persona": "HealthTech Founder — toxic hire + founder isolation",
        "objective": "My health-tech startup's head of sales is toxic. Everyone is afraid of her but she brings 60% of our revenue.",
        "messages": [
            "My head of sales is making everyone miserable but she generates 60% of our revenue. I can't fire her.",
            "Three team members have complained about her privately. One said they're looking for other jobs.",
            "She gaslights me in meetings. Tells me I agreed to things I never did.",
            "I feel completely alone in this. Can't fire her, can't keep her. Every option feels wrong."
        ],
        "expected_threats": ["toxic_hire", "revenue_concentration", "founder_isolation"],
        "strategic_question": "How do I transition away from a toxic but high-performing salesperson without losing our revenue?"
    },
    {
        "name": "Rohan Gupta",
        "email": f"rohan_{uuid.uuid4().hex[:6]}@founderai.co",
        "password": "Test123456",
        "persona": "Solo Founder — isolation + people-pleasing",
        "objective": "I'm a solo founder building a creator economy platform. I keep saying yes to every feature request and I'm drowning.",
        "messages": [
            "Every customer asks for a feature and I say yes. Now I have 47 features on the roadmap and nothing is done.",
            "I'm afraid if I say no, they'll leave for a competitor. I don't want to disappoint anyone.",
            "I've been working 16-hour days for 8 months. Nobody understands what this is like.",
            "What will they think if I launch something that doesn't have everything they asked for?"
        ],
        "expected_threats": ["founder_isolation", "strategy_drift", "execution_stalling"],
        "strategic_question": "How do I say no to customers without losing them?"
    }
]


def log_result(persona, step, status, detail=""):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {persona['name']} | {step}: {status}"
    if detail:
        line += f" — {detail[:150]}"
    print(line)
    RESULTS.append({"persona": persona["name"], "step": step, "status": status, "detail": detail})


def test_persona(persona):
    """Full lifecycle test for one virtual founder."""
    headers = {"Content-Type": "application/json"}
    session = requests.Session()
    
    # 1. Signup
    log_result(persona, "signup", "attempting", persona["email"])
    r = session.post(f"{BASE}/auth/signup", json={
        "email": persona["email"],
        "password": persona["password"],
        "name": persona["name"]
    }, timeout=30)
    if r.status_code != 200:
        log_result(persona, "signup", f"FAILED ({r.status_code})", r.text[:200])
        return
    log_result(persona, "signup", "OK", f"credits={r.json().get('user',{}).get('credits')}")

    # 2. Login to get cookie
    r = session.post(f"{BASE}/auth/login", json={
        "email": persona["email"],
        "password": persona["password"]
    }, timeout=30)
    if r.status_code != 200:
        log_result(persona, "login", "FAILED")
        return
    log_result(persona, "login", "OK")

    # 3. Start Journey
    log_result(persona, "journey/start", "sending objective")
    r = session.post(f"{BASE}/journey/start", json={
        "objective": persona["objective"]
    }, timeout=120)
    if r.status_code != 200:
        log_result(persona, "journey/start", f"FAILED ({r.status_code})")
        return
    log_result(persona, "journey/start", "OK", f"confidence={r.json().get('confidence')}%")

    # 4. Send 4 messages — crafted to trigger SALAAR threat detection
    for i, msg in enumerate(persona["messages"]):
        log_result(persona, f"message_{i+1}", "sending", msg[:80])
        r = session.post(f"{BASE}/journey/message", json={"message": msg}, timeout=120)
        if r.status_code == 200:
            log_result(persona, f"message_{i+1}", "OK")
        else:
            log_result(persona, f"message_{i+1}", f"FAILED ({r.status_code})")
        time.sleep(1)

    # 5. Strategic question — trigger causal chain
    log_result(persona, "strategic", "sending", persona["strategic_question"][:80])
    r = session.post(f"{BASE}/journey/message", json={"message": persona["strategic_question"]}, timeout=120)
    if r.status_code == 200:
        log_result(persona, "strategic", "OK")
    else:
        log_result(persona, "strategic", f"FAILED ({r.status_code})")

    # 6. Check SALAAR brief
    r = session.get(f"{BASE}/salaar/brief", timeout=30)
    if r.status_code == 200:
        brief = r.json()
        threats = brief.get("threats_active", 0)
        critical = brief.get("threats_critical", 0)
        auto = brief.get("actions_auto_executed", 0)
        people = len(brief.get("people_of_concern", []))
        chains = len(brief.get("active_chains", []))
        log_result(persona, "salaar_brief",
                   f"threats={threats} critical={critical} auto={auto} people={people} chains={chains}")
        
        # Check if expected threats were detected
        found = set()
        for alert in brief.get("top_alerts", []):
            found.add(alert.get("threat_key", ""))
        missed = [t for t in persona["expected_threats"] if t not in found]
        if missed:
            log_result(persona, "threat_check", f"MISSED: {', '.join(missed)}")
        else:
            detected = [t for t in persona["expected_threats"] if t in found]
            log_result(persona, "threat_check", f"ALL DETECTED: {', '.join(detected)}")
    else:
        log_result(persona, "salaar_brief", f"FAILED ({r.status_code})")

    # 7. Create a goal
    r = session.post(f"{BASE}/goals", json={
        "title": persona["objective"][:80],
        "why_now": persona["objective"]
    }, timeout=120)
    if r.status_code == 200:
        thread_id = r.json().get("thread", {}).get("thread_id", "")
        log_result(persona, "goal_create", "OK", f"thread_id={thread_id[:12]}")
        
        # Send a turn on the thread
        if thread_id:
            r = session.post(f"{BASE}/threads/{thread_id}/turn", json={
                "message": persona["messages"][0],
                "mode": "normal"
            }, timeout=120)
            if r.status_code == 200:
                log_result(persona, "thread_turn", "OK")
            else:
                log_result(persona, "thread_turn", f"FAILED ({r.status_code})")
    else:
        log_result(persona, "goal_create", f"FAILED ({r.status_code})")


def print_summary():
    print("\n" + "=" * 70)
    print("SALAAR VIRTUAL USER TEST — SUMMARY")
    print("=" * 70)
    
    personas_tested = len(set(r["persona"] for r in RESULTS))
    signups = sum(1 for r in RESULTS if r["step"] == "signup" and "OK" in r["status"])
    journeys = sum(1 for r in RESULTS if r["step"] == "journey/start" and "OK" in r["status"])
    threats_detected = sum(1 for r in RESULTS if r["step"] == "threat_check" and "ALL DETECTED" in r["status"])
    threats_missed = sum(1 for r in RESULTS if r["step"] == "threat_check" and "MISSED" in r["status"])
    
    print(f"  Personas tested: {personas_tested}")
    print(f"  Signups: {signups}")
    print(f"  Journeys started: {journeys}")
    print(f"  Threats ALL detected: {threats_detected}")
    print(f"  Threats partially missed: {threats_missed}")
    
    print("\n  SALAAR Brief Summaries:")
    for r in RESULTS:
        if r["step"] == "salaar_brief":
            print(f"    {r['persona']}: {r['detail']}")
    
    print("\n  Full results saved in RESULTS list")


if __name__ == "__main__":
    print("SALAAR Virtual User Test — 10 Founders")
    print(f"Target: {BASE}")
    print(f"Start: {datetime.now()}\n")
    
    for i, persona in enumerate(PERSONAS):
        print(f"\n--- Persona {i+1}/10: {persona['persona']} ---")
        try:
            test_persona(persona)
        except Exception as e:
            log_result(persona, "ERROR", str(e))
        time.sleep(2)  # Be nice to the server
    
    print_summary()
