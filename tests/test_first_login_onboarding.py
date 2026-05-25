import pytest


@pytest.fixture(autouse=True)
def _enable_dev_sessions(monkeypatch):
    monkeypatch.setenv("LETS_DEV_SESSIONS", "1")


def _login(client, name="alice", email=None):
    resp = client.post("/api/auth/dev-login", json={"name": name, "email": email})
    assert resp.status_code == 200
    return int(resp.json()["human_id"])


def test_first_login_creates_workspace_and_topic(temp_db, client):
    _login(client, "alice")
    workspaces = client.get("/api/workspaces").json()
    assert len(workspaces) == 1
    assert workspaces[0]["name"] == "我的工作区"
    ws_id = workspaces[0]["id"]
    topics = client.get(f"/api/workspaces/{ws_id}/topics").json()
    assert len(topics) == 1
    assert topics[0]["title"] == "全员话题"
    assert topics[0]["visibility"] == "public"


def test_second_login_does_not_duplicate(temp_db, client):
    _login(client, "alice")
    client.post("/api/auth/logout")
    _login(client, "alice")  # same human (same name+email)
    workspaces = client.get("/api/workspaces").json()
    assert len(workspaces) == 1
    topics = client.get(f"/api/workspaces/{workspaces[0]['id']}/topics").json()
    assert len(topics) == 1
