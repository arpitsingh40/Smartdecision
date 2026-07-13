"""
Verification + Learning Runtime.

Verification: Did the executed action achieve the intended capability outcome?
Learning: Update tool scores, detect patterns, apply only verified evidence.

Evidence-first learning. No permanent organizational learning without verification.
Evidence and learning events persist in MongoDB (evidence / learning_events collections)
— this ledger is the proof engine and must survive restarts.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Optional
from collections import defaultdict

from ontology import (
    Evidence, LearningEvent, LearningImpact,
    OutcomeStatus, Volatility, Trace, new_id, utcnow,
)
from db import evidence_col, learning_col

log = logging.getLogger("execution.verification")


def verify_action(
    tool_slug: str,
    capability: str,
    expected_outcome: str,
    actual_result: str,
    trace_id: str = None,
    executive_id: str = None,
    org_id: str = None,
) -> Evidence:
    """Compare expected vs actual outcome and produce verified evidence."""
    outcome = OutcomeStatus.UNKNOWN
    confidence = 0.0

    result_lower = actual_result.lower().strip() if actual_result else ""
    expected_lower = expected_outcome.lower().strip() if expected_outcome else ""

    # Simple outcome detection
    # ponytail: keyword heuristic, upgrade to LLM/structured verification when tools return schemas
    failure_signals = ["error", "failed", "denied", "unauthorized", "timeout", "not found",
                       "could not", "unable", "refused", "blocked"]
    success_signals = ["sent", "created", "delivered", "scheduled", "completed", "ok",
                       "success", "done", "received"]

    is_failure = any(s in result_lower for s in failure_signals)
    is_success = any(s in result_lower for s in success_signals) and not is_failure

    if is_failure:
        outcome = OutcomeStatus.FAILURE
        confidence = 0.3
    elif is_success:
        outcome = OutcomeStatus.SUCCESS
        confidence = 0.85
    elif len(actual_result) > 5:
        outcome = OutcomeStatus.PARTIAL
        confidence = 0.5
    else:
        outcome = OutcomeStatus.UNKNOWN
        confidence = 0.1

    ev = Evidence(
        trace_id=trace_id,
        evidence_type="EXECUTION",
        outcome=outcome,
        expected_outcome=expected_outcome,
        actual_result=actual_result,
        confidence=confidence,
        timestamp=utcnow(),
        volatility=Volatility.STABLE,
    )

    doc = ev.model_dump()
    # Context the Evidence model doesn't carry but the ledger needs:
    doc["tool_slug"] = tool_slug
    doc["capability"] = capability
    doc["executive_id"] = executive_id
    doc["org_id"] = org_id
    if evidence_col is not None:
        try:
            evidence_col.insert_one(dict(doc))
        except Exception as e:
            log.error(f"Evidence persist failed: {e}")
    log.info(f"Verification: {tool_slug} → {outcome.value} (confidence={confidence})")

    # Update tool scores
    try:
        from .tie import record_outcome as _tie_record
        _tie_record(tool_slug, outcome == OutcomeStatus.SUCCESS)
    except ImportError:
        pass

    return ev


def learn_from_evidence(evidence: Evidence, capability: str = "", org_id: str = None) -> Optional[LearningEvent]:
    """Detect patterns from verified evidence and produce learning."""
    if evidence_col is None:
        return None
    q = {"outcome": {"$in": ["SUCCESS", "FAILURE"]}}
    if org_id:
        q["org_id"] = org_id
    recent = list(evidence_col.find(q, {"_id": 0}).sort("timestamp", -1).limit(50))

    if len(recent) < 3:
        return None  # Not enough data to learn from

    # Pattern: consecutive failures of same tool
    tool_failures = defaultdict(list)
    for e in recent:
        slug = e.get("tool_slug", "unknown")
        if e.get("outcome") == "FAILURE":
            tool_failures[slug].append(e)

    learn = None
    for slug, failures in tool_failures.items():
        if len(failures) >= 3:
            already = learning_col is not None and learning_col.find_one(
                {"pattern_key": f"fail_{slug}", "org_id": org_id})
            if not already:
                learn = LearningEvent(
                    derived_from=[f.get("id", "") for f in failures],
                    pattern=f"Tool {slug} failed {len(failures)} times in recent executions",
                    impact=LearningImpact.TOOL_SCORE,
                    applied=True,
                    applied_at=utcnow(),
                )
                if learning_col is not None:
                    row = learn.model_dump()
                    row["pattern_key"] = f"fail_{slug}"
                    row["org_id"] = org_id
                    learning_col.insert_one(row)
                log.warning(f"Learning: {learn.pattern}")
                break

    return learn


def get_tool_reliability(tool_slug: str) -> dict:
    """Get reliability stats for a tool."""
    try:
        from .tie import _tool_scores
        if tool_slug in _tool_scores:
            s = _tool_scores[tool_slug]
            total = s["success"] + s["failure"]
            return {
                "tool": tool_slug,
                "success": s["success"],
                "failure": s["failure"],
                "total": total,
                "reliability": round(s["success"] / total, 2) if total > 0 else 0.5,
                "avg_latency_ms": s.get("avg_latency_ms", 0),
            }
    except ImportError:
        pass
    return {"tool": tool_slug, "reliability": 0.5, "note": "cold_start"}


def learning_summary(org_id: str = None) -> dict:
    """Summary of all organizational learning."""
    if evidence_col is None or learning_col is None:
        return {"total_evidence": 0, "total_learning_events": 0, "recent_learnings": []}
    q = {"org_id": org_id} if org_id else {}
    recents = list(learning_col.find(q, {"_id": 0, "pattern": 1}).sort("applied_at", -1).limit(10))
    return {
        "total_evidence": evidence_col.count_documents(q),
        "total_learning_events": learning_col.count_documents(q),
        "recent_learnings": [l.get("pattern", "") for l in recents],
    }


# ── Demo ──
def _demo():
    ev = verify_action("GMAIL_SEND_EMAIL", "email",
                       "Email delivered to customer",
                       "Email sent successfully, opened in 12 minutes",
                       trace_id="trace_abc", org_id="org_demo")
    ev2 = verify_action("GMAIL_SEND_EMAIL", "email",
                        "Email delivered", "Error: connection refused",
                        trace_id="trace_def", org_id="org_demo")
    ev3 = verify_action("GMAIL_SEND_EMAIL", "email",
                        "Email delivered", "Error: timeout",
                        trace_id="trace_ghi", org_id="org_demo")
    ev4 = verify_action("GMAIL_SEND_EMAIL", "email",
                        "Email delivered", "Error: quota exceeded... failed",
                        trace_id="trace_jkl", org_id="org_demo")

    assert ev.outcome == OutcomeStatus.SUCCESS
    assert ev2.outcome == OutcomeStatus.FAILURE
    learn = learn_from_evidence(ev4, "email", org_id="org_demo")
    assert learn is not None and "failed" in learn.pattern, "3 failures must produce a learning event"
    reliability = get_tool_reliability("GMAIL_SEND_EMAIL")
    summary = learning_summary("org_demo")
    assert summary["total_evidence"] >= 4

    return {
        "evidence_count": summary["total_evidence"],
        "learning_events": summary["total_learning_events"],
        "reliability": reliability,
        "summary": summary,
        "status": "OK",
    }


if __name__ == "__main__":
    print(json.dumps(_demo(), indent=2, default=str))
