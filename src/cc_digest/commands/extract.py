"""cc-digest extract — read Claude Code JSONL transcripts and store sessions."""

from __future__ import annotations

import os
from dataclasses import replace
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

from cc_digest.cli import app

console = Console()


@app.command()
def extract(
    session: str = typer.Option(None, "--session", "-s", help="Process a single session UUID"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Show stats without writing"),
    min_messages: int = typer.Option(
        None, "--min-messages", "-m", help="Min messages to include (default from config)"
    ),
    export_md: bool = typer.Option(False, "--export-md", help="Also export .md files to sessions/"),
    backend: str = typer.Option(None, "--backend", "-b", help="Storage backend: sqlite or mongo"),
):
    """Extract sessions from Claude Code JSONL transcripts into storage."""
    from cc_digest.config import load_config
    from cc_digest.extractor import (
        find_all_jsonl,
        process_jsonl,
        session_to_document,
        session_to_markdown,
        infer_project,
        get_first_user_text,
        slugify,
    )

    cfg = load_config()
    if backend:
        cfg = replace(cfg, storage_backend=backend)
    if min_messages is not None:
        cfg = replace(cfg, min_messages=min_messages)

    all_jsonl = find_all_jsonl(cfg.claude_projects_dir)
    if session:
        all_jsonl = [j for j in all_jsonl if j["session_id"] == session]
        if not all_jsonl:
            console.print(f"[red]Session {session} not found[/red]")
            raise typer.Exit(1)

    console.print(f"Found [bold]{len(all_jsonl)}[/bold] session files")

    store = None
    if not dry_run:
        from cc_digest.backends import get_backend

        store = get_backend(cfg)

    try:
        inserted = 0
        updated = 0
        skipped = 0
        total_input_mb = 0.0

        for i, entry in enumerate(all_jsonl):
            filepath = entry["path"]
            file_mb = os.path.getsize(filepath) / 1024 / 1024
            total_input_mb += file_mb

            data = process_jsonl(filepath)

            if len(data["messages"]) < cfg.min_messages:
                skipped += 1
                continue

            first_msg_text = get_first_user_text(data["messages"]) if data["messages"] else ""
            project = infer_project(
                data.get("cwd", ""),
                first_msg_text,
                entry.get("project_dir", ""),
                cfg.project_roots,
            )
            doc = session_to_document(data, project)

            title_short = doc["title"][:50] + "..." if len(doc["title"]) > 50 else doc["title"]
            console.print(
                f"  [{i + 1}/{len(all_jsonl)}] {doc['session_id'][:8]}… "
                f"[dim]{project}[/dim] {len(data['messages'])} msgs — {title_short}"
            )

            if store:
                is_new = store.upsert_session(doc)
                if is_new:
                    inserted += 1
                else:
                    updated += 1

                if export_md:
                    cfg.sessions_dir.mkdir(parents=True, exist_ok=True)
                    title_slug = slugify(get_first_user_text(data["messages"]))
                    if data.get("first_ts"):
                        try:
                            dt = datetime.fromisoformat(data["first_ts"].replace("Z", "+00:00"))
                            prefix = dt.strftime("%Y-%m-%d_%H%M")
                        except (ValueError, TypeError):
                            prefix = "unknown-date"
                    else:
                        prefix = "unknown-date"
                    filename = f"{prefix}_{title_slug or 'session'}.md"
                    md_path = cfg.sessions_dir / filename
                    md_path.write_text(
                        session_to_markdown(doc, cfg.user_display_name), encoding="utf-8"
                    )
            else:
                inserted += 1  # count as "would insert" for dry-run

        # Summary
        console.print()
        table = Table(title="Extract summary", show_header=False, title_style="bold")
        table.add_column("Key", style="dim")
        table.add_column("Value")
        if dry_run:
            table.add_row("Mode", "[yellow]DRY RUN[/yellow]")
        table.add_row("Sessions found", str(len(all_jsonl)))
        table.add_row("Skipped (too few msgs)", str(skipped))
        if dry_run:
            table.add_row("Would process", str(inserted))
        else:
            table.add_row("Inserted", str(inserted))
            table.add_row("Updated", str(updated))
        table.add_row("Input size", f"{total_input_mb:.1f} MB")
        console.print(table)
    finally:
        if store:
            store.close()
