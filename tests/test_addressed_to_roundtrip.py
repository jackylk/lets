"""End-to-end: addressed_to must round-trip through POST /api/messages
and feed the attention queue. Regression for the v1.5b smoke-test gap
where MessageCreate silently dropped the field."""
from __future__ import annotations

import pytest


@pytest.fixture
def auth(client):
    from app.auth import issue_token
    from app.identity import ensure_human
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="addr-test")
    return {"Authorization": f"Bearer {tok}"}


def test_addressed_to_survives_post(client, auth):
    """POST /api/messages with addressed_to should persist it."""
    from app.identity import ensure_human
    from app.db import connect

    neo = ensure_human("Neo")
    trinity = ensure_human("Trinity")
    with connect() as conn:
        c = conn.execute("INSERT INTO topics (slug, title) VALUES ('addr-t1', 'A1')")
        topic_id = c.lastrowid

    r = client.post("/api/messages", headers=auth, json={
        "topic_id": topic_id,
        "type": "question",
        "actor_type": "human",
        "actor_id": neo,
        "body": "neo asks trinity",
        "addressed_to": str(trinity),
        "metadata": {},
    })
    assert r.status_code == 200, r.text
    assert r.json()["addressed_to"] == str(trinity)


def test_addressed_to_feeds_attention(client, auth):
    """addressed_to roundtrip lands the message in the addressee's attention queue."""
    from app.identity import ensure_human
    from app.db import connect

    neo = ensure_human("Neo")
    trinity = ensure_human("Trinity")
    with connect() as conn:
        c = conn.execute("INSERT INTO topics (slug, title) VALUES ('addr-t2', 'A2')")
        topic_id = c.lastrowid

    client.post("/api/messages", headers=auth, json={
        "topic_id": topic_id,
        "type": "question",
        "actor_type": "human",
        "actor_id": neo,
        "body": "for trinity only",
        "addressed_to": str(trinity),
        "metadata": {},
    })

    att = client.get(f"/api/attention?human_id={trinity}", headers=auth).json()
    assert len(att["needs_decision"]) == 1
    assert att["needs_decision"][0]["body"] == "for trinity only"


def test_addressed_to_csv_multiple_humans(client, auth):
    """CSV of multiple IDs: each addressee sees it in their queue."""
    from app.identity import ensure_human
    from app.db import connect

    neo = ensure_human("Neo")
    trinity = ensure_human("Trinity")
    morpheus = ensure_human("Morpheus")
    with connect() as conn:
        c = conn.execute("INSERT INTO topics (slug, title) VALUES ('addr-t3', 'A3')")
        topic_id = c.lastrowid

    client.post("/api/messages", headers=auth, json={
        "topic_id": topic_id,
        "type": "question",
        "actor_type": "human",
        "actor_id": neo,
        "body": "@trinity @morpheus thoughts?",
        "addressed_to": f"{trinity},{morpheus}",
        "metadata": {},
    })

    for hid in (trinity, morpheus):
        att = client.get(f"/api/attention?human_id={hid}", headers=auth).json()
        assert any(m["body"] == "@trinity @morpheus thoughts?" for m in att["needs_decision"]), \
            f"human_id={hid} didn't see it: {att}"
