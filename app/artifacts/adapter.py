"""Artifact sync adapter contract.

All concrete backends (GitBackend, GoogleSlidesBackend, etc.) implement
``ArtifactSyncAdapter``. Lets core code interacts only with this interface.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


class BackendError(Exception):
    """Raised by adapters on backend-side failures (git error, API error, ...)."""


@dataclass
class CreateResult:
    backend_ref: str  # opaque, backend-specific (file path for git, presentationId for google)
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
