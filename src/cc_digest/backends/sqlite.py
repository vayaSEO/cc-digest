"""SQLite storage backend — zero external dependencies."""

from __future__ import annotations

import json
import math
import sqlite3

from cc_digest.config import Config


class SQLiteBackend:
    def __init__(self, cfg: Config):
        db_path = cfg.db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id   TEXT PRIMARY KEY,
                project      TEXT NOT NULL DEFAULT '',
                title        TEXT NOT NULL DEFAULT '',
                cwd          TEXT DEFAULT '',
                message_count INTEGER DEFAULT 0,
                started_at   TEXT,
                ended_at     TEXT,
                messages     TEXT NOT NULL DEFAULT '[]',
                source_file  TEXT DEFAULT '',
                digest       TEXT DEFAULT '',
                embedding    TEXT DEFAULT '',
                imported_at  TEXT DEFAULT (datetime('now'))
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project);
            CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
        """)
        self._conn.commit()

    def _row_to_dict(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        d["messages"] = json.loads(d.get("messages", "[]"))
        if d.get("embedding"):
            d["embedding"] = json.loads(d["embedding"])
        else:
            d["embedding"] = []
        return d

    def upsert_session(self, doc: dict) -> bool:
        cur = self._conn.execute(
            "SELECT 1 FROM sessions WHERE session_id = ?", (doc["session_id"],)
        )
        is_new = cur.fetchone() is None

        self._conn.execute(
            """
            INSERT INTO sessions (session_id, project, title, cwd, message_count,
                                  started_at, ended_at, messages, source_file)
            VALUES (:session_id, :project, :title, :cwd, :message_count,
                    :started_at, :ended_at, :messages, :source_file)
            ON CONFLICT(session_id) DO UPDATE SET
                project = excluded.project,
                title = excluded.title,
                cwd = excluded.cwd,
                message_count = excluded.message_count,
                started_at = excluded.started_at,
                ended_at = excluded.ended_at,
                messages = excluded.messages,
                source_file = excluded.source_file,
                imported_at = datetime('now')
        """,
            {
                "session_id": doc.get("session_id", ""),
                "project": doc.get("project", ""),
                "title": doc.get("title", ""),
                "cwd": doc.get("cwd", ""),
                "message_count": doc.get("message_count", 0),
                "started_at": doc.get("started_at", ""),
                "ended_at": doc.get("ended_at", ""),
                "messages": json.dumps(doc.get("messages", []), ensure_ascii=False),
                "source_file": doc.get("source_file", ""),
            },
        )
        self._conn.commit()
        return is_new

    def get_session(self, session_id: str) -> dict | None:
        cur = self._conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        row = cur.fetchone()
        return self._row_to_dict(row) if row else None

    def list_sessions(
        self,
        project: str | None = None,
        limit: int = 0,
        offset: int = 0,
        has_digest: bool | None = None,
    ) -> list[dict]:
        sql = "SELECT * FROM sessions WHERE 1=1"
        params: list = []
        if project:
            sql += " AND project = ?"
            params.append(project)
        if has_digest is True:
            sql += " AND digest != ''"
        elif has_digest is False:
            sql += " AND (digest = '' OR digest IS NULL)"
        sql += " ORDER BY started_at DESC"
        if limit > 0:
            sql += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])
        return [self._row_to_dict(r) for r in self._conn.execute(sql, params)]

    def count_sessions(self, project: str | None = None) -> int:
        if project:
            cur = self._conn.execute("SELECT COUNT(*) FROM sessions WHERE project = ?", (project,))
        else:
            cur = self._conn.execute("SELECT COUNT(*) FROM sessions")
        return cur.fetchone()[0]

    def update_digest(self, session_id: str, digest: str) -> None:
        self._conn.execute(
            "UPDATE sessions SET digest = ? WHERE session_id = ?", (digest, session_id)
        )
        self._conn.commit()

    def update_embedding(self, session_id: str, embedding: list[float]) -> None:
        self._conn.execute(
            "UPDATE sessions SET embedding = ? WHERE session_id = ?",
            (json.dumps(embedding), session_id),
        )
        self._conn.commit()

    def search_by_embedding(self, query_vec: list[float], top_k: int = 5) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM sessions WHERE embedding != '' AND digest != ''"
        ).fetchall()

        scored = []
        for row in rows:
            d = self._row_to_dict(row)
            emb = d.get("embedding", [])
            if not emb:
                continue
            sim = _cosine_similarity(query_vec, emb)
            d["score"] = sim
            scored.append(d)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def get_projects(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT DISTINCT project FROM sessions ORDER BY project"
        ).fetchall()
        return [r[0] for r in rows if r[0]]

    def close(self) -> None:
        self._conn.close()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
