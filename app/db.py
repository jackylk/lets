from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DB_PATH = Path(__file__).resolve().parent.parent / "lets.db"


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
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

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
                    'nudge', 'proactive_finding', 'task_tree_proposal', 'system'
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

        # Seed known agent roles (idempotent via INSERT OR IGNORE)
        conn.execute("INSERT OR IGNORE INTO agent_roles (name, description) VALUES (?, ?)",
                     ("claude", "Anthropic Claude Code"))
        conn.execute("INSERT OR IGNORE INTO agent_roles (name, description) VALUES (?, ?)",
                     ("codex", "OpenAI Codex CLI"))
