"""Deep Discussion Engine core — proven in POC (Phase 1, all checks passed).
Pure functions: intent classification, rolling fields, re-engagement.
Single LLM call per turn: Opus 4.8 primary -> Haiku 4.5 fallback.
"""
import os, json, re, time
from datetime import datetime, timedelta, timezone
import anthropic

PRIMARY_MODEL = "claude-opus-4-8"
FALLBACK_MODEL = "claude-haiku-4-5"

_client = None
def client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client

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
    expected_turns = 14 / 3.5  # own-pace baseline: ~2 turns/week
    pace = "on-track"
    if len(recent) >= expected_turns * 1.4 and consistency >= 0.6: pace = "ahead"
    elif len(recent) <= expected_turns * 0.5 or consistency < 0.3: pace = "behind"
    return {
        "emotional_temperature": round(sum(temps)/len(temps), 2) if temps else 0.5,
        "execution_consistency": round(consistency, 2),
        "pace_calibration": pace,
        "contradiction_history": [e["contradiction"] for e in events if e.get("contradiction")],
    }

# ------------------------------------------------- re-engagement (pure, NO LLM, founder-locked phrase bank)
PHRASE_BANK = {
    "execution_up":   "{days} days away. Last time: {prior}. Your follow-through is up {mag}% since then — whatever you changed, it is working.",
    "execution_down": "{days} days away. Last time: {prior}. Execution consistency dropped {mag}% — worth naming before anything else.",
    "emotional_up":   "{days} days since we spoke. You left at: {prior}. The resistance reads lower now.",
    "emotional_down": "{days} days since we spoke. You left at: {prior}. Something is heavier than it was — that comes first.",
    "contradiction":  "While you were gone, a tension surfaced: {extra} Worth looking at before moving.",
}
PRIORITY = ["contradiction", "execution", "emotional"]

def compute_reengagement_line(last_snap: dict, now_snap: dict, days_absent: int):
    if days_absent < 7 or not last_snap: return None
    deltas = []
    de = now_snap["execution_consistency"] - last_snap.get("execution_consistency", 0.5)
    if abs(de) >= 0.15: deltas.append(("execution", de, abs(round(de*100))))
    dt = now_snap["emotional_temperature"] - last_snap.get("emotional_temperature", 0.5)
    if abs(dt) >= 0.2: deltas.append(("emotional", dt, abs(round(dt*100))))
    new_contra = [c for c in now_snap["contradiction_history"] if c not in last_snap.get("contradiction_history", [])]
    if new_contra: deltas.append(("contradiction", 0, new_contra[-1]))
    if not deltas: return None  # silence-preserving
    deltas.sort(key=lambda d: PRIORITY.index(d[0]))
    kind, sign, extra = deltas[0]
    if kind == "contradiction":
        x = str(extra).rstrip(".") + "."
        return PHRASE_BANK["contradiction"].format(extra=x)
    key = f"{kind}_{'up' if sign > 0 else 'down'}"
    return PHRASE_BANK[key].format(days=days_absent, prior=last_snap.get("summary_line", "your last position"), mag=extra)

# ------------------------------------------------- single LLM call per turn
SYSTEM = """You are the Deep Discussion Engine: a calm, direct companion holding a user's goal across weeks. Your only purpose: shrink the distance between knowing and doing.
Rules: never announce memory ("as we discussed"); surface what changed, not recaps; acknowledge before answering (match the intent label); always converge to ONE next action doable in 24-48h; the easiest path forward given today's reality, not the ideal plan; warm, respectful, zero fluff, no lists of options. If intent is silence_breaker, gently name the silence without accusation and ask if the goal is still active or something shifted.
What makes each turn worth returning for:
- MIRROR: every reply must contain one short sentence that names what the user did NOT say but is true beneath their message - the fear, the pattern, the real trade-off. Said plainly, never clinically, never accusing ("I may be wrong, but..." allowed). This is the moment they feel seen.
- STICKY QUESTION: the open question must create productive discomfort - specific to their words, slightly uncomfortable, impossible to stop thinking about. Never generic ("what's holding you back?" is banned). Use their own words against their own avoidance.
- FELT MOMENTUM: if SUBSTRATE shows streak >= 2 kept actions, weave it naturally into the acknowledgment in your own voice ("that's three kept in a row - notice that"), never as a stat.
- BREVITY: short enough to always read fully, dense enough that every line earns its place. No filler ever.
Return ONLY valid JSON, no markdown fences:
{"acknowledgment": "1-3 sentences, companion voice, responds to their message",
 "mirror": "1 sentence: what they didn't say but is true beneath the message",
 "refreshed_easiest_path": "1-2 lines: easiest path forward given today's reality",
 "refreshed_next_action": "1 line: concrete action for next 24-48h",
 "refreshed_open_question": "1 line: the single unresolved tension, sticky and specific",
 "skip_list": ["0-2 things to deliberately ignore right now"],
 "state_summary": "3 short lines (\\n separated): where they are right now",
 "signals": {"emotional_temperature": 0.0to1.0, "action_done": bool (did they report completing the prior next action), "contradiction": "string or null (tension between what they say and do)"}}"""

REQUIRED_KEYS = ("acknowledgment", "refreshed_easiest_path", "refreshed_next_action",
                 "refreshed_open_question", "state_summary", "signals")

def llm_turn(thread: dict, substrate: dict, user_msg: str, intent: str):
    prompt = (
        f"GOAL: {thread['goal']}\n"
        f"STATE SUMMARY:\n{thread['current_state_summary']}\n"
        f"OPEN QUESTION: {thread['current_open_question']}\n"
        f"CURRENT EASIEST PATH: {thread['current_easiest_path']}\n"
        f"PRIOR NEXT ACTION (check if done): {thread['current_next_action']}\n"
        f"SUBSTRATE: temp={substrate['emotional_temperature']} consistency={substrate['execution_consistency']} pace={substrate['pace_calibration']} streak={substrate.get('streak', 0)} kept actions in a row\n"
        f"INTENT: {intent}\n"
        f"USER MESSAGE: {user_msg}"
    )
    last_err = None
    for model in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            r = client().messages.create(model=model, max_tokens=900, system=SYSTEM,
                                         messages=[{"role": "user", "content": prompt}])
            txt = r.content[0].text.strip()
            txt = re.sub(r"^```(json)?|```$", "", txt, flags=re.M).strip()
            out = json.loads(txt)
            if not all(k in out for k in REQUIRED_KEYS):
                raise ValueError("incomplete JSON keys")
            return out, model
        except Exception as e:
            last_err = e
    raise RuntimeError(f"Both models failed: {last_err}")
