"""When a human posts a chat with no addressed_to and they own exactly
one currently-online agent, the server fills in addressed_to so the
gateway picks the message up — no need to type @cc every turn.

With 0 or 2+ online agents we leave it null (force explicit @)."""
from __future__ import annotations

import pytest


@pytest.fixture
def auth(client):
    from app.auth import issue_token
    from app.identity import ensure_human
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="auto-addr-test")
    return {"Authorization": f"Bearer {tok}"}


def _make_topic(slug: str) -> int:
    from app.db import connect
    with connect() as conn:
        c = conn.execute(f"INSERT INTO topics (slug, title) VALUES ('{slug}', 't')")
        return int(c.lastrowid)


def _mark_token_online(token_id: int) -> None:
    from app.db import connect
    with connect() as conn:
        conn.execute(
            "UPDATE tokens SET last_used_at = datetime('now') WHERE id = ?",
            (token_id,),
        )


def test_single_online_agent_auto_addresses_owner(client, auth):
    """One online agent → human's chat is auto-addressed to the agent id."""
    from app.auth import issue_token
    from app.identity import ensure_human, ensure_agent_instance

    jacky = ensure_human("Jacky-auto1")
    cc = ensure_agent_instance(role="claude", human_id=jacky, device_label="mac")
    _, tok_id = issue_token(human_id=jacky, agent_instance_id=cc, label="cc")
    _mark_token_online(tok_id)

    tid = _make_topic("auto-1")
    r = client.post("/api/messages", headers=auth, json={
        "topic_id": tid,
        "type": "chat",
        "actor_type": "human",
        "actor_id": jacky,
        "body": "hi",  # no @
    })
    assert r.status_code == 200, r.text
    assert r.json()["addressed_to"] == f"agent:{cc}"


def test_two_online_agents_does_not_auto_address(client, auth):
    """Two online agents → ambiguous, leave addressed_to null."""
    from app.auth import issue_token
    from app.identity import ensure_human, ensure_agent_instance

    jacky = ensure_human("Jacky-auto2")
    cc = ensure_agent_instance(role="claude", human_id=jacky, device_label="mac")
    cx = ensure_agent_instance(role="codex", human_id=jacky, device_label="mac")
    _, t1 = issue_token(human_id=jacky, agent_instance_id=cc, label="cc")
    _, t2 = issue_token(human_id=jacky, agent_instance_id=cx, label="cx")
    _mark_token_online(t1)
    _mark_token_online(t2)

    tid = _make_topic("auto-2")
    r = client.post("/api/messages", headers=auth, json={
        "topic_id": tid,
        "type": "chat",
        "actor_type": "human",
        "actor_id": jacky,
        "body": "hi",
    })
    assert r.status_code == 200, r.text
    assert r.json()["addressed_to"] is None


def test_no_online_agents_does_not_auto_address(client, auth):
    """Zero online agents → leave addressed_to null (no one to wake)."""
    from app.identity import ensure_human, ensure_agent_instance

    jacky = ensure_human("Jacky-auto3")
    ensure_agent_instance(role="claude", human_id=jacky, device_label="mac")
    # Note: no _mark_token_online → agent is registered but offline.

    tid = _make_topic("auto-3")
    r = client.post("/api/messages", headers=auth, json={
        "topic_id": tid,
        "type": "chat",
        "actor_type": "human",
        "actor_id": jacky,
        "body": "hi",
    })
    assert r.status_code == 200, r.text
    assert r.json()["addressed_to"] is None


def test_explicit_addressed_to_is_respected(client, auth):
    """If the human DID provide addressed_to, don't overwrite it."""
    from app.auth import issue_token
    from app.identity import ensure_human, ensure_agent_instance

    jacky = ensure_human("Jacky-auto4")
    other = ensure_human("Other-auto4")
    cc = ensure_agent_instance(role="claude", human_id=jacky, device_label="mac")
    _, tok_id = issue_token(human_id=jacky, agent_instance_id=cc, label="cc")
    _mark_token_online(tok_id)

    tid = _make_topic("auto-4")
    r = client.post("/api/messages", headers=auth, json={
        "topic_id": tid,
        "type": "chat",
        "actor_type": "human",
        "actor_id": jacky,
        "body": "@other hi",
        "addressed_to": str(other),
    })
    assert r.status_code == 200, r.text
    assert r.json()["addressed_to"] == str(other)


def test_first_chat_renames_topic_from_generic_default(client, auth):
    """When a topic still has its auto-created '主频道' title and a human
    posts the first chat, the title gets replaced with a snippet of the
    message body so the sidebar isn't a sea of identical '主频道' rows."""
    from app.identity import ensure_human
    from app.db import connect

    jacky = ensure_human("Jacky-rename")
    with connect() as conn:
        c = conn.execute(
            "INSERT INTO topics (slug, title) VALUES ('rename-1', '主频道')"
        )
        topic_id = c.lastrowid

    r = client.post("/api/messages", headers=auth, json={
        "topic_id": topic_id,
        "type": "chat",
        "actor_type": "human",
        "actor_id": jacky,
        "body": "@cc 你能写一个关于罗马的 PPT 吗",
    })
    assert r.status_code == 200, r.text

    with connect() as conn:
        title = conn.execute(
            "SELECT title FROM topics WHERE id = ?", (topic_id,)
        ).fetchone()["title"]
    assert "罗马" in title
    # The leading @mention should be stripped.
    assert not title.startswith("@")


def test_real_title_is_not_overwritten(client, auth):
    """If the user already named the topic, subsequent chats leave it
    alone — only generic names get auto-renamed."""
    from app.identity import ensure_human
    from app.db import connect

    jacky = ensure_human("Jacky-rename2")
    with connect() as conn:
        c = conn.execute(
            "INSERT INTO topics (slug, title) VALUES ('rename-2', 'Q3 review')"
        )
        topic_id = c.lastrowid

    r = client.post("/api/messages", headers=auth, json={
        "topic_id": topic_id,
        "type": "chat",
        "actor_type": "human",
        "actor_id": jacky,
        "body": "let's get started",
    })
    assert r.status_code == 200

    with connect() as conn:
        title = conn.execute(
            "SELECT title FROM topics WHERE id = ?", (topic_id,)
        ).fetchone()["title"]
    assert title == "Q3 review"
