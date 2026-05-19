def test_humans_table_exists(temp_db):
    from app.db import connect
    with connect() as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='humans'").fetchall()
    assert len(rows) == 1


def test_humans_columns(temp_db):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(humans)").fetchall()}
    assert {"id", "name", "email", "created_at", "updated_at"}.issubset(cols)


def test_humans_insert(temp_db):
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO humans (name, email) VALUES (?, ?)",
            ("Neo", "neo@example.com"),
        )
        hid = cursor.lastrowid
        row = conn.execute("SELECT * FROM humans WHERE id = ?", (hid,)).fetchone()
    assert row["name"] == "Neo"
    assert row["email"] == "neo@example.com"


def test_agent_roles_table_exists(temp_db):
    from app.db import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_roles'"
        ).fetchall()
    assert len(rows) == 1


def test_agent_roles_columns(temp_db):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(agent_roles)").fetchall()}
    assert {"id", "name", "description", "created_at"}.issubset(cols)


def test_agent_roles_seeded(temp_db):
    """init_db should seed claude and codex roles."""
    from app.db import connect
    with connect() as conn:
        names = {r["name"] for r in conn.execute("SELECT name FROM agent_roles").fetchall()}
    assert "claude" in names
    assert "codex" in names


def test_agent_instances_table_exists(temp_db):
    from app.db import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='agent_instances'"
        ).fetchall()
    assert len(rows) == 1


def test_agent_instances_columns(temp_db):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(agent_instances)").fetchall()}
    assert {"id", "role_id", "human_id", "device_label", "status", "last_seen_at", "created_at"}.issubset(cols)


def test_agent_instances_unique_per_human_device(temp_db):
    """A human cannot have two instances of the same role on the same device."""
    from app.db import connect
    with connect() as conn:
        conn.execute("INSERT INTO humans (name) VALUES ('Neo')")
        human_id = conn.execute("SELECT id FROM humans WHERE name='Neo'").fetchone()["id"]
        role_id = conn.execute("SELECT id FROM agent_roles WHERE name='claude'").fetchone()["id"]
        conn.execute(
            "INSERT INTO agent_instances (role_id, human_id, device_label) VALUES (?, ?, ?)",
            (role_id, human_id, "neo-mbp"),
        )
        import sqlite3
        try:
            conn.execute(
                "INSERT INTO agent_instances (role_id, human_id, device_label) VALUES (?, ?, ?)",
                (role_id, human_id, "neo-mbp"),
            )
            assert False, "should have raised IntegrityError"
        except sqlite3.IntegrityError:
            pass


def test_ensure_human_creates(temp_db):
    from app.identity import ensure_human
    hid = ensure_human("Neo", email="neo@example.com")
    assert isinstance(hid, int) and hid > 0


def test_ensure_human_idempotent(temp_db):
    from app.identity import ensure_human
    a = ensure_human("Neo")
    b = ensure_human("Neo")
    assert a == b


def test_ensure_agent_instance_creates(temp_db):
    from app.identity import ensure_human, ensure_agent_instance
    hid = ensure_human("Neo")
    iid = ensure_agent_instance(role="claude", human_id=hid, device_label="neo-mbp")
    assert isinstance(iid, int)


def test_ensure_agent_instance_idempotent(temp_db):
    from app.identity import ensure_human, ensure_agent_instance
    hid = ensure_human("Neo")
    a = ensure_agent_instance(role="claude", human_id=hid, device_label="neo-mbp")
    b = ensure_agent_instance(role="claude", human_id=hid, device_label="neo-mbp")
    assert a == b


def test_ensure_agent_instance_unknown_role_raises(temp_db):
    from app.identity import ensure_human, ensure_agent_instance
    hid = ensure_human("Neo")
    import pytest
    with pytest.raises(ValueError, match="unknown agent role"):
        ensure_agent_instance(role="nonexistent", human_id=hid, device_label="x")
