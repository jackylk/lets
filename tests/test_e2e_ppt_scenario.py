"""End-to-end integration test for Track A.

Stitches together identity / events / messages / topics through HTTP to verify
the substrate is sufficient for v1.5 stream semantics, using a fragment of the
PPT collaboration scenario from the mock.
"""
from __future__ import annotations


def test_ppt_scenario_end_to_end(client):
    from app.auth import issue_token
    from app.identity import ensure_human

    admin_human_id = ensure_human("admin")
    admin_token, _ = issue_token(human_id=admin_human_id, label="e2e-test")
    auth = {"Authorization": f"Bearer {admin_token}"}

    # 1. Set up Neo, Trinity identities
    neo = client.get("/api/identity/me", headers={"X-Lets-Human": "Neo"}).json()
    trinity = client.get("/api/identity/me", headers={"X-Lets-Human": "Trinity"}).json()
    assert neo["human"]["name"] == "Neo"
    assert trinity["human"]["name"] == "Trinity"

    # 2. Set up claude on Neo's MBP
    cc_neo = client.get(
        "/api/identity/me",
        headers={
            "X-Lets-Human": "Neo",
            "X-Lets-Agent-Role": "claude",
            "X-Lets-Device": "neo-mbp",
        },
    ).json()
    assert cc_neo["agent_instance"]["device_label"] == "neo-mbp"
    assert cc_neo["agent_instance"]["role"] == "claude"

    # 3. Create a topic
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute(
            "INSERT INTO topics (slug, title) VALUES ('t-ppt', '为 Agent 记忆写一个研讨 PPT')"
        )
        topic_id = cursor.lastrowid

    # 4. Neo chats
    client.post(
        "/api/messages",
        headers=auth,
        json={
            "topic_id": topic_id, "type": "chat",
            "actor_type": "human", "actor_id": neo["human"]["id"],
            "body": "下周三研讨会，30min agent 记忆",
        },
    )

    # 5. Claude posts status
    client.post(
        "/api/messages",
        headers=auth,
        json={
            "topic_id": topic_id, "type": "status",
            "actor_type": "agent", "actor_id": cc_neo["agent_instance"]["id"],
            "body": "active · 读 docs · 10 min 出 v0",
            "metadata": {"agent_status": "active"},
        },
    )

    # 6. Claude posts artifact_revision
    client.post(
        "/api/messages",
        headers=auth,
        json={
            "topic_id": topic_id, "type": "artifact_revision",
            "actor_type": "agent", "actor_id": cc_neo["agent_instance"]["id"],
            "body": "v0: 8 页骨架",
            "metadata": {"artifact_name": "ai-memory-talk.pptx", "version": "v0"},
        },
    )

    # 7. Claude proposes spec_change
    client.post(
        "/api/messages",
        headers=auth,
        json={
            "topic_id": topic_id, "type": "spec_change",
            "actor_type": "agent", "actor_id": cc_neo["agent_instance"]["id"],
            "body": "改 research-talk-style skill 字号 10 → 14",
            "metadata": {
                "file": ".claude/skills/research-talk-style/SKILL.md",
                "before": 10,
                "after": 14,
            },
        },
    )

    # 8. Neo decides
    client.post(
        "/api/messages",
        headers=auth,
        json={
            "topic_id": topic_id, "type": "decision",
            "actor_type": "human", "actor_id": neo["human"]["id"],
            "body": "approve spec change v2 → v3",
            "metadata": {"decision_type": "adopt"},
        },
    )

    # 9. Pull full stream and verify ordering + types
    stream = client.get(f"/api/topics/{topic_id}/messages", headers=auth).json()
    types = [m["type"] for m in stream]
    assert types == ["chat", "status", "artifact_revision", "spec_change", "decision"]

    # 10. Verify type filter
    only_arts = client.get(
        f"/api/topics/{topic_id}/messages?type=artifact_revision",
        headers=auth,
    ).json()
    assert len(only_arts) == 1
    assert only_arts[0]["metadata"]["version"] == "v0"
