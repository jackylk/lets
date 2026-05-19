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
