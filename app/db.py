from __future__ import annotations

import os
import re
import sqlite3
import threading
from contextlib import contextmanager
from typing import Any, Iterator, Sequence

import psycopg
from psycopg.rows import dict_row


IntegrityError = sqlite3.IntegrityError


def database_url() -> str:
    return (
        os.environ.get("DATABASE_URL")
        or os.environ.get("LETS_DATABASE_URL")
        or "postgresql://jacky@localhost:5432/lets_dev"
    )


class _Row(dict):
    """Small sqlite3.Row-compatible dict.

    Most of Lets was written against sqlite3.Row. This keeps both
    row["name"] and row[0] working while the storage backend is Postgres.
    """

    def __init__(self, values: dict[str, Any]):
        super().__init__(values)
        self._keys = list(values.keys())

    def __getitem__(self, key: int | str) -> Any:  # type: ignore[override]
        if isinstance(key, int):
            return super().__getitem__(self._keys[key])
        return super().__getitem__(key)


def _row(values: dict[str, Any]) -> _Row:
    return _Row(dict(values))


_INSERT_RE = re.compile(r"^\s*INSERT\s+INTO\s+", re.IGNORECASE)
_RETURNING_RE = re.compile(r"\bRETURNING\b", re.IGNORECASE)
_PRAGMA_TABLE_INFO_RE = re.compile(
    r"^\s*PRAGMA\s+table_info\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*$",
    re.IGNORECASE,
)
_SQLITE_MASTER_RE = re.compile(
    r"^\s*SELECT\s+(?P<select>.+?)\s+FROM\s+sqlite_master(?P<rest>.*)$",
    re.IGNORECASE | re.DOTALL,
)
_DATETIME_NOW_RE = re.compile(
    r"datetime\s*\(\s*'now'\s*(?:,\s*'(?P<offset>[+-]\d+)\s+(?P<unit>[A-Za-z]+)'\s*)?\)",
    re.IGNORECASE,
)


def _translate_datetime(sql: str) -> str:
    def repl(m: re.Match[str]) -> str:
        offset = m.group("offset")
        unit = m.group("unit")
        if not offset or not unit:
            return "NOW()"
        sign = "+" if offset.startswith("+") else "-"
        amount = offset[1:]
        return f"NOW() {sign} INTERVAL '{amount} {unit}'"

    return _DATETIME_NOW_RE.sub(repl, sql)


def _translate_placeholders(sql: str) -> str:
    """Convert sqlite ``?`` placeholders to psycopg ``%s`` placeholders."""
    out: list[str] = []
    in_string = False
    quote = ""
    i = 0
    while i < len(sql):
        ch = sql[i]
        if in_string:
            if ch == quote:
                in_string = False
            if ch == "%":
                out.append("%%")
            else:
                out.append(ch)
        else:
            if ch in ("'", '"'):
                in_string = True
                quote = ch
                out.append(ch)
            elif ch == "?":
                out.append("%s")
            elif ch == "%":
                out.append("%%")
            else:
                out.append(ch)
        i += 1
    return "".join(out)


def _translate_sqlite_master(sql: str) -> str | None:
    m = _SQLITE_MASTER_RE.match(sql)
    if not m:
        return None
    select = m.group("select")
    rest = m.group("rest")
    # Tests only need name/sql/table/index introspection. pg_indexes.indexdef
    # is close enough to sqlite_master.sql for CHECK-style assertions.
    translated = (
        "SELECT table_name AS name, 'table' AS type, table_name AS tbl_name, "
        "NULL::text AS sql FROM information_schema.tables "
        "WHERE table_schema = 'public' "
        "UNION ALL "
        "SELECT indexname AS name, 'index' AS type, tablename AS tbl_name, "
        "indexdef AS sql FROM pg_indexes WHERE schemaname = 'public'"
    )
    out = f"SELECT {select} FROM ({translated}) sqlite_master {rest}"
    return out


def _translate_pragma(sql: str) -> str | None:
    m = _PRAGMA_TABLE_INFO_RE.match(sql)
    if not m:
        return None
    table = m.group(1)
    return (
        "SELECT column_name AS name, data_type AS type, "
        "CASE WHEN is_nullable = 'NO' THEN 1 ELSE 0 END AS notnull, "
        "column_default AS dflt_value "
        "FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = "
        f"'{table}' ORDER BY ordinal_position"
    )


def _translate_sql(sql: str) -> str:
    translated = _translate_pragma(sql) or _translate_sqlite_master(sql) or sql
    translated = _translate_datetime(translated)
    translated = re.sub(
        r"\bINSERT\s+OR\s+IGNORE\s+INTO\b",
        "INSERT INTO",
        translated,
        flags=re.IGNORECASE,
    )
    translated = _translate_placeholders(translated)
    translated = re.sub(r"\bIS\s+%s\b", "IS NOT DISTINCT FROM %s", translated, flags=re.IGNORECASE)
    return translated


class Cursor:
    def __init__(self, pg_cur: psycopg.Cursor):
        self._cur = pg_cur
        self.lastrowid: int | None = None
        self._auto_returning = False

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> "Cursor":
        sql_pg = _translate_sql(sql)
        self._auto_returning = False
        if _INSERT_RE.match(sql_pg) and not _RETURNING_RE.search(sql_pg):
            sql_pg = sql_pg.rstrip().rstrip(";") + " RETURNING id"
            self._auto_returning = True
        try:
            if params is None:
                self._cur.execute(sql_pg)
            else:
                self._cur.execute(sql_pg, tuple(params))
        except psycopg.errors.IntegrityError as e:
            raise sqlite3.IntegrityError(str(e)) from e
        self.lastrowid = None
        if self._auto_returning:
            try:
                row = self._cur.fetchone()
            except psycopg.ProgrammingError:
                row = None
            if row and "id" in row:
                self.lastrowid = int(row["id"])
        return self

    def executemany(self, sql: str, seq_params: list[Sequence[Any]]) -> "Cursor":
        sql_pg = _translate_sql(sql)
        self._cur.executemany(sql_pg, [tuple(p) for p in seq_params])
        return self

    def fetchone(self) -> _Row | None:
        try:
            row = self._cur.fetchone()
        except psycopg.ProgrammingError:
            return None
        return _row(row) if row is not None else None

    def fetchall(self) -> list[_Row]:
        try:
            rows = self._cur.fetchall()
        except psycopg.ProgrammingError:
            return []
        return [_row(r) for r in rows]

    @property
    def rowcount(self) -> int:
        return self._cur.rowcount

    def close(self) -> None:
        self._cur.close()


class Connection:
    def __init__(self, pg: psycopg.Connection):
        self._pg = pg

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> Cursor:
        cur = Cursor(self._pg.cursor(row_factory=dict_row))
        return cur.execute(sql, params)

    def executemany(self, sql: str, seq_params: list[Sequence[Any]]) -> Cursor:
        cur = Cursor(self._pg.cursor(row_factory=dict_row))
        return cur.executemany(sql, seq_params)

    def executescript(self, script: str) -> None:
        with self._pg.cursor() as cur:
            for statement in script.split(";"):
                statement = statement.strip()
                if statement:
                    cur.execute(statement)

    def commit(self) -> None:
        self._pg.commit()

    def rollback(self) -> None:
        self._pg.rollback()

    def close(self) -> None:
        self._pg.close()


@contextmanager
def connect() -> Iterator[Connection]:
    raw = psycopg.connect(database_url(), autocommit=False)
    conn = Connection(raw)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS work_items (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    type TEXT NOT NULL CHECK (type IN ('idea', 'task')),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open'
        CHECK (status IN ('open', 'claimed', 'in_progress', 'done', 'rejected')),
    created_by TEXT NOT NULL DEFAULT 'human',
    claimed_by_agent_id BIGINT,
    claimed_at TIMESTAMPTZ,
    git_branch TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS agents (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    agent_type TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'idle'
        CHECK (status IN ('idle', 'active', 'blocked', 'offline')),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS humans (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    email TEXT,
    github_id BIGINT UNIQUE,
    github_login TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS sessions (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    value_hash TEXT NOT NULL UNIQUE,
    human_id BIGINT NOT NULL REFERENCES humans(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_sessions_value_hash ON sessions(value_hash);
CREATE TABLE IF NOT EXISTS workspaces (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
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
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
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
CREATE TABLE IF NOT EXISTS agent_roles (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS agent_instances (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    role_id BIGINT NOT NULL REFERENCES agent_roles(id),
    human_id BIGINT NOT NULL REFERENCES humans(id),
    workspace_id BIGINT NOT NULL REFERENCES workspaces(id),
    device_label TEXT,
    model TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_agent_instances_human ON agent_instances(human_id);
CREATE INDEX IF NOT EXISTS idx_agent_instances_role ON agent_instances(role_id);
CREATE INDEX IF NOT EXISTS idx_agent_instances_workspace ON agent_instances(workspace_id);
CREATE TABLE IF NOT EXISTS tokens (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    value_hash TEXT NOT NULL UNIQUE,
    human_id BIGINT NOT NULL REFERENCES humans(id),
    agent_instance_id BIGINT REFERENCES agent_instances(id),
    label TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_tokens_value_hash ON tokens(value_hash);
CREATE INDEX IF NOT EXISTS idx_tokens_human ON tokens(human_id);
CREATE TABLE IF NOT EXISTS device_auth_flows (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    device_code TEXT NOT NULL UNIQUE,
    user_code TEXT NOT NULL UNIQUE,
    role TEXT NOT NULL,
    device_label TEXT NOT NULL,
    model TEXT,
    workspace_id BIGINT REFERENCES workspaces(id),
    human_id BIGINT REFERENCES humans(id),
    agent_instance_id BIGINT REFERENCES agent_instances(id),
    token_id BIGINT REFERENCES tokens(id),
    token_value TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    authorized_at TIMESTAMPTZ,
    consumed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_device_auth_flows_device_code ON device_auth_flows(device_code);
CREATE INDEX IF NOT EXISTS idx_device_auth_flows_user_code ON device_auth_flows(user_code);
CREATE TABLE IF NOT EXISTS events (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    event_type TEXT NOT NULL,
    actor_type TEXT NOT NULL CHECK (actor_type IN ('human', 'agent', 'system')),
    actor_id BIGINT,
    target_type TEXT NOT NULL,
    target_id BIGINT,
    project_id BIGINT,
    topic_id BIGINT,
    payload TEXT NOT NULL DEFAULT '{}',
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_events_target ON events(target_type, target_id);
CREATE INDEX IF NOT EXISTS idx_events_occurred_at ON events(occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_topic ON events(topic_id, occurred_at DESC);
CREATE TABLE IF NOT EXISTS status_updates (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    agent_id BIGINT NOT NULL REFERENCES agents(id),
    work_item_id BIGINT REFERENCES work_items(id),
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS findings (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    work_item_id BIGINT REFERENCES work_items(id),
    agent_id BIGINT NOT NULL REFERENCES agents(id),
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS human_notes (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    work_item_id BIGINT REFERENCES work_items(id),
    body TEXT NOT NULL,
    feedback_type TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS topics (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    workspace_id BIGINT REFERENCES workspaces(id),
    mode TEXT NOT NULL DEFAULT 'exploratory'
        CHECK (mode IN ('exploratory', 'actionable')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_topics_workspace ON topics(workspace_id);
CREATE TABLE IF NOT EXISTS messages (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    topic_id BIGINT NOT NULL REFERENCES topics(id),
    type TEXT NOT NULL CHECK (type IN (
        'chat', 'status', 'finding', 'decision', 'question',
        'handoff', 'review', 'artifact_revision', 'spec_change',
        'nudge', 'proactive_finding', 'task_tree_proposal',
        'project_proposal', 'goal_proposal', 'system', 'annotation'
    )),
    actor_type TEXT NOT NULL CHECK (actor_type IN ('human', 'agent', 'system')),
    actor_id BIGINT,
    body TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    ref_event_id BIGINT REFERENCES events(id),
    addressed_to TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_messages_topic_created ON messages(topic_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(type);
CREATE TABLE IF NOT EXISTS artifacts (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    slug TEXT NOT NULL,
    type TEXT NOT NULL,
    backend TEXT NOT NULL,
    backend_ref TEXT NOT NULL,
    title TEXT NOT NULL,
    topic_id BIGINT NOT NULL REFERENCES topics(id),
    current_version_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(slug, topic_id)
);
CREATE INDEX IF NOT EXISTS idx_artifacts_topic ON artifacts(topic_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(type);
CREATE TABLE IF NOT EXISTS artifact_versions (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    artifact_id BIGINT NOT NULL REFERENCES artifacts(id),
    version_label TEXT NOT NULL,
    backend_revision_id TEXT NOT NULL,
    created_by_human_id BIGINT REFERENCES humans(id),
    created_by_agent_instance_id BIGINT REFERENCES agent_instances(id),
    summary TEXT,
    preview_uri TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(artifact_id, version_label)
);
CREATE INDEX IF NOT EXISTS idx_artifact_versions_artifact ON artifact_versions(artifact_id, created_at DESC);
CREATE TABLE IF NOT EXISTS task_trees (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    topic_id BIGINT NOT NULL UNIQUE REFERENCES topics(id),
    goal_artifact_id BIGINT REFERENCES artifacts(id),
    goal_spec_text TEXT,
    version INT NOT NULL DEFAULT 1,
    approved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_by_human_id BIGINT REFERENCES humans(id),
    proposal_message_id BIGINT REFERENCES messages(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_task_trees_topic ON task_trees(topic_id);
CREATE TABLE IF NOT EXISTS task_items (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    task_tree_id BIGINT NOT NULL REFERENCES task_trees(id),
    parent_item_id BIGINT REFERENCES task_items(id),
    title TEXT NOT NULL,
    summary TEXT,
    linked_message_id BIGINT REFERENCES messages(id),
    deliverable_artifact_id BIGINT REFERENCES artifacts(id),
    owner_human_id BIGINT REFERENCES humans(id),
    owner_agent_instance_id BIGINT REFERENCES agent_instances(id),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'done')),
    position INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (NOT (owner_human_id IS NOT NULL AND owner_agent_instance_id IS NOT NULL))
);
CREATE INDEX IF NOT EXISTS idx_task_items_tree ON task_items(task_tree_id, position);
CREATE INDEX IF NOT EXISTS idx_task_items_parent ON task_items(parent_item_id);
CREATE TABLE IF NOT EXISTS drift_nudges (
    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    topic_id BIGINT NOT NULL REFERENCES topics(id),
    nudge_message_id BIGINT NOT NULL UNIQUE REFERENCES messages(id),
    triggered_by_agent_instance_id BIGINT REFERENCES agent_instances(id),
    drift_window_start_message_id BIGINT,
    drift_window_end_message_id BIGINT,
    drift_summary TEXT,
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT CHECK (
        resolved_by IS NULL OR resolved_by IN ('moved_to_topic', 'returned', 'dismissed')
    ),
    resolved_to_topic_id BIGINT REFERENCES topics(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_drift_nudges_topic ON drift_nudges(topic_id, created_at DESC);
"""


_init_lock = threading.Lock()
_initialized_url: str | None = None


def _migrate_projects_to_workspaces(conn) -> None:
    """One-shot migration for environments deployed before the workspace rewrite.

    MUST run BEFORE the main schema executescript so that subsequent
    `CREATE INDEX ... ON topics(workspace_id)` statements find the column
    already renamed. Idempotent — a no-op when the new schema is in place.

    Steps when legacy schema is detected:
      1. Create workspaces + workspace_members tables (minimal DDL — full
         schema with indexes runs in executescript afterwards)
      2. Copy projects → workspaces preserving id
      3. Rename topics.project_id → topics.workspace_id
      4. Backfill / NOT-NULL agent_instances.workspace_id
      5. Drop the legacy projects table
    """
    cols = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'topics' AND column_name IN ('project_id', 'workspace_id')"
    ).fetchall()
    col_names = {r["column_name"] for r in cols}
    has_legacy = "project_id" in col_names
    has_new = "workspace_id" in col_names
    if not has_legacy:
        return  # already on new schema (or fresh DB — executescript handles it)

    # Minimal DDL: create just the targets the INSERTs/FKs below need.
    # The full schema (indexes, workspace_invites etc) is created by
    # executescript() right after this migration returns.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workspaces (
            id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
            slug TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            owner_human_id BIGINT REFERENCES humans(id),
            is_private BOOLEAN NOT NULL DEFAULT TRUE,
            deleted_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_members (
            workspace_id BIGINT NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            human_id BIGINT NOT NULL REFERENCES humans(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK (role IN ('owner', 'member')),
            joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (workspace_id, human_id)
        )
        """
    )

    legacy_projects_exists = bool(conn.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = 'projects'"
    ).fetchone())

    if legacy_projects_exists:
        # Step 1: copy projects rows into workspaces, preserving id.
        # Explicit RETURNING because the wrapper auto-appends "RETURNING id"
        # which clashes with INSERT...SELECT...ON CONFLICT scoping.
        conn.execute(
            """
            INSERT INTO workspaces (id, slug, name, description, owner_human_id,
                                    created_at, updated_at)
            SELECT id, slug, name, description, owner_human_id,
                   created_at, updated_at
            FROM projects
            ON CONFLICT (id) DO NOTHING
            RETURNING workspaces.id
            """
        )
        # Step 3: project owner becomes workspace owner.
        conn.execute(
            """
            INSERT INTO workspace_members (workspace_id, human_id, role)
            SELECT id, owner_human_id, 'owner'
            FROM workspaces
            WHERE owner_human_id IS NOT NULL
            ON CONFLICT DO NOTHING
            RETURNING workspace_members.workspace_id
            """
        )
        # Resync the workspaces id sequence after preserving legacy ids.
        conn.execute(
            "SELECT setval(pg_get_serial_sequence('workspaces', 'id'), "
            "COALESCE((SELECT MAX(id) FROM workspaces), 1))"
        )

    # Step 2: rename topics.project_id → topics.workspace_id.
    if not has_new:
        # Drop the FK that referenced projects(id) — the new FK to workspaces(id)
        # is named topics_workspace_id_fkey, but the legacy column had its own
        # constraint that must go first.
        conn.execute(
            """
            DO $$
            DECLARE fk_name TEXT;
            BEGIN
              SELECT conname INTO fk_name FROM pg_constraint
              WHERE conrelid = 'topics'::regclass
                AND contype = 'f'
                AND pg_get_constraintdef(oid) LIKE '%project_id%';
              IF fk_name IS NOT NULL THEN
                EXECUTE 'ALTER TABLE topics DROP CONSTRAINT ' || quote_ident(fk_name);
              END IF;
            END $$;
            """
        )
        conn.execute("ALTER TABLE topics RENAME COLUMN project_id TO workspace_id")
        conn.execute(
            "ALTER TABLE topics ADD CONSTRAINT topics_workspace_id_fkey "
            "FOREIGN KEY (workspace_id) REFERENCES workspaces(id)"
        )

    # Step 4: drop the legacy table.
    conn.execute("DROP TABLE IF EXISTS projects CASCADE")

    # Step 5: agent_instances.workspace_id NOT NULL — fill any legacy NULLs.
    # Pre-rewrite agent_instances rows didn't have a workspace_id at all,
    # so the column was just added by CREATE TABLE IF NOT EXISTS? Actually no,
    # if the table already exists the CREATE is a no-op and the column may
    # be missing. Add it (nullable), backfill with the human's first workspace
    # (or auto-create one), then enforce NOT NULL.
    ai_cols = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'agent_instances' AND column_name = 'workspace_id'"
    ).fetchone()
    if ai_cols is None:
        conn.execute(
            "ALTER TABLE agent_instances ADD COLUMN workspace_id BIGINT "
            "REFERENCES workspaces(id)"
        )
        # Orphaned agents (human with no workspace membership) get a personal
        # workspace auto-created. Can't DELETE them — tokens FK to
        # agent_instances would block it, and dropping tokens would log the
        # user out unexpectedly.
        conn.execute(
            """
            INSERT INTO workspaces (slug, name, owner_human_id, is_private)
            SELECT 'personal-' || h.id,
                   COALESCE(h.name, 'user-' || h.id) || '''s workspace',
                   h.id,
                   TRUE
            FROM humans h
            WHERE EXISTS (
                SELECT 1 FROM agent_instances ai
                WHERE ai.human_id = h.id
            )
            AND NOT EXISTS (
                SELECT 1 FROM workspace_members wm
                WHERE wm.human_id = h.id
            )
            ON CONFLICT (slug) DO NOTHING
            RETURNING workspaces.id
            """
        )
        conn.execute(
            """
            INSERT INTO workspace_members (workspace_id, human_id, role)
            SELECT w.id, w.owner_human_id, 'owner'
            FROM workspaces w
            WHERE w.owner_human_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM workspace_members wm
                  WHERE wm.workspace_id = w.id AND wm.human_id = w.owner_human_id
              )
            ON CONFLICT DO NOTHING
            RETURNING workspace_members.workspace_id
            """
        )
        conn.execute(
            """
            UPDATE agent_instances ai
            SET workspace_id = (
                SELECT workspace_id FROM workspace_members wm
                WHERE wm.human_id = ai.human_id
                ORDER BY joined_at ASC LIMIT 1
            )
            WHERE workspace_id IS NULL
            """
        )
        conn.execute(
            "ALTER TABLE agent_instances ALTER COLUMN workspace_id SET NOT NULL"
        )


def _migrate_device_auth_flows_workspace(conn) -> None:
    """Add device_auth_flows.workspace_id on DBs created before d517b90.

    CREATE TABLE IF NOT EXISTS is a no-op on existing tables, so the column
    addition in the schema never reached prod. Idempotent ADD COLUMN IF NOT
    EXISTS fixes that without touching greenfield deployments.
    """
    conn.execute(
        "ALTER TABLE IF EXISTS device_auth_flows "
        "ADD COLUMN IF NOT EXISTS workspace_id BIGINT REFERENCES workspaces(id)"
    )


def init_db() -> None:
    global _initialized_url
    url = database_url()
    with _init_lock:
        with connect() as conn:
            # Pre-migration runs FIRST so renamed columns exist before
            # executescript() tries to build indexes that reference them.
            _migrate_projects_to_workspaces(conn)
            conn.executescript(_SCHEMA_SQL)
            _migrate_device_auth_flows_workspace(conn)
            conn.execute("INSERT INTO agent_roles (name, description) VALUES (?, ?) ON CONFLICT (name) DO NOTHING",
                         ("claude", "Anthropic Claude Code"))
            conn.execute("INSERT INTO agent_roles (name, description) VALUES (?, ?) ON CONFLICT (name) DO NOTHING",
                         ("codex", "OpenAI Codex CLI"))
        _initialized_url = url


def reset_initialized_marker() -> None:
    global _initialized_url
    _initialized_url = None
