"""
SmartDecigen Deep Discussion Engine - Phase 1 POC
Proves the entire core in isolation:
  A. Single LLM call turn engine (Opus 4.8 primary -> Haiku 4.5 fallback), strict JSON out
  B. Rule-based intent classifier (no LLM)
  C. Pure-function re-engagement (no LLM, phrase bank, silence-preserving)
  D. Deterministic rolling fields from substrate events
  E. Simulated multi-week scenario: update -> setback -> acknowledgment -> silence_breaker
"""
import os, json, re, time
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import anthropic

load_dotenv("/app/backend/.env")

PRIMARY_MODEL = "claude-opus-4-8"
FALLBACK_MODEL = "claude-haiku-4-5"
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

# ---------------------------------------------------------------- intent (pure)
ACK = re.compile(r"\b(did it|done|completed|finished|shipped|sent it|made the call|i did)\b", re.I)
SETBACK = re.compile(r"\b(couldn'?t|didn'?t|failed|stuck|blocked|gave up|too hard|avoided|put it off|procrastinat)\b", re.I)
QUESTION = re.compile(r"\?\s*$|^\s*(how|what|should|why|when|can i|do i|is it)\b", re.I)

def classify_intent(msg: str, days_since_last: float) -> str:
    if days_since_last >= 14: return "silence_breaker"
    if ACK.search(msg): return "acknowledgment"
    if SETBACK.search(msg): return "setback"
    if QUESTION.search(msg): return "question"
    if len(msg.split()) < 4: return "drift"
    return "update"

# ------------------------------------------------- rolling fields (pure, replayable)
def rolling_fields(events: list, now: datetime) -> dict:
    cutoff = now - timedelta(days=14)
    recent = [e for e in events if e["at"] >= cutoff]
    temps = [e["emotional_temperature"] for e in recent if e.get("emotional_temperature") is not None]
    acts = [e for e in recent if e.get("action_assigned")]
    done = [e for e in acts if e.get("action_done")]
    consistency = (len(done) / len(acts)) if acts else 0.5
    expected_turns = 14 / 3.5  # own pace baseline: ~2 turns/week
    pace = "on-track"
    if len(recent) >= expected_turns * 1.4 and consistency >= 0.6: pace = "ahead"
    elif len(recent) <= expected_turns * 0.5 or consistency < 0.3: pace = "behind"
    return {
        "emotional_temperature": round(sum(temps)/len(temps), 2) if temps else 0.5,
        "execution_consistency": round(consistency, 2),
        "pace_calibration": pace,
        "contradiction_history": [e["contradiction"] for e in events if e.get("contradiction")],
    }

# ------------------------------------------------- re-engagement (pure, NO LLM)
PHRASE_BANK = {
    "execution_up":   "{days} days away. Last time: {prior}. Your follow-through is up {mag}% since then — whatever you changed, it is working.",
    "execution_down": "{days} days away. Last time: {prior}. Execution consistency dropped {mag}% — worth naming before anything else.",
    "emotional_up":   "{days} days since we spoke. You left at: {prior}. The resistance reads lower now.",
    "emotional_down": "{days} days since we spoke. You left at: {prior}. Something is heavier than it was — that comes first.",
    "contradiction":  "While you were gone, a tension surfaced: {extra}. Worth looking at before moving.",
}
PRIORITY = ["contradiction", "execution", "emotional"]

def compute_reengagement_line(last_snap: dict, now_snap: dict, days_absent: int) -> str | None:
    if days_absent < 7: return None
    deltas = []
    de = now_snap["execution_consistency"] - last_snap["execution_consistency"]
    if abs(de) >= 0.15: deltas.append(("execution", de, abs(round(de*100))))
    dt = now_snap["emotional_temperature"] - last_snap["emotional_temperature"]
    if abs(dt) >= 0.2: deltas.append(("emotional", dt, abs(round(dt*100))))
    new_contra = [c for c in now_snap["contradiction_history"] if c not in last_snap["contradiction_history"]]
    if new_contra: deltas.append(("contradiction", 0, new_contra[-1]))
    if not deltas: return None  # silence-preserving
    deltas.sort(key=lambda d: PRIORITY.index(d[0]))
    kind, sign, extra = deltas[0]
    if kind == "contradiction":
        return PHRASE_BANK["contradiction"].format(extra=extra)
    key = f"{kind}_{'up' if sign > 0 else 'down'}"
    return PHRASE_BANK[key].format(days=days_absent, prior=last_snap.get("summary_line", "your last position"), mag=extra)

# ------------------------------------------------- turn engine LLM call (single)
SYSTEM = """You are the Deep Discussion Engine: a calm, direct companion holding a user's goal across weeks. Your only purpose: shrink the distance between knowing and doing.
Rules: never announce memory ("as we discussed"); surface what changed, not recaps; acknowledge before answering (match the intent label); always converge to ONE next action doable in 24-48h; the easiest path forward given today's reality, not the ideal plan; warm, respectful, zero fluff, no lists of options.
Return ONLY valid JSON, no markdown fences:
{"acknowledgment": "1-3 sentences, companion voice, responds to their message",
 "refreshed_easiest_path": "1-2 lines: easiest path forward given today's reality",
 "refreshed_next_action": "1 line: concrete action for next 24-48h",
 "refreshed_open_question": "1 line: the single unresolved tension",
 "skip_list": ["0-2 things to deliberately ignore right now"] ,
 "state_summary": "3 short lines (\\n separated): where they are right now",
 "signals": {"emotional_temperature": 0.0to1.0, "action_done": bool (did they report completing the prior next action), "contradiction": "string or null (tension between what they say and do)"}}"""

def llm_turn(thread: dict, substrate: dict, user_msg: str, intent: str) -> tuple[dict, str]:
    prompt = (
        f"GOAL: {thread['goal']}\n"
        f"STATE SUMMARY:\n{thread['current_state_summary']}\n"
        f"OPEN QUESTION: {thread['current_open_question']}\n"
        f"CURRENT EASIEST PATH: {thread['current_easiest_path']}\n"
        f"PRIOR NEXT ACTION (check if done): {thread['current_next_action']}\n"
        f"SUBSTRATE: temp={substrate['emotional_temperature']} consistency={substrate['execution_consistency']} pace={substrate['pace_calibration']}\n"
        f"INTENT: {intent}\n"
        f"USER MESSAGE: {user_msg}"
    )
    for model in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            r = client.messages.create(model=model, max_tokens=900, system=SYSTEM,
                                       messages=[{"role": "user", "content": prompt}])
            txt = r.content[0].text.strip()
            txt = re.sub(r"^```(json)?|```$", "", txt, flags=re.M).strip()
            return json.loads(txt), model
        except Exception as e:
            print(f"  [{model}] failed: {type(e).__name__}: {str(e)[:160]}")
    raise RuntimeError("Both models failed")

# ------------------------------------------------- pipeline (6 steps)
def run_turn(thread, events, user_msg, now, last_msg_at):
    t0 = time.time()
    days_gap = (now - last_msg_at).total_seconds() / 86400
    substrate = rolling_fields(events, now)                       # step 2
    intent = classify_intent(user_msg, days_gap)                  # step 3
    out, model = llm_turn(thread, substrate, user_msg, intent)    # step 4
    thread.update({                                               # step 5
        "current_state_summary": out["state_summary"],
        "current_open_question": out["refreshed_open_question"],
        "current_easiest_path": out["refreshed_easiest_path"],
        "current_next_action": out["refreshed_next_action"],
    })
    sig = out["signals"]
    events.append({"at": now, "emotional_temperature": sig["emotional_temperature"],
                   "action_assigned": True, "action_done": bool(sig["action_done"]),
                   "contradiction": sig.get("contradiction")})
    telemetry = {"intent": intent, "model": model, "latency_s": round(time.time()-t0, 1)}  # step 6
    return out, telemetry, substrate

# ================================================================= SCENARIO
def main():
    results = {}
    now = datetime.now(timezone.utc)
    thread = {"goal": "Launch my consulting offer and get the first paying client",
              "current_state_summary": "(new thread)", "current_open_question": "(none yet)",
              "current_easiest_path": "(none yet)", "current_next_action": "(none yet)"}
    events = []

    # Turn 1: opening update
    t = now - timedelta(days=21)
    out, tel, _ = run_turn(thread, events, 
        "I keep redesigning my website instead of reaching out to potential clients. I know outreach is what matters but I keep avoiding it.", t, t)
    print(f"\nT1 {tel} \n ack: {out['acknowledgment'][:120]}\n action: {out['refreshed_next_action']}\n question: {out['refreshed_open_question']}")
    ok1 = all(out.get(k) for k in ("acknowledgment","refreshed_easiest_path","refreshed_next_action","refreshed_open_question","state_summary"))
    results["turn_json_complete"] = ok1
    results["contradiction_detected"] = bool(out["signals"].get("contradiction"))
    snap_at_leave = {**rolling_fields(events, t), "summary_line": thread["current_state_summary"].split("\n")[0]}

    # Turn 2: setback (3 days later)
    t2 = t + timedelta(days=3)
    out2, tel2, _ = run_turn(thread, events, "I didn't send the messages. I got stuck rewriting my pitch and felt blocked.", t2, t)
    print(f"\nT2 {tel2} intent_expected=setback got={tel2['intent']}\n ack: {out2['acknowledgment'][:120]}")
    results["setback_intent"] = tel2["intent"] == "setback"
    results["setback_action_done_false"] = out2["signals"]["action_done"] is False

    # Turn 3: acknowledgment (2 days later)
    t3 = t2 + timedelta(days=2)
    out3, tel3, _ = run_turn(thread, events, "Done. I sent 5 outreach messages yesterday and one person replied.", t3, t2)
    print(f"\nT3 {tel3} intent_expected=acknowledgment got={tel3['intent']}\n ack: {out3['acknowledgment'][:120]}")
    results["ack_intent"] = tel3["intent"] == "acknowledgment"
    results["ack_action_done_true"] = out3["signals"]["action_done"] is True

    # Re-engagement after 16 days absence (pure, no LLM)
    t4 = t3 + timedelta(days=16)
    snap_now = rolling_fields(events, t4)
    snap_now["summary_line"] = thread["current_state_summary"].split("\n")[0]
    line = compute_reengagement_line(snap_at_leave, snap_now, 16)
    print(f"\nRE-ENGAGE (16d): {line}")
    results["reengagement_fires"] = line is not None
    # Null case: tiny delta
    null_line = compute_reengagement_line(snap_now, dict(snap_now), 10)
    results["reengagement_silence_preserved"] = null_line is None
    # <7 days = None always
    results["reengagement_under_7d_none"] = compute_reengagement_line(snap_at_leave, snap_now, 4) is None

    # Turn 4: silence breaker intent (>=14d gap)
    out4, tel4, _ = run_turn(thread, events, "I'm back. Things got busy with family stuff.", t4, t3)
    print(f"\nT4 {tel4} intent_expected=silence_breaker got={tel4['intent']}\n ack: {out4['acknowledgment'][:120]}")
    results["silence_breaker_intent"] = tel4["intent"] == "silence_breaker"

    # Fallback test: Haiku 4.5 reachable
    try:
        r = client.messages.create(model=FALLBACK_MODEL, max_tokens=50,
                                   messages=[{"role":"user","content":"Reply with exactly: OK"}])
        results["haiku_fallback_reachable"] = "OK" in r.content[0].text
    except Exception as e:
        print(f"Haiku check failed: {e}"); results["haiku_fallback_reachable"] = False

    # Prompt boundedness: state fields stay compact regardless of turns
    results["prompt_bounded"] = len(thread["current_state_summary"]) < 600 and len(thread["current_easiest_path"]) < 400

    print("\n" + "="*60)
    for k, v in results.items(): print(f"  {'PASS' if v else 'FAIL'}  {k}")
    print("="*60)
    print("ALL PASS" if all(results.values()) else "FAILURES PRESENT")

if __name__ == "__main__":
    main()
