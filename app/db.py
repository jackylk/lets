from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

_default = Path(__file__).resolve().parent.parent / "lets.db"
DB_PATH = Path(os.environ.get("LETS_DB_PATH", str(_default)))


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS work_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL CHECK (type IN ('idea', 'task')),
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open', 'claimed', 'in_progress', 'done', 'rejected')),
                created_by TEXT NOT NULL DEFAULT 'human',
                claimed_by_agent_id INTEGER,
                claimed_at TEXT,
                git_branch TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                agent_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'idle'
                    CHECK (status IN ('idle', 'active', 'blocked', 'offline')),
                last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS humans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                email TEXT,
                github_id INTEGER UNIQUE,
                github_login TEXT,
                avatar_url TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                value_hash TEXT NOT NULL UNIQUE,
                human_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_used_at TEXT,
                revoked_at TEXT,
                FOREIGN KEY(human_id) REFERENCES humans(id)
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_value_hash ON sessions(value_hash);

            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                description TEXT,
                owner_human_id INTEGER,
                repo_path TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(owner_human_id) REFERENCES humans(id)
            );
            CREATE INDEX IF NOT EXISTS idx_projects_slug ON projects(slug);

            CREATE TABLE IF NOT EXISTS agent_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS agent_instances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_id INTEGER NOT NULL,
                human_id INTEGER NOT NULL,
                device_label TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'idle'
                    CHECK (status IN ('idle', 'active', 'blocked', 'offline', 'working')),
                last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(role_id, human_id, device_label),
                FOREIGN KEY(role_id) REFERENCES agent_roles(id),
                FOREIGN KEY(human_id) REFERENCES humans(id)
            );

            CREATE INDEX IF NOT EXISTS idx_agent_instances_human ON agent_instances(human_id);
            CREATE INDEX IF NOT EXISTS idx_agent_instances_role ON agent_instances(role_id);

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

            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                actor_type TEXT NOT NULL CHECK (actor_type IN ('human', 'agent', 'system')),
                actor_id INTEGER,
                target_type TEXT NOT NULL,
                target_id INTEGER,
                project_id INTEGER,
                topic_id INTEGER,
                payload TEXT NOT NULL DEFAULT '{}',
                occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_events_target ON events(target_type, target_id);
            CREATE INDEX IF NOT EXISTS idx_events_occurred_at ON events(occurred_at DESC);
            CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
            CREATE INDEX IF NOT EXISTS idx_events_topic ON events(topic_id, occurred_at DESC);

            CREATE TABLE IF NOT EXISTS status_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id INTEGER NOT NULL,
                work_item_id INTEGER,
                status TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(agent_id) REFERENCES agents(id),
                FOREIGN KEY(work_item_id) REFERENCES work_items(id)
            );

            CREATE TABLE IF NOT EXISTS findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_item_id INTEGER,
                agent_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(work_item_id) REFERENCES work_items(id),
                FOREIGN KEY(agent_id) REFERENCES agents(id)
            );

            CREATE TABLE IF NOT EXISTS human_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                work_item_id INTEGER,
                body TEXT NOT NULL,
                feedback_type TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(work_item_id) REFERENCES work_items(id)
            );

            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                project_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_topics_project ON topics(project_id);

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK (type IN (
                    'chat', 'status', 'finding', 'decision', 'question',
                    'handoff', 'review', 'artifact_revision', 'spec_change',
                    'nudge', 'proactive_finding', 'task_tree_proposal',
                    'project_proposal', 'goal_proposal', 'system'
                )),
                actor_type TEXT NOT NULL CHECK (actor_type IN ('human', 'agent', 'system')),
                actor_id INTEGER,
                body TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}',
                ref_event_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(topic_id) REFERENCES topics(id),
                FOREIGN KEY(ref_event_id) REFERENCES events(id)
            );
            CREATE INDEX IF NOT EXISTS idx_messages_topic_created ON messages(topic_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(type);

            CREATE TABLE IF NOT EXISTS artifacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL,
                type TEXT NOT NULL,
                backend TEXT NOT NULL,
                backend_ref TEXT NOT NULL,
                title TEXT NOT NULL,
                topic_id INTEGER NOT NULL,
                current_version_id INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(slug, topic_id),
                FOREIGN KEY(topic_id) REFERENCES topics(id)
            );
            CREATE INDEX IF NOT EXISTS idx_artifacts_topic ON artifacts(topic_id);
            CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(type);

            CREATE TABLE IF NOT EXISTS artifact_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artifact_id INTEGER NOT NULL,
                version_label TEXT NOT NULL,
                backend_revision_id TEXT NOT NULL,
                created_by_human_id INTEGER,
                created_by_agent_instance_id INTEGER,
                summary TEXT,
                preview_uri TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(artifact_id, version_label),
                FOREIGN KEY(artifact_id) REFERENCES artifacts(id),
                FOREIGN KEY(created_by_human_id) REFERENCES humans(id),
                FOREIGN KEY(created_by_agent_instance_id) REFERENCES agent_instances(id)
            );
            CREATE INDEX IF NOT EXISTS idx_artifact_versions_artifact ON artifact_versions(artifact_id, created_at DESC);
            """
        )

        existing_cols = {row["name"] for row in conn.execute("PRAGMA table_info(human_notes)").fetchall()}
        if "feedback_type" not in existing_cols:
            conn.execute("ALTER TABLE human_notes ADD COLUMN feedback_type TEXT")

        # Widen messages.type CHECK to include 'project_proposal' (Track C1)
        # and 'goal_proposal' (Track C1.5). SQLite cannot ALTER a CHECK; rebuild
        # the table when the constraint in sqlite_master doesn't yet list a
        # required new value.
        msg_sql = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='messages'"
        ).fetchone()
        sql_text = (msg_sql["sql"] or "") if msg_sql else ""
        if msg_sql and ("project_proposal" not in sql_text or "goal_proposal" not in sql_text):
            pre_cols = {
                r["name"] for r in conn.execute("PRAGMA table_info(messages)").fetchall()
            }
            has_addr = "addressed_to" in pre_cols
            conn.execute(
                """
                CREATE TABLE messages_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_id INTEGER NOT NULL,
                    type TEXT NOT NULL CHECK (type IN (
                        'chat', 'status', 'finding', 'decision', 'question',
                        'handoff', 'review', 'artifact_revision', 'spec_change',
                        'nudge', 'proactive_finding', 'task_tree_proposal',
                        'project_proposal', 'goal_proposal', 'system'
                    )),
                    actor_type TEXT NOT NULL CHECK (actor_type IN ('human', 'agent', 'system')),
                    actor_id INTEGER,
                    body TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    ref_event_id INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    addressed_to TEXT,
                    FOREIGN KEY(topic_id) REFERENCES topics(id),
                    FOREIGN KEY(ref_event_id) REFERENCES events(id)
                )
                """
            )
            if has_addr:
                conn.execute(
                    "INSERT INTO messages_new (id, topic_id, type, actor_type, actor_id, body, metadata, ref_event_id, created_at, addressed_to) "
                    "SELECT id, topic_id, type, actor_type, actor_id, body, metadata, ref_event_id, created_at, addressed_to FROM messages"
                )
            else:
                conn.execute(
                    "INSERT INTO messages_new (id, topic_id, type, actor_type, actor_id, body, metadata, ref_event_id, created_at) "
                    "SELECT id, topic_id, type, actor_type, actor_id, body, metadata, ref_event_id, created_at FROM messages"
                )
            conn.execute("DROP TABLE messages")
            conn.execute("ALTER TABLE messages_new RENAME TO messages")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_topic_created ON messages(topic_id, created_at DESC)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_type ON messages(type)")

        # Add project_id column to topics if missing (idempotent migration)
        topic_cols = {r["name"] for r in conn.execute("PRAGMA table_info(topics)").fetchall()}
        if "project_id" not in topic_cols:
            conn.execute("ALTER TABLE topics ADD COLUMN project_id INTEGER REFERENCES projects(id)")

        # Add addressed_to column to messages if missing (idempotent migration).
        # Stores a CSV of human IDs the message is directed at — used by
        # GET /api/attention to build the per-user inbox.
        msg_cols_for_addr = {
            r["name"] for r in conn.execute("PRAGMA table_info(messages)").fetchall()
        }
        if "addressed_to" not in msg_cols_for_addr:
            conn.execute("ALTER TABLE messages ADD COLUMN addressed_to TEXT")

        # Seed the default project (idempotent via INSERT OR IGNORE on slug UNIQUE)
        conn.execute(
            "INSERT OR IGNORE INTO projects (slug, name, description) VALUES (?, ?, ?)",
            ("default", "Default Project", "Auto-created for topics without an explicit project."),
        )

        # Backfill any topics that still have NULL project_id
        default_id_row = conn.execute("SELECT id FROM projects WHERE slug='default'").fetchone()
        if default_id_row is not None:
            conn.execute(
                "UPDATE topics SET project_id = ? WHERE project_id IS NULL",
                (default_id_row["id"],),
            )

        # Seed known agent roles (idempotent via INSERT OR IGNORE)
        conn.execute("INSERT OR IGNORE INTO agent_roles (name, description) VALUES (?, ?)",
                     ("claude", "Anthropic Claude Code"))
        conn.execute("INSERT OR IGNORE INTO agent_roles (name, description) VALUES (?, ?)",
                     ("codex", "OpenAI Codex CLI"))

        _migrate_humans_github(conn)


def _migrate_humans_github(conn) -> None:
    """Non-destructive migration: ensure humans has github_id/login/avatar_url."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(humans)").fetchall()}
    if "github_id" not in cols:
        conn.execute("ALTER TABLE humans ADD COLUMN github_id INTEGER")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_humans_github_id ON humans(github_id)"
        )
    if "github_login" not in cols:
        conn.execute("ALTER TABLE humans ADD COLUMN github_login TEXT")
    if "avatar_url" not in cols:
        conn.execute("ALTER TABLE humans ADD COLUMN avatar_url TEXT")
