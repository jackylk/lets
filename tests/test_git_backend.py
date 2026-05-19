import subprocess


def _init_git_repo(path):
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "--allow-empty", "-m", "init", "--quiet"], check=True)


def test_git_backend_create_writes_file_and_commits(tmp_path):
    _init_git_repo(tmp_path)
    from app.artifacts.git_backend import GitBackend
    backend = GitBackend(repo_path=str(tmp_path))
    result = backend.create(slug="hello", content=b"hello world\n", metadata={"type": "text"})
    assert "hello" in result.backend_ref
    assert len(result.revision_id) == 40
    log = subprocess.run(
        ["git", "-C", str(tmp_path), "log", "--oneline", "--", result.backend_ref],
        capture_output=True, text=True, check=True,
    )
    assert log.stdout.strip(), "no commits for the file"


def test_git_backend_update_creates_new_revision(tmp_path):
    _init_git_repo(tmp_path)
    from app.artifacts.git_backend import GitBackend
    backend = GitBackend(repo_path=str(tmp_path))
    c = backend.create(slug="doc", content=b"v0", metadata={"type": "text"})
    u = backend.update(backend_ref=c.backend_ref, content=b"v1", metadata={"summary": "updated"})
    assert u.revision_id != c.revision_id


def test_git_backend_read_current_and_specific(tmp_path):
    _init_git_repo(tmp_path)
    from app.artifacts.git_backend import GitBackend
    backend = GitBackend(repo_path=str(tmp_path))
    c = backend.create(slug="doc", content=b"v0", metadata={"type": "text"})
    backend.update(backend_ref=c.backend_ref, content=b"v1", metadata={})
    assert backend.read(backend_ref=c.backend_ref) == b"v1"
    assert backend.read(backend_ref=c.backend_ref, revision_id=c.revision_id) == b"v0"


def test_git_backend_list_versions(tmp_path):
    _init_git_repo(tmp_path)
    from app.artifacts.git_backend import GitBackend
    backend = GitBackend(repo_path=str(tmp_path))
    c = backend.create(slug="doc", content=b"v0", metadata={"type": "text", "summary": "init"})
    backend.update(backend_ref=c.backend_ref, content=b"v1", metadata={"summary": "edit one"})
    backend.update(backend_ref=c.backend_ref, content=b"v2", metadata={"summary": "edit two"})
    versions = backend.list_versions(backend_ref=c.backend_ref)
    assert len(versions) == 3
    assert versions[0].summary == "init"
    assert versions[-1].summary == "edit two"


def test_git_backend_diff(tmp_path):
    _init_git_repo(tmp_path)
    from app.artifacts.git_backend import GitBackend
    backend = GitBackend(repo_path=str(tmp_path))
    c = backend.create(slug="d", content=b"alpha\nbeta\n", metadata={"type": "text"})
    u = backend.update(backend_ref=c.backend_ref, content=b"alpha\nGAMMA\n", metadata={})
    diff = backend.diff(backend_ref=c.backend_ref, from_revision=c.revision_id, to_revision=u.revision_id)
    assert "-beta" in diff
    assert "+GAMMA" in diff


def test_git_backend_raises_on_missing_ref(tmp_path):
    _init_git_repo(tmp_path)
    import pytest
    from app.artifacts.git_backend import GitBackend
    from app.artifacts.adapter import BackendError
    backend = GitBackend(repo_path=str(tmp_path))
    with pytest.raises(BackendError):
        backend.read(backend_ref="nonexistent.txt")
