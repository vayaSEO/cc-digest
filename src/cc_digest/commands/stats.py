"""cc-digest stats — show summary statistics about stored sessions."""

from __future__ import annotations

from dataclasses import replace

import typer
from rich.console import Console
from rich.table import Table

from cc_digest.cli import app

console = Console()


@app.command()
def stats(
    project: str = typer.Option(None, "--project", "-p", help="Filter by project"),
    backend: str = typer.Option(None, "--backend", "-b", help="Storage backend"),
):
    """Show statistics about extracted sessions."""
    from cc_digest.config import load_config
    from cc_digest.backends import get_backend

    cfg = load_config()
    if backend:
        cfg = replace(cfg, storage_backend=backend)

    store = get_backend(cfg)
    try:
        total = store.count_sessions(project=project)
        if total == 0:
            console.print(
                "[yellow]No sessions found.[/yellow] Run [bold]cc-digest extract[/bold] first."
            )
            return

        sessions = store.list_sessions(project=project)

        # Compute stats
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

        # Main stats table
        table = Table(title="Session Statistics", show_header=False, title_style="bold")
        table.add_column("Key", style="bold")
        table.add_column("Value")
        table.add_row("Total sessions", str(total))
        table.add_row("Total messages", f"{total_messages:,}")
        table.add_row(
            "Digested",
            f"{with_digest}/{total} ({with_digest / total * 100:.0f}%)" if total else "0",
        )
        table.add_row(
            "Embedded",
            f"{with_embedding}/{total} ({with_embedding / total * 100:.0f}%)" if total else "0",
        )
        if earliest:
            table.add_row("Earliest session", earliest[:10])
        if latest:
            table.add_row("Latest session", latest[:10])
        table.add_row("Storage backend", cfg.storage_backend)
        console.print(table)

        # Projects breakdown
        if len(projects) > 1 or not project:
            console.print()
            proj_table = Table(title="Sessions by project", title_style="bold")
            proj_table.add_column("Project", style="cyan")
            proj_table.add_column("Sessions", justify="right")
            proj_table.add_column("% of total", justify="right")
            for proj_name in sorted(projects, key=projects.get, reverse=True):
                count = projects[proj_name]
                pct = count / total * 100
                proj_table.add_row(proj_name, str(count), f"{pct:.0f}%")
            console.print(proj_table)
    finally:
        store.close()
