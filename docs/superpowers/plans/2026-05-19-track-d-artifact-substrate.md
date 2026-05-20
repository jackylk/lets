# Track D: Artifact Substrate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce an `Artifact` entity + version chain + a pluggable `ArtifactSyncAdapter` interface, and ship the first backend (Git). Lets stops treating "the thing agents produce" as ad-hoc strings inside messages — every artifact has a stable identity, semantic version chain, and a backend that knows how to read / write / diff / list versions.

**Architecture:** Two new tables (`artifacts`, `artifact_versions`). A Python ABC `ArtifactSyncAdapter` with 5 methods (`create / update / read / list_versions / diff`). The first concrete adapter `GitBackend` writes files into a dedicated git repo per artifact (or a shared "lets-artifacts" repo for v1.5b — see Open Questions). HTTP endpoints to create / read / update / list versions / diff. Tests use a temp git repo fixture.

**Tech Stack:** Python 3.13 · FastAPI · SQLite · stdlib subprocess for git operations · pytest · pytest fixtures for temp git repos

**Prerequisite:** Track A complete (humans / agent_instances / topics exist). This track is independent of Track B; they can run in parallel on separate branches.

---

## File Structure

**Created:**
- `app/artifacts/__init__.py` — package marker
- `app/artifacts/models.py` — Artifact / ArtifactVersion dataclasses + helper queries
- `app/artifacts/adapter.py` — `ArtifactSyncAdapter` ABC + `BackendError` exception
- `app/artifacts/git_backend.py` — `GitBackend` concrete adapter
- `app/artifacts/registry.py` — `get_adapter(backend_name) -> ArtifactSyncAdapter`
- `tests/test_artifacts_schema.py` — schema tests
- `tests/test_artifacts_adapter.py` — ABC contract tests
- `tests/test_git_backend.py` — GitBackend integration tests against a tmp git repo
- `tests/test_artifacts_api.py` — HTTP endpoint tests
- `tests/test_artifacts_e2e.py` — create → update → list versions → diff end-to-end

**Modified:**
- `app/db.py` — add `artifacts` + `artifact_versions` tables
- `app/main.py` — add 5 endpoints under `/api/artifacts`
- `README.md` — add Track D section

**Read-only references:**
- `docs/artifact-sync-strategy.md` — backend dispatch + Adapter contract
- `docs/agent-spec-collaboration.md` — Git as backend for spec + code

---

## Conventions

- TDD: failing test first, run to confirm, implement, run pass, commit
- Each artifact has a `slug` derived from a normalized title (`q3-review-ppt`); slug is unique within a project
- Backend-specific reference (`backend_ref`) is opaque to the rest of Lets — only the adapter knows how to interpret it
- Version chain has `(artifact_id, version_label)` UNIQUE; version_label can be anything (`v0`, `v1.2`, `final`, ...)
- Git commits made by the backend use author `Lets Backend <bot@lets.local>`
- All git subprocess calls use `check=True` and capture stderr for error reporting
- Tests use the `tmp_path` pytest fixture for git working trees; no global git state mutation

---

## Task 1: Add `artifacts` table

**Files:** `app/db.py` (modify), `tests/test_artifacts_schema.py` (create)

- [ ] **Step 1.1: Write failing tests**

Create `tests/test_artifacts_schema.py`:
```python
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
```

- [ ] **Step 1.2: Run — expect 3 FAIL**

```bash
.venv/bin/pytest tests/test_artifacts_schema.py -v
```

- [ ] **Step 1.3: Add table to `app/db.py` executescript**

Place after `messages` (`artifacts.topic_id REFERENCES topics(id)`, `current_version_id` is a forward-ref to a not-yet-created table — SQLite is lenient about that):

```sql
CREATE TABLE IF NOT EXISTS artifacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL,
    type TEXT NOT NULL,
    backend TEXT NOT NULL,
    backend_ref TEXT NOT NULL,
    title TEXT NOT NULL,
    topic_id INTEGER NOT NULL,
    current_version_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(slug, topic_id),
    FOREIGN KEY(topic_id) REFERENCES topics(id)
);
CREATE INDEX IF NOT EXISTS idx_artifacts_topic ON artifacts(topic_id);
CREATE INDEX IF NOT EXISTS idx_artifacts_type ON artifacts(type);
```

- [ ] **Step 1.4: Run — expect 3 passed**

```bash
.venv/bin/pytest tests/test_artifacts_schema.py -v
```

- [ ] **Step 1.5: Commit**

```bash
git add app/db.py tests/test_artifacts_schema.py
git commit -m "feat(schema): add artifacts table with (slug, topic_id) uniqueness"
```

---

## Task 2: Add `artifact_versions` table

**Files:** `app/db.py` (modify), `tests/test_artifacts_schema.py` (append)

- [ ] **Step 2.1: Append failing tests**

Append to `tests/test_artifacts_schema.py`:
```python
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
```

- [ ] **Step 2.2: Run — expect 3 FAIL**

- [ ] **Step 2.3: Add table**

Append to `executescript` after `artifacts`:
```sql
CREATE TABLE IF NOT EXISTS artifact_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id INTEGER NOT NULL,
    version_label TEXT NOT NULL,
    backend_revision_id TEXT NOT NULL,
    created_by_human_id INTEGER,
    created_by_agent_instance_id INTEGER,
    summary TEXT,
    preview_uri TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(artifact_id, version_label),
    FOREIGN KEY(artifact_id) REFERENCES artifacts(id),
    FOREIGN KEY(created_by_human_id) REFERENCES humans(id),
    FOREIGN KEY(created_by_agent_instance_id) REFERENCES agent_instances(id)
);
CREATE INDEX IF NOT EXISTS idx_artifact_versions_artifact ON artifact_versions(artifact_id, created_at DESC);
```

- [ ] **Step 2.4: Run — 6 passed**

- [ ] **Step 2.5: Commit**

```bash
git add app/db.py tests/test_artifacts_schema.py
git commit -m "feat(schema): add artifact_versions table with (artifact_id, version_label) uniqueness"
```

---

## Task 3: `ArtifactSyncAdapter` ABC

**Files:** `app/artifacts/__init__.py` (create empty), `app/artifacts/adapter.py` (create), `tests/test_artifacts_adapter.py` (create)

- [ ] **Step 3.1: Create package marker**

Create `app/artifacts/__init__.py` (empty).

- [ ] **Step 3.2: Write failing tests**

Create `tests/test_artifacts_adapter.py`:
```python
def test_adapter_abc_cannot_instantiate():
    """ArtifactSyncAdapter is abstract; instantiation must fail."""
    from app.artifacts.adapter import ArtifactSyncAdapter
    import pytest
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
```

- [ ] **Step 3.3: Run — expect FAIL**

```bash
.venv/bin/pytest tests/test_artifacts_adapter.py -v
```

- [ ] **Step 3.4: Implement ABC**

Create `app/artifacts/adapter.py`:
```python
"""Artifact sync adapter contract.

All concrete backends (GitBackend, GoogleSlidesBackend, etc.) implement
`ArtifactSyncAdapter`. Lets core code interacts only with this interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


class BackendError(Exception):
    """Raised by adapters on backend-side failures (git error, API error, ...)."""


@dataclass
class CreateResult:
    backend_ref: str  # opaque, backend-specific (e.g. file path for git, presentationId for google)
    revision_id: str  # opaque (commit sha for git)


@dataclass
class UpdateResult:
    revision_id: str  # new revision after the update


@dataclass
class VersionInfo:
    revision_id: str
    created_at: str  # ISO timestamp from backend
    summary: Optional[str] = None  # human-readable, backend-derived (commit message for git)


class ArtifactSyncAdapter(ABC):
    """All five operations operate on an opaque backend_ref."""

    @abstractmethod
    def create(self, *, slug: str, content: bytes, metadata: dict[str, Any]) -> CreateResult:
        """Materialize a new artifact in the backend. Return (backend_ref, initial revision_id)."""

    @abstractmethod
    def update(self, *, backend_ref: str, content: bytes, metadata: dict[str, Any]) -> UpdateResult:
        """Apply an update; return the new revision_id."""

    @abstractmethod
    def read(self, *, backend_ref: str, revision_id: Optional[str] = None) -> bytes:
        """Read the artifact's content. If revision_id is None, return current."""

    @abstractmethod
    def list_versions(self, *, backend_ref: str) -> list[VersionInfo]:
        """Return all revisions in chronological order (oldest → newest)."""

    @abstractmethod
    def diff(self, *, backend_ref: str, from_revision: str, to_revision: str) -> str:
        """Return a unified textual diff between two revisions."""
```

- [ ] **Step 3.5: Run — 3 passed**

- [ ] **Step 3.6: Commit**

```bash
git add app/artifacts/ tests/test_artifacts_adapter.py
git commit -m "feat(artifacts): ArtifactSyncAdapter ABC + BackendError"
```

---

## Task 4: GitBackend — implementation

**Files:** `app/artifacts/git_backend.py` (create), `tests/test_git_backend.py` (create)

- [ ] **Step 4.1: Write failing tests**

Create `tests/test_git_backend.py`:
```python
import subprocess


def _init_git_repo(path):
    subprocess.run(["git", "init", "--quiet", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "t@t"], check=True)
    # Initial empty commit so HEAD exists
    subprocess.run(["git", "-C", str(path), "commit", "--allow-empty", "-m", "init", "--quiet"], check=True)


def test_git_backend_create_writes_file_and_commits(tmp_path):
    _init_git_repo(tmp_path)
    from app.artifacts.git_backend import GitBackend
    backend = GitBackend(repo_path=str(tmp_path))
    result = backend.create(slug="hello", content=b"hello world\n", metadata={"type": "text"})
    assert result.backend_ref.endswith("hello.text") or "hello" in result.backend_ref
    assert len(result.revision_id) == 40  # full SHA
    # Verify the file is committed
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
    u = backend.update(backend_ref=c.backend_ref, content=b"v1", metadata={})
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
    # chronological asc
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
    from app.artifacts.git_backend import GitBackend
    from app.artifacts.adapter import BackendError
    backend = GitBackend(repo_path=str(tmp_path))
    import pytest
    with pytest.raises(BackendError):
        backend.read(backend_ref="nonexistent.txt")
```

- [ ] **Step 4.2: Run — expect 6 FAIL (import error)**

- [ ] **Step 4.3: Implement GitBackend**

Create `app/artifacts/git_backend.py`:
```python
"""Git-backed artifact storage.

Each artifact maps to one file in a git repo. `backend_ref` is the file path
(relative to the repo root). Revisions are git commit SHAs that touch the file.

The backend runs git as a subprocess. The repo is assumed to exist and be
initialized; callers (Lets backend setup) ensure that.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Optional

from .adapter import ArtifactSyncAdapter, BackendError, CreateResult, UpdateResult, VersionInfo


_SLUG_RE = re.compile(r"[^a-zA-Z0-9_\-]+")


def _safe_filename(slug: str, type_hint: str) -> str:
    """slug 'Q3 review!' + 'pptx' → 'q3-review-.pptx'.
    For text type, extension is 'text' so we don't pretend it's a .txt.
    """
    clean = _SLUG_RE.sub("-", slug.strip()).strip("-").lower()
    ext = type_hint if type_hint else "bin"
    return f"{clean}.{ext}"


def _run_git(repo_path: str, *args: str, input_bytes: Optional[bytes] = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", "-C", repo_path, *args],
            check=True,
            capture_output=True,
            input=input_bytes,
        )
    except subprocess.CalledProcessError as e:
        raise BackendError(
            f"git {' '.join(args)} failed (exit {e.returncode}): {e.stderr.decode('utf-8', 'replace').strip()}"
        ) from e


class GitBackend(ArtifactSyncAdapter):
    """One repo can host many artifacts; each artifact is a distinct file."""

    def __init__(self, repo_path: str) -> None:
        self.repo_path = repo_path
        if not Path(repo_path, ".git").exists():
            raise BackendError(f"not a git repo: {repo_path}")

    # --- helpers ---

    def _commit_file(self, rel_path: str, content: bytes, summary: str) -> str:
        full = Path(self.repo_path) / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(content)
        _run_git(self.repo_path, "add", rel_path)
        # Allow empty in case content is unchanged
        _run_git(
            self.repo_path,
            "-c", "user.name=Lets Backend",
            "-c", "user.email=bot@lets.local",
            "commit", "--allow-empty", "-m", summary,
        )
        sha = _run_git(self.repo_path, "rev-parse", "HEAD").stdout.decode().strip()
        return sha

    # --- ABC implementation ---

    def create(self, *, slug: str, content: bytes, metadata: dict[str, Any]) -> CreateResult:
        type_hint = metadata.get("type", "bin")
        rel_path = _safe_filename(slug, type_hint)
        if (Path(self.repo_path) / rel_path).exists():
            raise BackendError(f"file already exists: {rel_path}")
        summary = metadata.get("summary", f"create {slug}")
        sha = self._commit_file(rel_path, content, summary)
        return CreateResult(backend_ref=rel_path, revision_id=sha)

    def update(self, *, backend_ref: str, content: bytes, metadata: dict[str, Any]) -> UpdateResult:
        full = Path(self.repo_path) / backend_ref
        if not full.exists():
            raise BackendError(f"file not found: {backend_ref}")
        summary = metadata.get("summary", f"update {backend_ref}")
        sha = self._commit_file(backend_ref, content, summary)
        return UpdateResult(revision_id=sha)

    def read(self, *, backend_ref: str, revision_id: Optional[str] = None) -> bytes:
        if revision_id is None:
            full = Path(self.repo_path) / backend_ref
            if not full.exists():
                raise BackendError(f"file not found: {backend_ref}")
            return full.read_bytes()
        # `git show <rev>:<path>`
        result = _run_git(self.repo_path, "show", f"{revision_id}:{backend_ref}")
        return result.stdout

    def list_versions(self, *, backend_ref: str) -> list[VersionInfo]:
        # `git log --format=%H%x00%aI%x00%s --reverse -- <path>`
        result = _run_git(
            self.repo_path, "log",
            "--format=%H%x00%aI%x00%s", "--reverse", "--", backend_ref,
        )
        out = result.stdout.decode("utf-8", "replace").strip()
        if not out:
            raise BackendError(f"no history for {backend_ref}")
        versions: list[VersionInfo] = []
        for line in out.splitlines():
            sha, iso, subject = line.split("\x00", 2)
            versions.append(VersionInfo(revision_id=sha, created_at=iso, summary=subject))
        return versions

    def diff(self, *, backend_ref: str, from_revision: str, to_revision: str) -> str:
        result = _run_git(
            self.repo_path, "diff", from_revision, to_revision, "--", backend_ref,
        )
        return result.stdout.decode("utf-8", "replace")
```

- [ ] **Step 4.4: Run — 6 passed**

```bash
.venv/bin/pytest tests/test_git_backend.py -v
```

- [ ] **Step 4.5: Commit**

```bash
git add app/artifacts/git_backend.py tests/test_git_backend.py
git commit -m "feat(artifacts): GitBackend implementation with 5 ABC methods"
```

---

## Task 5: Backend registry

**Files:** `app/artifacts/registry.py` (create), `tests/test_artifacts_adapter.py` (append)

- [ ] **Step 5.1: Append failing test**

Append to `tests/test_artifacts_adapter.py`:
```python
def test_registry_returns_git_backend(tmp_path):
    import subprocess
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    from app.artifacts.registry import get_adapter
    adapter = get_adapter("git", repo_path=str(tmp_path))
    from app.artifacts.git_backend import GitBackend
    assert isinstance(adapter, GitBackend)


def test_registry_unknown_backend_raises():
    from app.artifacts.registry import get_adapter
    import pytest
    with pytest.raises(ValueError, match="unknown backend"):
        get_adapter("nonexistent")
```

- [ ] **Step 5.2: Run — expect FAIL**

- [ ] **Step 5.3: Implement registry**

Create `app/artifacts/registry.py`:
```python
"""Backend registry. As more backends land (google-slides, object-storage, ...),
register them here."""
from __future__ import annotations

from typing import Any

from .adapter import ArtifactSyncAdapter
from .git_backend import GitBackend


def get_adapter(backend: str, **kwargs: Any) -> ArtifactSyncAdapter:
    """Factory. kwargs are backend-specific configuration."""
    if backend == "git":
        repo_path = kwargs.get("repo_path")
        if not repo_path:
            raise ValueError("git backend requires repo_path")
        return GitBackend(repo_path=repo_path)
    raise ValueError(f"unknown backend: {backend}")
```

- [ ] **Step 5.4: Run — 5 passed in test_artifacts_adapter.py**

- [ ] **Step 5.5: Commit**

```bash
git add app/artifacts/registry.py tests/test_artifacts_adapter.py
git commit -m "feat(artifacts): backend registry with git adapter"
```

---

## Task 6: Models helpers — `app/artifacts/models.py`

**Files:** `app/artifacts/models.py` (create), `tests/test_artifacts_adapter.py` (append)

DB helpers for creating / loading artifacts and version chain.

- [ ] **Step 6.1: Append failing tests**

Append to `tests/test_artifacts_adapter.py`:
```python
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
    # current_version_id should now point at v_id
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
```

- [ ] **Step 6.2: Run — expect FAIL**

- [ ] **Step 6.3: Implement models**

Create `app/artifacts/models.py`:
```python
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
```

- [ ] **Step 6.4: Run — 8 passed in test_artifacts_adapter.py**

- [ ] **Step 6.5: Commit**

```bash
git add app/artifacts/models.py tests/test_artifacts_adapter.py
git commit -m "feat(artifacts): DB helpers for artifacts + version chain"
```

---

## Task 7: `POST /api/artifacts` endpoint

**Files:** `app/main.py` (modify), `tests/test_artifacts_api.py` (create)

The endpoint creates an artifact: writes content via the backend, records the row + initial version `v0`, returns the artifact + version dict.

For v1.5b the GitBackend repo path comes from an env var `LETS_GIT_REPO` (default: `<cwd>/lets-artifacts`). The implementer should ensure the repo exists with at least one commit before serving requests; we add this in `app/main.py`'s startup.

- [ ] **Step 7.1: Write failing test**

Create `tests/test_artifacts_api.py`:
```python
import os
import subprocess
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def git_artifacts_repo(monkeypatch):
    """Create a tmp git repo and point LETS_GIT_REPO at it."""
    tmp = tempfile.mkdtemp(prefix="lets-artifacts-")
    subprocess.run(["git", "init", "--quiet", tmp], check=True)
    subprocess.run(["git", "-C", tmp, "config", "user.name", "T"], check=True)
    subprocess.run(["git", "-C", tmp, "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", tmp, "commit", "--allow-empty", "-m", "init", "--quiet"], check=True)
    monkeypatch.setenv("LETS_GIT_REPO", tmp)
    yield tmp
    # cleanup
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


def test_post_artifact_creates_row_and_version(client, git_artifacts_repo):
    # Need a topic to attach to
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('t1','T1')")
        topic_id = cursor.lastrowid

    r = client.post(
        "/api/artifacts",
        json={
            "slug": "hello",
            "type": "text",
            "backend": "git",
            "title": "Hello doc",
            "topic_id": topic_id,
            "content_b64": "aGVsbG8gd29ybGQK",  # "hello world\n" base64
            "summary": "first draft",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["artifact"]["slug"] == "hello"
    assert data["version"]["version_label"] == "v0"
    assert data["version"]["backend_revision_id"]
```

- [ ] **Step 7.2: Run — expect FAIL (404 or error)**

- [ ] **Step 7.3: Add endpoint to main.py**

In `app/main.py` add at top of imports:
```python
import base64
import os
```

Add the model near other Pydantic models:
```python
class ArtifactCreate(BaseModel):
    slug: str = Field(min_length=1)
    type: str = Field(min_length=1)
    backend: str = Field(default="git")
    title: str = Field(min_length=1)
    topic_id: int
    content_b64: str
    summary: str | None = None
```

Add endpoint:
```python
@app.post("/api/artifacts")
def post_artifact(payload: ArtifactCreate) -> dict:
    from .artifacts.registry import get_adapter
    from .artifacts.models import create_artifact_row, record_version, get_artifact_by_id

    if payload.backend != "git":
        raise HTTPException(status_code=400, detail="only 'git' backend supported in v1.5b")

    repo_path = os.environ.get("LETS_GIT_REPO")
    if not repo_path:
        raise HTTPException(status_code=500, detail="LETS_GIT_REPO not configured")

    adapter = get_adapter("git", repo_path=repo_path)
    content = base64.b64decode(payload.content_b64)
    try:
        result = adapter.create(
            slug=payload.slug, content=content,
            metadata={"type": payload.type, "summary": payload.summary or f"create {payload.slug}"},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"backend error: {e}")

    art_id = create_artifact_row(
        slug=payload.slug, type=payload.type, backend=payload.backend,
        backend_ref=result.backend_ref, title=payload.title, topic_id=payload.topic_id,
    )
    v_id = record_version(
        artifact_id=art_id, version_label="v0",
        backend_revision_id=result.revision_id, summary=payload.summary,
    )

    return {
        "artifact": get_artifact_by_id(art_id),
        "version": {
            "id": v_id, "version_label": "v0",
            "backend_revision_id": result.revision_id,
        },
    }
```

- [ ] **Step 7.4: Run — test passes**

```bash
.venv/bin/pytest tests/test_artifacts_api.py -v
```

- [ ] **Step 7.5: Commit**

```bash
git add app/main.py tests/test_artifacts_api.py
git commit -m "feat(artifacts): POST /api/artifacts endpoint (Git backend, v0 initial version)"
```

---

## Task 8: `POST /api/artifacts/{id}/update` endpoint

**Files:** `app/main.py` (modify), `tests/test_artifacts_api.py` (append)

- [ ] **Step 8.1: Append failing test**

Append to `tests/test_artifacts_api.py`:
```python
def test_update_artifact_creates_new_version(client, git_artifacts_repo):
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('tu','TU')")
        topic_id = cursor.lastrowid

    create = client.post("/api/artifacts", json={
        "slug": "u", "type": "text", "backend": "git", "title": "U",
        "topic_id": topic_id, "content_b64": "djA=",  # 'v0'
        "summary": "init",
    }).json()
    aid = create["artifact"]["id"]

    upd = client.post(f"/api/artifacts/{aid}/update", json={
        "content_b64": "djE=",  # 'v1'
        "summary": "second pass",
        "version_label": "v1",
    })
    assert upd.status_code == 200
    data = upd.json()
    assert data["version"]["version_label"] == "v1"
    assert data["version"]["backend_revision_id"] != create["version"]["backend_revision_id"]
```

- [ ] **Step 8.2: Run — FAIL**

- [ ] **Step 8.3: Add endpoint**

```python
class ArtifactUpdate(BaseModel):
    content_b64: str
    summary: str | None = None
    version_label: str  # caller decides; must be unique per artifact


@app.post("/api/artifacts/{artifact_id}/update")
def update_artifact(artifact_id: int, payload: ArtifactUpdate) -> dict:
    from .artifacts.registry import get_adapter
    from .artifacts.models import record_version, get_artifact_by_id

    art = get_artifact_by_id(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="artifact not found")
    if art["backend"] != "git":
        raise HTTPException(status_code=400, detail="only 'git' backend supported in v1.5b")

    repo_path = os.environ.get("LETS_GIT_REPO")
    if not repo_path:
        raise HTTPException(status_code=500, detail="LETS_GIT_REPO not configured")

    adapter = get_adapter("git", repo_path=repo_path)
    content = base64.b64decode(payload.content_b64)
    try:
        result = adapter.update(
            backend_ref=art["backend_ref"], content=content,
            metadata={"summary": payload.summary or f"update {art['slug']}"},
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"backend error: {e}")

    v_id = record_version(
        artifact_id=artifact_id, version_label=payload.version_label,
        backend_revision_id=result.revision_id, summary=payload.summary,
    )
    return {
        "version": {
            "id": v_id, "version_label": payload.version_label,
            "backend_revision_id": result.revision_id,
        },
    }
```

- [ ] **Step 8.4: Run — test passes**

- [ ] **Step 8.5: Commit**

```bash
git add app/main.py tests/test_artifacts_api.py
git commit -m "feat(artifacts): POST /api/artifacts/{id}/update endpoint"
```

---

## Task 9: `GET /api/artifacts/{id}/versions` endpoint

**Files:** `app/main.py` (modify), `tests/test_artifacts_api.py` (append)

- [ ] **Step 9.1: Append test**

Append to `tests/test_artifacts_api.py`:
```python
def test_list_artifact_versions(client, git_artifacts_repo):
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('tl','TL')")
        topic_id = cursor.lastrowid

    c = client.post("/api/artifacts", json={
        "slug": "lv", "type": "text", "backend": "git", "title": "LV",
        "topic_id": topic_id, "content_b64": "djA=", "summary": "init",
    }).json()
    aid = c["artifact"]["id"]
    client.post(f"/api/artifacts/{aid}/update", json={
        "content_b64": "djE=", "summary": "two", "version_label": "v1",
    })
    client.post(f"/api/artifacts/{aid}/update", json={
        "content_b64": "djI=", "summary": "three", "version_label": "v2",
    })

    r = client.get(f"/api/artifacts/{aid}/versions")
    assert r.status_code == 200
    versions = r.json()
    labels = [v["version_label"] for v in versions]
    assert labels == ["v0", "v1", "v2"]
```

- [ ] **Step 9.2: Run — FAIL**

- [ ] **Step 9.3: Add endpoint**

```python
@app.get("/api/artifacts/{artifact_id}/versions")
def list_artifact_versions(artifact_id: int) -> list[dict]:
    from .artifacts.models import get_artifact_by_id, list_versions_by_artifact
    if not get_artifact_by_id(artifact_id):
        raise HTTPException(status_code=404, detail="artifact not found")
    return list_versions_by_artifact(artifact_id)
```

- [ ] **Step 9.4: Run — passes**

- [ ] **Step 9.5: Commit**

```bash
git add app/main.py tests/test_artifacts_api.py
git commit -m "feat(artifacts): GET /api/artifacts/{id}/versions endpoint"
```

---

## Task 10: `GET /api/artifacts/{id}/diff` endpoint

**Files:** `app/main.py` (modify), `tests/test_artifacts_api.py` (append)

- [ ] **Step 10.1: Append test**

```python
def test_diff_between_versions(client, git_artifacts_repo):
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('td','TD')")
        topic_id = cursor.lastrowid

    c = client.post("/api/artifacts", json={
        "slug": "dd", "type": "text", "backend": "git", "title": "DD",
        "topic_id": topic_id, "content_b64": "YWxwaGEKYmV0YQo=",  # "alpha\nbeta\n"
        "summary": "init",
    }).json()
    aid = c["artifact"]["id"]
    u = client.post(f"/api/artifacts/{aid}/update", json={
        "content_b64": "YWxwaGEKR0FNTUEK",  # "alpha\nGAMMA\n"
        "summary": "edit", "version_label": "v1",
    }).json()

    r = client.get(f"/api/artifacts/{aid}/diff?from_label=v0&to_label=v1")
    assert r.status_code == 200
    diff = r.json()["diff"]
    assert "-beta" in diff
    assert "+GAMMA" in diff
```

- [ ] **Step 10.2: Run — FAIL**

- [ ] **Step 10.3: Add endpoint**

```python
@app.get("/api/artifacts/{artifact_id}/diff")
def artifact_diff(
    artifact_id: int,
    from_label: str,
    to_label: str,
) -> dict:
    from .artifacts.registry import get_adapter
    from .artifacts.models import get_artifact_by_id, list_versions_by_artifact

    art = get_artifact_by_id(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="artifact not found")

    versions = list_versions_by_artifact(artifact_id)
    by_label = {v["version_label"]: v for v in versions}
    if from_label not in by_label or to_label not in by_label:
        raise HTTPException(status_code=404, detail="version label not found")

    repo_path = os.environ.get("LETS_GIT_REPO")
    if not repo_path:
        raise HTTPException(status_code=500, detail="LETS_GIT_REPO not configured")

    adapter = get_adapter("git", repo_path=repo_path)
    diff = adapter.diff(
        backend_ref=art["backend_ref"],
        from_revision=by_label[from_label]["backend_revision_id"],
        to_revision=by_label[to_label]["backend_revision_id"],
    )
    return {"from_label": from_label, "to_label": to_label, "diff": diff}
```

- [ ] **Step 10.4: Run — passes**

- [ ] **Step 10.5: Commit**

```bash
git add app/main.py tests/test_artifacts_api.py
git commit -m "feat(artifacts): GET /api/artifacts/{id}/diff endpoint"
```

---

## Task 11: `GET /api/artifacts/{id}` (read current) endpoint

**Files:** `app/main.py` (modify), `tests/test_artifacts_api.py` (append)

- [ ] **Step 11.1: Append test**

```python
def test_read_artifact_current(client, git_artifacts_repo):
    import base64
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('tr','TR')")
        topic_id = cursor.lastrowid

    c = client.post("/api/artifacts", json={
        "slug": "rr", "type": "text", "backend": "git", "title": "RR",
        "topic_id": topic_id, "content_b64": "YWJj",  # 'abc'
        "summary": "init",
    }).json()
    aid = c["artifact"]["id"]
    client.post(f"/api/artifacts/{aid}/update", json={
        "content_b64": "ZGVm",  # 'def'
        "summary": "edit", "version_label": "v1",
    })

    r = client.get(f"/api/artifacts/{aid}")
    assert r.status_code == 200
    data = r.json()
    assert data["artifact"]["slug"] == "rr"
    assert base64.b64decode(data["content_b64"]) == b"def"
    assert data["current_version_label"] == "v1"
```

- [ ] **Step 11.2: Run — FAIL**

- [ ] **Step 11.3: Add endpoint**

```python
@app.get("/api/artifacts/{artifact_id}")
def read_artifact(artifact_id: int, version_label: str | None = None) -> dict:
    import base64
    from .artifacts.registry import get_adapter
    from .artifacts.models import get_artifact_by_id, list_versions_by_artifact

    art = get_artifact_by_id(artifact_id)
    if not art:
        raise HTTPException(status_code=404, detail="artifact not found")

    versions = list_versions_by_artifact(artifact_id)
    by_label = {v["version_label"]: v for v in versions}
    current_v = None
    revision_id = None
    if version_label:
        if version_label not in by_label:
            raise HTTPException(status_code=404, detail="version label not found")
        current_v = version_label
        revision_id = by_label[version_label]["backend_revision_id"]
    else:
        if versions:
            current_v = versions[-1]["version_label"]
            # None means current working tree
            revision_id = None

    repo_path = os.environ.get("LETS_GIT_REPO")
    if not repo_path:
        raise HTTPException(status_code=500, detail="LETS_GIT_REPO not configured")
    adapter = get_adapter("git", repo_path=repo_path)
    content = adapter.read(backend_ref=art["backend_ref"], revision_id=revision_id)

    return {
        "artifact": art,
        "content_b64": base64.b64encode(content).decode("ascii"),
        "current_version_label": current_v,
    }
```

- [ ] **Step 11.4: Run — passes**

- [ ] **Step 11.5: Commit**

```bash
git add app/main.py tests/test_artifacts_api.py
git commit -m "feat(artifacts): GET /api/artifacts/{id} endpoint with optional version_label"
```

---

## Task 12: End-to-end test (create → update → list → diff → read)

**Files:** `tests/test_artifacts_e2e.py` (create)

- [ ] **Step 12.1: Write integration test**

Create `tests/test_artifacts_e2e.py`:
```python
import base64
import subprocess
import tempfile

import pytest


@pytest.fixture
def git_artifacts_repo(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="lets-artifacts-e2e-")
    subprocess.run(["git", "init", "--quiet", tmp], check=True)
    subprocess.run(["git", "-C", tmp, "config", "user.name", "T"], check=True)
    subprocess.run(["git", "-C", tmp, "config", "user.email", "t@t"], check=True)
    subprocess.run(["git", "-C", tmp, "commit", "--allow-empty", "-m", "init", "--quiet"], check=True)
    monkeypatch.setenv("LETS_GIT_REPO", tmp)
    yield tmp
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


def test_full_artifact_lifecycle(client, git_artifacts_repo):
    """Simulates a PPT-like scenario: create v0 → claude updates to v1 → trinity updates to v2 → diff."""
    from app.db import connect
    with connect() as conn:
        cursor = conn.execute("INSERT INTO topics (slug, title) VALUES ('e2e','PPT Topic')")
        topic_id = cursor.lastrowid

    # Neo creates the initial PPT skeleton
    r = client.post("/api/artifacts", json={
        "slug": "q3-ppt", "type": "pptx", "backend": "git",
        "title": "Q3 Review PPT", "topic_id": topic_id,
        "content_b64": base64.b64encode(b"slide1: Q3 numbers\n").decode(),
        "summary": "Neo: 8-page skeleton",
    })
    assert r.status_code == 200
    art_id = r.json()["artifact"]["id"]

    # Claude updates: add P4 matrix
    client.post(f"/api/artifacts/{art_id}/update", json={
        "content_b64": base64.b64encode(b"slide1: Q3 numbers\nslide4: matrix 4x6\n").decode(),
        "summary": "claude: P4 matrix",
        "version_label": "v1",
    })

    # Trinity updates: rephrase
    client.post(f"/api/artifacts/{art_id}/update", json={
        "content_b64": base64.b64encode(b"slide1: Q3 highlights\nslide4: matrix 4x6\n").decode(),
        "summary": "trinity: tighten P1",
        "version_label": "v2",
    })

    # List versions
    versions = client.get(f"/api/artifacts/{art_id}/versions").json()
    labels = [v["version_label"] for v in versions]
    assert labels == ["v0", "v1", "v2"]

    # Diff v0..v2
    diff = client.get(f"/api/artifacts/{art_id}/diff?from_label=v0&to_label=v2").json()
    assert "highlights" in diff["diff"]
    assert "matrix" in diff["diff"]

    # Read current
    current = client.get(f"/api/artifacts/{art_id}").json()
    assert base64.b64decode(current["content_b64"]) == b"slide1: Q3 highlights\nslide4: matrix 4x6\n"
    assert current["current_version_label"] == "v2"
```

- [ ] **Step 12.2: Run — passes**

```bash
.venv/bin/pytest tests/test_artifacts_e2e.py -v
.venv/bin/pytest -v
```

- [ ] **Step 12.3: Commit**

```bash
git add tests/test_artifacts_e2e.py
git commit -m "test(artifacts): end-to-end lifecycle (create + 2 updates + list + diff + read)"
```

---

## Task 13: README — Track D section

**Files:** `README.md` (modify)

- [ ] **Step 13.1: Append section**

After existing v1.5 sections:

```markdown
## v1.5 Artifact Substrate (Track D)

Artifacts are the structured products of collaboration (PPTs / docs / code /
analyses). Each artifact has a stable identity, a version chain, and a backend
adapter that knows how to read / write / diff / list versions.

### Schema (added by Track D)

- `artifacts` (id, slug, type, backend, backend_ref, title, topic_id, current_version_id, ...)
- `artifact_versions` (id, artifact_id, version_label, backend_revision_id, summary, preview_uri, created_by_*)

### Backend supported in v1.5b

- `git` — files live in a git repo pointed to by `LETS_GIT_REPO` env var

Future backends (v1.5c+): `google-slides`, `google-docs`, `google-sheets`,
`object-storage`, `feishu-*`. See `docs/artifact-sync-strategy.md`.

### API

```text
POST   /api/artifacts                 # create (initial version v0)
POST   /api/artifacts/{id}/update     # add a new version with semantic label
GET    /api/artifacts/{id}            # read current (or ?version_label=v1)
GET    /api/artifacts/{id}/versions   # list version chain
GET    /api/artifacts/{id}/diff       # ?from_label=v0&to_label=v1
```

### Setup

```bash
mkdir -p ~/lets-artifacts && cd ~/lets-artifacts && git init && \
  git commit --allow-empty -m init
export LETS_GIT_REPO=~/lets-artifacts
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```
```

- [ ] **Step 13.2: Commit**

```bash
git add README.md
git commit -m "docs: README section for Track D (Artifact substrate)"
```

---

## Self-Review Summary

**Spec coverage:**
- ✅ artifacts table — Task 1
- ✅ artifact_versions table — Task 2
- ✅ ArtifactSyncAdapter ABC — Task 3
- ✅ GitBackend implementation — Task 4
- ✅ Backend registry — Task 5
- ✅ Models DB helpers — Task 6
- ✅ POST /api/artifacts — Task 7
- ✅ POST /api/artifacts/{id}/update — Task 8
- ✅ GET /api/artifacts/{id}/versions — Task 9
- ✅ GET /api/artifacts/{id}/diff — Task 10
- ✅ GET /api/artifacts/{id} — Task 11
- ✅ E2E lifecycle test — Task 12
- ✅ README — Task 13

**Placeholder scan:** every test has real assertions; every code block is the actual code to copy; no "..." or "TODO".

**Type consistency:**
- `ArtifactSyncAdapter` methods always return the dataclass types declared (CreateResult / UpdateResult / VersionInfo).
- `backend_ref` is a str everywhere — file path for git, never confused with version_label.
- `version_label` is caller-supplied (caller decides v0/v1/final), not auto-generated.

**Known gaps deferred to v1.5c+:**
- Google Slides / Docs / Sheets backends
- Object Storage backend
- Diff for binary types (PPT inside pptx zip): not supported by git diff; future backends will handle
- Preview thumbnail generation (`preview_uri`): schema supports it, but no generator wired in
- Authorization on artifact endpoints (assumed handled by Track B's middleware once that lands)

**Coordination with Track B:** If Track B is merged before this track, the artifact endpoints will need `principal: dict = Depends(get_current_principal)` added during integration. Otherwise this track runs on the un-auth'd base.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-19-track-d-artifact-substrate.md`.**

Recommended execution: `superpowers:subagent-driven-development`. Tasks 1-2 (schema), 3-6 (backend layer), 7-11 (endpoints), 12-13 (integration + docs) are mostly sequential within each cluster but 7-11 can be parallelized if working in separate sub-branches.

**Dependency on Track A:** schema substrate must exist. `topics` table is required for `artifacts.topic_id` FK. `humans` and `agent_instances` are referenced by `artifact_versions.created_by_*`.

**Branch suggestion:** `track-d-artifacts` off the latest `track-a-schema` HEAD (parallel to `track-b-network`).
