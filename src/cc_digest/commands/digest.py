"""cc-digest digest — summarize sessions using a local LLM via Ollama."""

from __future__ import annotations

import re
import time
from dataclasses import replace

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn
from rich.table import Table

from cc_digest.cli import app

console = Console()

DIGEST_PROMPT = """Summarize this work session between a developer and an AI assistant.
Extract as bullet points:
- Project(s) worked on
- What was done (concrete actions)
- Technical decisions made
- Problems encountered and how they were resolved
- TODOs or pending items mentioned
Be concise. Maximum 10 bullet points. Respond in the same language as the conversation."""

_FILLER = frozenset(
    {
        "tool loaded.",
        "si",
        "sí",
        "ok",
        "vale",
        "dale",
        "yes",
        "no",
        "",
    }
)


def _is_filler(content: str) -> bool:
    s = content.strip().lower()
    return s in _FILLER or "[request interrupted" in s


def _truncate_code_blocks(text: str, max_lines: int = 3) -> str:
    """Collapse long code blocks to first few lines."""

    def _replace(m: re.Match) -> str:
        lines = m.group(0).split("\n")
        if len(lines) <= max_lines + 2:
            return m.group(0)
        return (
            lines[0]
            + "\n"
            + "\n".join(lines[1 : max_lines + 1])
            + f"\n[...{len(lines) - max_lines - 2} lines...]\n```"
        )

    return re.sub(r"```\w*\n.*?```", _replace, text, flags=re.DOTALL)


def _condense_assistant(content: str) -> str:
    """Keep only the first paragraph of long assistant messages."""
    content = _truncate_code_blocks(content)
    if len(content) > 500:
        para_end = content.find("\n\n")
        if para_end > 100:
            content = content[:para_end] + "\n[...]"
    return content[:800]


def _prepare_session_text(messages: list[dict], max_chars: int = 16_000) -> str:
    """Build a condensed text from session messages for the LLM.

    Strategy: keep head and tail messages complete (context + conclusions),
    condense the middle (user messages full, assistant first paragraph only),
    strip filler messages and collapse code blocks.
    """
    HEAD = 6
    TAIL = 6

    filtered = [
        (msg["role"], msg.get("content", msg.get("text", "")))
        for msg in messages
        if not _is_filler(msg.get("content", msg.get("text", "")))
    ]

    n = len(filtered)
    parts: list[str] = []
    total = 0

    for i, (role, content) in enumerate(filtered):
        label = "User" if role == "user" else "Assistant"

        if i < HEAD or i >= n - TAIL:
            # Head/tail: keep complete, just truncate code and very long msgs
            content = _truncate_code_blocks(content)
            if len(content) > 2000:
                cut = content[:2000].rfind("\n")
                content = content[: cut if cut > 500 else 2000] + "\n[...]"
        else:
            # Middle: user stays full (short), assistant condensed
            if role == "user":
                if len(content) > 1000:
                    content = content[:1000] + "\n[...]"
            else:
                content = _condense_assistant(content)

        line = f"[{label}]: {content}"
        if total + len(line) > max_chars:
            remaining = n - i
            parts.append(f"[... {remaining} messages omitted ...]")
            # Always append tail messages if we haven't reached them yet
            if i < n - TAIL:
                for j in range(max(i, n - TAIL), n):
                    r, c = filtered[j]
                    c = _truncate_code_blocks(c)[:1000]
                    parts.append(f"[{'User' if r == 'user' else 'Assistant'}]: {c}")
            break
        parts.append(line)
        total += len(line)

    return "\n\n".join(parts)


def _count_words(text: str) -> int:
    return len(text.split())


@app.command()
def digest(
    session: str = typer.Option(None, "--session", "-s", help="Digest a single session UUID"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Re-digest sessions that already have a digest"
    ),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show what would be digested"),
    export_md: bool = typer.Option(False, "--export-md", help="Also export digests as .md files"),
    model: str = typer.Option(None, "--model", help="Override digest model"),
    limit: int = typer.Option(0, "--limit", "-l", help="Max sessions to digest (0 = all)"),
    backend: str = typer.Option(None, "--backend", "-b", help="Storage backend: sqlite or mongo"),
):
    """Generate concise summaries of sessions using a local LLM (Ollama)."""
    from cc_digest.config import load_config
    from cc_digest.backends import get_backend
    from cc_digest.llm import check_ollama, chat

    cfg = load_config()
    if backend:
        cfg = replace(cfg, storage_backend=backend)
    if model:
        cfg = replace(cfg, digest_model=model)

    store = get_backend(cfg)
    try:
        # Get sessions to digest
        if session:
            doc = store.get_session(session)
            if not doc:
                console.print(f"[red]Session {session} not found in storage[/red]")
                raise typer.Exit(1)
            sessions = [doc]
        else:
            sessions = store.list_sessions(has_digest=False if not force else None)

        if not sessions:
            console.print(
                "[yellow]No sessions to digest.[/yellow] Run [bold]cc-digest extract[/bold] first."
            )
            return

        # Filter out already-digested unless --force
        if not force:
            sessions = [s for s in sessions if not s.get("digest")]

        if limit > 0:
            sessions = sessions[:limit]

        console.print(
            f"Sessions to digest: [bold]{len(sessions)}[/bold] (model: {cfg.digest_model})"
        )

        if dry_run:
            for s in sessions:
                title = s.get("title", "")[:60]
                console.print(
                    f"  {s['session_id'][:8]}… [dim]{s.get('project', '')}[/dim] — {title}"
                )
            return

        try:
            check_ollama(cfg)
        except RuntimeError as e:
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1)

        digested = 0
        errors = 0
        total_input_words = 0
        total_output_words = 0
        total_input_chars = 0
        t_start = time.monotonic()
        session_times: list[float] = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Digesting...", total=len(sessions))

            for s in sessions:
                title_short = s.get("title", "")[:40]
                progress.update(
                    task, description=f"[dim]{s['session_id'][:8]}…[/dim] {title_short}"
                )

                session_text = _prepare_session_text(s.get("messages", []))
                prompt = f"{DIGEST_PROMPT}\n\n---\n\n{session_text}"

                input_words = _count_words(session_text)
                total_input_words += input_words
                total_input_chars += len(session_text)

                t_session = time.monotonic()
                try:
                    result = chat(cfg, prompt)
                    elapsed = time.monotonic() - t_session
                    session_times.append(elapsed)

                    if result.strip():
                        store.update_digest(s["session_id"], result.strip())
                        digested += 1
                        total_output_words += _count_words(result)

                        if export_md:
                            cfg.digests_dir.mkdir(parents=True, exist_ok=True)
                            project = s.get("project", "general")
                            sid = s["session_id"][:8]
                            md_path = cfg.digests_dir / f"{project}_{sid}.md"
                            md_path.write_text(
                                f"# {s.get('title', '')}\n\n"
                                f"- **Session**: `{s['session_id']}`\n"
                                f"- **Project**: {project}\n\n"
                                f"---\n\n{result.strip()}\n",
                                encoding="utf-8",
                            )
                    else:
                        console.print(
                            f"  [yellow]Empty response for {s['session_id'][:8]}[/yellow]"
                        )
                        errors += 1
                except Exception as e:
                    elapsed = time.monotonic() - t_session
                    session_times.append(elapsed)
                    console.print(f"  [red]Error digesting {s['session_id'][:8]}: {e}[/red]")
                    errors += 1

                progress.advance(task)

        total_elapsed = time.monotonic() - t_start
        avg_time = sum(session_times) / len(session_times) if session_times else 0

        # Summary table
        console.print()
        table = Table(title="Digest summary", show_header=False, title_style="bold")
        table.add_column("Key", style="dim")
        table.add_column("Value")
        table.add_row("Model", cfg.digest_model)
        table.add_row("Digested", f"{digested} sessions")
        table.add_row("Errors", str(errors))
        table.add_row("Total time", f"{total_elapsed:.0f}s ({total_elapsed / 60:.1f} min)")
        table.add_row("Avg per session", f"{avg_time:.1f}s")
        if session_times:
            table.add_row(
                "Fastest / Slowest", f"{min(session_times):.1f}s / {max(session_times):.1f}s"
            )
        table.add_row("Input", f"{total_input_words:,} words ({total_input_chars / 1024:.0f} KB)")
        table.add_row("Output", f"{total_output_words:,} words")
        if total_input_words > 0:
            table.add_row("Compression", f"{total_input_words / max(total_output_words, 1):.0f}:1")
        console.print(table)
    finally:
        store.close()
