"""Artifact + ArtifactVersion DB helpers."""
from __future__ import annotations

from typing import Optional

from ..db import connect


def create_artifact_row(
    slug: str, type: str, backend: str, backend_ref: str,
    title: str, topic_id: int,
) -> int:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO artifacts (slug, type, backend, backend_ref, title, topic_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (slug, type, backend, backend_ref, title, topic_id),
        )
        return int(cursor.lastrowid)


def record_version(
    artifact_id: int,
    version_label: str,
    backend_revision_id: str,
    *,
    summary: Optional[str] = None,
    preview_uri: Optional[str] = None,
    created_by_human_id: Optional[int] = None,
    created_by_agent_instance_id: Optional[int] = None,
) -> int:
    with connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO artifact_versions
                (artifact_id, version_label, backend_revision_id, summary, preview_uri,
                 created_by_human_id, created_by_agent_instance_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (artifact_id, version_label, backend_revision_id, summary, preview_uri,
             created_by_human_id, created_by_agent_instance_id),
        )
        v_id = int(cursor.lastrowid)
        conn.execute(
            "UPDATE artifacts SET current_version_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (v_id, artifact_id),
        )
        return v_id


def get_artifact_by_id(artifact_id: int) -> Optional[dict]:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM artifacts WHERE id = ?", (artifact_id,)
        ).fetchone()
    return dict(row) if row else None


def list_versions_by_artifact(artifact_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT * FROM artifact_versions
            WHERE artifact_id = ?
            ORDER BY created_at ASC, id ASC
            """,
            (artifact_id,),
        ).fetchall()
    return [dict(r) for r in rows]
