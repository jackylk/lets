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
        "id",
        "value_hash",
        "human_id",
        "agent_instance_id",
        "label",
        "created_at",
        "last_used_at",
        "revoked_at",
    }

    assert expected.issubset(cols)


def test_tokens_value_hash_unique(temp_db):
    import sqlite3

    from app.db import connect

    with connect() as conn:
        conn.execute("INSERT INTO humans (name) VALUES ('Neo')")
        human_id = conn.execute("SELECT id FROM humans WHERE name='Neo'").fetchone()["id"]
        conn.execute(
            "INSERT INTO tokens (value_hash, human_id) VALUES (?, ?)",
            ("hash_abc", human_id),
        )
        try:
            conn.execute(
                "INSERT INTO tokens (value_hash, human_id) VALUES (?, ?)",
                ("hash_abc", human_id),
            )
            assert False, "should raise IntegrityError"
        except sqlite3.IntegrityError:
            pass


def test_issue_token_returns_plaintext_and_id(temp_db):
    from app.auth import issue_token
    from app.identity import ensure_human

    human_id = ensure_human("Neo")
    token, token_id = issue_token(human_id=human_id, label="neo-mbp-claude")

    assert token.startswith("lets_")
    assert len(token) >= 32
    assert isinstance(token_id, int)


def test_verify_token_returns_principal(temp_db):
    from app.auth import issue_token, verify_token
    from app.identity import ensure_human

    human_id = ensure_human("Neo")
    token, _ = issue_token(human_id=human_id)
    principal = verify_token(token)

    assert principal is not None
    assert principal["human_id"] == human_id
    assert principal["agent_instance_id"] is None


def test_verify_token_with_agent_instance(temp_db):
    from app.auth import issue_token, verify_token
    from app.identity import ensure_agent_instance, ensure_human

    human_id = ensure_human("Neo")
    agent_instance_id = ensure_agent_instance(
        role="claude",
        human_id=human_id,
        device_label="neo-mbp",
    )
    token, _ = issue_token(human_id=human_id, agent_instance_id=agent_instance_id)
    principal = verify_token(token)

    assert principal["agent_instance_id"] == agent_instance_id


def test_verify_token_rejects_unknown(temp_db):
    from app.auth import verify_token

    assert verify_token("lets_nonexistent_token") is None


def test_verify_token_rejects_revoked(temp_db):
    from app.auth import issue_token, revoke_token, verify_token
    from app.identity import ensure_human

    human_id = ensure_human("Neo")
    token, token_id = issue_token(human_id=human_id)
    revoke_token(token_id)

    assert verify_token(token) is None


def test_verify_token_updates_last_used_at(temp_db):
    from app.auth import issue_token, verify_token
    from app.db import connect
    from app.identity import ensure_human

    human_id = ensure_human("Neo")
    token, token_id = issue_token(human_id=human_id)
    with connect() as conn:
        before = conn.execute(
            "SELECT last_used_at FROM tokens WHERE id=?",
            (token_id,),
        ).fetchone()["last_used_at"]
    assert before is None

    verify_token(token)

    with connect() as conn:
        after = conn.execute(
            "SELECT last_used_at FROM tokens WHERE id=?",
            (token_id,),
        ).fetchone()["last_used_at"]
    assert after is not None
