"""Verify Firebase ID tokens before serving a publicly deployed journal."""
import json
import os

import firebase_admin
from firebase_admin import auth, credentials
from fastapi import Header, HTTPException, Query

from app.config import settings


def production_mode() -> bool:
    return settings.ENVIRONMENT.lower() == "production" or bool(os.getenv("VERCEL"))


def validate_production_config() -> None:
    if not production_mode():
        return
    if not settings.DATABASE_URL or not settings.DATABASE_URL.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
        raise RuntimeError("Production requires DATABASE_URL for persistent PostgreSQL storage.")
    if not settings.FIREBASE_SERVICE_ACCOUNT_JSON or not settings.ALLOWED_FIREBASE_UIDS.strip():
        raise RuntimeError("Production requires FIREBASE_SERVICE_ACCOUNT_JSON and ALLOWED_FIREBASE_UIDS.")
    if not firebase_admin._apps:
        firebase_admin.initialize_app(credentials.Certificate(json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON)))


def get_user_id(
    user_id: str = Query("single_user"),
    authorization: str | None = Header(None),
) -> str:
    if not production_mode():
        return user_id
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Sign in to access the journal.")
    try:
        uid = auth.verify_id_token(authorization[7:])["uid"]
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired sign-in token.") from exc
    allowed = {item.strip() for item in settings.ALLOWED_FIREBASE_UIDS.split(",") if item.strip()}
    if uid not in allowed:
        raise HTTPException(status_code=403, detail="This account is not allowed to access the journal.")
    return uid
