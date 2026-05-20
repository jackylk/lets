# Track B: Network Transport Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Lets reachable from another machine. Switch the MCP server from local stdio to HTTP/SSE transport, add token-based auth to all sensitive HTTP + MCP endpoints, package the backend as a Docker image with a docker-compose deploy config.

**Architecture:** Token rows (`tokens` table) issued via a CLI command, stored as opaque random strings. FastAPI `Depends(get_current_principal)` resolves a Bearer token to `(human, agent_instance?)`. FastMCP `streamable-http` transport mounted as a sub-app under the same FastAPI process. Docker compose runs uvicorn on port 8000 + persists the SQLite DB in a volume.

**Tech Stack:** Python 3.13 · FastAPI · FastMCP (streamable-http transport) · SQLite · secrets module · Docker · docker-compose

**Prerequisite:** Track A is complete (commit `4f50cc7` or later on `track-a-schema`). The schema substrate (humans / agent_roles / agent_instances / events / messages) must exist.

---

## File Structure

**Created:**
- `app/auth.py` — `Token` model, `issue_token`, `revoke_token`, `verify_token`, FastAPI dependency `get_current_principal`
- `app/tokens_cli.py` — `python -m app.tokens_cli issue/list/revoke` CLI
- `Dockerfile` — Python 3.13-slim base, copies app + tests, runs uvicorn
- `docker-compose.yml` — Single service "lets-backend", volume for `lets.db`
- `.mcp.json.example` — Template config with URL placeholder for remote接入
- `tests/test_auth.py` — token issuance / verification / dependency / API protection
- `tests/test_mcp_http.py` — MCP over HTTP roundtrip with auth

**Modified:**
- `app/db.py` — add `tokens` table
- `app/main.py` — apply `Depends(get_current_principal)` to identity/messages/events endpoints; mount MCP streamable-http sub-app
- `app/mcp_server.py` — switch transport from stdio to streamable-http; resolve agent identity from token
- `README.md` — add deployment + remote-MCP section

---

## Conventions

- TDD strict: write failing test → run to confirm failure → implement minimal → run pass → commit
- One commit per task; commit messages match the plan
- Token strings: 32 hex chars (16 random bytes from `secrets.token_hex(16)`)
- Bearer scheme: `Authorization: Bearer lets_<token>` with `lets_` prefix for grep-ability
- Auth failure returns 401 with `{"detail": "missing or invalid token"}`
- Public endpoints (no auth): `/api/context`, `/`, `/mock` — health/static only

---

## Task 1: Add `tokens` table

**Files:** `app/db.py` (modify), `tests/test_auth.py` (create)

- [ ] **Step 1.1: Write failing tests**

Create `tests/test_auth.py`:
```python
def test_tokens_table_exists(temp_db):
    from app.db import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tokens'"
        ).fetchall()
    assert len(rows) == 1


def test_tokens_columns(temp_db):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(tokens)").fetchall()}
    expected = {
        "id", "value_hash", "human_id", "agent_instance_id",
        "label", "created_at", "last_used_at", "revoked_at",
    }
    assert expected.issubset(cols)


def test_tokens_value_hash_unique(temp_db):
    import sqlite3
    from app.db import connect
    with connect() as conn:
        conn.execute("INSERT INTO humans (name) VALUES ('Neo')")
        hid = conn.execute("SELECT id FROM humans WHERE name='Neo'").fetchone()["id"]
        conn.execute(
            "INSERT INTO tokens (value_hash, human_id) VALUES (?, ?)",
            ("hash_abc", hid),
        )
        try:
            conn.execute(
                "INSERT INTO tokens (value_hash, human_id) VALUES (?, ?)",
                ("hash_abc", hid),
            )
            assert False, "should raise IntegrityError"
        except sqlite3.IntegrityError:
            pass
```

- [ ] **Step 1.2: Run — expect 3 FAIL**

```bash
.venv/bin/pytest tests/test_auth.py -v
```

- [ ] **Step 1.3: Add tokens table**

In `app/db.py`'s `executescript`, after `agent_instances`:

```sql
CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    value_hash TEXT NOT NULL UNIQUE,
    human_id INTEGER NOT NULL,
    agent_instance_id INTEGER,
    label TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_used_at TEXT,
    revoked_at TEXT,
    FOREIGN KEY(human_id) REFERENCES humans(id),
    FOREIGN KEY(agent_instance_id) REFERENCES agent_instances(id)
);
CREATE INDEX IF NOT EXISTS idx_tokens_value_hash ON tokens(value_hash);
CREATE INDEX IF NOT EXISTS idx_tokens_human ON tokens(human_id);
```

- [ ] **Step 1.4: Run — expect 3 passed**

```bash
.venv/bin/pytest tests/test_auth.py -v
```

- [ ] **Step 1.5: Commit**

```bash
git add app/db.py tests/test_auth.py
git commit -m "feat(schema): add tokens table for bearer-token auth"
```

---

## Task 2: `app/auth.py` — issue / verify helpers

**Files:** `app/auth.py` (create), `tests/test_auth.py` (append)

- [ ] **Step 2.1: Append failing tests**

Append to `tests/test_auth.py`:
```python
def test_issue_token_returns_plaintext_and_id(temp_db):
    from app.auth import issue_token
    from app.identity import ensure_human
    hid = ensure_human("Neo")
    tok, tok_id = issue_token(human_id=hid, label="neo-mbp-claude")
    assert tok.startswith("lets_")
    assert len(tok) >= 32
    assert isinstance(tok_id, int)


def test_verify_token_returns_principal(temp_db):
    from app.auth import issue_token, verify_token
    from app.identity import ensure_human
    hid = ensure_human("Neo")
    tok, _ = issue_token(human_id=hid)
    principal = verify_token(tok)
    assert principal is not None
    assert principal["human_id"] == hid
    assert principal["agent_instance_id"] is None


def test_verify_token_with_agent_instance(temp_db):
    from app.auth import issue_token, verify_token
    from app.identity import ensure_human, ensure_agent_instance
    hid = ensure_human("Neo")
    iid = ensure_agent_instance(role="claude", human_id=hid, device_label="neo-mbp")
    tok, _ = issue_token(human_id=hid, agent_instance_id=iid)
    principal = verify_token(tok)
    assert principal["agent_instance_id"] == iid


def test_verify_token_rejects_unknown(temp_db):
    from app.auth import verify_token
    assert verify_token("lets_nonexistent_token") is None


def test_verify_token_rejects_revoked(temp_db):
    from app.auth import issue_token, verify_token, revoke_token
    from app.identity import ensure_human
    hid = ensure_human("Neo")
    tok, tok_id = issue_token(human_id=hid)
    revoke_token(tok_id)
    assert verify_token(tok) is None


def test_verify_token_updates_last_used_at(temp_db):
    from app.auth import issue_token, verify_token
    from app.db import connect
    from app.identity import ensure_human
    hid = ensure_human("Neo")
    tok, tok_id = issue_token(human_id=hid)
    with connect() as conn:
        before = conn.execute("SELECT last_used_at FROM tokens WHERE id=?", (tok_id,)).fetchone()["last_used_at"]
    assert before is None
    verify_token(tok)
    with connect() as conn:
        after = conn.execute("SELECT last_used_at FROM tokens WHERE id=?", (tok_id,)).fetchone()["last_used_at"]
    assert after is not None
```

- [ ] **Step 2.2: Run — expect 6 FAIL (import error)**

```bash
.venv/bin/pytest tests/test_auth.py -v
```

- [ ] **Step 2.3: Create `app/auth.py`**

```python
from __future__ import annotations

import hashlib
import secrets
from typing import Optional

from .db import connect


TOKEN_PREFIX = "lets_"


def _hash_token(plaintext: str) -> str:
    """SHA-256 of the plaintext token. We never store the plaintext."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def issue_token(
    human_id: int,
    agent_instance_id: Optional[int] = None,
    label: Optional[str] = None,
) -> tuple[str, int]:
    """Mint a new token. Returns (plaintext, token_id). Plaintext is returned
    once and never recoverable from the DB."""
    plaintext = TOKEN_PREFIX + secrets.token_hex(16)
    value_hash = _hash_token(plaintext)
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO tokens (value_hash, human_id, agent_instance_id, label)
            VALUES (?, ?, ?, ?)
            """,
            (value_hash, human_id, agent_instance_id, label),
        )
        return plaintext, int(cursor.lastrowid)


def verify_token(plaintext: str) -> Optional[dict]:
    """Return principal dict {human_id, agent_instance_id, token_id} or None.
    Side-effect: updates last_used_at on success."""
    if not plaintext or not plaintext.startswith(TOKEN_PREFIX):
        return None
    value_hash = _hash_token(plaintext)
    with connect() as conn:
        row = conn.execute(
            """
            SELECT id, human_id, agent_instance_id, revoked_at
            FROM tokens
            WHERE value_hash = ?
            """,
            (value_hash,),
        ).fetchone()
        if not row or row["revoked_at"] is not None:
            return None
        conn.execute(
            "UPDATE tokens SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?",
            (row["id"],),
        )
        return {
            "token_id": int(row["id"]),
            "human_id": int(row["human_id"]),
            "agent_instance_id": (int(row["agent_instance_id"])
                                  if row["agent_instance_id"] is not None else None),
        }


def revoke_token(token_id: int) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE tokens SET revoked_at = CURRENT_TIMESTAMP WHERE id = ?",
            (token_id,),
        )


def list_tokens(human_id: Optional[int] = None) -> list[dict]:
    """Return all tokens (excluding value_hash) for an admin/CLI."""
    sql = (
        "SELECT id, human_id, agent_instance_id, label, created_at, "
        "last_used_at, revoked_at FROM tokens"
    )
    params: list = []
    if human_id is not None:
        sql += " WHERE human_id = ?"
        params.append(human_id)
    sql += " ORDER BY created_at DESC"
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
```

- [ ] **Step 2.4: Run — expect 9 passed (3 schema + 6 helper)**

```bash
.venv/bin/pytest tests/test_auth.py -v
```

- [ ] **Step 2.5: Commit**

```bash
git add app/auth.py tests/test_auth.py
git commit -m "feat(auth): add token issue/verify/revoke helpers with sha256 hash storage"
```

---

## Task 3: FastAPI `get_current_principal` dependency

**Files:** `app/auth.py` (extend), `tests/test_auth.py` (append)

- [ ] **Step 3.1: Append failing tests**

Append to `tests/test_auth.py`:
```python
def test_get_current_principal_valid_token(temp_db):
    from app.auth import issue_token, get_current_principal
    from app.identity import ensure_human
    hid = ensure_human("Neo")
    tok, _ = issue_token(human_id=hid)
    # Simulate dependency call manually
    p = get_current_principal(authorization=f"Bearer {tok}")
    assert p["human_id"] == hid


def test_get_current_principal_missing_header(temp_db):
    import pytest
    from fastapi import HTTPException
    from app.auth import get_current_principal
    with pytest.raises(HTTPException) as exc:
        get_current_principal(authorization=None)
    assert exc.value.status_code == 401


def test_get_current_principal_bad_scheme(temp_db):
    import pytest
    from fastapi import HTTPException
    from app.auth import get_current_principal
    with pytest.raises(HTTPException) as exc:
        get_current_principal(authorization="Basic abc")
    assert exc.value.status_code == 401


def test_get_current_principal_invalid_token(temp_db):
    import pytest
    from fastapi import HTTPException
    from app.auth import get_current_principal
    with pytest.raises(HTTPException) as exc:
        get_current_principal(authorization="Bearer lets_bogus")
    assert exc.value.status_code == 401
```

- [ ] **Step 3.2: Run — expect 4 FAIL**

```bash
.venv/bin/pytest tests/test_auth.py -v
```

- [ ] **Step 3.3: Add dependency to `app/auth.py`**

Append to `app/auth.py`:
```python
from fastapi import Header, HTTPException


def get_current_principal(
    authorization: Optional[str] = Header(default=None),
) -> dict:
    """FastAPI dependency: extract Bearer token, verify, return principal dict.
    Raises 401 on missing/invalid/revoked token."""
    if not authorization:
        raise HTTPException(status_code=401, detail="missing or invalid token")
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="missing or invalid token")
    principal = verify_token(parts[1].strip())
    if principal is None:
        raise HTTPException(status_code=401, detail="missing or invalid token")
    return principal
```

- [ ] **Step 3.4: Run — expect 13 passed**

```bash
.venv/bin/pytest tests/test_auth.py -v
```

- [ ] **Step 3.5: Commit**

```bash
git add app/auth.py tests/test_auth.py
git commit -m "feat(auth): add FastAPI Bearer-token dependency get_current_principal"
```

---

## Task 4: Token issuance CLI

**Files:** `app/tokens_cli.py` (create), `tests/test_auth.py` (append)

- [ ] **Step 4.1: Append test**

Append to `tests/test_auth.py`:
```python
def test_cli_issue_creates_token(temp_db, capsys):
    from app.identity import ensure_human
    hid = ensure_human("Neo")
    from app.tokens_cli import cli_issue
    cli_issue(human="Neo", role=None, device=None, label="ci-test")
    captured = capsys.readouterr()
    # First line should be the plaintext token
    assert "lets_" in captured.out
    # Token must exist for Neo
    from app.auth import list_tokens
    tokens = list_tokens(human_id=hid)
    assert len(tokens) == 1
    assert tokens[0]["label"] == "ci-test"


def test_cli_issue_with_role_and_device(temp_db, capsys):
    from app.identity import ensure_human
    hid = ensure_human("Neo")
    from app.tokens_cli import cli_issue
    cli_issue(human="Neo", role="claude", device="neo-mbp", label=None)
    from app.auth import list_tokens
    tokens = list_tokens(human_id=hid)
    assert tokens[0]["agent_instance_id"] is not None
```

- [ ] **Step 4.2: Run — expect 2 FAIL**

```bash
.venv/bin/pytest tests/test_auth.py -v
```

- [ ] **Step 4.3: Create CLI**

Create `app/tokens_cli.py`:
```python
"""Token issuance CLI. Usage:

    python -m app.tokens_cli issue --human Neo
    python -m app.tokens_cli issue --human Neo --role claude --device neo-mbp
    python -m app.tokens_cli list --human Neo
    python -m app.tokens_cli revoke --id 5
"""
from __future__ import annotations

import argparse
import sys
from typing import Optional

from .auth import issue_token, list_tokens, revoke_token
from .db import init_db
from .identity import ensure_human, ensure_agent_instance


def cli_issue(human: str, role: Optional[str], device: Optional[str], label: Optional[str]) -> None:
    hid = ensure_human(human)
    aid: Optional[int] = None
    if role and device:
        aid = ensure_agent_instance(role=role, human_id=hid, device_label=device)
    plaintext, tid = issue_token(human_id=hid, agent_instance_id=aid, label=label)
    # Print plaintext FIRST so the user sees it; never stored anywhere.
    print(plaintext)
    print(f"token_id={tid} human={human} role={role or '-'} device={device or '-'} label={label or '-'}",
          file=sys.stderr)


def cli_list(human: Optional[str]) -> None:
    hid: Optional[int] = None
    if human:
        hid = ensure_human(human)
    for t in list_tokens(human_id=hid):
        revoked = "(revoked)" if t["revoked_at"] else ""
        print(f"#{t['id']:>4}  human={t['human_id']}  ai={t['agent_instance_id'] or '-':<4}  "
              f"label={t['label'] or '-':<24}  last_used={t['last_used_at'] or 'never':<20}  {revoked}")


def cli_revoke(token_id: int) -> None:
    revoke_token(token_id)
    print(f"revoked token #{token_id}")


def main(argv: Optional[list[str]] = None) -> int:
    init_db()
    parser = argparse.ArgumentParser(prog="lets-tokens")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_issue = sub.add_parser("issue")
    p_issue.add_argument("--human", required=True)
    p_issue.add_argument("--role", default=None)
    p_issue.add_argument("--device", default=None)
    p_issue.add_argument("--label", default=None)

    p_list = sub.add_parser("list")
    p_list.add_argument("--human", default=None)

    p_rev = sub.add_parser("revoke")
    p_rev.add_argument("--id", type=int, required=True)

    args = parser.parse_args(argv)
    if args.cmd == "issue":
        cli_issue(args.human, args.role, args.device, args.label)
    elif args.cmd == "list":
        cli_list(args.human)
    elif args.cmd == "revoke":
        cli_revoke(args.id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4.4: Run — expect 15 passed**

```bash
.venv/bin/pytest tests/test_auth.py -v
```

- [ ] **Step 4.5: Smoke the CLI manually**

```bash
.venv/bin/python -m app.tokens_cli issue --human admin --label smoke-test
```
Expected: prints a `lets_...` token on stdout + an info line on stderr.

- [ ] **Step 4.6: Commit**

```bash
git add app/tokens_cli.py tests/test_auth.py
git commit -m "feat(auth): tokens CLI (issue/list/revoke)"
```

---

## Task 5: Protect HTTP endpoints with auth

**Files:** `app/main.py` (modify), `tests/test_auth.py` (append)

- [ ] **Step 5.1: Append failing tests**

Append to `tests/test_auth.py`:
```python
def _auth_header(client):
    """Helper: issue a token via direct DB ops, return Bearer header."""
    from app.identity import ensure_human
    from app.auth import issue_token
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="test")
    return {"Authorization": f"Bearer {tok}"}


def test_messages_requires_auth(client):
    # Create a topic first via raw DB (no auth needed for that path)
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('t1','T1')")
        topic_id = cursor.lastrowid

    r = client.post("/api/messages", json={
        "topic_id": topic_id, "type": "chat",
        "actor_type": "human", "actor_id": 1, "body": "hi",
    })
    assert r.status_code == 401


def test_messages_with_valid_token_works(client):
    headers = _auth_header(client)
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('t2','T2')")
        topic_id = cursor.lastrowid
    r = client.post("/api/messages", headers=headers, json={
        "topic_id": topic_id, "type": "chat",
        "actor_type": "human", "actor_id": 1, "body": "hi",
    })
    assert r.status_code == 200


def test_events_post_requires_auth(client):
    r = client.post("/api/events", json={
        "event_type": "t", "actor_type": "human", "actor_id": 1,
        "target_type": "x", "target_id": 1, "payload": {},
    })
    assert r.status_code == 401


def test_identity_me_does_not_require_token(client):
    # /api/identity/me is the bootstrap path — uses X-Lets-Human header, not Bearer
    r = client.get("/api/identity/me", headers={"X-Lets-Human": "Neo"})
    assert r.status_code == 200


def test_context_is_public(client):
    r = client.get("/api/context")
    assert r.status_code == 200
```

- [ ] **Step 5.2: Run — expect 4 FAIL (3 should-be-401-but-are-200 + 1 should-be-200-but-might-fail-too)**

```bash
.venv/bin/pytest tests/test_auth.py -v
```

- [ ] **Step 5.3: Apply auth dependency to sensitive endpoints**

In `app/main.py`, add to imports:
```python
from .auth import get_current_principal
```

Then, for each of these endpoints, add a `principal: dict = Depends(get_current_principal)` parameter (FastAPI import `Depends` from `fastapi` if not already):

- `POST /api/messages`
- `GET /api/topics/{topic_id}/messages`
- `POST /api/events`
- `GET /api/events`

Example for `post_message_endpoint`:
```python
from fastapi import Depends

@app.post("/api/messages")
def post_message_endpoint(
    payload: MessageCreate,
    principal: dict = Depends(get_current_principal),
) -> dict:
    ...
```

**Do NOT add auth to:**
- `GET /api/context` (public)
- `GET /` (serves index.html)
- `GET /mock` (serves mock.html)
- `GET /api/identity/me` (bootstrap; uses X-Lets-Human header instead)

For now, leave the legacy v1 endpoints (`/api/work-items`, `/api/status`, etc.) unprotected — Track C will revisit them when projects/members exist.

- [ ] **Step 5.4: Run — expect all auth tests pass**

```bash
.venv/bin/pytest tests/test_auth.py -v
.venv/bin/pytest -v
```

Full suite should still be green. **If pre-existing tests start failing with 401**, they need auth headers — extend the affected tests with `_auth_header(client)` or its equivalent. Specifically the e2e test in `tests/test_e2e_ppt_scenario.py` will need auth headers; update it accordingly.

- [ ] **Step 5.5: Update e2e test with auth headers**

Modify `tests/test_e2e_ppt_scenario.py` to use auth for `POST /api/messages` and `GET /api/topics/.../messages`:
```python
def test_ppt_scenario_end_to_end(client):
    # Bootstrap auth (admin token)
    from app.identity import ensure_human
    from app.auth import issue_token
    admin_hid = ensure_human("admin")
    admin_tok, _ = issue_token(human_id=admin_hid, label="e2e-test")
    auth = {"Authorization": f"Bearer {admin_tok}"}

    # ... rest of test, adding `headers=auth` to every client.post("/api/messages", ...)
    # and client.get("/api/topics/{id}/messages") call
```

(The same applies to `tests/test_messages.py` if any of its tests use the protected endpoints.)

- [ ] **Step 5.6: Run full suite green**

```bash
.venv/bin/pytest -v
```

- [ ] **Step 5.7: Commit**

```bash
git add app/main.py tests/test_auth.py tests/test_e2e_ppt_scenario.py tests/test_messages.py
git commit -m "feat(auth): require Bearer token on /api/messages, /api/events sensitive routes"
```

---

## Task 6: Switch MCP server to streamable-http transport

**Files:** `app/mcp_server.py` (modify), `app/main.py` (modify), `tests/test_mcp_http.py` (create)

The current `app/mcp_server.py` calls `mcp.run()` which uses stdio. FastMCP 2.x supports `transport="streamable-http"` exposing the MCP protocol over HTTP. We mount the resulting ASGI app as a sub-app under FastAPI so users hit `http://<host>:8000/mcp` with a Bearer token.

- [ ] **Step 6.1: Add failing test for HTTP transport mount**

Create `tests/test_mcp_http.py`:
```python
def test_mcp_endpoint_mounted(client):
    """The MCP streamable-http endpoint should be reachable under /mcp."""
    # MCP protocol uses POST with JSON-RPC; a GET to the endpoint may 405 or 404
    # depending on FastMCP. We just want to assert the route is mounted.
    r = client.get("/mcp/")
    # Either 200 (some endpoint) or 405 (method not allowed) means it's mounted.
    # 404 means not mounted.
    assert r.status_code != 404, f"MCP endpoint not mounted; got 404"


def test_mcp_endpoint_requires_auth(client):
    """MCP POST without Bearer should be 401."""
    r = client.post("/mcp/", json={
        "jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}
    })
    assert r.status_code in (401, 403)


def test_mcp_tools_list_with_auth(client):
    """With valid Bearer, MCP tools/list should return our registered tools."""
    from app.identity import ensure_human
    from app.auth import issue_token
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="mcp-test")
    r = client.post(
        "/mcp/",
        headers={
            "Authorization": f"Bearer {tok}",
            "Accept": "application/json, text/event-stream",
        },
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    )
    assert r.status_code == 200
    # FastMCP may return SSE or JSON; either way the body should mention "tools"
    assert "tools" in r.text or "result" in r.text
```

- [ ] **Step 6.2: Run — expect FAIL with 404**

```bash
.venv/bin/pytest tests/test_mcp_http.py -v
```

- [ ] **Step 6.3: Mount MCP HTTP app**

In `app/mcp_server.py`, after the existing tool definitions, add:
```python
def get_http_app():
    """Return an ASGI app for FastMCP's streamable-http transport, to be
    mounted under FastAPI."""
    init_db()
    # FastMCP 2.x: streamable_http_app() returns an ASGI app
    return mcp.streamable_http_app()
```

Replace the `def main()` body (which currently does `mcp.run()` stdio):
```python
def main() -> None:
    """Stand-alone stdio entry, kept for backward compatibility with old .mcp.json."""
    init_db()
    mcp.run()
```

In `app/main.py`, near the top after imports + before route definitions, add:
```python
from .mcp_server import mcp as _mcp_instance


# Mount MCP streamable-http endpoint at /mcp
_mcp_http = _mcp_instance.streamable_http_app()
app.mount("/mcp", _mcp_http)
```

**Note for implementer:** if `streamable_http_app` is the wrong method name for the installed FastMCP version, check `dir(mcp)` for the right one (it may be `http_app()`, `streamable_http()`, or similar). The point is to obtain an ASGI app from the FastMCP instance and mount it.

- [ ] **Step 6.4: Run — first two tests should pass (mounted + 401 without auth)**

The third test (with auth) requires Task 7's MCP auth bridge. Will fail until Task 7. Acceptable to commit Task 6 with 2 of 3 passing if test_mcp_tools_list_with_auth is marked `@pytest.mark.xfail(reason="auth bridge in Task 7")`.

```bash
.venv/bin/pytest tests/test_mcp_http.py -v
```

- [ ] **Step 6.5: Commit**

```bash
git add app/mcp_server.py app/main.py tests/test_mcp_http.py
git commit -m "feat(mcp): mount MCP streamable-http endpoint under FastAPI /mcp"
```

---

## Task 7: MCP token auth bridge

**Files:** `app/mcp_server.py` (modify), `app/main.py` (modify), `tests/test_mcp_http.py` (update)

FastMCP doesn't natively know about Bearer tokens. We wrap the mounted MCP ASGI app with a middleware that verifies `Authorization: Bearer ...` and rejects unauthenticated requests at the HTTP layer.

- [ ] **Step 7.1: Remove xfail from Task 6's tests**

In `tests/test_mcp_http.py`, ensure `test_mcp_tools_list_with_auth` no longer has `@pytest.mark.xfail`.

- [ ] **Step 7.2: Run — expect that test FAIL**

```bash
.venv/bin/pytest tests/test_mcp_http.py::test_mcp_tools_list_with_auth -v
```

- [ ] **Step 7.3: Add auth wrapper**

In `app/main.py`, replace the existing `app.mount("/mcp", _mcp_http)` with an auth-wrapped version:

```python
from starlette.types import ASGIApp, Receive, Scope, Send
from .auth import verify_token


class BearerAuthMiddleware:
    """Strict ASGI middleware: rejects non-Bearer or invalid-token requests."""
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        # Find Authorization header (case-insensitive)
        headers = dict((k.decode().lower(), v.decode()) for k, v in scope.get("headers", []))
        auth = headers.get("authorization", "")
        parts = auth.split(" ", 1)
        if len(parts) != 2 or parts[0].lower() != "bearer" or verify_token(parts[1].strip()) is None:
            await send({"type": "http.response.start", "status": 401,
                        "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body",
                        "body": b'{"detail":"missing or invalid token"}'})
            return
        await self.app(scope, receive, send)


app.mount("/mcp", BearerAuthMiddleware(_mcp_http))
```

- [ ] **Step 7.4: Run — all 3 MCP tests pass**

```bash
.venv/bin/pytest tests/test_mcp_http.py -v
```

- [ ] **Step 7.5: Run full suite**

```bash
.venv/bin/pytest -v
```

All tests should pass.

- [ ] **Step 7.6: Commit**

```bash
git add app/main.py tests/test_mcp_http.py
git commit -m "feat(mcp): bearer-token middleware on /mcp endpoint"
```

---

## Task 8: `.mcp.json.example` template + remove stdio default

**Files:** `.mcp.json.example` (create), `app/mcp_server.py` (cleanup comment)

- [ ] **Step 8.1: Create the example template**

Create `.mcp.json.example`:
```json
{
  "mcpServers": {
    "lets": {
      "type": "http",
      "url": "https://lets.example.com/mcp/",
      "headers": {
        "Authorization": "Bearer lets_REPLACE_WITH_YOUR_TOKEN"
      }
    }
  }
}
```

- [ ] **Step 8.2: Update root .mcp.json to use HTTP locally**

The existing `/Users/jacky/code/Lets/.mcp.json` currently runs the stdio server. Keep stdio as a fallback but add an HTTP option commented out — or do you want to switch the default? For v1.5a, **switch the default to HTTP** so the very repo dogfoods remote access:

Read the current `.mcp.json`, replace the `lets` server config with:
```json
{
  "mcpServers": {
    "lets": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp/",
      "headers": {
        "Authorization": "Bearer lets_REPLACE_WITH_LOCAL_TOKEN"
      }
    }
  }
}
```

Add a comment in `.mcp.json.example` (or a sibling `LOCAL_DEV.md`) noting that `lets_REPLACE_WITH_LOCAL_TOKEN` must be replaced with the output of `.venv/bin/python -m app.tokens_cli issue --human admin --label local-dev`.

- [ ] **Step 8.3: Commit**

```bash
git add .mcp.json .mcp.json.example
git commit -m "feat(mcp): switch .mcp.json to HTTP transport + add example template"
```

---

## Task 9: Dockerfile

**Files:** `Dockerfile` (create), `.dockerignore` (create)

- [ ] **Step 9.1: Write Dockerfile**

Create `Dockerfile`:
```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system deps (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY app/ ./app/
COPY web/ ./web/

# DB lives in /data (mounted volume)
ENV LETS_DB_PATH=/data/lets.db
VOLUME ["/data"]

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 9.2: Create .dockerignore**

Create `.dockerignore`:
```
.venv/
__pycache__/
*.pyc
.git/
.gitignore
tests/
docs/
mock-*.png
v[0-9]*.png
*.db
.playwright-mcp/
.DS_Store
README.md
```

- [ ] **Step 9.3: Make `DB_PATH` honor env var**

Modify `app/db.py`:
```python
import os
from pathlib import Path

_default = Path(__file__).resolve().parent.parent / "lets.db"
DB_PATH = Path(os.environ.get("LETS_DB_PATH", str(_default)))
```

(Replace the existing `DB_PATH = Path(...).parent.parent / "lets.db"` assignment.)

- [ ] **Step 9.4: Build image and smoke**

```bash
docker build -t lets:dev .
docker run --rm -d -p 8001:8000 -v lets_data:/data --name lets-smoke lets:dev
sleep 2
curl -s http://127.0.0.1:8001/api/context
docker stop lets-smoke
```

Expected: `{"project":{"name":"Lets",...}}`.

If Docker is not available in the implementer's environment, skip the smoke step and report DONE_WITH_CONCERNS noting which build step couldn't be exercised; the Dockerfile should still be reviewed for correctness.

- [ ] **Step 9.5: Commit**

```bash
git add Dockerfile .dockerignore app/db.py
git commit -m "feat(deploy): Dockerfile + env-controlled DB_PATH"
```

---

## Task 10: docker-compose.yml

**Files:** `docker-compose.yml` (create)

- [ ] **Step 10.1: Write compose file**

Create `docker-compose.yml`:
```yaml
services:
  lets-backend:
    build: .
    image: lets:dev
    container_name: lets-backend
    ports:
      - "8000:8000"
    volumes:
      - lets-data:/data
    environment:
      - LETS_DB_PATH=/data/lets.db
    restart: unless-stopped

volumes:
  lets-data:
```

- [ ] **Step 10.2: Smoke**

```bash
docker compose up -d
sleep 3
curl -s http://127.0.0.1:8000/api/context
docker compose down
```

Expected: `{"project":{"name":"Lets",...}}`.

(Skip if Docker not available; report.)

- [ ] **Step 10.3: Commit**

```bash
git add docker-compose.yml
git commit -m "feat(deploy): docker-compose single-service config"
```

---

## Task 11: README — deployment + remote MCP section

**Files:** `README.md` (modify)

- [ ] **Step 11.1: Append section**

Append to `README.md` (after the v1.5 Schema section):

```markdown
## v1.5 Deploy (Track B)

### Local dev

```bash
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Container

```bash
docker compose up -d
```

The DB persists in the named volume `lets-data`.

### Issue a token for a remote agent

```bash
.venv/bin/python -m app.tokens_cli issue --human Neo --role claude --device neo-mbp --label work-laptop
```

The CLI prints the plaintext token once. Paste it into the remote agent's `.mcp.json`:

```json
{
  "mcpServers": {
    "lets": {
      "type": "http",
      "url": "https://your-lets-host/mcp/",
      "headers": { "Authorization": "Bearer lets_..." }
    }
  }
}
```

### Public endpoints (no auth)

`GET /` `GET /mock` `GET /api/context` `GET /api/identity/me`

### Auth-required endpoints

All other `/api/...` routes and the `/mcp/` MCP endpoint require `Authorization: Bearer lets_...`.
```

- [ ] **Step 11.2: Commit**

```bash
git add README.md
git commit -m "docs: README section for v1.5 deploy + remote MCP"
```

---

## Task 12: Integration test — remote MCP via HTTP (smoke)

**Files:** `tests/test_mcp_http.py` (append)

Verify a remote-style call sequence end-to-end: issue token → call MCP `tools/list` → call a tool that needs DB access.

- [ ] **Step 12.1: Append integration test**

Append to `tests/test_mcp_http.py`:
```python
def test_mcp_remote_workflow(client):
    """Simulate a remote agent: issue token, call tools/list, call a tool."""
    from app.identity import ensure_human
    from app.auth import issue_token
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="integration")
    headers = {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/json, text/event-stream",
    }

    # List tools
    r = client.post(
        "/mcp/",
        headers=headers,
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    )
    assert r.status_code == 200
    # Body should contain at least one of our registered tool names
    body = r.text
    assert "get_project_context" in body or "list_work_items" in body

    # Call get_project_context tool
    r2 = client.post(
        "/mcp/",
        headers=headers,
        json={
            "jsonrpc": "2.0", "id": 2,
            "method": "tools/call",
            "params": {"name": "get_project_context", "arguments": {}},
        },
    )
    assert r2.status_code == 200
    assert "Lets" in r2.text
```

- [ ] **Step 12.2: Run**

```bash
.venv/bin/pytest tests/test_mcp_http.py::test_mcp_remote_workflow -v
```

Expected: PASS. If it doesn't, the most likely cause is FastMCP version differences in `streamable_http_app` semantics — investigate `dir(mcp_instance)`.

- [ ] **Step 12.3: Full suite green**

```bash
.venv/bin/pytest -v
```

- [ ] **Step 12.4: Commit**

```bash
git add tests/test_mcp_http.py
git commit -m "test(mcp): integration test for remote token + tools/list + tools/call"
```

---

## Self-Review Summary

**Spec coverage:**
- ✅ HTTP MCP transport — Task 6
- ✅ Token-based auth on HTTP endpoints — Task 5
- ✅ Token-based auth on MCP — Task 7
- ✅ Token CLI — Task 4
- ✅ Docker image — Task 9
- ✅ docker-compose — Task 10
- ✅ README deployment section — Task 11
- ✅ End-to-end remote-MCP test — Task 12

**Placeholder scan:** all code blocks complete; all tests have real assertions; no "TBD".

**Type consistency:** Bearer token format `lets_<32 hex>` referenced consistently across `app/auth.py`, tests, CLI, .mcp.json template.

**Known gaps deferred:**
- Token revocation UI/endpoint — CLI only for v1.5a; web UI in v1.5b
- Multi-tenant role-based access control — Track C territory (project membership)
- Rate limiting — out of scope for v1.5a
- Token rotation / TTL — not in v1.5 plan; tokens live until manually revoked

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-19-track-b-network-transport.md`.**

Recommended execution: `superpowers:subagent-driven-development`. Tasks 1-5 are sequential (each touches `app/auth.py` or `app/main.py`). Tasks 6-7 are the MCP migration. Tasks 8-12 are independent of each other and can be parallelized if you have multiple workers.

**Dependency on Track A:** schema substrate must be merged into `master` (or a working branch that contains it) before this track starts. The `tokens` table references `humans(id)` and `agent_instances(id)`.

**Branch suggestion:** `track-b-network` off the latest `track-a-schema` HEAD.
