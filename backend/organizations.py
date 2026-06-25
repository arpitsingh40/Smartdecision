"""Phase 1 — Organizations (company workspaces).

A founder creates ONE organization, then invites team members via a join link.
The org is the container that will later hold (Phase 2) the hidden strategy / North Star
and (Phase 3) the shared, founder-trained knowledge base. This module only builds the
container + membership + invites. No LLM, no credits.

Roles:
  owner  -> the company founder (distinct from platform `is_admin` / Founder OS)
  member -> a team member who joined via an invite link

Data model (all UUID ids, never Mongo ObjectId):
  organizations : {id, name, owner_user_id, member_count, created_at, + Phase-2 strategy fields}
  org_members   : {id, org_id, user_id, role, status(active|removed), joined_at}
  org_invites   : {id, org_id, code, email, role, created_by, status(pending|accepted|revoked),
                   created_at, accepted_by, accepted_at}
"""
import os
import json
import uuid
import secrets
import logging
from datetime import timedelta, datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr

from db import orgs_col, members_col, invites_col, users_col, decisions_col, plans_col
from security import current_user, now_utc
from engine import client, _extract_json

log = logging.getLogger("org")

router = APIRouter(prefix="/api/org", tags=["organizations"])

FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "").rstrip("/")


# ----------------------------------------------------------------- startup
def ensure_org_startup():
    """Idempotent indexes for the org layer. Called from server startup."""
    orgs_col.create_index("id", unique=True)
    orgs_col.create_index("owner_user_id")
    members_col.create_index("id", unique=True)
    members_col.create_index([("org_id", 1), ("user_id", 1)], unique=True)
    members_col.create_index([("user_id", 1), ("status", 1)])
    invites_col.create_index("id", unique=True)
    invites_col.create_index("code", unique=True)
    invites_col.create_index([("org_id", 1), ("status", 1)])
    plans_col.create_index("id", unique=True)
    plans_col.create_index([("org_id", 1), ("status", 1)])


# ----------------------------------------------------------------- models
class CreateOrgIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class InviteIn(BaseModel):
    email: EmailStr | None = None
    role: str = "member"


class JoinIn(BaseModel):
    code: str = Field(min_length=4, max_length=80)


class StrategyIn(BaseModel):
    """Founder-only hidden steering. NEVER exposed to members."""
    north_star: str = Field(default="", max_length=2000)
    target: str = Field(default="", max_length=300)
    deadline: str = Field(default="", max_length=120)
    priorities: list[str] = Field(default_factory=list)
    decision_rules: str = Field(default="", max_length=4000)
    # Layer 3: transparent pacing inputs (founder-entered, used only for arithmetic projection).
    current_arr: float | None = Field(default=None, ge=0)
    target_arr: float | None = Field(default=None, ge=0)


class ProgressIn(BaseModel):
    """Founder-only quick update of where the company is now (drives the Goal -> Progress tracker).
    Does NOT change the strategy or bump strategy_version - it only logs forward motion."""
    current_arr: float = Field(ge=0)


# ----------------------------------------------------------------- helpers
def _active_membership(user: dict) -> dict | None:
    return members_col.find_one({"user_id": user["id"], "status": "active"})


def _require_owner(user: dict) -> dict:
    m = members_col.find_one({"user_id": user["id"], "status": "active", "role": "owner"})
    if not m:
        raise HTTPException(403, "Only the workspace owner can do this")
    return m


def _org_view(org: dict, role: str) -> dict:
    """Member-safe org view. NEVER leaks the hidden strategy (Phase 2)."""
    return {
        "id": org["id"],
        "name": org["name"],
        "role": role,
        "member_count": int(org.get("member_count", 1)),
        "created_at": org.get("created_at"),
        "is_owner": role == "owner",
        # founder-only flag the UI uses to reveal the (Phase-2) strategy console
        "strategy_set": bool(org.get("north_star")),
    }


def _join_url(code: str) -> str:
    base = FRONTEND_BASE_URL or ""
    return f"{base}/join/{code}"


def _invite_view(inv: dict) -> dict:
    return {
        "id": inv["id"],
        "code": inv["code"],
        "email": inv.get("email") or "",
        "role": inv.get("role", "member"),
        "status": inv.get("status", "pending"),
        "created_at": inv.get("created_at"),
        "accepted_at": inv.get("accepted_at"),
        "join_url": _join_url(inv["code"]),
    }


# ----------------------------------------------------------------- endpoints
@router.post("")
def create_org(body: CreateOrgIn, user: dict = Depends(current_user)):
    """Create a company workspace. Caller becomes the owner (founder)."""
    if _active_membership(user):
        raise HTTPException(409, "You are already part of an organization")
    org = {
        "id": str(uuid.uuid4()),
        "name": body.name.strip(),
        "owner_user_id": user["id"],
        "member_count": 1,
        "created_at": now_utc(),
        # ---- Phase-2 hidden strategy (founder-only, never sent to members) ----
        "north_star": "", "target": "", "deadline": "",
        "priorities": [], "decision_rules": "", "strategy_updated_at": None,
        # ---- Layer 0/5: strategy versioning + pacing inputs ----
        "strategy_version": 0, "current_arr": None, "target_arr": None,
    }
    orgs_col.insert_one(org)
    members_col.insert_one({
        "id": str(uuid.uuid4()), "org_id": org["id"], "user_id": user["id"],
        "role": "owner", "status": "active", "joined_at": now_utc(),
    })
    users_col.update_one({"id": user["id"]}, {"$set": {"org_id": org["id"], "org_role": "owner"}})
    return _org_view(org, "owner")


@router.get("")
def my_org(user: dict = Depends(current_user)):
    """The caller's current workspace + their role. 404 if they have none."""
    m = _active_membership(user)
    if not m:
        raise HTTPException(404, "You are not part of any organization yet")
    org = orgs_col.find_one({"id": m["org_id"]})
    if not org:
        raise HTTPException(404, "Organization not found")
    return _org_view(org, m["role"])


@router.get("/members")
def list_members(user: dict = Depends(current_user)):
    """Owner-only roster of the workspace."""
    m = _require_owner(user)
    rows = list(members_col.find({"org_id": m["org_id"], "status": "active"}).sort("joined_at", 1))
    out = []
    for r in rows:
        u = users_col.find_one({"id": r["user_id"]}, {"_id": 0, "name": 1, "email": 1, "last_login_at": 1})
        out.append({
            "user_id": r["user_id"],
            "name": (u or {}).get("name", ""),
            "email": (u or {}).get("email", ""),
            "role": r["role"],
            "joined_at": r.get("joined_at"),
            "last_login_at": (u or {}).get("last_login_at"),
        })
    return {"members": out, "count": len(out)}


@router.delete("/members/{member_user_id}")
def remove_member(member_user_id: str, user: dict = Depends(current_user)):
    """Owner removes a member. Cannot remove the owner or themselves."""
    m = _require_owner(user)
    if member_user_id == user["id"]:
        raise HTTPException(400, "The owner cannot remove themselves")
    target = members_col.find_one({"org_id": m["org_id"], "user_id": member_user_id, "status": "active"})
    if not target:
        raise HTTPException(404, "Member not found")
    if target["role"] == "owner":
        raise HTTPException(400, "Cannot remove the owner")
    members_col.update_one({"id": target["id"]}, {"$set": {"status": "removed", "removed_at": now_utc()}})
    users_col.update_one({"id": member_user_id}, {"$set": {"org_id": None, "org_role": None}})
    orgs_col.update_one({"id": m["org_id"]}, {"$inc": {"member_count": -1}})
    return {"removed": True, "user_id": member_user_id}


@router.post("/invites")
def create_invite(body: InviteIn, user: dict = Depends(current_user)):
    """Owner creates a shareable join link (optionally tied to an email)."""
    m = _require_owner(user)
    code = secrets.token_urlsafe(9)
    inv = {
        "id": str(uuid.uuid4()),
        "org_id": m["org_id"],
        "code": code,
        "email": (str(body.email).lower() if body.email else ""),
        "role": "member",
        "created_by": user["id"],
        "status": "pending",
        "created_at": now_utc(),
        "accepted_by": None, "accepted_at": None,
    }
    invites_col.insert_one(inv)
    return _invite_view(inv)


@router.get("/invites")
def list_invites(user: dict = Depends(current_user)):
    """Owner sees all invites for the workspace."""
    m = _require_owner(user)
    rows = list(invites_col.find({"org_id": m["org_id"]}).sort("created_at", -1))
    return {"invites": [_invite_view(r) for r in rows]}


@router.post("/invites/{code}/revoke")
def revoke_invite(code: str, user: dict = Depends(current_user)):
    """Owner revokes a pending invite link."""
    m = _require_owner(user)
    inv = invites_col.find_one({"code": code, "org_id": m["org_id"]})
    if not inv:
        raise HTTPException(404, "Invite not found")
    if inv["status"] != "pending":
        raise HTTPException(409, f"Invite is already {inv['status']}")
    invites_col.update_one({"id": inv["id"]}, {"$set": {"status": "revoked"}})
    return {"revoked": True, "code": code}


@router.get("/invites/{code}")
def lookup_invite(code: str):
    """PUBLIC (no auth): the join landing page shows the org name before sign-in."""
    inv = invites_col.find_one({"code": code})
    if not inv or inv.get("status") != "pending":
        return {"valid": False}
    org = orgs_col.find_one({"id": inv["org_id"]}, {"_id": 0, "name": 1})
    return {
        "valid": True,
        "org_name": (org or {}).get("name", "this workspace"),
        "role": inv.get("role", "member"),
        "email": inv.get("email") or "",
    }


@router.post("/join")
def join_org(body: JoinIn, user: dict = Depends(current_user)):
    """Authenticated user accepts an invite and joins the workspace as a member."""
    if _active_membership(user):
        raise HTTPException(409, "You are already part of an organization")
    inv = invites_col.find_one({"code": body.code})
    if not inv:
        raise HTTPException(404, "Invite link is invalid")
    if inv["status"] != "pending":
        raise HTTPException(410, f"This invite link is {inv['status']}")
    org = orgs_col.find_one({"id": inv["org_id"]})
    if not org:
        raise HTTPException(404, "Organization no longer exists")
    members_col.insert_one({
        "id": str(uuid.uuid4()), "org_id": org["id"], "user_id": user["id"],
        "role": "member", "status": "active", "joined_at": now_utc(),
    })
    users_col.update_one({"id": user["id"]}, {"$set": {"org_id": org["id"], "org_role": "member"}})
    orgs_col.update_one({"id": org["id"]}, {"$inc": {"member_count": 1}})
    invites_col.update_one({"id": inv["id"]}, {"$set": {
        "status": "accepted", "accepted_by": user["id"], "accepted_at": now_utc(),
    }})
    return _org_view(org, "member")


# ----------------------------------------------------------------- hidden strategy (the moat)
def _strategy_view(org: dict) -> dict:
    return {
        "north_star": org.get("north_star", "") or "",
        "target": org.get("target", "") or "",
        "deadline": org.get("deadline", "") or "",
        "priorities": list(org.get("priorities", []) or []),
        "decision_rules": org.get("decision_rules", "") or "",
        "strategy_updated_at": org.get("strategy_updated_at"),
        "strategy_set": bool(org.get("north_star")),
        "strategy_version": org.get("strategy_version", 0),
        "current_arr": org.get("current_arr"),
        "target_arr": org.get("target_arr"),
    }


@router.get("/strategy")
def get_strategy(user: dict = Depends(current_user)):
    """Owner-only. The confidential North Star + priorities + rules. NEVER returned to members."""
    m = _require_owner(user)
    org = orgs_col.find_one({"id": m["org_id"]})
    if not org:
        raise HTTPException(404, "Organization not found")
    return _strategy_view(org)


@router.put("/strategy")
def set_strategy(body: StrategyIn, user: dict = Depends(current_user)):
    """Owner-only. Saves the hidden steering that silently guides every member's decisions.
    Layer 5: a meaningful change to the strategy bumps strategy_version, so every decision is
    stamped with the strategy that was active when it was made (before/after comparisons)."""
    m = _require_owner(user)
    org = orgs_col.find_one({"id": m["org_id"]})
    if not org:
        raise HTTPException(404, "Organization not found")
    priorities = [p.strip() for p in body.priorities if isinstance(p, str) and p.strip()][:8]
    # bump the version only when the steering content actually changed (not on a no-op save)
    prev = (org.get("north_star", ""), org.get("target", ""), org.get("deadline", ""),
            tuple(org.get("priorities", []) or []), org.get("decision_rules", ""))
    nxt = (body.north_star.strip(), body.target.strip(), body.deadline.strip(),
           tuple(priorities), body.decision_rules.strip())
    cur_ver = int(org.get("strategy_version", 0) or 0)
    new_ver = cur_ver + 1 if (nxt != prev or cur_ver == 0) else cur_ver
    orgs_col.update_one({"id": m["org_id"]}, {"$set": {
        "north_star": body.north_star.strip(),
        "target": body.target.strip(),
        "deadline": body.deadline.strip(),
        "priorities": priorities,
        "decision_rules": body.decision_rules.strip(),
        "current_arr": body.current_arr,
        "target_arr": body.target_arr,
        "strategy_version": new_ver,
        "strategy_updated_at": now_utc(),
    }})
    org = orgs_col.find_one({"id": m["org_id"]})
    if body.current_arr is not None:
        _append_arr_snapshot(m["org_id"], body.current_arr)
    return _strategy_view(org)


# ----------------------------------------------------------------- goal -> progress tracker (founder-only)
PROGRESS_HISTORY_CAP = 36


def _append_arr_snapshot(org_id: str, arr) -> None:
    """Log a point on the founder's progress curve (idempotent against an identical last value)."""
    try:
        arr = float(arr)
    except (TypeError, ValueError):
        return
    org = orgs_col.find_one({"id": org_id}, {"_id": 0, "arr_history": 1})
    hist = list((org or {}).get("arr_history", []) or [])
    if hist and isinstance(hist[-1], dict) and hist[-1].get("arr") == arr:
        return  # no movement, don't clutter the curve
    hist.append({"arr": arr, "at": now_utc().isoformat()})
    orgs_col.update_one({"id": org_id}, {"$set": {"arr_history": hist[-PROGRESS_HISTORY_CAP:]}})


def _progress_status(pct):
    if pct is None:
        return "Not started yet"
    if pct >= 100:
        return "Goal reached"
    if pct >= 90:
        return "Almost there"
    if pct >= 60:
        return "Closing in"
    if pct >= 25:
        return "Building momentum"
    if pct > 0:
        return "Just getting started"
    return "Not started yet"


def _goal_progress(org: dict | None) -> dict | None:
    """Transparent arithmetic Goal -> Progress view. Founder-only. Not an AI forecast.
    Returns None when there is no numeric target to measure against."""
    if not org:
        return None
    ca, ta = org.get("current_arr"), org.get("target_arr")
    if not ta or ta <= 0:
        return None
    ca = ca or 0
    progress_pct = round(100 * ca / ta)
    gap_pct = round(100 * (ta - ca) / ca) if ca and ca > 0 else None
    raw_hist = list(org.get("arr_history", []) or [])
    history = [{"arr": h.get("arr"), "at": h.get("at")} for h in raw_hist if isinstance(h, dict)]
    return {
        "north_star": (org.get("north_star") or "").strip(),
        "target": (org.get("target") or "").strip(),
        "deadline": (org.get("deadline") or "").strip(),
        "current_arr": ca,
        "target_arr": ta,
        "remaining": max(0, ta - ca),
        "progress_pct": progress_pct,
        "gap_pct": gap_pct,
        "status": _progress_status(progress_pct),
        "history": history[-12:],
        "note": "Arithmetic only (current ÷ target). Not a forecast.",
    }


@router.get("/progress")
def get_progress(user: dict = Depends(current_user)):
    """Owner-only. The Goal -> Progress snapshot for the founder dashboard."""
    m = _require_owner(user)
    org = orgs_col.find_one({"id": m["org_id"]})
    if not org:
        raise HTTPException(404, "Organization not found")
    return {"goal_progress": _goal_progress(org)}


@router.post("/progress")
def set_progress(body: ProgressIn, user: dict = Depends(current_user)):
    """Owner-only. Quick 'where are we now' update. Logs a point on the progress curve and
    recomputes the gap. Does NOT touch the strategy or strategy_version."""
    m = _require_owner(user)
    org = orgs_col.find_one({"id": m["org_id"]})
    if not org:
        raise HTTPException(404, "Organization not found")
    orgs_col.update_one({"id": m["org_id"]}, {"$set": {"current_arr": body.current_arr,
                                                       "progress_updated_at": now_utc()}})
    _append_arr_snapshot(m["org_id"], body.current_arr)
    org = orgs_col.find_one({"id": m["org_id"]})
    return {"goal_progress": _goal_progress(org)}


# ----------------------------------------------------------------- founder cockpit (private clarity)
def _scores_of(rows):
    out = []
    for r in rows:
        a = r.get("strategic_alignment")
        if isinstance(a, dict) and isinstance(a.get("score"), int):
            out.append(a["score"])
    return out


def _effectiveness_by_function(org_id):
    """Layer 3: per-function decision count, avg alignment, and correlational effectiveness %."""
    rows = list(decisions_col.find({"org_id": org_id},
                                   {"_id": 0, "function": 1, "strategic_alignment": 1, "outcome": 1}))
    teams = {}
    for r in rows:
        f = r.get("function") or "general"
        t = teams.setdefault(f, {"function": f, "decisions": 0, "_sc": [], "_oc": []})
        t["decisions"] += 1
        a = r.get("strategic_alignment")
        if isinstance(a, dict) and isinstance(a.get("score"), int):
            t["_sc"].append(a["score"])
        oc = r.get("outcome")
        if isinstance(oc, dict) and oc.get("status") in ("success", "partial", "failed"):
            t["_oc"].append(oc["status"])
    out = []
    for f, t in teams.items():
        sc, oc = t["_sc"], t["_oc"]
        out.append({
            "function": f, "decisions": t["decisions"],
            "avg_alignment": round(sum(sc) / len(sc)) if sc else None,
            "outcomes_scored": len(oc),
            "effectiveness_pct": round(100 * (oc.count("success") + 0.5 * oc.count("partial")) / len(oc)) if oc else None,
        })
    out.sort(key=lambda x: (x["avg_alignment"] is None, x["avg_alignment"] if x["avg_alignment"] is not None else 0))
    return out


def _pacing(org):
    """Layer 3: transparent arithmetic gap from founder-entered ARR. Not an AI forecast."""
    ca, ta = org.get("current_arr"), org.get("target_arr")
    if not ca or not ta or ca <= 0 or ta <= 0:
        return None
    gap_pct = round(100 * (ta - ca) / ca)
    return {"current_arr": ca, "target_arr": ta, "deadline": org.get("deadline", "") or "",
            "gap_pct": gap_pct,
            "note": f"Arithmetic only: to reach the target, ARR must grow {gap_pct}% from here. Not a forecast."}


@router.get("/cockpit")
def cockpit(user: dict = Depends(current_user)):
    """Owner-only. The private view: alignment, drift, execution, momentum. Members never see this."""
    m = _require_owner(user)
    org_id = m["org_id"]
    org = orgs_col.find_one({"id": org_id})
    base = {"org_id": org_id}
    since7 = now_utc() - timedelta(days=7)

    total = decisions_col.count_documents(base)
    last7 = decisions_col.count_documents({**base, "created_at": {"$gte": since7}})

    scored_rows = list(decisions_col.find(
        {**base, "strategic_alignment.score": {"$ne": None}},
        {"_id": 0, "strategic_alignment": 1},
    ))
    scores = _scores_of(scored_rows)
    avg_align = round(sum(scores) / len(scores)) if scores else None
    high = sum(1 for x in scores if x >= 70)
    medium = sum(1 for x in scores if 40 <= x < 70)
    low = sum(1 for x in scores if x < 40)

    committed = decisions_col.count_documents({**base, "committed_action": {"$ne": None}})
    done = decisions_col.count_documents({**base, "status": "done"})
    dropped = decisions_col.count_documents({**base, "status": "dropped"})
    open_count = decisions_col.count_documents({**base, "status": "open", "committed_action": {"$ne": None}})
    follow_through = round(100 * done / (done + dropped)) if (done + dropped) > 0 else None

    members = list(members_col.find({"org_id": org_id, "status": "active"}).sort("joined_at", 1))
    per_member = []
    for mm in members:
        u = users_col.find_one({"id": mm["user_id"]}, {"_id": 0, "name": 1, "email": 1})
        mrows = list(decisions_col.find({**base, "user_id": mm["user_id"]},
                                        {"_id": 0, "strategic_alignment": 1, "status": 1}))
        msc = _scores_of(mrows)
        per_member.append({
            "user_id": mm["user_id"], "name": (u or {}).get("name", ""), "email": (u or {}).get("email", ""),
            "role": mm["role"], "decisions": len(mrows),
            "avg_alignment": (round(sum(msc) / len(msc)) if msc else None),
            "done": sum(1 for r in mrows if r.get("status") == "done"),
        })

    drift = list(decisions_col.find(
        {**base, "strategic_alignment.score": {"$lt": 40}},
        {"_id": 0, "id": 1, "user_name": 1, "question": 1, "strategic_alignment": 1, "created_at": 1},
    ).sort("created_at", -1).limit(10))

    # in-flight committed actions across the team (drives the founder's live timers)
    now = now_utc()

    def _iso(dt):
        return dt.isoformat() if hasattr(dt, "isoformat") else dt

    active_rows = list(decisions_col.find(
        {**base, "status": "open", "committed_action": {"$ne": None}, "due_at": {"$ne": None}},
        {"_id": 0, "id": 1, "user_name": 1, "committed_action": 1, "due_at": 1},
    ).sort("due_at", 1).limit(25))
    
    def _is_overdue(due_at):
        """Check if due_at is overdue, handling both offset-aware and offset-naive datetimes"""
        if not due_at:
            return False
        if isinstance(due_at, datetime):
            if due_at.tzinfo is None:
                due_at = due_at.replace(tzinfo=timezone.utc)
            return due_at < now
        return False
    
    active_actions = [{
        "id": r["id"], "user_name": r.get("user_name") or "Member",
        "action": r.get("committed_action"), "due_at": _iso(r.get("due_at")),
        "overdue": _is_overdue(r.get("due_at")),
    } for r in active_rows]
    overdue = sum(1 for a in active_actions if a["overdue"])

    # results the team has actually achieved (founder + member both see the outcome)
    result_rows = list(decisions_col.find(
        {**base, "status": "done", "result": {"$ne": None}},
        {"_id": 0, "id": 1, "user_name": 1, "committed_action": 1, "next_action": 1,
         "result": 1, "result_at": 1},
    ).sort("result_at", -1).limit(12))
    results_feed = [{
        "id": r["id"], "user_name": r.get("user_name") or "Member",
        "action": r.get("committed_action") or r.get("next_action") or "",
        "result": r.get("result"), "result_at": _iso(r.get("result_at")),
    } for r in result_rows]

    # ---- Layer 1: outcome effectiveness (correlational) ----
    oc_rows = list(decisions_col.find(
        {**base, "outcome.status": {"$in": ["success", "partial", "failed"]}},
        {"_id": 0, "outcome": 1, "alignment_band": 1}))
    n_oc = len(oc_rows)
    n_succ = sum(1 for r in oc_rows if r["outcome"]["status"] == "success")
    n_part = sum(1 for r in oc_rows if r["outcome"]["status"] == "partial")
    n_fail = sum(1 for r in oc_rows if r["outcome"]["status"] == "failed")
    eff_pct = round(100 * (n_succ + 0.5 * n_part) / n_oc) if n_oc else None
    effectiveness = {"scored": n_oc, "success": n_succ, "partial": n_part, "failed": n_fail,
                     "effectiveness_pct": eff_pct}

    # ---- Layer 2: alignment calibration (does a high alignment score actually predict success?) ----
    def _succ_rate(band):
        b = [r for r in oc_rows if r.get("alignment_band") == band]
        if not b:
            return None, 0
        return round(100 * sum(1 for r in b if r["outcome"]["status"] == "success") / len(b)), len(b)
    hi_rate, _hi_n = _succ_rate("high")
    lo_rate, _lo_n = _succ_rate("low")
    lift = (hi_rate - lo_rate) if (hi_rate is not None and lo_rate is not None) else None
    predictive = bool(n_oc >= 12 and lift is not None and lift > 0)
    calibration = {"high_success_rate": hi_rate, "low_success_rate": lo_rate, "lift": lift,
                   "samples": n_oc, "predictive": predictive,
                   "note": "Alignment is a DIAGNOSTIC until proven predictive (positive lift with enough samples)."}

    # ---- Layer 3: per-team rollup, alignment trend, transparent pacing ----
    team_alignment = _effectiveness_by_function(org_id)
    recent_scored = _scores_of(list(decisions_col.find(
        {**base, "strategic_alignment.score": {"$ne": None}, "created_at": {"$gte": since7}},
        {"_id": 0, "strategic_alignment": 1})))
    prior_scored = _scores_of(list(decisions_col.find(
        {**base, "strategic_alignment.score": {"$ne": None}, "created_at": {"$lt": since7}},
        {"_id": 0, "strategic_alignment": 1})))
    recent_avg = round(sum(recent_scored) / len(recent_scored)) if recent_scored else None
    prior_avg = round(sum(prior_scored) / len(prior_scored)) if prior_scored else None
    align_trend = (recent_avg - prior_avg) if (recent_avg is not None and prior_avg is not None) else None
    pacing = _pacing(org)

    # ---- Layer 4: deterministic contradiction detection (declared vs observed) ----
    prox_rows = list(decisions_col.find({**base, "revenue_proximity": {"$ne": None}}, {"_id": 0, "revenue_proximity": 1}))
    internal_share = round(100 * sum(1 for r in prox_rows if r["revenue_proximity"] == "internal") / len(prox_rows)) if prox_rows else None
    contradictions = []
    if overdue >= 2:
        contradictions.append({"title": "Committed but not done",
                               "evidence": f"{overdue} committed actions are overdue.", "severity": "high"})
    if follow_through is not None and follow_through < 60 and (done + dropped) >= 5:
        contradictions.append({"title": "Low follow-through",
                               "evidence": f"Only {follow_through}% of acted decisions were completed.", "severity": "high"})
    prio_text = (" ".join(org.get("priorities", []) or []) + " " + (org.get("north_star", "") or "")).lower()
    growth_focus = any(w in prio_text for w in ("revenue", "growth", "arr", "sales", "customer", "enterprise", "acqui"))
    if growth_focus and internal_share is not None and internal_share >= 60:
        contradictions.append({"title": "Declared growth, internal effort",
                               "evidence": f"{internal_share}% of decisions are internal-facing despite a growth-focused strategy.",
                               "severity": "medium"})
    if align_trend is not None and align_trend <= -8:
        contradictions.append({"title": "Alignment slipping",
                               "evidence": f"Average alignment fell {abs(align_trend)} points vs the prior period.",
                               "severity": "medium"})

    return {
        "north_star": _strategy_view(org),
        "totals": {"decisions": total, "last_7d": last7, "members": len(members)},
        "alignment": {"avg": avg_align, "high": high, "medium": medium, "low": low, "scored": len(scores)},
        "execution": {"committed": committed, "open": open_count, "done": done,
                      "dropped": dropped, "overdue": overdue, "follow_through_pct": follow_through},
        "effectiveness": effectiveness,
        "calibration": calibration,
        "team_alignment": team_alignment,
        "alignment_trend": align_trend,
        "pacing": pacing,
        "goal_progress": _goal_progress(org),
        "contradictions": contradictions,
        "per_member": per_member,
        "drift": drift,
        "active_actions": active_actions,
        "results": results_feed,
    }


# ----------------------------------------------------------------- Layer 6: autonomous planning (human-gated)
DEP_FUNCTIONS = ("sales", "marketing", "product", "engineering", "operations", "finance", "leadership", "general")


def norm_dep_function(f):
    f = (f or "general").strip().lower()
    return f if f in DEP_FUNCTIONS else "general"


PLAN_SYSTEM = (
    "You are a strategy operator. Given a company's North Star, priorities, and what has historically "
    "worked per function, draft an objective cascade: ONE company objective, then a short objective plus "
    "2-3 measurable key results for each relevant function. Ground proposals in the historical "
    "effectiveness data provided (favour functions and plays that have actually worked). Be concrete and "
    "numeric where possible. This is a DRAFT for a human to ratify, never a final plan. "
    'Return ONLY JSON, no fences: {"company_objective": "...", "departments": [{"function": '
    '"sales|marketing|product|engineering|operations|finance|leadership", "objective": "...", '
    '"key_results": ["...", "..."]}]}'
)


class PlanDraftIn(BaseModel):
    target: str = Field(min_length=2, max_length=300)


def _plan_adherence(org_id, plan):
    since = plan.get("activated_at") or plan.get("created_at")
    q = {"org_id": org_id}
    if since:
        q["created_at"] = {"$gte": since}
    rows = list(decisions_col.find(q, {"_id": 0, "function": 1, "strategic_alignment": 1, "outcome": 1}))
    by_fn = {}
    for r in rows:
        f = r.get("function") or "general"
        d = by_fn.setdefault(f, {"_sc": [], "_oc": [], "n": 0})
        d["n"] += 1
        a = r.get("strategic_alignment")
        if isinstance(a, dict) and isinstance(a.get("score"), int):
            d["_sc"].append(a["score"])
        oc = r.get("outcome")
        if isinstance(oc, dict) and oc.get("status") in ("success", "partial", "failed"):
            d["_oc"].append(oc["status"])
    depts = []
    for dep in plan.get("departments", []) or []:
        f = dep.get("function", "general")
        d = by_fn.get(f, {"_sc": [], "_oc": [], "n": 0})
        oc = d["_oc"]
        depts.append({**dep, "decisions": d["n"],
                      "avg_alignment": round(sum(d["_sc"]) / len(d["_sc"])) if d["_sc"] else None,
                      "effectiveness_pct": round(100 * (oc.count("success") + 0.5 * oc.count("partial")) / len(oc)) if oc else None})
    total_dec = sum(x["n"] for x in by_fn.values())
    return depts, total_dec


def _plan_view(plan, org_id):
    out = {k: plan.get(k) for k in ("id", "target", "status", "company_objective", "created_at", "activated_at")}
    if plan.get("status") == "active":
        depts, total_dec = _plan_adherence(org_id, plan)
        out["departments"] = depts
        out["decisions_since_activation"] = total_dec
    else:
        out["departments"] = plan.get("departments", [])
    return out


@router.post("/plan/draft")
def draft_plan(body: PlanDraftIn, user: dict = Depends(current_user)):
    """Owner-only. AI DRAFTS an objective cascade grounded in what has worked; a human must ratify it."""
    m = _require_owner(user)
    org = orgs_col.find_one({"id": m["org_id"]})
    if not org:
        raise HTTPException(404, "Organization not found")
    eff = _effectiveness_by_function(org["id"])
    eff_text = "\n".join(
        f"- {e['function']}: {e['decisions']} decisions, avg alignment {e['avg_alignment']}, "
        f"effectiveness {e['effectiveness_pct']}% (n={e['outcomes_scored']})" for e in eff) or "(no history yet)"
    prio = "; ".join(org.get("priorities", []) or []) or "(none set)"
    prompt = (
        f"NORTH STAR: {org.get('north_star','') or '(not set)'}\n"
        f"TARGET: {org.get('target','')} {org.get('deadline','')}\n"
        f"PRIORITIES: {prio}\n"
        f"DECISION RULES: {org.get('decision_rules','') or '(none)'}\n"
        f"NEW OBJECTIVE THE FOUNDER WANTS: {body.target.strip()}\n\n"
        f"HISTORICAL EFFECTIVENESS BY FUNCTION (ground the plan in this):\n{eff_text}\n"
    )
    try:
        r = client().messages.create(model="claude-sonnet-4-5", max_tokens=1600,
                                     system=[{"type": "text", "text": PLAN_SYSTEM}],
                                     messages=[{"role": "user", "content": prompt}])
        txt = next((b.text for b in r.content if getattr(b, "type", "") == "text"), "").strip()
        data = json.loads(_extract_json(txt))
    except Exception as e:
        log.error(f"plan draft failed: {e}")
        raise HTTPException(502, "Could not draft a plan right now. Try again.")
    depts = []
    for d in (data.get("departments") or [])[:8]:
        if not isinstance(d, dict):
            continue
        krs = [str(k) for k in (d.get("key_results") or []) if str(k).strip()][:4]
        depts.append({"function": norm_dep_function(d.get("function")),
                      "objective": str(d.get("objective", ""))[:600], "key_results": krs})
    plan = {"id": str(uuid.uuid4()), "org_id": org["id"], "target": body.target.strip(),
            "status": "draft", "created_at": now_utc(), "activated_at": None, "created_by": user["id"],
            "company_objective": str(data.get("company_objective", ""))[:800], "departments": depts}
    plans_col.insert_one(plan)
    return _plan_view(plan, org["id"])


@router.get("/plan")
def get_plan(user: dict = Depends(current_user)):
    """Owner-only. The active ratified plan (with adherence) + the latest draft awaiting ratification."""
    m = _require_owner(user)
    org_id = m["org_id"]
    active = plans_col.find_one({"org_id": org_id, "status": "active"})
    draft = plans_col.find_one({"org_id": org_id, "status": "draft"}, sort=[("created_at", -1)])
    return {"active": _plan_view(active, org_id) if active else None,
            "draft": _plan_view(draft, org_id) if draft else None}


@router.post("/plan/{plan_id}/ratify")
def ratify_plan(plan_id: str, user: dict = Depends(current_user)):
    """Owner-only human ratification gate: a generated plan goes live ONLY when a human approves it."""
    m = _require_owner(user)
    org_id = m["org_id"]
    p = plans_col.find_one({"id": plan_id, "org_id": org_id})
    if not p:
        raise HTTPException(404, "Plan not found")
    plans_col.update_many({"org_id": org_id, "status": "active"}, {"$set": {"status": "archived"}})
    plans_col.update_one({"id": plan_id}, {"$set": {"status": "active", "activated_at": now_utc()}})
    p = plans_col.find_one({"id": plan_id})
    return _plan_view(p, org_id)
