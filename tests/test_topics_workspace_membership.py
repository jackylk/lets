import pytest


@pytest.fixture(autouse=True)
def _enable_dev_sessions(monkeypatch):
    monkeypatch.setenv("LETS_DEV_SESSIONS", "1")


def _login(client, name="alice", email=None):
    resp = client.post("/api/auth/dev-login", json={"name": name, "email": email})
    assert resp.status_code == 200
    return int(resp.json()["human_id"])


def test_list_topics_requires_membership(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.get(f"/api/workspaces/{ws['id']}/topics")
    assert r.status_code == 403


def test_create_topic_member_allowed(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    r = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "oauth", "title": "OAuth 流程"},
    )
    assert r.status_code == 200
    assert r.json()["title"] == "OAuth 流程"

    participants = client.get(f"/api/topics/{r.json()['id']}/participants").json()
    assert [h["name"] for h in participants["humans"]] == ["alice"]
    assert participants["humans"][0]["role"] == "owner"


def test_guest_cannot_create_topic(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()

    client.post("/api/auth/logout")
    joined = client.post(f"/api/invites/{inv['token']}/accept-guest", json={"name": "Guest"})
    assert joined.status_code == 200

    r = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "guest-topic", "title": "Guest Topic"},
        cookies={"lets_session": joined.cookies["lets_session"]},
    )

    assert r.status_code == 403
    assert r.json()["detail"] == "guest users cannot create topics"


def test_create_topic_non_member_403(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "oauth", "title": "OAuth"},
    )
    assert r.status_code == 403


def test_patch_topic_moves_workspace(temp_db, client):
    _login(client, "alice")
    ws_a = client.post("/api/workspaces", json={"name": "A"}).json()
    ws_b = client.post("/api/workspaces", json={"name": "B"}).json()
    topic = client.post(
        f"/api/workspaces/{ws_a['id']}/topics",
        json={"slug": "oauth", "title": "OAuth"},
    ).json()
    r = client.patch(
        f"/api/topics/{topic['id']}",
        json={"workspace_id": ws_b["id"]},
    )
    assert r.status_code == 200
    assert r.json()["workspace_id"] == ws_b["id"]


def test_patch_topic_agent_context_settings(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    topic = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "agent-rules", "title": "Agent Rules"},
    ).json()
    assert topic["agent_intervention_mode"] == "auto"
    assert topic["shared_context_mode"] == "topic_with_files"

    r = client.patch(
        f"/api/topics/{topic['id']}",
        json={
            "agent_intervention_mode": "mentions",
            "shared_context_mode": "topic_only",
        },
    )

    assert r.status_code == 200
    assert r.json()["agent_intervention_mode"] == "mentions"
    assert r.json()["shared_context_mode"] == "topic_only"

    fetched = client.get(f"/api/topics/{topic['id']}").json()
    assert fetched["agent_intervention_mode"] == "mentions"
    assert fetched["shared_context_mode"] == "topic_only"


def test_patch_topic_403_if_not_member_of_target(temp_db, client):
    alice_id = _login(client, "alice")
    ws_a = client.post("/api/workspaces", json={"name": "A"}).json()
    topic = client.post(
        f"/api/workspaces/{ws_a['id']}/topics",
        json={"slug": "x", "title": "X"},
    ).json()
    from app.db import connect
    with connect() as conn:
        bob_id = conn.execute(
            "INSERT INTO humans (name, email) VALUES ('bob', 'b@b') RETURNING id"
        ).fetchone()["id"]
        bob_ws = conn.execute(
            "INSERT INTO workspaces (slug, name, owner_human_id) "
            "VALUES ('bob-ws', 'Bob WS', ?) RETURNING id",
            (bob_id,),
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO workspace_members (workspace_id, human_id, role) "
            "VALUES (?, ?, 'owner') RETURNING workspace_id",
            (bob_ws, bob_id),
        )
    r = client.patch(
        f"/api/topics/{topic['id']}",
        json={"workspace_id": bob_ws},
    )
    assert r.status_code == 403


def test_archive_topic_hides_it_from_workspace_list(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    topic = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "archive-me", "title": "Archive Me"},
    ).json()

    r = client.post(f"/api/topics/{topic['id']}/archive")
    assert r.status_code == 200
    assert r.json()["archived_at"] is not None

    topics = client.get(f"/api/workspaces/{ws['id']}/topics").json()
    assert all(t["id"] != topic["id"] for t in topics)

    archived = client.get(f"/api/workspaces/{ws['id']}/topics?archived=true").json()
    assert [t["id"] for t in archived] == [topic["id"]]


def test_restore_topic_returns_it_to_workspace_list(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    topic = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "restore-me", "title": "Restore Me"},
    ).json()

    assert client.post(f"/api/topics/{topic['id']}/archive").status_code == 200

    r = client.post(f"/api/topics/{topic['id']}/restore")
    assert r.status_code == 200
    assert r.json()["archived_at"] is None

    topics = client.get(f"/api/workspaces/{ws['id']}/topics").json()
    assert topic["id"] in [t["id"] for t in topics]

    archived = client.get(f"/api/workspaces/{ws['id']}/topics?archived=true").json()
    assert all(t["id"] != topic["id"] for t in archived)


def test_workspace_topics_scope_mine_filters_to_participation(temp_db, client):
    alice_id = _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    mine = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "mine", "title": "Mine"},
    ).json()
    from app.db import connect
    with connect() as conn:
        other = conn.execute(
            "INSERT INTO topics (slug, title, workspace_id) VALUES ('all-only', 'All Only', ?) RETURNING id",
            (ws["id"],),
        ).fetchone()["id"]
        assert alice_id
        conn.execute(
            "DELETE FROM topic_participants WHERE topic_id = ? AND participant_type = 'human'",
            (other,),
        )

    mine_rows = client.get(f"/api/workspaces/{ws['id']}/topics?scope=mine").json()
    all_rows = client.get(f"/api/workspaces/{ws['id']}/topics?scope=all").json()
    public_id = next(t["id"] for t in all_rows if t["title"] == "全员话题")

    assert {t["id"] for t in mine_rows} == {public_id, mine["id"]}
    assert {t["id"] for t in all_rows} == {public_id, mine["id"], other}


def test_invited_member_sees_public_topic_not_private_until_added(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    private = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "private", "title": "Private"},
    ).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()

    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    assert client.post(f"/api/invites/{inv['token']}/accept").status_code == 200

    visible = client.get(f"/api/workspaces/{ws['id']}/topics?scope=all").json()
    assert [t["title"] for t in visible] == ["全员话题"]
    assert client.get(f"/api/topics/{private['id']}/messages").status_code == 403

    from app.db import connect
    with connect() as conn:
        bob_id = conn.execute("SELECT id FROM humans WHERE name = 'bob'").fetchone()["id"]

    client.post("/api/auth/logout")
    _login(client, "alice")
    added = client.post(
        f"/api/topics/{private['id']}/participants",
        json={"participant_type": "human", "participant_id": bob_id},
    )
    assert added.status_code == 200

    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    visible_after_add = client.get(f"/api/workspaces/{ws['id']}/topics?scope=all").json()
    assert private["id"] in {t["id"] for t in visible_after_add}
    msg = client.post(
        "/api/messages",
        json={
            "topic_id": private["id"],
            "type": "chat",
            "actor_type": "human",
            "body": "hello after add",
        },
    )
    assert msg.status_code == 200, msg.text


def test_add_topic_participants_from_workspace_pool(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    topic = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "participants", "title": "Participants"},
    ).json()

    from app.db import connect
    from app.identity import ensure_agent_instance
    with connect() as conn:
        bob_id = conn.execute(
            "INSERT INTO humans (name, email) VALUES ('bob', 'b@b') RETURNING id"
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO workspace_members (workspace_id, human_id, role) "
            "VALUES (?, ?, 'member') RETURNING workspace_id",
            (ws["id"], bob_id),
        )
    agent_id = ensure_agent_instance("claude", bob_id, "bob-mbp", workspace_id=ws["id"])

    r = client.post(
        f"/api/topics/{topic['id']}/participants",
        json={"participant_type": "human", "participant_id": bob_id},
    )
    assert r.status_code == 200
    assert "bob" in {h["name"] for h in r.json()["humans"]}

    r = client.post(
        f"/api/topics/{topic['id']}/participants",
        json={"participant_type": "agent", "participant_id": agent_id},
    )
    assert r.status_code == 200
    assert agent_id in {a["id"] for a in r.json()["agents"]}

    r = client.delete(f"/api/topics/{topic['id']}/participants/agent/{agent_id}")
    assert r.status_code == 200
    assert agent_id not in {a["id"] for a in r.json()["agents"]}


def test_topic_member_cannot_add_participant_unless_owner(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    topic = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "managed", "title": "Managed"},
    ).json()

    from app.db import connect
    with connect() as conn:
        bob_id = conn.execute(
            "INSERT INTO humans (name, email) VALUES ('bob', 'b@b') RETURNING id"
        ).fetchone()["id"]
        carol_id = conn.execute(
            "INSERT INTO humans (name, email) VALUES ('carol', 'c@c') RETURNING id"
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO workspace_members (workspace_id, human_id, role) "
            "VALUES (?, ?, 'member') RETURNING workspace_id",
            (ws["id"], bob_id),
        )
        conn.execute(
            "INSERT INTO workspace_members (workspace_id, human_id, role) "
            "VALUES (?, ?, 'member') RETURNING workspace_id",
            (ws["id"], carol_id),
        )
        conn.execute(
            """
            INSERT INTO topic_participants (topic_id, participant_type, participant_id, role)
            VALUES (?, 'human', ?, 'member')
            RETURNING topic_id
            """,
            (topic["id"], bob_id),
        )

    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.post(
        f"/api/topics/{topic['id']}/participants",
        json={"participant_type": "human", "participant_id": carol_id},
    )
    assert r.status_code == 403


def test_workspace_owner_can_manage_private_topic_without_participating(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    topic = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "owner-managed", "title": "Owner Managed"},
    ).json()

    from app.db import connect
    with connect() as conn:
        alice_id = conn.execute("SELECT id FROM humans WHERE name = 'alice'").fetchone()["id"]
        bob_id = conn.execute(
            "INSERT INTO humans (name, email) VALUES ('bob', 'b@b') RETURNING id"
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO workspace_members (workspace_id, human_id, role) "
            "VALUES (?, ?, 'member') RETURNING workspace_id",
            (ws["id"], bob_id),
        )
        conn.execute(
            "DELETE FROM topic_participants WHERE topic_id = ? AND participant_id = ?",
            (topic["id"], alice_id),
        )

    r = client.post(
        f"/api/topics/{topic['id']}/participants",
        json={"participant_type": "human", "participant_id": bob_id},
    )
    assert r.status_code == 200
    assert "bob" in {h["name"] for h in r.json()["humans"]}


def test_public_topic_participants_cannot_be_removed(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    public_topic = next(
        t for t in client.get(f"/api/workspaces/{ws['id']}/topics?scope=all").json()
        if t["title"] == "全员话题"
    )

    from app.db import connect
    with connect() as conn:
        alice_id = conn.execute("SELECT id FROM humans WHERE name = 'alice'").fetchone()["id"]

    r = client.delete(f"/api/topics/{public_topic['id']}/participants/human/{alice_id}")
    assert r.status_code == 400


def test_removing_workspace_member_cleans_topic_participants(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    topic = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "cleanup-member", "title": "Cleanup Member"},
    ).json()

    from app.db import connect
    with connect() as conn:
        bob_id = conn.execute(
            "INSERT INTO humans (name, email) VALUES ('bob', 'b@b') RETURNING id"
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO workspace_members (workspace_id, human_id, role) "
            "VALUES (?, ?, 'member') RETURNING workspace_id",
            (ws["id"], bob_id),
        )
        conn.execute(
            """
            INSERT INTO topic_participants (topic_id, participant_type, participant_id, role)
            VALUES (?, 'human', ?, 'member')
            RETURNING topic_id
            """,
            (topic["id"], bob_id),
        )

    r = client.delete(f"/api/workspaces/{ws['id']}/members/{bob_id}")
    assert r.status_code == 200

    with connect() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM topic_participants
            WHERE topic_id = ? AND participant_type = 'human' AND participant_id = ?
            """,
            (topic["id"], bob_id),
        ).fetchone()
    assert row is None


def test_removing_workspace_agent_cleans_topic_participants(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    topic = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "cleanup-agent", "title": "Cleanup Agent"},
    ).json()

    from app.db import connect
    from app.identity import ensure_agent_instance
    with connect() as conn:
        alice_id = conn.execute("SELECT id FROM humans WHERE name = 'alice'").fetchone()["id"]
    agent_id = ensure_agent_instance("claude", alice_id, "alice-mbp", workspace_id=ws["id"])
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO topic_participants (topic_id, participant_type, participant_id, role)
            VALUES (?, 'agent', ?, 'member')
            ON CONFLICT DO NOTHING
            RETURNING topic_id
            """,
            (topic["id"], agent_id),
        )

    r = client.delete(f"/api/workspaces/{ws['id']}/agent-members/{agent_id}")
    assert r.status_code == 200

    with connect() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM topic_participants
            WHERE topic_id = ? AND participant_type = 'agent' AND participant_id = ?
            """,
            (topic["id"], agent_id),
        ).fetchone()
    assert row is None


def test_deleted_agent_not_returned_as_topic_participant(temp_db, client):
    alice_id = _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    topic = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "deleted-agent", "title": "Deleted Agent"},
    ).json()

    from app.db import connect
    from app.identity import ensure_agent_instance
    agent_id = ensure_agent_instance("codex", alice_id, "alice-mbp", workspace_id=ws["id"])
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO topic_participants (topic_id, participant_type, participant_id, role)
            VALUES (?, 'agent', ?, 'member')
            ON CONFLICT DO NOTHING
            RETURNING topic_id
            """,
            (topic["id"], agent_id),
        )
        conn.execute(
            """
            INSERT INTO messages (topic_id, type, actor_type, actor_id, body)
            VALUES (?, 'chat', 'agent', ?, 'old reply')
            RETURNING id
            """,
            (topic["id"], agent_id),
        )
        conn.execute(
            "UPDATE agent_instances SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
            (agent_id,),
        )

    r = client.get(f"/api/topics/{topic['id']}/participants")
    assert r.status_code == 200
    assert r.json()["agents"] == []


def test_delete_agent_cleans_topic_participants(temp_db, client):
    alice_id = _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    topic = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "delete-agent-cleanup", "title": "Delete Agent Cleanup"},
    ).json()

    from app.db import connect
    from app.identity import ensure_agent_instance
    agent_id = ensure_agent_instance("codex", alice_id, "alice-mbp", workspace_id=ws["id"])
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO topic_participants (topic_id, participant_type, participant_id, role)
            VALUES (?, 'agent', ?, 'member')
            ON CONFLICT DO NOTHING
            RETURNING topic_id
            """,
            (topic["id"], agent_id),
        )

    r = client.delete(f"/api/agents/{agent_id}")
    assert r.status_code == 200

    with connect() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM topic_participants
            WHERE participant_type = 'agent' AND participant_id = ?
            """,
            (agent_id,),
        ).fetchone()
    assert row is None


def test_delete_topic_hides_it_and_blocks_direct_access(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    topic = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "delete-me", "title": "Delete Me"},
    ).json()

    r = client.delete(f"/api/topics/{topic['id']}")
    assert r.status_code == 200
    assert r.json() == {"ok": True}

    topics = client.get(f"/api/workspaces/{ws['id']}/topics").json()
    assert all(t["id"] != topic["id"] for t in topics)
    assert client.get(f"/api/topics/{topic['id']}").status_code == 404


def test_topic_lifecycle_actions_require_membership(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    topic = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "private-topic", "title": "Private Topic"},
    ).json()

    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")

    assert client.post(f"/api/topics/{topic['id']}/archive").status_code == 403
    assert client.post(f"/api/topics/{topic['id']}/restore").status_code == 403
    assert client.delete(f"/api/topics/{topic['id']}").status_code == 403
