from __future__ import annotations

import hashlib
import secrets
from typing import Any

from .db import connect


TOKEN_PREFIX = "lets_"


def _hash_token(plaintext: str) -> str:
    """SHA-256 of the plaintext token. We never store the plaintext."""
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def issue_token(
    human_id: int,
    agent_instance_id: int | None = None,
    label: str | None = None,
) -> tuple[str, int]:
    """Mint a new token. Returns (plaintext, token_id)."""
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


def verify_token(plaintext: str) -> dict[str, Any] | None:
    """Return principal dict or None. Updates last_used_at on success."""
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
            "agent_instance_id": (
                int(row["agent_instance_id"])
                if row["agent_instance_id"] is not None
                else None
            ),
        }


def revoke_token(token_id: int) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE tokens SET revoked_at = CURRENT_TIMESTAMP WHERE id = ?",
            (token_id,),
        )


def list_tokens(human_id: int | None = None) -> list[dict]:
    """Return tokens without exposing value_hash."""
    sql = (
        "SELECT id, human_id, agent_instance_id, label, created_at, "
        "last_used_at, revoked_at FROM tokens"
    )
    params: list[Any] = []
    if human_id is not None:
        sql += " WHERE human_id = ?"
        params.append(human_id)
    sql += " ORDER BY created_at DESC"
    with connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(row) for row in rows]
