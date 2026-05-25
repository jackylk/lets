"""Lets gateway — the relay between your local CC/Codex and the Lets web app.

CC and Codex are the agents. This process is just the gateway that ferries
messages between them and Lets — it doesn't think, it doesn't hold
conversation memory, it just routes.

Run one gateway per agent_instance on your local machine. It authenticates
to a Lets instance via a Bearer token (bound to one specific agent_instance),
polls every topic you're a participant in, and when it sees a message
addressed to your human, spawns the matching local CLI agent to handle it
and posts the agent's reply back to the topic.

Usage:
    python -m app.gateway --token lets_xxx
    python -m app.gateway --token lets_xxx --cmd "claude --print"
    python -m app.gateway --token lets_xxx --cmd "codex exec"

The token determines the gateway's identity (role + device_label).
Without --cmd it auto-picks the CLI based on the token's role:
    claude → "claude --print"
    codex  → "codex exec"

Once running, the bound agent_instance shows up in the Lets web UI's
"Agent" sidebar with a green dot within ~30s, and any chat/question
posted in the web that includes the agent's human_id in addressed_to
will trigger a real local CLI invocation.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# Bypass any system proxy (macOS often injects one for localhost) so urllib
# doesn't 502 on a 127.0.0.1 backend. Build an opener once.
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _urlopen(req: urllib.request.Request, timeout: float = 20.0):
    return _OPENER.open(req, timeout=timeout)


@dataclass
class Identity:
    human_id: int
    human_name: str
    agent_instance_id: int
    role: str
    device_label: str
    model: str | None = None


def _http(host: str, token: str, method: str, path: str, body: dict | None = None) -> Any:
    url = f"{host.rstrip('/')}{path}"
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, method=method, data=data)
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with _urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} → {e.code}: {e.read().decode('utf-8')}") from e


def _http_public(host: str, method: str, path: str) -> Any:
    req = urllib.request.Request(f"{host.rstrip('/')}{path}", method=method)
    try:
        with _urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} → {e.code}: {e.read().decode('utf-8')}") from e


def _mcp_call(host: str, token: str, name: str, arguments: dict) -> Any:
    """Invoke an MCP tool via JSON-RPC and return the unwrapped result.

    FastMCP's streamable-http requires Accept: application/json and
    text/event-stream both, and responds with event-stream framing —
    we parse the first `data: ` line as the JSON-RPC payload.
    """
    req = urllib.request.Request(
        f"{host.rstrip('/')}/mcp/",
        method="POST",
        data=json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    body = _urlopen(req, timeout=20).read().decode("utf-8")
    raw: Any
    if body.lstrip().startswith("event:"):
        raw = None
        for line in body.splitlines():
            if line.startswith("data: "):
                raw = json.loads(line[6:])
                break
        if raw is None:
            raise RuntimeError(f"no data: line in SSE response: {body[:200]}")
    else:
        raw = json.loads(body)
    result = raw.get("result", {}) if isinstance(raw, dict) else {}
    if result.get("isError"):
        raise RuntimeError(f"MCP {name} error: {result}")
    # Each content block is a separate JSON-serialized return value
    content = result.get("content", [])
    parsed: list = []
    for c in content:
        if c.get("type") != "text":
            continue
        try:
            parsed.append(json.loads(c["text"]))
        except json.JSONDecodeError:
            parsed.append(c["text"])
    if not parsed:
        return None
    return parsed if len(parsed) > 1 else parsed[0]


def _whoami(host: str, token: str) -> Identity:
    # /mcp/ over urllib without SSE Accept may not work — use /api/identity/me
    # equivalent via the MCP whoami tool. Fall back to direct DB shape.
    raw = _urlopen(
        urllib.request.Request(
            f"{host}/mcp/",
            method="POST",
            data=json.dumps({
                "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": "whoami", "arguments": {}},
            }).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
        ),
        timeout=10,
    ).read().decode("utf-8")
    # Parse SSE response
    payload = None
    for line in raw.splitlines():
        if line.startswith("data: "):
            payload = json.loads(line[6:])
            break
    if payload is None:
        payload = json.loads(raw)
    content = payload["result"]["content"]
    me = json.loads(content[0]["text"])
    if me.get("agent_instance_id") is None:
        raise SystemExit(
            "this token is not bound to an agent_instance. Issue a new one with "
            "scripts/connect_local_agents.sh or the web Settings → Agent Tokens page."
        )
    return Identity(
        human_id=int(me["human_id"]),
        human_name=str(me.get("human_name") or "?"),
        agent_instance_id=int(me["agent_instance_id"]),
        role=str(me.get("role") or "?"),
        device_label=str(me.get("device_label") or "?"),
        model=str(me.get("model")).strip() if me.get("model") else None,
    )


def _is_retryable_network_error(exc: BaseException) -> bool:
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code >= 500 or exc.code == 429
    if isinstance(exc, urllib.error.URLError):
        return True
    return False


def _wait_for_identity(host: str, token: str) -> Identity:
    delay = 2.0
    while True:
        try:
            return _whoami(host, token)
        except SystemExit:
            raise
        except Exception as e:
            if not _is_retryable_network_error(e):
                raise
            print(f"identity check failed; retrying in {delay:.0f}s: {e}", file=sys.stderr)
            time.sleep(delay)
            delay = min(delay * 1.5, 30.0)


def _list_topics(host: str, token: str) -> list[dict]:
    raw = _mcp_call(host, token, "list_my_topics", {"limit": 50})
    if raw is None:
        return []
    return raw if isinstance(raw, list) else [raw]


def _read_topic(host: str, token: str, topic_id: int, after_id: int | None) -> list[dict]:
    """Read messages in chronological (oldest-first) order.

    When ``after_id`` is given we use the natural incremental path. Without
    it we still need the *latest* N messages (for prompt-building) — so we
    pull ``order=desc`` to get the newest first and then reverse so callers
    keep seeing oldest-first. Without this, topics longer than ``limit``
    silently drop the tail and the gateway logs "trigger msg vanished".
    """
    args: dict = {"topic_id": topic_id, "limit": 500}
    if after_id is not None:
        args["after_id"] = after_id
    else:
        args["order"] = "desc"
    raw = _mcp_call(host, token, "read_topic", args)
    if raw is None:
        return []
    msgs = raw if isinstance(raw, list) else [raw]
    if after_id is None:
        # We asked for newest-first; restore chronological order for the caller.
        msgs = list(reversed(msgs))
    return msgs


def _post(host: str, token: str, topic_id: int, type_: str, body: str, **metadata) -> dict:
    return _mcp_call(host, token, "post_typed_message", {
        "topic_id": topic_id,
        "type": type_,
        "body": body,
        "metadata": metadata or {},
    })


def _addressed_to_me(msg: dict, my_agent_id: int, my_human_id: int | None = None) -> bool:
    addr = msg.get("addressed_to")
    if not addr:
        return False
    parts = {p.strip() for p in str(addr).split(",")}
    if f"agent:{my_agent_id}" in parts:
        return True
    # Legacy compatibility: a bare number used to mean human:<id>.
    return my_human_id is not None and str(my_human_id) in parts


_PROACTIVE_REPLY_TYPES = {
    "chat", "finding", "decision", "question", "handoff", "review",
    "artifact_revision", "spec_change", "nudge", "proactive_finding",
}


def _should_proactively_join(recent: list[dict], trigger: dict, my_agent_id: int) -> bool:
    """Conservative observer-mode trigger for multi-human conversations.

    Direct mentions are handled elsewhere. This path is for "agent can speak at
    the right time": after several consecutive human chat messages, and only
    when at least two humans are actually participating, join with a broadening
    thought instead of answering every line.
    """
    if trigger.get("actor_type") != "human" or trigger.get("type") != "chat":
        return False
    recent_human_ids = {
        int(m["actor_id"])
        for m in recent[-12:]
        if m.get("actor_type") == "human"
        and m.get("type") == "chat"
        and m.get("actor_id") is not None
    }
    if len(recent_human_ids) < 2:
        return False

    human_msgs_since_agent = 0
    for m in reversed(recent):
        if (
            m.get("actor_type") == "agent"
            and int(m.get("actor_id") or 0) == my_agent_id
            and m.get("type") in _PROACTIVE_REPLY_TYPES
        ):
            break
        if m.get("actor_type") == "human" and m.get("type") == "chat":
            human_msgs_since_agent += 1

    return human_msgs_since_agent >= 4 and human_msgs_since_agent % 4 == 0


# Compact pane-updates spec — same parser, fraction of the tokens.
# "headline" is a ≤30-char one-liner the UI shows when the agent's full
# reply is folded ("AI 折叠" view mode). Should capture the essence of this
# turn so the human can decide whether to expand.
_PANE_UPDATE_INSTRUCTIONS = (
    "Maintain the right context pane as a living design memo. After the reply, "
    "append pane_updates whenever this turn adds or refines a decision, option, "
    "constraint, open question, blind spot, critique, or extension. Omit only "
    "when there is truly no durable context to save.\n"
    "The pane is where most of your value should accumulate. Keep chat replies "
    "short and useful; pane_updates carry the durable shared structure.\n"
    "For brainstorming/design discussions, you MUST usually write at least: "
    "one decision or current goal, 2-4 options when alternatives appear, and "
    "one blind_spot or critique when there is a real risk. The pane is the "
    "product's shared memory, not an optional appendix.\n"
    "<pane_updates>{\"headline\":\"≤30字 中文一句话本轮要点\","
    "\"decisions\":[{\"body\":\"…\"}],"
    "\"options\":[{\"title\":\"…\",\"body\":\"…\",\"pros\":[\"…\"],\"cons\":[\"…\"]}],"
    "\"constraints\":[{\"body\":\"…\"}],"
    "\"open_questions\":[{\"body\":\"…\"}],"
    "\"blind_spots\":[{\"body\":\"…\"}],"
    "\"critiques\":[{\"body\":\"…\"}],"
    "\"extensions\":[{\"body\":\"…\"}]}</pane_updates>\n"
    "Valid JSON, omit keys you have nothing for, one line per item, "
    "no duplicates with prior items, no mention in prose. "
    "Always include headline — it's what the human sees when your reply is folded.\n"
    "open_questions are EXPENSIVE — they pile up in the human's right pane "
    "and demand attention. Emit ONLY when there is a real, blocking, "
    "undecided choice that the human (not you) must answer. At most 1 per "
    "reply. If you can take a position, do that instead — put it in "
    "decisions or just say it in prose.\n"
    "blind_spots: things the human is NOT considering but should — risks, "
    "missing stakeholders, second-order effects, scope creep. Only emit when "
    "you have a concrete one (≤25 字 中文)，not every turn. At most 2 per reply.\n"
    "critiques: a devil's-advocate take on the current direction — \"this "
    "won't work because…\" / \"the weak spot here is…\". Use to surface "
    "objections that aren't pure blind spots, more like reasoned dissent. "
    "At most 1 per reply, only when warranted.\n"
    "extensions: creative \"yes-and\" — adjacent ideas / variations that "
    "extend the current direction in a useful way. At most 1 per reply.\n"
    "When useful, draw mermaid diagrams (flow, graph, sequence) directly in "
    "your prose — they auto-collect into 图与资料. For decision trees use "
    "mermaid `graph TD`. For comparing multiple options use a markdown "
    "table in prose. When summarizing 3+ branching options or sub-features, "
    "use a mermaid `mindmap` block — it gives the human a tree view they "
    "can scan at a glance."
)


_PERSONA_OVERLAYS = {
    "red": (
        "\n\nRED-TEAM MODE: you argue against the current direction. "
        "Find the weakest assumption every turn and challenge it. "
        "When you raise a critique, put it in pane_updates.critiques. "
        "Don't be contrarian for sport — challenge what would actually "
        "kill the project: hidden costs, unmodeled risk, the user "
        "saying 'no' for a reason you haven't surfaced. If after "
        "challenging you still think it's fine, say so plainly."
    ),
    "blue": (
        "\n\nBLUE-TEAM MODE: you defend and refine the current "
        "direction. When someone (human or red-team) attacks it, "
        "address the specific weak point — concede where they're "
        "right, sharpen where they're wrong. Move toward a decision; "
        "don't relitigate settled questions. When you confirm an "
        "objection has been addressed, put it in pane_updates.decisions."
    ),
}


_HEALTH_TOPIC_RE = re.compile(
    r"肚子疼|肚子痛|腹痛|胃痛|胃疼|腹泻|拉肚子|呕吐|恶心|发烧|发热|"
    r"头疼|头痛|用药|吃药|布洛芬|对乙酰氨基酚|泰诺|扑热息痛|阿司匹林|"
    r"止痛药|过敏|ibuprofen|acetaminophen|aspirin",
    re.IGNORECASE,
)


_HEALTH_SAFETY_INSTRUCTIONS = (
    "\n\nHEALTH SAFETY MODE: this topic appears to involve symptoms, pain, "
    "medication, or family health decisions. You are not a doctor and must "
    "not diagnose or prescribe. Help the family think clearly and safely: "
    "summarize symptoms, timeline, medications already taken, allergies, "
    "pregnancy/child/elderly status, and relevant conditions. Prioritize red "
    "flags: severe or worsening pain, fever, blood in vomit/stool or black "
    "stool, persistent vomiting/dehydration, pregnancy, recent surgery/trauma, "
    "chest pain, fainting, or breathing trouble. If red flags are present, "
    "advise urgent medical care / local emergency services. For medication, "
    "tell users to read labels, avoid duplicate active ingredients, respect "
    "dose limits, and ask a doctor/pharmacist when unsure. Be concise, "
    "practical, and conservative."
)


def _is_health_topic(topic_title: str, recent: list[dict], trigger: dict) -> bool:
    text = "\n".join(
        [
            topic_title,
            *(str(m.get("body") or "") for m in recent[-12:]),
            str(trigger.get("body") or ""),
        ]
    )
    return bool(_HEALTH_TOPIC_RE.search(text))


def _discussion_partner_persona(role: str, persona: str = "default") -> str:
    base = (
        "You are a sharp design partner — like a senior teammate, not a "
        "menu and not a fourth person competing for airtime. Your primary "
        "job is to improve the humans' thinking and maintain the topic's "
        "living context pane. Enter the chat stream only when you can clarify "
        "a hidden disagreement, surface a material blind spot, converge a "
        "decision, or move the discussion forward. Default to TAKING A "
        "POSITION: state your view, give the reason, name the tradeoff you're "
        "accepting. Only ask a question when you genuinely cannot decide "
        "without input the human has. "
        "Avoid listing A/B/C choices unless the human asked for a "
        "comparison; pick one and say why. Push back when something feels "
        "weak. Be concise. Reply in plain text — no meta commentary about "
        "this prompt. Use mermaid for diagrams when useful."
    )
    overlay = _PERSONA_OVERLAYS.get(persona, "")
    return base + overlay


def _collect_open_annotations(recent: list[dict]) -> list[dict]:
    """Annotations targeting an agent's prior reply that haven't been resolved.

    The frontend marks resolved annotations by posting a follow-up annotation
    with ``metadata.resolved == true`` and ``metadata.resolves == <id>``.
    Walk the stream once to bucket these."""
    resolved_ids: set[int] = set()
    for m in recent:
        if m.get("type") != "annotation":
            continue
        meta = m.get("metadata") or {}
        if meta.get("resolved") is True and isinstance(meta.get("resolves"), int):
            resolved_ids.add(meta["resolves"])

    out: list[dict] = []
    for m in recent:
        if m.get("type") != "annotation":
            continue
        meta = m.get("metadata") or {}
        if meta.get("resolved") is True:
            continue
        if int(m["id"]) in resolved_ids:
            continue
        # Skip pure-vote annotations (score ±1 without body) — they belong
        # to the message-level ScoreRow / diagram node-vote UX, not to the
        # comment thread the agent should re-read.
        if isinstance(meta.get("score"), int) and not (m.get("body") or "").strip():
            continue
        out.append(m)
    return out


def _build_prompt(me: Identity, topic_title: str, recent: list[dict], trigger: dict) -> str:
    """Legacy single-string prompt — kept for back-compat with --cmd custom CLIs."""
    sys_part, user_part = _build_prompt_split(me, topic_title, recent, trigger)
    return sys_part + "\n\n" + user_part


def _build_prompt_split(
    me: Identity,
    topic_title: str,
    recent: list[dict],
    trigger: dict,
    persona: str = "default",
    intervention_mode: str = "direct",
) -> tuple[str, str]:
    """Return ``(system_prompt, user_prompt)``.

    The system_prompt is everything STABLE across turns (persona + the
    pane_updates protocol). The user_prompt is everything VARIABLE
    (history + new message). Anthropic's prompt cache hits on the stable
    prefix, so splitting like this maximizes cache reuse turn-over-turn:
    after the first turn, the persona block is read from cache (10% of
    full input cost, faster TTFT).
    """
    history_lines = []
    # 8 recent messages × 150 char trunc is enough context for a turn while
    # keeping the user prompt small enough that input is no longer the
    # bottleneck. Older history is already in the agent's --resume session.
    for m in recent[-8:]:
        if m["id"] == trigger["id"]:
            continue
        if m.get("type") == "annotation":
            continue
        actor = "H" if m["actor_type"] == "human" else "A"
        body_line = (m.get("body") or "").replace("\n", " ")[:150]
        history_lines.append(f"{actor} [{m['type']}]: {body_line}")
    history = "\n".join(history_lines) if history_lines else "(none)"

    annotations = _collect_open_annotations(recent)
    if annotations:
        ann_lines = []
        for a in annotations:
            meta = a.get("metadata") or {}
            quote = (meta.get("target_quote") or "").replace("\n", " ").strip()[:100]
            body = (a.get("body") or "").strip()[:200]
            ann_lines.append(f'  - on "{quote}": {body}')
        annotation_section = (
            "\nOpen annotations on your earlier replies (address explicitly):\n"
            + "\n".join(ann_lines) + "\n"
        )
    else:
        annotation_section = ""

    # Tell the agent which prior questions the human has already answered —
    # so it stops surfacing them in pane_updates.open_questions. Keeps the
    # right pane clean and avoids the "agent re-raises stale issues" feel.
    resolved_section = _collect_resolved_questions_section(recent)

    health_mode = _is_health_topic(topic_title, recent, trigger)
    system_prompt = (
        f"{_discussion_partner_persona(me.role, persona)}\n\n{_PANE_UPDATE_INSTRUCTIONS}"
        f"{_HEALTH_SAFETY_INSTRUCTIONS if health_mode else ''}"
    )

    sender = "human" if trigger["actor_type"] == "human" else "agent"
    if intervention_mode == "proactive":
        intervention_note = (
            "\nIntervention mode: proactive observer. The human did not "
            "explicitly @mention you. Act as a living discussion memo: briefly "
            "summarize the current goal/方案, broaden the option space, surface "
            "one concrete blind spot/risk/decision point, and suggest a next "
            "step. Keep it concise and avoid taking over the conversation.\n"
        )
    else:
        intervention_note = ""
    if health_mode:
        intervention_note += (
            "\nThis is health-related. Do not brainstorm like a design topic. "
            "First help the family confirm severity, red flags, timeline, "
            "medication history, and whether professional care is needed.\n"
        )
    user_prompt = (
        f"Topic: {topic_title}\n\n"
        f"Recent:\n{history}\n"
        f"{annotation_section}"
        f"{resolved_section}\n"
        f"{intervention_note}"
        f"New {sender} msg:\n{trigger.get('body', '')}"
    )

    return system_prompt, user_prompt


def _collect_resolved_questions_section(recent: list[dict]) -> str:
    """Build a short prompt section listing question/answer pairs the human
    has already resolved via the right-pane "答" inline editor. Lets the
    agent stop re-raising them in pane_updates.open_questions."""
    # Map question_id → question_body
    questions: dict[int, str] = {}
    for m in recent:
        meta = m.get("metadata") or {}
        if meta.get("discussion_kind") != "open_question":
            continue
        questions[int(m["id"])] = (m.get("body") or "").strip()
    # Find decisions that resolve them
    pairs: list[tuple[str, str]] = []
    for m in recent:
        meta = m.get("metadata") or {}
        if meta.get("discussion_kind") != "decision":
            continue
        qid = meta.get("resolves_question")
        if not isinstance(qid, int):
            continue
        q = questions.get(qid)
        if not q:
            continue
        pairs.append((q[:80], (m.get("body") or "").strip()[:120]))
    if not pairs:
        return ""
    lines = "\n".join(f'  - Q: "{q}" → A: {a}' for q, a in pairs)
    return (
        "\nQuestions the human already answered (do not re-list these as "
        "open_questions):\n" + lines + "\n"
    )


# ─── Pane-update parsing & posting ───────────────────────────────────────

_PANE_FENCE_RE = re.compile(
    r"<pane_updates>\s*([\s\S]*?)\s*</pane_updates>",
    re.IGNORECASE,
)


def _parse_pane_updates(output: str) -> tuple[str, dict]:
    """Pull a <pane_updates> JSON block out of the agent's reply, if any.

    Returns ``(chat_body, updates)`` where ``chat_body`` is the agent's prose
    with the entire fence removed (even if the JSON inside was malformed) and
    ``updates`` is the parsed dict (empty on parse failure)."""
    m = _PANE_FENCE_RE.search(output)
    if not m:
        return output, {}
    chat_body = (output[: m.start()] + output[m.end() :]).rstrip()
    inner = (m.group(1) or "").strip()
    if not inner:
        return chat_body, {}
    nested = _parse_pane_updates_json_candidate(inner)
    if nested is not None:
        return chat_body, nested
    try:
        updates = json.loads(inner)
    except json.JSONDecodeError:
        print(
            f"  WARN: pane_updates JSON malformed, falling back to prose extraction: {inner[:200]}",
            file=sys.stderr,
        )
        return chat_body, _fallback_pane_updates(inner)
    if not isinstance(updates, dict):
        return chat_body, {}
    return chat_body, updates


def _parse_pane_updates_json_candidate(text: str) -> dict | None:
    """Recover JSON when the model explains the protocol before the real block."""
    marker = "<pane_updates>"
    lower = text.lower()
    if marker not in lower:
        return None
    start = lower.rfind(marker) + len(marker)
    candidate = _balanced_json_object(text[start:].strip())
    if not candidate:
        return None
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _balanced_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for i, ch in enumerate(text[start:], start=start):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _fallback_pane_updates(chat_body: str) -> dict:
    """Best-effort context-pane extraction when the agent forgets pane_updates.

    The model often writes useful sections in prose ("目标", "候选方案",
    "风险") but omits the machine-readable block. Keep the product useful by
    promoting those sections into pane cards.
    """
    updates: dict[str, Any] = {}
    headline = _first_nonempty_line(chat_body)
    if headline:
        updates["headline"] = headline[:60]

    goals = _section_items(chat_body, ("目标", "核心目标"))
    if goals:
        updates["decisions"] = [{"body": goals[0][:220]}]

    options = _section_items(chat_body, ("候选方案", "方案", "路线"))
    if options:
        updates["options"] = [
            {"title": _compact_title(item), "body": item[:260]}
            for item in options[:4]
        ]

    risks = _section_items(chat_body, ("风险", "问题", "盲点"))
    if risks:
        updates["blind_spots"] = [{"body": item[:180]} for item in risks[:2]]

    return updates if any(k in updates for k in ("decisions", "options", "blind_spots")) else {}


def _first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        s = line.strip().strip("*# ")
        if s:
            return s
    return ""


def _section_items(text: str, headings: tuple[str, ...]) -> list[str]:
    lines = text.splitlines()
    capture = False
    out: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if not current:
            return
        item = " ".join(part.strip() for part in current if part.strip()).strip()
        current.clear()
        if item:
            out.append(item)

    heading_re = re.compile(r"^\s*(?:#{1,4}\s*)?\*{0,2}([^*#：:]+)[：:]?\*{0,2}\s*$")
    item_re = re.compile(r"^\s*(?:[-*]\s+|\d+[.、]\s+)(.*)$")

    for line in lines:
        raw = line.strip()
        hm = heading_re.match(raw)
        if hm:
            title = hm.group(1).strip()
            if any(h in title for h in headings):
                flush()
                capture = True
                continue
            if capture and re.search(r"目标|方案|风险|问题|盲点|约束|下一步|总结|核心", title):
                flush()
                capture = False
        if not capture:
            continue
        im = item_re.match(raw)
        if im:
            flush()
            current.append(im.group(1).strip())
        elif raw:
            current.append(raw)
        else:
            flush()
    flush()
    return out


def _compact_title(text: str) -> str:
    title = re.sub(r"^[\d.、\s]+", "", text).strip()
    title = re.split(r"[。:：]|\s{2,}", title, maxsplit=1)[0].strip()
    if len(title) > 18 and re.search(r"(版|索|检索|方案|路线|RAG|Embedding|关键词)", title):
        title = re.split(r"\s+", title, maxsplit=1)[0].strip()
    return title[:32] or "候选方案"


_KIND_TO_TYPE = {
    "decision":      "decision",
    "option":        "proactive_finding",
    "constraint":    "finding",
    "open_question": "question",
    "blind_spot":    "proactive_finding",
    "critique":      "proactive_finding",
    "extension":     "proactive_finding",
}
_KIND_TO_ARRAY = {
    "decision":      "decisions",
    "option":        "options",
    "constraint":    "constraints",
    "open_question": "open_questions",
    "blind_spot":    "blind_spots",
    "critique":      "critiques",
    "extension":     "extensions",
}


def _post_pane_updates(host: str, token: str, topic_id: int, updates: dict, source_msg_id: int | None = None) -> int:
    """Post each pane_update item as its own typed message. Returns count posted."""
    posted = 0
    for kind, type_ in _KIND_TO_TYPE.items():
        items = updates.get(_KIND_TO_ARRAY[kind]) or []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            body = (item.get("body") or item.get("title") or "").strip()
            if not body:
                continue
            metadata: dict[str, Any] = {"discussion_kind": kind}
            if source_msg_id is not None:
                metadata["promoted_from"] = source_msg_id
            if kind == "option":
                if isinstance(item.get("title"), str) and item["title"].strip():
                    metadata["title"] = item["title"].strip()
                if isinstance(item.get("pros"), list):
                    metadata["pros"] = [str(p) for p in item["pros"] if p]
                if isinstance(item.get("cons"), list):
                    metadata["cons"] = [str(c) for c in item["cons"] if c]
            try:
                _post(host, token, topic_id, type_, body, **metadata)
                posted += 1
            except Exception as e:
                print(f"  WARN: failed to post pane_update {kind}: {e}", file=sys.stderr)
    return posted


def _default_session_dir() -> str:
    home = os.path.expanduser(os.environ.get("LETS_HOME", "~/.lets"))
    return os.path.join(home, "sessions")


def _session_path(session_dir: str, host: str, topic_id: int, engine: str) -> str:
    key = json.dumps(
        {
            "host": host.rstrip("/"),
            "topic_id": int(topic_id),
            "engine": engine,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
    return os.path.join(session_dir, f"{digest}.json")


def _load_session(session_dir: str, host: str, topic_id: int, engine: str) -> dict | None:
    path = _session_path(session_dir, host, topic_id, engine)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    if not data.get("session_id"):
        return None
    return data


def _save_session(
    session_dir: str,
    host: str,
    topic_id: int,
    engine: str,
    session_id: str,
    *,
    last_message_id: int | None = None,
) -> None:
    os.makedirs(session_dir, exist_ok=True)
    path = _session_path(session_dir, host, topic_id, engine)
    now = time.time()
    prior = _load_session(session_dir, host, topic_id, engine) or {}
    data = {
        "host": host.rstrip("/"),
        "topic_id": int(topic_id),
        "engine": engine,
        "session_id": session_id,
        "created_at": prior.get("created_at") or now,
        "updated_at": now,
    }
    if last_message_id is not None:
        data["last_message_id"] = int(last_message_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    os.chmod(path, 0o600)


def _find_session_id(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("session_id", "sessionId"):
            found = value.get(key)
            if isinstance(found, str) and found.strip():
                return found.strip()
        session = value.get("session")
        if isinstance(session, dict):
            found = session.get("id")
            if isinstance(found, str) and found.strip():
                return found.strip()
        for child in value.values():
            found = _find_session_id(child)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = _find_session_id(child)
            if found:
                return found
    return None


def _text_from_value(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        parts = []
        for item in value:
            text = _text_from_value(item)
            if text:
                parts.append(text)
        return "\n".join(parts).strip() or None
    if not isinstance(value, dict):
        return None

    for key in ("result", "output", "text", "content", "message"):
        if key not in value:
            continue
        candidate = value[key]
        if isinstance(candidate, dict) and key == "message":
            role = candidate.get("role")
            if role and role not in ("assistant", "agent"):
                continue
        text = _text_from_value(candidate)
        if text:
            return text

    # OpenAI/Codex-style content blocks.
    parts = []
    for child in value.values():
        if isinstance(child, (dict, list)):
            text = _text_from_value(child)
            if text:
                parts.append(text)
    return "\n".join(parts).strip() or None


def _parse_agent_output(stdout: str) -> tuple[str, str | None]:
    raw = stdout.strip()
    if not raw:
        return "", None

    records: list[Any] = []
    try:
        records.append(json.loads(raw))
    except json.JSONDecodeError:
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                records = []
                break

    if not records:
        return raw, None

    session_id = None
    texts: list[str] = []
    for record in records:
        session_id = _find_session_id(record) or session_id
        text = _text_from_value(record)
        if text:
            texts.append(text)
    return ("\n".join(texts).strip() or raw), session_id


def _with_arg(cmd: list[str], *args: str) -> list[str]:
    out = list(cmd)
    for arg in args:
        if arg not in out:
            out.append(arg)
    return out


def _with_model(cmd: list[str], engine: str, model: str | None) -> list[str]:
    if engine not in ("claude", "codex") or not model or "--model" in cmd or "-m" in cmd:
        return cmd
    return [*cmd, "--model", model]


def _agent_command(
    cmd: list[str],
    engine: str,
    session_id: str | None,
    system_prompt: str | None = None,
) -> list[str]:
    if engine == "claude":
        out = list(cmd)
        if "--output-format" not in out:
            out.extend(["--output-format", "json"])
        if session_id and "--resume" not in out and "-r" not in out:
            out.extend(["--resume", session_id])
        # Stable persona / pane_updates instructions go in --append-system-prompt
        # so Anthropic's prompt cache hits this prefix on subsequent turns.
        if system_prompt and "--append-system-prompt" not in out:
            out.extend(["--append-system-prompt", system_prompt])
        return out
    if engine == "codex":
        if len(cmd) >= 2 and cmd[0] == "codex" and cmd[1] == "exec":
            out = [cmd[0], cmd[1]]
            if "--skip-git-repo-check" not in out:
                out.append("--skip-git-repo-check")
            if session_id:
                out.extend(["resume", session_id])
            out.extend(cmd[2:])
            return _with_arg(out, "--json")
        return cmd
    return cmd


def _error_for_cli(engine: str, cmd: list[str], returncode: int, stderr: str) -> str:
    name = "Claude CLI" if engine == "claude" else "Codex CLI" if engine == "codex" else "local CLI"
    probe = "claude --print 'hi'" if engine == "claude" else "codex exec --skip-git-repo-check 'hi'" if engine == "codex" else "the CLI"
    return (
        f"{name} 调用失败。\n\n"
        f"command: {' '.join(cmd)}\n"
        f"exit: {returncode}\n"
        f"stderr:\n{(stderr.strip() or '(no stderr)')[:2000]}\n\n"
        f"在终端运行 `{probe}` 验证本机非交互模式可用后，再重试这条消息。"
    )


def _timeout_for_cli(engine: str, timeout: int) -> str:
    name = "Claude CLI" if engine == "claude" else "Codex CLI" if engine == "codex" else "local CLI"
    probe = "claude --print 'hi'" if engine == "claude" else "codex exec --skip-git-repo-check 'hi'" if engine == "codex" else "the CLI"
    return (
        f"{name} 超过 {timeout}s 没有返回。\n\n"
        f"在终端运行 `{probe}` 验证本机非交互模式可用；"
        "如果它也卡住，需要先修复本机 CLI 的登录/网络环境。"
    )


def _invoke_agent_turn(
    *,
    cmd: list[str],
    prompt: str,
    timeout: int,
    me: Identity,
    host: str,
    topic_id: int,
    session_dir: str,
    trigger_message_id: int | None = None,
    system_prompt: str | None = None,
) -> tuple[bool, str]:
    """Invoke the local agent CLI with session-resume support.

    If the saved session_id is unknown to the CLI (`claude` deletes its local
    session DB on upgrade, the user removes ~/.claude, etc.), `claude --resume`
    can either error out fast (`No conversation found`) or — in non-tty stdin
    mode — hang waiting for a confirmation. Either way we drop the stale
    session_id, delete the cache file, and retry once without `--resume`.

    ``system_prompt`` is the stable part of the prompt (persona, output format
    spec). Passing it separately via --append-system-prompt lets Anthropic's
    prompt cache hit it on subsequent turns, cutting input cost and TTFT.
    """
    session = _load_session(session_dir, host, topic_id, me.role)
    session_id = str(session["session_id"]) if session else None

    def _run(use_session_id: str | None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            _agent_command(cmd, me.role, use_session_id, system_prompt) + [prompt],
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )

    def _stale_session(returncode: int, stderr: str) -> bool:
        if returncode == 0:
            return False
        lowered = (stderr or "").lower()
        return (
            "no conversation found" in lowered
            or "session not found" in lowered
            or "unknown session" in lowered
        )

    try:
        try:
            proc = _run(session_id)
        except subprocess.TimeoutExpired:
            # Could be a hung --resume on a stale session — retry fresh.
            if not session_id:
                return False, _timeout_for_cli(me.role, timeout)
            _forget_session(session_dir, host, topic_id, me.role)
            proc = _run(None)

        if session_id and _stale_session(proc.returncode, proc.stderr):
            _forget_session(session_dir, host, topic_id, me.role)
            proc = _run(None)

        if proc.returncode != 0:
            return False, _error_for_cli(
                me.role,
                _agent_command(cmd, me.role, None, system_prompt),
                proc.returncode,
                proc.stderr,
            )
        text, next_session_id = _parse_agent_output(proc.stdout)
        if next_session_id:
            _save_session(
                session_dir,
                host,
                topic_id,
                me.role,
                next_session_id,
                last_message_id=trigger_message_id,
            )
        if not text:
            return False, "local CLI produced no output"
        return True, text
    except subprocess.TimeoutExpired:
        return False, _timeout_for_cli(me.role, timeout)
    except FileNotFoundError as e:
        return False, f"local CLI not found: {e}"


def _forget_session(session_dir: str, host: str, topic_id: int, engine: str) -> None:
    path = _session_path(session_dir, host, topic_id, engine)
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        pass


def _invoke_local_cli(cmd: list[str], prompt: str, timeout: int) -> tuple[bool, str]:
    """Run the local agent CLI with the prompt; capture stdout."""
    try:
        proc = subprocess.run(
            cmd + [prompt] if "--print" in cmd or "exec" in cmd[-1:] else cmd,
            input=None if "--print" in cmd or "exec" in cmd[-1:] else prompt,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            return False, _error_for_cli("local", cmd, proc.returncode, proc.stderr)
        out = proc.stdout.strip()
        if not out:
            return False, "local CLI produced no output"
        return True, out
    except subprocess.TimeoutExpired:
        return False, _timeout_for_cli("local", timeout)
    except FileNotFoundError as e:
        return False, f"local CLI not found: {e}"


def _lets_home() -> str:
    return os.environ.get("LETS_HOME", os.path.expanduser("~/.lets"))


def _token_paths() -> tuple[str, str]:
    """Legacy single-token slot (back-compat). New installs use _agent_token_path."""
    home = _lets_home()
    return os.path.join(home, "token"), os.path.join(home, "token.json")


def _agent_token_path(role: str) -> str:
    """Per-agent token file. Enables `lets add claude` + `lets add codex` to
    coexist instead of clobbering each other."""
    return os.path.join(_lets_home(), "tokens", f"{role}.json")


def _list_agent_tokens() -> list[dict]:
    """Return all per-agent token records (legacy single + new per-role)."""
    out: list[dict] = []
    tokens_dir = os.path.join(_lets_home(), "tokens")
    if os.path.isdir(tokens_dir):
        for name in sorted(os.listdir(tokens_dir)):
            if not name.endswith(".json"):
                continue
            path = os.path.join(tokens_dir, name)
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                data["_path"] = path
                data["_role"] = data.get("agent_instance", {}).get("role") or name[:-5]
                out.append(data)
            except (json.JSONDecodeError, OSError):
                continue
    # Legacy fallback: include ~/.lets/token.json if no per-role file covers it.
    legacy = _load_token_meta()
    if legacy:
        role = (legacy.get("agent_instance") or {}).get("role") or "claude"
        if not any(r.get("_role") == role for r in out):
            legacy = dict(legacy)
            legacy["_path"] = _token_paths()[1]
            legacy["_role"] = role
            out.append(legacy)
    return out


def _load_token_for_agent(role: str | None) -> dict | None:
    """Resolve which token to use. If role given, look at tokens/<role>.json
    first, fall back to legacy. If role omitted, prefer legacy (single-agent
    install), else the first per-role token."""
    if role:
        path = _agent_token_path(role)
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        legacy = _load_token_meta()
        if legacy and (legacy.get("agent_instance") or {}).get("role") == role:
            return legacy
        return None
    legacy = _load_token_meta()
    if legacy:
        return legacy
    all_tokens = _list_agent_tokens()
    return all_tokens[0] if all_tokens else None


def _save_agent_token(role: str, host: str, token: str, agent_instance: dict | None) -> str:
    path = _agent_token_path(role)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "host": host.rstrip("/"),
                "token": token,
                "agent_instance": agent_instance,
            },
            f,
            indent=2,
        )
        f.write("\n")
    os.chmod(path, 0o600)
    return path


def _login(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="lets login")
    parser.add_argument(
        "--host",
        default=os.environ.get("LETS_HOST", "https://lets.up.railway.app"),
        help="Lets backend base URL",
    )
    parser.add_argument(
        "--role",
        choices=["claude", "codex"],
        default=os.environ.get("LETS_AGENT_ROLE", "claude"),
        help="Local agent type to register",
    )
    parser.add_argument(
        "--device-label",
        default=os.environ.get("LETS_DEVICE_LABEL", socket.gethostname()),
        help="Human-readable device label",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=600,
        help="Seconds to wait for browser authorization",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Print the authorization URL but do not open a browser",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("LETS_MODEL"),
        help="Model to store/use for this agent.",
    )
    parser.add_argument(
        "--workspace",
        default=os.environ.get("LETS_WORKSPACE"),
        help="Workspace slug to bind this agent to (default: caller's first workspace, auto-creates '我的工作区' if none).",
    )
    args = parser.parse_args(argv)

    params_dict = {
        "role": args.role,
        "device_label": args.device_label,
    }
    if args.model:
        params_dict["model"] = args.model
    if args.workspace:
        params_dict["workspace"] = args.workspace
    params = urllib.parse.urlencode(params_dict)
    start = _http_public(args.host, "GET", f"/auth/device-flow/start?{params}")
    verification_url = start["verification_url"]
    device_code = start["device_code"]
    interval = int(start.get("interval") or 3)

    if not args.no_open:
        opened = webbrowser.open(verification_url)
        if opened:
            print("Opened your browser to authorize this computer.")
        else:
            print("Could not open a browser automatically.")
    print("Open this URL in your browser if it did not open automatically:")
    print(verification_url)
    print()
    print(f"Code: {start['user_code']}")
    print("Waiting for authorization...")

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        poll_params = urllib.parse.urlencode({"device_code": device_code})
        data = _http_public(args.host, "GET", f"/auth/device-flow/poll?{poll_params}")
        if data.get("status") == "authorized":
            token = data["token"]
            agent_instance = data.get("agent_instance") or {}
            # New per-role slot — supports multi-agent.
            role_for_storage = agent_instance.get("role") or args.role
            role_path = _save_agent_token(
                role_for_storage, args.host, token, agent_instance,
            )
            # Legacy single-token slot is kept in sync so existing tooling
            # (`lets gateway` with no --agent, old install scripts) still works.
            token_path, token_json_path = _token_paths()
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(token)
            os.chmod(token_path, 0o600)
            with open(token_json_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "host": args.host.rstrip("/"),
                        "token": token,
                        "agent_instance": agent_instance,
                    },
                    f,
                    indent=2,
                )
                f.write("\n")
            os.chmod(token_json_path, 0o600)
            print(f"Saved token to {role_path}")
            print("Next: lets gateway")
            return 0
        time.sleep(interval)

    print("Timed out waiting for authorization.", file=sys.stderr)
    return 1


def _load_token_meta() -> dict | None:
    _, token_json_path = _token_paths()
    if not os.path.exists(token_json_path):
        return None
    try:
        with open(token_json_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _status(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="lets status")
    parser.parse_args(argv)
    token_path, _ = _token_paths()
    if not os.path.exists(token_path):
        print("not logged in. Run: lets login")
        return 1
    meta = _load_token_meta()
    if meta is None:
        print(f"logged in (token at {token_path}, no metadata file)")
        return 0
    ai = meta.get("agent_instance") or {}
    print(f"logged in to {meta.get('host', '?')}")
    if ai:
        human_label = ai.get("human_name")
        if not human_label and ai.get("owner_human_id") is not None:
            human_label = f"id:{ai.get('owner_human_id')}"
        if not human_label:
            human_label = "?"
        print(
            f"  as {ai.get('role', '?')}:{ai.get('device_label', '?')} "
            f"(human={human_label}, "
            f"agent_instance_id={ai.get('id', '?')})"
        )
    print(f"  token: {token_path}")
    plist = _launchd_plist_path()
    if os.path.exists(plist):
        print(f"  autostart: enabled ({plist})")
    else:
        print("  autostart: not installed (Run: lets install)")
    return 0


def _topics(argv: list[str]) -> int:
    """List the user's recent topics with ids so they can `lets spec <id>`."""
    parser = argparse.ArgumentParser(prog="lets topics")
    parser.add_argument("--host", default=None)
    parser.add_argument("--agent", default=None)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)

    rec = _load_token_for_agent(args.agent)
    if not rec or not rec.get("token"):
        print("Missing token. Run: lets login", file=sys.stderr)
        return 2
    host = args.host or rec.get("host") or "http://127.0.0.1:8000"
    token = rec["token"]

    try:
        topics = _mcp_call(host, token, "list_my_topics", {"limit": args.limit}) or []
    except Exception as e:
        print(f"Failed to list topics: {e}", file=sys.stderr)
        return 1
    if not isinstance(topics, list):
        topics = [topics] if topics else []

    if not topics:
        print("no topics yet.")
        return 0
    # Column widths sized for readable output.
    for t in topics:
        tid = t.get("id", "?")
        title = (t.get("title") or "").strip() or "(untitled)"
        if len(title) > 60:
            title = title[:57] + "…"
        print(f"  {tid:>4}  {title}")
    return 0


def _print_main_help() -> None:
    print(
        """usage: lets <command> [options]

Commands:
  add <claude|codex>     authorize and start a local agent
  leave                  remove this agent from a workspace
  gateway                start registered agent gateways in the background
  status                 show local Lets login and autostart status
  login                  authorize this computer
  logout                 remove the local token
  install                install launchd autostart
  uninstall              remove launchd autostart
  topics                 list recent topic ids
  spec <topic-id>        export a topic handoff spec
  run                    run the foreground gateway loop

Run `lets <command> --help` for command-specific options."""
    )


def _workspace_matches(workspace: dict, target: str) -> bool:
    normalized = target.strip().lower()
    return (
        str(workspace.get("id")) == normalized
        or str(workspace.get("slug") or "").lower() == normalized
        or str(workspace.get("name") or "").lower() == normalized
    )


def _leave_workspace(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="lets leave")
    parser.add_argument(
        "--workspace",
        "-w",
        required=True,
        help="Workspace id, slug, or exact name to leave.",
    )
    parser.add_argument(
        "--agent",
        default=None,
        help="Agent role to use (claude / codex). Defaults to the saved token.",
    )
    parser.add_argument(
        "--host",
        default=None,
        help="Lets backend URL. Defaults to the host stored at login.",
    )
    args = parser.parse_args(argv)

    rec = _load_token_for_agent(args.agent)
    if not rec or not rec.get("token"):
        print("Missing token. Run: lets add claude", file=sys.stderr)
        return 2

    host = args.host or rec.get("host") or os.environ.get("LETS_HOST", "http://127.0.0.1:8000")
    token = rec["token"]
    agent = rec.get("agent_instance") or {}
    agent_id = agent.get("id")
    if agent_id is None:
        agent_id = _whoami(host, token).agent_instance_id

    try:
        memberships = _http(host, token, "GET", "/api/agents/me/memberships") or []
    except Exception as e:
        print(f"Failed to list agent workspaces: {e}", file=sys.stderr)
        return 1
    matches = [w for w in memberships if _workspace_matches(w, args.workspace)]
    if not matches:
        print(f"agent is not in workspace: {args.workspace}", file=sys.stderr)
        return 1
    if len(matches) > 1:
        names = ", ".join(f"{w.get('name')} ({w.get('slug') or w.get('id')})" for w in matches)
        print(f"workspace is ambiguous: {names}", file=sys.stderr)
        return 1

    workspace = matches[0]
    try:
        _http(
            host,
            token,
            "DELETE",
            f"/api/workspaces/{workspace['id']}/agent-members/{agent_id}",
        )
    except Exception as e:
        print(f"Failed to leave workspace: {e}", file=sys.stderr)
        return 1

    role = agent.get("role") or args.agent or "agent"
    device = agent.get("device_label") or agent_id
    print(f"{role}:{device} left workspace {workspace.get('name') or workspace.get('slug') or workspace['id']}")
    return 0


def _spec(argv: list[str]) -> int:
    """Pull a topic from the blackboard and render it as a handoff spec.

    Usage: lets spec <topic-id> [--out spec.md] [--limit 500] [--host …]

    Designed so the human can throw it at a weaker agent (codex+deepseek
    etc.) on another machine and have enough context to actually build the
    thing without seeing the original chat.
    """
    parser = argparse.ArgumentParser(prog="lets spec")
    parser.add_argument("topic_id", type=int, help="Topic id to export")
    parser.add_argument(
        "--out", default="-",
        help="Output file path. Default '-' writes to stdout.",
    )
    parser.add_argument(
        "--limit", type=int, default=500,
        help="Max messages to pull from the topic (default 500).",
    )
    parser.add_argument(
        "--host", default=None,
        help="Lets backend URL. Defaults to the host stored at login.",
    )
    parser.add_argument(
        "--agent", default=None,
        help="Which agent's token to use (claude/codex). Defaults to "
             "first available.",
    )
    parser.add_argument(
        "--polish", action="store_true",
        help="Run claude --print over the raw spec to derive 设计目标 + "
             "实施步骤 sections. Adds ~30-60s but makes the spec materially "
             "more useful for handoff. Requires `claude` CLI on PATH.",
    )
    parser.add_argument(
        "--polish-model", default="sonnet",
        help="Model alias for --polish (default: sonnet, the balance of "
             "quality vs speed for a single-shot transform).",
    )
    parser.add_argument(
        "--self-test", action="store_true",
        help="After rendering (and optional polish), have an agent read "
             "the spec as if it were a weaker dev about to ship — appends "
             "a「自检」section listing concrete blockers the agent would "
             "hit. Useful for finding gaps before handoff.",
    )
    args = parser.parse_args(argv)

    rec = _load_token_for_agent(args.agent)
    if not rec or not rec.get("token"):
        print("Missing token. Run: lets login", file=sys.stderr)
        return 2
    host = args.host or rec.get("host") or "http://127.0.0.1:8000"
    token = rec["token"]

    try:
        msgs = _mcp_call(host, token, "read_topic", {
            "topic_id": args.topic_id,
            "limit": args.limit,
            "order": "asc",
        }) or []
    except Exception as e:
        print(f"Failed to read topic {args.topic_id}: {e}", file=sys.stderr)
        return 1
    if not isinstance(msgs, list):
        msgs = [msgs] if msgs else []

    from app.spec import render_spec_markdown
    text = render_spec_markdown(args.topic_id, msgs)

    if args.polish:
        try:
            text = _polish_spec(text, model=args.polish_model)
        except Exception as e:
            print(f"polish failed (keeping raw spec): {e}", file=sys.stderr)

    if args.self_test:
        try:
            text = _append_self_test(text, model=args.polish_model)
        except Exception as e:
            print(f"self-test failed (keeping spec as-is): {e}", file=sys.stderr)

    if args.out == "-":
        print(text)
    else:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"wrote {args.out} ({len(text)} chars, {len(msgs)} messages)",
              file=sys.stderr)
    return 0


_SPEC_POLISH_SYSTEM = (
    "You polish a design-discussion spec for handoff to a weaker dev agent "
    "(codex+deepseek-tier). The raw spec below comes from a discussion "
    "blackboard. Tasks, in order:\n"
    "1. Preserve the very first line verbatim (it is the `# Topic #N — title` "
    "header). Never rewrite or drop it.\n"
    "2. If 设计目标 is missing, infer one from the discussion and add it "
    "right after the masthead blockquote. 2-3 lines max.\n"
    "3. Keep EVERY existing [#nnn] citation exactly where it is — they are "
    "load-bearing back-references.\n"
    "4. Don't delete any existing bullet. You may reorder within a section.\n"
    "5. Append a new section `## 实施步骤 (v1)` at the bottom: 5-8 "
    "concrete, ordered, build-able steps for a weak agent to ship v1. "
    "Each step: 1 line action + 1 line acceptance criterion. Cite the "
    "relevant [#nnn] where applicable.\n"
    "6. Append a new section `## 风险与未决` summarizing what could still "
    "go wrong + which open_questions actually block v1.\n"
    "OUTPUT FORMAT: the very first character of your reply must be `#` "
    "(the topic header). No preamble like \"以下是…\" or \"Here is…\", no "
    "leading code fences, no trailing commentary."
)


_POLISH_PREAMBLE_RES = [
    re.compile(r"^\s*(以下是|这是|下面是)[^\n]*?[:：]?\s*\n+", re.IGNORECASE),
    re.compile(r"^\s*(here(?:'s| is)|below is)[^\n]*?[:]?\s*\n+", re.IGNORECASE),
    re.compile(r"^\s*```(?:markdown|md)?\s*\n"),
    re.compile(r"^\s*---\s*\n"),
]


def _strip_polish_preamble(text: str, expected_header: str | None = None) -> str:
    """Strip common LLM preambles ("以下是…", code fences, leading ---).

    Repeats until no known preamble pattern matches. If the first line isn't
    the expected topic header, prepend it back."""
    out = text
    changed = True
    while changed:
        changed = False
        for rx in _POLISH_PREAMBLE_RES:
            new = rx.sub("", out, count=1)
            if new != out:
                out = new
                changed = True
                break
    out = out.lstrip()
    if expected_header and not out.startswith(expected_header.rstrip()):
        out = expected_header.rstrip() + "\n\n" + out
    # Strip trailing code fence if claude wrapped the whole thing.
    out = re.sub(r"\n```\s*$", "", out)
    return out


_SPEC_SELFTEST_SYSTEM = (
    "You're a junior backend engineer about to start coding from the spec "
    "below. Your tooling is weak: codex CLI + deepseek-flash. Read every "
    "section, then list the top 5-10 concrete blockers you'd hit before "
    "you could write meaningful code. A blocker is: a missing decision, "
    "an ambiguous term, an implicit assumption only an insider would "
    "know, or an underspecified interface. Format strictly:\n"
    "- One bullet per blocker, ≤25 字 中文 per bullet.\n"
    "- End each bullet with the most relevant [#nnn] citation if there is "
    "one, otherwise omit it.\n"
    "- Skip nice-to-haves; focus on what literally blocks `npm i` to MVP.\n"
    "- No preamble like \"以下是\". First character of output is `-`."
)


def _append_self_test(spec_text: str, model: str = "sonnet") -> str:
    """Append a 「自检」section to the spec by asking the agent to find gaps.

    Runs ``claude --print`` once over the spec with the self-test prompt;
    inserts the result as a markdown section so the human can see what a
    weak downstream agent would trip over before actually handing off."""
    import subprocess
    proc = subprocess.run(
        ["claude", "--print", "--model", model,
         "--append-system-prompt", _SPEC_SELFTEST_SYSTEM, spec_text],
        capture_output=True, text=True, timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude returned {proc.returncode}: {proc.stderr[:300]}")
    report = (proc.stdout or "").strip()
    if not report:
        raise RuntimeError("claude returned empty report")
    # Strip the same wrappers the polish path handles.
    report = _strip_polish_preamble(report)
    section = (
        "\n\n## 自检 (gaps a weak agent would hit)\n\n"
        "> 由 `lets spec --self-test` 自动生成 — agent 站在弱开发者角度，"
        "列出他在动手前必须先问的问题。每条都是动手前需补的洞。\n\n"
        + report.rstrip() + "\n"
    )
    return spec_text.rstrip() + section


def _polish_spec(raw: str, model: str = "sonnet") -> str:
    """Run claude --print over the raw spec to add 设计目标 + 实施步骤.

    Uses --append-system-prompt so the polish instructions are stable and
    cache-friendly; the variable raw spec goes on stdin. Falls back to the
    raw spec on any failure (caller handles the exception)."""
    import subprocess
    proc = subprocess.run(
        ["claude", "--print", "--model", model,
         "--append-system-prompt", _SPEC_POLISH_SYSTEM, raw],
        capture_output=True, text=True, timeout=300,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude returned {proc.returncode}: {proc.stderr[:300]}")
    out = (proc.stdout or "").strip()
    if not out:
        raise RuntimeError("claude returned empty output")
    # Preserve the topic header — claude sometimes drops it when restructuring.
    header = raw.splitlines()[0] if raw else None
    cleaned = _strip_polish_preamble(out, expected_header=header)
    return cleaned + "\n"


def _render_spec_markdown(topic_id: int, msgs: list[dict]) -> str:
    """Back-compat shim — real implementation lives in ``app.spec``.

    Tests import ``gateway._render_spec_markdown`` directly; we keep the
    name so they don't break, but delegate to the shared module.
    """
    from app.spec import render_spec_markdown
    return render_spec_markdown(topic_id, msgs)


def _logout(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="lets logout")
    parser.parse_args(argv)
    token_path, token_json_path = _token_paths()
    removed = False
    for p in (token_path, token_json_path):
        if os.path.exists(p):
            os.remove(p)
            print(f"removed {p}")
            removed = True
    if not removed:
        print("not logged in (nothing to remove)")
    return 0


def _launchd_label() -> str:
    return "com.lets.gateway"


def _launchd_plist_path() -> str:
    return os.path.expanduser(
        f"~/Library/LaunchAgents/{_launchd_label()}.plist"
    )


def _log_paths(role: str | None = None) -> tuple[str, str]:
    home = os.path.expanduser(os.environ.get("LETS_HOME", "~/.lets"))
    log_dir = os.path.join(home, "logs")
    os.makedirs(log_dir, exist_ok=True)
    stem = f"gateway-{role}" if role else "gateway"
    return os.path.join(log_dir, f"{stem}.out.log"), os.path.join(log_dir, f"{stem}.err.log")


def _script_invocation() -> tuple[str, list[str], str]:
    """Return a concrete invocation for both repo and standalone installs."""
    script = str(Path(__file__).resolve())
    return sys.executable, [script], str(Path(script).parent)


def _install(argv: list[str]) -> int:
    """Write a launchd plist so the gateway auto-starts on login (macOS)."""
    parser = argparse.ArgumentParser(prog="lets install")
    parser.add_argument(
        "--host", default=None,
        help="Override --host for the daemon (default: from saved token.json)",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("LETS_MODEL"),
        help="Model to use on launchd autostart (claude only).",
    )
    args = parser.parse_args(argv)

    if sys.platform != "darwin":
        print(
            "lets install currently supports macOS (launchd) only. "
            "On Linux, add a systemd user unit by hand for now.",
            file=sys.stderr,
        )
        return 2

    token_path, _ = _token_paths()
    if not os.path.exists(token_path):
        print("not logged in. Run: lets login  first.", file=sys.stderr)
        return 1

    meta = _load_token_meta() or {}
    host = args.host or meta.get("host") or "http://127.0.0.1:8000"

    python_exec, argv_prefix, workdir = _script_invocation()
    home = os.path.expanduser(os.environ.get("LETS_HOME", "~/.lets"))
    out_log, err_log = _log_paths()
    run_args = [python_exec, *argv_prefix, "run", "--host", host]
    if args.model:
        run_args.extend(["--model", args.model])
    program_args = "\n".join(
        f"    <string>{arg}</string>"
        for arg in run_args
    )

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{_launchd_label()}</string>
  <key>ProgramArguments</key>
  <array>
{program_args}
  </array>
  <key>WorkingDirectory</key>
  <string>{workdir}</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key>
  <string>{out_log}</string>
  <key>StandardErrorPath</key>
  <string>{err_log}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>LETS_HOME</key>
    <string>{home}</string>
    <key>PATH</key>
    <string>{os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')}</string>
  </dict>
</dict>
</plist>
"""
    plist_path = _launchd_plist_path()
    os.makedirs(os.path.dirname(plist_path), exist_ok=True)
    with open(plist_path, "w", encoding="utf-8") as f:
        f.write(plist)
    print(f"wrote {plist_path}")

    # Reload: unload + load (ignore errors on first install)
    subprocess.run(
        ["launchctl", "unload", "-w", plist_path],
        capture_output=True, check=False,
    )
    res = subprocess.run(
        ["launchctl", "load", "-w", plist_path],
        capture_output=True, check=False, text=True,
    )
    if res.returncode != 0:
        print(f"launchctl load failed: {res.stderr.strip()}", file=sys.stderr)
        return res.returncode
    print(f"launchctl loaded {_launchd_label()} — gateway is running in the background and will run at login.")
    print(f"  out: {out_log}")
    print(f"  err: {err_log}")
    print("To check status now: launchctl list | grep lets")
    return 0


def _uninstall(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="lets uninstall")
    parser.parse_args(argv)
    plist_path = _launchd_plist_path()
    if not os.path.exists(plist_path):
        print("not installed (no plist at " + plist_path + ")")
        return 0
    subprocess.run(
        ["launchctl", "unload", "-w", plist_path],
        capture_output=True, check=False,
    )
    os.remove(plist_path)
    print(f"removed {plist_path} and unloaded {_launchd_label()}")
    return 0


def _spawn_background_for(role: str, host: str, extra: list[str]) -> int:
    python_exec, argv_prefix, workdir = _script_invocation()
    out_log, err_log = _log_paths(role=role)
    # `-u` keeps stdout/stderr unbuffered so the log file is useful while the
    # daemon is running (otherwise prints sit in Python's buffer forever).
    cmd = [
        python_exec, "-u", *argv_prefix, "run",
        "--host", host, "--agent", role,
        *extra,
    ]
    with open(out_log, "ab") as out, open(err_log, "ab") as err:
        proc = subprocess.Popen(
            cmd,
            cwd=workdir,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            start_new_session=True,
        )
    print(f"gateway[{role}] started in background (pid {proc.pid})")
    print(f"  out: {out_log}")
    print(f"  err: {err_log}")
    return proc.pid


def _start_background(argv: list[str]) -> int:
    """`lets gateway` — start background daemon(s).

    With `--agent <role>`: starts that single agent (singleton lock will
    take over any prior instance with the same agent_instance_id).
    With no `--agent`: starts every registered agent token.
    """
    parser = argparse.ArgumentParser(prog="lets gateway")
    parser.add_argument(
        "--host", default=None,
        help="Override host for the daemon (default: from saved token)",
    )
    parser.add_argument(
        "--agent", default=None,
        help="Role to start (claude / codex). Omit to start every registered agent.",
    )
    args, passthrough = parser.parse_known_args(argv)

    if args.agent:
        tok = _load_token_for_agent(args.agent)
        if not tok:
            print(
                f"no token for agent '{args.agent}'. Run: lets add {args.agent}",
                file=sys.stderr,
            )
            return 1
        host = args.host or tok.get("host") or os.environ.get("LETS_HOST", "http://127.0.0.1:8000")
        _spawn_background_for(args.agent, host, passthrough)
        return 0

    # No --agent: start every registered agent. Useful one-liner after a reboot.
    records = _list_agent_tokens()
    if not records:
        print("no agents registered. Run: lets add claude", file=sys.stderr)
        return 1
    for rec in records:
        role = rec.get("_role") or "claude"
        host = args.host or rec.get("host") or os.environ.get("LETS_HOST", "http://127.0.0.1:8000")
        _spawn_background_for(role, host, passthrough)
    return 0


def _add_agent(argv: list[str]) -> int:
    """`lets add <role>` — device-flow login for a new agent + background daemon.

    Combines the two-step flow (login → start gateway) into one command. Safe
    to re-run: re-authorizes the device and the singleton lock causes the new
    background daemon to replace any prior one for the same role.
    """
    parser = argparse.ArgumentParser(prog="lets add")
    parser.add_argument(
        "role",
        nargs="?",
        choices=["claude", "codex"],
        default="claude",
        help="Agent role to add (default: claude)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("LETS_HOST", "https://lets.up.railway.app"),
        help="Lets backend base URL",
    )
    parser.add_argument(
        "--device-label",
        default=os.environ.get("LETS_DEVICE_LABEL", socket.gethostname()),
        help="Human-readable device label",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Print the authorization URL but don't open a browser",
    )
    parser.add_argument(
        "--no-start",
        action="store_true",
        help="Just authorize; don't start the background gateway",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("LETS_MODEL"),
        help="Model to store/use for this agent (alias or full model id).",
    )
    parser.add_argument(
        "--workspace",
        default=os.environ.get("LETS_WORKSPACE"),
        help="Workspace slug to bind this agent to (default: caller's first workspace).",
    )
    args = parser.parse_args(argv)

    print(f"Adding agent: {args.role} on {args.device_label}")
    login_args = [
        "--host", args.host,
        "--role", args.role,
        "--device-label", args.device_label,
    ]
    if args.no_open:
        login_args.append("--no-open")
    if args.model:
        login_args.extend(["--model", args.model])
    if args.workspace:
        login_args.extend(["--workspace", args.workspace])
    rc = _login(login_args)
    if rc != 0:
        return rc

    if args.no_start:
        print(f"agent '{args.role}' registered. Start later with: lets gateway --agent {args.role}")
        return 0

    print()
    extra = ["--model", args.model] if args.model else []
    _spawn_background_for(args.role, args.host, extra)
    print()
    print(f"agent '{args.role}' is live. Manage with:")
    print(f"  lets gateway --agent {args.role}    # restart")
    print(f"  lets status                         # see all agents")
    return 0


def _singleton_lock_path(agent_instance_id: int) -> str:
    home = os.path.expanduser(os.environ.get("LETS_HOME", "~/.lets"))
    locks_dir = os.path.join(home, "locks")
    os.makedirs(locks_dir, exist_ok=True)
    return os.path.join(locks_dir, f"agent-{agent_instance_id}.lock")


def _pid_alive(pid: int) -> bool:
    if pid <= 1:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _acquire_singleton(agent_instance_id: int):
    """Acquire a per-agent_instance file lock; if another gateway already
    holds it, SIGTERM that process and take over. Returns the open file
    handle (caller keeps it alive). Returns None only if we couldn't
    dislodge the previous holder after several retries."""
    lock_path = _singleton_lock_path(agent_instance_id)
    # Open in r+ so concurrent processes share the same inode for flock.
    if not os.path.exists(lock_path):
        with open(lock_path, "w"):
            pass
    f = open(lock_path, "r+")
    for attempt in range(6):
        try:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            # Acquired — write our pid and return.
            f.seek(0)
            f.truncate()
            f.write(f"{os.getpid()}\n")
            f.flush()
            return f
        except BlockingIOError:
            # Someone else owns it. Identify them, SIGTERM, wait, retry.
            f.seek(0)
            content = f.read().strip()
            try:
                prev_pid = int(content.splitlines()[0]) if content else 0
            except ValueError:
                prev_pid = 0
            if attempt == 0 and prev_pid and prev_pid != os.getpid() and _pid_alive(prev_pid):
                print(
                    f"replacing previous gateway pid={prev_pid} for "
                    f"agent_instance_id={agent_instance_id}…"
                )
                try:
                    os.kill(prev_pid, signal.SIGTERM)
                except (ProcessLookupError, PermissionError):
                    pass
            time.sleep(0.5)
    f.close()
    return None


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("-h", "--help"):
        _print_main_help()
        return 0
    # Subcommand dispatch — kept additive so existing entry-points (bare
    # invocation, `run` subcommand) still work.
    if argv and argv[0] in ("login",):
        return _login(argv[1:])
    if argv and argv[0] in ("status",):
        return _status(argv[1:])
    if argv and argv[0] in ("logout",):
        return _logout(argv[1:])
    if argv and argv[0] in ("install",):
        return _install(argv[1:])
    if argv and argv[0] in ("uninstall",):
        return _uninstall(argv[1:])
    if argv and argv[0] in ("gateway",):
        return _start_background(argv[1:])
    if argv and argv[0] in ("add",):
        return _add_agent(argv[1:])
    if argv and argv[0] in ("leave",):
        return _leave_workspace(argv[1:])
    if argv and argv[0] in ("spec",):
        return _spec(argv[1:])
    if argv and argv[0] in ("topics",):
        return _topics(argv[1:])
    # "run" means foreground daemon for debugging/backward compatibility.
    if argv and argv[0] in ("run",):
        argv = argv[1:]

    parser = argparse.ArgumentParser(prog="lets run")
    parser.add_argument(
        "--token",
        default=os.environ.get("LETS_TOKEN"),
        help="Bearer token bound to an agent_instance (or set $LETS_TOKEN)",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("LETS_HOST", "http://127.0.0.1:8000"),
        help="Lets backend base URL",
    )
    parser.add_argument(
        "--cmd",
        default=None,
        help="Shell command for the local CLI agent. Default picks by role: "
             "claude → 'claude --print', codex → 'codex exec'. "
             "The prompt is appended as the last argument.",
    )
    parser.add_argument(
        "--poll-interval",
        type=float, default=3.0,
        help="Seconds between topic-stream polls (default 3.0)",
    )
    parser.add_argument(
        "--cli-timeout",
        type=int, default=240,
        help="Seconds to wait for the local CLI invocation (default 240). "
             "claude --print on the long discussion-partner prompts routinely "
             "takes 60-180s on a real conversation; 120 used to clip the tail.",
    )
    parser.add_argument(
        "--model",
        default=os.environ.get("LETS_MODEL"),
        help="Model alias to pass to the local CLI (haiku/sonnet/opus or full "
             "model id). When omitted, uses the web setting on this "
             "agent_instance, falling back to haiku.",
    )
    parser.add_argument(
        "--session-dir",
        default=os.environ.get("LETS_SESSION_DIR", _default_session_dir()),
        help="Directory for local CLI session metadata (default: ~/.lets/sessions)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the would-be CLI invocation but don't actually run it. "
             "Useful for testing the routing logic without burning CLI time.",
    )
    parser.add_argument(
        "--agent",
        default=None,
        help="Role to run (claude / codex). Picks the matching token from "
             "~/.lets/tokens/<role>.json; falls back to the legacy single "
             "token file when omitted.",
    )
    args = parser.parse_args(argv)
    args.persona = os.environ.get("LETS_PERSONA", "default")
    if args.persona not in ("default", "red", "blue"):
        args.persona = "default"

    if not args.token:
        # Prefer per-agent token if --agent was given; otherwise use the
        # legacy single-file slot (or LETS_TOKEN env).
        rec = _load_token_for_agent(args.agent)
        if rec and rec.get("token"):
            args.token = rec["token"]
            # Honor token's host if user didn't override.
            if args.host == "http://127.0.0.1:8000" and rec.get("host"):
                args.host = rec["host"]

    if not args.token:
        print(
            "Missing token. Run: lets add claude  (or set LETS_TOKEN)",
            file=sys.stderr,
        )
        return 2

    me = _wait_for_identity(args.host, args.token)
    print(
        f"connected as {me.role}:{me.device_label} "
        f"(human={me.human_name}, agent_instance_id={me.agent_instance_id})"
    )

    # Ensure only one gateway runs per agent_instance on this machine.
    # If a previous gateway is running, SIGTERM it and take over — this is
    # what users expect when they re-run `lets gateway` (or re-install).
    lock_handle = _acquire_singleton(me.agent_instance_id)
    if lock_handle is None:
        print(
            f"could not acquire singleton lock for agent_instance_id={me.agent_instance_id}. "
            f"Another gateway is wedged; kill it manually (ps -ef | grep gateway.py).",
            file=sys.stderr,
        )
        return 1

    custom_cmd = bool(args.cmd)
    if custom_cmd:
        cli_cmd = shlex.split(args.cmd)
    elif me.role == "claude":
        cli_cmd = ["claude", "--print"]
    elif me.role == "codex":
        cli_cmd = ["codex", "exec"]
    else:
        print(f"unknown role '{me.role}' — pass --cmd explicitly", file=sys.stderr)
        return 2
    model_source = "CLI/env" if args.model else "web setting"
    print(f"will invoke: {' '.join(cli_cmd)} <prompt> (model from {model_source})")

    last_seen_per_topic: dict[int, int] = {}
    # Cold-start: avoid replying to historical messages. Seed each topic's
    # cursor at its current max id.
    topics_snap = _list_topics(args.host, args.token)
    for t in topics_snap:
        last_id = int(t.get("last_message_id") or 0)
        last_seen_per_topic[int(t["id"])] = last_id
    print(
        f"seeded {len(last_seen_per_topic)} topic cursor(s) "
        f"(will respond to messages newer than current head)"
    )

    # Pending state: messages I haven't replied to yet.
    # Direct one-human/one-agent turns should feel like DM. Observer-mode turns
    # use a longer pause and only fire when recent human discussion is dense
    # enough that the agent likely has something useful to add.
    #   pending[tid] = { trigger_ids: list[int], last_msg_at: float,
    #                    urgent: bool, proactive: bool }
    pending: dict[int, dict] = {}
    QUIET_WINDOW_URGENT = 1.0
    QUIET_WINDOW_NORMAL = 6.0
    QUIET_WINDOW_PROACTIVE = 10.0

    while True:
        try:
            topics = _list_topics(args.host, args.token)
            topic_by_id = {int(t["id"]): t for t in topics}

            # ── Phase 1: poll for new messages and accumulate pending state ──
            for tid, t in topic_by_id.items():
                cur = last_seen_per_topic.get(tid, 0)
                new_msgs = _read_topic(args.host, args.token, tid, cur)
                if not new_msgs:
                    continue
                last_seen_per_topic[tid] = max(
                    last_seen_per_topic.get(tid, 0),
                    max(int(m["id"]) for m in new_msgs),
                )
                for m in new_msgs:
                    if (m.get("actor_type") == "agent"
                            and int(m.get("actor_id") or 0) == me.agent_instance_id):
                        continue  # own posts
                    addressed = _addressed_to_me(m, me.agent_instance_id, me.human_id)
                    proactive = False
                    if not addressed:
                        if m.get("actor_type") == "human" and m.get("type") == "chat":
                            try:
                                proactive = _should_proactively_join(
                                    _read_topic(args.host, args.token, tid, None),
                                    m,
                                    me.agent_instance_id,
                                )
                            except Exception as e:
                                print(f"  WARN: proactive check failed: {e}", file=sys.stderr)
                        if not proactive:
                            existing = pending.get(tid)
                            if (
                                existing
                                and existing.get("proactive")
                                and m.get("actor_type") == "human"
                                and m.get("type") == "chat"
                            ):
                                existing["trigger_ids"].append(int(m["id"]))
                                existing["last_msg_at"] = time.time()
                            continue
                    body_lc = (m.get("body") or "").lower()
                    urgent = addressed and (
                        "@" in body_lc or str(m.get("addressed_to") or "").startswith("agent:")
                    )
                    p = pending.setdefault(
                        tid,
                        {
                            "trigger_ids": [],
                            "last_msg_at": 0.0,
                            "urgent": False,
                            "proactive": proactive,
                        },
                    )
                    p["trigger_ids"].append(int(m["id"]))
                    p["last_msg_at"] = time.time()
                    p["proactive"] = p["proactive"] and proactive
                    if urgent:
                        p["urgent"] = True

            # ── Phase 2: fire on any topic that's been quiet long enough ──
            now = time.time()
            for tid in list(pending.keys()):
                p = pending[tid]
                if p.get("proactive") and not p["urgent"]:
                    window = QUIET_WINDOW_PROACTIVE
                else:
                    window = QUIET_WINDOW_URGENT if p["urgent"] else QUIET_WINDOW_NORMAL
                if now - p["last_msg_at"] < window:
                    continue  # still typing — wait

                t = topic_by_id.get(tid)
                if t is None:
                    pending.pop(tid)
                    continue

                trigger_ids = p["trigger_ids"]
                pending.pop(tid)  # consume before potentially long CLI call

                # Build prompt using the latest trigger message; the earlier
                # burst entries are already inside `recent` (last 8 messages).
                recent = _read_topic(args.host, args.token, tid, None)
                trigger = next((m for m in reversed(recent) if int(m["id"]) == trigger_ids[-1]), None)
                if trigger is None:
                    print(f"[topic {tid}] trigger msg {trigger_ids[-1]} vanished; skipping")
                    continue

                try:
                    me = _whoami(args.host, args.token)
                except Exception as e:
                    print(f"  WARN: failed to refresh agent settings: {e}", file=sys.stderr)
                effective_model = args.model or me.model or "haiku"
                effective_cli_cmd = _with_model(cli_cmd, me.role, effective_model)

                system_prompt, user_prompt = _build_prompt_split(
                    me=me,
                    topic_title=t.get("title", f"topic#{tid}"),
                    recent=recent,
                    trigger=trigger,
                    persona=args.persona,
                    intervention_mode="proactive" if p.get("proactive") else "direct",
                )
                print(
                    f"[topic {tid}] firing on {len(trigger_ids)} message(s) "
                    f"(burst {trigger_ids[0]}→{trigger_ids[-1]}, urgent={p['urgent']}, "
                    f"proactive={p.get('proactive', False)})"
                )

                # Post a "thinking" status so the human sees something happening
                # during the 30-60s LLM call. Stream.tsx auto-hides this once
                # the actual chat reply arrives (status + reply collapse to one
                # bubble, like WhatsApp's typing indicator).
                if not args.dry_run:
                    try:
                        _post(
                            args.host, args.token, tid, "status",
                            "思考中…",
                            phase="thinking",
                            cites=trigger_ids,
                        )
                    except Exception as e:
                        print(f"  (status post failed: {e})")

                if args.dry_run:
                    print(f"  DRY RUN — would run: {' '.join(effective_cli_cmd)}")
                    print(f"  system:\n{system_prompt}\n")
                    print(f"  user:\n{user_prompt}\n")
                    ok, output = True, "[dry-run] not actually invoked"
                elif custom_cmd:
                    # Custom CLI gets the legacy single-string prompt — we
                    # don't know if it supports a separate system prompt.
                    ok, output = _invoke_local_cli(
                        cli_cmd, system_prompt + "\n\n" + user_prompt, args.cli_timeout,
                    )
                else:
                    ok, output = _invoke_agent_turn(
                        cmd=effective_cli_cmd,
                        prompt=user_prompt,
                        timeout=args.cli_timeout,
                        me=me,
                        host=args.host,
                        topic_id=tid,
                        session_dir=args.session_dir,
                        trigger_message_id=trigger_ids[-1],
                        system_prompt=system_prompt,
                    )

                if ok:
                    chat_body, updates = _parse_pane_updates(output)
                    if not updates:
                        updates = _fallback_pane_updates(chat_body or output)
                    if not updates and output != chat_body:
                        updates = _fallback_pane_updates(output)
                    # Pull out headline (separate from the array fields the
                    # right pane consumes). It lives on the chat message
                    # metadata so the frontend's folded view can show it.
                    headline = None
                    if isinstance(updates.get("headline"), str):
                        headline = updates["headline"].strip()[:60] or None
                    chat_meta: dict[str, Any] = {"cites": trigger_ids}
                    if headline:
                        chat_meta["headline"] = headline
                    try:
                        chat_msg = _post(
                            args.host, args.token, tid, "chat",
                            chat_body or output,
                            **chat_meta,
                        )
                        chat_id = chat_msg.get("id") if isinstance(chat_msg, dict) else None
                        print(
                            f"  posted reply ({len(chat_body or output)} chars, "
                            f"cites={trigger_ids}"
                            f"{', headline=' + repr(headline) if headline else ''})"
                        )
                    except Exception as e:
                        print(f"  reply post failed: {e}")
                        chat_id = None
                    if updates:
                        try:
                            n = _post_pane_updates(
                                args.host, args.token, tid, updates, source_msg_id=chat_id,
                            )
                            print(f"  posted {n} pane update(s)")
                        except Exception as e:
                            print(f"  pane_updates post failed: {e}")
                else:
                    try:
                        _post(
                            args.host, args.token, tid, "finding",
                            output + " · ERROR",
                            cites=trigger_ids,
                        )
                        print(f"  posted error ({len(output)} chars)")
                    except Exception as e:
                        print(f"  reply post failed: {e}")
        except Exception as e:
            print(f"loop error: {e}", file=sys.stderr)
        time.sleep(args.poll_interval)


if __name__ == "__main__":
    sys.exit(main())
