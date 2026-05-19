def _auth_header():
    from app.auth import issue_token
    from app.identity import ensure_human

    human_id = ensure_human("admin")
    token, _ = issue_token(human_id=human_id, label="events-test")
    return {"Authorization": f"Bearer {token}"}


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


def test_record_event_helper(temp_db):
    from app.events import record_event
    eid = record_event(
        event_type="idea.claimed",
        actor_type="agent",
        actor_id=1,
        target_type="work_item",
        target_id=42,
        payload={"git_branch": "master"},
    )
    assert isinstance(eid, int)


def test_record_event_payload_is_json(temp_db):
    import json
    from app.events import record_event
    from app.db import connect
    eid = record_event(
        event_type="t",
        actor_type="human",
        actor_id=1,
        target_type="x",
        target_id=1,
        payload={"k": "v"},
    )
    with connect() as conn:
        row = conn.execute("SELECT payload FROM events WHERE id = ?", (eid,)).fetchone()
    parsed = json.loads(row["payload"])
    assert parsed["k"] == "v"


def test_post_events_endpoint(client):
    headers = _auth_header()
    r = client.post(
        "/api/events",
        headers=headers,
        json={
            "event_type": "idea.claimed",
            "actor_type": "agent",
            "actor_id": 1,
            "target_type": "work_item",
            "target_id": 42,
            "payload": {"branch": "master"},
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["event_type"] == "idea.claimed"
    assert data["payload"]["branch"] == "master"


def test_get_events_filtered_by_target(client):
    headers = _auth_header()
    client.post("/api/events", json={
        "event_type": "a.b", "actor_type": "human", "actor_id": 1,
        "target_type": "topic", "target_id": 10, "payload": {},
    }, headers=headers)
    client.post("/api/events", json={
        "event_type": "c.d", "actor_type": "human", "actor_id": 1,
        "target_type": "topic", "target_id": 11, "payload": {},
    }, headers=headers)
    r = client.get("/api/events?target_type=topic&target_id=10", headers=headers)
    assert r.status_code == 200
    events = r.json()
    assert len(events) == 1
    assert events[0]["event_type"] == "a.b"
