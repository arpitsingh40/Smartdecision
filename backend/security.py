"""Auth primitives shared by all routers (JWT, password hashing, admin gate)."""
import os
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException, Header, Depends
from passlib.context import CryptContext
from db import users_col

import logging

_log = logging.getLogger("sdg")

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
if not JWT_SECRET or JWT_SECRET in ("dev-secret", "dev-jwt-secret", "dev-jwt-secret-change-in-production"):
    _log.warning("SECURITY WARNING: Using a weak/default JWT_SECRET. Set a strong random secret in production.")
    if JWT_SECRET.startswith("dev-"):
        _log.warning(f"  Current JWT_SECRET starts with 'dev-', suggesting it's a placeholder.")


def now_utc():
    return datetime.now(timezone.utc)


def as_aware(dt):
    if dt and getattr(dt, "tzinfo", None) is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def make_token(user_id: str) -> str:
    return jwt.encode({"sub": user_id, "exp": now_utc() + timedelta(days=30)}, JWT_SECRET, algorithm="HS256")


def current_user(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(authorization.split(" ", 1)[1], JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(401, "Invalid or expired token")
    user = users_col.find_one({"id": payload["sub"]})
    if not user:
        raise HTTPException(401, "User not found")
    return user


def optional_user(authorization: str = Header(None)):
    """Like current_user but returns None instead of raising (used by traffic tracking)."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        payload = jwt.decode(authorization.split(" ", 1)[1], JWT_SECRET, algorithms=["HS256"])
        return users_col.find_one({"id": payload["sub"]})
    except Exception:
        return None


def require_admin(user: dict = Depends(current_user)) -> dict:
    if not user.get("is_admin"):
        raise HTTPException(403, "Founder access only")
    return user
