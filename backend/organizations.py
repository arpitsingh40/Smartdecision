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
import uuid
import secrets
from datetime import timedelta, datetime, timezone

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr

from db import orgs_col, members_col, invites_col, users_col, decisions_col
from security import current_user, now_utc

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
    """Owner-only. Saves the hidden steering that silently guides every member's decisions."""
    m = _require_owner(user)
    priorities = [p.strip() for p in body.priorities if isinstance(p, str) and p.strip()][:8]
    orgs_col.update_one({"id": m["org_id"]}, {"$set": {
        "north_star": body.north_star.strip(),
        "target": body.target.strip(),
        "deadline": body.deadline.strip(),
        "priorities": priorities,
        "decision_rules": body.decision_rules.strip(),
        "strategy_updated_at": now_utc(),
    }})
    org = orgs_col.find_one({"id": m["org_id"]})
    return _strategy_view(org)


# ----------------------------------------------------------------- founder cockpit (private clarity)
def _scores_of(rows):
    out = []
    for r in rows:
        a = r.get("strategic_alignment")
        if isinstance(a, dict) and isinstance(a.get("score"), int):
            out.append(a["score"])
    return out


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

    return {
        "north_star": _strategy_view(org),
        "totals": {"decisions": total, "last_7d": last7, "members": len(members)},
        "alignment": {"avg": avg_align, "high": high, "medium": medium, "low": low, "scored": len(scores)},
        "execution": {"committed": committed, "open": open_count, "done": done,
                      "dropped": dropped, "overdue": overdue, "follow_through_pct": follow_through},
        "per_member": per_member,
        "drift": drift,
        "active_actions": active_actions,
        "results": results_feed,
    }
