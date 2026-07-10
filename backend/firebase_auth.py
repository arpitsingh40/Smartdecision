"""Firebase phone authentication — primary auth method.
Flow:
  1. Frontend sends OTP to phone via Firebase Client SDK
  2. User enters OTP → Firebase returns ID token
  3. Frontend posts { id_token } to /auth/firebase
  4. Backend verifies ID token with Firebase Admin SDK
  5. Extracts phone number, upserts user (create or login)
  6. Returns JWT + user object

Email is NOT required at this stage. Email capture is deferred to the
"export details" flow in the founder profile."""
import os
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import Header as FHeader
from pydantic import BaseModel
from db import users_col
from security import make_token, now_utc, pwd, current_user
from tracking import client_ip, geo_lookup
from ledger import record_ledger, inc_stats

router = APIRouter(prefix="/api/auth", tags=["auth"])
log = logging.getLogger("firebase_auth")

SIGNUP_CREDITS = int(os.environ.get("SIGNUP_CREDITS", "0"))  # no free credits for new signups

# Firebase Admin SDK — optional. If FIREBASE_PROJECT_ID is not set, the endpoint
# returns a 501 (not implemented) so the app degrades gracefully.
_firebase_app = None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app
    project_id = os.environ.get("FIREBASE_PROJECT_ID", "")
    if not project_id:
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials
        import json
        json_str = os.environ.get("FIREBASE_CREDENTIALS_JSON", "")
        if json_str:
            cred = credentials.Certificate(json.loads(json_str))
            log.info("Firebase Admin SDK initialized from FIREBASE_CREDENTIALS_JSON env var")
        else:
            cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
            if cred_path and os.path.exists(cred_path):
                cred = credentials.Certificate(cred_path)
            else:
                cred = credentials.ApplicationDefault()
        _firebase_app = firebase_admin.initialize_app(cred, {"projectId": project_id})
        log.info(f"Firebase Admin SDK initialized for project {project_id}")
        return _firebase_app
    except Exception as e:
        log.warning(f"Firebase Admin SDK init failed: {e}")
        return None


def verify_firebase_token(id_token: str) -> dict:
    """Verify a Firebase ID token and return the decoded payload.
    Returns {phone_number, uid, ...} or raises HTTPException."""
    app = _get_firebase_app()
    if not app:
        raise HTTPException(501, "Firebase auth is not configured. Contact the admin.")
    try:
        from firebase_admin import auth
        decoded = auth.verify_id_token(id_token)
        return decoded
    except Exception as e:
        log.warning(f"Firebase token verification failed: {e}")
        raise HTTPException(401, "Invalid or expired verification code.")


class FirebaseAuthIn(BaseModel):
    id_token: str
    name: str = ""
    ref: str = ""


@router.post("/firebase")
def firebase_auth(body: FirebaseAuthIn, request: Request):
    """Verify Firebase phone auth token and login/register the user."""
    decoded = verify_firebase_token(body.id_token)
    phone = decoded.get("phone_number", "").strip()
    if not phone:
        raise HTTPException(400, "No phone number in the verification token.")
    firebase_uid = decoded.get("uid", "")
    ip = client_ip(request)
    geo = geo_lookup(ip)
    # Find existing user by phone
    user = users_col.find_one({"phone": phone})
    now = now_utc()
    if user:
        users_col.update_one({"id": user["id"]}, {
            "$set": {"last_login_at": now, "last_ip": ip,
                     "firebase_uid": firebase_uid},
        })
        if not user.get("country"):
            users_col.update_one({"id": user["id"]}, {
                "$set": {"country": geo["country"], "city": geo["city"]}})
        token = make_token(user["id"])
        return {"token": token, "is_new": False,
                "user": _format_user(user)}
    # Create new user
    user_id = str(uuid.uuid4())
    new_user = {
        "id": user_id,
        "phone": phone,
        "firebase_uid": firebase_uid,
        "name": body.name.strip() or "",
        "email": "",
        "password_hash": "",
        "credits": SIGNUP_CREDITS,
        "created_at": now,
        "country": geo["country"], "city": geo["city"], "last_ip": ip,
        "questions_asked": 0, "tokens_in": 0, "tokens_out": 0,
        "credits_issued_free": SIGNUP_CREDITS, "credits_issued_paid": 0,
    }
    users_col.insert_one(new_user)
    record_ledger(user_id, "free_grant", SIGNUP_CREDITS, reason="signup")
    inc_stats({"credits_issued_free": SIGNUP_CREDITS})
    token = make_token(user_id)
    return {"token": token, "is_new": True,
            "user": _format_user(new_user)}


class FirebaseLinkEmailIn(BaseModel):
    id_token: str
    email: str


@router.post("/firebase/link-email")
def link_email(body: FirebaseLinkEmailIn, user: dict = Depends(current_user)):
    """Link an email to the current Firebase-authenticated account.
    Used when the founder wants to export details or set up email-based features."""
    _verify_firebase_token(body.id_token)
    email = body.email.lower().strip()
    if not email:
        raise HTTPException(422, "Email is required.")
    existing = users_col.find_one({"email": email})
    if existing and existing["id"] != user["id"]:
        raise HTTPException(409, "This email is already linked to another account.")
    users_col.update_one({"id": user["id"]}, {"$set": {"email": email}})
    return {"ok": True, "email": email}


def _verify_firebase_token(id_token: str) -> dict:
    """Internal helper, same as verify_firebase_token but returns the decoded payload or raises."""
    app = _get_firebase_app()
    if not app:
        raise HTTPException(501, "Firebase auth is not configured.")
    try:
        from firebase_admin import auth
        return auth.verify_id_token(id_token)
    except Exception as e:
        raise HTTPException(401, "Invalid token.")


def _format_user(u: dict) -> dict:
    return {
        "id": u["id"],
        "phone": u.get("phone", ""),
        "email": u.get("email", ""),
        "name": u.get("name", ""),
        "credits": u.get("credits", 0),
        "is_admin": bool(u.get("is_admin")),
        "questionnaire_completed": bool(u.get("questionnaire_completed")),
        "org_id": u.get("org_id"),
        "org_role": u.get("org_role"),
    }


# Note: current_user is re-exported from security for server.py