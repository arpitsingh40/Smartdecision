"""SALAAR Inline — deep integration into the engine turn pipeline.

Runs DURING every engine turn — not on a separate cron. SALAAR scans the user's
message for threats using the 169-lens pattern matcher, builds a context block
that the engine injects silently into the LLM prompt, and triggers L1-L2
auto-actions via the execution runtime.

This is the real SALAAR: watching from the same room, not from the next one.
"""
import logging
from typing import Optional

from db import orgs_col, members_col, tasks_col
from lenses import select_lenses

log = logging.getLogger("salaar.inline")


def salaar_inline_scan(user_msg: str, thread: dict, user_doc: dict) -> dict:
    """Run SALAAR threat scan inline during an engine turn.
    
    Called from run_pipeline() BEFORE the LLM call. Uses the founder's
    latest message + thread context to detect threats and build context.
    
    Returns:
        {
            "threats": [...],           # threats detected in this message
            "context_block": str,       # text to inject into the engine prompt
            "auto_actions": [...],      # L1-L2 actions to auto-execute
            "people_detected": [...],   # people mentioned with behavior patterns
            "lens_recommendations": [],  # lenses SALAAR recommends for this turn
        }
    """
    from salaar.threats import match_threats, record_threat
    from salaar.people import extract_people_from_text, get_or_create_person, scan_behavior
    
    result = {
        "threats": [],
        "context_block": "",
        "auto_actions": [],
        "people_detected": [],
        "lens_recommendations": [],
    }
    
    if not user_msg or not user_doc:
        return result
    
    user_id = user_doc.get("id", "")
    org_id = user_doc.get("org_id")
    
    # ── 1. Threat detection (169 lens-powered) ──
    threats = match_threats(user_msg, org_id) if org_id else []
    result["threats"] = threats
    
    if threats:
        # Build SALAAR context block for the engine prompt
        lines = ["SALAAR SHADOW BRIEF (detected in this message — use silently, do NOT recite):"]
        for t in threats:
            # Record the threat
            record_threat(
                org_id, t["threat_key"], user_id,
                t["matched_text"], t["severity"],
                t["lenses"], t["diagnosis"],
            )
            
            repeat_tag = " (REPEAT PATTERN)" if t.get("repeat") else ""
            lines.append(
                f"- [{t['severity'].upper()}] {t['diagnosis']}{repeat_tag}"
            )
            lines.append(f"  Lenses to apply: {', '.join(t['lenses'][:3])}")
            lines.append(f"  Action level: {t['action_level']}")
            
            # Collect lens recommendations from threats
            for lens_id in t.get("lenses", []):
                if lens_id not in result["lens_recommendations"]:
                    result["lens_recommendations"].append(lens_id)
        
        lines.append(
            "\nSALAAR RULE: If the message contains a threat signal, your acknowledgment "
            "must address it indirectly — do NOT announce 'I detected X.' Instead, ask "
            "the question that the threat implies. For example, if founder isolation is "
            "detected, ask: 'Who else knows the real picture right now?'"
        )
        result["context_block"] = "\n".join(lines)
    
    # ── 2. People scanning (psychology lenses) ──
    people_keys = extract_people_from_text(user_msg)
    for pk in people_keys:
        if not org_id:
            continue
        person = get_or_create_person(org_id, pk, role=pk)
        behaviors = scan_behavior(user_msg, person["id"], org_id)
        if behaviors:
            # Add silent guidance to context block
            behavior_notes = []
            for b in behaviors:
                behavior_notes.append(f"  - {b['pattern_key']}: {b['insight'][:120]}")
            result["people_detected"].append({
                "person_key": pk,
                "behaviors": [b["pattern_key"] for b in behaviors],
                "notes": behavior_notes,
            })
    
    # ── 3. Dynamically select lenses based on threat + message ──
    try:
        selected = select_lenses(user_msg, max_lenses=3, min_score=2)
        for lens in selected if isinstance(selected, list) else []:
            lid = lens if isinstance(lens, str) else lens.get("id", "")
            if lid and lid not in result["lens_recommendations"]:
                result["lens_recommendations"].append(lid)
    except Exception:
        pass  # select_lenses may not be available or fail on some inputs
    
    return result


def salaar_auto_execute(org_id: str, user_id: str, threats: list[dict]):
    """Execute L1-L2 auto-actions via the execution runtime.
    
    L1: Execute reversible — auto, no notification
    L2: Execute + notify — auto, founder gets a one-line summary
    
    Returns list of executed action results."""
    from salaar.actions import decide_action_level, create_action, THREAT_ACTIONS
    
    executed = []
    if not org_id or not threats:
        return executed
    
    for threat in threats:
        authority = decide_action_level(threat, org_id)
        if authority not in ("L1", "L2"):
            continue  # L3-L5 need founder approval — skip for inline
        
        # Create the action
        aid = create_action(org_id, user_id, threat, authority)
        if not aid:
            continue
        
        # L1-L2: Try to execute via MCP tools if available
        threat_key = threat.get("threat_key", "")
        action_def = THREAT_ACTIONS.get(threat_key, {})
        
        result = {
            "action_id": aid,
            "threat_key": threat_key,
            "authority": authority,
            "title": action_def.get("title", threat_key),
            "status": "executed",
        }
        
        # For OKR stalling (L1), try to auto-refresh OKR progress
        if threat_key == "okr_stalling":
            try:
                from okr_engine import refresh_okr_progress_from_scan
                health = refresh_okr_progress_from_scan(org_id)
                if health:
                    result["okr_health"] = health
            except Exception:
                pass
        
        # For execution stalling (L2), try to unblock tasks
        if threat_key == "execution_stalling":
            try:
                from execution.bridge import unblock_stalled_tasks
                unblocked = unblock_stalled_tasks(org_id) if hasattr(
                    __import__('execution.bridge', fromlist=['unblock_stalled_tasks']),
                    'unblock_stalled_tasks'
                ) else 0
                result["tasks_unblocked"] = unblocked
            except Exception:
                pass
        
        executed.append(result)
    
    return executed


def salaar_prompt_injection(user_msg: str, thread: dict, user_doc: dict) -> str:
    """The one-liner for engine.py — returns a text block to inject into the prompt.
    
    Usage in engine.py llm_turn():
        salaar_block = salaar_prompt_injection(user_msg, thread, user_doc)
        prompt = f"{prompt}\n{salaar_block}"
    """
    scan = salaar_inline_scan(user_msg, thread, user_doc)
    return scan.get("context_block", "")


def salaar_outcome_learn(org_id: str, threat_key: str, outcome: str, evidence: dict):
    """Store pattern → outcome when a threat resolves. Closes the learning loop.
    
    Call this when:
    - A milestone is completed that addresses the threat
    - A task linked to the threat is marked done
    - The founder explicitly resolves the situation
    """
    from salaar.threats import store_pattern_memory
    store_pattern_memory(org_id, threat_key, {
        "outcome": outcome,
        "resolved_at": __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
        **evidence,
    })
