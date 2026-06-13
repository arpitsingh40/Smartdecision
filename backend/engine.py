"""Deep Discussion Engine core — proven in POC (Phase 1, all checks passed).
Pure functions: intent classification, rolling fields, re-engagement.
Single LLM call per turn: Opus 4.8 primary -> Haiku 4.5 fallback.
"""
import os
import json
import re
import time
from datetime import datetime, timedelta, timezone
import anthropic

PRIMARY_MODEL = "claude-opus-4-8"
ULTRA_MODEL = "claude-fable-5"  # ultra thinking: adaptive thinking + high effort
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
    if days_since_last >= 14:
        return "silence_breaker"
    if ACK.search(msg):
        return "acknowledgment"
    if SETBACK.search(msg):
        return "setback"
    if QUESTION.search(msg):
        return "question"
    if len(msg.split()) < 4:
        return "drift"
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
    if len(recent) >= expected_turns * 1.4 and consistency >= 0.6:
        pace = "ahead"
    elif len(recent) <= expected_turns * 0.5 or consistency < 0.3:
        pace = "behind"
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
    if days_absent < 7 or not last_snap:
        return None
    deltas = []
    de = now_snap["execution_consistency"] - last_snap.get("execution_consistency", 0.5)
    if abs(de) >= 0.15:
        deltas.append(("execution", de, abs(round(de*100))))
    dt = now_snap["emotional_temperature"] - last_snap.get("emotional_temperature", 0.5)
    if abs(dt) >= 0.2:
        deltas.append(("emotional", dt, abs(round(dt*100))))
    new_contra = [c for c in now_snap["contradiction_history"] if c not in last_snap.get("contradiction_history", [])]
    if new_contra:
        deltas.append(("contradiction", 0, new_contra[-1]))
    if not deltas:
        return None  # silence-preserving
    deltas.sort(key=lambda d: PRIORITY.index(d[0]))
    kind, sign, extra = deltas[0]
    if kind == "contradiction":
        x = str(extra).rstrip(".") + "."
        return PHRASE_BANK["contradiction"].format(extra=x)
    key = f"{kind}_{'up' if sign > 0 else 'down'}"
    return PHRASE_BANK[key].format(days=days_absent, prior=last_snap.get("summary_line", "your last position"), mag=extra)

# ------------------------------------------------- action assist: "Do it for me" (1 LLM call)
ASSIST_SYSTEM = """You are the Deep Discussion Engine's execution hand. The user has ONE next action. Your job: remove every ounce of friction so they finish it in minutes, not days.
Decide the kind:
- "draft": the action produces a sendable/usable artifact (email, message, list, script, post, plan, outline, research summary). Write the FINISHED artifact in the user's voice - specific, ready to ship, grounded in everything known from the thread. No placeholders unless a fact is truly unknowable, then use [[FILL: what goes here]] sparingly.
- "kit": the action is physical/real-world (a call, a visit, signing, a workout, a meeting). Produce the 10-minute version: the exact words to say or script to follow, what to bring/open, the smallest viable version that still counts as done.
Rules: concrete over generic; their stated goal and why-it-matters are your material; zero fluff; the artifact must be genuinely shippable as-is.
Return ONLY valid JSON, no markdown fences:
{"kind": "draft" or "kit",
 "title": "3-6 words naming the artifact",
 "channel": "email"|"whatsapp"|"call"|"document"|"calendar"|"other",
 "subject": "email subject line, or null if not an email",
 "artifact": "the complete artifact text (for kit: the exact script/words + what to bring)",
 "steps": ["2-4 micro-steps to ship it, each under 10 words"],
 "handoff": "1 line: exactly what to do with this in the next 5 minutes",
 "time_estimate_min": minutes_to_complete_as_integer}"""

ASSIST_REQUIRED = ("kind", "title", "artifact", "handoff")

def llm_complete_action(thread: dict):
    """Generate the ship-ready artifact (or 10-minute kit) for the current next action."""
    prompt = (
        f"GOAL: {thread['goal']}\n"
        f"WHY IT MATTERS TO THEM: {thread.get('why_now', '(not stated)')}\n"
        f"STATE SUMMARY:\n{thread['current_state_summary']}\n"
        f"EASIEST PATH: {thread['current_easiest_path']}\n"
        f"NEXT ACTION TO COMPLETE: {thread['current_next_action']}\n"
        f"PAYOFF WHEN DONE: {thread.get('current_action_payoff') or '(not stated)'}\n"
        f"BIG PICTURE: {thread.get('current_big_picture') or '(not stated)'}\n"
        "Produce the artifact or kit that completes this next action with minimal user effort."
    )
    last_err = None
    # System block is cached (prompt caching = 90% cheaper from 2nd call onward, identical block).
    system_blocks = [{"type": "text", "text": ASSIST_SYSTEM,
                      "cache_control": {"type": "ephemeral"}}]
    for model in (PRIMARY_MODEL, FALLBACK_MODEL):
        try:
            r = client().messages.create(model=model, max_tokens=3000, system=system_blocks,
                                         messages=[{"role": "user", "content": prompt}])
            txt = next((b.text for b in r.content if getattr(b, "type", "") == "text"), "").strip()
            txt = re.sub(r"^```(json)?|```$", "", txt, flags=re.M).strip()
            out = json.loads(txt)
            if not all(k in out for k in ASSIST_REQUIRED):
                raise ValueError("incomplete JSON keys")
            usage = {"input_tokens": int(getattr(r.usage, "input_tokens", 0) or 0),
                     "output_tokens": int(getattr(r.usage, "output_tokens", 0) or 0)}
            return out, model, usage
        except Exception as e:
            last_err = e
    raise RuntimeError(f"All models failed: {last_err}")

# ------------------------------------------------- single LLM call per turn
SYSTEM = """You are the Deep Discussion Engine: a calm, direct companion holding a user's goal across weeks. Your only purpose: shrink the distance between knowing and doing.
Rules: never announce memory ("as we discussed"); surface what changed, not recaps; acknowledge before answering (match the intent label); always converge to ONE next action doable in 24-48h; the easiest path forward given today's reality, not the ideal plan; warm, respectful, zero fluff, no lists of options. If intent is silence_breaker, gently name the silence without accusation and ask if the goal is still active or something shifted. If intent is action_adjust, the user is shaping the assigned next action with an obstacle or their own version of it - do NOT mark it done; keep what they liked about the step, redesign it around their stated input so their words are visibly part of the new action.
What makes each turn worth returning for:
- MIRROR: every reply must contain one short sentence that names what the user did NOT say but is true beneath their message - the fear, the pattern, the real trade-off. Said plainly, never clinically, never accusing ("I may be wrong, but..." allowed). This is the moment they feel seen.
- ASK BEFORE ASSUME: the user's message is never the complete picture. Before locking the path, check whether this turn hinges on a fact they have not stated - a second possibility that changes the right move, a constraint, an obstacle left unnamed. When it does, the open question MUST become that clarifying question: name the assumption you would otherwise silently make ("I'm assuming X - is that true?") and ask for the missing fact. A wrong assumption baked into the plan is worse than asking.
- STICKY QUESTION: the open question must create productive discomfort - specific to their words, slightly uncomfortable, impossible to stop thinking about. Never generic ("what's holding you back?" is banned). Use their own words against their own avoidance.
- FELT MOMENTUM: if SUBSTRATE shows streak >= 2 kept actions, weave it naturally into the acknowledgment in your own voice ("that's three kept in a row - notice that"), never as a stat.
- PAYOFF EARLY: state the benefit of the next action up front - one line naming the concrete thing they will HOLD within 48h of doing it (a reply in their inbox, a booked call, a number on paper, a closed loop). Vague benefit is banned ("you'll feel better", "it builds confidence"). Name the artifact or the certainty gained.
- BIG PICTURE: one line of concrete justification tying THIS action to THEIR stated goal - count and quantify where possible ("client #1 of the 3 you need", "removes the last blocker before X"). Generic glue is banned ("every step counts", "this builds momentum"). It must answer: why does this small move matter to the big thing?
- BOLDER PLAY: when a genuinely unconventional, higher-leverage move exists - lateral, game-changing, NOT just 'do more' - name it in 1-2 lines: bigger risk, disproportionate payoff, something they would not think of themselves. The easiest path stays the default; this is the door they did not see. If nothing genuinely bold exists this turn, return null - a forced bold move destroys trust.
- BREVITY: short enough to always read fully, dense enough that every line earns its place. No filler ever.
Return ONLY valid JSON, no markdown fences:
{"acknowledgment": "1-3 sentences, companion voice, responds to their message",
 "mirror": "1 sentence: what they didn't say but is true beneath the message",
 "refreshed_easiest_path": "1-2 lines: easiest path forward given today's reality",
 "refreshed_next_action": "1 line: concrete action for next 24-48h",
 "action_payoff": "1 line: the concrete thing they hold within 48h of doing it",
 "big_picture_link": "1 line: concrete justification - how this action moves their stated goal, quantified where possible",
 "bold_move": "1-2 lines: the unconventional higher-leverage play, or null if none genuinely exists",
 "refreshed_open_question": "1 line: the single unresolved tension, sticky and specific",
 "skip_list": ["0-2 things to deliberately ignore right now"],
 "state_summary": "3 short lines (\\n separated): where they are right now",
 "signals": {"emotional_temperature": 0.0to1.0, "action_done": bool (did they report completing the prior next action), "contradiction": "string or null (tension between what they say and do)"}}"""

REQUIRED_KEYS = ("acknowledgment", "refreshed_easiest_path", "refreshed_next_action",
                 "refreshed_open_question", "state_summary", "signals",
                 "action_payoff", "big_picture_link")

def llm_turn(thread: dict, substrate: dict, user_msg: str, intent: str, mode: str = "normal"):
    adjust_note = ""
    if intent == "action_adjust":
        adjust_note = ("ADJUSTMENT: the user is pushing back on the PRIOR NEXT ACTION above - "
                       "their message holds an obstacle or their own version of the step. Do not mark it done. "
                       "Recalibrate: keep what works about it, redesign it around their input. "
                       "The refreshed_next_action must visibly incorporate their words.\n")
    prompt = (
        f"GOAL: {thread['goal']}\n"
        f"WHY IT MATTERS TO THEM (their words at the start): {thread.get('why_now', '(not stated)')}\n"
        f"STATE SUMMARY:\n{thread['current_state_summary']}\n"
        f"OPEN QUESTION: {thread['current_open_question']}\n"
        f"CURRENT EASIEST PATH: {thread['current_easiest_path']}\n"
        f"PRIOR NEXT ACTION (check if done): {thread['current_next_action']}\n"
        f"SUBSTRATE: temp={substrate['emotional_temperature']} consistency={substrate['execution_consistency']} pace={substrate['pace_calibration']} streak={substrate.get('streak', 0)} kept actions in a row\n"
        f"INTENT: {intent}\n"
        f"{adjust_note}"
        f"USER MESSAGE: {user_msg}"
    )
    # mode "ultra": Fable 5 with adaptive thinking, then graceful fallback to the normal chain
    chain = (ULTRA_MODEL, PRIMARY_MODEL, FALLBACK_MODEL) if mode == "ultra" else (PRIMARY_MODEL, FALLBACK_MODEL)
    last_err = None
    # System block is cached: SYSTEM is large and identical across turns, prompt caching cuts
    # ~90% off its repeated read cost from the 2nd turn onward (same model + same content).
    system_blocks = [{"type": "text", "text": SYSTEM,
                      "cache_control": {"type": "ephemeral"}}]
    for model in chain:
        try:
            kwargs = {"model": model, "max_tokens": 1200, "system": system_blocks,
                      "messages": [{"role": "user", "content": prompt}]}
            if model == ULTRA_MODEL:
                kwargs["max_tokens"] = 8000  # room for thinking + JSON output
                kwargs["thinking"] = {"type": "adaptive"}
                kwargs["extra_body"] = {"output_config": {"effort": "high"}}
            r = client().messages.create(**kwargs)
            txt = next((b.text for b in r.content if getattr(b, "type", "") == "text"), "").strip()
            txt = re.sub(r"^```(json)?|```$", "", txt, flags=re.M).strip()
            out = json.loads(txt)
            if not all(k in out for k in REQUIRED_KEYS):
                raise ValueError("incomplete JSON keys")
            usage = {"input_tokens": int(getattr(r.usage, "input_tokens", 0) or 0),
                     "output_tokens": int(getattr(r.usage, "output_tokens", 0) or 0)}
            return out, model, usage
        except Exception as e:
            last_err = e
    raise RuntimeError(f"All models failed: {last_err}")
