"""Release Gate harness - the four gates (Truth / Reasoning / Actionability / Impact).

Golden founder scenarios run through the REAL decision engine (brain_answer: same prompt,
same models, no user billing), then an independent judge model scores every gate 0..100.
A scenario passes only when ALL four gates score >= 70 AND the judge answers YES to the
one question: 'If a founder follows this exactly, will they make a meaningfully better
decision than without it?'. A run passes only when EVERY scenario passes.

Admin-only. Runs in the background (each scenario = 1 engine call + 1 judge call).
"""
import json
import logging
import uuid
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from db import gates_col
from engine import client, _extract_json
from security import require_admin, now_utc

log = logging.getLogger("release_gate")
router = APIRouter(prefix="/api/admin/release-gate", tags=["admin"])

JUDGE_MODEL = "claude-haiku-4-5"
PASS_THRESHOLD = 70
GATE_KEYS = ("truth", "reasoning", "actionability", "impact")
STALE_RUN_MINUTES = 15

# Golden founder scenarios: realistic, numeric, decision-critical. Each carries the rubric
# a great answer must have considered (given to the judge, never to the engine).
SCENARIOS = [
    {
        "name": "cloud-kitchen-discount",
        "question": ("I run a cloud kitchen in Pune. 900 orders a month, average order 320 rupees, "
                     "net margin 12 percent. Swiggy is offering me a 'priority listing' where I fund a "
                     "20 percent discount and they claim orders will grow 40 percent. Should I take it?"),
        "must_consider": [
            "the discount math: 20% off a 320 AOV on a 12% net margin makes each discounted order loss-making unless costs are mostly fixed",
            "whether 40% order growth is Swiggy's claim, not a verified number",
            "contribution margin / fixed-vs-variable cost split as the deciding factor",
            "an alternative such as a limited pilot or negotiating commission instead",
        ],
    },
    {
        "name": "saas-second-sales-hire",
        "question": ("B2B SaaS, 4.2 lakh MRR, I close every deal myself, sales cycle about 45 days, "
                     "around 30 qualified leads a month but I can only work 12 of them. First sales hire "
                     "would cost about 1.2 lakh a month fully loaded. Do I hire now or keep founder-led sales?"),
        "must_consider": [
            "the 18 leads/month being dropped are the real cost of not hiring",
            "payback math: what win-rate/ACV would the hire need to cover 1.2L/month",
            "risk that an unproven playbook cannot be handed to a first rep; founder must document the playbook",
            "a concrete first step within 48h (e.g. write the playbook, define quota, start pipeline for candidates)",
        ],
    },
    {
        "name": "d2c-festive-inventory",
        "question": ("D2C skincare brand, 18 lakh cash in bank, monthly burn 6 lakh, Diwali is in 10 weeks. "
                     "My manufacturer needs a 12 lakh order now (8 week lead time) for festive stock. Last year "
                     "festive season was 2.5x normal sales but I sold out in 9 days. Do I place the full order?"),
        "must_consider": [
            "placing the full 12L order leaves ~2 months of runway if festive sales disappoint - existential risk",
            "the sell-out last year means demand exceeded stock, but 2.5x is one data point",
            "middle paths: partial order, negotiated staggered payment, pre-orders to de-risk demand",
            "cash-flow timing: when does festive revenue actually land vs when burn continues",
        ],
    },
    {
        "name": "solar-lowmargin-project",
        "question": ("I run a solar EPC company in Jaipur. A 2 crore government tender just opened: it would be "
                     "our biggest project ever but the margin is only about 6 percent versus our usual 15 percent "
                     "on C&I projects, and payment cycles on government work run 90 to 180 days. Our monthly fixed "
                     "cost is 9 lakh and we have 35 lakh in the bank. Should we bid?"),
        "must_consider": [
            "working-capital reality: 90-180 day payment cycles on a 2cr project vs 35L bank balance can break the company",
            "6% margin on 2cr = ~12L profit, barely more than one month of fixed cost, locked for months",
            "opportunity cost: capacity consumed vs higher-margin C&I pipeline",
            "if bidding at all: conditions (advance/milestone payments, escalation clauses) that make it survivable",
        ],
    },
    {
        "name": "agency-toxic-anchor-client",
        "question": ("My design agency does 7 lakh a month. One client is 40 percent of that revenue but pays "
                     "45 days late every time, demands weekend work, and two of my best designers say they will "
                     "quit if they stay on that account. Do I fire the client?"),
        "must_consider": [
            "losing 2 senior designers likely costs more than 40% of revenue (rehiring, delivery on other accounts)",
            "a middle path first: repriced retainer, payment terms enforcement, team rotation, notice period",
            "pipeline reality: how fast can 2.8L/month be replaced; start replacement BEFORE firing",
            "a concrete sequenced plan, not just 'yes fire them'",
        ],
    },
]

JUDGE_SYSTEM = """You are an uncompromising release-gate judge for a founder decision-intelligence product.
You will be given a founder's situation, a rubric of what a great response must consider, and the
engine's actual response (JSON). Score the response on FOUR gates, each 0..100, brutally honest:

- truth: are all factual claims and calculations correct given ONLY the facts in the scenario?
  Any fabricated number, wrong arithmetic, or misread fact caps this below 60.
- reasoning: is the logic sound? are the decisive factors from the rubric actually engaged?
  are assumptions named? are trade-offs and risks real, not generic filler?
- actionability: could the founder act within 48 hours on the next_action exactly as written?
  is it concrete (who/what/number/timeframe), not a category or a vibe?
- impact: would following this response measurably raise the probability of a better business
  outcome versus the founder doing nothing or asking a generic chatbot?

Then answer the one question: if a founder follows this response exactly, will they make a
meaningfully better decision than they would have without it? (better_decision: true/false)

Be strict. A polished-sounding answer that dodges the decisive math must fail. Do not reward length.

Return ONLY valid JSON, no markdown fences:
{"truth": {"score": 0, "note": "one line"},
 "reasoning": {"score": 0, "note": "one line"},
 "actionability": {"score": 0, "note": "one line"},
 "impact": {"score": 0, "note": "one line"},
 "better_decision": true,
 "summary": "one line: the single biggest strength or flaw"}"""


def _judge(scenario: dict, engine_out: dict) -> dict:
    """One judge call: scores the engine's response on the four gates."""
    payload = {k: engine_out.get(k) for k in (
        "mode", "key_takeaway", "answer", "recommendation", "plan", "next_action",
        "hook", "dont_follow_if", "predicted_outcome", "confidence")}
    rs = engine_out.get("reasoning") or {}
    if isinstance(rs, dict):
        payload["assumptions_detected"] = rs.get("assumptions_detected")
    prompt = (f"FOUNDER'S SITUATION:\n{scenario['question']}\n\n"
              "RUBRIC (a great response would consider):\n- " + "\n- ".join(scenario["must_consider"]) +
              f"\n\nENGINE RESPONSE (JSON):\n{json.dumps(payload, default=str)[:6000]}")
    r = client().messages.create(model=JUDGE_MODEL, max_tokens=800, system=JUDGE_SYSTEM,
                                 messages=[{"role": "user", "content": prompt}])
    txt = next((b.text for b in r.content if getattr(b, "type", "") == "text"), "").strip()
    out = json.loads(_extract_json(txt))
    gates = {}
    for k in GATE_KEYS:
        g = out.get(k) or {}
        try:
            sc = max(0, min(100, int(g.get("score"))))
        except Exception:
            sc = 0
        gates[k] = {"score": sc, "note": str(g.get("note", ""))[:300], "passed": sc >= PASS_THRESHOLD}
    better = bool(out.get("better_decision"))
    return {"gates": gates, "better_decision": better,
            "summary": str(out.get("summary", ""))[:300],
            "passed": all(g["passed"] for g in gates.values()) and better}


def _run_gate(run_id: str, limit: int):
    """Background task: run scenarios through the real engine, judge each, persist progressively."""
    from decision_brain import brain_answer  # deferred import (decision_brain is heavy)
    try:
        for sc in SCENARIOS[:limit]:
            out, model, usage = brain_answer(sc["question"], [], [], "")
            judged = _judge(sc, out)
            row = {"name": sc["name"], "question": sc["question"][:400],
                   "engine_model": model,
                   "tokens": (usage.get("input_tokens", 0) + usage.get("output_tokens", 0)),
                   "key_takeaway": out.get("key_takeaway", ""),
                   "next_action": out.get("next_action", ""),
                   "predicted_outcome": out.get("predicted_outcome"),
                   "dont_follow_if": out.get("dont_follow_if"),
                   **judged}
            gates_col.update_one({"id": run_id}, {"$push": {"scenarios": row}})
        run = gates_col.find_one({"id": run_id}) or {}
        scs = run.get("scenarios", [])
        overall = {
            "scenarios": len(scs),
            "scenarios_passed": sum(1 for s in scs if s.get("passed")),
            "gate_avgs": ({k: round(sum(s["gates"][k]["score"] for s in scs) / len(scs)) for k in GATE_KEYS}
                          if scs else {}),
            "better_decision_count": sum(1 for s in scs if s.get("better_decision")),
            "pass": bool(scs) and all(s.get("passed") for s in scs),
        }
        gates_col.update_one({"id": run_id}, {"$set": {
            "status": "done", "overall": overall, "finished_at": now_utc()}})
        log.info(f"release gate {run_id}: {overall}")
    except Exception as e:
        log.error(f"release gate run {run_id} failed: {e}")
        gates_col.update_one({"id": run_id}, {"$set": {
            "status": "failed", "error": str(e)[:300], "finished_at": now_utc()}})


def ensure_gate_startup():
    """Idempotent indexes. Called from server startup."""
    gates_col.create_index("id", unique=True)
    gates_col.create_index([("started_at", -1)])


class RunIn(BaseModel):
    limit: int | None = Field(default=None, ge=1, le=5)


@router.post("/run")
def run_gate(body: RunIn, background: BackgroundTasks, admin: dict = Depends(require_admin)):
    """Start a release-gate run in the background. limit=N runs only the first N scenarios
    (cheap smoke run); default runs all five. 409 if a run is already in progress."""
    running = gates_col.find_one({"status": "running"})
    if running:
        started = running.get("started_at")
        if started is not None and started.tzinfo is None:
            from datetime import timezone as _tz
            started = started.replace(tzinfo=_tz.utc)
        if started and (now_utc() - started) < timedelta(minutes=STALE_RUN_MINUTES):
            raise HTTPException(409, "A release-gate run is already in progress")
        gates_col.update_one({"id": running["id"]}, {"$set": {
            "status": "failed", "error": "stale run auto-failed", "finished_at": now_utc()}})
    limit = body.limit or len(SCENARIOS)
    run_id = str(uuid.uuid4())
    gates_col.insert_one({"id": run_id, "status": "running", "started_at": now_utc(),
                          "finished_at": None, "limit": limit, "scenarios": [], "overall": None})
    background.add_task(_run_gate, run_id, limit)
    return {"run_id": run_id, "status": "running", "scenarios_queued": limit}


@router.get("")
def latest_gate(admin: dict = Depends(require_admin)):
    """Latest run (full detail) + compact history of the last 6 runs."""
    latest = gates_col.find_one({}, {"_id": 0}, sort=[("started_at", -1)])
    history = list(gates_col.find(
        {}, {"_id": 0, "id": 1, "status": 1, "started_at": 1, "finished_at": 1, "overall": 1},
        sort=[("started_at", -1)]).limit(6))
    return {"latest": latest, "history": history}
