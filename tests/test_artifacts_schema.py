def test_artifacts_table_exists(temp_db):
    from app.db import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='artifacts'"
        ).fetchall()
    assert len(rows) == 1


def test_artifacts_columns(temp_db):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(artifacts)").fetchall()}
    expected = {
        "id", "slug", "type", "backend", "backend_ref",
        "title", "topic_id", "current_version_id",
        "created_at", "updated_at",
    }
    assert expected.issubset(cols)


def test_artifacts_slug_unique_within_topic(temp_db):
    """Within one topic, slugs must be unique. Cross-topic dupes are allowed."""
    import sqlite3
    from app.db import connect
    with connect() as conn:
        conn.execute("INSERT INTO topics (slug, title) VALUES ('t1','T1')")
        conn.execute("INSERT INTO topics (slug, title) VALUES ('t2','T2')")
        t1 = conn.execute("SELECT id FROM topics WHERE slug='t1'").fetchone()["id"]
        t2 = conn.execute("SELECT id FROM topics WHERE slug='t2'").fetchone()["id"]
        conn.execute(
            "INSERT INTO artifacts (slug, type, backend, backend_ref, title, topic_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("q3-ppt", "pptx", "git", "ppts/q3.pptx", "Q3 PPT", t1),
        )
        # Same slug, different topic — OK
        conn.execute(
            "INSERT INTO artifacts (slug, type, backend, backend_ref, title, topic_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("q3-ppt", "pptx", "git", "ppts/q3.pptx", "Q3 PPT v2", t2),
        )
        # Same slug, same topic — IntegrityError
        try:
            conn.execute(
                "INSERT INTO artifacts (slug, type, backend, backend_ref, title, topic_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("q3-ppt", "pptx", "git", "ppts/q3.pptx", "Dupe", t1),
            )
            assert False, "should raise IntegrityError"
        except sqlite3.IntegrityError:
            pass


def test_artifact_versions_table_exists(temp_db):
    from app.db import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='artifact_versions'"
        ).fetchall()
    assert len(rows) == 1


def test_artifact_versions_columns(temp_db):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(artifact_versions)").fetchall()}
    expected = {
        "id", "artifact_id", "version_label", "backend_revision_id",
        "created_by_human_id", "created_by_agent_instance_id",
        "summary", "preview_uri", "created_at",
    }
    assert expected.issubset(cols)


def test_artifact_versions_label_unique_per_artifact(temp_db):
    """(artifact_id, version_label) must be unique."""
    import sqlite3
    from app.db import connect
    with connect() as conn:
        conn.execute("INSERT INTO topics (slug, title) VALUES ('t1','T1')")
        tid = conn.execute("SELECT id FROM topics WHERE slug='t1'").fetchone()["id"]
        conn.execute(
            "INSERT INTO artifacts (slug, type, backend, backend_ref, title, topic_id) "
            "VALUES (?,?,?,?,?,?)",
            ("a", "code", "git", "/repo", "A", tid),
        )
        aid = conn.execute("SELECT id FROM artifacts WHERE slug='a'").fetchone()["id"]
        conn.execute(
            "INSERT INTO artifact_versions (artifact_id, version_label, backend_revision_id) "
            "VALUES (?,?,?)",
            (aid, "v0", "abc123"),
        )
        try:
            conn.execute(
                "INSERT INTO artifact_versions (artifact_id, version_label, backend_revision_id) "
                "VALUES (?,?,?)",
                (aid, "v0", "def456"),
            )
            assert False, "should raise IntegrityError"
        except sqlite3.IntegrityError:
            pass


def test_attachments_tables_exist(temp_db):
    from app.db import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('attachments', 'attachment_chunks')"
        ).fetchall()
    assert {r["name"] for r in rows} == {"attachments", "attachment_chunks"}


def test_attachments_columns(temp_db):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(attachments)").fetchall()}
    expected = {
        "id", "workspace_id", "topic_id", "message_id", "uploaded_by_human_id",
        "kind", "filename", "mime_type", "byte_size", "sha256",
        "storage_backend", "storage_key", "created_at",
    }
    assert expected.issubset(cols)


def test_attachment_chunks_columns(temp_db):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(attachment_chunks)").fetchall()}
    expected = {
        "id", "attachment_id", "workspace_id", "topic_id", "chunk_index",
        "text", "metadata", "created_at",
    }
    assert expected.issubset(cols)


def test_topics_agent_context_columns(temp_db):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(topics)").fetchall()}
    assert {"agent_intervention_mode", "shared_context_mode"}.issubset(cols)
