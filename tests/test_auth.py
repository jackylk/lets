def test_tokens_table_exists(temp_db):
    from app.db import connect

    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tokens'"
        ).fetchall()

    assert len(rows) == 1


def test_tokens_columns(temp_db):
    from app.db import connect

    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(tokens)").fetchall()}
    expected = {
        "id",
        "value_hash",
        "human_id",
        "agent_instance_id",
        "label",
        "created_at",
        "last_used_at",
        "revoked_at",
    }

    assert expected.issubset(cols)


def test_tokens_value_hash_unique(temp_db):
    import sqlite3

    from app.db import connect

    with connect() as conn:
        conn.execute("INSERT INTO humans (name) VALUES ('Neo')")
        human_id = conn.execute("SELECT id FROM humans WHERE name='Neo'").fetchone()["id"]
        conn.execute(
            "INSERT INTO tokens (value_hash, human_id) VALUES (?, ?)",
            ("hash_abc", human_id),
        )
        try:
            conn.execute(
                "INSERT INTO tokens (value_hash, human_id) VALUES (?, ?)",
                ("hash_abc", human_id),
            )
            assert False, "should raise IntegrityError"
        except sqlite3.IntegrityError:
            pass
