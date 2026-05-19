def test_projects_table_exists(temp_db):
    from app.db import connect
    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"
        ).fetchall()
    assert len(rows) == 1


def test_projects_columns(temp_db):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(projects)").fetchall()}
    expected = {
        "id", "slug", "name", "description", "owner_human_id",
        "repo_path", "created_at", "updated_at",
    }
    assert expected.issubset(cols)


def test_projects_slug_unique(temp_db):
    import sqlite3
    from app.db import connect
    with connect() as conn:
        conn.execute("INSERT INTO projects (slug, name) VALUES ('p1', 'P1')")
        try:
            conn.execute("INSERT INTO projects (slug, name) VALUES ('p1', 'Dupe')")
            assert False, "should raise IntegrityError"
        except sqlite3.IntegrityError:
            pass


def test_topics_has_project_id_column(temp_db):
    from app.db import connect
    with connect() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(topics)").fetchall()}
    assert "project_id" in cols


def test_default_project_auto_created(temp_db):
    """init_db should seed a 'default' project so pre-existing topics have a home."""
    from app.db import connect
    with connect() as conn:
        row = conn.execute("SELECT id, name FROM projects WHERE slug='default'").fetchone()
    assert row is not None
    assert row["name"] == "Default Project"


def test_existing_topics_migrated_to_default_project(temp_db):
    """If a topic exists without project_id, init_db should assign it to default."""
    from app.db import connect
    # Pre-create a topic without project_id (simulating pre-migration state)
    with connect() as conn:
        conn.execute(
            "INSERT INTO topics (slug, title, project_id) VALUES ('orphan', 'Orphan', NULL)"
        )
    # Re-run init_db — should backfill
    from app.db import init_db
    init_db()
    with connect() as conn:
        row = conn.execute("SELECT project_id FROM topics WHERE slug='orphan'").fetchone()
        default_id = conn.execute("SELECT id FROM projects WHERE slug='default'").fetchone()["id"]
    assert row["project_id"] is not None
    assert row["project_id"] == default_id
