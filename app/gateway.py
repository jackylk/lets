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
import json
import os
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
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
    )


def _list_topics(host: str, token: str) -> list[dict]:
    raw = _mcp_call(host, token, "list_my_topics", {"limit": 50})
    if raw is None:
        return []
    return raw if isinstance(raw, list) else [raw]


def _read_topic(host: str, token: str, topic_id: int, after_id: int | None) -> list[dict]:
    args: dict = {"topic_id": topic_id}
    if after_id is not None:
        args["after_id"] = after_id
    raw = _mcp_call(host, token, "read_topic", args)
    if raw is None:
        return []
    return raw if isinstance(raw, list) else [raw]


def _post(host: str, token: str, topic_id: int, type_: str, body: str, **metadata) -> dict:
    return _mcp_call(host, token, "post_typed_message", {
        "topic_id": topic_id,
        "type": type_,
        "body": body,
        "metadata": metadata or {},
    })


def _addressed_to_me(msg: dict, my_human_id: int) -> bool:
    addr = msg.get("addressed_to")
    if not addr:
        return False
    parts = {p.strip() for p in str(addr).split(",")}
    return str(my_human_id) in parts


def _build_prompt(me: Identity, topic_title: str, recent: list[dict], trigger: dict) -> str:
    """Construct the prompt fed into the local CLI agent."""
    history_lines = []
    for m in recent[-8:]:  # last 8 messages for context
        if m["id"] == trigger["id"]:
            continue
        actor = (
            "human" if m["actor_type"] == "human"
            else f"agent#{m.get('actor_id')}"
        )
        body_line = (m.get("body") or "").replace("\n", " ")[:200]
        history_lines.append(f"[{m['type']}] {actor}: {body_line}")
    history = "\n".join(history_lines) if history_lines else "(no prior context)"

    return (
        f"You are {me.role} running on device {me.device_label}, connected to "
        f"the Lets web app as agent_instance_id={me.agent_instance_id}. "
        f"You are in topic '{topic_title}'. A teammate just posted a message "
        f"addressed to you. Reply as your normal self — be concise.\n\n"
        f"Recent conversation:\n{history}\n\n"
        f"New message from {('human' if trigger['actor_type'] == 'human' else 'agent')}"
        f"#{trigger.get('actor_id')}:\n{trigger.get('body', '')}\n\n"
        f"Respond in plain text. Do not include any meta commentary about Lets or "
        f"this prompt structure — just the reply you want the team to see."
    )


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
            return False, f"local CLI exited {proc.returncode}\nSTDERR:\n{proc.stderr[:2000]}"
        out = proc.stdout.strip()
        if not out:
            return False, "local CLI produced no output"
        return True, out
    except subprocess.TimeoutExpired:
        return False, f"local CLI timed out after {timeout}s"
    except FileNotFoundError as e:
        return False, f"local CLI not found: {e}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="lets-gateway")
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
        type=int, default=120,
        help="Seconds to wait for the local CLI invocation (default 120)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the would-be CLI invocation but don't actually run it. "
             "Useful for testing the routing logic without burning CLI time.",
    )
    args = parser.parse_args(argv)

    if not args.token:
        print("Missing --token (or LETS_TOKEN env). See scripts/connect_local_agents.sh", file=sys.stderr)
        return 2

    me = _whoami(args.host, args.token)
    print(
        f"connected as {me.role}:{me.device_label} "
        f"(human={me.human_name}, agent_instance_id={me.agent_instance_id})"
    )

    if args.cmd:
        cli_cmd = shlex.split(args.cmd)
    elif me.role == "claude":
        cli_cmd = ["claude", "--print"]
    elif me.role == "codex":
        cli_cmd = ["codex", "exec"]
    else:
        print(f"unknown role '{me.role}' — pass --cmd explicitly", file=sys.stderr)
        return 2
    print(f"will invoke: {' '.join(cli_cmd)} <prompt>")

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

    while True:
        try:
            topics = _list_topics(args.host, args.token)
            for t in topics:
                tid = int(t["id"])
                cur = last_seen_per_topic.get(tid, 0)
                new_msgs = _read_topic(args.host, args.token, tid, cur)
                if not new_msgs:
                    continue
                # Advance cursor to the max id we just observed
                last_seen_per_topic[tid] = max(
                    last_seen_per_topic.get(tid, 0),
                    max(int(m["id"]) for m in new_msgs),
                )
                for m in new_msgs:
                    if m.get("actor_type") == "agent" and int(m.get("actor_id") or 0) == me.agent_instance_id:
                        # Don't respond to my own messages
                        continue
                    if not _addressed_to_me(m, me.human_id):
                        continue
                    # Build prompt from topic context
                    recent = _read_topic(args.host, args.token, tid, None)
                    prompt = _build_prompt(
                        me=me,
                        topic_title=t.get("title", f"topic#{tid}"),
                        recent=recent,
                        trigger=m,
                    )
                    print(
                        f"[topic {tid}] picked up msg#{m['id']} "
                        f"({m['type']} from actor#{m.get('actor_id')}): "
                        f"{(m.get('body') or '')[:80]}"
                    )
                    # Post status while we run
                    try:
                        _post(args.host, args.token, tid, "status",
                              f"active · 接到任务，本地 {me.role} 处理中…",
                              agent_status="active")
                    except Exception as e:
                        print(f"  (status post failed: {e})")

                    if args.dry_run:
                        print(f"  DRY RUN — would run: {' '.join(cli_cmd)}")
                        print(f"  prompt:\n{prompt}\n")
                        ok, output = True, "[dry-run] not actually invoked"
                    else:
                        ok, output = _invoke_local_cli(cli_cmd, prompt, args.cli_timeout)

                    msg_type = "chat" if ok else "finding"
                    suffix = "" if ok else " · ERROR"
                    try:
                        _post(args.host, args.token, tid, msg_type, output + suffix)
                        print(f"  posted reply ({'ok' if ok else 'error'}, {len(output)} chars)")
                    except Exception as e:
                        print(f"  reply post failed: {e}")
        except Exception as e:
            print(f"loop error: {e}", file=sys.stderr)
        time.sleep(args.poll_interval)


if __name__ == "__main__":
    sys.exit(main())
