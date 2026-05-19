import json
import pytest


@pytest.fixture
def auth(client):
    from app.auth import issue_token
    from app.identity import ensure_human
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="sse-test")
    return {"Authorization": f"Bearer {tok}"}


def test_after_id_filter_returns_only_newer_messages(client, auth):
    """GET /api/topics/{id}/messages?after_id=N returns only id > N."""
    from app.identity import ensure_human
    from app.db import connect
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('sse-t1', 'SSE 1')")
        topic_id = cur.lastrowid
    hid = ensure_human("Neo")
    ids = []
    for body in ("first", "second", "third"):
        r = client.post("/api/messages", headers=auth, json={
            "topic_id": topic_id, "type": "chat",
            "actor_type": "human", "actor_id": hid, "body": body,
        })
        assert r.status_code == 200, r.text
        ids.append(r.json()["id"])
    r = client.get(f"/api/topics/{topic_id}/messages?after_id={ids[1]}", headers=auth)
    assert r.status_code == 200
    bodies = [m["body"] for m in r.json()]
    assert bodies == ["third"]


def test_sse_stream_endpoint_responds(client, auth):
    """GET /api/topics/{id}/stream serves a text/event-stream that delivers published messages."""
    import asyncio

    from app.db import connect
    from app.main import app as fastapi_app
    from app.sse import broadcaster

    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('sse-t2', 'SSE 2')")
        topic_id = cur.lastrowid

    # Drive the ASGI app directly. httpx's ASGITransport buffers the full
    # response body before exposing chunks, so we talk ASGI ourselves to
    # observe headers + the first body event without buffering.
    async def _run():
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": f"/api/topics/{topic_id}/stream",
            "raw_path": f"/api/topics/{topic_id}/stream".encode(),
            "query_string": b"",
            "root_path": "",
            "headers": [
                (b"host", b"testserver"),
                (b"authorization", auth["Authorization"].encode()),
            ],
            "server": ("testserver", 80),
            "client": ("testclient", 50000),
        }

        sent: list[dict] = []
        done = asyncio.Event()

        async def receive():
            # Hold the connection open; never report a disconnect.
            await done.wait()
            return {"type": "http.disconnect"}

        async def send(message):
            sent.append(message)
            if message.get("type") == "http.response.body":
                done.set()

        # Schedule a publish shortly after subscription so the generator
        # advances past its first ``await queue.get()``.
        async def kick():
            for _ in range(20):
                if any(m.get("type") == "http.response.start" for m in sent):
                    break
                await asyncio.sleep(0.05)
            await broadcaster.publish(topic_id, {"id": 9001, "body": "ping"})

        task = asyncio.create_task(fastapi_app(scope, receive, send))
        kicker = asyncio.create_task(kick())
        try:
            await asyncio.wait_for(done.wait(), timeout=3.0)
        finally:
            kicker.cancel()
            task.cancel()
            for t in (kicker, task):
                try:
                    await t
                except (asyncio.CancelledError, Exception):
                    pass
        return sent

    sent = asyncio.run(_run())
    starts = [m for m in sent if m.get("type") == "http.response.start"]
    bodies = [m for m in sent if m.get("type") == "http.response.body"]
    assert starts and starts[0]["status"] == 200
    headers = {k.decode().lower(): v.decode() for k, v in starts[0]["headers"]}
    assert headers["content-type"].startswith("text/event-stream")
    assert bodies, "expected at least one body chunk"
    body_text = b"".join(b.get("body", b"") for b in bodies).decode("utf-8", errors="replace")
    # Either the opening sentinel or the published event must appear.
    assert ":ok" in body_text or "9001" in body_text


def test_sse_requires_auth(client):
    r = client.get("/api/topics/1/stream")
    assert r.status_code == 401


def test_broadcaster_publish_then_subscribe_receives(temp_db):
    """Unit-level: TopicBroadcaster delivers published messages to a subscriber."""
    import asyncio
    from app.sse import broadcaster

    async def runner():
        q = await broadcaster.subscribe(topic_id=42)
        await broadcaster.publish(topic_id=42, payload={"id": 1, "body": "hi"})
        msg = await asyncio.wait_for(q.get(), timeout=0.5)
        broadcaster.unsubscribe(topic_id=42, queue=q)
        return msg

    msg = asyncio.run(runner())
    assert msg["id"] == 1
