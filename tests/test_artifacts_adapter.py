"""Tests for ArtifactSyncAdapter ABC + DB model helpers."""
from __future__ import annotations


def test_adapter_abc_cannot_instantiate():
    """ArtifactSyncAdapter is abstract; instantiation must fail."""
    import pytest
    from app.artifacts.adapter import ArtifactSyncAdapter
    with pytest.raises(TypeError):
        ArtifactSyncAdapter()


def test_adapter_has_required_methods():
    """The ABC declares 5 methods."""
    from app.artifacts.adapter import ArtifactSyncAdapter
    for m in ("create", "update", "read", "list_versions", "diff"):
        assert hasattr(ArtifactSyncAdapter, m), f"missing method: {m}"


def test_backend_error_is_exception():
    from app.artifacts.adapter import BackendError
    assert issubclass(BackendError, Exception)


def test_dataclasses_present():
    from app.artifacts.adapter import CreateResult, UpdateResult, VersionInfo
    c = CreateResult(backend_ref="x.txt", revision_id="abc")
    assert c.backend_ref == "x.txt"
    u = UpdateResult(revision_id="def")
    assert u.revision_id == "def"
    v = VersionInfo(revision_id="ghi", created_at="2026-01-01T00:00:00Z")
    assert v.summary is None


def test_create_artifact_row(temp_db):
    from app.artifacts.models import create_artifact_row
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('t1','T1')")
        topic_id = cursor.lastrowid
    art_id = create_artifact_row(
        slug="hello", type="text", backend="git",
        backend_ref="hello.text", title="Hello",
        topic_id=topic_id,
    )
    assert isinstance(art_id, int)


def test_record_version_creates_chain_and_updates_current(temp_db):
    from app.artifacts.models import create_artifact_row, record_version
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('t1','T1')")
        topic_id = cursor.lastrowid
    art_id = create_artifact_row(
        slug="doc", type="text", backend="git",
        backend_ref="doc.text", title="D", topic_id=topic_id,
    )
    v_id = record_version(
        artifact_id=art_id, version_label="v0",
        backend_revision_id="abc123", summary="init",
    )
    assert isinstance(v_id, int)
    with connect() as conn:
        row = conn.execute(
            "SELECT current_version_id FROM artifacts WHERE id=?", (art_id,)
        ).fetchone()
    assert row["current_version_id"] == v_id


def test_get_artifact_by_id(temp_db):
    from app.artifacts.models import create_artifact_row, get_artifact_by_id
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('t1','T1')")
        topic_id = cursor.lastrowid
    art_id = create_artifact_row(
        slug="doc", type="text", backend="git",
        backend_ref="doc.text", title="D", topic_id=topic_id,
    )
    art = get_artifact_by_id(art_id)
    assert art["slug"] == "doc"
    assert art["title"] == "D"


def test_list_versions_by_artifact_ordered(temp_db):
    from app.artifacts.models import create_artifact_row, record_version, list_versions_by_artifact
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('t1','T1')")
        topic_id = cursor.lastrowid
    art_id = create_artifact_row(
        slug="d", type="text", backend="git",
        backend_ref="d.text", title="D", topic_id=topic_id,
    )
    record_version(artifact_id=art_id, version_label="v0", backend_revision_id="aaa")
    record_version(artifact_id=art_id, version_label="v1", backend_revision_id="bbb")
    record_version(artifact_id=art_id, version_label="v2", backend_revision_id="ccc")
    versions = list_versions_by_artifact(art_id)
    labels = [v["version_label"] for v in versions]
    assert labels == ["v0", "v1", "v2"]


def test_registry_returns_git_backend(tmp_path):
    import subprocess
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    from app.artifacts.registry import get_adapter
    adapter = get_adapter("git", repo_path=str(tmp_path))
    from app.artifacts.git_backend import GitBackend
    assert isinstance(adapter, GitBackend)


def test_registry_unknown_backend_raises():
    import pytest
    from app.artifacts.registry import get_adapter
    with pytest.raises(ValueError, match="unknown backend"):
        get_adapter("nonexistent")
