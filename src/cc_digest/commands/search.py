"""cc-digest search & embed — find sessions by semantic similarity or text grep."""

from __future__ import annotations

import re
from dataclasses import replace

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from cc_digest.cli import app

console = Console()


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query"),
    top_k: int = typer.Option(5, "--top", "-k", help="Number of results to show"),
    mode: str = typer.Option("auto", "--mode", help="Search mode: auto, semantic, grep"),
    project: str = typer.Option(None, "--project", "-p", help="Filter by project"),
    backend: str = typer.Option(None, "--backend", "-b", help="Storage backend"),
):
    """Search sessions by semantic similarity or text matching."""
    from cc_digest.config import load_config
    from cc_digest.backends import get_backend

    cfg = load_config()
    if backend:
        cfg = replace(cfg, storage_backend=backend)

    store = get_backend(cfg)
    try:
        # Decide mode
        if mode == "auto":
            sessions_with_emb = store.list_sessions(has_digest=True, limit=1)
            has_embeddings = any(s.get("embedding") for s in sessions_with_emb)
            mode = "semantic" if has_embeddings else "grep"

        if mode == "semantic":
            _search_semantic(cfg, store, query, top_k, project)
        else:
            _search_grep(store, query, top_k, project)
    finally:
        store.close()


def _search_semantic(cfg, store, query: str, top_k: int, project: str | None):
    """Search using embeddings cosine similarity."""
    from cc_digest.llm import embed as get_embedding

    console.print("[dim]Generating embedding for query...[/dim]")
    try:
        query_vec = get_embedding(cfg, query)
    except Exception as e:
        console.print(f"[red]Cannot generate embedding: {e}[/red]")
        console.print("[yellow]Falling back to grep mode.[/yellow]")
        _search_grep(store, query, top_k, project)
        return

    if not query_vec:
        console.print("[yellow]Empty embedding. Falling back to grep.[/yellow]")
        _search_grep(store, query, top_k, project)
        return

    results = store.search_by_embedding(query_vec, top_k=top_k * 2)

    if project:
        results = [r for r in results if r.get("project") == project]
    results = results[:top_k]

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    console.print(f"\n[bold]Top {len(results)} results[/bold] (semantic search)\n")
    for i, r in enumerate(results, 1):
        _print_result(i, r, r.get("score", 0))


def _search_grep(store, query: str, top_k: int, project: str | None):
    """Fallback: search digests and titles by word-boundary text matching."""
    sessions = store.list_sessions(project=project, has_digest=True)

    query_lower = query.lower()
    words = query_lower.split()
    # Pre-compile word boundary patterns
    patterns = [re.compile(rf"\b{re.escape(w)}\b") for w in words]
    scored = []

    for s in sessions:
        digest = s.get("digest", "")
        title = s.get("title", "")
        search_text = f"{title} {digest}".lower()

        hits = sum(1 for p in patterns if p.search(search_text))
        if hits > 0:
            s["score"] = hits / len(words)
            scored.append(s)

    # Also search in sessions without digest (title + first messages)
    if len(scored) < top_k:
        no_digest = store.list_sessions(project=project, has_digest=False)
        for s in no_digest:
            title = s.get("title", "").lower()
            msg_text = " ".join(
                m.get("content", "")[:200] for m in s.get("messages", [])[:5]
            ).lower()
            search_text = f"{title} {msg_text}"
            hits = sum(1 for p in patterns if p.search(search_text))
            if hits > 0:
                s["score"] = hits / len(words) * 0.5
                scored.append(s)

    scored.sort(key=lambda x: x["score"], reverse=True)
    results = scored[:top_k]

    if not results:
        console.print("[yellow]No results found.[/yellow]")
        return

    console.print(f"\n[bold]Top {len(results)} results[/bold] (text search)\n")
    for i, r in enumerate(results, 1):
        _print_result(i, r, r.get("score", 0))


def _print_result(rank: int, session: dict, score: float):
    """Pretty-print a single search result."""
    title = session.get("title", "sin-titulo")
    project = session.get("project", "")
    sid = session.get("session_id", "")[:8]
    digest = session.get("digest", "")

    header = Text()
    header.append(f"#{rank} ", style="bold cyan")
    header.append(f"[{project}] ", style="bold green")
    header.append(title, style="bold")
    header.append(f"  ({sid}…  score: {score:.2f})", style="dim")

    content = digest[:500] + "…" if len(digest) > 500 else digest
    if not content:
        content = "[no digest — run cc-digest digest first]"

    console.print(Panel(content, title=header, border_style="dim", padding=(0, 1)))


@app.command()
def embed(
    force: bool = typer.Option(
        False, "--force", "-f", help="Re-embed sessions that already have embeddings"
    ),
    limit: int = typer.Option(0, "--limit", "-l", help="Max sessions to embed (0 = all)"),
    backend: str = typer.Option(None, "--backend", "-b", help="Storage backend"),
):
    """Generate embeddings for all digested sessions (needed for semantic search)."""
    from cc_digest.config import load_config
    from cc_digest.backends import get_backend
    from cc_digest.llm import check_ollama, embed as get_embedding
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn

    cfg = load_config()
    if backend:
        cfg = replace(cfg, storage_backend=backend)

    store = get_backend(cfg)
    try:
        sessions = store.list_sessions(has_digest=True)

        if not force:
            sessions = [s for s in sessions if not s.get("embedding")]

        if limit > 0:
            sessions = sessions[:limit]

        if not sessions:
            console.print("[yellow]No sessions to embed.[/yellow]")
            return

        console.print(f"Sessions to embed: [bold]{len(sessions)}[/bold] (model: {cfg.embed_model})")

        try:
            check_ollama(cfg)
        except RuntimeError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)

        embedded = 0
        errors = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Embedding...", total=len(sessions))

            for s in sessions:
                progress.update(task, description=f"[dim]{s['session_id'][:8]}…[/dim]")

                digest_text = s.get("digest", "")
                title = s.get("title", "")
                text_to_embed = f"{title}\n{digest_text}"

                try:
                    vec = get_embedding(cfg, text_to_embed)
                    if vec:
                        store.update_embedding(s["session_id"], vec)
                        embedded += 1
                    else:
                        errors += 1
                except Exception as e:
                    console.print(f"  [red]Error: {e}[/red]")
                    errors += 1

                progress.advance(task)

        console.print(f"\n[bold]Done:[/bold] {embedded} embedded, {errors} errors")
    finally:
        store.close()
