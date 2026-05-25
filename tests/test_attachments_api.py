from __future__ import annotations

import hashlib

import pytest


@pytest.fixture
def auth(client):
    from app.auth import issue_token
    from app.identity import ensure_human

    hid = ensure_human("attachments-admin")
    tok, _ = issue_token(human_id=hid, label="attachments-test")
    return {"Authorization": f"Bearer {tok}"}


def _topic_id() -> int:
    from app.db import connect

    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('attachments-t', 'Attachments')")
        return int(cur.lastrowid)


def test_upload_attachment_stores_file_on_volume(client, auth, tmp_path, monkeypatch):
    monkeypatch.setenv("LETS_UPLOAD_DIR", str(tmp_path))
    topic_id = _topic_id()
    body = b"hello from a shared file\n"

    res = client.post(
        f"/api/topics/{topic_id}/attachments?filename=notes.txt",
        headers={**auth, "content-type": "text/plain"},
        content=body,
    )

    assert res.status_code == 200, res.text
    data = res.json()
    assert data["kind"] == "file"
    assert data["filename"] == "notes.txt"
    assert data["mime_type"] == "text/plain"
    assert data["byte_size"] == len(body)
    assert data["sha256"] == hashlib.sha256(body).hexdigest()
    assert data["storage_backend"] == "local_volume"
    stored = tmp_path / data["storage_key"]
    assert stored.read_bytes() == body


def test_list_and_download_attachment(client, auth, tmp_path, monkeypatch):
    monkeypatch.setenv("LETS_UPLOAD_DIR", str(tmp_path))
    topic_id = _topic_id()
    body = b"\x89PNG\r\nshared image"

    upload = client.post(
        f"/api/topics/{topic_id}/attachments?filename=screen.png",
        headers={**auth, "content-type": "image/png"},
        content=body,
    )
    assert upload.status_code == 200, upload.text
    attachment = upload.json()

    listed = client.get(f"/api/topics/{topic_id}/attachments", headers=auth)
    assert listed.status_code == 200
    rows = listed.json()
    assert [r["id"] for r in rows] == [attachment["id"]]
    assert rows[0]["kind"] == "image"
    assert rows[0]["download_url"] == f"/api/attachments/{attachment['id']}/download"

    downloaded = client.get(rows[0]["download_url"], headers=auth)
    assert downloaded.status_code == 200
    assert downloaded.content == body
    assert downloaded.headers["content-type"].startswith("image/png")


def test_attachment_upload_requires_auth(client, tmp_path, monkeypatch):
    monkeypatch.setenv("LETS_UPLOAD_DIR", str(tmp_path))
    topic_id = _topic_id()

    res = client.post(
        f"/api/topics/{topic_id}/attachments?filename=x.txt",
        headers={"content-type": "text/plain"},
        content=b"x",
    )

    assert res.status_code == 401


def test_attachment_upload_rejects_oversized_body(client, auth, tmp_path, monkeypatch):
    monkeypatch.setenv("LETS_UPLOAD_DIR", str(tmp_path))
    monkeypatch.setenv("LETS_MAX_ATTACHMENT_BYTES", "3")
    topic_id = _topic_id()

    res = client.post(
        f"/api/topics/{topic_id}/attachments?filename=x.txt",
        headers={**auth, "content-type": "text/plain"},
        content=b"too large",
    )

    assert res.status_code == 413
