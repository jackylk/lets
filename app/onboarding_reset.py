from __future__ import annotations

import os
from pathlib import Path

import psycopg
from psycopg import sql

from .db import database_url


RESET_TABLES = (
    "drift_nudges",
    "task_items",
    "task_trees",
    "artifact_versions",
    "artifacts",
    "messages",
    "topics",
    "human_notes",
    "findings",
    "status_updates",
    "events",
    "device_auth_flows",
    "tokens",
    "agent_instances",
    "workspace_invites",
    "workspace_members",
    "workspaces",
    "sessions",
    "humans",
    "agents",
    "work_items",
    "agent_roles",
)


def _marker_path() -> Path:
    marker = os.environ.get("LETS_ONBOARDING_RESET_MARKER")
    if marker:
        return Path(marker)
    repo = Path(os.environ.get("LETS_GIT_REPO", "/data/lets-artifacts"))
    return repo.parent / ".lets-onboarding-reset.done"


def reset_once() -> None:
    run_id = os.environ.get("LETS_ONBOARDING_RESET_ONCE")
    if not run_id:
        return

    marker = _marker_path()
    if marker.exists() and marker.read_text(encoding="utf-8").strip() == run_id:
        print(f"onboarding reset already applied: {run_id}", flush=True)
        return

    with psycopg.connect(database_url(), autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                  AND table_name = ANY(%s)
                """,
                (list(RESET_TABLES),),
            )
            existing = [row[0] for row in cur.fetchall()]
            if existing:
                cur.execute(
                    sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(
                        sql.SQL(", ").join(sql.Identifier(name) for name in existing)
                    )
                )
            if "agent_roles" in existing:
                cur.execute(
                    """
                    INSERT INTO agent_roles (name, description)
                    VALUES ('claude', 'Anthropic Claude Code')
                    ON CONFLICT (name) DO NOTHING
                    """
                )
                cur.execute(
                    """
                    INSERT INTO agent_roles (name, description)
                    VALUES ('codex', 'OpenAI Codex CLI')
                    ON CONFLICT (name) DO NOTHING
                    """
                )
        conn.commit()

    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(run_id + "\n", encoding="utf-8")
    print(f"onboarding reset applied: {run_id}", flush=True)


if __name__ == "__main__":
    reset_once()
