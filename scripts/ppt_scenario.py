"""End-to-end PPT scenario: human briefs CC, CC drafts, Codex reviews, CC revises.

Drives two MCP HTTP clients against any Lets host (local or Railway) using
two pre-issued agent-bound Bearer tokens. The human side is simulated by
direct POSTs to /api/messages with a Bearer token of a human-only session,
because the web UI only mints those interactively via OAuth + the Agent
Tokens settings page — here we just want a typed-message stream the agents
can see.

Usage:
    LETS_HOST=https://lets.up.railway.app \
    LETS_HUMAN_TOKEN=lets_... \
    LETS_CC_TOKEN=lets_... \
    LETS_CODEX_TOKEN=lets_... \
    python scripts/ppt_scenario.py

The script prints a checklist as it goes and exits 0 on success.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from typing import Any

import httpx


def fail(msg: str) -> None:
    print(f"\x1b[31m✗ {msg}\x1b[0m", file=sys.stderr)
    sys.exit(1)


def ok(msg: str) -> None:
    print(f"\x1b[32m✓\x1b[0m {msg}")


def section(title: str) -> None:
    print(f"\n\x1b[1m── {title}\x1b[0m")


def mcp_call(client: httpx.Client, token: str, name: str, arguments: dict[str, Any]) -> Any:
    """Invoke an MCP tool via JSON-RPC over /mcp/. Returns the parsed result."""
    r = client.post(
        "/mcp/",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        },
        json={
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
        timeout=30.0,
    )
    if r.status_code != 200:
        fail(f"MCP {name} HTTP {r.status_code}: {r.text[:300]}")
    body = r.text
    if body.startswith("event:"):
        for line in body.splitlines():
            if line.startswith("data: "):
                body = line[6:]; break
    payload = json.loads(body)
    if "error" in payload:
        fail(f"MCP {name} JSON-RPC error: {payload['error']}")
    result = payload.get("result", {})
    if result.get("isError"):
        fail(f"MCP {name} tool error: {result}")
    content = result.get("content", [])
    texts = [c["text"] for c in content if c.get("type") == "text"]
    parsed: list = []
    for t in texts:
        try:
            parsed.append(json.loads(t))
        except json.JSONDecodeError:
            parsed.append(t)
    if not parsed:
        return result
    return parsed if len(parsed) > 1 else parsed[0]


def http_post(client: httpx.Client, token: str, path: str, body: dict) -> dict:
    r = client.post(
        path,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json=body,
        timeout=15.0,
    )
    if r.status_code != 200:
        fail(f"{path} HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


def http_get(client: httpx.Client, token: str, path: str) -> Any:
    r = client.get(
        path,
        headers={"Authorization": f"Bearer {token}"},
        timeout=15.0,
    )
    if r.status_code != 200:
        fail(f"GET {path} HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


PPT_V0_OUTLINE = """\
# 罗马旅游精华 5 页大纲 (v0 — CC drafted)

## 1. Hello Roma
- 时长建议: 30s
- 一句话: "永恒之城，三千年文明的露天博物馆"
- 视觉: Colosseum 黎明 / Trevi 喷泉夜景对切

## 2. 古罗马核心 (Forum + Colosseum + Palatino)
- 推荐时长: 0.5 day
- 必看: Colosseum 内部、Forum Romanum 西侧高台俯瞰
- 一句话: "脚踩两千年" — 联票 16 EUR

## 3. 梵蒂冈 (St. Peter's + Sistine Chapel)
- 推荐时长: 半天-1 天
- 必看: Michelangelo Pietà、Sistine Chapel 天顶画
- 务必预约 Vatican Museum，否则排队 2-3h

## 4. 文艺复兴 & 巴洛克步行 (Pantheon → Trevi → Piazza Navona)
- 推荐时长: 2-3h 步行
- Pantheon 免费、Trevi 投币、Piazza Navona Bernini 喷泉
- 黄昏点灯后照片最佳

## 5. 餐 + 收尾
- Trastevere 区 carbonara / supplì
- 周日 EUR 区免费博物馆 (Museo della Civiltà Romana)
- 一张交通通票 Roma Pass 72h 38.5 EUR
"""

PPT_V1_OUTLINE = """\
# 罗马旅游精华 5 页大纲 (v1 — after Codex review)

## 1. Hello Roma — 设置预期
- 时长建议: 45s (Codex: 30s 太赶，留 15s 给停顿)
- 一句话: "永恒之城——三千年的露天博物馆，但只给我们 3 天"
- 视觉: Colosseum 黎明 + Trevi 夜景对切；底部叠加行程总览图

## 2. Day 1: 古罗马核心
- Colosseum + Forum + Palatino 联票 (16 EUR, 提前 7 天网订)
- 推荐入场: 9:00 a.m.；Colosseum 地下 + 上层需另外预约
- Codex 提醒: 周一 Forum 早闭，安排在周二或周四最佳

## 3. Day 2: 梵蒂冈整天
- St. Peter's Basilica + Vatican Museums + Sistine Chapel
- 必预约 Vatican Museum，开 7:00 Open Door 票（贵 5 EUR 省 2h）
- Sistine Chapel 禁拍照，留 30 min 给广角脖子

## 4. Day 3 上午: 文艺复兴 + 巴洛克步行
- Pantheon → Trevi → Piazza Navona → Campo de' Fiori
- Pantheon 免费但需预约 (新规, 2025+); Trevi 投币背向；Bernini 4 河喷泉
- 黄昏点灯前 30 min 抵达 Piazza Navona 拍光线

## 5. Day 3 下午 + 收尾: 餐 + 后路
- Trastevere 区 carbonara / supplì / Da Enzo al 29 必排队
- Roma Pass 72h 53 EUR (Codex: 价格更新，原稿 38.5 是旧价)
- 离开前 2h 提前到 Termini，行李寄存 6 EUR / 4h
- 周日免费博物馆窗口仅每月第一个周日 (Codex 校正)
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default=os.environ.get("LETS_HOST", "http://127.0.0.1:8000"))
    parser.add_argument("--human-token", default=os.environ.get("LETS_HUMAN_TOKEN"))
    parser.add_argument("--cc-token", default=os.environ.get("LETS_CC_TOKEN"))
    parser.add_argument("--codex-token", default=os.environ.get("LETS_CODEX_TOKEN"))
    parser.add_argument("--human-id", type=int, default=int(os.environ.get("LETS_HUMAN_ID", "0") or "0"))
    args = parser.parse_args()

    for name, val in [
        ("--host", args.host),
        ("--human-token (LETS_HUMAN_TOKEN)", args.human_token),
        ("--cc-token (LETS_CC_TOKEN)", args.cc_token),
        ("--codex-token (LETS_CODEX_TOKEN)", args.codex_token),
    ]:
        if not val:
            fail(f"missing {name}")

    base = args.host.rstrip("/")
    client = httpx.Client(base_url=base, trust_env=False)

    # --- 0. Agents introduce themselves
    section("0. Agents introduce themselves")
    cc_self = mcp_call(client, args.cc_token, "whoami", {})
    print("   CC:   ", cc_self)
    if cc_self.get("agent_instance_id") is None:
        fail("CC token is not bound to an agent_instance")
    codex_self = mcp_call(client, args.codex_token, "whoami", {})
    print("   Codex:", codex_self)
    if codex_self.get("agent_instance_id") is None:
        fail("Codex token is not bound to an agent_instance")
    ok("both agents identified themselves via MCP whoami")

    # --- 1. Human creates a project + topic
    section("1. Human creates project + topic")
    if args.human_id == 0:
        # Derive from human token via /api/agents/online or by reading what CC sees
        # Easiest: post a finding via Bearer token-protected /api/tokens? That needs session.
        # Fallback: assume human_id == cc_self.human_id (same person owns both tokens).
        args.human_id = cc_self["human_id"]
        print(f"   (derived human_id={args.human_id} from CC token)")

    proj_slug = f"rome-trip-{int(time.time())}"
    proj = http_post(client, args.human_token, "/api/projects", {
        "name": "Rome Trip PPT", "slug": proj_slug,
        "description": "5-page PPT introducing top Rome sights",
    })
    project_id = proj["id"]
    ok(f"project created: id={project_id} slug={proj['slug']}")

    topic_slug = f"v0-outline-{int(time.time())}"
    topic = http_post(client, args.human_token, f"/api/projects/{project_id}/topics", {
        "slug": topic_slug, "title": "Rome PPT v0 outline",
    })
    topic_id = topic["id"]
    ok(f"topic created: id={topic_id} slug={topic['slug']}")

    # --- 2. Human briefs the agents
    section("2. Human posts brief, @CC for drafting, @Codex for later review")
    cc_human = cc_self["human_id"]
    codex_human = codex_self["human_id"]
    cc_aid = cc_self["agent_instance_id"]
    codex_aid = codex_self["agent_instance_id"]

    brief = http_post(client, args.human_token, "/api/messages", {
        "topic_id": topic_id, "type": "chat", "actor_type": "human",
        "actor_id": args.human_id,
        "body": "@cc 帮我做一个 5 页 PPT 大纲：介绍罗马旅游精华景点，受众是 3-天首次访问的游客。等 v0 出来后 @codex 帮忙评审一下细节准确性。",
        "metadata": {"goal": "5-page Rome travel PPT"},
        "addressed_to": str(cc_human),
    })
    ok(f"human briefed: message id={brief['id']}")

    # --- 3. CC reads the brief
    section("3. CC reads the brief via read_topic")
    seen = mcp_call(client, args.cc_token, "read_topic", {"topic_id": topic_id})
    if not isinstance(seen, list):
        seen = [seen]
    found = next((m for m in seen if "罗马" in m.get("body", "") or "Rome" in m.get("body", "")), None)
    if not found:
        fail(f"CC didn't see the brief; got {seen}")
    ok(f"CC sees brief (msg id={found['id']})")

    # CC posts status: "got it, drafting"
    mcp_call(client, args.cc_token, "post_typed_message", {
        "topic_id": topic_id, "type": "status",
        "body": "active · 正在起草 v0 5 页大纲 · 预计 30s",
        "metadata": {"agent_status": "active"},
    })
    ok("CC posted status 'active · drafting v0'")

    # --- 4. CC creates v0 artifact + announces it
    section("4. CC creates v0 artifact and announces via artifact_revision")
    v0 = mcp_call(client, args.cc_token, "create_artifact", {
        "topic_id": topic_id,
        "slug": f"rome-ppt-{int(time.time())}",
        "type": "outline",
        "title": "Rome Trip PPT — v0 draft",
        "content_b64": base64.b64encode(PPT_V0_OUTLINE.encode("utf-8")).decode("ascii"),
        "summary": "Initial 5-page outline by CC",
    })
    artifact_id = v0["artifact"]["id"]
    ok(f"v0 artifact created: id={artifact_id} ({v0['version']['version_label']}) sha={v0['version']['backend_revision_id'][:8]}")

    mcp_call(client, args.cc_token, "post_typed_message", {
        "topic_id": topic_id, "type": "artifact_revision",
        "body": "v0 出来了 · 5 页骨架已落地 · @codex 麻烦评审",
        "metadata": {"artifact_id": artifact_id, "version": "v0"},
        "addressed_to": str(codex_human),
    })
    ok("CC posted artifact_revision pinging Codex")

    # --- 5. Codex sees the @mention in attention
    section("5. Codex reads the topic and reviews the v0")
    codex_seen = mcp_call(client, args.codex_token, "read_topic", {"topic_id": topic_id})
    if not isinstance(codex_seen, list):
        codex_seen = [codex_seen]
    rev_msgs = [m for m in codex_seen if m.get("type") == "artifact_revision"]
    if not rev_msgs:
        fail(f"Codex didn't see artifact_revision; got {codex_seen}")
    ok(f"Codex sees {len(rev_msgs)} artifact_revision message(s)")

    # Codex posts a review with concrete corrections
    mcp_call(client, args.codex_token, "post_typed_message", {
        "topic_id": topic_id, "type": "review",
        "body": (
            "v0 评审:\n"
            "1. 第 1 页 30s 太赶，建议 45s 给设置预期留空间。\n"
            "2. Pantheon 2025+ 起需要预约（免费但要 booking），原稿没提。\n"
            "3. Roma Pass 72h 价格已涨到 53 EUR，原稿 38.5 是旧价。\n"
            "4. 周日免费博物馆窗口仅每月第一个周日（原稿模糊）。\n"
            "5. 建议按 Day 1/2/3 重新组织页面骨架，对应游客 3 天行程。"
        ),
        "metadata": {"artifact_id": artifact_id, "review_target_version": "v0"},
        "addressed_to": str(cc_human),
    })
    ok("Codex posted detailed review")

    # --- 6. CC reads review, produces v1
    section("6. CC reads Codex review and ships v1")
    after = mcp_call(client, args.cc_token, "read_topic", {
        "topic_id": topic_id, "after_id": found["id"],
    })
    if not isinstance(after, list):
        after = [after]
    reviews = [m for m in after if m.get("type") == "review"]
    if not reviews:
        fail(f"CC didn't see Codex review; got {after}")
    ok(f"CC reads {len(reviews)} review message(s)")

    v1 = mcp_call(client, args.cc_token, "update_artifact", {
        "artifact_id": artifact_id,
        "version_label": "v1",
        "content_b64": base64.b64encode(PPT_V1_OUTLINE.encode("utf-8")).decode("ascii"),
        "summary": "Apply Codex's 5 corrections + restructure as Day 1/2/3",
    })
    ok(f"v1 shipped: {v1['version']['version_label']} sha={v1['version']['backend_revision_id'][:8]}")

    mcp_call(client, args.cc_token, "post_typed_message", {
        "topic_id": topic_id, "type": "finding",
        "body": "完工 · v1 已应用 Codex 的全部 5 条修正 · 已重构为 Day 1/2/3 骨架",
        "metadata": {"artifact_id": artifact_id, "version": "v1"},
        "addressed_to": str(args.human_id),
    })
    ok("CC posted finding announcing completion")

    # --- 7. Verification
    section("7. Verification")
    stream = http_get(client, args.human_token, f"/api/topics/{topic_id}/messages")
    types = [m["type"] for m in stream]
    print(f"   topic stream types: {types}")
    expected = ["chat", "status", "artifact_revision", "review", "finding"]
    for t in expected:
        if t not in types:
            fail(f"missing message type in topic stream: {t}")
    ok(f"topic stream contains all expected types: {expected}")

    versions = http_get(client, args.human_token, f"/api/artifacts/{artifact_id}/versions")
    labels = [v["version_label"] for v in versions]
    print(f"   artifact versions: {labels}")
    if "v0" not in labels or "v1" not in labels:
        fail(f"missing v0 or v1 in artifact versions: {labels}")
    ok("artifact has v0 + v1")

    # Attention queue for CC should have included Codex's review at one point
    cc_att = http_get(client, args.human_token, f"/api/attention?human_id={cc_human}")
    print(f"   CC attention needs_decision count: {len(cc_att['needs_decision'])}")
    # Not strictly required (since review isn't in needs_decision types), but useful info.

    # Final v1 content
    final = http_get(client, args.human_token, f"/api/artifacts/{artifact_id}?version_label=v1")
    print(f"   final v1 backend_ref: {final.get('artifact', final).get('backend_ref')}")

    section("✓ PPT scenario PASSED")
    print(f"  project: {base}/app/  (slug={proj_slug})")
    print(f"  topic_id={topic_id}, artifact_id={artifact_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
