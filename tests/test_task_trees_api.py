def test_get_task_tree_empty(client):
    """When no task_tree exists for a topic, return tree=None, items=[]."""
    from app.db import connect
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('gtt-empty', 'x')")
        tid = cur.lastrowid
    res = client.get(f"/api/topics/{tid}/task-tree", headers={"X-Lets-Human": "Reader"})
    assert res.status_code == 401  # no Bearer / no session


def test_get_task_tree_empty_with_session(client):
    """When no tree exists, session-authed read returns {tree: None, items: []}."""
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    hid = ensure_human("Reader")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('gtt-sess', 'x')")
        tid = cur.lastrowid
    res = client.get(
        f"/api/topics/{tid}/task-tree",
        cookies={"lets_session": sess},
    )
    assert res.status_code == 200
    body = res.json()
    assert body == {"tree": None, "items": []}


def test_get_task_tree_with_items(client):
    """After seeding a tree + items, the response shape is correct."""
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    from app.task_trees import upsert_tree, replace_items

    hid = ensure_human("OwnerHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('gtt-items', 'x')")
        tid = cur.lastrowid
    tree = upsert_tree(
        topic_id=tid,
        goal_artifact_id=None,
        goal_spec_text="Spec goes here",
        proposal_message_id=None,
        approved_by_human_id=hid,
    )
    replace_items(tree["id"], [
        {"title": "Outline"},
        {"title": "Section 1", "parent_index": 0},
        {"title": "Section 2", "parent_index": 0},
    ])
    res = client.get(
        f"/api/topics/{tid}/task-tree",
        cookies={"lets_session": sess},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["tree"]["goal_spec_text"] == "Spec goes here"
    assert len(body["items"]) == 3
    # First item has no parent; later two are children of first
    assert body["items"][0]["parent_item_id"] is None
    children = [i for i in body["items"] if i["parent_item_id"] == body["items"][0]["id"]]
    assert len(children) == 2
