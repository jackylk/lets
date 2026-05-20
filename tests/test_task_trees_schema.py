def test_task_trees_table_exists(client):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(task_trees)").fetchall()}
    expected = {
        "id", "topic_id", "goal_artifact_id", "goal_spec_text",
        "version", "approved_at", "approved_by_human_id",
        "proposal_message_id", "created_at", "updated_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_task_trees_topic_id_unique(client):
    """One topic can only have one task_tree row."""
    import sqlite3
    from app.db import connect
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('tt-uniq', 'x')")
        tid = cur.lastrowid
        conn.execute("INSERT INTO task_trees (topic_id) VALUES (?)", (tid,))
        try:
            conn.execute("INSERT INTO task_trees (topic_id) VALUES (?)", (tid,))
            raised = False
        except sqlite3.IntegrityError:
            raised = True
    assert raised


def test_task_items_table_exists(client):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(task_items)").fetchall()}
    expected = {
        "id", "task_tree_id", "parent_item_id", "title",
        "summary", "linked_message_id", "deliverable_artifact_id",
        "owner_human_id", "owner_agent_instance_id",
        "status", "position", "created_at", "updated_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_task_items_owner_xor_constraint(client):
    """task_items: owner_human_id and owner_agent_instance_id cannot both be set."""
    import sqlite3
    from app.db import connect
    from app.identity import ensure_human, ensure_agent_instance

    hid = ensure_human("Owner Test")
    aid = ensure_agent_instance(role="claude", human_id=hid, device_label="dev")

    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('tt-owner', 'x')")
        tid = cur.lastrowid
        cur = conn.execute("INSERT INTO task_trees (topic_id) VALUES (?)", (tid,))
        tree_id = cur.lastrowid
        try:
            conn.execute(
                """INSERT INTO task_items (task_tree_id, title,
                                           owner_human_id, owner_agent_instance_id)
                   VALUES (?, ?, ?, ?)""",
                (tree_id, "both owners", hid, aid),
            )
            raised = False
        except sqlite3.IntegrityError:
            raised = True
    assert raised


def test_task_items_status_check(client):
    """task_items.status: pending|active|done only."""
    import sqlite3
    from app.db import connect
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('tt-status', 'x')")
        tid = cur.lastrowid
        cur = conn.execute("INSERT INTO task_trees (topic_id) VALUES (?)", (tid,))
        tree_id = cur.lastrowid
        try:
            conn.execute(
                "INSERT INTO task_items (task_tree_id, title, status) VALUES (?, ?, ?)",
                (tree_id, "bogus status", "in-progress"),
            )
            raised = False
        except sqlite3.IntegrityError:
            raised = True
    assert raised
