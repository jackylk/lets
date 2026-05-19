import os
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def git_artifacts_repo(monkeypatch):
    """Create a tmp git repo and point LETS_GIT_REPO at it."""
    tmp = tempfile.mkdtemp(prefix="lets-artifacts-")
    subprocess.run(["git", "init", "--quiet", tmp], check=True)
    subprocess.run(["git", "-C", tmp, "config", "user.name", "T"], check=True)
    subprocess.run(["git", "-C", tmp, "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", tmp, "commit", "--allow-empty", "-m", "init", "--quiet"], check=True)
    monkeypatch.setenv("LETS_GIT_REPO", tmp)
    yield tmp
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def auth(client):
    """Issue an admin token, return Authorization headers dict."""
    from app.auth import issue_token
    from app.identity import ensure_human
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="api-test")
    return {"Authorization": f"Bearer {tok}"}


def test_post_artifact_creates_row_and_version(client, git_artifacts_repo, auth):
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('t1','T1')")
        topic_id = cursor.lastrowid

    r = client.post(
        "/api/artifacts", headers=auth,
        json={
            "slug": "hello", "type": "text", "backend": "git",
            "title": "Hello doc", "topic_id": topic_id,
            "content_b64": "aGVsbG8gd29ybGQK",  # "hello world\n"
            "summary": "first draft",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["artifact"]["slug"] == "hello"
    assert data["version"]["version_label"] == "v0"
    assert data["version"]["backend_revision_id"]


def test_post_artifact_requires_auth(client, git_artifacts_repo):
    """Without Bearer, should 401."""
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('t2','T2')")
        topic_id = cursor.lastrowid
    r = client.post("/api/artifacts", json={
        "slug": "x", "type": "text", "backend": "git",
        "title": "X", "topic_id": topic_id,
        "content_b64": "eA==", "summary": "x",
    })
    assert r.status_code == 401


def test_update_artifact_creates_new_version(client, git_artifacts_repo, auth):
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('tu','TU')")
        topic_id = cursor.lastrowid

    create = client.post("/api/artifacts", headers=auth, json={
        "slug": "u", "type": "text", "backend": "git", "title": "U",
        "topic_id": topic_id, "content_b64": "djA=", "summary": "init",
    }).json()
    aid = create["artifact"]["id"]

    upd = client.post(f"/api/artifacts/{aid}/update", headers=auth, json={
        "content_b64": "djE=", "summary": "second pass",
        "version_label": "v1",
    })
    assert upd.status_code == 200
    data = upd.json()
    assert data["version"]["version_label"] == "v1"
    assert data["version"]["backend_revision_id"] != create["version"]["backend_revision_id"]


def test_list_artifact_versions(client, git_artifacts_repo, auth):
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('tl','TL')")
        topic_id = cursor.lastrowid

    c = client.post("/api/artifacts", headers=auth, json={
        "slug": "lv", "type": "text", "backend": "git", "title": "LV",
        "topic_id": topic_id, "content_b64": "djA=", "summary": "init",
    }).json()
    aid = c["artifact"]["id"]
    client.post(f"/api/artifacts/{aid}/update", headers=auth, json={
        "content_b64": "djE=", "summary": "two", "version_label": "v1",
    })
    client.post(f"/api/artifacts/{aid}/update", headers=auth, json={
        "content_b64": "djI=", "summary": "three", "version_label": "v2",
    })

    r = client.get(f"/api/artifacts/{aid}/versions", headers=auth)
    assert r.status_code == 200
    versions = r.json()
    labels = [v["version_label"] for v in versions]
    assert labels == ["v0", "v1", "v2"]


def test_diff_between_versions(client, git_artifacts_repo, auth):
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('td','TD')")
        topic_id = cursor.lastrowid

    c = client.post("/api/artifacts", headers=auth, json={
        "slug": "dd", "type": "text", "backend": "git", "title": "DD",
        "topic_id": topic_id, "content_b64": "YWxwaGEKYmV0YQo=",
        "summary": "init",
    }).json()
    aid = c["artifact"]["id"]
    client.post(f"/api/artifacts/{aid}/update", headers=auth, json={
        "content_b64": "YWxwaGEKR0FNTUEK",
        "summary": "edit", "version_label": "v1",
    })

    r = client.get(f"/api/artifacts/{aid}/diff?from_label=v0&to_label=v1", headers=auth)
    assert r.status_code == 200
    diff = r.json()["diff"]
    assert "-beta" in diff
    assert "+GAMMA" in diff
