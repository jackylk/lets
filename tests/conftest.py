"""Test fixtures for Lets.

Tests run against Postgres, matching Railway. The test database must exist:

    createdb -h localhost lets_test
"""
from __future__ import annotations

import os

import psycopg
import pytest
from fastapi.testclient import TestClient


def _test_db_url() -> str:
    return os.environ.get(
        "LETS_TEST_DATABASE_URL",
        "postgresql://jacky@localhost:5432/lets_test",
    )


def _reset_schema(url: str) -> None:
    with psycopg.connect(url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS public CASCADE")
            cur.execute("CREATE SCHEMA public")


@pytest.fixture
def temp_db(monkeypatch):
    """Fresh Postgres schema per test."""
    url = _test_db_url()
    _reset_schema(url)
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.delenv("LETS_DATABASE_URL", raising=False)

    from app import db as db_module
    db_module.reset_initialized_marker()
    db_module.init_db()
    yield url


@pytest.fixture
def client(temp_db):
    """FastAPI TestClient using a fresh DB."""
    import importlib
    from app import main as main_module

    importlib.reload(main_module)
    with TestClient(main_module.app) as c:
        yield c
