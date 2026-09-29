"""Production configuration and API identity must fail closed."""
import pytest
import importlib
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import auth as journal_auth
from app.config import settings
from app.database.sqlite_db import database_url
from app.main import app


def test_production_requires_persistent_database(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr(settings, "DATABASE_URL", "")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        journal_auth.validate_production_config()


def test_production_requires_firebase_access_control(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr(settings, "DATABASE_URL", "postgresql://example.invalid/db")
    monkeypatch.setattr(settings, "FIREBASE_SERVICE_ACCOUNT_JSON", "")
    monkeypatch.setattr(settings, "ALLOWED_FIREBASE_UIDS", "")
    with pytest.raises(RuntimeError, match="FIREBASE_SERVICE_ACCOUNT_JSON"):
        journal_auth.validate_production_config()


def test_production_uses_verified_uid_not_query_parameter(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr(settings, "ALLOWED_FIREBASE_UIDS", "allowed-user")
    monkeypatch.setattr(journal_auth.auth, "verify_id_token", lambda token: {"uid": "allowed-user"})
    assert journal_auth.get_user_id(user_id="forged-user", authorization="Bearer token") == "allowed-user"
    with pytest.raises(HTTPException) as missing:
        journal_auth.get_user_id(user_id="allowed-user", authorization=None)
    assert missing.value.status_code == 401


def test_database_url_accepts_marketplace_postgres_uri(monkeypatch):
    monkeypatch.setattr(settings, "DATABASE_URL", "postgres://user:pass@localhost/db?sslmode=require")
    assert database_url() == "postgresql+psycopg://user:pass@localhost/db?sslmode=require"


def test_api_routes_require_token_on_vercel(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setattr(importlib.import_module("app.main"), "validate_production_config", lambda: None)
    with TestClient(app) as client:
        assert client.get("/api/trades").status_code == 401
        assert client.get("/api/ai-coach/providers").status_code == 401
        assert client.post("/api/ingest/csv", files={"file": ("book.csv", b"x")}).status_code == 401
