"""Tests for cc_digest.backends.sqlite — CRUD operations."""

import pytest


def test_upsert_new_session(sqlite_store, sample_session_doc):
    is_new = sqlite_store.upsert_session(sample_session_doc)
    assert is_new is True


def test_upsert_existing_session_updates(sqlite_store, sample_session_doc):
    sqlite_store.upsert_session(sample_session_doc)
    sample_session_doc["title"] = "updated title"
    is_new = sqlite_store.upsert_session(sample_session_doc)
    assert is_new is False
    doc = sqlite_store.get_session(sample_session_doc["session_id"])
    assert doc["title"] == "updated title"


def test_get_session_not_found(sqlite_store):
    assert sqlite_store.get_session("nonexistent") is None


def test_list_sessions_all(sqlite_store, sample_session_doc):
    for i in range(3):
        doc = {**sample_session_doc, "session_id": f"session-{i}"}
        sqlite_store.upsert_session(doc)
    sessions = sqlite_store.list_sessions()
    assert len(sessions) == 3


def test_list_sessions_by_project(sqlite_store, sample_session_doc):
    sqlite_store.upsert_session({**sample_session_doc, "session_id": "s1", "project": "app1"})
    sqlite_store.upsert_session({**sample_session_doc, "session_id": "s2", "project": "app2"})
    sqlite_store.upsert_session({**sample_session_doc, "session_id": "s3", "project": "app1"})
    result = sqlite_store.list_sessions(project="app1")
    assert len(result) == 2
    assert all(s["project"] == "app1" for s in result)


def test_list_sessions_has_digest_filter(sqlite_store, sample_session_doc):
    sqlite_store.upsert_session({**sample_session_doc, "session_id": "s1"})
    sqlite_store.upsert_session({**sample_session_doc, "session_id": "s2"})
    sqlite_store.update_digest("s1", "This is a digest")
    with_digest = sqlite_store.list_sessions(has_digest=True)
    without_digest = sqlite_store.list_sessions(has_digest=False)
    assert len(with_digest) == 1
    assert len(without_digest) == 1
    assert with_digest[0]["session_id"] == "s1"


def test_list_sessions_limit_offset(sqlite_store, sample_session_doc):
    for i in range(5):
        doc = {
            **sample_session_doc,
            "session_id": f"s{i}",
            "started_at": f"2026-03-{20 - i:02d}T10:00:00Z",
        }
        sqlite_store.upsert_session(doc)
    result = sqlite_store.list_sessions(limit=2, offset=1)
    assert len(result) == 2


def test_count_sessions(sqlite_store, sample_session_doc):
    for i in range(3):
        sqlite_store.upsert_session({**sample_session_doc, "session_id": f"s{i}"})
    assert sqlite_store.count_sessions() == 3


def test_count_sessions_by_project(sqlite_store, sample_session_doc):
    sqlite_store.upsert_session({**sample_session_doc, "session_id": "s1", "project": "a"})
    sqlite_store.upsert_session({**sample_session_doc, "session_id": "s2", "project": "b"})
    assert sqlite_store.count_sessions(project="a") == 1


def test_update_digest(sqlite_store, sample_session_doc):
    sqlite_store.upsert_session(sample_session_doc)
    sqlite_store.update_digest(sample_session_doc["session_id"], "Summary text")
    doc = sqlite_store.get_session(sample_session_doc["session_id"])
    assert doc["digest"] == "Summary text"


def test_update_embedding(sqlite_store, sample_session_doc):
    sqlite_store.upsert_session(sample_session_doc)
    vec = [0.1, 0.2, 0.3, 0.4]
    sqlite_store.update_embedding(sample_session_doc["session_id"], vec)
    doc = sqlite_store.get_session(sample_session_doc["session_id"])
    assert doc["embedding"] == pytest.approx(vec)


def test_search_by_embedding(sqlite_store, sample_session_doc):
    # Insert 3 sessions with different embeddings and digests
    for i, vec in enumerate([[1, 0, 0], [0, 1, 0], [0.9, 0.1, 0]]):
        sid = f"s{i}"
        sqlite_store.upsert_session({**sample_session_doc, "session_id": sid})
        sqlite_store.update_digest(sid, f"digest {i}")
        sqlite_store.update_embedding(sid, vec)

    results = sqlite_store.search_by_embedding([1, 0, 0], top_k=2)
    assert len(results) == 2
    # Most similar to [1,0,0] should be s0, then s2
    assert results[0]["session_id"] == "s0"
    assert results[1]["session_id"] == "s2"


def test_get_projects(sqlite_store, sample_session_doc):
    sqlite_store.upsert_session({**sample_session_doc, "session_id": "s1", "project": "beta"})
    sqlite_store.upsert_session({**sample_session_doc, "session_id": "s2", "project": "alpha"})
    projects = sqlite_store.get_projects()
    assert projects == ["alpha", "beta"]


def test_messages_roundtrip_json(sqlite_store, sample_session_doc):
    sqlite_store.upsert_session(sample_session_doc)
    doc = sqlite_store.get_session(sample_session_doc["session_id"])
    assert isinstance(doc["messages"], list)
    assert doc["messages"][0]["role"] == "user"
    assert doc["messages"][0]["content"] == "fix the login bug"
