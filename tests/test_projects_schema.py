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


def test_create_project(temp_db):
    from app.projects import create_project
    pid = create_project(name="My Project", description="hello")
    assert isinstance(pid, int)


def test_create_project_slug_derived(temp_db):
    from app.projects import create_project, get_project_by_id
    pid = create_project(name="Hello World!")
    p = get_project_by_id(pid)
    assert p["slug"] == "hello-world"


def test_create_project_explicit_slug(temp_db):
    from app.projects import create_project, get_project_by_id
    pid = create_project(name="Hello", slug="my-slug")
    p = get_project_by_id(pid)
    assert p["slug"] == "my-slug"


def test_create_project_slug_collision_raises(temp_db):
    import pytest
    from app.projects import create_project
    create_project(name="A", slug="dupe")
    with pytest.raises(ValueError, match="slug already in use"):
        create_project(name="B", slug="dupe")


def test_get_project_by_slug(temp_db):
    from app.projects import create_project, get_project_by_slug
    create_project(name="My Project", slug="my-proj")
    p = get_project_by_slug("my-proj")
    assert p["name"] == "My Project"


def test_list_projects(temp_db):
    from app.projects import create_project, list_projects
    # default project already exists from init_db
    create_project(name="Alpha")
    create_project(name="Beta")
    projects = list_projects()
    slugs = {p["slug"] for p in projects}
    assert {"default", "alpha", "beta"}.issubset(slugs)


def test_update_project_repo_path(temp_db):
    from app.projects import create_project, get_project_by_id, update_project_repo_path
    pid = create_project(name="P")
    update_project_repo_path(pid, "/tmp/some-repo")
    p = get_project_by_id(pid)
    assert p["repo_path"] == "/tmp/some-repo"
