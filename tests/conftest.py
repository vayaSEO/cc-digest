"""Shared fixtures for cc-digest tests."""

import pytest

from cc_digest.config import Config
from cc_digest.backends.sqlite import SQLiteBackend


@pytest.fixture
def sample_session_doc():
    """A minimal valid session document."""
    return {
        "session_id": "abc12345-6789-0000-1111-222233334444",
        "project": "myapp",
        "title": "fix the login bug",
        "cwd": "/Users/test/Projects/myapp",
        "message_count": 3,
        "started_at": "2026-03-20T10:00:00Z",
        "ended_at": "2026-03-20T10:30:00Z",
        "messages": [
            {"role": "user", "content": "fix the login bug"},
            {"role": "assistant", "content": "I'll look into the auth module."},
            {"role": "user", "content": "thanks"},
        ],
        "source_file": "",
    }


@pytest.fixture
def sqlite_store(tmp_path):
    """Ephemeral SQLite backend for testing."""
    cfg = Config(
        data_dir=tmp_path,
        sqlite_path=tmp_path / "test.db",
    )
    store = SQLiteBackend(cfg)
    yield store
    store.close()
