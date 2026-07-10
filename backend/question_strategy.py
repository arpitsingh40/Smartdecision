"""Question Strategy Engine — the meta-layer that decides what KIND of turn to take.

Every conversation turn is a strategic move, not just a response. Different user states
require different question types and timing. This module maps detected user state to
the optimal conversation strategy and handles timing (when to reveal, when to hold).

Question types:
  reflect          Listen, acknowledge, build safety. Default.
  name_unspoken    Name what the user isn't saying — hidden fear, assumption, contradiction.
  reveal_pattern   Connect current behavior to recurring patterns across sessions.
  reframe          Shift how the user sees the problem — when they're going wrong direction.
  force_choice     Concrete commitment when execution is needed and success is close.
  retreat          Back off, give space, permission not to answer.
  get_out_of_way   Minimal response, let them execute — they have momentum.

Timing modes:
  now    Deploy this turn.
  seed   Plant the observation gently — don't deliver directly, let it surface.
  wait   Not ready. Log it, come back later.

Usage:
  strategy = decide_strategy(user_state)
  # Returns: {"type": strategy_name, "timing": timing_mode, "payload": observation_or_None}
"""

from __future__ import annotations
from typing import Optional

# ---------------------------------------------------------------------------
# Question type taxonomy
# ---------------------------------------------------------------------------
STRATEGY_TYPES = (
    "reflect",
    "name_unspoken",
    "reveal_pattern",
    "reframe",
    "force_choice",
    "retreat",
    "get_out_of_way",
)

TIMING_MODES = ("now", "seed", "wait")

# ---------------------------------------------------------------------------
# User state — the input to the strategy engine
# ---------------------------------------------------------------------------
class UserState:
    __slots__ = (
        "safety_level",          # 0-1: how much trust has been built
        "pattern_confidence",    # 0-1: how confident we are about detected patterns
        "pattern_type",          # str or None: what kind of pattern detected
        "direction_quality",     # "good" | "wrong" | "unclear"
        "execution_readiness",   # "ready" | "stuck" | "avoiding" | "not_ready"
        "emotional_temp",        # 0-1: from rolling_fields
        "execution_consistency", # 0-1: from rolling_fields
        "pace",                  # "ahead" | "on-track" | "behind"
        "streak",                # int: consecutive kept actions
        "intent",                # str: current turn intent
        "phase",                 # str: current conversation phase
        "needs_now",             # str: what user needs this turn
        "turn_count",            # int: total turns in this conversation
        "last_turn_heavy",       # bool: was last turn emotionally heavy
        "contradictions",        # list: detected contradictions
        "vulnerability_history", # int: how many times user has been vulnerable
    )

    def __init__(self):
        for attr in self.__slots__:
            setattr(self, attr, None)


# ---------------------------------------------------------------------------
# Strategy output
# ---------------------------------------------------------------------------
class Strategy:
    __slots__ = ("type", "timing", "payload", "reason")

    def __init__(self, strategy_type: str = "reflect", timing: str = "now",
                 payload: Optional[str] = None, reason: str = ""):
        self.type = strategy_type
        self.timing = timing
        self.payload = payload
        self.reason = reason

    def to_dict(self) -> dict:
        return {"type": self.type, "timing": self.timing,
                "payload": self.payload, "reason": self.reason}


# ---------------------------------------------------------------------------
# State detection helpers
# ---------------------------------------------------------------------------
def _safety_level(understanding: Optional[dict], turn_count: int,
                  vulnerability_history: int, streak: int) -> float:
    """Compute safety level from available signals."""
    score = 0.0
    # Turns together build safety
    score += min(turn_count / 20, 0.3)  # up to 0.3 over 20 turns
    # Vulnerability history: they've opened up before
    score += min(vulnerability_history * 0.1, 0.3)  # up to 0.3
    # Streak shows commitment
    score += min(streak * 0.05, 0.2)  # up to 0.2
    # Understanding depth: do we actually know them?
    if understanding:
        filled = sum(1 for v in understanding.values()
                     if isinstance(v, str) and v.strip())
        score += min(filled * 0.04, 0.2)  # up to 0.2
    return min(round(score, 2), 1.0)


def _direction_quality(phase: str, consistency: float,
                       contradictions: list, intent: str) -> str:
    """Assess whether user is going in a good direction."""
    if phase in ("acting", "checking_in") and consistency >= 0.5:
        return "good"
    if contradictions and len(contradictions) >= 2:
        return "wrong"
    if intent == "setback" and consistency < 0.3:
        return "wrong"
    if phase == "exploring":
        return "unclear"
    return "unclear"


def _execution_readiness(phase: str, intent: str, consistency: float,
                         streak: int, needs_now: Optional[str]) -> str:
    """Assess whether user is ready to execute."""
    if phase in ("acting", "checking_in"):
        return "ready"
    if phase == "ready_to_act":
        if intent == "question":
            return "stuck"
        return "ready"
    if consistency < 0.3 and streak == 0:
        return "avoiding"
    if phase in ("exploring", "naming"):
        return "not_ready"
    return "not_ready"


def _needs_now(understanding: Optional[dict]) -> Optional[str]:
    """Extract what the user needs this turn from understanding."""
    if understanding and isinstance(understanding.get("needs_now"), str):
        return understanding["needs_now"].strip().lower() or None
    return None


def _detect_contradictions(substrate: Optional[dict]) -> list:
    """Extract contradiction history from substrate."""
    if substrate and isinstance(substrate.get("contradiction_history"), list):
        return substrate["contradiction_history"]
    return []


# ---------------------------------------------------------------------------
# Strategy decision logic
# ---------------------------------------------------------------------------
def decide_strategy(
    understanding: Optional[dict] = None,
    substrate: Optional[dict] = None,
    intent: str = "update",
    phase: str = "exploring",
    turn_count: int = 0,
    vulnerability_history: int = 0,
    patterns: Optional[dict] = None,
) -> Strategy:
    """Main entry point: given user state, return the optimal strategy.

    Args:
        understanding: The 'understanding' dict from engine (cross-session memory).
        substrate: The 'rolling_fields' dict (emotional_temperature, consistency, etc).
        intent: Current turn intent (acknowledgment, setback, question, etc).
        phase: Current conversation phase (exploring, naming, etc).
        turn_count: Total turns in this conversation.
        vulnerability_history: How many times user has shared something vulnerable.
        patterns: Pattern detection results from pattern_detector (optional).

    Returns:
        Strategy object with type, timing, payload, and reason.
    """
    # --- 1. Build state ---
    s = UserState()
    s.understanding = understanding
    s.substrate = substrate
    s.intent = intent
    s.phase = phase
    s.turn_count = turn_count
    s.vulnerability_history = vulnerability_history
    s.contradictions = _detect_contradictions(substrate)
    s.emotional_temp = (substrate or {}).get("emotional_temperature", 0.5)
    s.execution_consistency = (substrate or {}).get("execution_consistency", 0.5)
    s.pace = (substrate or {}).get("pace_calibration", "on-track")
    s.streak = (substrate or {}).get("streak", 0)
    s.needs_now = _needs_now(understanding)
    s.safety_level = _safety_level(understanding, turn_count,
                                   vulnerability_history, s.streak)
    s.direction_quality = _direction_quality(phase, s.execution_consistency,
                                             s.contradictions, intent)
    s.execution_readiness = _execution_readiness(phase, intent,
                                                  s.execution_consistency,
                                                  s.streak, s.needs_now)

    # Pattern detection integration
    s.pattern_confidence = 0.0
    s.pattern_type = None
    if patterns:
        s.pattern_confidence = patterns.get("confidence", 0.0)
        s.pattern_type = patterns.get("pattern_type")

    # --- 2. Strategy decision tree ---

    # Priority 1: Retreat needed? (user showed resistance or last turn was heavy)
    if intent == "setback":
        return Strategy("retreat", "now",
                        reason="User reported a setback — back off, acknowledge, rebuild safety")

    # Priority 2: Get out of the way (user has momentum)
    if (s.execution_readiness == "ready" and s.direction_quality == "good"
            and s.streak >= 2 and s.execution_consistency >= 0.6):
        return Strategy("get_out_of_way", "now",
                        reason="User has momentum and clear direction — minimal interference")

    # Priority 3: Reveal pattern (high confidence, high safety)
    if (s.pattern_confidence >= 0.7 and s.safety_level >= 0.65
            and s.pattern_type):
        return Strategy("reveal_pattern", "now",
                        payload=patterns.get("observation"),
                        reason=f"High-confidence pattern detected: {s.pattern_type}")

    if (s.pattern_confidence >= 0.5 and s.safety_level >= 0.5
            and s.pattern_type):
        return Strategy("reveal_pattern", "seed",
                        payload=patterns.get("observation"),
                        reason=f"Medium-confidence pattern detected: {s.pattern_type} — seeding")

    # Priority 4: Name the unspoken (contradictions, avoidance, fear visible)
    if s.contradictions and s.safety_level >= 0.6:
        latest = s.contradictions[-1]
        return Strategy("name_unspoken", "now",
                        payload=latest,
                        reason=f"Contradiction detected with sufficient safety: {latest[:80]}")

    if s.contradictions and s.safety_level >= 0.4:
        latest = s.contradictions[-1]
        return Strategy("name_unspoken", "seed",
                        payload=latest,
                        reason=f"Contradiction detected, safety building — seeding: {latest[:80]}")

    # Priority 5: Reframe (wrong direction)
    if s.direction_quality == "wrong" and s.safety_level >= 0.5:
        return Strategy("reframe", "now",
                        reason="User is going in wrong direction — offer new frame")

    # Priority 6: Force choice (ready but hesitating)
    if (s.execution_readiness in ("ready", "stuck")
            and s.phase in ("ready_to_act", "acting")):
        return Strategy("force_choice", "now",
                        reason="User is ready to act — commit to a concrete next action")

    # Priority 7: Handle by needs_now
    if s.needs_now == "encouragement" and s.execution_consistency < 0.4:
        return Strategy("reflect", "now",
                        reason="User needs encouragement and consistency is low — warm reflect")

    # Priority 8: Handle by intent
    if intent == "silence_breaker":
        return Strategy("reflect", "now",
                        reason="User returned after silence — warm re-engagement")

    if intent == "drift" and turn_count > 5:
        return Strategy("name_unspoken", "seed",
                        reason="Shallow engagement detected — plant gentle observation")

    # Default: reflect
    if s.safety_level < 0.4:
        return Strategy("reflect", "now",
                        reason="Safety still building — listen and acknowledge")

    return Strategy("reflect", "now",
                    reason="No strong signal — reflect and stay present")


# ---------------------------------------------------------------------------
# Prompt block builder — injects strategy into LLM prompt
# ---------------------------------------------------------------------------
STRATEGY_PROMPTS = {
    "reflect": (
        "HOW TO RESPOND THIS TURN:\n"
        "Listen and reflect. Show you heard them. No deep observations yet — "
        "just be present, acknowledge what they said, and leave a light opening "
        "for them to continue.\n"
    ),
    "name_unspoken": (
        "HOW TO RESPOND THIS TURN:\n"
        "There's something beneath what they're saying — a tension, a fear, "
        "a contradiction they haven't named. Reflect what they said first, "
        "then gently name what you sense underneath. Soft opener: 'I may be "
        "wrong, but…' or 'It sounds a little like…'. Make it a statement, "
        "not an accusation.\n"
    ),
    "reveal_pattern": (
        "HOW TO RESPOND THIS TURN:\n"
        "You've noticed a pattern across your conversations with this person. "
        "They may not see it themselves. After acknowledging what they said, "
        "gently name the pattern you've observed — connect what's happening "
        "now to what's happened before. Frame it as an observation, not a "
        "diagnosis. 'I've noticed something…' or 'This might be familiar…'\n"
    ),
    "reframe": (
        "HOW TO RESPOND THIS TURN:\n"
        "The user may be looking at this from a perspective that isn't serving "
        "them. After reflecting what they said, offer a different way to see "
        "the situation — a reframe that opens new possibilities. Don't tell "
        "them they're wrong. Offer the new frame as a question or possibility: "
        "'What if the real question isn't X, but Y?'\n"
    ),
    "force_choice": (
        "HOW TO RESPOND THIS TURN:\n"
        "The user is ready to act but needs to commit. After a brief reflection, "
        "present ONE concrete choice and ask for commitment. Make it easy to "
        "say yes to. 'Here's what I'd do if I were you: X. Want to lock it in?'\n"
    ),
    "retreat": (
        "HOW TO RESPOND THIS TURN:\n"
        "The user hit a setback or the last turn was heavy. Lead with warmth "
        "and permission. Acknowledge the difficulty without pushing. Give them "
        "space — they can share more if they want, or set it aside. 'That's "
        "tough. You don't have to figure this out right now.'\n"
    ),
    "get_out_of_way": (
        "HOW TO RESPOND THIS TURN:\n"
        "The user has momentum. Keep your response minimal. Acknowledge their "
        "progress briefly, encourage them to keep going, and get out of their "
        "way. Don't add new questions or observations. 'You're on a roll. Go "
        "do it — tell me how it went.'\n"
    ),
}


def strategy_prompt_block(strategy: Strategy) -> str:
    """Build the strategy instruction block to inject into the LLM prompt."""
    base = STRATEGY_PROMPTS.get(strategy.type, STRATEGY_PROMPTS["reflect"])
    if strategy.payload:
        payload_line = f"\nOBSERVATION TO WEAVE IN (if timing is right):\n{strategy.payload}\n"
    else:
        payload_line = ""
    return f"\n{base}{payload_line}"
