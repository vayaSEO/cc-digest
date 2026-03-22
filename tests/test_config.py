"""Tests for cc_digest.config — configuration loading."""

from pathlib import Path

from cc_digest.config import Config, load_config


def test_default_values():
    cfg = Config()
    assert cfg.storage_backend == "sqlite"
    assert cfg.digest_model == "qwen3:14b"
    assert cfg.embed_model == "nomic-embed-text"
    assert cfg.min_messages == 4
    assert cfg.ollama_url == "http://localhost:11434"
    assert cfg.user_display_name == "User"


def test_db_path_default():
    cfg = Config()
    assert cfg.db_path == cfg.data_dir / "cc-digest.db"


def test_db_path_custom():
    cfg = Config(sqlite_path=Path("/tmp/custom.db"))
    assert cfg.db_path == Path("/tmp/custom.db")


def test_sessions_dir():
    cfg = Config(data_dir=Path("/tmp/test"))
    assert cfg.sessions_dir == Path("/tmp/test/sessions")


def test_digests_dir():
    cfg = Config(data_dir=Path("/tmp/test"))
    assert cfg.digests_dir == Path("/tmp/test/sessions-digest")


def test_load_config_defaults_no_env(monkeypatch):
    # Clear any relevant env vars
    for key in ["STORAGE_BACKEND", "DIGEST_MODEL", "MIN_MESSAGES", "OLLAMA_URL"]:
        monkeypatch.delenv(key, raising=False)
    cfg = load_config()
    assert cfg.storage_backend == "sqlite"
    assert cfg.digest_model == "qwen3:14b"
    assert cfg.min_messages == 4


def test_load_config_respects_env_vars(monkeypatch):
    monkeypatch.setenv("STORAGE_BACKEND", "mongo")
    monkeypatch.setenv("DIGEST_MODEL", "gemma3:12b")
    monkeypatch.setenv("MIN_MESSAGES", "10")
    cfg = load_config()
    assert cfg.storage_backend == "mongo"
    assert cfg.digest_model == "gemma3:12b"
    assert cfg.min_messages == 10


def test_load_config_project_roots_from_env(monkeypatch):
    monkeypatch.setenv("PROJECT_ROOTS", "code,work,repos")
    cfg = load_config()
    assert cfg.project_roots == ("code", "work", "repos")
