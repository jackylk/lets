from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def temp_db(monkeypatch):
    """Provide a fresh SQLite DB per test. Monkeypatches app.db.DB_PATH."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_path = Path(f.name)
    try:
        from app import db as db_module
        monkeypatch.setattr(db_module, "DB_PATH", tmp_path)
        db_module.init_db()
        yield tmp_path
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@pytest.fixture
def client(temp_db):
    """FastAPI TestClient using a fresh DB. Reimports app to pick up monkeypatched DB_PATH."""
    import importlib
    from app import main as main_module
    importlib.reload(main_module)
    return TestClient(main_module.app)
