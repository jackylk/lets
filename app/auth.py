from __future__ import annotations

import hashlib
import secrets
from typing import Any

from fastapi import Cookie, Header, HTTPException

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


def get_current_principal(
    authorization: str | None = Header(default=None),
) -> dict:
    """FastAPI dependency: extract Bearer token and return principal."""
    if not authorization:
        raise HTTPException(status_code=401, detail="missing or invalid token")

    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="missing or invalid token")

    principal = verify_token(parts[1].strip())
    if principal is None:
        raise HTTPException(status_code=401, detail="missing or invalid token")
    return principal


# ---------------------------------------------------------------------------
# Session cookie helpers (Track F Task 43)
#
# Sessions authenticate browser users after GitHub OAuth. They are an opaque,
# random, server-issued credential stored hashed in the ``sessions`` table.
# Distinct from agent ``tokens`` (Bearer in .mcp.json) which auth CLI agents.
# ---------------------------------------------------------------------------


def issue_session(human_id: int) -> str:
    """Mint a new opaque session value; return the plaintext (set as cookie)."""
    raw = secrets.token_urlsafe(32)
    value_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    with connect() as conn:
        conn.execute(
            "INSERT INTO sessions (value_hash, human_id) VALUES (?, ?)",
            (value_hash, human_id),
        )
    return raw


def verify_session(value: str) -> dict | None:
    """Return principal dict (human_id, name, github_login, avatar_url) or None.

    Bumps ``last_used_at`` on success. Returns None for revoked or unknown values.
    """
    if not value:
        return None
    value_hash = hashlib.sha256(value.encode("utf-8")).hexdigest()
    with connect() as conn:
        row = conn.execute(
            """
            SELECT s.id AS session_id, s.human_id, h.name, h.github_login, h.avatar_url
            FROM sessions s
            JOIN humans h ON h.id = s.human_id
            WHERE s.value_hash = ? AND s.revoked_at IS NULL
            """,
            (value_hash,),
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            "UPDATE sessions SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?",
            (row["session_id"],),
        )
        return dict(row)


def revoke_session(value: str) -> None:
    """Mark the session row revoked. No-op if value is unknown."""
    if not value:
        return
    value_hash = hashlib.sha256(value.encode("utf-8")).hexdigest()
    with connect() as conn:
        conn.execute(
            "UPDATE sessions SET revoked_at = CURRENT_TIMESTAMP WHERE value_hash = ?",
            (value_hash,),
        )


def get_session_principal(
    lets_session: str | None = Cookie(default=None, alias="lets_session"),
) -> dict:
    """FastAPI dependency: require a valid ``lets_session`` cookie."""
    if not lets_session:
        raise HTTPException(status_code=401, detail="not authenticated")
    principal = verify_session(lets_session)
    if principal is None:
        raise HTTPException(status_code=401, detail="invalid session")
    return principal
