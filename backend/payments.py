"""Zoho Payments (India) top-ups - one-time purchases, not subscriptions.
Packs: 100 credits = Rs 399, 500 credits = Rs 999.

ZOHO_TEST_MODE=true (default until real keys are supplied): full order lifecycle with a
local simulated checkout page. Drop in real Zoho creds + ZOHO_TEST_MODE=false -> live
hosted checkout, webhook + server-side verification. Zero code change.

Safety: server-side amount validation, idempotent fulfilment (status-guarded atomic
update -> a webhook + redirect can both fire and credits are added exactly once),
HMAC-SHA256 webhook signature verification, immutable order amounts + status history."""
import os
import hmac
import hashlib
import json
import time
import uuid
import logging
from typing import Optional
import requests as http
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from pymongo import ReturnDocument
from db import users_col, orders_col
from security import current_user, now_utc
from ledger import record_ledger, inc_stats

router = APIRouter(prefix="/api/payments", tags=["payments"])
log = logging.getLogger("payments")

PACKS = {
    "pack_100": {"credits": 100, "amount_inr": 399, "label": "100 credits"},
    "pack_500": {"credits": 500, "amount_inr": 999, "label": "500 credits", "tag": "Best value"},
}


def _test_mode() -> bool:
    return os.environ.get("ZOHO_TEST_MODE", "true").lower() == "true"


def _frontend_base(request: Request) -> str:
    return (os.environ.get("FRONTEND_BASE_URL") or request.headers.get("origin") or "").rstrip("/")


# ----------------------------------------------------------------- zoho client
_token_cache = {"token": None, "exp": 0.0}


def _zoho_access_token() -> str:
    if _token_cache["token"] and time.time() < _token_cache["exp"] - 120:
        return _token_cache["token"]
    r = http.post(os.environ.get("ZOHO_OAUTH_BASE", "https://accounts.zoho.in/oauth/v2/token"), data={
        "refresh_token": os.environ["ZOHO_REFRESH_TOKEN"],
        "client_id": os.environ["ZOHO_CLIENT_ID"],
        "client_secret": os.environ["ZOHO_CLIENT_SECRET"],
        "grant_type": "refresh_token",
    }, timeout=15)
    data = r.json()
    if "access_token" not in data:
        raise RuntimeError(f"Zoho OAuth refresh failed: {data}")
    _token_cache["token"] = data["access_token"]
    _token_cache["exp"] = time.time() + int(data.get("expires_in", 3600))
    return _token_cache["token"]


def _zoho_api(method: str, path: str, payload: Optional[dict] = None) -> dict:
    base = os.environ.get("ZOHO_API_BASE", "https://payments.zoho.in/api/v1")
    account_id = os.environ["ZOHO_ACCOUNT_ID"]
    headers = {"Authorization": f"Zoho-oauthtoken {_zoho_access_token()}",
               "content-type": "application/json"}
    r = http.request(method, f"{base}{path}", params={"account_id": account_id},
                     json=payload, headers=headers, timeout=20)
    if r.status_code >= 400:
        raise RuntimeError(f"Zoho API {path} -> {r.status_code}: {r.text[:300]}")
    return r.json()


# ----------------------------------------------------------------- fulfilment (idempotent)
def fulfil_order(order_id: str, source: str):
    """Credits exactly once: atomic status-guarded transition created/failed -> paid."""
    now = now_utc()
    order = orders_col.find_one_and_update(
        {"order_id": order_id, "status": {"$ne": "paid"}},
        {"$set": {"status": "paid", "paid_at": now, "paid_via": source, "updated_at": now},
         "$push": {"status_history": {"status": "paid", "at": now, "via": source}}},
        return_document=ReturnDocument.AFTER)
    if not order:
        return None  # already fulfilled or unknown -> no double credit
    users_col.update_one({"id": order["user_id"]},
                         {"$inc": {"credits": order["credits"], "credits_issued_paid": order["credits"]}})
    record_ledger(order["user_id"], "purchase", order["credits"],
                  amount_inr=order["amount_inr"], order_id=order_id, pack_id=order["pack_id"])
    inc_stats({"credits_issued_paid": order["credits"], "revenue_inr": order["amount_inr"],
               "purchases_count": 1})
    log.info(f"order {order_id} fulfilled via {source}: +{order['credits']} credits")
    return order


def _mark_failed(order_id: str, reason: str):
    now = now_utc()
    orders_col.update_one(
        {"order_id": order_id, "status": {"$ne": "paid"}},
        {"$set": {"status": "failed", "updated_at": now},
         "$push": {"status_history": {"status": "failed", "at": now, "reason": reason}}})


# ----------------------------------------------------------------- endpoints
@router.get("/packs")
def packs():
    return {"packs": [{"pack_id": k, **v} for k, v in PACKS.items()],
            "test_mode": _test_mode(), "currency": "INR"}


class OrderIn(BaseModel):
    pack_id: str


@router.post("/create-order")
def create_order(body: OrderIn, request: Request, user: dict = Depends(current_user)):
    pack = PACKS.get(body.pack_id)
    if not pack:
        raise HTTPException(422, "Unknown pack")
    now = now_utc()
    order_id = str(uuid.uuid4())
    order = {
        "order_id": order_id, "user_id": user["id"], "user_email": user["email"],
        "pack_id": body.pack_id, "credits": pack["credits"], "amount_inr": pack["amount_inr"],
        "currency": "INR", "status": "created", "test": _test_mode(),
        "zoho_session_id": None, "zoho_payment_id": None,
        "created_at": now, "updated_at": now,
        "status_history": [{"status": "created", "at": now}],
    }
    orders_col.insert_one(order)
    front = _frontend_base(request)
    if _test_mode():
        return {"order_id": order_id, "test_mode": True,
                "checkout_url": f"{front}/pay/test-checkout?order_id={order_id}"}
    try:
        resp = _zoho_api("POST", "/paymentsessions", {
            "amount": str(pack["amount_inr"]),
            "currency_code": "INR",
            "configurations": {"hosted_checkout_parameters": {
                "success_url": f"{front}/pay/result?order_id={order_id}",
                "failure_url": f"{front}/pay/result?order_id={order_id}",
                "description": f"SmartDecigen top-up: {pack['label']}",
            }},
        })
        data = resp.get("payments_session") or resp.get("data") or resp
        session_id = data.get("payments_session_id") or data.get("payment_session_id")
        access_key = data.get("access_key")
        if not session_id or not access_key:
            raise RuntimeError(f"unexpected Zoho session response: {json.dumps(resp)[:300]}")
        orders_col.update_one({"order_id": order_id},
                              {"$set": {"zoho_session_id": session_id, "updated_at": now_utc()}})
        host = os.environ.get("ZOHO_API_BASE", "https://payments.zoho.in/api/v1").split("/api/")[0]
        return {"order_id": order_id, "test_mode": False,
                "checkout_url": f"{host}/hostedcheckout/{access_key}"}
    except Exception as e:
        _mark_failed(order_id, f"session creation failed: {e}")
        log.error(f"zoho session create failed: {e}")
        raise HTTPException(502, "Could not start the payment. You were not charged - try again.")


class TestCompleteIn(BaseModel):
    order_id: str
    outcome: str  # success | failure


@router.post("/test-complete")
def test_complete(body: TestCompleteIn, user: dict = Depends(current_user)):
    """TEST MODE ONLY: simulates Zoho's webhook so the full flow is verifiable today."""
    if not _test_mode():
        raise HTTPException(403, "Test completion is disabled in live mode")
    order = orders_col.find_one({"order_id": body.order_id, "user_id": user["id"]})
    if not order:
        raise HTTPException(404, "Order not found")
    if body.outcome == "success":
        fulfil_order(body.order_id, "test_simulation")
    else:
        _mark_failed(body.order_id, "simulated failure")
    fresh = users_col.find_one({"id": user["id"]})
    o = orders_col.find_one({"order_id": body.order_id}, {"_id": 0, "status": 1})
    return {"status": o["status"], "credits": fresh.get("credits", 0)}


@router.get("/status/{order_id}")
def order_status(order_id: str, user: dict = Depends(current_user)):
    order = orders_col.find_one({"order_id": order_id, "user_id": user["id"]})
    if not order:
        raise HTTPException(404, "Order not found")
    # live mode: if still pending, verify against Zoho (source of truth) before answering
    if not _test_mode() and order["status"] == "created" and order.get("zoho_session_id"):
        try:
            resp = _zoho_api("GET", f"/paymentsessions/{order['zoho_session_id']}")
            data = resp.get("payments_session") or resp.get("data") or resp
            pay_status = (data.get("payment_status") or data.get("status") or "").lower()
            payment_id = data.get("payment_id")
            if payment_id:
                orders_col.update_one({"order_id": order_id}, {"$set": {"zoho_payment_id": payment_id}})
            if pay_status in ("succeeded", "success", "captured", "paid"):
                fulfil_order(order_id, "status_poll")
            elif pay_status in ("failed", "cancelled"):
                _mark_failed(order_id, f"zoho status {pay_status}")
        except Exception as e:
            log.warning(f"zoho status check failed for {order_id}: {e}")
    order = orders_col.find_one({"order_id": order_id}, {"_id": 0, "status_history": 0})
    fresh = users_col.find_one({"id": user["id"]})
    return {"order_id": order_id, "status": order["status"], "credits_added": order["credits"],
            "amount_inr": order["amount_inr"], "pack_id": order["pack_id"],
            "test": order.get("test", False), "balance": fresh.get("credits", 0)}


@router.get("/history")
def history(user: dict = Depends(current_user)):
    items = []
    for o in orders_col.find({"user_id": user["id"]}, {"_id": 0, "status_history": 0}).sort("created_at", -1).limit(50):
        o["created_at"] = o["created_at"].isoformat() if hasattr(o["created_at"], "isoformat") else o["created_at"]
        o["updated_at"] = o["updated_at"].isoformat() if hasattr(o["updated_at"], "isoformat") else o["updated_at"]
        o.pop("paid_at", None)
        items.append(o)
    return {"items": items}


# ----------------------------------------------------------------- webhook (live mode)
def _verify_webhook_signature(raw: bytes, header_value: str, key: str) -> bool:
    try:
        parts = dict(p.strip().split("=", 1) for p in header_value.split(","))
        ts, sig = parts.get("t"), parts.get("v")
        if not ts or not sig:
            return False
        mac = hmac.new(key.encode(), msg=f"{ts}.{raw.decode()}".encode(), digestmod=hashlib.sha256)
        return hmac.compare_digest(mac.hexdigest(), sig)
    except Exception:
        return False


def _find_key(obj, names):
    """Defensive: find first matching key anywhere in a nested payload."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in names and isinstance(v, (str, int, float)):
                return v
        for v in obj.values():
            r = _find_key(v, names)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = _find_key(v, names)
            if r is not None:
                return r
    return None


@router.post("/webhook/zoho")
async def zoho_webhook(request: Request):
    raw = await request.body()
    secret = os.environ.get("ZOHO_WEBHOOK_SECRET", "")
    header = request.headers.get("x-zoho-webhook-signature", "")
    if secret and not _verify_webhook_signature(raw, header, secret):
        raise HTTPException(400, "Invalid webhook signature")
    try:
        payload = json.loads(raw.decode() or "{}")
    except Exception:
        return {"received": True}
    session_id = _find_key(payload, {"payments_session_id", "payment_session_id"})
    payment_id = _find_key(payload, {"payment_id"})
    status_val = str(_find_key(payload, {"status", "payment_status"}) or "").lower()
    event = str(_find_key(payload, {"event", "event_type"}) or "").lower()
    order = None
    if session_id:
        order = orders_col.find_one({"zoho_session_id": session_id})
    if not order and payment_id:
        order = orders_col.find_one({"zoho_payment_id": payment_id})
    if not order:
        return {"received": True}
    if payment_id:
        orders_col.update_one({"order_id": order["order_id"]}, {"$set": {"zoho_payment_id": payment_id}})
    if "success" in event or status_val in ("succeeded", "success", "captured", "paid"):
        fulfil_order(order["order_id"], "webhook")
    elif "fail" in event or status_val in ("failed", "cancelled"):
        _mark_failed(order["order_id"], f"webhook {event or status_val}")
    return {"received": True}
