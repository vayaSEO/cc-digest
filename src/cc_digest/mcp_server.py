"""MCP server — expose cc-digest search tools to Claude Code."""

from __future__ import annotations

import asyncio
import logging
import re
import sys

logger = logging.getLogger("cc_digest.mcp")


def _compact_session(s: dict) -> dict:
    """Strip heavy fields for compact JSON responses."""
    return {k: v for k, v in s.items() if k not in ("messages", "embedding")}


def _grep_search(store, query: str, top_k: int, project: str | None) -> list[dict]:
    """Word-boundary text search over digests and titles."""
    sessions = store.list_sessions(project=project, has_digest=True)
    words = query.lower().split()
    patterns = [re.compile(rf"\b{re.escape(w)}\b") for w in words]
    scored: list[dict] = []

    for s in sessions:
        search_text = f"{s.get('title', '')} {s.get('digest', '')}".lower()
        hits = sum(1 for p in patterns if p.search(search_text))
        if hits > 0:
            s["score"] = round(hits / len(words), 3)
            scored.append(s)

    if len(scored) < top_k:
        no_digest = store.list_sessions(project=project, has_digest=False)
        for s in no_digest:
            msg_text = " ".join(
                m.get("content", "")[:200] for m in s.get("messages", [])[:5]
            )
            search_text = f"{s.get('title', '')} {msg_text}".lower()
            hits = sum(1 for p in patterns if p.search(search_text))
            if hits > 0:
                s["score"] = round(hits / len(words) * 0.5, 3)
                scored.append(s)

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def _semantic_search(cfg, store, query: str, top_k: int, project: str | None) -> list[dict] | None:
    """Semantic search via embeddings. Returns None if Ollama is unreachable."""
    from cc_digest.llm import embed as get_embedding

    try:
        query_vec = get_embedding(cfg, query)
    except Exception:
        logger.warning("Ollama unreachable, falling back to grep")
        return None

    if not query_vec:
        return None

    results = store.search_by_embedding(query_vec, top_k=top_k * 2)
    if project:
        results = [r for r in results if r.get("project") == project]
    return results[:top_k]


def _do_search(query: str, top_k: int, mode: str, project: str | None) -> dict:
    """Synchronous search dispatcher."""
    from cc_digest.backends import get_backend
    from cc_digest.config import load_config

    cfg = load_config()
    store = get_backend(cfg)
    try:
        effective_mode = mode
        if mode == "auto":
            samples = store.list_sessions(has_digest=True, limit=1)
            has_emb = any(s.get("embedding") for s in samples)
            effective_mode = "semantic" if has_emb else "grep"

        results = None
        if effective_mode == "semantic":
            results = _semantic_search(cfg, store, query, top_k, project)
            if results is None:
                effective_mode = "grep"

        if results is None:
            results = _grep_search(store, query, top_k, project)

        return {
            "mode": effective_mode,
            "count": len(results),
            "results": [_compact_session(r) for r in results],
        }
    finally:
        store.close()


def _do_list(project: str | None, limit: int, offset: int, has_digest: bool | None) -> dict:
    """Synchronous list sessions."""
    from cc_digest.backends import get_backend
    from cc_digest.config import load_config

    cfg = load_config()
    store = get_backend(cfg)
    try:
        sessions = store.list_sessions(
            project=project, limit=limit, offset=offset, has_digest=has_digest,
        )
        total = store.count_sessions(project=project)
        return {
            "total": total,
            "returned": len(sessions),
            "offset": offset,
            "sessions": [_compact_session(s) for s in sessions],
        }
    finally:
        store.close()


def _do_stats(project: str | None) -> dict:
    """Synchronous stats computation."""
    from cc_digest.backends import get_backend
    from cc_digest.config import load_config

    cfg = load_config()
    store = get_backend(cfg)
    try:
        sessions = store.list_sessions(project=project)
        if not sessions:
            return {"total_sessions": 0, "message": "No sessions found. Run cc-digest extract first."}

        projects: dict[str, int] = {}
        total_messages = 0
        with_digest = 0
        with_embedding = 0
        earliest = None
        latest = None

        for s in sessions:
            proj = s.get("project", "general")
            projects[proj] = projects.get(proj, 0) + 1
            total_messages += s.get("message_count", 0)
            if s.get("digest"):
                with_digest += 1
            if s.get("embedding"):
                with_embedding += 1
            started = s.get("started_at", "")
            if started:
                if earliest is None or started < earliest:
                    earliest = started
                if latest is None or started > latest:
                    latest = started

        return {
            "total_sessions": len(sessions),
            "total_messages": total_messages,
            "digested": with_digest,
            "embedded": with_embedding,
            "earliest_session": earliest[:10] if earliest else None,
            "latest_session": latest[:10] if latest else None,
            "projects": projects,
        }
    finally:
        store.close()


def create_server():
    """Create and configure the FastMCP server."""
    try:
        from fastmcp import FastMCP
    except ImportError:
        print(
            "FastMCP is required for the MCP server.\n"
            "Install with: pip install cc-digest[mcp]",
            file=sys.stderr,
        )
        sys.exit(1)

    mcp = FastMCP(
        name="cc-digest",
        instructions=(
            "Search and explore past Claude Code sessions. "
            "Use search_sessions to find context from previous conversations. "
            "Use list_sessions to browse sessions by project. "
            "Use session_stats for an overview of session history."
        ),
    )

    @mcp.tool
    async def search_sessions(
        query: str,
        top_k: int = 5,
        mode: str = "auto",
        project: str | None = None,
    ) -> dict:
        """Search past Claude Code sessions by meaning or text.

        Use this to find context from previous conversations — architectural
        decisions, debugging steps, solutions, or any past work.

        Args:
            query: Natural language search query.
            top_k: Max results to return (1-20, default 5).
            mode: "auto" (semantic with grep fallback), "semantic", or "grep".
            project: Filter by project name, or None for all.
        """
        top_k = max(1, min(top_k, 20))
        return await asyncio.to_thread(_do_search, query, top_k, mode, project)

    @mcp.tool
    async def list_sessions(
        project: str | None = None,
        limit: int = 20,
        offset: int = 0,
        has_digest: bool | None = None,
    ) -> dict:
        """List stored Claude Code sessions with optional filtering.

        Args:
            project: Filter by project name, or None for all.
            limit: Max sessions to return (default 20, max 100).
            offset: Skip N sessions for pagination.
            has_digest: True = only digested, False = only undigested, None = all.
        """
        limit = max(1, min(limit, 100))
        return await asyncio.to_thread(_do_list, project, limit, offset, has_digest)

    @mcp.tool
    async def session_stats(project: str | None = None) -> dict:
        """Get statistics about stored Claude Code sessions.

        Args:
            project: Filter stats to a specific project, or None for global.
        """
        return await asyncio.to_thread(_do_stats, project)

    return mcp


def main():
    """Entry point: run the MCP server over stdio."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logging.getLogger("cc_digest").addHandler(handler)
    logging.getLogger("cc_digest").setLevel(logging.INFO)

    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
