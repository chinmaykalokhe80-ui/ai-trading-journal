"""Keep tests isolated from the user's journal and external services."""
import os
import tempfile

_test_dir = tempfile.TemporaryDirectory(prefix="journal-tests-")
os.environ["SQLITE_DB_PATH"] = os.path.join(_test_dir.name, "tests.db")
os.environ.pop("DATABASE_URL", None)
os.environ.pop("VERCEL", None)
os.environ["ENVIRONMENT"] = "development"
os.environ["GEMINI_API_KEY"] = ""
os.environ["FIREBASE_SERVICE_ACCOUNT_PATH"] = ""
os.environ.pop("FIRESTORE_EMULATOR_HOST", None)

import pytest
from app.database.sqlite_db import Base, engine


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch):
    from app.database import firestore
    from app.config import settings
    monkeypatch.setattr(firestore, "db_client", None)
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
