"""Real SSE round-trip: POST /api/messages must publish to broadcaster.

Regression for the v1.5b bug where post_message_endpoint was a sync def,
so FastAPI ran it in a threadpool where asyncio.get_running_loop() raised
RuntimeError and the broadcaster.publish call was silently skipped — every
real-mode SSE publish was a no-op despite the unit-level broadcaster test
passing.

We call the endpoint coroutine directly (bypassing ASGI/HTTP) and verify
that a subscriber's queue receives the published message. Going through
httpx.ASGITransport for both a streaming GET and a concurrent POST gets
deadlock-prone on Python 3.13; the direct call is what actually pins the
bug — was the publish awaited inside the async event loop or not.
"""
from __future__ import annotations

import asyncio
import secrets

import pytest


@pytest.mark.asyncio
async def test_post_message_endpoint_publishes_to_broadcaster(temp_db):
    from app.main import post_message_endpoint, MessageCreate
    from app.db import connect
    from app.identity import ensure_human
    from app.sse import broadcaster

    admin_id = ensure_human("admin")
    slug = f"sse-rt-{secrets.token_hex(4)}"
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO topics (slug, title) VALUES (?, 'SSE RT')",
            (slug,),
        )
        topic_id = cur.lastrowid

    queue = await broadcaster.subscribe(topic_id)
    try:
        payload = MessageCreate(
            topic_id=topic_id,
            type="chat",
            actor_type="human",
            actor_id=admin_id,
            body="published via async endpoint",
        )
        principal = {"human_id": admin_id, "name": "admin"}
        await post_message_endpoint(payload=payload, principal=principal)

        # Subscriber must see the published message within a tight window.
        # If the endpoint were sync def, publish would silently no-op and
        # this would hang until the timeout.
        delivered = await asyncio.wait_for(queue.get(), timeout=1.0)
    finally:
        broadcaster.unsubscribe(topic_id, queue)

    assert delivered["body"] == "published via async endpoint"
    assert delivered["topic_id"] == topic_id
    assert delivered["type"] == "chat"
