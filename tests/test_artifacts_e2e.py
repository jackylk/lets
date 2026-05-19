import base64
import subprocess
import tempfile

import pytest


@pytest.fixture
def git_artifacts_repo(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="lets-artifacts-e2e-")
    subprocess.run(["git", "init", "--quiet", tmp], check=True)
    subprocess.run(["git", "-C", tmp, "config", "user.name", "T"], check=True)
    subprocess.run(["git", "-C", tmp, "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", tmp, "commit", "--allow-empty", "-m", "init", "--quiet"], check=True)
    monkeypatch.setenv("LETS_GIT_REPO", tmp)
    yield tmp
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


def test_full_artifact_lifecycle(client, git_artifacts_repo):
    """Simulates a PPT-like scenario: create v0 → update v1 → update v2 → list → diff → read."""
    from app.auth import issue_token
    from app.identity import ensure_human
    admin_hid = ensure_human("admin")
    admin_tok, _ = issue_token(human_id=admin_hid, label="artifact-e2e")
    auth = {"Authorization": f"Bearer {admin_tok}"}

    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('e2e','PPT Topic')")
        topic_id = cursor.lastrowid

    r = client.post("/api/artifacts", headers=auth, json={
        "slug": "q3-ppt", "type": "pptx", "backend": "git",
        "title": "Q3 Review PPT", "topic_id": topic_id,
        "content_b64": base64.b64encode(b"slide1: Q3 numbers\n").decode(),
        "summary": "Neo: 8-page skeleton",
    })
    assert r.status_code == 200
    art_id = r.json()["artifact"]["id"]

    client.post(f"/api/artifacts/{art_id}/update", headers=auth, json={
        "content_b64": base64.b64encode(b"slide1: Q3 numbers\nslide4: matrix 4x6\n").decode(),
        "summary": "claude: P4 matrix",
        "version_label": "v1",
    })

    client.post(f"/api/artifacts/{art_id}/update", headers=auth, json={
        "content_b64": base64.b64encode(b"slide1: Q3 highlights\nslide4: matrix 4x6\n").decode(),
        "summary": "trinity: tighten P1",
        "version_label": "v2",
    })

    versions = client.get(f"/api/artifacts/{art_id}/versions", headers=auth).json()
    labels = [v["version_label"] for v in versions]
    assert labels == ["v0", "v1", "v2"]

    diff = client.get(f"/api/artifacts/{art_id}/diff?from_label=v0&to_label=v2", headers=auth).json()
    assert "highlights" in diff["diff"]
    assert "matrix" in diff["diff"]

    current = client.get(f"/api/artifacts/{art_id}", headers=auth).json()
    assert base64.b64decode(current["content_b64"]) == b"slide1: Q3 highlights\nslide4: matrix 4x6\n"
    assert current["current_version_label"] == "v2"
