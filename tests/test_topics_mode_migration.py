def test_topics_mode_column_exists(client):
    """After init_db, topics.mode should default to 'exploratory'."""
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(topics)").fetchall()}
    assert "mode" in cols


def test_topics_mode_default_exploratory(client):
    from app.db import connect
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO topics (slug, title) VALUES ('mode-default', 'x')"
        )
        topic_id = cur.lastrowid
        row = conn.execute("SELECT mode FROM topics WHERE id = ?", (topic_id,)).fetchone()
    assert row["mode"] == "exploratory"


def test_topics_mode_check_constraint(client):
    """topics.mode must be 'exploratory' or 'actionable'."""
    import sqlite3
    from app.db import connect
    with connect() as conn:
        try:
            conn.execute(
                "INSERT INTO topics (slug, title, mode) VALUES ('bad', 'x', 'bogus')"
            )
            raised = False
        except sqlite3.IntegrityError:
            raised = True
    assert raised, "expected CHECK constraint to reject mode='bogus'"
