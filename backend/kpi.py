"""Launch KPI instrumentation (Founder Decision Intelligence Launch Checklist).

Two parts:
1. /api/kpi/signal  - one-tap user signals for KPI 1 (problem detection accuracy) and
   KPI 2 (decision improvement rate). Idempotent per (user, kind, decision): re-tapping
   REPLACES the previous value, so a user can never double-count themselves.
2. /api/admin/launch-readiness - the five launch KPIs computed live from real usage
   (pure Mongo aggregation, zero LLM) + the latest release-gate verdict.
"""
import uuid
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from db import users_col, decisions_col, kpi_events_col, gates_col, members_col
from security import current_user, require_admin, now_utc

log = logging.getLogger("kpi")
router = APIRouter(prefix="/api/kpi", tags=["kpi"])
launch_router = APIRouter(prefix="/api/admin", tags=["admin"])

KINDS = ("problem_detection", "decision_improvement")


def ensure_kpi_startup():
    """Idempotent indexes. Called from server startup."""
    kpi_events_col.create_index([("user_id", 1), ("kind", 1), ("dedupe", 1)], unique=True)
    kpi_events_col.create_index([("kind", 1), ("at", -1)])


def _iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


class SignalIn(BaseModel):
    kind: str = Field(min_length=3, max_length=40)
    value: bool
    decision_id: str | None = Field(default=None, max_length=80)


@router.post("/signal")
def kpi_signal(body: SignalIn, user: dict = Depends(current_user)):
    """One-tap KPI signal. kind=problem_detection ('did this name your real problem?')
    or decision_improvement ('did this change or improve your decision?').
    Idempotent: same user + kind + decision replaces the previous answer."""
    kind = body.kind.strip().lower()
    if kind not in KINDS:
        raise HTTPException(422, f"kind must be one of {', '.join(KINDS)}")
    dedupe = body.decision_id or ("day-" + now_utc().strftime("%Y%m%d"))
    m = members_col.find_one({"user_id": user["id"], "status": "active"})
    kpi_events_col.update_one(
        {"user_id": user["id"], "kind": kind, "dedupe": dedupe},
        {"$set": {"value": bool(body.value), "decision_id": body.decision_id,
                  "org_id": (m or {}).get("org_id"), "at": now_utc()},
         "$setOnInsert": {"id": str(uuid.uuid4())}},
        upsert=True)
    return {"ok": True, "kind": kind, "value": bool(body.value)}


# ----------------------------------------------------------------- admin: the 5 launch KPIs
def _pct(part, whole):
    return round(100 * part / whole) if whole else None


def _kpi_signal_stats(kind):
    yes = kpi_events_col.count_documents({"kind": kind, "value": True})
    no = kpi_events_col.count_documents({"kind": kind, "value": False})
    return {"yes": yes, "no": no, "n": yes + no, "pct": _pct(yes, yes + no)}


@launch_router.get("/launch-readiness")
def launch_readiness(admin: dict = Depends(require_admin)):
    """The five launch KPIs from the Founder Decision Intelligence Launch Checklist,
    computed live from real usage. Honest: every KPI carries its n; no data -> null pct."""
    from decision_brain import calibration_for  # deferred import (avoids circular load)

    now = now_utc()
    # KPI 1 + 2: one-tap user signals
    kpi1 = _kpi_signal_stats("problem_detection")
    kpi2 = _kpi_signal_stats("decision_improvement")

    # KPI 3: execution rate (index-backed counts, platform-wide)
    committed = decisions_col.count_documents({"committed_action": {"$ne": None}})
    done = decisions_col.count_documents({"status": "done"})
    dropped = decisions_col.count_documents({"status": "dropped"})
    open_c = decisions_col.count_documents({"status": "open", "committed_action": {"$ne": None}})
    kpi3 = {"committed": committed, "done": done, "dropped": dropped, "open": open_c,
            "completion_pct": _pct(done, committed),
            "follow_through_pct": _pct(done, done + dropped)}

    # KPI 4: outcome improvement (outcome-scored decisions + rupee tally + calibration)
    oc = {s: decisions_col.count_documents({"outcome.status": s}) for s in ("success", "partial", "failed")}
    n_oc = sum(oc.values())
    positive = round(100 * (oc["success"] + 0.5 * oc["partial"]) / n_oc) if n_oc else None
    imp = list(decisions_col.aggregate([
        {"$match": {"impact_inr": {"$ne": None}}},
        {"$group": {"_id": None, "total": {"$sum": "$impact_inr"}, "n": {"$sum": 1}}}]))
    kpi4 = {"outcomes": oc, "n": n_oc, "positive_pct": positive,
            "impact_inr_total": int(imp[0]["total"]) if imp else 0,
            "impact_reports": int(imp[0]["n"]) if imp else 0,
            "calibration": calibration_for({})}

    # KPI 5: return rate (non-admin users who came back at least a day after signup)
    week_ago = now - timedelta(days=7)
    eligible = users_col.count_documents({"created_at": {"$lte": week_ago}, "is_admin": {"$ne": True}})
    returned = users_col.count_documents({
        "created_at": {"$lte": week_ago}, "is_admin": {"$ne": True},
        "$expr": {"$gte": ["$last_active_at", {"$add": ["$created_at", 24 * 3600 * 1000]}]}})
    active_7d = users_col.count_documents({"last_active_at": {"$gte": week_ago}, "is_admin": {"$ne": True}})
    kpi5 = {"eligible": eligible, "returned": returned, "return_pct": _pct(returned, eligible),
            "active_7d": active_7d}

    # Latest release-gate verdict (the four gates)
    latest = gates_col.find_one({}, {"_id": 0}, sort=[("started_at", -1)])
    gate = None
    if latest:
        gate = {"id": latest.get("id"), "status": latest.get("status"),
                "overall": latest.get("overall"), "started_at": _iso(latest.get("started_at"))}

    return {"kpi1_problem_detection": kpi1, "kpi2_decision_improvement": kpi2,
            "kpi3_execution": kpi3, "kpi4_outcome": kpi4, "kpi5_return": kpi5,
            "release_gate": gate, "generated_at": _iso(now)}
