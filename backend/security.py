"""Auth primitives shared by all routers (JWT, password hashing, admin gate).
Supports both sync and async endpoints. Tokens stored in DB — revocable server-side."""
import os
import uuid
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException, Header, Depends
from passlib.context import CryptContext
from db import users_col, async_users_col, sessions_col, async_sessions_col

import logging

_log = logging.getLogger("sdg")

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
if not JWT_SECRET or JWT_SECRET in ("dev-secret", "dev-jwt-secret", "dev-jwt-secret-change-in-production"):
    _log.warning("SECURITY WARNING: Using a weak/default JWT_SECRET. Set a strong random secret in production.")
    if JWT_SECRET.startswith("dev-"):
        _log.warning(f"  Current JWT_SECRET starts with 'dev-', suggesting it's a placeholder.")

TOKEN_DAYS = 30


def now_utc():
    return datetime.now(timezone.utc)


def as_aware(dt):
    if dt and getattr(dt, "tzinfo", None) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def make_token(user_id: str) -> tuple[str, str]:
    """Create a JWT + store session in DB. Returns (token_id, jwt_string)."""
    token_id = str(uuid.uuid4())
    exp = now_utc() + timedelta(days=TOKEN_DAYS)
    j = jwt.encode({"sub": user_id, "jti": token_id, "exp": exp}, JWT_SECRET, algorithm="HS256")
    sessions_col.insert_one({
        "token_id": token_id, "user_id": user_id,
        "created_at": now_utc(), "expires_at": exp, "revoked": False,
    })
    return token_id, j


def revoke_token(token_id: str):
    sessions_col.update_one({"token_id": token_id}, {"$set": {"revoked": True}})


def revoke_all_user_tokens(user_id: str):
    """Revoke every session for a user (e.g. password change, account ban)."""
    sessions_col.update_many({"user_id": user_id}, {"$set": {"revoked": True}})


def _decode_token(authorization: str) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    try:
        return jwt.decode(authorization.split(" ", 1)[1], JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid or expired token")


def _verify_session(payload: dict):
    token_id = payload.get("jti")
    if not token_id:
        raise HTTPException(401, "Token missing session id")
    session = sessions_col.find_one({"token_id": token_id})
    if not session or session.get("revoked"):
        raise HTTPException(401, "Session revoked or not found")


def current_user(authorization: str = Header(None)) -> dict:
    payload = _decode_token(authorization)
    _verify_session(payload)
    user = users_col.find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(401, "User not found")
    return user


async def current_user_async(authorization: str = Header(None)) -> dict:
    payload = _decode_token(authorization)
    token_id = payload.get("jti")
    if not token_id:
        raise HTTPException(401, "Token missing session id")
    session = await async_sessions_col.find_one({"token_id": token_id})
    if not session or session.get("revoked"):
        raise HTTPException(401, "Session revoked or not found")
    user = await async_users_col.find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(401, "User not found")
    return user


def optional_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        payload = _decode_token(authorization)
        token_id = payload.get("jti")
        if not token_id:
            return None
        session = sessions_col.find_one({"token_id": token_id})
        if not session or session.get("revoked"):
            return None
        return users_col.find_one({"id": payload["sub"]})
    except Exception:
        return None


async def optional_user_async(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        payload = _decode_token(authorization)
        token_id = payload.get("jti")
        if not token_id:
            return None
        if async_sessions_col is None:
            return None
        session = await async_sessions_col.find_one({"token_id": token_id})
        if not session or session.get("revoked"):
            return None
        return await async_users_col.find_one({"id": payload["sub"]})
    except Exception:
        return None


# Cleanup job: delete expired sessions older than 60 days
def cleanup_expired_sessions():
    cutoff = now_utc() - timedelta(days=60)
    sessions_col.delete_many({"expires_at": {"$lt": cutoff}})


def require_admin(user: dict = Depends(current_user)) -> dict:
    if not user.get("is_admin"):
        raise HTTPException(403, "Founder access only")
    return user


async def require_admin_async(user: dict = Depends(current_user_async)) -> dict:
    if not user.get("is_admin"):
        raise HTTPException(403, "Founder access only")
    return user
