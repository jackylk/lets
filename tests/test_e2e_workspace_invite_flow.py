"""End-to-end test for the workspace + membership + invite feature.

Walks the full happy-path scenario from the spec:
- Alice creates a new workspace + topic
- Alice invites Bob (magic link)
- Bob accepts and gains visibility
- Bob posts a message in the topic
- Alice moves the topic to her other workspace
- Bob loses access to the moved topic
"""
import pytest


@pytest.fixture(autouse=True)
def _enable_dev_sessions(monkeypatch):
    monkeypatch.setenv("LETS_DEV_SESSIONS", "1")


def _login(client, name, email=None):
    resp = client.post("/api/auth/dev-login", json={"name": name, "email": email})
    assert resp.status_code == 200, resp.text
    return int(resp.json()["human_id"])


def test_full_invite_flow(temp_db, client):
    # Alice: first login auto-creates "我的工作区". Then she creates a new workspace.
    _login(client, "alice")
    new_ws = client.post("/api/workspaces", json={"name": "用户认证"}).json()
    all_alice = client.get("/api/workspaces").json()
    names = {w["name"] for w in all_alice}
    assert names == {"我的工作区", "用户认证"}

    # Topic in the new workspace
    topic = client.post(
        f"/api/workspaces/{new_ws['id']}/topics",
        json={"slug": "oauth", "title": "OAuth 流程"},
    ).json()
    assert topic["workspace_id"] == new_ws["id"]

    # Alice invites Bob
    inv = client.post(f"/api/workspaces/{new_ws['id']}/invites", json={}).json()
    assert "token" in inv

    # Bob accepts
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    accept = client.post(f"/api/invites/{inv['token']}/accept")
    assert accept.status_code == 200
    assert accept.json()["workspace_id"] == new_ws["id"]

    # Bob sees both his own "我的工作区" (onboarding) and the invited "用户认证"
    bob_workspaces = client.get("/api/workspaces").json()
    bob_names = {w["name"] for w in bob_workspaces}
    assert "用户认证" in bob_names
    assert "我的工作区" in bob_names  # his own from onboarding

    # Bob sees the topic Alice created
    topics_seen = client.get(f"/api/workspaces/{new_ws['id']}/topics").json()
    assert topic["id"] in [t["id"] for t in topics_seen]

    # Bob posts a message
    msg = client.post(
        "/api/messages",
        json={
            "topic_id": topic["id"],
            "type": "chat",
            "actor_type": "human",
            "body": "hello from Bob",
        },
    )
    assert msg.status_code == 200, msg.text

    # Alice moves topic to her '我的工作区' (a workspace Bob is NOT a member of)
    client.post("/api/auth/logout")
    _login(client, "alice")
    alice_workspaces = client.get("/api/workspaces").json()
    alice_my_ws = next(w for w in alice_workspaces if w["name"] == "我的工作区")
    moved = client.patch(
        f"/api/topics/{topic['id']}", json={"workspace_id": alice_my_ws["id"]}
    )
    assert moved.status_code == 200
    assert moved.json()["workspace_id"] == alice_my_ws["id"]

    # Bob loses access: the topic no longer shows under 用户认证
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    bob_topics_in_old = client.get(f"/api/workspaces/{new_ws['id']}/topics").json()
    assert topic["id"] not in [t["id"] for t in bob_topics_in_old]
    # And direct topic access is forbidden
    r = client.get(f"/api/topics/{topic['id']}/messages")
    assert r.status_code == 403
