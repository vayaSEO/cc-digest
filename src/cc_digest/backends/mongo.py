"""MongoDB storage backend — optional, install with: pip install cc-digest[mongo]."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from cc_digest.config import Config


class MongoBackend:
    def __init__(self, cfg: Config):
        try:
            from pymongo import MongoClient
        except ImportError:
            raise RuntimeError(
                "pymongo is required for MongoDB backend.\n"
                "Install with: pip install cc-digest[mongo]"
            )
        self._client = MongoClient(cfg.mongo_uri)
        self._db = self._client[cfg.mongo_db]
        self._col = self._db["sessions"]
        self._ensure_indexes()

    def _ensure_indexes(self):
        self._col.create_index("session_id", unique=True, sparse=True)
        self._col.create_index("project")
        self._col.create_index("started_at")

    def upsert_session(self, doc: dict) -> bool:
        doc["imported_at"] = datetime.now(timezone.utc)
        result = self._col.replace_one(
            {"session_id": doc["session_id"]},
            doc,
            upsert=True,
        )
        return result.upserted_id is not None

    def get_session(self, session_id: str) -> dict | None:
        doc = self._col.find_one({"session_id": session_id}, {"_id": 0})
        return doc

    def list_sessions(
        self,
        project: str | None = None,
        limit: int = 0,
        offset: int = 0,
        has_digest: bool | None = None,
    ) -> list[dict]:
        query: dict = {}
        if project:
            query["project"] = project
        if has_digest is True:
            query["digest"] = {"$exists": True, "$ne": ""}
        elif has_digest is False:
            query["$or"] = [{"digest": {"$exists": False}}, {"digest": ""}]

        cursor = self._col.find(query, {"_id": 0}).sort("started_at", -1)
        if offset:
            cursor = cursor.skip(offset)
        if limit:
            cursor = cursor.limit(limit)
        return list(cursor)

    def count_sessions(self, project: str | None = None) -> int:
        query = {"project": project} if project else {}
        return self._col.count_documents(query)

    def update_digest(self, session_id: str, digest: str) -> None:
        self._col.update_one({"session_id": session_id}, {"$set": {"digest": digest}})

    def update_embedding(self, session_id: str, embedding: list[float]) -> None:
        self._col.update_one({"session_id": session_id}, {"$set": {"embedding": embedding}})

    def search_by_embedding(self, query_vec: list[float], top_k: int = 5) -> list[dict]:
        docs = list(
            self._col.find(
                {"embedding": {"$exists": True, "$ne": []}, "digest": {"$exists": True, "$ne": ""}},
                {"_id": 0},
            )
        )
        scored = []
        for doc in docs:
            emb = doc.get("embedding", [])
            if not emb:
                continue
            sim = _cosine_similarity(query_vec, emb)
            doc["score"] = sim
            scored.append(doc)
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def get_projects(self) -> list[str]:
        return sorted(self._col.distinct("project"))

    def close(self) -> None:
        self._client.close()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
