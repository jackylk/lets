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
    assert {
        "id",
        "role_id",
        "owner_human_id",
        "device_label",
        "model",
        "display_name",
        "paused_at",
        "deleted_at",
        "created_at",
    }.issubset(cols)


def test_agent_instances_unique_per_human_device(temp_db):
    """A human cannot have two instances of the same role on the same device."""
    from app.db import connect
    with connect() as conn:
        conn.execute("INSERT INTO humans (name) VALUES ('Neo')")
        human_id = conn.execute("SELECT id FROM humans WHERE name='Neo'").fetchone()["id"]
        role_id = conn.execute("SELECT id FROM agent_roles WHERE name='claude'").fetchone()["id"]
        conn.execute(
            "INSERT INTO agent_instances (role_id, owner_human_id, device_label) VALUES (?, ?, ?)",
            (role_id, human_id, "neo-mbp"),
        )
        import sqlite3
        try:
            conn.execute(
                "INSERT INTO agent_instances (role_id, owner_human_id, device_label) VALUES (?, ?, ?)",
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
    from app.db import connect
    from app.identity import ensure_human, ensure_agent_instance
    hid = ensure_human("Neo")
    iid = ensure_agent_instance(role="claude", human_id=hid, device_label="neo-mbp")
    assert isinstance(iid, int)
    with connect() as conn:
        row = conn.execute(
            "SELECT display_name FROM agent_instances WHERE id = ?",
            (iid,),
        ).fetchone()
    assert row["display_name"] == "Neo"


def test_ensure_agent_instance_assigns_distinct_display_names_per_owner(temp_db):
    from app.db import connect
    from app.identity import ensure_human, ensure_agent_instance

    hid = ensure_human("Neo")
    first = ensure_agent_instance(role="claude", human_id=hid, device_label="neo-mbp")
    second = ensure_agent_instance(role="codex", human_id=hid, device_label="neo-mbp")

    with connect() as conn:
        rows = conn.execute(
            "SELECT display_name FROM agent_instances WHERE id IN (?, ?) ORDER BY id",
            (first, second),
        ).fetchall()
    assert [r["display_name"] for r in rows] == ["Neo", "Trinity"]


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


def test_identity_me_creates_human_on_first_call(client):
    response = client.get(
        "/api/identity/me",
        headers={
            "X-Lets-Human": "Neo",
            "X-Lets-Human-Email": "neo@example.com",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["human"]["name"] == "Neo"
    assert isinstance(data["human"]["id"], int)


def test_identity_me_idempotent(client):
    response1 = client.get("/api/identity/me", headers={"X-Lets-Human": "Trinity"})
    response2 = client.get("/api/identity/me", headers={"X-Lets-Human": "Trinity"})

    assert response1.json()["human"]["id"] == response2.json()["human"]["id"]


def test_identity_me_includes_agent_instance_when_headers_given(client):
    response = client.get(
        "/api/identity/me",
        headers={
            "X-Lets-Human": "Neo",
            "X-Lets-Agent-Role": "claude",
            "X-Lets-Device": "neo-mbp",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["agent_instance"]["device_label"] == "neo-mbp"
    assert data["agent_instance"]["role"] == "claude"


def test_identity_me_missing_human_returns_400(client):
    response = client.get("/api/identity/me")

    assert response.status_code == 400
