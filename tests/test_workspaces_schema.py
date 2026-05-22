from app.db import connect


def _cols(conn, table: str) -> set[str]:
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = ?",
        (table,),
    ).fetchall()
    return {r["column_name"] for r in rows}


def test_workspaces_table_columns(temp_db):
    with connect() as conn:
        cols = _cols(conn, "workspaces")
    assert {
        "id", "slug", "name", "description", "owner_human_id",
        "is_private", "deleted_at", "created_at", "updated_at",
    }.issubset(cols)


def test_workspace_members_table_columns(temp_db):
    with connect() as conn:
        cols = _cols(conn, "workspace_members")
    assert {"workspace_id", "human_id", "role", "joined_at"}.issubset(cols)


def test_workspace_invites_table_columns(temp_db):
    with connect() as conn:
        cols = _cols(conn, "workspace_invites")
    assert {
        "id", "workspace_id", "token", "created_by_human_id",
        "expires_at", "max_uses", "used_count", "revoked_at", "created_at",
    }.issubset(cols)


def test_topics_has_workspace_id_not_project_id(temp_db):
    with connect() as conn:
        cols = _cols(conn, "topics")
    assert "workspace_id" in cols
    assert "project_id" not in cols


def test_agent_instances_has_workspace_id_not_null(temp_db):
    with connect() as conn:
        row = conn.execute(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name='agent_instances' AND column_name='workspace_id'"
        ).fetchone()
    assert row is not None
    assert row["is_nullable"] == "NO"


def test_projects_table_gone(temp_db):
    with connect() as conn:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name='projects'"
        ).fetchall()
    assert rows == []


def test_workspace_slug_unique(temp_db):
    import sqlite3
    with connect() as conn:
        human_id = conn.execute(
            "INSERT INTO humans (name) VALUES ('test') RETURNING id"
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO workspaces (slug, name, owner_human_id) "
            "VALUES (?, ?, ?)",
            ("w1", "W1", human_id),
        )
        try:
            conn.execute(
                "INSERT INTO workspaces (slug, name, owner_human_id) "
                "VALUES (?, ?, ?)",
                ("w1", "Dup", human_id),
            )
            assert False, "expected unique violation"
        except sqlite3.IntegrityError:
            pass


def test_workspace_invites_token_unique(temp_db):
    import sqlite3
    with connect() as conn:
        human_id = conn.execute(
            "INSERT INTO humans (name) VALUES ('test') RETURNING id"
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO workspaces (slug, name, owner_human_id) "
            "VALUES ('w1', 'W1', ?)",
            (human_id,),
        )
        ws_id = conn.execute("SELECT id FROM workspaces").fetchone()["id"]
        conn.execute(
            "INSERT INTO workspace_invites (workspace_id, token, created_by_human_id) "
            "VALUES (?, ?, ?)",
            (ws_id, "tok1", human_id),
        )
        try:
            conn.execute(
                "INSERT INTO workspace_invites (workspace_id, token, created_by_human_id) "
                "VALUES (?, ?, ?)",
                (ws_id, "tok1", human_id),
            )
            assert False, "expected unique violation"
        except sqlite3.IntegrityError:
            pass
