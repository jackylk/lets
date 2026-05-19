import pytest


@pytest.fixture
def auth(client):
    from app.auth import issue_token
    from app.identity import ensure_human
    hid = ensure_human("admin")
    tok, _ = issue_token(human_id=hid, label="topics-test")
    return {"Authorization": f"Bearer {tok}"}


def test_topics_helper_create(temp_db):
    """app.topics.create_topic creates a row."""
    from app.topics import create_topic
    from app.projects import create_project
    pid = create_project(name="P")
    tid = create_topic(slug="t1", title="Topic One", project_id=pid)
    assert isinstance(tid, int)


def test_topics_helper_get_by_slug_within_project(temp_db):
    from app.topics import create_topic, get_topic_by_slug
    from app.projects import create_project
    pid = create_project(name="P")
    create_topic(slug="t1", title="T1", project_id=pid)
    t = get_topic_by_slug("t1", project_id=pid)
    assert t["title"] == "T1"


def test_topics_helper_list_by_project(temp_db):
    from app.topics import create_topic, list_topics_by_project
    from app.projects import create_project
    pid = create_project(name="P")
    create_topic(slug="t1", title="T1", project_id=pid)
    create_topic(slug="t2", title="T2", project_id=pid)
    topics = list_topics_by_project(pid)
    slugs = {t["slug"] for t in topics}
    assert {"t1", "t2"} == slugs


def test_topics_helper_slug_collision_within_project_raises(temp_db):
    import pytest
    from app.topics import create_topic
    from app.projects import create_project
    pid = create_project(name="P")
    create_topic(slug="dupe", title="A", project_id=pid)
    with pytest.raises(ValueError, match="slug already in use"):
        create_topic(slug="dupe", title="B", project_id=pid)
