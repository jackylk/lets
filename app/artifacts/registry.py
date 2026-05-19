"""Backend registry. As more backends land (google-slides, object-storage, ...),
register them here."""
from __future__ import annotations

from typing import Any

from .adapter import ArtifactSyncAdapter
from .git_backend import GitBackend


def get_adapter(backend: str, **kwargs: Any) -> ArtifactSyncAdapter:
    if backend == "git":
        repo_path = kwargs.get("repo_path")
        if not repo_path:
            raise ValueError("git backend requires repo_path")
        return GitBackend(repo_path=repo_path)
    raise ValueError(f"unknown backend: {backend}")
