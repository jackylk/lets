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


def test_adopt_task_tree_from_proposal(client):
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    from app.messages import post_message

    hid = ensure_human("AdoptHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('adopt-tt', 'x')")
        tid = cur.lastrowid
    proposal_id = post_message(
        topic_id=tid, type="task_tree_proposal",
        actor_type="agent", actor_id=None,
        body="拆成 3 个",
        metadata={
            "title": "PPT Tree",
            "items": [
                {"title": "Outline"},
                {"title": "P1", "parent_index": 0},
                {"title": "P2", "parent_index": 0},
            ],
        },
    )
    res = client.post(
        f"/api/topics/{tid}/task-tree",
        cookies={"lets_session": sess},
        json={"proposal_message_id": proposal_id},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["tree"]["version"] == 1
    assert len(body["items"]) == 3


def test_adopt_task_tree_increments_version(client):
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    from app.messages import post_message

    hid = ensure_human("VHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('adopt-v2', 'x')")
        tid = cur.lastrowid
    p1 = post_message(
        topic_id=tid, type="task_tree_proposal",
        actor_type="agent", actor_id=None,
        body="v1",
        metadata={"title": "T1", "items": [{"title": "A"}]},
    )
    client.post(
        f"/api/topics/{tid}/task-tree",
        cookies={"lets_session": sess},
        json={"proposal_message_id": p1},
    )
    p2 = post_message(
        topic_id=tid, type="task_tree_proposal",
        actor_type="agent", actor_id=None,
        body="v2",
        metadata={"title": "T2", "items": [{"title": "B"}, {"title": "C"}]},
    )
    res2 = client.post(
        f"/api/topics/{tid}/task-tree",
        cookies={"lets_session": sess},
        json={"proposal_message_id": p2},
    )
    assert res2.status_code == 201
    body = res2.json()
    assert body["tree"]["version"] == 2
    assert [i["title"] for i in body["items"]] == ["B", "C"]


def test_adopt_goal_from_proposal(client):
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    from app.messages import post_message

    hid = ensure_human("GoalHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('adopt-goal', 'x')")
        tid = cur.lastrowid
    proposal_id = post_message(
        topic_id=tid, type="goal_proposal",
        actor_type="agent", actor_id=None,
        body="30 分钟 talk",
        metadata={"artifact_id": None, "spec_text": "30 分钟 talk · 技术受众"},
    )
    res = client.post(
        f"/api/topics/{tid}/goal",
        cookies={"lets_session": sess},
        json={"goal_proposal_message_id": proposal_id},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["tree"]["goal_spec_text"] == "30 分钟 talk · 技术受众"
    assert body["items"] == []  # goal adoption alone does not create items


def test_add_task_item(client):
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    from app.task_trees import upsert_tree

    hid = ensure_human("AddHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('add-item', 'x')")
        tid = cur.lastrowid
    tree = upsert_tree(
        topic_id=tid, goal_artifact_id=None, goal_spec_text=None,
        proposal_message_id=None, approved_by_human_id=hid,
    )
    res = client.post(
        "/api/task-items",
        cookies={"lets_session": sess},
        json={
            "task_tree_id": tree["id"],
            "title": "new item",
            "summary": "compare two directions",
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["title"] == "new item"
    assert body["summary"] == "compare two directions"
    assert body["status"] == "pending"
    assert body["position"] == 0


def test_patch_task_item_status(client):
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    from app.task_trees import upsert_tree, add_item

    hid = ensure_human("PatchHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('patch-item', 'x')")
        tid = cur.lastrowid
    tree = upsert_tree(
        topic_id=tid, goal_artifact_id=None, goal_spec_text=None,
        proposal_message_id=None, approved_by_human_id=hid,
    )
    item = add_item(tree["id"], "todo")
    res = client.patch(
        f"/api/task-items/{item['id']}",
        cookies={"lets_session": sess},
        json={"status": "done", "summary": "shipped"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "done"
    assert res.json()["summary"] == "shipped"


def test_patch_task_item_invalid_status(client):
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    from app.task_trees import upsert_tree, add_item

    hid = ensure_human("BadPatchHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('badpatch', 'x')")
        tid = cur.lastrowid
    tree = upsert_tree(
        topic_id=tid, goal_artifact_id=None, goal_spec_text=None,
        proposal_message_id=None, approved_by_human_id=hid,
    )
    item = add_item(tree["id"], "todo")
    res = client.patch(
        f"/api/task-items/{item['id']}",
        cookies={"lets_session": sess},
        json={"status": "in-progress"},
    )
    assert res.status_code == 400
