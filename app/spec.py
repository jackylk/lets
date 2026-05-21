"""Pure projection from a topic's typed-message stream to a handoff spec.

Lives in its own module so both the CLI (`lets spec`) and the HTTP API
(`GET /api/topics/{id}/spec`) project the same way. No DB, no I/O — just
a list of message dicts in, markdown string out.
"""
from __future__ import annotations

import re


def render_spec_markdown(topic_id: int, msgs: list[dict]) -> str:
    """Project ``msgs`` into a handoff-quality markdown spec.

    Reads each ``discussion_kind`` off ``message.metadata`` and groups them
    into spec sections. Each item carries a ``[#msg-id]`` citation so a
    downstream agent (or user) can jump back into the discussion for
    context. Items are sorted by aggregate ±1 score (high → low, latest
    vote per actor wins) so human-curated priorities rise to the top of
    each section.
    """
    by_kind: dict[str, list[dict]] = {
        k: [] for k in
        ("decision", "option", "constraint", "open_question",
         "blind_spot", "critique", "extension")
    }
    diagrams: list[tuple[int, str]] = []
    links: list[tuple[int, str]] = []
    goal_msgs: list[dict] = []
    chats: list[dict] = []
    resolved_q_ids: set[int] = set()

    # Aggregate ±1 scores: latest vote per (actor, target) wins.
    latest_vote: dict[tuple[int, int], int] = {}
    for m in msgs:
        if m.get("type") != "annotation":
            continue
        meta = m.get("metadata") or {}
        tgt = meta.get("target_message_id")
        sc = meta.get("score")
        actor = m.get("actor_id")
        if isinstance(tgt, int) and isinstance(sc, int) and isinstance(actor, int):
            latest_vote[(actor, tgt)] = sc
    score_by_msg: dict[int, int] = {}
    for (_, tgt), s in latest_vote.items():
        score_by_msg[tgt] = score_by_msg.get(tgt, 0) + s

    for m in msgs:
        meta = m.get("metadata") or {}
        kind = meta.get("discussion_kind")
        if kind in by_kind:
            by_kind[kind].append(m)
        if kind == "decision" and isinstance(meta.get("resolves_question"), int):
            resolved_q_ids.add(int(meta["resolves_question"]))
        if m.get("type") == "chat":
            chats.append(m)
        if m.get("type") == "goal_proposed" or meta.get("kind") == "goal":
            goal_msgs.append(m)
        body = m.get("body") or ""
        for mm in re.finditer(r"```mermaid\s+([\s\S]*?)```", body):
            diagrams.append((int(m["id"]), mm.group(1).strip()))
        for u in re.finditer(r"https?://[^\s)>'\"]+", body):
            links.append((int(m["id"]), u.group(0)))

    title_msgs = [m for m in msgs if m.get("type") == "topic_renamed"]
    topic_title: str | None = None
    if title_msgs:
        topic_title = (title_msgs[-1].get("body") or "").strip() or None

    def _fmt_item(m: dict) -> str:
        body = (m.get("body") or "").strip().replace("\n", " ")
        mid = int(m["id"])
        score = score_by_msg.get(mid, 0)
        cite = f" [#{mid}]"
        score_tag = ""
        if score > 0:
            score_tag = f" `+{score}`"
        elif score < 0:
            score_tag = f" `{score}`"
        return f"- {body}{score_tag}{cite}"

    def section(name: str, items: list[dict]) -> str:
        if not items:
            return ""
        ranked = sorted(
            items,
            key=lambda m: (-score_by_msg.get(int(m["id"]), 0), int(m["id"])),
        )
        out = [f"## {name}\n"]
        for m in ranked:
            out.append(_fmt_item(m))
        return "\n".join(out) + "\n\n"

    parts: list[str] = []
    parts.append(
        f"# Topic #{topic_id}"
        + (f" — {topic_title}" if topic_title else "")
        + "\n\n"
    )
    parts.append(
        "> 这份 spec 由 `lets spec` 从黑板自动凝结，喂给开发 agent 即可独立动手。\n"
        "> 失效或不明确处通常意味着讨论阶段还没穷尽——回到原 topic 补充即可。\n\n"
    )

    if goal_msgs:
        parts.append("## 设计目标\n")
        for g in goal_msgs[-3:]:
            parts.append(f"- {(g.get('body') or '').strip()}")
        parts.append("\n")

    parts.append(section("共识 (decisions)", by_kind["decision"]))
    parts.append(section("候选方案 (options)", by_kind["option"]))
    parts.append(section("约束 (constraints)", by_kind["constraint"]))

    open_qs = [m for m in by_kind["open_question"] if int(m["id"]) not in resolved_q_ids]
    if open_qs:
        parts.append(section("待解决问题 (open questions)", open_qs))

    parts.append(section("盲点 (blind spots — 设计中容易漏的)", by_kind["blind_spot"]))
    parts.append(section("反方观点 (critiques)", by_kind["critique"]))
    parts.append(section("延展想法 (extensions)", by_kind["extension"]))

    if diagrams:
        parts.append("## 图与资料\n")
        for _mid, src in diagrams:
            parts.append("```mermaid")
            parts.append(src)
            parts.append("```\n")
    if links:
        parts.append("## 引用链接\n")
        seen: set[str] = set()
        for _mid, u in links:
            if u in seen:
                continue
            seen.add(u)
            parts.append(f"- {u}")
        parts.append("")

    if chats:
        parts.append("## 关键讨论 (tail)\n")
        for c in chats[-12:]:
            who = "agent" if c.get("actor_type") == "agent" else "human"
            body = (c.get("body") or "").strip().replace("\n", " ")
            if len(body) > 280:
                body = body[:280] + "…"
            parts.append(f"- **{who}** [{c.get('id')}]: {body}")
        parts.append("")

    return "\n".join(parts).rstrip() + "\n"
