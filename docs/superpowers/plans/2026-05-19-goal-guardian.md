# Goal Guardian Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship v1.5c-2 Goal Guardian: per-topic Goal + Task Tree entities + agent-self-reported Drift Nudges with three resolutions (spinoff / return / dismiss). End-to-end success scenario in spec §10.

**Architecture:** Three new SQLite tables (`task_trees`, `task_items`, `drift_nudges`) plus a `topics.mode` column. Six new REST endpoints + four new MCP tools + extension of `GET /api/topics/{id}/messages` response from `MessageDTO[]` to `{messages, drift_context}`. Frontend rewires three existing components (`TaskTreePanel`, `NudgeMessage`, `TaskTreeProposalMessage`) and adds one new component (`GoalProposalMessage`) + one modal (`SpinoffDialog`). A `lets-goal-guardian` skill captures agent-side discipline.

**Tech Stack:** Python 3.13 + FastAPI + SQLite (stdlib) + Pydantic (existing backend) · React 18 + TS + Tailwind v4 + TanStack Query + MSW (existing frontend) · pytest · vitest · Playwright.

**Spec reference:** `docs/superpowers/specs/2026-05-19-goal-guardian-design.md` (read this once before starting Task 1; do not re-read it per task — this plan is self-contained).

**Prerequisite check:**
- Branch is up to date with `main` containing Track F + Phase 12 auth (verify `git log --oneline -5` shows `2b66ea5 docs(spec): v1.5c-2 Goal Guardian design`).
- `pytest -q` reports 182 passing on baseline. `cd frontend && pnpm test --run` reports 52 passing.
- `frontend/src/messages/TaskTreeProposalMessage.tsx` and `frontend/src/messages/NudgeMessage.tsx` already exist (rendered from fixtures during Track F).
- `messages.type` CHECK already accepts `nudge`, `task_tree_proposal`, `goal_proposal`.

---

## File Structure

**Backend — created:**
- `tests/test_task_trees_schema.py` — schema-shape tests for the three new tables
- `tests/test_task_trees_api.py` — REST endpoint tests for `/api/topics/{id}/task-tree`, `/api/task-items/*`, `/api/topics/{id}/goal`
- `tests/test_drift_nudges_api.py` — REST endpoint tests for `/api/nudges/{id}/resolve`
- `tests/test_drift_context.py` — tests for the extended `topic_stream` response shape
- `tests/test_goal_guardian_mcp.py` — MCP tool integration tests (`propose_goal`, `propose_task_tree`, `update_task_status`, `post_nudge`)
- `tests/test_e2e_goal_guardian.py` — full §10 success-criteria scenario as a pytest

**Backend — modified:**
- `app/db.py` — three new table DDLs in `init_db()` + `_migrate_topics_mode()` helper + call it from `init_db()`
- `app/messages.py` — no schema change (typed messages already accepted); add `topic_stream_v2()` helper returning `dict` with `drift_context`
- `app/main.py` — six new endpoints + change `get_topic_messages` return type to `dict`
- `app/mcp_server.py` — four new MCP tools

**Backend — created:**
- `app/task_trees.py` — task-tree / task-item domain helpers (DB access, dataclass-like dict returns)
- `app/drift.py` — drift-context computation + `post_nudge` core (used by MCP tool and direct API)

**Frontend — created:**
- `frontend/src/api/taskTreeTypes.ts` — `TaskTreeDTO`, `TaskItemDTO`, `DriftContextDTO`, `NudgeResolveInput`, `NudgeResolution`
- `frontend/src/api/taskTreeQueries.ts` — `useTopicTaskTree`, `useAddTaskItem`, `useUpdateTaskItem`, `useAdoptTaskTreeProposal`, `useAdoptGoalProposal`, `useResolveNudge`
- `frontend/src/messages/GoalProposalMessage.tsx` + `.test.tsx` — new typed-message component
- `frontend/src/nudge/SpinoffDialog.tsx` + `.test.tsx` — modal for "独立成新 topic" path

**Frontend — modified:**
- `frontend/src/api/types.ts` — extend `MessageDTO` re-export with `TaskTreeProposalMeta` already present; nothing new here
- `frontend/src/api/queries.ts` — change `useTopicMessages` return type from `MessageDTO[]` to `{messages, drift_context}` plus a backward-compat data accessor; export `useTopicStream` unchanged
- `frontend/src/api/client.ts` — no change
- `frontend/src/topic/TopicView.tsx` — read `data.messages` instead of `data`; pass `drift_context` to Composer / Stream (optional, can defer)
- `frontend/src/messages/Message.tsx` — add `goal_proposal` dispatch case
- `frontend/src/messages/TaskTreeProposalMessage.tsx` — add "Adopt as task tree" button + `useAdoptTaskTreeProposal` call
- `frontend/src/messages/NudgeMessage.tsx` — three quick-action buttons + resolved-state footer + integration with `SpinoffDialog`
- `frontend/src/context/TaskTreePanel.tsx` — rewrite from hardcoded fixture to `useTopicTaskTree` + true-tree rendering + checkbox + add-row
- `frontend/src/context/GoalDetailPanel.tsx` — wire to `useTopicTaskTree().tree.goal_*` instead of hardcoded
- `frontend/src/context/TopicContext.tsx` — remove the hardcoded TaskTreePanel/GoalDetailPanel props; the components now self-fetch
- `frontend/src/fixtures/handlers.ts` — add MSW handlers for the new endpoints + `drift_context` in the messages endpoint
- `frontend/src/fixtures/seed.ts` — add a seeded task_tree + goal for topic 1
- `frontend/e2e/ppt-scenario.spec.ts` — adapt assertions that called `getByText("ai-memory-talk.pptx")` since GoalDetailPanel now reads from query

**Skill — created:**
- `.claude/skills/lets-goal-guardian/SKILL.md` — agent-side discipline for drift detection (spec §7.1)

---

## Conventions

- **TDD per task**: each task starts with a failing test or test-update, then minimal implementation, then verify pass, then commit.
- **Backend commits**: prefix `feat(goal-guardian):`, `test(goal-guardian):`, `chore(goal-guardian):`.
- **Frontend commits**: prefix `feat(frontend):`, `test(frontend):`.
- **`pnpm` invocation**: the user's zsh has an `nvm` lazy-loader that recurses on `pnpm` — use the absolute path `/Users/jacky/.nvm/versions/node/v22.17.0/bin/pnpm` in all bash steps that call `pnpm`. Or call `vite` / `vitest` from `node_modules/.bin` directly.
- **Bash localhost curls**: the dev machine exports `http_proxy=127.0.0.1:7890`; always use `curl --noproxy '*'` for localhost.
- **Backend pytest**: run as `.venv/bin/pytest tests/specific_test.py -v` for scoped, `.venv/bin/pytest -q` for full.
- **Co-author trailer**: every commit message uses heredoc with `Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>` to match repo convention.
- **Branch**: work on `main` directly (the user has been merging directly to main since Track F). Verify `git rev-parse --abbrev-ref HEAD == 'main'` at the start of each task.
- **API request shape change**: the breaking change in `topic_stream` response from `MessageDTO[]` to `{messages, drift_context}` happens in **Task 9** (one task touches both backend response shape + all frontend consumers). After Task 9, all subsequent frontend tasks consume the new shape.
- **Backward compat decision**: no version flag, no fallback. The whole repo is in one cut.

---

## Phase Milestones

| Phase | Tasks | Demo |
|-------|-------|------|
| **A. Schema + helpers** | T1–T3 | `task_trees`, `task_items`, `drift_nudges` migrate + `_migrate_topics_mode` adds the column; helpers can CRUD via pytest |
| **B. REST endpoints** | T4–T8 | All six new endpoints land with pytest coverage |
| **C. `topic_stream` extension** | T9 | Single breaking change: response shape updated, all existing tests + 1 frontend hook adapted |
| **D. MCP tools** | T10–T13 | Four new tools registered + integration-tested through MCP transport |
| **E. Frontend: data layer** | T14–T15 | New queries hook + MSW fixtures |
| **F. Frontend: components** | T16–T20 | TaskTreePanel rewrite + GoalDetailPanel wire + NudgeMessage actions + SpinoffDialog + GoalProposalMessage |
| **G. Skill + E2E** | T21–T22 | `lets-goal-guardian` skill committed + pytest e2e + Playwright e2e |

---

## Task 1: `topics.mode` column + migration

**Files:**
- Modify: `app/db.py` (extend `init_db()` and add migration helper)
- Create: `tests/test_topics_mode_migration.py`

- [ ] **Step 1.1: Write failing test**

Create `tests/test_topics_mode_migration.py`:
```python
def test_topics_mode_column_exists(client):
    """After init_db, topics.mode should default to 'exploratory'."""
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(topics)").fetchall()}
    assert "mode" in cols


def test_topics_mode_default_exploratory(client):
    from app.db import connect
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO topics (slug, title) VALUES ('mode-default', 'x')"
        )
        topic_id = cur.lastrowid
        row = conn.execute("SELECT mode FROM topics WHERE id = ?", (topic_id,)).fetchone()
    assert row["mode"] == "exploratory"


def test_topics_mode_check_constraint(client):
    """topics.mode must be 'exploratory' or 'actionable'."""
    import sqlite3
    from app.db import connect
    with connect() as conn:
        try:
            conn.execute(
                "INSERT INTO topics (slug, title, mode) VALUES ('bad', 'x', 'bogus')"
            )
            raised = False
        except sqlite3.IntegrityError:
            raised = True
    assert raised, "expected CHECK constraint to reject mode='bogus'"
```

- [ ] **Step 1.2: Run test (should fail)**

```bash
.venv/bin/pytest tests/test_topics_mode_migration.py -v
```

Expected: 3 fails — "no such column: mode" or KeyError on "mode".

- [ ] **Step 1.3: Add migration helper + call it**

Edit `app/db.py`. After the existing `_migrate_humans_github` function, add:

```python
def _migrate_topics_mode(conn) -> None:
    """Non-destructive migration: ensure topics has mode column with CHECK."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(topics)").fetchall()}
    if "mode" in cols:
        return
    # SQLite cannot add a column with a CHECK constraint via ALTER. Rebuild.
    conn.execute("""
        CREATE TABLE topics_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            project_id INTEGER,
            mode TEXT NOT NULL DEFAULT 'exploratory'
                CHECK (mode IN ('exploratory', 'actionable')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        INSERT INTO topics_new (id, slug, title, project_id, created_at, updated_at)
        SELECT id, slug, title, project_id, created_at, updated_at FROM topics
    """)
    conn.execute("DROP TABLE topics")
    conn.execute("ALTER TABLE topics_new RENAME TO topics")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_topics_project ON topics(project_id)")
```

In `init_db()`, find the line `_migrate_humans_github(conn)` and add a new line below it:

```python
        _migrate_humans_github(conn)
        _migrate_topics_mode(conn)
```

- [ ] **Step 1.4: Run test (should pass)**

```bash
.venv/bin/pytest tests/test_topics_mode_migration.py -v
```

Expected: 3 pass.

- [ ] **Step 1.5: Run full backend test suite to confirm no regression**

```bash
.venv/bin/pytest -q
```

Expected: 185 pass (182 baseline + 3 new). If existing tests break (likely from changing CREATE TABLE topics), investigate — the migration must keep the existing schema columns plus add `mode`.

- [ ] **Step 1.6: Commit**

```bash
git add app/db.py tests/test_topics_mode_migration.py
git commit -m "$(cat <<'EOF'
feat(goal-guardian): topics.mode column + migration

New CHECK constraint (exploratory|actionable), default 'exploratory'.
SQLite cannot ALTER a CHECK; uses idempotent table-rebuild like the
existing _migrate_humans_github pattern.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: `task_trees` + `task_items` schema

**Files:**
- Modify: `app/db.py` (DDL inside `init_db()`)
- Create: `tests/test_task_trees_schema.py`

- [ ] **Step 2.1: Write failing test**

Create `tests/test_task_trees_schema.py`:
```python
def test_task_trees_table_exists(client):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(task_trees)").fetchall()}
    expected = {
        "id", "topic_id", "goal_artifact_id", "goal_spec_text",
        "version", "approved_at", "approved_by_human_id",
        "proposal_message_id", "created_at", "updated_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_task_trees_topic_id_unique(client):
    """One topic can only have one task_tree row."""
    import sqlite3
    from app.db import connect
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('tt-uniq', 'x')")
        tid = cur.lastrowid
        conn.execute("INSERT INTO task_trees (topic_id) VALUES (?)", (tid,))
        try:
            conn.execute("INSERT INTO task_trees (topic_id) VALUES (?)", (tid,))
            raised = False
        except sqlite3.IntegrityError:
            raised = True
    assert raised


def test_task_items_table_exists(client):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(task_items)").fetchall()}
    expected = {
        "id", "task_tree_id", "parent_item_id", "title",
        "owner_human_id", "owner_agent_instance_id",
        "status", "position", "created_at", "updated_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_task_items_owner_xor_constraint(client):
    """task_items: owner_human_id and owner_agent_instance_id cannot both be set."""
    import sqlite3
    from app.db import connect
    from app.identity import ensure_human, ensure_agent_instance

    hid = ensure_human("Owner Test")
    aid = ensure_agent_instance(role="claude", human_id=hid, device_label="dev")

    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('tt-owner', 'x')")
        tid = cur.lastrowid
        cur = conn.execute("INSERT INTO task_trees (topic_id) VALUES (?)", (tid,))
        tree_id = cur.lastrowid
        try:
            conn.execute(
                """INSERT INTO task_items (task_tree_id, title,
                                           owner_human_id, owner_agent_instance_id)
                   VALUES (?, ?, ?, ?)""",
                (tree_id, "both owners", hid, aid),
            )
            raised = False
        except sqlite3.IntegrityError:
            raised = True
    assert raised


def test_task_items_status_check(client):
    """task_items.status: pending|active|done only."""
    import sqlite3
    from app.db import connect
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('tt-status', 'x')")
        tid = cur.lastrowid
        cur = conn.execute("INSERT INTO task_trees (topic_id) VALUES (?)", (tid,))
        tree_id = cur.lastrowid
        try:
            conn.execute(
                "INSERT INTO task_items (task_tree_id, title, status) VALUES (?, ?, ?)",
                (tree_id, "bogus status", "in-progress"),
            )
            raised = False
        except sqlite3.IntegrityError:
            raised = True
    assert raised
```

- [ ] **Step 2.2: Run test (should fail)**

```bash
.venv/bin/pytest tests/test_task_trees_schema.py -v
```

Expected: 5 fails ("no such table: task_trees" etc.).

- [ ] **Step 2.3: Add DDLs to `init_db()`**

In `app/db.py`, find the `init_db()` function. Inside its `executescript` block (or sequential `execute` calls — match existing style), add the two new tables. They should come after `messages` table creation:

```python
            CREATE TABLE IF NOT EXISTS task_trees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL UNIQUE,
                goal_artifact_id INTEGER,
                goal_spec_text TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                approved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                approved_by_human_id INTEGER,
                proposal_message_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics(id),
                FOREIGN KEY (goal_artifact_id) REFERENCES artifacts(id),
                FOREIGN KEY (approved_by_human_id) REFERENCES humans(id),
                FOREIGN KEY (proposal_message_id) REFERENCES messages(id)
            );
            CREATE INDEX IF NOT EXISTS idx_task_trees_topic ON task_trees(topic_id);

            CREATE TABLE IF NOT EXISTS task_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_tree_id INTEGER NOT NULL,
                parent_item_id INTEGER,
                title TEXT NOT NULL,
                owner_human_id INTEGER,
                owner_agent_instance_id INTEGER,
                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'active', 'done')),
                position INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_tree_id) REFERENCES task_trees(id),
                FOREIGN KEY (parent_item_id) REFERENCES task_items(id),
                FOREIGN KEY (owner_human_id) REFERENCES humans(id),
                FOREIGN KEY (owner_agent_instance_id) REFERENCES agent_instances(id),
                CHECK (NOT (owner_human_id IS NOT NULL AND owner_agent_instance_id IS NOT NULL))
            );
            CREATE INDEX IF NOT EXISTS idx_task_items_tree ON task_items(task_tree_id, position);
            CREATE INDEX IF NOT EXISTS idx_task_items_parent ON task_items(parent_item_id);
```

- [ ] **Step 2.4: Run test (should pass)**

```bash
.venv/bin/pytest tests/test_task_trees_schema.py -v
```

Expected: 5 pass.

- [ ] **Step 2.5: Run full suite**

```bash
.venv/bin/pytest -q
```

Expected: 190 pass (185 + 5 new).

- [ ] **Step 2.6: Commit**

```bash
git add app/db.py tests/test_task_trees_schema.py
git commit -m "$(cat <<'EOF'
feat(goal-guardian): task_trees + task_items schema

task_trees has UNIQUE(topic_id) for 1:1 topic↔tree relation.
task_items uses self-referencing parent_item_id for true tree shape
and a CHECK constraint forbidding both owner_human_id and
owner_agent_instance_id being set simultaneously.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: `drift_nudges` schema + `app/task_trees.py` + `app/drift.py` helpers

**Files:**
- Modify: `app/db.py` (DDL inside `init_db()`)
- Create: `app/task_trees.py`
- Create: `app/drift.py`
- Create: `tests/test_drift_nudges_schema.py`

- [ ] **Step 3.1: Write failing test**

Create `tests/test_drift_nudges_schema.py`:
```python
def test_drift_nudges_table_exists(client):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(drift_nudges)").fetchall()}
    expected = {
        "id", "topic_id", "nudge_message_id", "triggered_by_agent_instance_id",
        "drift_window_start_message_id", "drift_window_end_message_id",
        "drift_summary", "resolved_at", "resolved_by", "resolved_to_topic_id",
        "created_at",
    }
    assert expected.issubset(cols), f"missing: {expected - cols}"


def test_drift_nudges_resolved_by_check(client):
    import sqlite3
    from app.db import connect
    from app.identity import ensure_human
    from app.messages import post_message

    hid = ensure_human("Drift Test")
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('drift-rb', 'x')")
        tid = cur.lastrowid
    mid = post_message(
        topic_id=tid, type="nudge",
        actor_type="system", actor_id=None,
        body="off topic", metadata={"reason": "test"},
    )
    with connect() as conn:
        try:
            conn.execute(
                """INSERT INTO drift_nudges (topic_id, nudge_message_id, resolved_by)
                   VALUES (?, ?, ?)""",
                (tid, mid, "bogus"),
            )
            raised = False
        except sqlite3.IntegrityError:
            raised = True
    assert raised


def test_drift_nudges_nudge_message_id_unique(client):
    """A single message can back at most one drift_nudges row."""
    import sqlite3
    from app.db import connect
    from app.messages import post_message

    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('drift-uniq', 'x')")
        tid = cur.lastrowid
    mid = post_message(
        topic_id=tid, type="nudge",
        actor_type="system", actor_id=None,
        body="off topic", metadata={},
    )
    with connect() as conn:
        conn.execute(
            "INSERT INTO drift_nudges (topic_id, nudge_message_id) VALUES (?, ?)",
            (tid, mid),
        )
        try:
            conn.execute(
                "INSERT INTO drift_nudges (topic_id, nudge_message_id) VALUES (?, ?)",
                (tid, mid),
            )
            raised = False
        except sqlite3.IntegrityError:
            raised = True
    assert raised
```

- [ ] **Step 3.2: Run test (should fail)**

```bash
.venv/bin/pytest tests/test_drift_nudges_schema.py -v
```

Expected: 3 fails.

- [ ] **Step 3.3: Add `drift_nudges` DDL to `init_db()`**

In `app/db.py`, after the `task_items` DDL added in Task 2, insert:

```python
            CREATE TABLE IF NOT EXISTS drift_nudges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                nudge_message_id INTEGER NOT NULL UNIQUE,
                triggered_by_agent_instance_id INTEGER,
                drift_window_start_message_id INTEGER,
                drift_window_end_message_id INTEGER,
                drift_summary TEXT,
                resolved_at TEXT,
                resolved_by TEXT
                    CHECK (resolved_by IS NULL OR
                           resolved_by IN ('moved_to_topic', 'returned', 'dismissed')),
                resolved_to_topic_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (topic_id) REFERENCES topics(id),
                FOREIGN KEY (nudge_message_id) REFERENCES messages(id),
                FOREIGN KEY (triggered_by_agent_instance_id) REFERENCES agent_instances(id),
                FOREIGN KEY (resolved_to_topic_id) REFERENCES topics(id)
            );
            CREATE INDEX IF NOT EXISTS idx_drift_nudges_topic
                ON drift_nudges(topic_id, created_at DESC);
```

- [ ] **Step 3.4: Create `app/task_trees.py` with the domain helpers**

Create `app/task_trees.py`:
```python
"""Task tree + task item domain helpers."""
from __future__ import annotations

import json
from typing import Any

from .db import connect


def get_tree_by_topic(topic_id: int) -> dict | None:
    """Return the active task_tree row for ``topic_id`` or None."""
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM task_trees WHERE topic_id = ?", (topic_id,)
        ).fetchone()
    return dict(row) if row else None


def list_items(tree_id: int) -> list[dict]:
    """Return all task_items for ``tree_id`` ordered by parent then position."""
    with connect() as conn:
        rows = conn.execute(
            """SELECT * FROM task_items
               WHERE task_tree_id = ?
               ORDER BY COALESCE(parent_item_id, 0), position, id""",
            (tree_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def upsert_tree(
    topic_id: int,
    goal_artifact_id: int | None,
    goal_spec_text: str | None,
    proposal_message_id: int | None,
    approved_by_human_id: int | None,
) -> dict:
    """Insert a new task_trees row for ``topic_id`` or bump version + update goal."""
    with connect() as conn:
        existing = conn.execute(
            "SELECT id, version FROM task_trees WHERE topic_id = ?", (topic_id,)
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE task_trees SET
                       version = version + 1,
                       goal_artifact_id = COALESCE(?, goal_artifact_id),
                       goal_spec_text = COALESCE(?, goal_spec_text),
                       proposal_message_id = COALESCE(?, proposal_message_id),
                       approved_by_human_id = COALESCE(?, approved_by_human_id),
                       approved_at = CURRENT_TIMESTAMP,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE id = ?""",
                (
                    goal_artifact_id, goal_spec_text,
                    proposal_message_id, approved_by_human_id,
                    existing["id"],
                ),
            )
            tree_id = existing["id"]
        else:
            cur = conn.execute(
                """INSERT INTO task_trees
                       (topic_id, goal_artifact_id, goal_spec_text,
                        proposal_message_id, approved_by_human_id)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    topic_id, goal_artifact_id, goal_spec_text,
                    proposal_message_id, approved_by_human_id,
                ),
            )
            tree_id = int(cur.lastrowid)
        row = conn.execute(
            "SELECT * FROM task_trees WHERE id = ?", (tree_id,)
        ).fetchone()
    return dict(row)


def replace_items(tree_id: int, items: list[dict]) -> list[dict]:
    """Replace all task_items under ``tree_id`` with the given list.

    Each item dict has: title (required), parent_index (optional, 0-based into
    the items list to set parent), owner_human_id (optional),
    owner_agent_instance_id (optional). position is assigned by enumeration.
    """
    with connect() as conn:
        conn.execute("DELETE FROM task_items WHERE task_tree_id = ?", (tree_id,))
        # Two-pass insert: first all items without parent set, then UPDATE parent FKs.
        new_ids: list[int] = []
        for pos, item in enumerate(items):
            cur = conn.execute(
                """INSERT INTO task_items
                       (task_tree_id, title, owner_human_id, owner_agent_instance_id,
                        position)
                   VALUES (?, ?, ?, ?, ?)""",
                (
                    tree_id, item["title"],
                    item.get("owner_human_id"),
                    item.get("owner_agent_instance_id"),
                    pos,
                ),
            )
            new_ids.append(int(cur.lastrowid))
        for pos, item in enumerate(items):
            parent_idx = item.get("parent_index")
            if parent_idx is not None and 0 <= parent_idx < len(new_ids):
                conn.execute(
                    "UPDATE task_items SET parent_item_id = ? WHERE id = ?",
                    (new_ids[parent_idx], new_ids[pos]),
                )
    return list_items(tree_id)


def add_item(
    tree_id: int,
    title: str,
    parent_item_id: int | None = None,
    owner_human_id: int | None = None,
    owner_agent_instance_id: int | None = None,
) -> dict:
    """Append a new task_item under ``tree_id`` (optionally under a parent)."""
    with connect() as conn:
        row = conn.execute(
            """SELECT COALESCE(MAX(position), -1) + 1 AS next_pos
               FROM task_items
               WHERE task_tree_id = ?
                 AND (parent_item_id IS ? OR parent_item_id = ?)""",
            (tree_id, parent_item_id, parent_item_id),
        ).fetchone()
        next_pos = row["next_pos"]
        cur = conn.execute(
            """INSERT INTO task_items
                   (task_tree_id, parent_item_id, title,
                    owner_human_id, owner_agent_instance_id, position)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (tree_id, parent_item_id, title,
             owner_human_id, owner_agent_instance_id, next_pos),
        )
        new_row = conn.execute(
            "SELECT * FROM task_items WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return dict(new_row)


def update_item(item_id: int, *, status: str | None = None, title: str | None = None) -> dict:
    """Update status and/or title of a task_item."""
    if status is None and title is None:
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM task_items WHERE id = ?", (item_id,)
            ).fetchone()
        if row is None:
            raise KeyError(f"task_item {item_id} not found")
        return dict(row)

    fields: list[str] = []
    params: list[Any] = []
    if status is not None:
        if status not in ("pending", "active", "done"):
            raise ValueError(f"invalid status: {status}")
        fields.append("status = ?")
        params.append(status)
    if title is not None:
        fields.append("title = ?")
        params.append(title)
    fields.append("updated_at = CURRENT_TIMESTAMP")
    params.append(item_id)
    with connect() as conn:
        conn.execute(
            f"UPDATE task_items SET {', '.join(fields)} WHERE id = ?",
            params,
        )
        row = conn.execute(
            "SELECT * FROM task_items WHERE id = ?", (item_id,)
        ).fetchone()
    if row is None:
        raise KeyError(f"task_item {item_id} not found")
    return dict(row)


def active_item(topic_id: int) -> dict | None:
    """Return the single task_item with status='active' for this topic, or None."""
    with connect() as conn:
        row = conn.execute(
            """SELECT ti.*
               FROM task_items ti
               JOIN task_trees tt ON tt.id = ti.task_tree_id
               WHERE tt.topic_id = ? AND ti.status = 'active'
               ORDER BY ti.position ASC, ti.id ASC
               LIMIT 1""",
            (topic_id,),
        ).fetchone()
    return dict(row) if row else None
```

- [ ] **Step 3.5: Create `app/drift.py`**

Create `app/drift.py`:
```python
"""Drift context computation + nudge persistence."""
from __future__ import annotations

import json

from .db import connect
from .messages import post_message
from .task_trees import active_item


def compute_drift_context(topic_id: int) -> dict:
    """Return the drift_context dict embedded in topic_stream responses.

    Shape (see spec §5.3):
      topic_mode: "exploratory" | "actionable"
      active_task: {id, title} | null
      last_nudge_at: ISO timestamp | null
      last_nudge_message_id: int | null
      last_nudge_resolved_by: "moved_to_topic"|"returned"|"dismissed"|null
      messages_since_last_nudge: int
    """
    with connect() as conn:
        topic_row = conn.execute(
            "SELECT mode FROM topics WHERE id = ?", (topic_id,)
        ).fetchone()
        if topic_row is None:
            raise KeyError(f"topic {topic_id} not found")
        mode = topic_row["mode"]

        last_nudge = conn.execute(
            """SELECT id, nudge_message_id, resolved_by, created_at
               FROM drift_nudges
               WHERE topic_id = ?
               ORDER BY created_at DESC, id DESC
               LIMIT 1""",
            (topic_id,),
        ).fetchone()

        last_nudge_msg_id = last_nudge["nudge_message_id"] if last_nudge else None
        if last_nudge_msg_id is None:
            count_row = conn.execute(
                "SELECT COUNT(*) AS n FROM messages WHERE topic_id = ?",
                (topic_id,),
            ).fetchone()
        else:
            count_row = conn.execute(
                """SELECT COUNT(*) AS n FROM messages
                   WHERE topic_id = ? AND id > ?""",
                (topic_id, last_nudge_msg_id),
            ).fetchone()
        msgs_since = int(count_row["n"])

    active = active_item(topic_id)
    return {
        "topic_mode": mode,
        "active_task": (
            {"id": active["id"], "title": active["title"]} if active else None
        ),
        "last_nudge_at": last_nudge["created_at"] if last_nudge else None,
        "last_nudge_message_id": last_nudge_msg_id,
        "last_nudge_resolved_by": (
            last_nudge["resolved_by"] if last_nudge else None
        ),
        "messages_since_last_nudge": msgs_since,
    }


def post_nudge(
    topic_id: int,
    triggered_by_agent_instance_id: int | None,
    reason: str,
    drift_summary: str,
    window_start_message_id: int | None = None,
    window_end_message_id: int | None = None,
) -> dict:
    """Post a nudge typed message + record a drift_nudges row in one transaction.

    Returns: {"nudge_message_id": ..., "drift_nudge_id": ...}.
    """
    metadata = {"reason": reason, "drift_summary": drift_summary}
    nudge_msg_id = post_message(
        topic_id=topic_id,
        type="nudge",
        actor_type="agent" if triggered_by_agent_instance_id else "system",
        actor_id=triggered_by_agent_instance_id,
        body=reason,
        metadata=metadata,
    )
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO drift_nudges
                   (topic_id, nudge_message_id, triggered_by_agent_instance_id,
                    drift_window_start_message_id, drift_window_end_message_id,
                    drift_summary)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                topic_id, nudge_msg_id, triggered_by_agent_instance_id,
                window_start_message_id, window_end_message_id, drift_summary,
            ),
        )
        nudge_id = int(cur.lastrowid)
    return {"nudge_message_id": nudge_msg_id, "drift_nudge_id": nudge_id}


def resolve_nudge(
    drift_nudge_id: int,
    resolution: str,
    resolved_to_topic_id: int | None = None,
) -> dict:
    """Mark a drift_nudge resolved. Caller is responsible for FK validity."""
    if resolution not in ("moved_to_topic", "returned", "dismissed"):
        raise ValueError(f"invalid resolution: {resolution}")
    with connect() as conn:
        conn.execute(
            """UPDATE drift_nudges
               SET resolved_at = CURRENT_TIMESTAMP,
                   resolved_by = ?,
                   resolved_to_topic_id = ?
               WHERE id = ?""",
            (resolution, resolved_to_topic_id, drift_nudge_id),
        )
        row = conn.execute(
            "SELECT * FROM drift_nudges WHERE id = ?", (drift_nudge_id,)
        ).fetchone()
    if row is None:
        raise KeyError(f"drift_nudge {drift_nudge_id} not found")
    return dict(row)
```

- [ ] **Step 3.6: Run test (should pass)**

```bash
.venv/bin/pytest tests/test_drift_nudges_schema.py -v
```

Expected: 3 pass.

- [ ] **Step 3.7: Run full suite**

```bash
.venv/bin/pytest -q
```

Expected: 193 pass.

- [ ] **Step 3.8: Commit**

```bash
git add app/db.py app/task_trees.py app/drift.py tests/test_drift_nudges_schema.py
git commit -m "$(cat <<'EOF'
feat(goal-guardian): drift_nudges schema + task_trees + drift helpers

drift_nudges row 1:1 with a nudge typed message (UNIQUE nudge_message_id).
Tracks resolution state for the three Q4 actions.

app/task_trees.py: get_tree_by_topic, list_items, upsert_tree,
replace_items, add_item, update_item, active_item.

app/drift.py: compute_drift_context (spec §5.3 shape), post_nudge
(message + drift_nudges row in one txn), resolve_nudge.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: `GET /api/topics/{id}/task-tree`

**Files:**
- Modify: `app/main.py` (add endpoint near other topic routes)
- Create: `tests/test_task_trees_api.py`

- [ ] **Step 4.1: Write failing test**

Create `tests/test_task_trees_api.py`:
```python
def test_get_task_tree_empty(client):
    """When no task_tree exists for a topic, return tree=None, items=[]."""
    from app.db import connect
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('gtt-empty', 'x')")
        tid = cur.lastrowid
    res = client.get(f"/api/topics/{tid}/task-tree", headers={"X-Lets-Human": "Reader"})
    assert res.status_code == 401  # no Bearer / no session


def test_get_task_tree_empty_with_session(client):
    """When no tree exists, session-authed read returns {tree: None, items: []}."""
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    hid = ensure_human("Reader")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('gtt-sess', 'x')")
        tid = cur.lastrowid
    res = client.get(
        f"/api/topics/{tid}/task-tree",
        cookies={"lets_session": sess},
    )
    assert res.status_code == 200
    body = res.json()
    assert body == {"tree": None, "items": []}


def test_get_task_tree_with_items(client):
    """After seeding a tree + items, the response shape is correct."""
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    from app.task_trees import upsert_tree, replace_items

    hid = ensure_human("OwnerHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('gtt-items', 'x')")
        tid = cur.lastrowid
    tree = upsert_tree(
        topic_id=tid,
        goal_artifact_id=None,
        goal_spec_text="Spec goes here",
        proposal_message_id=None,
        approved_by_human_id=hid,
    )
    replace_items(tree["id"], [
        {"title": "Outline"},
        {"title": "Section 1", "parent_index": 0},
        {"title": "Section 2", "parent_index": 0},
    ])
    res = client.get(
        f"/api/topics/{tid}/task-tree",
        cookies={"lets_session": sess},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["tree"]["goal_spec_text"] == "Spec goes here"
    assert len(body["items"]) == 3
    # First item has no parent; later two are children of first
    assert body["items"][0]["parent_item_id"] is None
    children = [i for i in body["items"] if i["parent_item_id"] == body["items"][0]["id"]]
    assert len(children) == 2
```

- [ ] **Step 4.2: Run test (should fail)**

```bash
.venv/bin/pytest tests/test_task_trees_api.py::test_get_task_tree_empty -v
```

Expected: fails with 404.

- [ ] **Step 4.3: Add endpoint to `app/main.py`**

Add this endpoint after the existing `get_topic_messages` endpoint (search for `@app.get("/api/topics/{topic_id}/messages")` and add the new route after that block):

```python
@app.get("/api/topics/{topic_id}/task-tree")
def get_topic_task_tree(
    topic_id: int,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .task_trees import get_tree_by_topic, list_items
    tree = get_tree_by_topic(topic_id)
    if tree is None:
        return {"tree": None, "items": []}
    return {"tree": tree, "items": list_items(tree["id"])}
```

- [ ] **Step 4.4: Run tests (should pass)**

```bash
.venv/bin/pytest tests/test_task_trees_api.py -v
```

Expected: 3 pass.

- [ ] **Step 4.5: Full suite**

```bash
.venv/bin/pytest -q
```

Expected: 196 pass.

- [ ] **Step 4.6: Commit**

```bash
git add app/main.py tests/test_task_trees_api.py
git commit -m "$(cat <<'EOF'
feat(goal-guardian): GET /api/topics/{id}/task-tree

Returns {tree, items} with items ordered by parent then position.
Empty topic returns {tree: null, items: []}. Reads use the dual
session-cookie OR Bearer auth pattern via get_api_principal.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: `POST /api/topics/{id}/task-tree` + `POST /api/topics/{id}/goal`

**Files:**
- Modify: `app/main.py` (add two endpoints + Pydantic models)
- Modify: `tests/test_task_trees_api.py` (append tests)

- [ ] **Step 5.1: Append failing tests**

Append to `tests/test_task_trees_api.py`:
```python
def test_adopt_task_tree_from_proposal(client):
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    from app.messages import post_message

    hid = ensure_human("AdoptHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('adopt-tt', 'x')")
        tid = cur.lastrowid
    proposal_id = post_message(
        topic_id=tid, type="task_tree_proposal",
        actor_type="agent", actor_id=None,
        body="拆成 3 个",
        metadata={
            "title": "PPT Tree",
            "items": [
                {"title": "Outline"},
                {"title": "P1", "parent_index": 0},
                {"title": "P2", "parent_index": 0},
            ],
        },
    )
    res = client.post(
        f"/api/topics/{tid}/task-tree",
        cookies={"lets_session": sess},
        json={"proposal_message_id": proposal_id},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["tree"]["version"] == 1
    assert len(body["items"]) == 3


def test_adopt_task_tree_increments_version(client):
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    from app.messages import post_message

    hid = ensure_human("VHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('adopt-v2', 'x')")
        tid = cur.lastrowid
    p1 = post_message(
        topic_id=tid, type="task_tree_proposal",
        actor_type="agent", actor_id=None,
        body="v1",
        metadata={"title": "T1", "items": [{"title": "A"}]},
    )
    client.post(
        f"/api/topics/{tid}/task-tree",
        cookies={"lets_session": sess},
        json={"proposal_message_id": p1},
    )
    p2 = post_message(
        topic_id=tid, type="task_tree_proposal",
        actor_type="agent", actor_id=None,
        body="v2",
        metadata={"title": "T2", "items": [{"title": "B"}, {"title": "C"}]},
    )
    res2 = client.post(
        f"/api/topics/{tid}/task-tree",
        cookies={"lets_session": sess},
        json={"proposal_message_id": p2},
    )
    assert res2.status_code == 201
    body = res2.json()
    assert body["tree"]["version"] == 2
    assert [i["title"] for i in body["items"]] == ["B", "C"]


def test_adopt_goal_from_proposal(client):
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    from app.messages import post_message

    hid = ensure_human("GoalHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('adopt-goal', 'x')")
        tid = cur.lastrowid
    proposal_id = post_message(
        topic_id=tid, type="goal_proposal",
        actor_type="agent", actor_id=None,
        body="30 分钟 talk",
        metadata={"artifact_id": None, "spec_text": "30 分钟 talk · 技术受众"},
    )
    res = client.post(
        f"/api/topics/{tid}/goal",
        cookies={"lets_session": sess},
        json={"goal_proposal_message_id": proposal_id},
    )
    assert res.status_code == 201
    body = res.json()
    assert body["tree"]["goal_spec_text"] == "30 分钟 talk · 技术受众"
    assert body["items"] == []  # goal adoption alone does not create items
```

- [ ] **Step 5.2: Run test (should fail)**

```bash
.venv/bin/pytest tests/test_task_trees_api.py -v
```

Expected: 3 new fail (405 / 404 / etc.).

- [ ] **Step 5.3: Add endpoints + Pydantic models to `app/main.py`**

Find the section where other Pydantic models are defined (e.g., near `class MessageCreate(BaseModel)`). Add:

```python
class TaskTreeAdoptInput(BaseModel):
    proposal_message_id: int


class GoalAdoptInput(BaseModel):
    goal_proposal_message_id: int | None = None
    artifact_id: int | None = None
    spec_text: str | None = None
```

Then add the two endpoints after the existing `get_topic_task_tree`:

```python
@app.post("/api/topics/{topic_id}/task-tree", status_code=201)
def adopt_task_tree(
    topic_id: int,
    payload: TaskTreeAdoptInput,
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> dict:
    from .auth import verify_session
    from .messages import topic_stream
    from .task_trees import get_tree_by_topic, list_items, replace_items, upsert_tree

    if not lets_session:
        raise HTTPException(status_code=401, detail="session required")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")

    # Find the proposal message in this topic
    msgs = topic_stream(topic_id, limit=10000)
    proposal = next(
        (m for m in msgs if m["id"] == payload.proposal_message_id),
        None,
    )
    if proposal is None or proposal["type"] != "task_tree_proposal":
        raise HTTPException(status_code=400, detail="proposal not found in topic")

    meta = proposal["metadata"] or {}
    items = meta.get("items") or []
    tree = upsert_tree(
        topic_id=topic_id,
        goal_artifact_id=None,
        goal_spec_text=None,
        proposal_message_id=payload.proposal_message_id,
        approved_by_human_id=principal["human_id"],
    )
    replace_items(tree["id"], items)
    return {"tree": tree, "items": list_items(tree["id"])}


@app.post("/api/topics/{topic_id}/goal", status_code=201)
def adopt_goal(
    topic_id: int,
    payload: GoalAdoptInput,
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> dict:
    from .auth import verify_session
    from .messages import topic_stream
    from .task_trees import get_tree_by_topic, list_items, upsert_tree

    if not lets_session:
        raise HTTPException(status_code=401, detail="session required")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")

    artifact_id: int | None = payload.artifact_id
    spec_text: str | None = payload.spec_text

    if payload.goal_proposal_message_id is not None:
        msgs = topic_stream(topic_id, limit=10000)
        proposal = next(
            (m for m in msgs if m["id"] == payload.goal_proposal_message_id),
            None,
        )
        if proposal is None or proposal["type"] != "goal_proposal":
            raise HTTPException(status_code=400, detail="proposal not found in topic")
        meta = proposal["metadata"] or {}
        artifact_id = artifact_id or meta.get("artifact_id")
        spec_text = spec_text or meta.get("spec_text") or proposal["body"]

    if not spec_text and artifact_id is None:
        raise HTTPException(status_code=400, detail="goal must have spec_text or artifact_id")

    tree = upsert_tree(
        topic_id=topic_id,
        goal_artifact_id=artifact_id,
        goal_spec_text=spec_text,
        proposal_message_id=payload.goal_proposal_message_id,
        approved_by_human_id=principal["human_id"],
    )
    return {"tree": tree, "items": list_items(tree["id"])}
```

- [ ] **Step 5.4: Run tests (should pass)**

```bash
.venv/bin/pytest tests/test_task_trees_api.py -v
```

Expected: 6 pass total.

- [ ] **Step 5.5: Commit**

```bash
git add app/main.py tests/test_task_trees_api.py
git commit -m "$(cat <<'EOF'
feat(goal-guardian): POST /api/topics/{id}/task-tree + /goal endpoints

Both gated by session cookie (human-only action). task-tree adoption
reads the referenced task_tree_proposal message metadata, replaces all
existing items, and bumps task_trees.version. Goal adoption stores
artifact_id + spec_text on the same task_trees row (no items mutation).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: `POST /api/task-items` + `PATCH /api/task-items/{id}`

**Files:**
- Modify: `app/main.py`
- Modify: `tests/test_task_trees_api.py`

- [ ] **Step 6.1: Append failing tests**

Append to `tests/test_task_trees_api.py`:
```python
def test_add_task_item(client):
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    from app.task_trees import upsert_tree

    hid = ensure_human("AddHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('add-item', 'x')")
        tid = cur.lastrowid
    tree = upsert_tree(
        topic_id=tid, goal_artifact_id=None, goal_spec_text=None,
        proposal_message_id=None, approved_by_human_id=hid,
    )
    res = client.post(
        "/api/task-items",
        cookies={"lets_session": sess},
        json={"task_tree_id": tree["id"], "title": "new item"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["title"] == "new item"
    assert body["status"] == "pending"
    assert body["position"] == 0


def test_patch_task_item_status(client):
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    from app.task_trees import upsert_tree, add_item

    hid = ensure_human("PatchHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('patch-item', 'x')")
        tid = cur.lastrowid
    tree = upsert_tree(
        topic_id=tid, goal_artifact_id=None, goal_spec_text=None,
        proposal_message_id=None, approved_by_human_id=hid,
    )
    item = add_item(tree["id"], "todo")
    res = client.patch(
        f"/api/task-items/{item['id']}",
        cookies={"lets_session": sess},
        json={"status": "done"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "done"


def test_patch_task_item_invalid_status(client):
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    from app.task_trees import upsert_tree, add_item

    hid = ensure_human("BadPatchHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('badpatch', 'x')")
        tid = cur.lastrowid
    tree = upsert_tree(
        topic_id=tid, goal_artifact_id=None, goal_spec_text=None,
        proposal_message_id=None, approved_by_human_id=hid,
    )
    item = add_item(tree["id"], "todo")
    res = client.patch(
        f"/api/task-items/{item['id']}",
        cookies={"lets_session": sess},
        json={"status": "in-progress"},
    )
    assert res.status_code == 400
```

- [ ] **Step 6.2: Run test (should fail)**

```bash
.venv/bin/pytest tests/test_task_trees_api.py::test_add_task_item -v
```

Expected: 404.

- [ ] **Step 6.3: Add endpoints to `app/main.py`**

After the adopt endpoints, add:

```python
class TaskItemCreate(BaseModel):
    task_tree_id: int
    title: str
    parent_item_id: int | None = None
    owner_human_id: int | None = None
    owner_agent_instance_id: int | None = None


class TaskItemPatch(BaseModel):
    status: str | None = None
    title: str | None = None


@app.post("/api/task-items", status_code=201)
def post_task_item(
    payload: TaskItemCreate,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .task_trees import add_item
    return add_item(
        tree_id=payload.task_tree_id,
        title=payload.title,
        parent_item_id=payload.parent_item_id,
        owner_human_id=payload.owner_human_id,
        owner_agent_instance_id=payload.owner_agent_instance_id,
    )


@app.patch("/api/task-items/{item_id}")
def patch_task_item(
    item_id: int,
    payload: TaskItemPatch,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .task_trees import update_item
    try:
        return update_item(item_id, status=payload.status, title=payload.title)
    except KeyError:
        raise HTTPException(status_code=404, detail="task_item not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
```

- [ ] **Step 6.4: Run tests (should pass)**

```bash
.venv/bin/pytest tests/test_task_trees_api.py -v
```

Expected: 9 pass total.

- [ ] **Step 6.5: Commit**

```bash
git add app/main.py tests/test_task_trees_api.py
git commit -m "$(cat <<'EOF'
feat(goal-guardian): POST /api/task-items + PATCH /api/task-items/{id}

Both accept session OR Bearer auth (agents add via MCP too).
PATCH only mutates status/title; owner/parent/position are immutable
in v1.5c-2 per design §5.1.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: `POST /api/nudges/{id}/resolve`

**Files:**
- Modify: `app/main.py`
- Create: `tests/test_drift_nudges_api.py`

- [ ] **Step 7.1: Write failing test**

Create `tests/test_drift_nudges_api.py`:
```python
def test_resolve_nudge_dismissed(client):
    from app.auth import issue_session
    from app.db import connect
    from app.drift import post_nudge
    from app.identity import ensure_human

    hid = ensure_human("DismissHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('resnud-d', 'x')")
        tid = cur.lastrowid
    nudge = post_nudge(
        topic_id=tid,
        triggered_by_agent_instance_id=None,
        reason="off-topic",
        drift_summary="discussing friday team dinner",
    )
    res = client.post(
        f"/api/nudges/{nudge['drift_nudge_id']}/resolve",
        cookies={"lets_session": sess},
        json={"resolved_by": "dismissed"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["resolved_by"] == "dismissed"
    assert body["resolved_at"] is not None


def test_resolve_nudge_returned(client):
    from app.auth import issue_session
    from app.db import connect
    from app.drift import post_nudge
    from app.identity import ensure_human

    hid = ensure_human("ReturnHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('resnud-r', 'x')")
        tid = cur.lastrowid
    nudge = post_nudge(
        topic_id=tid, triggered_by_agent_instance_id=None,
        reason="off", drift_summary="x",
    )
    res = client.post(
        f"/api/nudges/{nudge['drift_nudge_id']}/resolve",
        cookies={"lets_session": sess},
        json={"resolved_by": "returned"},
    )
    assert res.status_code == 200
    assert res.json()["resolved_by"] == "returned"


def test_resolve_nudge_moved_to_topic_creates_new_topic(client):
    from app.auth import issue_session
    from app.db import connect
    from app.drift import post_nudge
    from app.identity import ensure_human

    hid = ensure_human("SpinoffHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO projects (slug, name) VALUES ('p-spinoff', 'P')"
        )
        pid = cur.lastrowid
        cur = conn.execute(
            "INSERT INTO topics (slug, title, project_id) VALUES ('resnud-m', 'x', ?)",
            (pid,),
        )
        tid = cur.lastrowid
    nudge = post_nudge(
        topic_id=tid, triggered_by_agent_instance_id=None,
        reason="off-topic", drift_summary="planning friday dinner at 7pm",
    )
    res = client.post(
        f"/api/nudges/{nudge['drift_nudge_id']}/resolve",
        cookies={"lets_session": sess},
        json={"resolved_by": "moved_to_topic", "spinoff_title": "周五团建"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["resolved_by"] == "moved_to_topic"
    assert body["resolved_to_topic_id"] is not None

    # Verify the new topic has a system message with the drift_summary
    new_tid = body["resolved_to_topic_id"]
    with connect() as conn:
        topic_row = conn.execute(
            "SELECT slug, title, project_id FROM topics WHERE id = ?", (new_tid,)
        ).fetchone()
        msg_row = conn.execute(
            """SELECT body FROM messages
               WHERE topic_id = ? AND type = 'system' LIMIT 1""",
            (new_tid,),
        ).fetchone()
    assert topic_row["title"] == "周五团建"
    assert topic_row["project_id"] == pid
    assert "planning friday dinner" in msg_row["body"]


def test_resolve_nudge_missing_spinoff_title(client):
    from app.auth import issue_session
    from app.db import connect
    from app.drift import post_nudge
    from app.identity import ensure_human

    hid = ensure_human("MissingHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('resnud-miss', 'x')")
        tid = cur.lastrowid
    nudge = post_nudge(
        topic_id=tid, triggered_by_agent_instance_id=None,
        reason="off", drift_summary="x",
    )
    res = client.post(
        f"/api/nudges/{nudge['drift_nudge_id']}/resolve",
        cookies={"lets_session": sess},
        json={"resolved_by": "moved_to_topic"},  # no spinoff_title
    )
    assert res.status_code == 400
```

- [ ] **Step 7.2: Run test (should fail)**

```bash
.venv/bin/pytest tests/test_drift_nudges_api.py -v
```

Expected: 4 fails (404).

- [ ] **Step 7.3: Add endpoint to `app/main.py`**

```python
class NudgeResolveInput(BaseModel):
    resolved_by: str
    spinoff_title: str | None = None


@app.post("/api/nudges/{drift_nudge_id}/resolve")
def resolve_drift_nudge(
    drift_nudge_id: int,
    payload: NudgeResolveInput,
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> dict:
    from .auth import verify_session
    from .db import connect
    from .drift import resolve_nudge
    from .messages import post_message

    if not lets_session:
        raise HTTPException(status_code=401, detail="session required")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")

    # Read the existing nudge for context
    with connect() as conn:
        nudge_row = conn.execute(
            "SELECT * FROM drift_nudges WHERE id = ?", (drift_nudge_id,)
        ).fetchone()
    if nudge_row is None:
        raise HTTPException(status_code=404, detail="nudge not found")

    resolved_to_topic_id: int | None = None

    if payload.resolved_by == "moved_to_topic":
        if not payload.spinoff_title:
            raise HTTPException(status_code=400, detail="spinoff_title required")
        # Create the new topic in the same project
        with connect() as conn:
            src_topic = conn.execute(
                "SELECT project_id FROM topics WHERE id = ?", (nudge_row["topic_id"],)
            ).fetchone()
            project_id = src_topic["project_id"] if src_topic else None
            # Generate a slug from the title (lower, replace ws with -)
            import re, time
            slug_base = re.sub(r"\s+", "-", payload.spinoff_title.strip().lower())[:60]
            slug = f"{slug_base}-{int(time.time())}"
            cur = conn.execute(
                "INSERT INTO topics (slug, title, project_id) VALUES (?, ?, ?)",
                (slug, payload.spinoff_title, project_id),
            )
            new_topic_id = int(cur.lastrowid)
        # Post a system message summarizing the spinoff
        summary_body = (
            f"从 topic#{nudge_row['topic_id']} 迁移而来。"
            f"摘要：{nudge_row['drift_summary'] or '（无摘要）'}"
        )
        post_message(
            topic_id=new_topic_id, type="system",
            actor_type="system", actor_id=None,
            body=summary_body, metadata={"source_topic_id": nudge_row["topic_id"]},
        )
        resolved_to_topic_id = new_topic_id

    elif payload.resolved_by not in ("returned", "dismissed"):
        raise HTTPException(status_code=400, detail="invalid resolved_by")

    try:
        return resolve_nudge(
            drift_nudge_id, payload.resolved_by,
            resolved_to_topic_id=resolved_to_topic_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
```

- [ ] **Step 7.4: Run tests (should pass)**

```bash
.venv/bin/pytest tests/test_drift_nudges_api.py -v
```

Expected: 4 pass.

- [ ] **Step 7.5: Commit**

```bash
git add app/main.py tests/test_drift_nudges_api.py
git commit -m "$(cat <<'EOF'
feat(goal-guardian): POST /api/nudges/{id}/resolve

Three resolutions (moved_to_topic, returned, dismissed). moved_to_topic
creates a fresh topic in the same project + posts a system message
summarizing the drift. Per design §5.1 + Q4-A: original messages are
NOT migrated; the new topic is a fresh start.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Run full suite — Phase B done

- [ ] **Step 8.1: Run full backend tests**

```bash
.venv/bin/pytest -q
```

Expected: ~205 pass (193 + 4 task-tree-api + 4 drift-api + earlier additions). Investigate any new failures — most likely from existing tests that call `get_topic_messages` expecting `list[dict]` but the response shape will change in Task 9. Should still be a list at this point — Task 9 is the breaking change.

- [ ] **Step 8.2: No commit** — checkpoint only.

---

## Task 9: Extend `topic_stream` response to include `drift_context`

This is the **single breaking change** for the whole feature. After this task, all consumers of `GET /api/topics/{id}/messages` must read `data.messages` instead of `data`.

**Files:**
- Modify: `app/main.py` (response shape)
- Modify: `app/messages.py` — no change; the endpoint composes the new shape
- Create: `tests/test_drift_context.py`
- Modify: existing pytest files that check `client.get(...)` response shape for messages

- [ ] **Step 9.1: Write failing test**

Create `tests/test_drift_context.py`:
```python
def test_drift_context_default_exploratory(client):
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human

    hid = ensure_human("CtxHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('dctx-1', 'x')")
        tid = cur.lastrowid
    res = client.get(
        f"/api/topics/{tid}/messages",
        cookies={"lets_session": sess},
    )
    body = res.json()
    assert isinstance(body, dict)
    assert "messages" in body
    assert "drift_context" in body
    ctx = body["drift_context"]
    assert ctx["topic_mode"] == "exploratory"
    assert ctx["active_task"] is None
    assert ctx["last_nudge_at"] is None
    assert ctx["last_nudge_message_id"] is None
    assert ctx["last_nudge_resolved_by"] is None
    assert ctx["messages_since_last_nudge"] == 0


def test_drift_context_after_nudge(client):
    from app.auth import issue_session
    from app.db import connect
    from app.drift import post_nudge
    from app.identity import ensure_human
    from app.messages import post_message

    hid = ensure_human("CtxNudgeHuman")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('dctx-n', 'x')")
        tid = cur.lastrowid
    # 1 chat, nudge, 2 chats
    post_message(topic_id=tid, type="chat", actor_type="human",
                 actor_id=hid, body="m1", metadata={})
    post_nudge(topic_id=tid, triggered_by_agent_instance_id=None,
               reason="drift", drift_summary="s")
    post_message(topic_id=tid, type="chat", actor_type="human",
                 actor_id=hid, body="m2", metadata={})
    post_message(topic_id=tid, type="chat", actor_type="human",
                 actor_id=hid, body="m3", metadata={})

    res = client.get(
        f"/api/topics/{tid}/messages",
        cookies={"lets_session": sess},
    )
    ctx = res.json()["drift_context"]
    assert ctx["last_nudge_message_id"] is not None
    assert ctx["messages_since_last_nudge"] == 2


def test_drift_context_active_task(client):
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human
    from app.task_trees import upsert_tree, add_item, update_item

    hid = ensure_human("CtxActive")
    sess = issue_session(hid)
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('dctx-act', 'x')")
        tid = cur.lastrowid
    tree = upsert_tree(
        topic_id=tid, goal_artifact_id=None, goal_spec_text=None,
        proposal_message_id=None, approved_by_human_id=hid,
    )
    item = add_item(tree["id"], "Section 1")
    update_item(item["id"], status="active")
    res = client.get(
        f"/api/topics/{tid}/messages",
        cookies={"lets_session": sess},
    )
    ctx = res.json()["drift_context"]
    assert ctx["active_task"] is not None
    assert ctx["active_task"]["title"] == "Section 1"
```

- [ ] **Step 9.2: Run test (should fail)**

```bash
.venv/bin/pytest tests/test_drift_context.py -v
```

Expected: AssertionError (current endpoint returns list, not dict).

- [ ] **Step 9.3: Modify `get_topic_messages` in `app/main.py`**

Find the existing endpoint:
```python
@app.get("/api/topics/{topic_id}/messages")
def get_topic_messages(
    topic_id: int,
    type: list[str] | None = Query(default=None),
    limit: int = 500,
    after_id: int | None = None,
    principal: dict = Depends(get_api_principal),
) -> list[dict]:
    from .messages import topic_stream
    return topic_stream(topic_id, type_filter=type, limit=limit, after_id=after_id)
```

Replace with:
```python
@app.get("/api/topics/{topic_id}/messages")
def get_topic_messages(
    topic_id: int,
    type: list[str] | None = Query(default=None),
    limit: int = 500,
    after_id: int | None = None,
    principal: dict = Depends(get_api_principal),
) -> dict:
    from .drift import compute_drift_context
    from .messages import topic_stream
    return {
        "messages": topic_stream(
            topic_id, type_filter=type, limit=limit, after_id=after_id,
        ),
        "drift_context": compute_drift_context(topic_id),
    }
```

- [ ] **Step 9.4: Run drift_context tests (should pass)**

```bash
.venv/bin/pytest tests/test_drift_context.py -v
```

Expected: 3 pass.

- [ ] **Step 9.5: Run full backend suite, adapt regressions**

```bash
.venv/bin/pytest -q
```

Expect failures in any test that did `res.json() == [...]` on `/api/topics/{id}/messages` or `len(res.json())`. Search for those:

```bash
grep -rn '/messages"' tests/ | grep -v "test_drift_context\|test_topics_messages" | head -20
```

For each failing test, change `body = res.json()` to `body = res.json()["messages"]` (and add `ctx = res.json()["drift_context"]` if you also want to assert on context, which most tests don't).

Most likely files needing update:
- `tests/test_messages.py` — find every `.json()` call against `/api/topics/{id}/messages` and patch
- `tests/test_e2e_ppt_scenario.py` — same
- `tests/test_e2e_project_lifecycle.py` — same
- `tests/test_topics_api.py` (if any reads messages) — same

After patching, rerun:

```bash
.venv/bin/pytest -q
```

Expected: all green.

- [ ] **Step 9.6: Update frontend `useTopicMessages` to consume new shape**

Edit `frontend/src/api/queries.ts`. Find:
```ts
export function useTopicMessages(topicId: number) {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["topics", topicId, "messages"],
    queryFn: () => apiRequest<MessageDTO[]>(`/api/topics/${topicId}/messages`, { identity }),
  });
}
```

Replace with:
```ts
export interface TopicMessagesResponse {
  messages: MessageDTO[];
  drift_context: DriftContextDTO;
}

export interface DriftContextDTO {
  topic_mode: "exploratory" | "actionable";
  active_task: { id: number; title: string } | null;
  last_nudge_at: string | null;
  last_nudge_message_id: number | null;
  last_nudge_resolved_by: "moved_to_topic" | "returned" | "dismissed" | null;
  messages_since_last_nudge: number;
}

export function useTopicMessages(topicId: number) {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["topics", topicId, "messages"],
    queryFn: () => apiRequest<TopicMessagesResponse>(`/api/topics/${topicId}/messages`, { identity }),
  });
}
```

(The DriftContextDTO type can also be moved to `taskTreeTypes.ts` in Task 14. For now keep it inline.)

- [ ] **Step 9.7: Update frontend callers of `useTopicMessages`**

Two consumers:

`frontend/src/topic/TopicView.tsx`: find `const initial = useTopicMessages(topicId);` then `const base = initial.data ?? [];` — change to `const base = initial.data?.messages ?? [];`. Search for any other reference to `initial.data` that treated it as array; convert.

`frontend/src/attention/AttentionView.tsx`: find `const { data, isLoading } = useTopicMessages(1);` then `const messages = data ?? [];` — change to `const messages = data?.messages ?? [];`.

- [ ] **Step 9.8: Update MSW fixture handler**

Edit `frontend/src/fixtures/handlers.ts`. Find the handler for `/api/topics/:id/messages`:
```ts
http.get("/api/topics/:id/messages", ({ params, request }) => {
  const url = new URL(request.url);
  const types = url.searchParams.getAll("type");
  const topicId = Number(params.id);
  let messages = seed.messages.filter((m) => m.topic_id === topicId);
  if (types.length) messages = messages.filter((m) => types.includes(m.type));
  return HttpResponse.json(messages);
}),
```

Replace with:
```ts
http.get("/api/topics/:id/messages", ({ params, request }) => {
  const url = new URL(request.url);
  const types = url.searchParams.getAll("type");
  const topicId = Number(params.id);
  let messages = seed.messages.filter((m) => m.topic_id === topicId);
  if (types.length) messages = messages.filter((m) => types.includes(m.type));
  return HttpResponse.json({
    messages,
    drift_context: {
      topic_mode: "exploratory",
      active_task: null,
      last_nudge_at: null,
      last_nudge_message_id: null,
      last_nudge_resolved_by: null,
      messages_since_last_nudge: messages.length,
    },
  });
}),
```

- [ ] **Step 9.9: Run frontend tests**

```bash
cd frontend && /Users/jacky/.nvm/versions/node/v22.17.0/bin/pnpm test --run
```

Expected: 52 pass (existing). The change is API-compatible at the call sites because we patched them in 9.7.

- [ ] **Step 9.10: Commit**

```bash
git add app/main.py tests/test_drift_context.py tests/test_messages.py \
        tests/test_e2e_ppt_scenario.py tests/test_e2e_project_lifecycle.py \
        tests/test_topics_api.py \
        frontend/src/api/queries.ts \
        frontend/src/topic/TopicView.tsx \
        frontend/src/attention/AttentionView.tsx \
        frontend/src/fixtures/handlers.ts
git commit -m "$(cat <<'EOF'
feat(goal-guardian): extend GET /api/topics/{id}/messages with drift_context

Single breaking change: response was MessageDTO[], now is
{messages: MessageDTO[], drift_context: DriftContextDTO}. All backend
and frontend callers updated in this commit.

Agents read drift_context to decide whether to post_nudge (spec §7.1).
The frontend doesn't yet use drift_context — that wires in Task 17.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

Some of the `git add` files may not exist if there are no message-fetching tests in them. Skip files that have no changes — `git add` will silently skip non-modified paths in your worktree.

---

## Task 10: MCP tool `propose_goal`

**Files:**
- Modify: `app/mcp_server.py`
- Create: `tests/test_goal_guardian_mcp.py`

- [ ] **Step 10.1: Write failing test**

Create `tests/test_goal_guardian_mcp.py`:
```python
def test_propose_goal_via_mcp(client):
    """Through MCP, propose_goal should insert a goal_proposal message."""
    from app.db import connect
    from app.mcp_server import propose_goal
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('mcp-pg', 'x')")
        tid = cur.lastrowid
    result = propose_goal(
        topic_id=tid,
        spec_text="30 分钟 talk · 技术受众",
        artifact_id=None,
    )
    assert result["topic_id"] == tid
    assert result["type"] == "goal_proposal"
    assert "30 分钟" in result["body"]
    assert result["metadata"]["spec_text"] == "30 分钟 talk · 技术受众"
```

- [ ] **Step 10.2: Run test (should fail)**

```bash
.venv/bin/pytest tests/test_goal_guardian_mcp.py::test_propose_goal_via_mcp -v
```

Expected: ImportError on `propose_goal`.

- [ ] **Step 10.3: Add MCP tool**

In `app/mcp_server.py`, after the last existing `@mcp.tool()` block, add:

```python
@mcp.tool()
def propose_goal(
    topic_id: int,
    spec_text: str,
    artifact_id: int | None = None,
) -> dict:
    """Propose the final goal for a topic (artifact + spec). Posts a
    goal_proposal typed message; humans must adopt to make it active."""
    import json
    from .db import connect
    from .messages import post_message

    metadata = {
        "artifact_id": artifact_id,
        "spec_text": spec_text,
        "proposed_at": "now",
    }
    msg_id = post_message(
        topic_id=topic_id,
        type="goal_proposal",
        actor_type="agent",
        actor_id=None,
        body=spec_text,
        metadata=metadata,
    )
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM messages WHERE id = ?", (msg_id,)
        ).fetchone()
    msg = dict(row)
    if isinstance(msg.get("metadata"), str):
        msg["metadata"] = json.loads(msg["metadata"])
    return msg
```

- [ ] **Step 10.4: Run test (should pass)**

```bash
.venv/bin/pytest tests/test_goal_guardian_mcp.py::test_propose_goal_via_mcp -v
```

Expected: pass.

- [ ] **Step 10.5: Commit**

```bash
git add app/mcp_server.py tests/test_goal_guardian_mcp.py
git commit -m "$(cat <<'EOF'
feat(goal-guardian): MCP tool propose_goal

Agents call this to post a goal_proposal typed message.
Humans must adopt via POST /api/topics/{id}/goal to make it active.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 11: MCP tool `propose_task_tree`

**Files:**
- Modify: `app/mcp_server.py`
- Modify: `tests/test_goal_guardian_mcp.py`

- [ ] **Step 11.1: Append failing test**

Append to `tests/test_goal_guardian_mcp.py`:
```python
def test_propose_task_tree_via_mcp(client):
    from app.db import connect
    from app.mcp_server import propose_task_tree
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('mcp-ptt', 'x')")
        tid = cur.lastrowid
    result = propose_task_tree(
        topic_id=tid,
        title="PPT Tree",
        items=[
            {"title": "Outline"},
            {"title": "P1", "parent_index": 0},
            {"title": "P2", "parent_index": 0},
        ],
    )
    assert result["type"] == "task_tree_proposal"
    assert result["metadata"]["title"] == "PPT Tree"
    assert len(result["metadata"]["items"]) == 3
```

- [ ] **Step 11.2: Run test (should fail)**

```bash
.venv/bin/pytest tests/test_goal_guardian_mcp.py::test_propose_task_tree_via_mcp -v
```

- [ ] **Step 11.3: Add MCP tool**

In `app/mcp_server.py`, after `propose_goal`, add:

```python
@mcp.tool()
def propose_task_tree(
    topic_id: int,
    title: str,
    items: list[dict],
) -> dict:
    """Propose a hierarchical task breakdown for a topic.

    items is a list of {title, parent_index?, owner_human_id?,
    owner_agent_instance_id?}. parent_index is 0-based into the items
    list itself, used to express parent-child relations at adoption time.

    Posts a task_tree_proposal typed message; humans must adopt via
    POST /api/topics/{id}/task-tree to make it active."""
    import json
    from .db import connect
    from .messages import post_message

    body = f"提议把这个 topic 拆成 {len(items)} 个任务"
    metadata = {"title": title, "items": items}
    msg_id = post_message(
        topic_id=topic_id,
        type="task_tree_proposal",
        actor_type="agent",
        actor_id=None,
        body=body,
        metadata=metadata,
    )
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM messages WHERE id = ?", (msg_id,)
        ).fetchone()
    msg = dict(row)
    if isinstance(msg.get("metadata"), str):
        msg["metadata"] = json.loads(msg["metadata"])
    return msg
```

- [ ] **Step 11.4: Run test (should pass)**

```bash
.venv/bin/pytest tests/test_goal_guardian_mcp.py::test_propose_task_tree_via_mcp -v
```

- [ ] **Step 11.5: Commit**

```bash
git add app/mcp_server.py tests/test_goal_guardian_mcp.py
git commit -m "$(cat <<'EOF'
feat(goal-guardian): MCP tool propose_task_tree

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 12: MCP tool `update_task_status`

**Files:**
- Modify: `app/mcp_server.py`
- Modify: `tests/test_goal_guardian_mcp.py`

- [ ] **Step 12.1: Append failing test**

```python
def test_update_task_status_via_mcp(client):
    from app.db import connect
    from app.identity import ensure_human
    from app.mcp_server import update_task_status
    from app.task_trees import upsert_tree, add_item
    hid = ensure_human("MCPStatHuman")
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('mcp-uts', 'x')")
        tid = cur.lastrowid
    tree = upsert_tree(
        topic_id=tid, goal_artifact_id=None, goal_spec_text=None,
        proposal_message_id=None, approved_by_human_id=hid,
    )
    item = add_item(tree["id"], "section")
    result = update_task_status(item_id=item["id"], status="active")
    assert result["status"] == "active"
    # Also check a status typed message was posted for visibility
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE topic_id = ? AND type = 'status'", (tid,)
        ).fetchall()
    assert len(rows) >= 1
```

- [ ] **Step 12.2: Run test (should fail)**

- [ ] **Step 12.3: Add MCP tool**

```python
@mcp.tool()
def update_task_status(item_id: int, status: str) -> dict:
    """Update a task_item's status (pending|active|done). Posts a status
    typed message into the parent topic so the stream reflects the change."""
    import json
    from .db import connect
    from .messages import post_message
    from .task_trees import update_item

    if status not in ("pending", "active", "done"):
        raise ValueError(f"invalid status: {status}")
    updated = update_item(item_id, status=status)

    # Find the topic for the item's tree
    with connect() as conn:
        topic_row = conn.execute(
            """SELECT tt.topic_id
               FROM task_items ti
               JOIN task_trees tt ON tt.id = ti.task_tree_id
               WHERE ti.id = ?""",
            (item_id,),
        ).fetchone()
    if topic_row is None:
        return updated

    body = f"task {item_id} ({updated['title']}) → {status}"
    post_message(
        topic_id=int(topic_row["topic_id"]),
        type="status",
        actor_type="agent",
        actor_id=None,
        body=body,
        metadata={"task_item_id": item_id, "new_status": status},
    )
    return updated
```

- [ ] **Step 12.4: Run test (should pass)**

```bash
.venv/bin/pytest tests/test_goal_guardian_mcp.py::test_update_task_status_via_mcp -v
```

- [ ] **Step 12.5: Commit**

```bash
git add app/mcp_server.py tests/test_goal_guardian_mcp.py
git commit -m "$(cat <<'EOF'
feat(goal-guardian): MCP tool update_task_status

Side effect: posts a 'status' typed message into the parent topic
so the conversation log shows agent claims and completions.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 13: MCP tool `post_nudge`

**Files:**
- Modify: `app/mcp_server.py`
- Modify: `tests/test_goal_guardian_mcp.py`

- [ ] **Step 13.1: Append failing test**

```python
def test_post_nudge_via_mcp(client):
    from app.db import connect
    from app.mcp_server import post_nudge as mcp_post_nudge
    with connect() as conn:
        cur = conn.execute("INSERT INTO topics (slug, title) VALUES ('mcp-pn', 'x')")
        tid = cur.lastrowid
    result = mcp_post_nudge(
        topic_id=tid,
        reason="off-topic for 5 minutes",
        drift_summary="discussion about friday team dinner",
    )
    assert "nudge_message_id" in result
    assert "drift_nudge_id" in result
    # Both rows exist
    with connect() as conn:
        msg = conn.execute(
            "SELECT type, body FROM messages WHERE id = ?",
            (result["nudge_message_id"],),
        ).fetchone()
        dnudge = conn.execute(
            "SELECT topic_id, drift_summary FROM drift_nudges WHERE id = ?",
            (result["drift_nudge_id"],),
        ).fetchone()
    assert msg["type"] == "nudge"
    assert dnudge["topic_id"] == tid
    assert "friday" in dnudge["drift_summary"]
```

- [ ] **Step 13.2: Run test (should fail)**

- [ ] **Step 13.3: Add MCP tool**

In `app/mcp_server.py`:

```python
@mcp.tool()
def post_nudge(
    topic_id: int,
    reason: str,
    drift_summary: str,
    triggered_by_agent_instance_id: int | None = None,
    window_start_message_id: int | None = None,
    window_end_message_id: int | None = None,
) -> dict:
    """Post a nudge typed message + record a drift_nudges row in one txn.

    Agents should only call this after consulting the drift_context
    in the topic_stream response and confirming the previous nudge
    wasn't 'dismissed'. See .claude/skills/lets-goal-guardian/SKILL.md."""
    from .drift import post_nudge as _post_nudge
    return _post_nudge(
        topic_id=topic_id,
        triggered_by_agent_instance_id=triggered_by_agent_instance_id,
        reason=reason,
        drift_summary=drift_summary,
        window_start_message_id=window_start_message_id,
        window_end_message_id=window_end_message_id,
    )
```

- [ ] **Step 13.4: Run test (should pass)**

- [ ] **Step 13.5: Run full backend suite**

```bash
.venv/bin/pytest -q
```

Expected: ~215 pass.

- [ ] **Step 13.6: Commit**

```bash
git add app/mcp_server.py tests/test_goal_guardian_mcp.py
git commit -m "$(cat <<'EOF'
feat(goal-guardian): MCP tool post_nudge

Wraps drift.post_nudge for agent self-report drift detection.
Agent-side discipline (when to call, when not to) lives in the
lets-goal-guardian skill, not in code.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 14: Frontend types + queries hook

**Files:**
- Create: `frontend/src/api/taskTreeTypes.ts`
- Create: `frontend/src/api/taskTreeQueries.ts`
- Modify: `frontend/src/api/queries.ts` (move `DriftContextDTO` to taskTreeTypes)

- [ ] **Step 14.1: Create `frontend/src/api/taskTreeTypes.ts`**

```ts
export interface TaskTreeDTO {
  id: number;
  topic_id: number;
  goal_artifact_id: number | null;
  goal_spec_text: string | null;
  version: number;
  approved_at: string;
  approved_by_human_id: number | null;
  proposal_message_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface TaskItemDTO {
  id: number;
  task_tree_id: number;
  parent_item_id: number | null;
  title: string;
  owner_human_id: number | null;
  owner_agent_instance_id: number | null;
  status: "pending" | "active" | "done";
  position: number;
  created_at: string;
  updated_at: string;
}

export interface TaskTreeResponse {
  tree: TaskTreeDTO | null;
  items: TaskItemDTO[];
}

export interface DriftContextDTO {
  topic_mode: "exploratory" | "actionable";
  active_task: { id: number; title: string } | null;
  last_nudge_at: string | null;
  last_nudge_message_id: number | null;
  last_nudge_resolved_by: "moved_to_topic" | "returned" | "dismissed" | null;
  messages_since_last_nudge: number;
}

export interface AddTaskItemInput {
  task_tree_id: number;
  title: string;
  parent_item_id?: number | null;
  owner_human_id?: number | null;
  owner_agent_instance_id?: number | null;
}

export interface PatchTaskItemInput {
  status?: "pending" | "active" | "done";
  title?: string;
}

export interface AdoptTaskTreeInput {
  proposal_message_id: number;
}

export interface AdoptGoalInput {
  goal_proposal_message_id?: number;
  artifact_id?: number | null;
  spec_text?: string | null;
}

export type NudgeResolution = "moved_to_topic" | "returned" | "dismissed";

export interface ResolveNudgeInput {
  resolved_by: NudgeResolution;
  spinoff_title?: string;
}

export interface ResolveNudgeResponse {
  id: number;
  topic_id: number;
  resolved_by: NudgeResolution;
  resolved_to_topic_id: number | null;
  resolved_at: string;
}
```

- [ ] **Step 14.2: Move `DriftContextDTO` from `queries.ts` to `taskTreeTypes.ts`**

In `frontend/src/api/queries.ts`, remove the inline `interface DriftContextDTO` and `interface TopicMessagesResponse`, then import them:

```ts
import type { DriftContextDTO } from "./taskTreeTypes";
import type { MessageDTO } from "./types";

export interface TopicMessagesResponse {
  messages: MessageDTO[];
  drift_context: DriftContextDTO;
}
```

- [ ] **Step 14.3: Create `frontend/src/api/taskTreeQueries.ts`**

```ts
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "./client";
import { useIdentity } from "../identity/useIdentity";
import type {
  AddTaskItemInput,
  AdoptGoalInput,
  AdoptTaskTreeInput,
  PatchTaskItemInput,
  ResolveNudgeInput,
  ResolveNudgeResponse,
  TaskItemDTO,
  TaskTreeResponse,
} from "./taskTreeTypes";

export function useTopicTaskTree(topicId: number) {
  const identity = useIdentity();
  return useQuery({
    queryKey: ["topics", topicId, "task-tree"],
    queryFn: () =>
      apiRequest<TaskTreeResponse>(`/api/topics/${topicId}/task-tree`, { identity }),
  });
}

export function useAdoptTaskTreeProposal(topicId: number) {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: AdoptTaskTreeInput) =>
      apiRequest<TaskTreeResponse>(`/api/topics/${topicId}/task-tree`, {
        method: "POST",
        body: input,
        identity,
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["topics", topicId, "task-tree"] }),
  });
}

export function useAdoptGoalProposal(topicId: number) {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: AdoptGoalInput) =>
      apiRequest<TaskTreeResponse>(`/api/topics/${topicId}/goal`, {
        method: "POST",
        body: input,
        identity,
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["topics", topicId, "task-tree"] }),
  });
}

export function useAddTaskItem(topicId: number) {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: AddTaskItemInput) =>
      apiRequest<TaskItemDTO>(`/api/task-items`, {
        method: "POST",
        body: input,
        identity,
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["topics", topicId, "task-tree"] }),
  });
}

export function useUpdateTaskItem(topicId: number) {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...input }: PatchTaskItemInput & { id: number }) =>
      apiRequest<TaskItemDTO>(`/api/task-items/${id}`, {
        method: "PATCH",
        body: input,
        identity,
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["topics", topicId, "task-tree"] }),
  });
}

export function useResolveNudge(topicId: number) {
  const identity = useIdentity();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...input }: ResolveNudgeInput & { id: number }) =>
      apiRequest<ResolveNudgeResponse>(`/api/nudges/${id}/resolve`, {
        method: "POST",
        body: input,
        identity,
      }),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["topics", topicId, "messages"] }),
  });
}
```

- [ ] **Step 14.4: Verify type-check**

```bash
cd frontend && /Users/jacky/.nvm/versions/node/v22.17.0/bin/pnpm exec tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 14.5: Commit**

```bash
git add frontend/src/api/taskTreeTypes.ts frontend/src/api/taskTreeQueries.ts frontend/src/api/queries.ts
git commit -m "$(cat <<'EOF'
feat(frontend): task-tree + drift-context types + query hooks

useTopicTaskTree, useAdoptTaskTreeProposal, useAdoptGoalProposal,
useAddTaskItem, useUpdateTaskItem, useResolveNudge.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 15: MSW fixtures for task-tree + nudge endpoints

**Files:**
- Modify: `frontend/src/fixtures/seed.ts`
- Modify: `frontend/src/fixtures/handlers.ts`

- [ ] **Step 15.1: Extend seed**

Edit `frontend/src/fixtures/seed.ts`. Add to `SeedState`:
```ts
import type { TaskItemDTO, TaskTreeDTO } from "../api/taskTreeTypes";

export interface SeedState {
  topics: TopicDTO[];
  messages: MessageDTO[];
  humans: { id: number; name: string }[];
  agentInstances: { id: number; role: string; device_label: string; human_id: number }[];
  taskTrees: TaskTreeDTO[];
  taskItems: TaskItemDTO[];
  driftNudges: Array<{
    id: number;
    topic_id: number;
    nudge_message_id: number;
    drift_summary: string;
    resolved_by: "moved_to_topic" | "returned" | "dismissed" | null;
    resolved_at: string | null;
    resolved_to_topic_id: number | null;
  }>;
}
```

In `makeSeed()`, after constructing `messages`, add:
```ts
const taskTrees: TaskTreeDTO[] = [{
  id: 1, topic_id: 1,
  goal_artifact_id: null,
  goal_spec_text: "30 分钟 talk · 技术受众 · 突出「事件性记忆 vs 语义记忆」",
  version: 1,
  approved_at: "2026-05-19T09:33:00Z",
  approved_by_human_id: 1,
  proposal_message_id: 6,
  created_at: "2026-05-19T09:33:00Z",
  updated_at: "2026-05-19T09:33:00Z",
}];
const taskItems: TaskItemDTO[] = [
  { id: 1, task_tree_id: 1, parent_item_id: null,
    title: "Framing 角度定下来", owner_human_id: 3, owner_agent_instance_id: null,
    status: "done", position: 0,
    created_at: "2026-05-19T09:33:00Z", updated_at: "2026-05-19T09:33:00Z" },
  { id: 2, task_tree_id: 1, parent_item_id: null,
    title: "P4 业界对比矩阵 4×6", owner_human_id: null, owner_agent_instance_id: 11,
    status: "done", position: 1,
    created_at: "2026-05-19T09:33:00Z", updated_at: "2026-05-19T09:33:00Z" },
  { id: 3, task_tree_id: 1, parent_item_id: null,
    title: "Skill 字号修正", owner_human_id: null, owner_agent_instance_id: 13,
    status: "done", position: 2,
    created_at: "2026-05-19T09:33:00Z", updated_at: "2026-05-19T09:33:00Z" },
  { id: 4, task_tree_id: 1, parent_item_id: null,
    title: "P2 framing 改写", owner_human_id: null, owner_agent_instance_id: 11,
    status: "active", position: 3,
    created_at: "2026-05-19T09:33:00Z", updated_at: "2026-05-19T09:33:00Z" },
  { id: 5, task_tree_id: 1, parent_item_id: null,
    title: "P5 加文字解释", owner_human_id: null, owner_agent_instance_id: null,
    status: "pending", position: 4,
    created_at: "2026-05-19T09:33:00Z", updated_at: "2026-05-19T09:33:00Z" },
  { id: 6, task_tree_id: 1, parent_item_id: 5,
    title: "P5 子任务: 找去年反馈数据", owner_human_id: null, owner_agent_instance_id: null,
    status: "pending", position: 0,
    created_at: "2026-05-19T09:33:00Z", updated_at: "2026-05-19T09:33:00Z" },
  { id: 7, task_tree_id: 1, parent_item_id: null,
    title: "Demo / Q&A 准备", owner_human_id: 1, owner_agent_instance_id: null,
    status: "pending", position: 5,
    created_at: "2026-05-19T09:33:00Z", updated_at: "2026-05-19T09:33:00Z" },
  { id: 8, task_tree_id: 1, parent_item_id: null,
    title: "排练 30min", owner_human_id: null, owner_agent_instance_id: null,
    status: "pending", position: 6,
    created_at: "2026-05-19T09:33:00Z", updated_at: "2026-05-19T09:33:00Z" },
];
const driftNudges: SeedState["driftNudges"] = [{
  id: 1, topic_id: 1, nudge_message_id: 12,
  drift_summary: "讨论 framing 25 分钟",
  resolved_by: null, resolved_at: null, resolved_to_topic_id: null,
}];

return { topics, messages, humans, agentInstances, taskTrees, taskItems, driftNudges };
```

- [ ] **Step 15.2: Update topic-stream MSW handler to reflect actionable mode + active task + drift state**

Replace the previous Task 9.8 implementation of the messages handler with a more accurate one that uses the seeded `driftNudges` and `taskItems`. In `frontend/src/fixtures/handlers.ts`:

```ts
http.get("/api/topics/:id/messages", ({ params, request }) => {
  const url = new URL(request.url);
  const types = url.searchParams.getAll("type");
  const topicId = Number(params.id);
  let messages = seed.messages.filter((m) => m.topic_id === topicId);
  if (types.length) messages = messages.filter((m) => types.includes(m.type));
  const topic = seed.topics.find((t) => t.id === topicId);
  const activeItem = seed.taskItems.find(
    (i) =>
      i.status === "active" &&
      seed.taskTrees.find((t) => t.id === i.task_tree_id)?.topic_id === topicId,
  );
  const lastNudge = seed.driftNudges
    .filter((n) => n.topic_id === topicId)
    .sort((a, b) => b.id - a.id)[0];
  const lastNudgeMsg = lastNudge
    ? seed.messages.find((m) => m.id === lastNudge.nudge_message_id)
    : null;
  const messagesAfterNudge = lastNudge
    ? messages.filter((m) => m.id > lastNudge.nudge_message_id).length
    : messages.length;
  return HttpResponse.json({
    messages,
    drift_context: {
      // Topic mode is not part of TopicDTO yet on the frontend; mock as
      // "actionable" for topic 1 to exercise the drift UI in dev.
      topic_mode: topicId === 1 ? "actionable" : "exploratory",
      active_task: activeItem
        ? { id: activeItem.id, title: activeItem.title }
        : null,
      last_nudge_at: lastNudgeMsg?.created_at ?? null,
      last_nudge_message_id: lastNudge?.nudge_message_id ?? null,
      last_nudge_resolved_by: lastNudge?.resolved_by ?? null,
      messages_since_last_nudge: messagesAfterNudge,
    },
  });
}),
```

- [ ] **Step 15.3: Add MSW handlers for task-tree + nudge endpoints**

In `frontend/src/fixtures/handlers.ts`, append to the `handlers` array:

```ts
http.get("/api/topics/:id/task-tree", ({ params }) => {
  const topicId = Number(params.id);
  const tree = seed.taskTrees.find((t) => t.topic_id === topicId) ?? null;
  const items = tree ? seed.taskItems.filter((i) => i.task_tree_id === tree.id) : [];
  return HttpResponse.json({ tree, items });
}),

http.post("/api/topics/:id/task-tree", async ({ params, request }) => {
  const topicId = Number(params.id);
  const body = (await request.json()) as { proposal_message_id: number };
  const proposal = seed.messages.find((m) => m.id === body.proposal_message_id);
  if (!proposal || proposal.type !== "task_tree_proposal") {
    return new HttpResponse(JSON.stringify({ detail: "proposal not found" }), {
      status: 400,
    });
  }
  let tree = seed.taskTrees.find((t) => t.topic_id === topicId);
  if (!tree) {
    tree = {
      id: seed.taskTrees.length + 1,
      topic_id: topicId, goal_artifact_id: null, goal_spec_text: null,
      version: 1,
      approved_at: new Date().toISOString(),
      approved_by_human_id: 1,
      proposal_message_id: body.proposal_message_id,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    seed.taskTrees.push(tree);
  } else {
    tree.version += 1;
    tree.proposal_message_id = body.proposal_message_id;
    tree.updated_at = new Date().toISOString();
  }
  seed.taskItems = seed.taskItems.filter((i) => i.task_tree_id !== tree!.id);
  const meta = (proposal.metadata ?? {}) as { items?: Array<{title:string;parent_index?:number}> };
  const propItems = meta.items ?? [];
  const newIds: number[] = [];
  for (let i = 0; i < propItems.length; i++) {
    const id = seed.taskItems.length + i + 100;
    newIds.push(id);
    seed.taskItems.push({
      id, task_tree_id: tree.id, parent_item_id: null,
      title: propItems[i]!.title,
      owner_human_id: null, owner_agent_instance_id: null,
      status: "pending", position: i,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
  }
  for (let i = 0; i < propItems.length; i++) {
    const idx = propItems[i]!.parent_index;
    if (idx !== undefined && idx >= 0 && idx < newIds.length) {
      const item = seed.taskItems.find((it) => it.id === newIds[i]);
      if (item) item.parent_item_id = newIds[idx] ?? null;
    }
  }
  const items = seed.taskItems.filter((it) => it.task_tree_id === tree.id);
  return HttpResponse.json({ tree, items }, { status: 201 });
}),

http.post("/api/topics/:id/goal", async ({ params, request }) => {
  const topicId = Number(params.id);
  const body = (await request.json()) as {
    goal_proposal_message_id?: number;
    spec_text?: string;
    artifact_id?: number | null;
  };
  let specText = body.spec_text ?? null;
  let artifactId = body.artifact_id ?? null;
  if (body.goal_proposal_message_id) {
    const prop = seed.messages.find((m) => m.id === body.goal_proposal_message_id);
    if (prop) {
      const meta = (prop.metadata ?? {}) as { spec_text?: string; artifact_id?: number };
      specText = specText ?? meta.spec_text ?? prop.body;
      artifactId = artifactId ?? meta.artifact_id ?? null;
    }
  }
  let tree = seed.taskTrees.find((t) => t.topic_id === topicId);
  if (!tree) {
    tree = {
      id: seed.taskTrees.length + 1, topic_id: topicId,
      goal_artifact_id: artifactId, goal_spec_text: specText,
      version: 1, approved_at: new Date().toISOString(),
      approved_by_human_id: 1, proposal_message_id: body.goal_proposal_message_id ?? null,
      created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    };
    seed.taskTrees.push(tree);
  } else {
    tree.goal_artifact_id = artifactId;
    tree.goal_spec_text = specText;
    tree.updated_at = new Date().toISOString();
  }
  const items = seed.taskItems.filter((it) => it.task_tree_id === tree!.id);
  return HttpResponse.json({ tree, items }, { status: 201 });
}),

http.post("/api/task-items", async ({ request }) => {
  const body = (await request.json()) as {
    task_tree_id: number; title: string; parent_item_id?: number | null;
    owner_human_id?: number | null; owner_agent_instance_id?: number | null;
  };
  const siblings = seed.taskItems.filter(
    (i) => i.task_tree_id === body.task_tree_id && i.parent_item_id === (body.parent_item_id ?? null),
  );
  const item = {
    id: seed.taskItems.length + 1000,
    task_tree_id: body.task_tree_id,
    parent_item_id: body.parent_item_id ?? null,
    title: body.title,
    owner_human_id: body.owner_human_id ?? null,
    owner_agent_instance_id: body.owner_agent_instance_id ?? null,
    status: "pending" as const,
    position: siblings.length,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  seed.taskItems.push(item);
  return HttpResponse.json(item, { status: 201 });
}),

http.patch("/api/task-items/:id", async ({ params, request }) => {
  const id = Number(params.id);
  const body = (await request.json()) as { status?: "pending"|"active"|"done"; title?: string };
  const item = seed.taskItems.find((i) => i.id === id);
  if (!item) return new HttpResponse(null, { status: 404 });
  if (body.status) item.status = body.status;
  if (body.title) item.title = body.title;
  item.updated_at = new Date().toISOString();
  return HttpResponse.json(item);
}),

http.post("/api/nudges/:id/resolve", async ({ params, request }) => {
  const id = Number(params.id);
  const body = (await request.json()) as { resolved_by: "moved_to_topic"|"returned"|"dismissed"; spinoff_title?: string };
  const nudge = seed.driftNudges.find((n) => n.id === id);
  if (!nudge) return new HttpResponse(null, { status: 404 });
  nudge.resolved_by = body.resolved_by;
  nudge.resolved_at = new Date().toISOString();
  if (body.resolved_by === "moved_to_topic") {
    if (!body.spinoff_title) {
      return new HttpResponse(JSON.stringify({ detail: "spinoff_title required" }), { status: 400 });
    }
    const newTopicId = seed.topics.length + 1;
    seed.topics.push({
      id: newTopicId,
      slug: `spinoff-${newTopicId}`,
      title: body.spinoff_title,
      project_id: seed.topics.find((t) => t.id === nudge.topic_id)?.project_id ?? null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
    nudge.resolved_to_topic_id = newTopicId;
  }
  return HttpResponse.json({
    id: nudge.id, topic_id: nudge.topic_id,
    resolved_by: nudge.resolved_by, resolved_to_topic_id: nudge.resolved_to_topic_id,
    resolved_at: nudge.resolved_at,
  });
}),
```

- [ ] **Step 15.3 (verify): Run frontend tests**

```bash
cd frontend && /Users/jacky/.nvm/versions/node/v22.17.0/bin/pnpm test --run
```

Expected: 52 pass (existing). Some tests may fail if the seed shape change broke their assumptions — patch any seed-shape comparisons.

- [ ] **Step 15.4: Commit**

```bash
git add frontend/src/fixtures/seed.ts frontend/src/fixtures/handlers.ts
git commit -m "$(cat <<'EOF'
feat(frontend): MSW fixtures for task-tree + nudge endpoints

Seed includes a task_tree (8 items, one nested under P5) and one
unresolved drift nudge for topic 1. Handlers mutate the shared seed
across requests within a single test/dev session.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 16: TaskTreePanel rewrite — real data + tree rendering + edit

**Files:**
- Modify: `frontend/src/context/TaskTreePanel.tsx`
- Modify: `frontend/src/context/TaskTreePanel.test.tsx`
- Modify: `frontend/src/context/TopicContext.tsx` (remove old hardcoded props)

- [ ] **Step 16.1: Update test**

Replace `frontend/src/context/TaskTreePanel.test.tsx` with:
```tsx
import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { TaskTreePanel } from "./TaskTreePanel";

describe("<TaskTreePanel />", () => {
  it("renders nested tree from useTopicTaskTree (fixture topic 1)", async () => {
    renderWithProviders(<TaskTreePanel topicId={1} />);
    await waitFor(() => {
      expect(screen.getByText(/Framing 角度定下来/)).toBeInTheDocument();
    });
    // The nested item under P5 is hidden by default (children collapsed)
    expect(screen.queryByText(/找去年反馈数据/)).not.toBeInTheDocument();
  });

  it("toggling expand shows nested children", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TaskTreePanel topicId={1} />);
    await waitFor(() => screen.getByText(/P5 加文字解释/));
    const expandBtn = screen.getByRole("button", {
      name: /expand-5/i,  // testid-style aria-label
    });
    await user.click(expandBtn);
    expect(screen.getByText(/找去年反馈数据/)).toBeInTheDocument();
  });

  it("checking a task marks it done", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TaskTreePanel topicId={1} />);
    await waitFor(() => screen.getByText(/P5 加文字解释/));
    const cb = screen.getByRole("checkbox", { name: /P5 加文字解释/ });
    expect(cb).not.toBeChecked();
    await user.click(cb);
    await waitFor(() => expect(cb).toBeChecked());
  });

  it("can add a new task at root", async () => {
    const user = userEvent.setup();
    renderWithProviders(<TaskTreePanel topicId={1} />);
    await waitFor(() => screen.getByText(/Framing 角度定下来/));
    await user.click(screen.getByRole("button", { name: /\+ 加任务/i }));
    const input = screen.getByPlaceholderText(/输入新任务/i);
    await user.type(input, "新任务1{Enter}");
    await waitFor(() => expect(screen.getByText(/新任务1/)).toBeInTheDocument());
  });
});
```

- [ ] **Step 16.2: Replace `TaskTreePanel.tsx`**

```tsx
import { useState } from "react";
import { cn } from "../lib/cn";
import {
  useAddTaskItem,
  useTopicTaskTree,
  useUpdateTaskItem,
} from "../api/taskTreeQueries";
import type { TaskItemDTO } from "../api/taskTreeTypes";

interface Props {
  topicId: number;
}

export function TaskTreePanel({ topicId }: Props) {
  const tree = useTopicTaskTree(topicId);
  const update = useUpdateTaskItem(topicId);
  const add = useAddTaskItem(topicId);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [adding, setAdding] = useState(false);
  const [newTitle, setNewTitle] = useState("");

  if (tree.isLoading || !tree.data) {
    return <div className="text-text-dim text-sm">加载中…</div>;
  }
  if (!tree.data.tree) {
    return (
      <div className="border border-dashed border-border rounded p-3 text-center text-text-dim text-sm">
        尚未设定 task tree
      </div>
    );
  }

  const treeId = tree.data.tree.id;
  const items = tree.data.items;
  const roots = items.filter((i) => i.parent_item_id === null);
  const doneCount = items.filter((i) => i.status === "done").length;

  function toggleExpand(id: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleDone(item: TaskItemDTO) {
    update.mutate({
      id: item.id,
      status: item.status === "done" ? "pending" : "done",
    });
  }

  function submitAdd() {
    if (!newTitle.trim()) return;
    add.mutate({ task_tree_id: treeId, title: newTitle.trim() });
    setNewTitle("");
    setAdding(false);
  }

  function renderItem(item: TaskItemDTO, depth: number) {
    const children = items.filter((i) => i.parent_item_id === item.id);
    const hasChildren = children.length > 0;
    const isExpanded = expanded.has(item.id);
    return (
      <div key={item.id}>
        <div
          className="flex items-center gap-2 text-[12.5px] py-0.5"
          style={{ paddingLeft: depth * 12 }}
        >
          {hasChildren ? (
            <button
              type="button"
              aria-label={`expand-${item.id}`}
              onClick={() => toggleExpand(item.id)}
              className="text-[10px] text-text-dim w-3"
            >
              {isExpanded ? "▾" : "▸"}
            </button>
          ) : (
            <span className="w-3" />
          )}
          <input
            type="checkbox"
            checked={item.status === "done"}
            onChange={() => toggleDone(item)}
            aria-label={item.title}
            className="cursor-pointer"
          />
          <span
            className={cn(
              "flex-1 truncate",
              item.status === "done" && "text-text-dim line-through",
            )}
          >
            {item.title}
          </span>
        </div>
        {hasChildren && isExpanded && (
          <div>{children.map((c) => renderItem(c, depth + 1))}</div>
        )}
      </div>
    );
  }

  return (
    <div className="border border-border-soft rounded-lg bg-surface-elev p-3 flex flex-col gap-2">
      <div className="flex items-baseline justify-between">
        <span className="font-semibold text-[13px]">研讨 PPT 终版</span>
        <span className="font-mono text-[11px] text-text-dim">
          {doneCount} / {items.length} done
        </span>
      </div>
      <div className="flex flex-col">
        {roots.map((r) => renderItem(r, 0))}
      </div>
      {adding ? (
        <input
          autoFocus
          placeholder="输入新任务，回车保存"
          value={newTitle}
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") submitAdd();
            if (e.key === "Escape") setAdding(false);
          }}
          className="text-[12px] px-2 py-1 border border-border rounded bg-bg"
        />
      ) : (
        <button
          type="button"
          onClick={() => setAdding(true)}
          className="text-[11px] text-text-dim hover:text-text text-left"
        >
          + 加任务
        </button>
      )}
    </div>
  );
}
```

- [ ] **Step 16.3: Update `TopicContext.tsx` to pass topicId, drop hardcoded items**

In `frontend/src/context/TopicContext.tsx`, find:
```tsx
<ContextBlock label="目标分解" right="claude · 09:33">
  <TaskTreePanel
    title="研讨 PPT 终版"
    items={[ ... ]}
  />
</ContextBlock>
```

Replace with:
```tsx
<ContextBlock label="目标分解">
  <TaskTreePanel topicId={1} />
</ContextBlock>
```

- [ ] **Step 16.4: Run tests**

```bash
cd frontend && /Users/jacky/.nvm/versions/node/v22.17.0/bin/pnpm test TaskTreePanel --run
```

Expected: 4 pass (new tests).

```bash
cd frontend && /Users/jacky/.nvm/versions/node/v22.17.0/bin/pnpm test --run
```

Expected: ~56 total (was 52, +4 new).

- [ ] **Step 16.5: Commit**

```bash
git add frontend/src/context/TaskTreePanel.tsx \
        frontend/src/context/TaskTreePanel.test.tsx \
        frontend/src/context/TopicContext.tsx
git commit -m "$(cat <<'EOF'
feat(frontend): TaskTreePanel real-tree + checkbox + add-row

Hierarchy via parent_item_id, indentation 12px per level, collapse/expand
via local Set<number>. Two edit actions only (Q2-D): toggle done, add
new root-level task. Owner picker / drag-reorder out of scope.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 17: GoalDetailPanel wired to real data

**Files:**
- Modify: `frontend/src/context/GoalDetailPanel.tsx`
- Modify: `frontend/src/context/GoalDetailPanel.test.tsx`
- Modify: `frontend/src/context/TopicContext.tsx`

- [ ] **Step 17.1: Update test**

Replace `frontend/src/context/GoalDetailPanel.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { renderWithProviders } from "../../test/render";
import { GoalDetailPanel } from "./GoalDetailPanel";

describe("<GoalDetailPanel />", () => {
  it("renders the seeded goal spec for topic 1", async () => {
    renderWithProviders(<GoalDetailPanel topicId={1} />);
    await waitFor(() => {
      expect(screen.getByText(/30 分钟 talk/)).toBeInTheDocument();
    });
  });

  it("renders empty state when no tree exists (topic 2)", async () => {
    renderWithProviders(<GoalDetailPanel topicId={9999} />);
    await waitFor(() => {
      expect(screen.getByText(/尚未设定目标/)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 17.2: Replace `GoalDetailPanel.tsx`**

```tsx
import { useTopicTaskTree } from "../api/taskTreeQueries";

interface Props {
  topicId: number;
}

export function GoalDetailPanel({ topicId }: Props) {
  const tree = useTopicTaskTree(topicId);
  if (tree.isLoading || !tree.data) {
    return <div className="text-text-dim text-sm">…</div>;
  }
  if (!tree.data.tree || !tree.data.tree.goal_spec_text) {
    return (
      <div className="border border-dashed border-border rounded p-3 text-center text-text-dim text-sm">
        尚未设定目标
      </div>
    );
  }
  const t = tree.data.tree;
  return (
    <div className="border border-border-soft rounded-lg bg-surface-elev p-3 flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <span className="text-[11px] uppercase tracking-wider text-text-dim font-semibold">
          目标 Artifact
        </span>
        <span className="font-mono text-[11px] text-text-dim ml-auto">
          v{t.version}
        </span>
      </div>
      {t.goal_artifact_id && (
        <div className="font-mono text-[13px]">artifact#{t.goal_artifact_id}</div>
      )}
      <p className="text-[12px] text-text-muted leading-relaxed">
        {t.goal_spec_text}
      </p>
    </div>
  );
}
```

(Approvers UI + Mark as Final button: removed for v1.5c-2 since we deferred goal editing per spec §2. The buttons can come back in a future task once we wire goal-update flows.)

- [ ] **Step 17.3: Update `TopicContext.tsx`**

Find:
```tsx
<ContextBlock label="目标">
  <GoalDetailPanel ... hardcoded props ... />
</ContextBlock>
```

Replace with:
```tsx
<ContextBlock label="目标">
  <GoalDetailPanel topicId={1} />
</ContextBlock>
```

- [ ] **Step 17.4: Run tests**

```bash
cd frontend && /Users/jacky/.nvm/versions/node/v22.17.0/bin/pnpm test GoalDetailPanel --run
```

Expected: 2 pass.

- [ ] **Step 17.5: Commit**

```bash
git add frontend/src/context/GoalDetailPanel.tsx \
        frontend/src/context/GoalDetailPanel.test.tsx \
        frontend/src/context/TopicContext.tsx
git commit -m "$(cat <<'EOF'
feat(frontend): GoalDetailPanel reads useTopicTaskTree

Empty state when no tree exists, renders goal_spec_text otherwise.
Approver list + Mark as Final removed in v1.5c-2 (goal editing
is out of scope per spec §2; will return in a later task).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 18: TaskTreeProposalMessage adopt button

**Files:**
- Modify: `frontend/src/messages/TaskTreeProposalMessage.tsx`
- Modify: `frontend/src/messages/TaskTreeProposalMessage.test.tsx`

- [ ] **Step 18.1: Update test**

Replace `frontend/src/messages/TaskTreeProposalMessage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { TaskTreeProposalMessage } from "./TaskTreeProposalMessage";

const sampleMessage = {
  id: 6, topic_id: 1, type: "task_tree_proposal" as const,
  actor_type: "agent" as const, actor_id: 11,
  body: "建议分 3 个任务",
  metadata: {
    title: "PPT",
    items: [
      { title: "Framing", status: "done" },
      { title: "矩阵", status: "active" },
      { title: "排练", status: "pending" },
    ],
  },
  ref_event_id: null,
  created_at: "2026-05-19T09:33:00Z",
};

describe("<TaskTreeProposalMessage />", () => {
  it("renders title + items as before", () => {
    renderWithProviders(
      <TaskTreeProposalMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={sampleMessage}
      />,
    );
    expect(screen.getByText("PPT")).toBeInTheDocument();
    expect(screen.getByText("Framing")).toBeInTheDocument();
  });

  it("renders Adopt button and calls the endpoint on click", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <TaskTreeProposalMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={sampleMessage}
      />,
    );
    const btn = screen.getByRole("button", { name: /Adopt as task tree/i });
    await user.click(btn);
    await waitFor(() => {
      expect(screen.getByText(/Adopted/i)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 18.2: Replace `TaskTreeProposalMessage.tsx`**

```tsx
import { useState } from "react";
import type { MessageDTO, TaskTreeProposalMeta } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { cn } from "../lib/cn";
import { useAdoptTaskTreeProposal } from "../api/taskTreeQueries";

interface Actor { kind: "human" | "claude" | "codex" | "system"; initial: string; displayName: string }

export function TaskTreeProposalMessage({
  message,
  actor,
}: {
  message: MessageDTO;
  actor: Actor;
}) {
  const meta = message.metadata as Partial<TaskTreeProposalMeta>;
  const items = meta.items ?? [];
  const doneCount = items.filter((i) => i.status === "done").length;
  const adopt = useAdoptTaskTreeProposal(message.topic_id);
  const [adopted, setAdopted] = useState(false);

  function handleAdopt() {
    adopt.mutate(
      { proposal_message_id: message.id },
      { onSuccess: () => setAdopted(true) },
    );
  }

  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag="task_tree"
      tone="tree"
      body={
        <div className="flex flex-col gap-1.5">
          <div className="flex items-center gap-2 text-[13px]">
            <span className="font-semibold">{meta.title ?? "task tree"}</span>
            <span className="font-mono text-text-dim text-[11px]">
              {doneCount} / {items.length} done
            </span>
          </div>
          <ul className="flex flex-col gap-1">
            {items.map((it, i) => (
              <li key={i} className="flex items-center gap-2 text-[12.5px]">
                <span
                  className={cn(
                    "w-2 h-2 rounded-full",
                    it.status === "done" && "bg-status-on",
                    it.status === "active" && "bg-status-work",
                    (!it.status || it.status === "pending") &&
                      "border border-border bg-surface",
                  )}
                />
                <span
                  className={
                    it.status === "done" ? "text-text-dim line-through" : ""
                  }
                >
                  {it.title}
                </span>
                {it.owner_name && (
                  <span className="ml-auto text-[11px] font-mono text-text-dim">
                    {it.owner_name}
                  </span>
                )}
              </li>
            ))}
          </ul>
          <div className="flex items-center gap-2 mt-2">
            <div className="flex-1" />
            {adopted ? (
              <span className="text-[12px] text-status-on font-medium">
                Adopted ✓
              </span>
            ) : (
              <button
                type="button"
                onClick={handleAdopt}
                disabled={adopt.isPending}
                className="px-2 py-1 rounded bg-tree text-bg text-[12px] font-medium disabled:opacity-40"
              >
                Adopt as task tree
              </button>
            )}
          </div>
        </div>
      }
    />
  );
}
```

- [ ] **Step 18.3: Run tests**

```bash
cd frontend && /Users/jacky/.nvm/versions/node/v22.17.0/bin/pnpm test TaskTreeProposalMessage --run
```

Expected: 2 pass.

- [ ] **Step 18.4: Commit**

```bash
git add frontend/src/messages/TaskTreeProposalMessage.tsx \
        frontend/src/messages/TaskTreeProposalMessage.test.tsx
git commit -m "$(cat <<'EOF'
feat(frontend): TaskTreeProposalMessage Adopt button

Posts POST /api/topics/{id}/task-tree referencing this message id,
flips to "Adopted ✓" footer once the mutation succeeds.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 19: NudgeMessage + SpinoffDialog

**Files:**
- Create: `frontend/src/nudge/SpinoffDialog.tsx`
- Create: `frontend/src/nudge/SpinoffDialog.test.tsx`
- Modify: `frontend/src/messages/NudgeMessage.tsx`
- Modify: `frontend/src/messages/NudgeMessage.test.tsx`

- [ ] **Step 19.1: Create SpinoffDialog**

Create `frontend/src/nudge/SpinoffDialog.tsx`:
```tsx
import { useState } from "react";

interface Props {
  suggestedTitle: string;
  onSubmit: (title: string) => Promise<void>;
  onCancel: () => void;
}

export function SpinoffDialog({ suggestedTitle, onSubmit, onCancel }: Props) {
  const [title, setTitle] = useState(suggestedTitle);
  const [submitting, setSubmitting] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    setSubmitting(true);
    try {
      await onSubmit(title.trim());
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/30 grid place-items-center z-50">
      <form
        onSubmit={submit}
        className="bg-bg border border-border rounded-xl w-full max-w-md p-5 flex flex-col gap-3"
      >
        <h2 className="font-[var(--font-display)] text-lg">独立成新 topic</h2>
        <p className="text-[12px] text-text-muted">
          原讨论会保留在当前 topic。新 topic 会从一条系统消息开始，记录摘要。
        </p>
        <label className="text-[12px] text-text-muted flex flex-col gap-1">
          新 topic 标题
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="border border-border rounded px-2 py-1.5 bg-surface-elev"
            autoFocus
          />
        </label>
        <div className="flex gap-2 mt-1">
          <button
            type="button"
            onClick={onCancel}
            className="px-3 py-1.5 rounded border border-border text-[13px]"
          >
            取消
          </button>
          <div className="flex-1" />
          <button
            type="submit"
            disabled={submitting || !title.trim()}
            className="px-3 py-1.5 rounded bg-text text-bg text-[13px] font-medium disabled:opacity-50"
          >
            创建
          </button>
        </div>
      </form>
    </div>
  );
}
```

Create `frontend/src/nudge/SpinoffDialog.test.tsx`:
```tsx
import { describe, it, expect, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { SpinoffDialog } from "./SpinoffDialog";

describe("<SpinoffDialog />", () => {
  it("submits title and fires onSubmit", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    const onCancel = vi.fn();
    renderWithProviders(
      <SpinoffDialog
        suggestedTitle="周五团建"
        onSubmit={onSubmit}
        onCancel={onCancel}
      />,
    );
    const input = screen.getByLabelText(/新 topic 标题/);
    expect((input as HTMLInputElement).value).toBe("周五团建");
    await user.click(screen.getByRole("button", { name: /创建/ }));
    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith("周五团建");
    });
  });

  it("calls onCancel from cancel button", async () => {
    const user = userEvent.setup();
    const onCancel = vi.fn();
    renderWithProviders(
      <SpinoffDialog
        suggestedTitle="t"
        onSubmit={vi.fn()}
        onCancel={onCancel}
      />,
    );
    await user.click(screen.getByRole("button", { name: /取消/ }));
    expect(onCancel).toHaveBeenCalled();
  });
});
```

- [ ] **Step 19.2: Update NudgeMessage test**

Replace `frontend/src/messages/NudgeMessage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { NudgeMessage } from "./NudgeMessage";

const sampleNudge = {
  id: 12, topic_id: 1, type: "nudge" as const,
  actor_type: "system" as const, actor_id: null,
  body: "这条线程已经讨论 framing 25 分钟，要不要先决定再继续？",
  metadata: { reason: "framing-loop", drift_summary: "discussing framing", drift_nudge_id: 1 },
  ref_event_id: null,
  created_at: "2026-05-19T10:50:00Z",
};

describe("<NudgeMessage />", () => {
  it("renders three quick-action buttons", () => {
    renderWithProviders(
      <NudgeMessage
        actor={{ kind: "system", initial: "S", displayName: "system" }}
        message={sampleNudge}
      />,
    );
    expect(screen.getByRole("button", { name: /独立成新 topic/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /回主线/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /略过/ })).toBeInTheDocument();
  });

  it("clicking 略过 dismisses the nudge", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <NudgeMessage
        actor={{ kind: "system", initial: "S", displayName: "system" }}
        message={sampleNudge}
      />,
    );
    await user.click(screen.getByRole("button", { name: /略过/ }));
    await waitFor(() => {
      expect(screen.getByText(/已处理：略过/)).toBeInTheDocument();
    });
  });

  it("clicking 独立成新 topic opens spinoff dialog", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <NudgeMessage
        actor={{ kind: "system", initial: "S", displayName: "system" }}
        message={sampleNudge}
      />,
    );
    await user.click(screen.getByRole("button", { name: /独立成新 topic/ }));
    await waitFor(() => {
      expect(screen.getByLabelText(/新 topic 标题/)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 19.3: Replace NudgeMessage.tsx**

```tsx
import { useState } from "react";
import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { useResolveNudge } from "../api/taskTreeQueries";
import { SpinoffDialog } from "../nudge/SpinoffDialog";
import type { NudgeResolution } from "../api/taskTreeTypes";

interface Actor { kind: "system" | "human" | "claude" | "codex"; initial: string; displayName: string }

interface NudgeMeta {
  reason?: string;
  drift_summary?: string;
  drift_nudge_id?: number;
}

export function NudgeMessage({
  message,
  actor,
}: {
  message: MessageDTO;
  actor: Actor;
}) {
  const meta = (message.metadata ?? {}) as NudgeMeta;
  const resolve = useResolveNudge(message.topic_id);
  const [showSpinoff, setShowSpinoff] = useState(false);
  const [resolvedBy, setResolvedBy] = useState<NudgeResolution | null>(null);
  const [spinoffTopicId, setSpinoffTopicId] = useState<number | null>(null);

  if (!meta.drift_nudge_id) {
    // Backward compat: nudge without backing drift_nudges row (legacy fixtures)
    return (
      <BaseMessage
        actor={actor}
        timeIso={message.created_at}
        tag="nudge"
        tone="nudge"
        body={<span>{message.body}</span>}
      />
    );
  }

  function doResolve(resolution: NudgeResolution, spinoffTitle?: string) {
    resolve.mutate(
      { id: meta.drift_nudge_id!, resolved_by: resolution, spinoff_title: spinoffTitle },
      {
        onSuccess: (data) => {
          setResolvedBy(resolution);
          if (data?.resolved_to_topic_id) setSpinoffTopicId(data.resolved_to_topic_id);
          setShowSpinoff(false);
        },
      },
    );
  }

  const footer =
    resolvedBy === "dismissed" ? (
      <span className="text-[11px] text-text-dim">已处理：略过</span>
    ) : resolvedBy === "returned" ? (
      <span className="text-[11px] text-text-dim">已处理：回主线</span>
    ) : resolvedBy === "moved_to_topic" ? (
      <span className="text-[11px] text-text-dim">
        已处理：迁移到 topic #{spinoffTopicId}
      </span>
    ) : null;

  return (
    <>
      <BaseMessage
        actor={actor}
        timeIso={message.created_at}
        tag={`nudge${meta.reason ? ` · ${meta.reason}` : ""}`}
        tone="nudge"
        body={
          <div className="flex flex-col gap-2">
            <span>{message.body}</span>
            {!resolvedBy ? (
              <div className="flex gap-2 items-center flex-wrap">
                <button
                  type="button"
                  onClick={() => setShowSpinoff(true)}
                  className="px-2 py-1 rounded bg-nudge text-bg text-[12px]"
                  disabled={resolve.isPending}
                >
                  独立成新 topic
                </button>
                <button
                  type="button"
                  onClick={() => doResolve("returned")}
                  className="px-2 py-1 rounded border border-border text-[12px]"
                  disabled={resolve.isPending}
                >
                  回主线
                </button>
                <button
                  type="button"
                  onClick={() => doResolve("dismissed")}
                  className="px-2 py-1 rounded border border-border text-[12px]"
                  disabled={resolve.isPending}
                >
                  略过
                </button>
              </div>
            ) : (
              footer
            )}
          </div>
        }
      />
      {showSpinoff && (
        <SpinoffDialog
          suggestedTitle={meta.drift_summary?.slice(0, 24) ?? "新 topic"}
          onSubmit={async (title) => doResolve("moved_to_topic", title)}
          onCancel={() => setShowSpinoff(false)}
        />
      )}
    </>
  );
}
```

- [ ] **Step 19.4: Add `drift_nudge_id` to the seed nudge metadata**

Edit `frontend/src/fixtures/seed.ts`. Find the `mk(12, ...)` line for the nudge and change its metadata:
```ts
mk(12, 1, "nudge", "system", null,
  "这条线程已经讨论 framing 25 分钟，要不要先决定再继续？",
  { reason: "framing-loop", drift_summary: "讨论 framing 25 分钟", drift_nudge_id: 1 },
  "2026-05-19T10:50:00Z"),
```

- [ ] **Step 19.5: Run tests**

```bash
cd frontend && /Users/jacky/.nvm/versions/node/v22.17.0/bin/pnpm test "NudgeMessage|SpinoffDialog" --run
```

Expected: 5 pass.

- [ ] **Step 19.6: Commit**

```bash
git add frontend/src/messages/NudgeMessage.tsx \
        frontend/src/messages/NudgeMessage.test.tsx \
        frontend/src/nudge/SpinoffDialog.tsx \
        frontend/src/nudge/SpinoffDialog.test.tsx \
        frontend/src/fixtures/seed.ts
git commit -m "$(cat <<'EOF'
feat(frontend): NudgeMessage three actions + SpinoffDialog

独立成新 topic opens a modal with prefilled title (from drift_summary),
回主线 and 略过 resolve immediately. Resolution shows a small footer
line in the same nudge component; nudge stays in stream.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 20: GoalProposalMessage component + dispatch wiring

**Files:**
- Create: `frontend/src/messages/GoalProposalMessage.tsx`
- Create: `frontend/src/messages/GoalProposalMessage.test.tsx`
- Modify: `frontend/src/messages/Message.tsx`

- [ ] **Step 20.1: Write failing test**

Create `frontend/src/messages/GoalProposalMessage.test.tsx`:
```tsx
import { describe, it, expect } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { renderWithProviders } from "../../test/render";
import { GoalProposalMessage } from "./GoalProposalMessage";

const sample = {
  id: 100, topic_id: 1, type: "goal_proposal" as const,
  actor_type: "agent" as const, actor_id: 11,
  body: "30 分钟 talk · 技术受众",
  metadata: { artifact_id: null, spec_text: "30 分钟 talk · 技术受众" },
  ref_event_id: null,
  created_at: "2026-05-19T09:30:00Z",
};

describe("<GoalProposalMessage />", () => {
  it("renders the proposed spec and an adopt button", () => {
    renderWithProviders(
      <GoalProposalMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={sample}
      />,
    );
    expect(screen.getByText(/30 分钟 talk/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Set as goal/i })).toBeInTheDocument();
  });

  it("adopts the goal on click", async () => {
    const user = userEvent.setup();
    renderWithProviders(
      <GoalProposalMessage
        actor={{ kind: "claude", initial: "CC", displayName: "claude" }}
        message={sample}
      />,
    );
    await user.click(screen.getByRole("button", { name: /Set as goal/i }));
    await waitFor(() => {
      expect(screen.getByText(/Adopted/i)).toBeInTheDocument();
    });
  });
});
```

- [ ] **Step 20.2: Create `GoalProposalMessage.tsx`**

```tsx
import { useState } from "react";
import type { MessageDTO } from "../api/types";
import { BaseMessage } from "./BaseMessage";
import { useAdoptGoalProposal } from "../api/taskTreeQueries";

interface Actor {
  kind: "human" | "claude" | "codex" | "system";
  initial: string;
  displayName: string;
}

interface GoalProposalMeta {
  artifact_id?: number | null;
  spec_text?: string;
}

export function GoalProposalMessage({
  message,
  actor,
}: {
  message: MessageDTO;
  actor: Actor;
}) {
  const meta = (message.metadata ?? {}) as GoalProposalMeta;
  const adopt = useAdoptGoalProposal(message.topic_id);
  const [adopted, setAdopted] = useState(false);

  function handleAdopt() {
    adopt.mutate(
      { goal_proposal_message_id: message.id },
      { onSuccess: () => setAdopted(true) },
    );
  }

  return (
    <BaseMessage
      actor={actor}
      timeIso={message.created_at}
      tag="goal_proposal"
      tone="spec"
      body={
        <div className="flex flex-col gap-2">
          {meta.artifact_id && (
            <div className="font-mono text-[12px] text-text-muted">
              artifact#{meta.artifact_id}
            </div>
          )}
          <div className="text-[13px]">{message.body}</div>
          <div className="flex items-center gap-2 mt-1">
            <div className="flex-1" />
            {adopted ? (
              <span className="text-[12px] text-status-on font-medium">
                Adopted ✓
              </span>
            ) : (
              <button
                type="button"
                onClick={handleAdopt}
                disabled={adopt.isPending}
                className="px-2 py-1 rounded bg-spec text-bg text-[12px] font-medium disabled:opacity-40"
              >
                Set as goal
              </button>
            )}
          </div>
        </div>
      }
    />
  );
}
```

- [ ] **Step 20.3: Add dispatch case to `Message.tsx`**

Edit `frontend/src/messages/Message.tsx`. Add at top:
```ts
import { GoalProposalMessage } from "./GoalProposalMessage";
```

Then in the `switch (message.type)` block, add a case before the `system` case:
```ts
    case "goal_proposal":
      return <GoalProposalMessage message={message} actor={actor} />;
```

Note: `MessageType` already includes `goal_proposal` (added by Track C1.5 backend work), so this is purely UI dispatch.

If `MESSAGE_TYPES` in `frontend/src/api/types.ts` does NOT include `"goal_proposal"`, add it. Verify:
```bash
grep "goal_proposal" frontend/src/api/types.ts
```

If absent, find the `MESSAGE_TYPES` array and add `"goal_proposal"` to it.

- [ ] **Step 20.4: Run tests**

```bash
cd frontend && /Users/jacky/.nvm/versions/node/v22.17.0/bin/pnpm test GoalProposalMessage --run
```

Expected: 2 pass.

```bash
cd frontend && /Users/jacky/.nvm/versions/node/v22.17.0/bin/pnpm exec tsc --noEmit
```

Expected: 0 errors.

- [ ] **Step 20.5: Commit**

```bash
git add frontend/src/messages/GoalProposalMessage.tsx \
        frontend/src/messages/GoalProposalMessage.test.tsx \
        frontend/src/messages/Message.tsx \
        frontend/src/api/types.ts
git commit -m "$(cat <<'EOF'
feat(frontend): GoalProposalMessage typed-message component

Dispatches goal_proposal messages in the stream. Set as goal button
posts POST /api/topics/{id}/goal referencing this message id.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 21: `lets-goal-guardian` skill

**Files:**
- Create: `.claude/skills/lets-goal-guardian/SKILL.md`

- [ ] **Step 21.1: Create the skill file**

Create `.claude/skills/lets-goal-guardian/SKILL.md`:
```markdown
---
name: lets-goal-guardian
description: Use whenever a Lets topic is open. Reads drift_context from the topic stream response and decides whether to post a nudge using LLM judgment, never an algorithm. Only nudges actionable topics; respects prior dismissal; sticks to "温和提醒" tone.
---

# Lets Goal Guardian

This skill activates whenever you are working in a Lets topic (you posted at
least one message in the topic, or were @mentioned in it).

## Read drift_context first

The `GET /api/topics/{id}/messages` response contains:

```json
{
  "messages": [...],
  "drift_context": {
    "topic_mode": "exploratory" | "actionable",
    "active_task": { "id": int, "title": string } | null,
    "last_nudge_at": string | null,
    "last_nudge_message_id": int | null,
    "last_nudge_resolved_by": "moved_to_topic" | "returned" | "dismissed" | null,
    "messages_since_last_nudge": int
  }
}
```

You consume this same response when you read the stream. **Read it on every
reply** — don't cache.

## When to nudge

Post a `nudge` (via the `post_nudge` MCP tool) only when ALL of the following
hold:

1. `topic_mode == "actionable"`.
2. `active_task != null` — there is a clear current task to drift away from.
3. Looking at the most recent 3–5 messages in the topic, they discuss
   something **clearly unrelated** to `active_task.title`. Use your own
   judgment. Examples that count as drift: scheduling lunch, planning a
   team dinner, discussing unrelated bugs in a different project. Examples
   that DON'T count: tangential research, jokes that bring the team back,
   the same task discussed from a different angle.
4. `messages_since_last_nudge >= 3` — you don't nudge after every off-topic
   message; let conversations breathe.
5. `last_nudge_at` is either null, or more than 5 minutes ago, or the prior
   nudge was resolved as `"returned"` (not `"dismissed"` and not pending).
6. If `last_nudge_resolved_by == "dismissed"`, do NOT nudge again until a
   clear topic-shift signal (e.g., someone posts a question about a totally
   new subject, suggesting that "dismissed" no longer applies).

## How to nudge

Call `post_nudge(topic_id, reason, drift_summary)`:

- `reason`: 1 sentence, gentle. Examples: "这条线程已经讨论 X 几分钟了，要不要
  先聚焦 active task？" / "看起来话题漂到 X 了，需要回主线吗？"
- `drift_summary`: 2–4 words capturing what the off-topic discussion is
  about. The user will see this when deciding whether to spin it off as a
  separate topic. Examples: "周五团建" / "另一个项目的 bug" / "选择编辑器
  字体".

## Tone discipline

- Never blame ("you're off topic").
- Always offer the spinoff path first ("可以独立成新 topic 继续聊").
- Don't nudge twice for the same drift window even if conversation
  technically resets.

## What NOT to do

- Don't call `post_nudge` if `topic_mode == "exploratory"`. Exploratory
  topics are explicitly for free-form exploration.
- Don't call `post_nudge` if there is no `active_task`. Without a task
  to drift from, "drift" is meaningless.
- Don't post a `chat` message saying "I noticed drift" — use the nudge
  typed message via the MCP tool. Chat messages don't get the visual
  treatment (background tint + three quick-action buttons) that humans
  expect from a nudge.

## Tuning

If users report "you nudge too much" or "you never nudge when needed,"
adjust the heuristics in step 3 (relevance threshold) and step 4
(messages_since_last_nudge minimum). Both live in this skill, not in
code.
```

- [ ] **Step 21.2: Verify file exists**

```bash
ls -la .claude/skills/lets-goal-guardian/SKILL.md
```

- [ ] **Step 21.3: Commit**

```bash
git add .claude/skills/lets-goal-guardian/SKILL.md
git commit -m "$(cat <<'EOF'
feat(skill): lets-goal-guardian — agent-side drift-nudge discipline

Captures the LLM-judgment heuristic agents use to decide whether
to post_nudge: read drift_context, check active_task + topic_mode,
check messages_since_last_nudge, respect dismissed resolution,
maintain 温和提醒 tone. All tuning is via this skill text, not code.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 22: End-to-end pytest + Playwright

**Files:**
- Create: `tests/test_e2e_goal_guardian.py`
- Modify: `frontend/e2e/ppt-scenario.spec.ts` (append e2e scenarios)

- [ ] **Step 22.1: Create backend e2e test**

Create `tests/test_e2e_goal_guardian.py`:
```python
def test_e2e_goal_guardian_full_scenario(client):
    """Replays the spec §10 success criteria as a pytest scenario."""
    from app.auth import issue_session
    from app.db import connect
    from app.identity import ensure_human, ensure_agent_instance
    from app.mcp_server import (
        propose_task_tree,
        post_nudge as mcp_post_nudge,
    )
    from app.messages import post_message, topic_stream

    # 1. Neo sets up a topic in actionable mode
    neo = ensure_human("Neo")
    sess = issue_session(neo)
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO topics (slug, title, mode)
               VALUES ('e2e-gg', 'Goal Guardian E2E', 'actionable')"""
        )
        tid = cur.lastrowid

    # 2. claude proposes a 5-item task tree (1 has nested children)
    cc = ensure_agent_instance(role="claude", human_id=neo, device_label="neo-mbp")
    proposal = propose_task_tree(
        topic_id=tid,
        title="PPT Tree",
        items=[
            {"title": "Outline"},
            {"title": "Section 1", "parent_index": 0},
            {"title": "Section 1.1", "parent_index": 1},
            {"title": "Section 1.2", "parent_index": 1},
            {"title": "Section 2", "parent_index": 0},
        ],
    )

    # 3. Neo adopts → tree visible with hierarchy
    res = client.post(
        f"/api/topics/{tid}/task-tree",
        cookies={"lets_session": sess},
        json={"proposal_message_id": proposal["id"]},
    )
    assert res.status_code == 201
    tree_response = res.json()
    assert len(tree_response["items"]) == 5
    # Item with parent_index=1 should have parent_item_id of items[1]
    items_by_title = {i["title"]: i for i in tree_response["items"]}
    assert items_by_title["Section 1.1"]["parent_item_id"] == items_by_title["Section 1"]["id"]

    # 4. Conversation drifts to team dinner (3+ chat messages)
    for body in ["顺便聊一下周五团建", "周五晚 7 点 OK 吗", "去那家烤肉店？"]:
        post_message(
            topic_id=tid, type="chat", actor_type="human",
            actor_id=neo, body=body, metadata={},
        )

    # 5. codex (different agent) reads drift_context, posts nudge
    cx = ensure_agent_instance(role="codex", human_id=neo, device_label="neo-mbp")
    stream_res = client.get(
        f"/api/topics/{tid}/messages",
        cookies={"lets_session": sess},
    )
    ctx = stream_res.json()["drift_context"]
    assert ctx["topic_mode"] == "actionable"
    assert ctx["messages_since_last_nudge"] >= 3

    nudge = mcp_post_nudge(
        topic_id=tid,
        reason="看起来话题漂到周五团建了，需要回主线吗？",
        drift_summary="周五团建",
        triggered_by_agent_instance_id=cx,
    )
    assert "nudge_message_id" in nudge

    # 6. Neo clicks "独立成新 topic" — verify the spinoff flow
    res = client.post(
        f"/api/nudges/{nudge['drift_nudge_id']}/resolve",
        cookies={"lets_session": sess},
        json={"resolved_by": "moved_to_topic", "spinoff_title": "周五团建"},
    )
    assert res.status_code == 200
    body = res.json()
    new_topic_id = body["resolved_to_topic_id"]
    assert new_topic_id is not None
    assert new_topic_id != tid

    # 7. New topic has the expected system message with drift_summary
    with connect() as conn:
        sysmsg = conn.execute(
            """SELECT body FROM messages
               WHERE topic_id = ? AND type = 'system' LIMIT 1""",
            (new_topic_id,),
        ).fetchone()
        title_row = conn.execute(
            "SELECT title FROM topics WHERE id = ?", (new_topic_id,)
        ).fetchone()
    assert "周五团建" in sysmsg["body"]
    assert title_row["title"] == "周五团建"

    # 8. Original topic's drift_context now reflects resolution
    res2 = client.get(
        f"/api/topics/{tid}/messages",
        cookies={"lets_session": sess},
    )
    ctx2 = res2.json()["drift_context"]
    assert ctx2["last_nudge_resolved_by"] == "moved_to_topic"
```

- [ ] **Step 22.2: Append Playwright e2e**

Append to `frontend/e2e/ppt-scenario.spec.ts`:
```ts
test("Adopt task_tree_proposal — button flips to Adopted", async ({ page }) => {
  await page.goto("/");
  // Scroll to the task_tree_proposal message
  const adoptBtn = page.getByRole("button", { name: /Adopt as task tree/i });
  await expect(adoptBtn).toBeVisible();
  await adoptBtn.click();
  await expect(page.getByText(/Adopted/i)).toBeVisible();
});

test("Nudge 略过 dismisses the nudge inline", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "略过" }).click();
  await expect(page.getByText(/已处理：略过/)).toBeVisible();
});

test("Spinoff dialog creates new topic + footer updates", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "独立成新 topic" }).click();
  // Default title prefilled from drift_summary
  await page.getByLabel(/新 topic 标题/).fill("周五团建");
  await page.getByRole("button", { name: "创建" }).click();
  await expect(page.getByText(/已处理：迁移到 topic/)).toBeVisible();
});
```

- [ ] **Step 22.3: Run all tests**

Backend:
```bash
.venv/bin/pytest -q
```

Frontend unit + integration:
```bash
cd frontend && /Users/jacky/.nvm/versions/node/v22.17.0/bin/pnpm test --run
```

Frontend Playwright:
```bash
cd frontend && /Users/jacky/.nvm/versions/node/v22.17.0/bin/pnpm e2e
```

Expected: backend ~220 pass, frontend ~62 pass, Playwright 6 pass (3 prior + 3 new). If MSW seed mutation across tests causes flakiness (a previous test leaves the nudge resolved, the next test can't find the button), prefix the suite with `test.describe.configure({ mode: "serial" })` and use the `resetFixtures()` helper at test boundaries.

- [ ] **Step 22.4: Commit**

```bash
git add tests/test_e2e_goal_guardian.py frontend/e2e/ppt-scenario.spec.ts
git commit -m "$(cat <<'EOF'
test(goal-guardian): backend + Playwright e2e for §10 scenario

Backend replay: propose tree → adopt → drift → nudge (via MCP)
→ moved_to_topic → verify new topic + system message + drift_context
update on original topic.

Playwright: Adopt task_tree_proposal button, 略过 inline dismissal,
spinoff dialog creates new topic.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

### Spec coverage check

Going through `docs/superpowers/specs/2026-05-19-goal-guardian-design.md` section by section:

- **§3 Architecture diagram** — All five pieces present: task_trees (Task 2), task_items (Task 2), drift_nudges (Task 3), topics.mode (Task 1), drift_context in topic_stream (Task 9). ✅
- **§4.1 topics.mode column** — Task 1. ✅
- **§4.2 task_trees table** — Task 2. ✅
- **§4.3 task_items table + XOR owner CHECK** — Task 2. ✅
- **§4.4 drift_nudges table** — Task 3. ✅
- **§5.1 GET /api/topics/{id}/task-tree** — Task 4. ✅
- **§5.1 POST /api/topics/{id}/task-tree + /goal** — Task 5. ✅
- **§5.1 POST + PATCH /api/task-items** — Task 6. ✅
- **§5.1 POST /api/nudges/{id}/resolve** — Task 7. ✅
- **§5.2 MCP tools (propose_goal, propose_task_tree, update_task_status, post_nudge)** — Tasks 10–13. ✅
- **§5.3 topic_stream extension** — Task 9. ✅
- **§6.1 TaskTreePanel rewrite** — Task 16. ✅
- **§6.2 NudgeMessage interactions** — Task 19. ✅
- **§6.3 TaskTreeProposalMessage adopt button** — Task 18. ✅
- **§6.4 GoalProposalMessage component** — Task 20. ✅
- **§6.5 GoalDetailPanel real data** — Task 17. ✅
- **§7.1 lets-goal-guardian skill** — Task 21. ✅
- **§10 success scenario** — Task 22 e2e + Playwright. ✅

No gaps.

### Placeholder check

Searched for TBD / TODO / "fill in" / "Similar to Task N" / "Add appropriate error handling" / "Write tests for the above" — none found.

### Type consistency

- `task_tree_id` / `task_item_id` / `topic_id` are integers throughout, in matching names across Python (`int`) and TS (`number`).
- `MessageType` includes `goal_proposal` (Task 20 step 20.3 verifies).
- `NudgeMeta` shape on the frontend uses `drift_nudge_id?: number` matching the backend's `drift_nudges.id` (Task 13 returns this; Task 19.4 stores it in the seed metadata).
- `tone="spec"` reused for both `goal_proposal` and `spec_change` — intentional, both are config-change-like; if the colors look too similar in review, tweak in a polish pass.
- `task_items.status` values `pending|active|done` consistent in:
  - DB CHECK (Task 2)
  - `app/task_trees.py` `update_item` validation (Task 3)
  - `TaskItemPatch` Pydantic (Task 6)
  - `TaskItemDTO` TS union (Task 14)
  - skill text (Task 21)

No inconsistencies.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-19-goal-guardian.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
