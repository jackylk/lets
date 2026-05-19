def test_topics_table_exists(temp_db):
    from app.db import connect

    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='topics'"
        ).fetchall()

    assert len(rows) == 1


def test_topics_columns(temp_db):
    from app.db import connect

    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(topics)").fetchall()}

    assert {"id", "slug", "title", "created_at", "updated_at"}.issubset(cols)


def test_topics_slug_unique(temp_db):
    import sqlite3

    from app.db import connect

    with connect() as conn:
        conn.execute("INSERT INTO topics (slug, title) VALUES (?, ?)", ("t-ppt", "PPT"))
        try:
            conn.execute("INSERT INTO topics (slug, title) VALUES (?, ?)", ("t-ppt", "Other"))
            assert False, "should raise IntegrityError"
        except sqlite3.IntegrityError:
            pass
