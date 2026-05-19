"""Git-backed artifact storage.

Each artifact maps to one file in a git repo. `backend_ref` is the file path
(relative to the repo root). Revisions are git commit SHAs that touch the file.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any, Optional

from .adapter import ArtifactSyncAdapter, BackendError, CreateResult, UpdateResult, VersionInfo


_SLUG_RE = re.compile(r"[^a-zA-Z0-9_\-]+")


def _safe_filename(slug: str, type_hint: str) -> str:
    """slug 'Q3 review!' + 'pptx' → 'q3-review.pptx'."""
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

    def _commit_file(self, rel_path: str, content: bytes, summary: str) -> str:
        full = Path(self.repo_path) / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(content)
        _run_git(self.repo_path, "add", rel_path)
        _run_git(
            self.repo_path,
            "-c", "user.name=Lets Backend",
            "-c", "user.email=bot@lets.local",
            "commit", "--allow-empty", "-m", summary,
        )
        sha = _run_git(self.repo_path, "rev-parse", "HEAD").stdout.decode().strip()
        return sha

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
        result = _run_git(self.repo_path, "show", f"{revision_id}:{backend_ref}")
        return result.stdout

    def list_versions(self, *, backend_ref: str) -> list[VersionInfo]:
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
