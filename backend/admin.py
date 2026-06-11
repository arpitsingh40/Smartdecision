"""Founder OS API - admin-only (ceo@smartdecigen.com).
Every list is paginated + index-backed; summaries read pre-aggregated counters,
so these endpoints stay O(1)/O(page) even at millions of users."""
import re
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from db import users_col, threads_col, telemetry_col, ledger_col, traffic_col, orders_col
from security import require_admin, now_utc, as_aware
from ledger import get_stats

router = APIRouter(prefix="/api/admin", tags=["admin"])

USER_PROJ = {"_id": 0, "password_hash": 0}


def _iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


def _clean(doc: dict) -> dict:
    out = {}
    for k, v in doc.items():
        if k == "_id":
            continue
        out[k] = _iso(v) if hasattr(v, "isoformat") else v
    return out


@router.get("/overview")
def overview(admin: dict = Depends(require_admin)):
    s = get_stats()
    now = now_utc()
    week_ago = now - timedelta(days=7)
    day_ago = now - timedelta(days=1)
    users_total = users_col.count_documents({})
    users_7d = users_col.count_documents({"created_at": {"$gte": week_ago}})
    questions_7d = telemetry_col.count_documents({"type": "discussion_turn", "at": {"$gte": week_ago}})
    sessions_7d = traffic_col.count_documents({"started_at": {"$gte": week_ago}})
    active_now = traffic_col.count_documents({"last_seen_at": {"$gte": now - timedelta(minutes=3)}})
    # avg session time over the most recent 500 sessions (bounded work)
    agg = list(traffic_col.aggregate([
        {"$sort": {"started_at": -1}}, {"$limit": 500},
        {"$group": {"_id": None, "avg_s": {"$avg": "$duration_s"}, "total_s": {"$sum": "$duration_s"}}}]))
    avg_s = round(agg[0]["avg_s"]) if agg else 0
    issued_free = s.get("credits_issued_free", 0)
    issued_paid = s.get("credits_issued_paid", 0)
    spent = s.get("credits_spent", 0)
    return {
        "users": {"total": users_total, "new_7d": users_7d,
                  "active_24h": users_col.count_documents({"last_active_at": {"$gte": day_ago}})},
        "engine": {"questions_total": s.get("questions_total", 0),
                   "turns_normal": s.get("turns_normal", 0),
                   "turns_ultra": s.get("turns_ultra", 0),
                   "questions_7d": questions_7d},
        "credits": {"issued_total": issued_free + issued_paid, "issued_free": issued_free,
                    "issued_paid": issued_paid, "spent": spent,
                    "outstanding": issued_free + issued_paid - spent},
        "tokens": {"input_total": s.get("tokens_in", 0), "output_total": s.get("tokens_out", 0)},
        "revenue": {"total_inr": s.get("revenue_inr", 0), "purchases": s.get("purchases_count", 0)},
        "traffic": {"sessions_total": s.get("sessions_total", 0), "unique_ips": s.get("unique_ips", 0),
                    "sessions_7d": sessions_7d, "avg_session_s": avg_s, "active_now": active_now},
    }


@router.get("/users")
def list_users(page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100),
               q: str = Query(""), admin: dict = Depends(require_admin)):
    filt = {}
    if q.strip():
        rx = {"$regex": re.escape(q.strip()), "$options": "i"}
        filt = {"$or": [{"email": rx}, {"name": rx}, {"country": rx}]}
    total = users_col.count_documents(filt)
    items = [_clean(u) for u in users_col.find(filt, USER_PROJ)
             .sort("created_at", -1).skip((page - 1) * limit).limit(limit)]
    return {"items": items, "total": total, "page": page, "pages": max(1, -(-total // limit))}


@router.get("/users/{user_id}/activity")
def user_activity(user_id: str, admin: dict = Depends(require_admin)):
    u = users_col.find_one({"id": user_id}, USER_PROJ)
    if not u:
        raise HTTPException(404, "User not found")
    threads = []
    for t in threads_col.find({"user_id": user_id}).sort("opened_at", -1).limit(50):
        qa, pending = [], None
        for m in t.get("messages", []):
            if m.get("role") == "user":
                pending = m
            elif m.get("role") == "engine" and pending is not None:
                qa.append({"question": pending.get("text", ""), "reply": m.get("text", ""),
                           "intent": pending.get("intent"), "at": _iso(m.get("at"))})
                pending = None
        threads.append({"thread_id": t["thread_id"], "goal": t.get("goal", ""),
                        "status": t.get("status", ""), "opened_at": _iso(t.get("opened_at")), "qa": qa})
    ledger = [_clean(entry) for entry in ledger_col.find({"user_id": user_id}).sort("at", -1).limit(50)]
    return {"user": _clean(u), "threads": threads, "ledger": ledger}


@router.get("/traffic")
def traffic(page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100),
            admin: dict = Depends(require_admin)):
    s = get_stats()
    total = traffic_col.count_documents({})
    items = [_clean(t) for t in traffic_col.find({}, {"_id": 0})
             .sort("started_at", -1).skip((page - 1) * limit).limit(limit)]
    agg = list(traffic_col.aggregate([
        {"$sort": {"started_at": -1}}, {"$limit": 500},
        {"$group": {"_id": None, "avg_s": {"$avg": "$duration_s"}, "total_s": {"$sum": "$duration_s"}}}]))
    summary = {"sessions_total": total, "unique_ips": s.get("unique_ips", 0),
               "avg_session_s": round(agg[0]["avg_s"]) if agg else 0,
               "time_recent_500_s": agg[0]["total_s"] if agg else 0,
               "active_now": traffic_col.count_documents({"last_seen_at": {"$gte": now_utc() - timedelta(minutes=3)}})}
    return {"summary": summary, "items": items, "total": total, "page": page,
            "pages": max(1, -(-total // limit))}


@router.get("/usage")
def usage(page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100),
          admin: dict = Depends(require_admin)):
    s = get_stats()
    issued_free = s.get("credits_issued_free", 0)
    issued_paid = s.get("credits_issued_paid", 0)
    summary = {
        "credits": {"issued_total": issued_free + issued_paid, "issued_free": issued_free,
                    "issued_paid": issued_paid, "spent": s.get("credits_spent", 0),
                    "outstanding": issued_free + issued_paid - s.get("credits_spent", 0)},
        "tokens": {"input_total": s.get("tokens_in", 0), "output_total": s.get("tokens_out", 0)},
        "turns": {"total": s.get("questions_total", 0), "normal": s.get("turns_normal", 0),
                  "ultra": s.get("turns_ultra", 0)},
        "revenue": {"total_inr": s.get("revenue_inr", 0), "purchases": s.get("purchases_count", 0)},
    }
    total = users_col.count_documents({})
    proj = {"_id": 0, "id": 1, "email": 1, "name": 1, "country": 1, "credits": 1,
            "questions_asked": 1, "tokens_in": 1, "tokens_out": 1,
            "credits_issued_free": 1, "credits_issued_paid": 1, "created_at": 1, "last_active_at": 1}
    items = [_clean(u) for u in users_col.find({}, proj)
             .sort([("questions_asked", -1), ("created_at", -1)]).skip((page - 1) * limit).limit(limit)]
    return {"summary": summary, "items": items, "total": total, "page": page,
            "pages": max(1, -(-total // limit))}


@router.get("/purchases")
def purchases(page: int = Query(1, ge=1), limit: int = Query(25, ge=1, le=100),
              admin: dict = Depends(require_admin)):
    total = orders_col.count_documents({})
    items = [_clean(o) for o in orders_col.find({}, {"_id": 0, "status_history": 0})
             .sort("created_at", -1).skip((page - 1) * limit).limit(limit)]
    return {"items": items, "total": total, "page": page, "pages": max(1, -(-total // limit))}
