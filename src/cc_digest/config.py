"""Configuration loaded from .env and environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def _find_dotenv() -> Path | None:
    """Walk up from cwd looking for .env, stop at cc-digest project root."""
    here = Path.cwd()
    for parent in [here, *here.parents]:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
        if (parent / "pyproject.toml").is_file():
            break
    return None


@dataclass(frozen=True)
class Config:
    # Paths
    claude_projects_dir: Path = field(default_factory=lambda: Path.home() / ".claude" / "projects")
    data_dir: Path = field(default_factory=lambda: Path.home() / ".local" / "share" / "cc-digest")

    # Display
    user_display_name: str = "User"

    # Storage
    storage_backend: str = "sqlite"  # "sqlite" | "mongo"
    sqlite_path: Path | None = None  # default: data_dir / "cc-digest.db"
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "claude_sessions"

    # Ollama
    ollama_url: str = "http://localhost:11434"
    digest_model: str = "qwen3:14b"
    embed_model: str = "nomic-embed-text"

    # Project detection
    project_roots: tuple[str, ...] = ("Projects", "Proyectos", "dev", "workspace", "repos", "src")

    # Extraction
    min_messages: int = 4

    @property
    def db_path(self) -> Path:
        if self.sqlite_path:
            return self.sqlite_path
        return self.data_dir / "cc-digest.db"

    @property
    def sessions_dir(self) -> Path:
        return self.data_dir / "sessions"

    @property
    def digests_dir(self) -> Path:
        return self.data_dir / "sessions-digest"


def load_config() -> Config:
    """Load config from .env file and environment variables."""
    dotenv_path = _find_dotenv()
    if dotenv_path:
        load_dotenv(dotenv_path)

    def env(key: str, default: str = "") -> str:
        return os.environ.get(key, default)

    def env_path(key: str, default: str = "") -> Path | None:
        val = env(key)
        return (
            Path(os.path.expanduser(val))
            if val
            else (Path(os.path.expanduser(default)) if default else None)
        )

    data_dir = (
        env_path("CC_DIGEST_DATA_DIR", "~/.local/share/cc-digest")
        or Path.home() / ".local" / "share" / "cc-digest"
    )

    return Config(
        claude_projects_dir=env_path("CLAUDE_PROJECTS_DIR", "~/.claude/projects")
        or Path.home() / ".claude" / "projects",
        data_dir=data_dir,
        user_display_name=env("USER_DISPLAY_NAME", "User"),
        storage_backend=env("STORAGE_BACKEND", "sqlite"),
        sqlite_path=env_path("SQLITE_PATH"),
        mongo_uri=env("MONGO_URI", "mongodb://localhost:27017"),
        mongo_db=env("MONGO_DB", "claude_sessions"),
        ollama_url=env("OLLAMA_URL", "http://localhost:11434"),
        digest_model=env("DIGEST_MODEL", "qwen3:14b"),
        embed_model=env("EMBED_MODEL", "nomic-embed-text"),
        min_messages=int(env("MIN_MESSAGES", "4")),
        project_roots=tuple(
            env("PROJECT_ROOTS", "Projects,Proyectos,dev,workspace,repos,src").split(",")
        ),
    )
