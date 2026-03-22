"""Storage backends — SQLite (default) and MongoDB (opt-in)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cc_digest.backends.base import StorageBackend
    from cc_digest.config import Config


def get_backend(cfg: "Config") -> "StorageBackend":
    """Factory: return the configured storage backend."""
    if cfg.storage_backend == "mongo":
        from cc_digest.backends.mongo import MongoBackend

        return MongoBackend(cfg)
    from cc_digest.backends.sqlite import SQLiteBackend

    return SQLiteBackend(cfg)
