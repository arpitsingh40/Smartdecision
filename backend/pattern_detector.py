"""Pattern Detector — longitudinal analysis of user behavior across sessions.

Detects recurring patterns in how a user shows up, makes decisions, and responds
to challenges. Stores findings in user_patterns collection for use by the
question strategy engine.

Pattern types detected:
  - approach_avoid:  User gets excited, takes first step, then disappears
  - same_stuck:      User keeps hitting the same blocker in different contexts
  - commitment_fear:  User gets to the point of committing, then pulls back
  - reframe_resist:   User consistently rejects new frames or advice
  - blame_external:   User consistently attributes setbacks to external factors
  - perfection_delay: User delays action waiting for "perfect" conditions
  - scope_creep:      User keeps expanding the problem instead of narrowing

Usage:
  patterns = detect_patterns(understanding_history, substrate_history, user_id, thread_id)
  # Returns: {"pattern_type": str|None, "confidence": 0-1, "observation": str|None,
  #           "evidence_count": int, "first_observed": iso|None, "latest_observed": iso|None}
"""

from __future__ import annotations
from typing import Optional
from datetime import datetime
from collections import Counter

# ---------------------------------------------------------------------------
# Pattern definitions — what to look for
# ---------------------------------------------------------------------------

PATTERN_SIGNATURES = {
    "approach_avoid": {
        "label": "Approach-avoid cycle",
        "description": "Gets excited, starts, then disappears when it gets real",
        "indicators": [
            "streak drops to 0 after initial enthusiasm",
            "pace shifts from ahead to behind",
            "long gaps after phase reaches ready_to_act or acting",
            "emotional_temp drops sharply after initial high",
        ],
    },
    "same_stuck": {
        "label": "Same stuck point",
        "description": "Keeps hitting the same blocker across different goals",
        "indicators": [
            "same blocker keyword appears across multiple threads",
            "fears field shows same content across sessions",
            "gap_to_goal doesn't shrink over time",
        ],
    },
    "commitment_fear": {
        "label": "Commitment fear",
        "description": "Gets to commitment point, then pulls back or changes topic",
        "indicators": [
            "phase oscillates between naming and ready_to_act without advancing",
            "user sends drift or question intent when phase is ready_to_act",
            "multiple 'not yet' or 'let me think' responses to consent questions",
        ],
    },
    "reframe_resist": {
        "label": "Reframe resistance",
        "description": "Consistently rejects or deflects new perspectives",
        "indicators": [
            "mirror observations are dismissed or ignored",
            "user repeats same question in different wording",
            "understanding.blockers stays empty or unchanged after reframes",
        ],
    },
    "perfection_delay": {
        "label": "Perfection delay",
        "description": "Waits for perfect conditions before acting",
        "indicators": [
            "execution_consistency stays low despite high emotional_temp",
            "needs_now frequently 'more information' or 'clarity'",
            "user asks many questions before acting",
            "phase stays in exploring/naming longer than expected",
        ],
    },
}

# How many observations needed for each confidence level
CONFIDENCE_THRESHOLDS = {
    0.3: 1,   # seed: first observation
    0.5: 2,   # medium: repeated observation
    0.7: 3,   # high: confirmed pattern
    0.9: 5,   # very high: established pattern
}


# ---------------------------------------------------------------------------
# Pattern detection logic
# ---------------------------------------------------------------------------

def _check_approach_avoid(history: list[dict], recent: list[dict]) -> tuple[float, Optional[str]]:
    """Detect approach-avoid cycle."""
    evidence = 0
    obs_parts = []

    # Check for enthusiasm drop
    temps = [h.get("emotional_temp", 0.5) for h in history if h.get("emotional_temp")]
    if len(temps) >= 4:
        early_avg = sum(temps[:2]) / 2
        late_avg = sum(temps[-2:]) / 2
        if early_avg - late_avg > 0.3:
            evidence += 1
            obs_parts.append("emotional temperature dropped significantly from early enthusiasm")

    # Check for streak breaking
    streaks = [h.get("streak", 0) for h in recent if h.get("streak") is not None]
    if len(streaks) >= 3:
        if streaks[0] > 0 and streaks[-1] == 0:
            evidence += 1
            obs_parts.append("streak broke after initial progress")

    # Check for long gaps after engagement
    if len(recent) >= 4:
        phases = [h.get("phase") for h in recent[-4:] if h.get("phase")]
        if "ready_to_act" in phases or "acting" in phases:
            # Check if there's a gap after reaching action phase
            gaps = [h.get("days_gap", 0) for h in recent[-3:] if h.get("days_gap") is not None]
            if gaps and max(gaps) > 7:
                evidence += 1
                obs_parts.append("long gap after reaching action phase")

    if evidence == 0:
        return 0.0, None

    confidence = min(evidence * 0.25, 0.9)
    observation = ("You tend to start with real energy — then something shifts "
                   "when it stops being new and starts being real. "
                   "I've seen this rhythm a few times now.") if obs_parts else None
    return confidence, observation


def _check_same_stuck(history: list[dict]) -> tuple[float, Optional[str]]:
    """Detect same blocker appearing across different contexts."""
    evidence = 0
    blockers_seen = []

    for h in history:
        blockers = h.get("blockers", "")
        if isinstance(blockers, str) and blockers.strip():
            blockers_seen.append(blockers.strip().lower())

    if len(blockers_seen) < 2:
        return 0.0, None

    # Find common keywords across different blocker descriptions
    all_words = []
    for b in blockers_seen:
        words = set(w for w in b.split() if len(w) > 3)
        all_words.extend(words)
    common = [w for w, c in Counter(all_words).most_common(3) if c >= 2]

    evidence = len(common)
    if evidence == 0:
        return 0.0, None

    confidence = min(evidence * 0.25, 0.8)
    keyword_hint = common[0] if common else ""
    observation = (f"I keep noticing '{keyword_hint}' come up — "
                   "across different things you're working on. "
                   "It may be the same wall showing up in different rooms.") if keyword_hint else None
    return confidence, observation


def _check_commitment_fear(recent: list[dict]) -> tuple[float, Optional[str]]:
    """Detect pattern of pulling back at commitment point."""
    evidence = 0
    obs_parts = []

    phases = [h.get("phase") for h in recent if h.get("phase")]
    intents = [h.get("intent") for h in recent if h.get("intent")]

    # Check for phase oscillation around ready_to_act
    if "ready_to_act" in phases:
        # Count how many times we've been at ready_to_act
        ready_count = phases.count("ready_to_act")
        acting_count = phases.count("acting")
        if ready_count >= 2 and acting_count == 0:
            evidence += 1
            obs_parts.append("multiple times at commitment point without advancing")

    # Check for drift/question intent at commitment point
    if len(phases) >= 3 and len(intents) >= 3:
        for i in range(1, len(phases)):
            if phases[i-1] == "ready_to_act" and intents[i] in ("drift", "question"):
                evidence += 1
                obs_parts.append("deflected with a question at commitment point")
                break

    if evidence == 0:
        return 0.0, None

    confidence = min(evidence * 0.3, 0.85)
    observation = ("I've noticed something: when we get to the point of locking "
                   "in a real commitment, something pulls you away. "
                   "Noticing it — not judging it.") if obs_parts else None
    return confidence, observation


def _check_reframe_resist(recent: list[dict]) -> tuple[float, Optional[str]]:
    """Detect resistance to new frames or perspectives."""
    evidence = 0

    # Check if understanding shows blockers unchanged despite suggestions
    understandings = [h.get("understanding", {}) for h in recent if h.get("understanding")]
    if understandings:
        blockers_values = [u.get("blockers", "") for u in understandings if u.get("blockers")]
        if len(blockers_values) >= 3:
            unique_blockers = len(set(b.strip().lower() for b in blockers_values if isinstance(b, str)))
            if unique_blockers <= 1 and len(blockers_values) >= 3:
                evidence += 1

    if evidence == 0:
        return 0.0, None

    confidence = min(evidence * 0.3, 0.6)
    observation = ("You tend to hold onto your initial frame pretty tightly — "
                   "even when new angles come up. That persistence is useful "
                   "in some places; in others it might be the thing that's "
                   "keeping you stuck.") if evidence else None
    return confidence, observation


# ---------------------------------------------------------------------------
# Main detection function
# ---------------------------------------------------------------------------

def detect_patterns(
    understanding_history: list[dict],
    substrate_history: list[dict],
    user_id: str,
    thread_id: str,
) -> dict:
    """Run all pattern detectors against user history.

    Args:
        understanding_history: List of understanding dicts across sessions.
        substrate_history: List of rolling_fields snapshots across turns.
        user_id: User identifier.
        thread_id: Current thread identifier.

    Returns:
        dict with keys: pattern_type, confidence, observation, evidence_count
    """
    detectors = [
        ("approach_avoid", _check_approach_avoid, [substrate_history, substrate_history[-10:] if len(substrate_history) > 10 else substrate_history]),
        ("same_stuck", _check_same_stuck, [understanding_history]),
        ("commitment_fear", _check_commitment_fear, [substrate_history[-15:] if len(substrate_history) > 15 else substrate_history]),
        ("reframe_resist", _check_reframe_resist, [substrate_history[-15:] if len(substrate_history) > 15 else substrate_history]),
    ]

    best_pattern = None
    best_confidence = 0.0
    best_observation = None

    for pattern_type, detector_fn, args in detectors:
        try:
            confidence, observation = detector_fn(*args)
            if confidence > best_confidence:
                best_confidence = confidence
                best_pattern = pattern_type
                best_observation = observation
        except Exception:
            continue

    return {
        "pattern_type": best_pattern,
        "confidence": round(best_confidence, 2),
        "observation": best_observation,
        "evidence_count": round(best_confidence * 4) if best_confidence > 0 else 0,
    }
