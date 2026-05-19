"""Test fixtures for Lets.

Two fixtures, both function-scoped:

- ``temp_db``: creates a fresh SQLite DB per test, monkeypatches
  ``app.db.DB_PATH``, then calls ``init_db()``. Works because
  ``app.db.connect()`` reads ``DB_PATH`` at call time (not at import).

- ``client``: depends on ``temp_db``, then reloads ``app.main`` so its
  module-level imports re-bind, and enters ``TestClient`` as a context
  manager so FastAPI lifespan events run.

**Do not** import ``app.main`` at test module scope — go through the
``client`` fixture. Module-scope imports would hold stale references
across tests because ``client`` reloads the module per test.
"""
from __future__ import annotations

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
    """FastAPI TestClient using a fresh DB.

    Reloads app.main so its module-level imports re-bind under the
    monkeypatched DB_PATH, then enters TestClient as a context manager
    so FastAPI startup/shutdown events run.
    """
    import importlib
    from app import main as main_module
    importlib.reload(main_module)
    with TestClient(main_module.app) as c:
        yield c
