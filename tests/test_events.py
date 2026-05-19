def test_events_table_exists(temp_db):
    from app.db import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
        ).fetchall()
    assert len(rows) == 1


def test_events_columns(temp_db):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(events)").fetchall()}
    expected = {
        "id", "event_type", "actor_type", "actor_id",
        "target_type", "target_id",
        "project_id", "topic_id",
        "payload", "occurred_at",
    }
    assert expected.issubset(cols)


def test_events_insert_minimal(temp_db):
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO events (event_type, actor_type, actor_id, target_type, target_id, payload)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("test.event", "human", 1, "work_item", 42, "{}"),
        )
        eid = cursor.lastrowid
        row = conn.execute("SELECT * FROM events WHERE id = ?", (eid,)).fetchone()
    assert row["event_type"] == "test.event"
    assert row["payload"] == "{}"


def test_events_indexed_on_target_and_occurred_at(temp_db):
    from app.db import connect
    with connect() as conn:
        idx_names = {
            r["name"]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='events'"
            ).fetchall()
        }
    assert any("target" in n.lower() for n in idx_names)
    assert any("occurred" in n.lower() for n in idx_names)
