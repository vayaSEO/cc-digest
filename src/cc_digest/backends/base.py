"""Abstract storage backend protocol."""

from __future__ import annotations

from typing import Protocol


class StorageBackend(Protocol):
    """Interface that every storage backend must implement."""

    def upsert_session(self, doc: dict) -> bool:
        """Insert or update a session. Returns True if new, False if updated."""
        ...

    def get_session(self, session_id: str) -> dict | None:
        """Return a single session by ID, or None."""
        ...

    def list_sessions(
        self,
        project: str | None = None,
        limit: int = 0,
        offset: int = 0,
        has_digest: bool | None = None,
    ) -> list[dict]:
        """List sessions with optional filters."""
        ...

    def count_sessions(self, project: str | None = None) -> int:
        """Count total sessions, optionally filtered by project."""
        ...

    def update_digest(self, session_id: str, digest: str) -> None:
        """Store the LLM-generated digest for a session."""
        ...

    def update_embedding(self, session_id: str, embedding: list[float]) -> None:
        """Store the embedding vector for a session's digest."""
        ...

    def search_by_embedding(self, query_vec: list[float], top_k: int = 5) -> list[dict]:
        """Return top_k sessions most similar to query_vec (cosine similarity)."""
        ...

    def get_projects(self) -> list[str]:
        """Return list of distinct project names."""
        ...

    def close(self) -> None:
        """Clean up resources."""
        ...
