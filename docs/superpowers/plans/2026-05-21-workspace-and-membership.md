# Workspace + Membership + Invite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the flat "topics" sidebar into per-workspace groupings with first-class agent membership and magic-link invites, while preserving the new-user "open-and-chat" experience.

**Architecture:** Rename `projects` → `workspaces` (no real users, so we do a clean schema rewrite via `init_db()` — no migration scripts). Add `workspace_members` (humans only) and `workspace_invites` (magic-link tokens). `agent_instances` gets a NOT NULL `workspace_id` column — agents become first-class workspace members alongside humans. All workspace/topic APIs gain a `require_workspace_member` guard. First-login auto-creates `my-workspace-<human_id>` + `主频道` topic so users land directly in chat. Magic-link invites generate `/join/:token` URLs; clicking → login → idempotent accept → land in workspace.

**Tech Stack:** Python 3.13 · FastAPI · Postgres (psycopg) · pytest · React 18 · TypeScript · Vitest · TanStack Query

**Spec:** `docs/superpowers/specs/2026-05-21-workspace-and-membership-design.md`

---

## File Structure

**Created:**
- `app/workspaces.py` — workspace + member + invite helpers (slug gen, create, ensure_default_for_human, generate_invite_token, accept_invite)
- `tests/test_workspaces_schema.py`
- `tests/test_workspaces_api.py`
- `tests/test_workspace_members_api.py`
- `tests/test_workspace_invites_api.py`
- `tests/test_topics_workspace_membership.py`
- `tests/test_first_login_onboarding.py`
- `tests/test_e2e_workspace_invite_flow.py`
- `frontend/src/workspace/WorkspaceSwitcher.tsx`
- `frontend/src/workspace/WorkspaceSection.tsx`
- `frontend/src/workspace/CreateWorkspaceInline.tsx`
- `frontend/src/workspace/InviteDialog.tsx`
- `frontend/src/workspace/MoveTopicMenu.tsx`
- `frontend/src/workspace/MembersList.tsx`
- `frontend/src/join/JoinTokenPage.tsx`
- `frontend/src/workspace/*.test.tsx` (per component)

**Modified:**
- `app/db.py` — rewrite `init_db()`: drop `projects`, create `workspaces` + `workspace_members` + `workspace_invites`; rename `topics.project_id` → `workspace_id`; add `agent_instances.workspace_id NOT NULL`
- `app/main.py` — replace `/api/projects*` with `/api/workspaces*`; add member/invite endpoints; add `/join/:token`; first-login onboarding
- `app/identity.py` — `ensure_agent_instance` takes `workspace_id` instead of (or in addition to) `human_id` as membership anchor
- `app/gateway.py` — `lets add --workspace` flag, device-flow passes workspace_id
- `frontend/src/layout/Sidebar.tsx` — switcher + nested sections layout
- `frontend/src/api/types.ts` — Workspace, WorkspaceMember, WorkspaceInvite types
- `frontend/src/api/queries.ts` — workspace hooks
- `frontend/src/App.tsx` — drop client-side "主频道" auto-create (moved to backend onboarding)

**Deleted / Renamed:**
- `app/projects.py` → `app/workspaces.py` (rewrite, not pure rename)
- `frontend/src/layout/Sidebar.tsx`'s `ChannelRow` → `TopicRow` (rename component + class names)

---

## Conventions

- **TDD**: failing test → confirm failure → minimal impl → confirm pass → commit
- **One task = one commit** (no batching)
- **Postgres tests** use the `temp_db` fixture in `tests/conftest.py` — fresh schema per test
- **Auth**: every mutation endpoint requires `principal: dict = Depends(get_api_principal)`
- **Membership guard**: `require_workspace_member(workspace_id, human_id, conn)` raises `HTTPException(403)` if not a member; called inside any workspace-scoped endpoint
- **Slug rules** (Workspace):
  - ASCII name: `re.sub(r'[^a-z0-9-]+', '-', name.lower()).strip('-')`
  - Non-ASCII (CJK etc) result is empty → fallback `ws-<6-char base32>` using `secrets.token_hex(3)`
  - Conflict on insert → append `-2`, `-3` … until unique
- **Invite token**: `secrets.token_urlsafe(16)` → 22-char URL-safe string
- **Commit message style**: thematic, lowercase prefix, `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` trailer
- **Schema rewrite policy**: since no real users, `init_db()` is rewritten freely — no `ALTER` migrations preserved

---

## Task 1: Schema rewrite — workspaces, members, invites tables

**Files:**
- Modify: `app/db.py` (around lines 297–530, the projects + topics + agent_instances + init_db sections)
- Create: `tests/test_workspaces_schema.py`

- [ ] **Step 1.1: Write failing schema tests**

Create `tests/test_workspaces_schema.py`:

```python
from app.db import connect


def _cols(conn, table: str) -> set[str]:
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
        (table,),
    ).fetchall()
    return {r["column_name"] for r in rows}


def test_workspaces_table_columns(temp_db):
    with connect() as conn:
        cols = _cols(conn, "workspaces")
    assert {
        "id", "slug", "name", "description", "owner_human_id",
        "is_private", "deleted_at", "created_at", "updated_at",
    }.issubset(cols)


def test_workspace_members_table_columns(temp_db):
    with connect() as conn:
        cols = _cols(conn, "workspace_members")
    assert {"workspace_id", "human_id", "role", "joined_at"}.issubset(cols)


def test_workspace_invites_table_columns(temp_db):
    with connect() as conn:
        cols = _cols(conn, "workspace_invites")
    assert {
        "id", "workspace_id", "token", "created_by_human_id",
        "expires_at", "max_uses", "used_count", "revoked_at", "created_at",
    }.issubset(cols)


def test_topics_has_workspace_id_not_project_id(temp_db):
    with connect() as conn:
        cols = _cols(conn, "topics")
    assert "workspace_id" in cols
    assert "project_id" not in cols


def test_agent_instances_has_workspace_id_not_null(temp_db):
    with connect() as conn:
        row = conn.execute(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name='agent_instances' AND column_name='workspace_id'"
        ).fetchone()
    assert row is not None
    assert row["is_nullable"] == "NO"


def test_projects_table_gone(temp_db):
    with connect() as conn:
        rows = conn.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name='projects'"
        ).fetchall()
    assert rows == []


def test_workspace_slug_unique(temp_db):
    from app.db import connect
    import psycopg
    with connect() as conn:
        conn.execute(
            "INSERT INTO workspaces (slug, name, owner_human_id) "
            "VALUES (%s, %s, %s)",
            ("w1", "W1", 1),
        )
        try:
            conn.execute(
                "INSERT INTO workspaces (slug, name, owner_human_id) "
                "VALUES (%s, %s, %s)",
                ("w1", "Dup", 1),
            )
            assert False, "expected unique violation"
        except psycopg.errors.UniqueViolation:
            pass


def test_workspace_invites_token_unique(temp_db):
    from app.db import connect
    import psycopg
    with connect() as conn:
        conn.execute(
            "INSERT INTO workspaces (slug, name, owner_human_id) "
            "VALUES ('w1', 'W1', 1)"
        )
        ws_id = conn.execute("SELECT id FROM workspaces").fetchone()["id"]
        conn.execute(
            "INSERT INTO workspace_invites (workspace_id, token, created_by_human_id) "
            "VALUES (%s, %s, %s)",
            (ws_id, "tok1", 1),
        )
        try:
            conn.execute(
                "INSERT INTO workspace_invites (workspace_id, token, created_by_human_id) "
                "VALUES (%s, %s, %s)",
                (ws_id, "tok1", 1),
            )
            assert False
        except psycopg.errors.UniqueViolation:
            pass
```

- [ ] **Step 1.2: Run tests to verify failure**

Run: `pytest tests/test_workspaces_schema.py -v`
Expected: All 8 tests FAIL (tables don't exist yet)

- [ ] **Step 1.3: Update `app/db.py` schema**

In `app/db.py`, in the schema DDL block (currently around lines 297–510):

1. **Delete** the `CREATE TABLE IF NOT EXISTS projects` block and `idx_projects_slug` index.
2. **Replace** with:

```sql
CREATE TABLE IF NOT EXISTS workspaces (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    owner_human_id BIGINT REFERENCES humans(id),
    is_private BOOLEAN NOT NULL DEFAULT TRUE,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_workspaces_slug ON workspaces(slug);
CREATE INDEX IF NOT EXISTS idx_workspaces_owner ON workspaces(owner_human_id);

CREATE TABLE IF NOT EXISTS workspace_members (
    workspace_id BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    human_id BIGINT NOT NULL REFERENCES humans(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('owner', 'member')),
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (workspace_id, human_id)
);
CREATE INDEX IF NOT EXISTS idx_workspace_members_human ON workspace_members(human_id);

CREATE TABLE IF NOT EXISTS workspace_invites (
    id BIGSERIAL PRIMARY KEY,
    workspace_id BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    token TEXT UNIQUE NOT NULL,
    created_by_human_id BIGINT NOT NULL REFERENCES humans(id),
    expires_at TIMESTAMPTZ,
    max_uses INT,
    used_count INT NOT NULL DEFAULT 0,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_workspace_invites_workspace ON workspace_invites(workspace_id);
```

3. **Modify** `topics` table: rename `project_id` → `workspace_id`:

```sql
CREATE TABLE IF NOT EXISTS topics (
    id BIGSERIAL PRIMARY KEY,
    slug TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    workspace_id BIGINT REFERENCES workspaces(id),
    mode TEXT NOT NULL DEFAULT 'exploratory',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

4. **Modify** `agent_instances` table — add `workspace_id` column (NOT NULL):

```sql
CREATE TABLE IF NOT EXISTS agent_instances (
    id BIGSERIAL PRIMARY KEY,
    role_id BIGINT NOT NULL REFERENCES agent_roles(id),
    human_id BIGINT NOT NULL REFERENCES humans(id),
    workspace_id BIGINT NOT NULL REFERENCES workspaces(id),
    device_label TEXT,
    model TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

5. **Update** `init_db()` body (around line 510): remove the `ALTER TABLE topics ADD COLUMN IF NOT EXISTS project_id` and the default-project seeding. Keep no auto-default — onboarding creates per-human (Task 11).

- [ ] **Step 1.4: Run tests to verify pass**

Run: `pytest tests/test_workspaces_schema.py -v`
Expected: All 8 tests PASS

- [ ] **Step 1.5: Sanity-run the rest of the test suite (expect breakage)**

Run: `pytest tests/ -x --co -q 2>&1 | head -40`

Expected: Other tests (using `project_id`, `projects` table, `agent_instances` without workspace_id) will be broken. That's fine — they'll get fixed as we wire the new module in. Just confirm the schema tests are green.

- [ ] **Step 1.6: Commit**

```bash
git add app/db.py tests/test_workspaces_schema.py
git commit -m "$(cat <<'EOF'
schema(workspace): replace projects with workspaces + members + invites

Drops the projects table, introduces workspaces (renamed concept) plus
workspace_members and workspace_invites. topics.project_id is renamed
to workspace_id. agent_instances gains a NOT NULL workspace_id column
so each agent process is tied to exactly one workspace.

No real users yet, so this is a clean rewrite of init_db() — no
ALTER migrations preserved.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Workspaces helper module

**Files:**
- Create: `app/workspaces.py`
- Create: `tests/test_workspaces_helper.py`
- Delete (at end of task): `app/projects.py` (after confirming no remaining imports)

- [ ] **Step 2.1: Write failing tests**

Create `tests/test_workspaces_helper.py`:

```python
import pytest
from app.workspaces import (
    slugify,
    create_workspace,
    list_workspaces_for_human,
    is_workspace_member,
    generate_invite_token,
)
from app.db import connect


def _make_human(name="alice", email=None):
    with connect() as conn:
        row = conn.execute(
            "INSERT INTO humans (name, email) VALUES (%s, %s) RETURNING id",
            (name, email),
        ).fetchone()
    return int(row["id"])


def test_slugify_ascii(temp_db):
    assert slugify("User Auth") == "user-auth"
    assert slugify("API v2 Design!") == "api-v2-design"
    assert slugify("  Whitespace  ") == "whitespace"


def test_slugify_cjk_fallback(temp_db):
    s = slugify("用户认证")
    assert s.startswith("ws-")
    assert len(s) == 9  # "ws-" + 6 hex chars


def test_slugify_conflict_appends_counter(temp_db):
    hid = _make_human()
    create_workspace(name="User Auth", owner_human_id=hid)
    ws2 = create_workspace(name="User Auth", owner_human_id=hid)
    assert ws2["slug"] == "user-auth-2"


def test_create_workspace_returns_dict(temp_db):
    hid = _make_human()
    ws = create_workspace(name="User Auth", owner_human_id=hid)
    assert ws["id"] > 0
    assert ws["slug"] == "user-auth"
    assert ws["name"] == "User Auth"
    assert ws["owner_human_id"] == hid


def test_create_workspace_auto_adds_owner_member(temp_db):
    hid = _make_human()
    ws = create_workspace(name="User Auth", owner_human_id=hid)
    assert is_workspace_member(ws["id"], hid)


def test_list_workspaces_for_human(temp_db):
    a = _make_human("alice")
    b = _make_human("bob", "b@b")
    ws_a = create_workspace(name="A", owner_human_id=a)
    ws_b = create_workspace(name="B", owner_human_id=b)
    a_list = list_workspaces_for_human(a)
    assert [w["id"] for w in a_list] == [ws_a["id"]]
    b_list = list_workspaces_for_human(b)
    assert [w["id"] for w in b_list] == [ws_b["id"]]


def test_generate_invite_token_unique(temp_db):
    tokens = {generate_invite_token() for _ in range(50)}
    assert len(tokens) == 50
    for t in tokens:
        assert len(t) >= 20
```

- [ ] **Step 2.2: Run tests to verify failure**

Run: `pytest tests/test_workspaces_helper.py -v`
Expected: ImportError — `app.workspaces` doesn't exist

- [ ] **Step 2.3: Implement `app/workspaces.py`**

Create `app/workspaces.py`:

```python
from __future__ import annotations

import re
import secrets
from typing import Any

from .db import connect


def slugify(name: str) -> str:
    """Lowercase + dashes; CJK / non-ASCII names fall back to ws-<6hex>."""
    s = re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")
    if not s:
        s = f"ws-{secrets.token_hex(3)}"
    return s


def _next_unique_slug(base: str, conn) -> str:
    candidate = base
    n = 2
    while True:
        row = conn.execute(
            "SELECT 1 FROM workspaces WHERE slug = %s", (candidate,)
        ).fetchone()
        if row is None:
            return candidate
        candidate = f"{base}-{n}"
        n += 1


def create_workspace(name: str, owner_human_id: int) -> dict[str, Any]:
    """Create workspace and add the owner as a member in one transaction."""
    base = slugify(name)
    with connect() as conn:
        slug = _next_unique_slug(base, conn)
        row = conn.execute(
            """
            INSERT INTO workspaces (slug, name, owner_human_id)
            VALUES (%s, %s, %s)
            RETURNING id, slug, name, description, owner_human_id,
                      is_private, deleted_at, created_at, updated_at
            """,
            (slug, name, owner_human_id),
        ).fetchone()
        conn.execute(
            """
            INSERT INTO workspace_members (workspace_id, human_id, role)
            VALUES (%s, %s, 'owner')
            """,
            (row["id"], owner_human_id),
        )
        return dict(row)


def is_workspace_member(workspace_id: int, human_id: int) -> bool:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT 1 FROM workspace_members
            WHERE workspace_id = %s AND human_id = %s
            """,
            (workspace_id, human_id),
        ).fetchone()
    return row is not None


def list_workspaces_for_human(human_id: int) -> list[dict[str, Any]]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT w.id, w.slug, w.name, w.description, w.owner_human_id,
                   w.is_private, w.created_at, w.updated_at,
                   wm.role AS my_role
            FROM workspaces w
            JOIN workspace_members wm ON wm.workspace_id = w.id
            WHERE wm.human_id = %s AND w.deleted_at IS NULL
            ORDER BY w.updated_at DESC
            """,
            (human_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def generate_invite_token() -> str:
    return secrets.token_urlsafe(16)
```

- [ ] **Step 2.4: Run tests to verify pass**

Run: `pytest tests/test_workspaces_helper.py -v`
Expected: All 7 tests PASS

- [ ] **Step 2.5: Delete the old `app/projects.py`**

Run: `git rm app/projects.py`

Then `grep -rn "from app.projects\|from .projects" app/ frontend/ tests/ 2>/dev/null` — if any results, leave them broken for Task 5 (they'll be reworked when we rewrite the API layer).

- [ ] **Step 2.6: Commit**

```bash
git add app/workspaces.py tests/test_workspaces_helper.py
git rm app/projects.py
git commit -m "$(cat <<'EOF'
feat(workspace): helpers for slug, create, membership check

Adds app/workspaces.py with slugify (ASCII + CJK fallback + conflict
suffixing), create_workspace (auto-inserts owner as member),
is_workspace_member, list_workspaces_for_human, and
generate_invite_token. Removes the old app/projects.py — the API
layer is rewritten in Task 5.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Workspace membership guard utility

**Files:**
- Modify: `app/workspaces.py` (add `require_workspace_member`)
- Modify: `tests/test_workspaces_helper.py` (extend)

- [ ] **Step 3.1: Extend test file**

Append to `tests/test_workspaces_helper.py`:

```python
def test_require_workspace_member_passes_for_member(temp_db):
    from app.workspaces import require_workspace_member, create_workspace
    hid = _make_human()
    ws = create_workspace(name="X", owner_human_id=hid)
    require_workspace_member(ws["id"], hid)  # no raise


def test_require_workspace_member_raises_for_non_member(temp_db):
    from fastapi import HTTPException
    from app.workspaces import require_workspace_member, create_workspace
    owner = _make_human("alice")
    intruder = _make_human("bob", "b@b")
    ws = create_workspace(name="X", owner_human_id=owner)
    with pytest.raises(HTTPException) as exc:
        require_workspace_member(ws["id"], intruder)
    assert exc.value.status_code == 403
```

- [ ] **Step 3.2: Run to verify failure**

Run: `pytest tests/test_workspaces_helper.py::test_require_workspace_member_passes_for_member -v`
Expected: ImportError on `require_workspace_member`

- [ ] **Step 3.3: Add to `app/workspaces.py`**

Append to `app/workspaces.py`:

```python
def require_workspace_member(workspace_id: int, human_id: int) -> None:
    """Raise 403 if the human is not a member of the workspace."""
    from fastapi import HTTPException
    if not is_workspace_member(workspace_id, human_id):
        raise HTTPException(status_code=403, detail="not a workspace member")


def require_workspace_owner(workspace_id: int, human_id: int) -> None:
    from fastapi import HTTPException
    with connect() as conn:
        row = conn.execute(
            """
            SELECT role FROM workspace_members
            WHERE workspace_id = %s AND human_id = %s
            """,
            (workspace_id, human_id),
        ).fetchone()
    if row is None or row["role"] != "owner":
        raise HTTPException(status_code=403, detail="not a workspace owner")
```

- [ ] **Step 3.4: Run to verify pass**

Run: `pytest tests/test_workspaces_helper.py -v`
Expected: All tests PASS (9 total)

- [ ] **Step 3.5: Commit**

```bash
git add app/workspaces.py tests/test_workspaces_helper.py
git commit -m "$(cat <<'EOF'
feat(workspace): membership + owner guards

Adds require_workspace_member and require_workspace_owner helpers that
raise HTTPException(403) when the caller is not authorized. These are
the single chokepoint for workspace-scoped access checks.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Workspace CRUD API

**Files:**
- Modify: `app/main.py` (replace `/api/projects*` block with `/api/workspaces*`)
- Create: `tests/test_workspaces_api.py`

- [ ] **Step 4.1: Write failing API tests**

Create `tests/test_workspaces_api.py`:

```python
def _login(client, name="alice", email=None):
    """Helper: dev-login as a human, return session client + human_id."""
    resp = client.post("/api/auth/dev-login", json={"name": name, "email": email})
    assert resp.status_code == 200
    return int(resp.json()["human_id"])


def test_post_workspaces_creates(temp_db, client):
    _login(client)
    r = client.post("/api/workspaces", json={"name": "User Auth"})
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "User Auth"
    assert body["slug"] == "user-auth"
    assert body["my_role"] == "owner"


def test_get_workspaces_lists_only_mine(temp_db, client):
    alice_id = _login(client, "alice")
    client.post("/api/workspaces", json={"name": "Auth"})
    # log out and log in as bob
    client.post("/api/auth/logout")
    bob_id = _login(client, "bob", "b@b")
    client.post("/api/workspaces", json={"name": "Bob WS"})
    r = client.get("/api/workspaces")
    names = [w["name"] for w in r.json()]
    assert names == ["Bob WS"]


def test_patch_workspace_rename_owner_only(temp_db, client):
    _login(client, "alice")
    r = client.post("/api/workspaces", json={"name": "Old"})
    ws_id = r.json()["id"]
    r2 = client.patch(f"/api/workspaces/{ws_id}", json={"name": "New"})
    assert r2.status_code == 200
    assert r2.json()["name"] == "New"


def test_patch_workspace_403_for_non_owner(temp_db, client):
    alice_id = _login(client, "alice")
    r = client.post("/api/workspaces", json={"name": "A"})
    ws_id = r.json()["id"]
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r2 = client.patch(f"/api/workspaces/{ws_id}", json={"name": "Hijack"})
    assert r2.status_code == 403


def test_delete_workspace_soft_delete(temp_db, client):
    _login(client, "alice")
    r = client.post("/api/workspaces", json={"name": "X"})
    ws_id = r.json()["id"]
    r2 = client.delete(f"/api/workspaces/{ws_id}")
    assert r2.status_code == 200
    r3 = client.get("/api/workspaces")
    assert r3.json() == []
```

You will need a `client` fixture and `dev-login` route. If they don't exist, also add them in this step. Check `tests/conftest.py` and `tests/test_dev_login.py` for the existing pattern.

- [ ] **Step 4.2: Run to verify failure**

Run: `pytest tests/test_workspaces_api.py -v`
Expected: 404 on the new routes

- [ ] **Step 4.3: Replace `/api/projects*` endpoints with `/api/workspaces*` in `app/main.py`**

Find the existing `@app.post("/api/projects")` and surrounding routes (search for `"/api/projects"` in `app/main.py`) — delete them and replace with:

```python
class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


class WorkspaceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=128)


@app.get("/api/workspaces")
def list_workspaces(
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    from .workspaces import list_workspaces_for_human
    return list_workspaces_for_human(int(principal["human_id"]))


@app.post("/api/workspaces")
def create_workspace_endpoint(
    payload: WorkspaceCreate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .workspaces import create_workspace
    ws = create_workspace(name=payload.name, owner_human_id=int(principal["human_id"]))
    ws["my_role"] = "owner"
    return ws


@app.get("/api/workspaces/{workspace_id}")
def get_workspace(
    workspace_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .workspaces import require_workspace_member
    require_workspace_member(workspace_id, int(principal["human_id"]))
    with connect() as conn:
        row = conn.execute(
            "SELECT id, slug, name, description, owner_human_id, is_private, "
            "created_at, updated_at FROM workspaces WHERE id = %s AND deleted_at IS NULL",
            (workspace_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="workspace not found")
    return dict(row)


@app.patch("/api/workspaces/{workspace_id}")
def update_workspace(
    workspace_id: int,
    payload: WorkspaceUpdate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .workspaces import require_workspace_owner
    require_workspace_owner(workspace_id, int(principal["human_id"]))
    with connect() as conn:
        conn.execute(
            "UPDATE workspaces SET name = %s, updated_at = NOW() WHERE id = %s",
            (payload.name, workspace_id),
        )
        row = conn.execute(
            "SELECT id, slug, name, description FROM workspaces WHERE id = %s",
            (workspace_id,),
        ).fetchone()
    return dict(row)


@app.delete("/api/workspaces/{workspace_id}")
def delete_workspace(
    workspace_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .workspaces import require_workspace_owner
    require_workspace_owner(workspace_id, int(principal["human_id"]))
    with connect() as conn:
        # Refuse to soft-delete a caller's last workspace.
        my_count = conn.execute(
            """
            SELECT COUNT(*) AS n FROM workspaces w
            JOIN workspace_members wm ON wm.workspace_id = w.id
            WHERE wm.human_id = %s AND w.deleted_at IS NULL
            """,
            (principal["human_id"],),
        ).fetchone()["n"]
        if int(my_count) <= 1:
            raise HTTPException(
                status_code=400,
                detail="cannot delete your last workspace",
            )
        conn.execute(
            "UPDATE workspaces SET deleted_at = NOW() WHERE id = %s",
            (workspace_id,),
        )
    return {"ok": True}
```

Imports needed at top of `app/main.py`: `from .db import connect` (likely already there); `from .workspaces import ...` lazy-imported inline above.

- [ ] **Step 4.4: Run to verify pass**

Run: `pytest tests/test_workspaces_api.py -v`
Expected: All 5 tests PASS

- [ ] **Step 4.5: Commit**

```bash
git add app/main.py tests/test_workspaces_api.py
git commit -m "$(cat <<'EOF'
feat(api): workspace CRUD endpoints

Replaces /api/projects routes with /api/workspaces. GET lists only
the caller's memberships. POST creates + auto-owners the caller.
PATCH/DELETE require owner. DELETE soft-deletes via deleted_at and
refuses to drop the caller's last workspace so they're never stranded.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Workspace members API

**Files:**
- Modify: `app/main.py`
- Create: `tests/test_workspace_members_api.py`

- [ ] **Step 5.1: Write tests**

Create `tests/test_workspace_members_api.py`:

```python
def test_list_members_includes_owner(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    r = client.get(f"/api/workspaces/{ws['id']}/members")
    assert r.status_code == 200
    members = r.json()
    humans = [m for m in members if m["kind"] == "human"]
    assert len(humans) == 1
    assert humans[0]["role"] == "owner"


def test_list_members_includes_agents(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    # Seed an agent_instance row tied to this workspace
    from app.db import connect
    with connect() as conn:
        conn.execute(
            "INSERT INTO agent_roles (name) VALUES ('claude') ON CONFLICT DO NOTHING"
        )
        role_id = conn.execute(
            "SELECT id FROM agent_roles WHERE name='claude'"
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO agent_instances (role_id, human_id, workspace_id, device_label) "
            "VALUES (%s, %s, %s, 'mac')",
            (role_id, 1, ws["id"]),  # human_id 1 = alice
        )
    r = client.get(f"/api/workspaces/{ws['id']}/members")
    agents = [m for m in r.json() if m["kind"] == "agent"]
    assert len(agents) == 1
    assert agents[0]["role"] == "claude"


def test_remove_member_owner_only(temp_db, client):
    alice_id = _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    # bob accepts (we don't have invites yet, so just insert directly for now)
    from app.db import connect
    with connect() as conn:
        bob_id = conn.execute(
            "INSERT INTO humans (name, email) VALUES ('bob', 'b@b') RETURNING id"
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO workspace_members (workspace_id, human_id, role) "
            "VALUES (%s, %s, 'member')",
            (ws["id"], bob_id),
        )
    r = client.delete(f"/api/workspaces/{ws['id']}/members/{bob_id}")
    assert r.status_code == 200
    members = client.get(f"/api/workspaces/{ws['id']}/members").json()
    bob_rows = [m for m in members if m["kind"] == "human" and m["name"] == "bob"]
    assert bob_rows == []


def test_cannot_remove_owner(temp_db, client):
    alice_id = _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    r = client.delete(f"/api/workspaces/{ws['id']}/members/{alice_id}")
    assert r.status_code == 400
```

(Add the `_login` helper to a shared fixture or inline at top of file.)

- [ ] **Step 5.2: Run to verify failure**

Run: `pytest tests/test_workspace_members_api.py -v`
Expected: 404 on routes

- [ ] **Step 5.3: Add member endpoints to `app/main.py`**

```python
@app.get("/api/workspaces/{workspace_id}/members")
def list_workspace_members(
    workspace_id: int,
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    from .workspaces import require_workspace_member
    require_workspace_member(workspace_id, int(principal["human_id"]))
    with connect() as conn:
        human_rows = conn.execute(
            """
            SELECT h.id, h.name, h.email, h.avatar_url, wm.role, wm.joined_at
            FROM workspace_members wm
            JOIN humans h ON h.id = wm.human_id
            WHERE wm.workspace_id = %s
            ORDER BY wm.joined_at ASC
            """,
            (workspace_id,),
        ).fetchall()
        agent_rows = conn.execute(
            """
            SELECT ai.id, ar.name AS role, ai.device_label, ai.model,
                   ai.human_id AS started_by_human_id, h.name AS started_by_name
            FROM agent_instances ai
            JOIN agent_roles ar ON ar.id = ai.role_id
            JOIN humans h ON h.id = ai.human_id
            WHERE ai.workspace_id = %s
            ORDER BY ai.created_at ASC
            """,
            (workspace_id,),
        ).fetchall()
    humans = [{**dict(r), "kind": "human"} for r in human_rows]
    agents = [{**dict(r), "kind": "agent"} for r in agent_rows]
    return humans + agents


@app.delete("/api/workspaces/{workspace_id}/members/{human_id}")
def remove_workspace_member(
    workspace_id: int,
    human_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .workspaces import require_workspace_owner
    require_workspace_owner(workspace_id, int(principal["human_id"]))
    with connect() as conn:
        row = conn.execute(
            "SELECT role FROM workspace_members WHERE workspace_id = %s AND human_id = %s",
            (workspace_id, human_id),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="member not found")
        if row["role"] == "owner":
            raise HTTPException(status_code=400, detail="cannot remove owner")
        conn.execute(
            "DELETE FROM workspace_members WHERE workspace_id = %s AND human_id = %s",
            (workspace_id, human_id),
        )
    return {"ok": True}
```

- [ ] **Step 5.4: Run to verify pass**

Run: `pytest tests/test_workspace_members_api.py -v`
Expected: 4 tests PASS

- [ ] **Step 5.5: Commit**

```bash
git add app/main.py tests/test_workspace_members_api.py
git commit -m "$(cat <<'EOF'
feat(api): workspace members listing + removal

GET /api/workspaces/:id/members returns a unified list of humans
(role: owner|member) and agent_instances (kind: agent) so the UI can
render one panel. DELETE removes a member; refuses to drop the owner.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Invite generation + listing + revocation API

**Files:**
- Modify: `app/main.py`
- Create: `tests/test_workspace_invites_api.py`

- [ ] **Step 6.1: Write tests**

Create `tests/test_workspace_invites_api.py`:

```python
def test_create_invite_returns_url(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    r = client.post(f"/api/workspaces/{ws['id']}/invites", json={})
    assert r.status_code == 200
    body = r.json()
    assert "token" in body
    assert len(body["token"]) >= 20
    assert body["join_url"].endswith(f"/join/{body['token']}")


def test_list_invites_excludes_revoked(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()
    client.delete(f"/api/invites/{inv['id']}")
    listing = client.get(f"/api/workspaces/{ws['id']}/invites").json()
    assert listing == []


def test_create_invite_member_only_403(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.post(f"/api/workspaces/{ws['id']}/invites", json={})
    assert r.status_code == 403
```

- [ ] **Step 6.2: Run to verify failure**

Run: `pytest tests/test_workspace_invites_api.py -v`
Expected: 404 on routes

- [ ] **Step 6.3: Add invite endpoints**

In `app/main.py`:

```python
@app.post("/api/workspaces/{workspace_id}/invites")
def create_workspace_invite(
    workspace_id: int,
    request: Request,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .workspaces import require_workspace_owner, generate_invite_token
    require_workspace_owner(workspace_id, int(principal["human_id"]))
    token = generate_invite_token()
    with connect() as conn:
        row = conn.execute(
            """
            INSERT INTO workspace_invites (workspace_id, token, created_by_human_id)
            VALUES (%s, %s, %s)
            RETURNING id, token, created_at
            """,
            (workspace_id, token, principal["human_id"]),
        ).fetchone()
    base_url = _public_base_url(request)
    return {
        "id": int(row["id"]),
        "token": row["token"],
        "join_url": f"{base_url}/join/{row['token']}",
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@app.get("/api/workspaces/{workspace_id}/invites")
def list_workspace_invites(
    workspace_id: int,
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    from .workspaces import require_workspace_owner
    require_workspace_owner(workspace_id, int(principal["human_id"]))
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, token, created_by_human_id, used_count,
                   expires_at, max_uses, created_at
            FROM workspace_invites
            WHERE workspace_id = %s
              AND revoked_at IS NULL
              AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY created_at DESC
            """,
            (workspace_id,),
        ).fetchall()
    return [dict(r) for r in rows]


@app.delete("/api/invites/{invite_id}")
def revoke_invite(
    invite_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .workspaces import require_workspace_owner
    with connect() as conn:
        inv = conn.execute(
            "SELECT workspace_id FROM workspace_invites WHERE id = %s",
            (invite_id,),
        ).fetchone()
        if inv is None:
            raise HTTPException(status_code=404, detail="invite not found")
    require_workspace_owner(int(inv["workspace_id"]), int(principal["human_id"]))
    with connect() as conn:
        conn.execute(
            "UPDATE workspace_invites SET revoked_at = NOW() WHERE id = %s",
            (invite_id,),
        )
    return {"ok": True}
```

- [ ] **Step 6.4: Run to verify pass**

Run: `pytest tests/test_workspace_invites_api.py -v`
Expected: 3 tests PASS

- [ ] **Step 6.5: Commit**

```bash
git add app/main.py tests/test_workspace_invites_api.py
git commit -m "$(cat <<'EOF'
feat(api): workspace invite create/list/revoke

POST /api/workspaces/:id/invites mints a token and returns a join_url.
GET filters out revoked + expired. DELETE /api/invites/:id soft-revokes.
All three are owner-only.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Invite accept endpoint (idempotent)

**Files:**
- Modify: `app/main.py`
- Create test cases in `tests/test_workspace_invites_api.py` (append)

- [ ] **Step 7.1: Append tests**

```python
def test_accept_invite_adds_member(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.post(f"/api/invites/{inv['token']}/accept")
    assert r.status_code == 200
    body = r.json()
    assert body["workspace_id"] == ws["id"]
    # Bob now sees the workspace in his list
    bobs = client.get("/api/workspaces").json()
    assert ws["id"] in [w["id"] for w in bobs]


def test_accept_invite_idempotent(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    client.post(f"/api/invites/{inv['token']}/accept")
    r = client.post(f"/api/invites/{inv['token']}/accept")
    assert r.status_code == 200  # still 200, no duplicate insert
    # Used_count incremented only once
    client.post("/api/auth/logout")
    _login(client, "alice")
    invs = client.get(f"/api/workspaces/{ws['id']}/invites").json()
    assert invs[0]["used_count"] == 1


def test_accept_invite_revoked_token_404(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()
    client.delete(f"/api/invites/{inv['id']}")
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.post(f"/api/invites/{inv['token']}/accept")
    assert r.status_code == 404
```

- [ ] **Step 7.2: Run to verify failure**

Run: `pytest tests/test_workspace_invites_api.py::test_accept_invite_adds_member -v`
Expected: 404

- [ ] **Step 7.3: Add accept endpoint**

```python
@app.post("/api/invites/{token}/accept")
def accept_invite(
    token: str,
    principal: dict = Depends(get_api_principal),
) -> dict:
    human_id = int(principal["human_id"])
    with connect() as conn:
        inv = conn.execute(
            """
            SELECT id, workspace_id, max_uses, used_count, expires_at
            FROM workspace_invites
            WHERE token = %s
              AND revoked_at IS NULL
              AND (expires_at IS NULL OR expires_at > NOW())
              AND (max_uses IS NULL OR used_count < max_uses)
            """,
            (token,),
        ).fetchone()
        if inv is None:
            raise HTTPException(status_code=404, detail="invite not valid")
        already = conn.execute(
            """
            SELECT 1 FROM workspace_members
            WHERE workspace_id = %s AND human_id = %s
            """,
            (inv["workspace_id"], human_id),
        ).fetchone()
        if already is None:
            conn.execute(
                """
                INSERT INTO workspace_members (workspace_id, human_id, role)
                VALUES (%s, %s, 'member')
                """,
                (inv["workspace_id"], human_id),
            )
            conn.execute(
                """
                UPDATE workspace_invites
                SET used_count = used_count + 1
                WHERE id = %s
                """,
                (inv["id"],),
            )
    return {"workspace_id": int(inv["workspace_id"])}
```

- [ ] **Step 7.4: Run to verify pass**

Run: `pytest tests/test_workspace_invites_api.py -v`
Expected: 6 tests PASS

- [ ] **Step 7.5: Commit**

```bash
git add app/main.py tests/test_workspace_invites_api.py
git commit -m "$(cat <<'EOF'
feat(api): idempotent invite accept

POST /api/invites/:token/accept adds the caller as a workspace member
if they're not already. Repeat calls return 200 without double-inserting
or double-incrementing used_count. Revoked/expired/exhausted tokens
return 404.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Topic API — workspace nesting + membership enforcement

**Files:**
- Modify: `app/main.py`
- Create: `tests/test_topics_workspace_membership.py`

- [ ] **Step 8.1: Write tests**

Create `tests/test_topics_workspace_membership.py`:

```python
def test_list_topics_requires_membership(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.get(f"/api/workspaces/{ws['id']}/topics")
    assert r.status_code == 403


def test_create_topic_member_allowed(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    r = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "oauth", "title": "OAuth 流程"},
    )
    assert r.status_code == 200
    assert r.json()["title"] == "OAuth 流程"


def test_create_topic_non_member_403(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "oauth", "title": "OAuth"},
    )
    assert r.status_code == 403
```

- [ ] **Step 8.2: Run to verify failure**

Run: `pytest tests/test_topics_workspace_membership.py -v`
Expected: Routes still on `/api/projects/`, so 404

- [ ] **Step 8.3: Rename existing topic-list endpoint**

In `app/main.py` find the existing `@app.get("/api/projects/{project_id}/topics")` and `@app.post("/api/projects/{project_id}/topics")`. Rename the path to `/api/workspaces/{workspace_id}/topics`, rename the path-param `project_id` → `workspace_id`, and add membership guard:

```python
@app.get("/api/workspaces/{workspace_id}/topics")
def list_topics_in_workspace(
    workspace_id: int,
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    from .workspaces import require_workspace_member
    require_workspace_member(workspace_id, int(principal["human_id"]))
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, slug, title, workspace_id, mode, created_at, updated_at
            FROM topics
            WHERE workspace_id = %s
            ORDER BY updated_at DESC
            """,
            (workspace_id,),
        ).fetchall()
    return [dict(r) for r in rows]


class TopicCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    mode: str = Field(default="exploratory")


@app.post("/api/workspaces/{workspace_id}/topics")
def create_topic_in_workspace(
    workspace_id: int,
    payload: TopicCreate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .workspaces import require_workspace_member
    require_workspace_member(workspace_id, int(principal["human_id"]))
    with connect() as conn:
        try:
            row = conn.execute(
                """
                INSERT INTO topics (slug, title, workspace_id, mode)
                VALUES (%s, %s, %s, %s)
                RETURNING id, slug, title, workspace_id, mode,
                          created_at, updated_at
                """,
                (payload.slug, payload.title, workspace_id, payload.mode),
            ).fetchone()
        except IntegrityError as e:
            if "topics_slug_key" in str(e).lower() or "unique" in str(e).lower():
                raise HTTPException(status_code=409, detail=f"slug in use: {payload.slug}")
            raise
    return dict(row)
```

Also: search `/api/topics/{topic_id}` GETs and any topic-scoped reads (`messages`, `task-tree`, `artifacts`) and add a membership guard. A helper:

```python
def _require_topic_member(topic_id: int, human_id: int) -> int:
    """Return workspace_id; raise 403 if caller not a member."""
    from .workspaces import require_workspace_member
    with connect() as conn:
        row = conn.execute(
            "SELECT workspace_id FROM topics WHERE id = %s", (topic_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="topic not found")
    require_workspace_member(int(row["workspace_id"]), human_id)
    return int(row["workspace_id"])
```

Add a `_require_topic_member(topic_id, int(principal["human_id"]))` call at the top of every `@app.get("/api/topics/...")` and `@app.post("/api/topics/...")` and `@app.get("/api/messages")` style endpoint that takes `topic_id`. Sweep the file.

- [ ] **Step 8.4: Run to verify pass**

Run: `pytest tests/test_topics_workspace_membership.py -v` then `pytest tests/ -x -q`
Expected: workspace_membership tests pass; other broken tests will surface — fix them by updating `_login`-style helpers and creating a workspace before creating topics in those tests. Where tests previously created topics under a default project, change them to create a workspace + topic.

- [ ] **Step 8.5: Commit**

```bash
git add app/main.py tests/test_topics_workspace_membership.py
git commit -m "$(cat <<'EOF'
feat(api): scope topic routes under workspace + enforce membership

Renames /api/projects/:id/topics to /api/workspaces/:id/topics and
adds require_workspace_member to every workspace- and topic-scoped
endpoint via the _require_topic_member helper.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Topic cross-workspace move endpoint

**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_topics_workspace_membership.py` (append)

- [ ] **Step 9.1: Append tests**

```python
def test_patch_topic_moves_workspace(temp_db, client):
    _login(client, "alice")
    ws_a = client.post("/api/workspaces", json={"name": "A"}).json()
    ws_b = client.post("/api/workspaces", json={"name": "B"}).json()
    topic = client.post(
        f"/api/workspaces/{ws_a['id']}/topics",
        json={"slug": "oauth", "title": "OAuth"},
    ).json()
    r = client.patch(
        f"/api/topics/{topic['id']}",
        json={"workspace_id": ws_b["id"]},
    )
    assert r.status_code == 200
    assert r.json()["workspace_id"] == ws_b["id"]


def test_patch_topic_403_if_not_member_of_target(temp_db, client):
    alice_id = _login(client, "alice")
    ws_a = client.post("/api/workspaces", json={"name": "A"}).json()
    topic = client.post(
        f"/api/workspaces/{ws_a['id']}/topics",
        json={"slug": "x", "title": "X"},
    ).json()
    # Make a workspace owned by bob that alice isn't a member of.
    from app.db import connect
    with connect() as conn:
        bob_id = conn.execute(
            "INSERT INTO humans (name, email) VALUES ('bob', 'b@b') RETURNING id"
        ).fetchone()["id"]
        bob_ws = conn.execute(
            "INSERT INTO workspaces (slug, name, owner_human_id) "
            "VALUES ('bob-ws', 'Bob WS', %s) RETURNING id",
            (bob_id,),
        ).fetchone()["id"]
        conn.execute(
            "INSERT INTO workspace_members (workspace_id, human_id, role) "
            "VALUES (%s, %s, 'owner')",
            (bob_ws, bob_id),
        )
    r = client.patch(
        f"/api/topics/{topic['id']}",
        json={"workspace_id": bob_ws},
    )
    assert r.status_code == 403
```

- [ ] **Step 9.2: Run to verify failure**

- [ ] **Step 9.3: Add PATCH route**

```python
class TopicUpdate(BaseModel):
    workspace_id: int | None = None
    title: str | None = None


@app.patch("/api/topics/{topic_id}")
def update_topic(
    topic_id: int,
    payload: TopicUpdate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    human_id = int(principal["human_id"])
    _require_topic_member(topic_id, human_id)  # must be member of current ws
    sets, vals = [], []
    if payload.workspace_id is not None:
        from .workspaces import require_workspace_member
        require_workspace_member(payload.workspace_id, human_id)  # and of new ws
        sets.append("workspace_id = %s")
        vals.append(payload.workspace_id)
    if payload.title is not None:
        sets.append("title = %s")
        vals.append(payload.title)
    if not sets:
        raise HTTPException(status_code=400, detail="no fields to update")
    sets.append("updated_at = NOW()")
    vals.append(topic_id)
    with connect() as conn:
        row = conn.execute(
            f"UPDATE topics SET {', '.join(sets)} WHERE id = %s "
            "RETURNING id, slug, title, workspace_id, mode, updated_at",
            tuple(vals),
        ).fetchone()
    return dict(row)
```

- [ ] **Step 9.4: Run to verify pass**

- [ ] **Step 9.5: Commit**

```bash
git add app/main.py tests/test_topics_workspace_membership.py
git commit -m "$(cat <<'EOF'
feat(api): PATCH /api/topics/:id supports cross-workspace move + rename

Caller must be a member of both the current and (when moving) the
target workspace.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 10: Device-flow takes workspace_id

**Files:**
- Modify: `app/main.py` (device-flow routes, lines around 2238–2310)
- Modify: `app/identity.py` (`ensure_agent_instance` signature)
- Modify: `tests/test_device_flow.py`

- [ ] **Step 10.1: Update test**

In `tests/test_device_flow.py`, find the device-flow happy-path test and adjust:

```python
def test_device_flow_with_workspace(temp_db, client):
    alice_id = _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    r = client.post(
        "/api/auth/device-flow/start",
        params={"role": "claude", "workspace_id": ws["id"]},
    )
    assert r.status_code == 200
    device_code = r.json()["device_code"]
    # authorize
    user_code = r.json()["user_code"]
    client.post(f"/api/auth/device-flow/authorize/{user_code}")
    poll = client.get(f"/api/auth/device-flow/poll/{device_code}")
    assert poll.status_code == 200
    agent = poll.json()["agent"]
    assert agent["workspace_id"] == ws["id"]


def test_device_flow_defaults_to_caller_first_workspace(temp_db, client):
    alice_id = _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "MyWS"}).json()
    r = client.post(
        "/api/auth/device-flow/start", params={"role": "claude"}
    )
    user_code = r.json()["user_code"]
    client.post(f"/api/auth/device-flow/authorize/{user_code}")
    poll = client.get(f"/api/auth/device-flow/poll/{r.json()['device_code']}")
    assert poll.json()["agent"]["workspace_id"] == ws["id"]
```

- [ ] **Step 10.2: Run to verify failure**

- [ ] **Step 10.3: Update `device_auth_flows` schema** in `app/db.py`

Add `workspace_id` column to the CREATE TABLE for `device_auth_flows`:

```sql
CREATE TABLE IF NOT EXISTS device_auth_flows (
    ...existing columns...,
    workspace_id BIGINT REFERENCES workspaces(id),
    ...
);
```

- [ ] **Step 10.4: Update `ensure_agent_instance` in `app/identity.py`**

```python
def ensure_agent_instance(
    role: str,
    human_id: int,
    device_label: str,
    workspace_id: int,
    model: str | None = None,
) -> int:
    """workspace_id is now required."""
    with connect() as conn:
        role_row = conn.execute(
            "SELECT id FROM agent_roles WHERE name = %s", (role,)
        ).fetchone()
        if role_row is None:
            raise ValueError(f"unknown role: {role}")
        role_id = role_row["id"]
        existing = conn.execute(
            """
            SELECT id FROM agent_instances
            WHERE role_id = %s AND human_id = %s
              AND device_label = %s AND workspace_id = %s
            """,
            (role_id, human_id, device_label, workspace_id),
        ).fetchone()
        if existing:
            if model is not None:
                conn.execute(
                    "UPDATE agent_instances SET model = %s, updated_at = NOW() "
                    "WHERE id = %s",
                    (model, existing["id"]),
                )
            return int(existing["id"])
        cursor = conn.execute(
            """
            INSERT INTO agent_instances
                (role_id, human_id, workspace_id, device_label, model)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (role_id, human_id, workspace_id, device_label, model),
        )
        return int(cursor.fetchone()["id"])
```

- [ ] **Step 10.5: Update device-flow start/authorize in `app/main.py`**

Add `workspace_id` query param to `device_flow_start`. In `device_flow_authorize`, if `workspace_id` is None on the row, default to the caller's first owned workspace:

```python
@app.post("/api/auth/device-flow/start")
def device_flow_start(
    request: Request,
    role: str = Query(default="claude"),
    device_label: str = Query(default="local"),
    model: str | None = Query(default=None),
    workspace_id: int | None = Query(default=None),
) -> dict:
    # ... existing validation ...
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO device_auth_flows
                (device_code, user_code, role, device_label, model,
                 workspace_id, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW() + INTERVAL '10 minutes')
            """,
            (device_code, user_code, role, device_label, model, workspace_id),
        )
    # ... unchanged remainder ...
```

In `device_flow_authorize` (where it consumes the row and calls `ensure_agent_instance`):

```python
# After fetching `row` and ensuring `authorized_at IS NULL` etc:
ws_id = row["workspace_id"]
if ws_id is None:
    # Default to caller's first workspace; create one if they have none.
    from .workspaces import list_workspaces_for_human, create_workspace
    mine = list_workspaces_for_human(human_id)
    if mine:
        ws_id = mine[0]["id"]
    else:
        ws = create_workspace(name="我的工作区", owner_human_id=human_id)
        ws_id = ws["id"]

agent_id = ensure_agent_instance(
    role=role,
    human_id=human_id,
    device_label=device_label,
    workspace_id=int(ws_id),
    model=str(row["model"]).strip() if row["model"] else None,
)
```

- [ ] **Step 10.6: Run to verify pass**

Run: `pytest tests/test_device_flow.py -v`

- [ ] **Step 10.7: Commit**

```bash
git add app/db.py app/main.py app/identity.py tests/test_device_flow.py
git commit -m "$(cat <<'EOF'
feat(device-flow): bind agents to a workspace

Adds workspace_id to device_auth_flows + the start params. If the
caller didn't specify, fall back to their first workspace (or create
'我的工作区' if they have none). ensure_agent_instance now requires
workspace_id and uniqueness is keyed on (role, human, device, ws).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: First-login onboarding (backend)

**Files:**
- Modify: `app/main.py` (GitHub callback + dev-login)
- Create: `tests/test_first_login_onboarding.py`

- [ ] **Step 11.1: Write tests**

Create `tests/test_first_login_onboarding.py`:

```python
def test_first_login_creates_workspace_and_topic(temp_db, client):
    _login(client, "alice")
    workspaces = client.get("/api/workspaces").json()
    assert len(workspaces) == 1
    assert workspaces[0]["name"] == "我的工作区"
    ws_id = workspaces[0]["id"]
    topics = client.get(f"/api/workspaces/{ws_id}/topics").json()
    assert len(topics) == 1
    assert topics[0]["title"] == "主频道"


def test_second_login_does_not_duplicate(temp_db, client):
    _login(client, "alice")
    client.post("/api/auth/logout")
    _login(client, "alice")  # same human
    workspaces = client.get("/api/workspaces").json()
    assert len(workspaces) == 1
    topics = client.get(f"/api/workspaces/{workspaces[0]['id']}/topics").json()
    assert len(topics) == 1
```

- [ ] **Step 11.2: Run to verify failure**

- [ ] **Step 11.3: Add `_ensure_onboarded(human_id)` helper in `app/main.py`**

```python
def _ensure_onboarded(human_id: int) -> None:
    """Create '我的工作区' + '主频道' on first login if absent. Idempotent."""
    from .workspaces import list_workspaces_for_human, create_workspace
    if list_workspaces_for_human(human_id):
        return
    ws = create_workspace(name="我的工作区", owner_human_id=human_id)
    with connect() as conn:
        slug = f"general-{int(__import__('time').time())}"
        conn.execute(
            """
            INSERT INTO topics (slug, title, workspace_id, mode)
            VALUES (%s, %s, %s, 'exploratory')
            """,
            (slug, "主频道", ws["id"]),
        )
```

- [ ] **Step 11.4: Call after every successful login**

In `app/main.py`, find the GitHub callback (`auth_github_callback`) and the dev-login route. After setting the session cookie, call `_ensure_onboarded(human_id)`:

```python
# In auth_github_callback, after upserting human + setting session:
_ensure_onboarded(human_id)

# In dev-login route similarly:
_ensure_onboarded(human_id)
```

- [ ] **Step 11.5: Run to verify pass**

Run: `pytest tests/test_first_login_onboarding.py -v`

- [ ] **Step 11.6: Commit**

```bash
git add app/main.py tests/test_first_login_onboarding.py
git commit -m "$(cat <<'EOF'
feat(onboarding): auto-create 我的工作区 + 主频道 on first login

_ensure_onboarded runs after every login and is idempotent: if the
human already owns at least one workspace, it's a no-op. Otherwise it
mints '我的工作区' and a 'general-<ts>' topic so the user lands
straight in chat.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: `/join/:token` landing page

**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_workspace_invites_api.py` (append)

- [ ] **Step 12.1: Append tests**

```python
def test_join_token_unauthenticated_redirects_to_login(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()
    client.post("/api/auth/logout")
    r = client.get(f"/join/{inv['token']}", follow_redirects=False)
    assert r.status_code in (302, 303, 307)
    assert "/login" in r.headers["location"]
    assert f"/join/{inv['token']}" in r.headers["location"]


def test_join_token_authenticated_adds_and_redirects(temp_db, client):
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "A"}).json()
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.get(f"/join/{inv['token']}", follow_redirects=False)
    assert r.status_code in (302, 303, 307)
    # Bob is now a member
    bobs_ws = client.get("/api/workspaces").json()
    assert ws["id"] in [w["id"] for w in bobs_ws]
```

- [ ] **Step 12.2: Run to verify failure**

- [ ] **Step 12.3: Add `/join/:token` route**

```python
from fastapi.responses import RedirectResponse


@app.get("/join/{token}")
def join_by_token(
    token: str,
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> RedirectResponse:
    from .auth import verify_session
    if not lets_session or verify_session(lets_session) is None:
        return RedirectResponse(
            url=f"/login?redirect=/join/{token}", status_code=303
        )
    principal = verify_session(lets_session)
    human_id = int(principal["human_id"])
    # Idempotent accept
    with connect() as conn:
        inv = conn.execute(
            """
            SELECT id, workspace_id FROM workspace_invites
            WHERE token = %s
              AND revoked_at IS NULL
              AND (expires_at IS NULL OR expires_at > NOW())
              AND (max_uses IS NULL OR used_count < max_uses)
            """,
            (token,),
        ).fetchone()
        if inv is None:
            return RedirectResponse(url="/?error=invite_invalid", status_code=303)
        already = conn.execute(
            "SELECT 1 FROM workspace_members WHERE workspace_id = %s AND human_id = %s",
            (inv["workspace_id"], human_id),
        ).fetchone()
        if already is None:
            conn.execute(
                "INSERT INTO workspace_members (workspace_id, human_id, role) "
                "VALUES (%s, %s, 'member')",
                (inv["workspace_id"], human_id),
            )
            conn.execute(
                "UPDATE workspace_invites SET used_count = used_count + 1 WHERE id = %s",
                (inv["id"],),
            )
    return RedirectResponse(
        url=f"/?workspace={inv['workspace_id']}", status_code=303
    )
```

- [ ] **Step 12.4: Run to verify pass**

- [ ] **Step 12.5: Commit**

```bash
git add app/main.py tests/test_workspace_invites_api.py
git commit -m "$(cat <<'EOF'
feat(invite): /join/:token landing redirects to login or accepts

Unauthenticated → /login?redirect=/join/:token. Authenticated and not
yet a member → add row + bump used_count + redirect to home with the
workspace selected. Invalid token → home with error query.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: Frontend types + API hooks

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/queries.ts`
- Create: `frontend/src/api/queries.workspace.test.tsx` (or extend existing `queries.test.tsx`)

- [ ] **Step 13.1: Add types**

In `frontend/src/api/types.ts` append:

```typescript
export interface Workspace {
  id: number;
  slug: string;
  name: string;
  description: string | null;
  owner_human_id: number;
  is_private: boolean;
  my_role: "owner" | "member";
  created_at: string;
  updated_at: string;
}

export interface WorkspaceMemberHuman {
  kind: "human";
  id: number;
  name: string;
  email: string | null;
  avatar_url: string | null;
  role: "owner" | "member";
  joined_at: string;
}

export interface WorkspaceMemberAgent {
  kind: "agent";
  id: number;
  role: string;
  device_label: string | null;
  model: string | null;
  started_by_name: string;
}

export type WorkspaceMember = WorkspaceMemberHuman | WorkspaceMemberAgent;

export interface WorkspaceInvite {
  id: number;
  token: string;
  join_url: string;
  created_at: string;
}
```

- [ ] **Step 13.2: Add query hooks**

In `frontend/src/api/queries.ts` append:

```typescript
export function useWorkspaces() {
  return useQuery({
    queryKey: ["workspaces"],
    queryFn: async () => {
      const r = await apiClient.get<Workspace[]>("/api/workspaces");
      return r.data;
    },
  });
}

export function useCreateWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (name: string) => {
      const r = await apiClient.post<Workspace>("/api/workspaces", { name });
      return r.data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["workspaces"] });
    },
  });
}

export function useRenameWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, name }: { id: number; name: string }) => {
      const r = await apiClient.patch<Workspace>(`/api/workspaces/${id}`, { name });
      return r.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workspaces"] }),
  });
}

export function useDeleteWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/api/workspaces/${id}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workspaces"] }),
  });
}

export function useWorkspaceMembers(workspaceId: number | null) {
  return useQuery({
    queryKey: ["workspace-members", workspaceId],
    enabled: workspaceId != null,
    queryFn: async () => {
      const r = await apiClient.get<WorkspaceMember[]>(
        `/api/workspaces/${workspaceId}/members`
      );
      return r.data;
    },
  });
}

export function useCreateInvite() {
  return useMutation({
    mutationFn: async (workspaceId: number) => {
      const r = await apiClient.post<WorkspaceInvite>(
        `/api/workspaces/${workspaceId}/invites`,
        {}
      );
      return r.data;
    },
  });
}

export function useTopicsInWorkspace(workspaceId: number | null) {
  return useQuery({
    queryKey: ["workspace-topics", workspaceId],
    enabled: workspaceId != null,
    queryFn: async () => {
      const r = await apiClient.get<TopicDTO[]>(
        `/api/workspaces/${workspaceId}/topics`
      );
      return r.data;
    },
  });
}

export function useMoveTopic() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ topicId, workspaceId }: { topicId: number; workspaceId: number }) => {
      const r = await apiClient.patch<TopicDTO>(`/api/topics/${topicId}`, {
        workspace_id: workspaceId,
      });
      return r.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["workspace-topics"] }),
  });
}
```

Replace any existing `useProjects` / `useTopicsInProject` hooks (their old paths `/api/projects/...` are gone).

- [ ] **Step 13.3: Write a small unit test**

In `frontend/src/api/queries.test.tsx` add (or use existing test file pattern):

```typescript
import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useWorkspaces } from "./queries";

// Assumes MSW handler in fixtures/handlers.ts is updated below

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe("useWorkspaces", () => {
  it("returns workspaces list", async () => {
    const { result } = renderHook(() => useWorkspaces(), { wrapper });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toBeInstanceOf(Array);
  });
});
```

In `frontend/src/fixtures/handlers.ts` add an MSW handler for `GET /api/workspaces` returning a fixture list.

- [ ] **Step 13.4: Run frontend tests**

Run: `cd frontend && pnpm test --run`
Expected: all green

- [ ] **Step 13.5: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/api/queries.ts frontend/src/api/queries.test.tsx frontend/src/fixtures/handlers.ts
git commit -m "$(cat <<'EOF'
feat(frontend): workspace types + query hooks

Adds Workspace, WorkspaceMember{Human,Agent}, WorkspaceInvite types
and useWorkspaces / useCreateWorkspace / useRenameWorkspace /
useDeleteWorkspace / useWorkspaceMembers / useCreateInvite /
useTopicsInWorkspace / useMoveTopic hooks. Removes the old project-
scoped hooks.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: Sidebar rewrite — switcher + nested workspaces + members

**Files:**
- Modify: `frontend/src/layout/Sidebar.tsx` (heavy rewrite; rename `ChannelRow` → `TopicRow`)
- Create: `frontend/src/workspace/WorkspaceSwitcher.tsx`
- Create: `frontend/src/workspace/WorkspaceSection.tsx`
- Create: `frontend/src/workspace/CreateWorkspaceInline.tsx`
- Create: `frontend/src/workspace/MembersList.tsx`
- Each with companion `*.test.tsx`

- [ ] **Step 14.1: Write a Sidebar render test**

In `frontend/src/layout/Sidebar.test.tsx`, write:

```typescript
it("renders the active workspace's topics and collapses others", () => {
  render(
    <Sidebar
      activeWorkspace={{ id: 1, name: "我的工作区", slug: "my-ws", ...}}
      workspaces={[
        { id: 1, name: "我的工作区", ... },
        { id: 2, name: "用户认证", ... },
      ]}
      topics={[{ id: 10, slug: "general-1", title: "主频道", workspace_id: 1 }]}
      members={[]}
      onCreateTopic={vi.fn()}
      onSelectTopic={vi.fn()}
      onSwitchWorkspace={vi.fn()}
      onCreateWorkspace={vi.fn()}
      onInviteMember={vi.fn()}
    />
  );
  expect(screen.getByText("我的工作区")).toBeInTheDocument();
  expect(screen.getByText("主频道")).toBeInTheDocument();
  // Other workspace collapsed: name visible but its topics not loaded yet
  expect(screen.getByText("用户认证")).toBeInTheDocument();
});
```

- [ ] **Step 14.2: Build the components**

Create `frontend/src/workspace/WorkspaceSwitcher.tsx`:

```typescript
import type { Workspace } from "../api/types";

interface Props {
  workspaces: Workspace[];
  activeId: number;
  onSelect: (id: number) => void;
  onCreate: () => void;
}

export function WorkspaceSwitcher({ workspaces, activeId, onSelect, onCreate }: Props) {
  const active = workspaces.find((w) => w.id === activeId);
  const others = workspaces.filter((w) => w.id !== activeId).slice(0, 2);
  return (
    <div className="flex items-center gap-1 px-3 py-2 border-b border-border">
      <button
        type="button"
        className="font-[var(--font-display)] text-sm text-text px-2 py-1 rounded hover:bg-hover"
      >
        {active?.name ?? "—"} ▾
      </button>
      {others.map((w) => (
        <button
          key={w.id}
          type="button"
          onClick={() => onSelect(w.id)}
          className="text-xs text-text-dim hover:text-text px-2 py-1 rounded hover:bg-hover"
        >
          {w.name}
        </button>
      ))}
      <button
        type="button"
        onClick={onCreate}
        title="新建工作区"
        className="text-xs text-text-dim hover:text-text px-2 py-1 rounded hover:bg-hover ml-auto"
      >
        ＋
      </button>
    </div>
  );
}
```

Create `frontend/src/workspace/WorkspaceSection.tsx` (folded section for one inactive workspace + lazy-load its topics on expand):

```typescript
import { useState } from "react";
import { useTopicsInWorkspace } from "../api/queries";
import type { Workspace } from "../api/types";

interface Props {
  workspace: Workspace;
  onSelectTopic: (workspaceId: number, topicId: number) => void;
}

export function WorkspaceSection({ workspace, onSelectTopic }: Props) {
  const [open, setOpen] = useState(false);
  const { data: topics } = useTopicsInWorkspace(open ? workspace.id : null);
  return (
    <div className="px-3 py-1">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 text-xs text-text-dim hover:text-text w-full"
      >
        <span>{open ? "▾" : "▸"}</span>
        <span>{workspace.name}</span>
        {topics && <span className="ml-auto">{topics.length}</span>}
      </button>
      {open && topics && (
        <div className="pl-4 mt-1 space-y-0.5">
          {topics.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => onSelectTopic(workspace.id, t.id)}
              className="text-xs text-text-dim hover:text-text block w-full text-left"
            >
              {t.title}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

Create `frontend/src/workspace/CreateWorkspaceInline.tsx`:

```typescript
import { useState } from "react";

interface Props {
  onSubmit: (name: string) => void;
  onCancel: () => void;
}

export function CreateWorkspaceInline({ onSubmit, onCancel }: Props) {
  const [value, setValue] = useState("");
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (value.trim()) onSubmit(value.trim());
      }}
      className="px-3 py-2 border-b border-border"
    >
      <input
        autoFocus
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Escape") onCancel();
        }}
        placeholder="工作区名字…"
        className="w-full text-sm bg-transparent border border-border rounded px-2 py-1 focus:outline-none focus:border-accent"
      />
    </form>
  );
}
```

Create `frontend/src/workspace/MembersList.tsx`:

```typescript
import type { WorkspaceMember } from "../api/types";

interface Props {
  members: WorkspaceMember[];
  onInvite: () => void;
}

export function MembersList({ members, onInvite }: Props) {
  return (
    <div className="px-3 py-2 border-t border-border">
      <div className="text-xs uppercase tracking-wider text-text-dim mb-2">成员</div>
      <div className="space-y-1">
        {members.map((m) =>
          m.kind === "human" ? (
            <div key={`h-${m.id}`} className="flex items-center gap-2 text-sm">
              <span className="text-text">{m.name}</span>
              {m.role === "owner" && (
                <span className="text-[10px] uppercase text-text-dim">owner</span>
              )}
            </div>
          ) : (
            <div key={`a-${m.id}`} className="flex items-center gap-2 text-sm">
              <span className="text-text">{m.role}</span>
              <span className="text-[10px] text-text-dim">
                agent · {m.started_by_name} 启动
              </span>
            </div>
          )
        )}
      </div>
      <button
        type="button"
        onClick={onInvite}
        className="text-xs text-text-dim hover:text-text mt-2"
      >
        ＋ 邀请成员
      </button>
    </div>
  );
}
```

- [ ] **Step 14.3: Rewrite `Sidebar.tsx`**

Replace the entire file. `ChannelRow` becomes `TopicRow` (just a rename, same internals):

```typescript
import { WorkspaceSwitcher } from "../workspace/WorkspaceSwitcher";
import { WorkspaceSection } from "../workspace/WorkspaceSection";
import { CreateWorkspaceInline } from "../workspace/CreateWorkspaceInline";
import { MembersList } from "../workspace/MembersList";
import type { TopicDTO, Workspace, WorkspaceMember } from "../api/types";

interface Props {
  activeWorkspace: Workspace | undefined;
  workspaces: Workspace[];
  topics: TopicDTO[];
  members: WorkspaceMember[];
  activeTopicId: number | null;
  onSelectTopic: (id: number) => void;
  onCreateTopic: (t: { slug: string; title: string }) => void;
  onSwitchWorkspace: (id: number) => void;
  onCreateWorkspace: (name: string) => void;
  onInviteMember: () => void;
}

interface TopicRowProps {
  topic: TopicDTO;
  active: boolean;
  onSelect: () => void;
}

function TopicRow({ topic, active, onSelect }: TopicRowProps) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className={`flex items-baseline gap-2 w-full text-left px-3 py-1.5 hover:bg-hover ${
        active ? "bg-hover" : ""
      }`}
    >
      <span className="font-mono text-[10px] uppercase tracking-wider text-text-dim w-12 shrink-0">
        {topic.slug.slice(0, 6).toUpperCase()}
      </span>
      <span className="text-sm text-text truncate">{topic.title}</span>
    </button>
  );
}

import { useState } from "react";

export function Sidebar(props: Props) {
  const [creating, setCreating] = useState(false);
  const otherWorkspaces = props.workspaces.filter(
    (w) => w.id !== props.activeWorkspace?.id
  );
  return (
    <div className="h-full flex flex-col">
      <WorkspaceSwitcher
        workspaces={props.workspaces}
        activeId={props.activeWorkspace?.id ?? -1}
        onSelect={props.onSwitchWorkspace}
        onCreate={() => setCreating(true)}
      />
      {creating && (
        <CreateWorkspaceInline
          onSubmit={(name) => {
            props.onCreateWorkspace(name);
            setCreating(false);
          }}
          onCancel={() => setCreating(false)}
        />
      )}

      <div className="px-3 py-2 border-b border-border">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs uppercase tracking-wider text-text-dim">话题</span>
          <span className="text-xs text-text-dim">{props.topics.length}</span>
          <button
            type="button"
            aria-label="新建话题"
            title="新建话题"
            onClick={() =>
              props.onCreateTopic({
                slug: `topic-${Date.now().toString(36)}`,
                title: "新话题",
              })
            }
            className="text-xs text-text-dim hover:text-text"
          >
            ＋
          </button>
        </div>
        {props.topics.length === 0 ? (
          <div className="text-xs text-text-dim italic">还没有话题</div>
        ) : (
          <div className="space-y-0.5">
            {props.topics.map((t) => (
              <TopicRow
                key={t.id}
                topic={t}
                active={props.activeTopicId === t.id}
                onSelect={() => props.onSelectTopic(t.id)}
              />
            ))}
          </div>
        )}
      </div>

      {otherWorkspaces.length > 0 && (
        <div className="border-b border-border py-1">
          {otherWorkspaces.map((w) => (
            <WorkspaceSection
              key={w.id}
              workspace={w}
              onSelectTopic={(wsId, topicId) => {
                props.onSwitchWorkspace(wsId);
                props.onSelectTopic(topicId);
              }}
            />
          ))}
        </div>
      )}

      <div className="flex-1" />
      <MembersList members={props.members} onInvite={props.onInviteMember} />
    </div>
  );
}
```

Also: any test files still importing `ChannelRow` must be updated to `TopicRow`. Grep: `grep -rn "ChannelRow" frontend/`.

- [ ] **Step 14.4: Run frontend tests**

Run: `cd frontend && pnpm test --run -- Sidebar`

- [ ] **Step 14.5: Commit**

```bash
git add frontend/src/layout/Sidebar.tsx frontend/src/layout/Sidebar.test.tsx frontend/src/workspace/
git commit -m "$(cat <<'EOF'
feat(sidebar): workspace switcher + nested sections + members list

Top of sidebar: WorkspaceSwitcher. Active workspace renders its topics
with the renamed TopicRow (was ChannelRow). Other workspaces are
collapsed WorkspaceSections that lazy-load topics on expand. Bottom:
MembersList showing humans and agents in one panel, with an invite
trigger.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 15: Invite dialog UI

**Files:**
- Create: `frontend/src/workspace/InviteDialog.tsx`
- Create: `frontend/src/workspace/InviteDialog.test.tsx`

- [ ] **Step 15.1: Write test**

```typescript
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { InviteDialog } from "./InviteDialog";

describe("InviteDialog", () => {
  it("renders join URL + copies on click", async () => {
    const writeText = vi.fn();
    Object.assign(navigator, { clipboard: { writeText } });
    render(
      <InviteDialog
        workspaceName="我的工作区"
        joinUrl="https://lets.app/join/abc123"
        onClose={vi.fn()}
      />
    );
    expect(screen.getByText(/join\/abc123/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("复制"));
    expect(writeText).toHaveBeenCalledWith("https://lets.app/join/abc123");
  });
});
```

- [ ] **Step 15.2: Run to verify failure**

- [ ] **Step 15.3: Implement**

```typescript
interface Props {
  workspaceName: string;
  joinUrl: string;
  onClose: () => void;
}

export function InviteDialog({ workspaceName, joinUrl, onClose }: Props) {
  return (
    <div className="fixed inset-0 bg-black/40 grid place-items-center z-50">
      <div className="bg-bg border border-border rounded p-6 max-w-md w-full">
        <h2 className="text-lg font-[var(--font-display)] mb-3">
          邀请新成员加入「{workspaceName}」
        </h2>
        <p className="text-sm text-text-dim mb-3">把这个链接发给 ta：</p>
        <div className="flex items-center gap-2 mb-4">
          <code className="flex-1 bg-hover px-3 py-2 rounded text-xs break-all">
            {joinUrl}
          </code>
          <button
            type="button"
            onClick={() => navigator.clipboard.writeText(joinUrl)}
            className="text-xs px-3 py-2 border border-border rounded hover:bg-hover"
          >
            复制
          </button>
        </div>
        <p className="text-xs text-text-dim mb-4">
          收到链接的人点击进入，登录 GitHub 后会自动成为成员。
        </p>
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="text-sm px-4 py-2 border border-border rounded hover:bg-hover"
          >
            完成
          </button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 15.4: Run to verify pass**

- [ ] **Step 15.5: Commit**

```bash
git add frontend/src/workspace/InviteDialog.tsx frontend/src/workspace/InviteDialog.test.tsx
git commit -m "$(cat <<'EOF'
feat(invite): InviteDialog with copy-to-clipboard join URL

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 16: MoveTopicMenu + /join landing page

**Files:**
- Create: `frontend/src/workspace/MoveTopicMenu.tsx` + test
- Create: `frontend/src/join/JoinTokenPage.tsx` + test

- [ ] **Step 16.1: MoveTopicMenu test + impl**

`frontend/src/workspace/MoveTopicMenu.test.tsx`:

```typescript
it("lists destination workspaces and triggers onMove", () => {
  const onMove = vi.fn();
  render(
    <MoveTopicMenu
      currentWorkspaceId={1}
      workspaces={[
        { id: 1, name: "A", ... },
        { id: 2, name: "B", ... },
      ]}
      onMove={onMove}
    />
  );
  fireEvent.click(screen.getByText("B"));
  expect(onMove).toHaveBeenCalledWith(2);
});
```

`MoveTopicMenu.tsx`:

```typescript
import type { Workspace } from "../api/types";

interface Props {
  currentWorkspaceId: number;
  workspaces: Workspace[];
  onMove: (workspaceId: number) => void;
}

export function MoveTopicMenu({ currentWorkspaceId, workspaces, onMove }: Props) {
  const destinations = workspaces.filter((w) => w.id !== currentWorkspaceId);
  if (destinations.length === 0) {
    return <div className="text-xs text-text-dim">没有其他工作区</div>;
  }
  return (
    <div className="border border-border rounded bg-bg shadow p-1 min-w-[160px]">
      {destinations.map((w) => (
        <button
          key={w.id}
          type="button"
          onClick={() => onMove(w.id)}
          className="block w-full text-left text-sm px-3 py-1.5 hover:bg-hover rounded"
        >
          {w.name}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 16.2: JoinTokenPage test + impl**

`frontend/src/join/JoinTokenPage.test.tsx`:

```typescript
it("shows loading then redirects via window.location on success", async () => {
  // Setup MSW handler for POST /api/invites/abc123/accept → { workspace_id: 42 }
  render(<JoinTokenPage token="abc123" />);
  await waitFor(() => {
    expect(window.location.pathname).toMatch(/\?workspace=42|workspace=42/);
  });
});
```

`JoinTokenPage.tsx`:

```typescript
import { useEffect, useState } from "react";
import { apiClient } from "../api/client";

interface Props {
  token: string;
}

export function JoinTokenPage({ token }: Props) {
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    apiClient
      .post<{ workspace_id: number }>(`/api/invites/${token}/accept`)
      .then((r) => {
        window.location.href = `/?workspace=${r.data.workspace_id}`;
      })
      .catch(() => setError("邀请链接无效或已过期"));
  }, [token]);
  return (
    <div className="grid place-items-center min-h-screen text-sm text-text-dim">
      {error ?? "加入工作区中…"}
    </div>
  );
}
```

Wire `JoinTokenPage` into `App.tsx` routing: if the URL is `/join/:token`, render this component (the backend's `/join/:token` route is the unauthenticated entry point; once cookie is set and SPA loads, this client component runs the accept call. **Note:** for the SPA-only flow, the backend `/join/:token` only handles the redirect-to-login case; if authenticated, it serves the SPA which then runs `JoinTokenPage`. Adjust the backend route in step 12 if needed so an authenticated `/join/:token` request returns the SPA HTML rather than a 303 — see verification in step 16.4.)

- [ ] **Step 16.3: Reconcile backend `/join/:token`**

In `app/main.py`, change the route added in Task 12: when authenticated, instead of redirecting, return the SPA index HTML (the same response the root `GET /` returns). This way the SPA picks up the token from `window.location.pathname` and runs `JoinTokenPage`.

```python
@app.get("/join/{token}")
def join_by_token(
    token: str,
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
):
    from .auth import verify_session
    if not lets_session or verify_session(lets_session) is None:
        return RedirectResponse(
            url=f"/login?redirect=/join/{token}", status_code=303
        )
    return _serve_spa()  # whatever helper serves the SPA; existing GET / logic
```

Update Task 12's test to reflect: authenticated GET `/join/:token` returns HTML, not a redirect. The actual `accept` call now happens client-side via the SPA.

- [ ] **Step 16.4: Run tests**

Run: `cd frontend && pnpm test --run` and `pytest tests/test_workspace_invites_api.py -v`

- [ ] **Step 16.5: Commit**

```bash
git add frontend/src/workspace/MoveTopicMenu.tsx frontend/src/workspace/MoveTopicMenu.test.tsx \
        frontend/src/join/JoinTokenPage.tsx frontend/src/join/JoinTokenPage.test.tsx \
        app/main.py tests/test_workspace_invites_api.py
git commit -m "$(cat <<'EOF'
feat(invite): MoveTopicMenu + JoinTokenPage SPA flow

MoveTopicMenu lets a topic owner pick a destination workspace.
JoinTokenPage runs the accept API call after the SPA loads, so the
backend /join route only needs to handle redirect-to-login then serve
the SPA when authenticated.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 17: CLI — `lets add --workspace`

**Files:**
- Modify: `app/gateway.py`
- Modify: `tests/test_gateway.py` (or wherever gateway args are tested; create one if absent)

- [ ] **Step 17.1: Write/extend test**

Locate (or create) `tests/test_gateway_add.py`:

```python
def test_add_parses_workspace_flag():
    import sys
    from app import gateway
    argv = ["claude", "--workspace", "user-auth"]
    args = gateway._parse_add_args(argv)
    assert args.workspace == "user-auth"
```

- [ ] **Step 17.2: Run to verify failure**

- [ ] **Step 17.3: Modify `app/gateway.py`**

Find the `_add` function (the implementation of `lets add`). Add `--workspace` argparse argument:

```python
parser.add_argument(
    "--workspace",
    default=os.environ.get("LETS_WORKSPACE"),
    help="Workspace slug to join (default: caller's first owned workspace)",
)
```

When calling `POST /api/auth/device-flow/start`, if `args.workspace` is set, the gateway must first resolve it to an id by calling `GET /api/workspaces` (filter on slug). Pass `workspace_id` as query param.

```python
def _resolve_workspace_id(host: str, token: str | None, slug: str | None) -> int | None:
    if slug is None:
        return None
    workspaces = _http(host, token or "", "GET", "/api/workspaces", None)
    for w in workspaces:
        if w["slug"] == slug:
            return int(w["id"])
    raise SystemExit(f"workspace not found: {slug}")
```

Then thread the `workspace_id` into the device-flow start call.

- [ ] **Step 17.4: Update the install script gen in `app/main.py` (`/install/gateway.sh` route)** to pass `--workspace` through `LETS_WORKSPACE` env var if set:

```bash
WORKSPACE_ARGS=()
if [ -n "${LETS_WORKSPACE:-}" ]; then
  WORKSPACE_ARGS=(--workspace "$LETS_WORKSPACE")
fi
```

(Mirror the MODEL_ARGS pattern from the recent install fix.)

- [ ] **Step 17.5: Run tests**

Run: `pytest tests/test_gateway_add.py -v`

- [ ] **Step 17.6: Commit**

```bash
git add app/gateway.py app/main.py tests/test_gateway_add.py
git commit -m "$(cat <<'EOF'
feat(cli): lets add --workspace slug binds agent to a workspace

The flag (or LETS_WORKSPACE env var) resolves the slug to an id and
passes it to device-flow/start. The install one-liner mirrors the
MODEL_ARGS bash-3.2-safe expansion pattern.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 18: E2E test + full repo sweep

**Files:**
- Create: `tests/test_e2e_workspace_invite_flow.py`
- Modify: any remaining files still referencing "project" / "channel" in user-visible strings

- [ ] **Step 18.1: Write E2E test**

```python
def test_full_invite_flow(temp_db, client):
    # Alice
    _login(client, "alice")
    ws = client.post("/api/workspaces", json={"name": "用户认证"}).json()
    # Onboarding gave her '我的工作区' + a 主频道; she now has 2 workspaces
    all_mine = client.get("/api/workspaces").json()
    assert {w["name"] for w in all_mine} == {"我的工作区", "用户认证"}
    # Create a topic in the new workspace
    topic = client.post(
        f"/api/workspaces/{ws['id']}/topics",
        json={"slug": "oauth", "title": "OAuth 流程"},
    ).json()
    # Invite Bob
    inv = client.post(f"/api/workspaces/{ws['id']}/invites", json={}).json()

    # Bob accepts
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    r = client.post(f"/api/invites/{inv['token']}/accept")
    assert r.json()["workspace_id"] == ws["id"]
    # Bob sees the workspace
    bob_ws = client.get("/api/workspaces").json()
    assert ws["id"] in [w["id"] for w in bob_ws]
    # Bob sees the topic
    topics = client.get(f"/api/workspaces/{ws['id']}/topics").json()
    assert topic["id"] in [t["id"] for t in topics]
    # Bob posts a message
    msg = client.post(
        "/api/messages",
        json={
            "topic_id": topic["id"],
            "kind": "chat",
            "body": "hello from Bob",
        },
    )
    assert msg.status_code == 200

    # Alice moves the topic to her '我的工作区'
    client.post("/api/auth/logout")
    _login(client, "alice")
    my_ws_id = [w["id"] for w in client.get("/api/workspaces").json() if w["name"] == "我的工作区"][0]
    moved = client.patch(
        f"/api/topics/{topic['id']}", json={"workspace_id": my_ws_id}
    )
    assert moved.json()["workspace_id"] == my_ws_id

    # Bob is no longer a member of 我的工作区, so he can't see the topic anymore
    client.post("/api/auth/logout")
    _login(client, "bob", "b@b")
    bob_topics_in_old = client.get(f"/api/workspaces/{ws['id']}/topics").json()
    assert topic["id"] not in [t["id"] for t in bob_topics_in_old]
    r = client.get(f"/api/topics/{topic['id']}/messages")
    assert r.status_code == 403  # not a member of 我的工作区
```

- [ ] **Step 18.2: Run E2E**

Run: `pytest tests/test_e2e_workspace_invite_flow.py -v`

- [ ] **Step 18.3: Final sweep — ChannelRow / channel CSS / "project" residue**

Run: `grep -rn "ChannelRow\|className.*channel-" frontend/src/ 2>/dev/null` — rename remaining instances to TopicRow / topic-.

Run: `grep -rn "project_id\|projects" app/ tests/ 2>/dev/null | grep -v ".pyc" | grep -v "test_e2e"` — anything left, fix.

Run: `pytest tests/ -x -q` and `cd frontend && pnpm test --run` and `pnpm typecheck` to make sure nothing's broken.

- [ ] **Step 18.4: Commit**

```bash
git add tests/test_e2e_workspace_invite_flow.py [other modified files]
git commit -m "$(cat <<'EOF'
test(e2e): full workspace + invite + topic move flow

Asserts the spec's central scenario end-to-end: Alice creates a
workspace, invites Bob, Bob accepts and chats, Alice moves the topic
elsewhere, Bob loses access. Also sweeps the last ChannelRow /
project residues.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review Checklist (run before handing off)

- [ ] Every spec section in §3-§7 has a task implementing it
- [ ] No "TBD", "TODO", "implement later" left in this plan
- [ ] All function names, types, route paths match between tasks (e.g. `require_workspace_member` is the same name everywhere)
- [ ] Each task ends with a green test + a single commit
- [ ] DB schema (Task 1) covers all columns referenced by later tasks
- [ ] No task references a helper that wasn't defined in an earlier task

---

**Plan complete and saved to** `docs/superpowers/plans/2026-05-21-workspace-and-membership.md`.
