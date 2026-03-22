"""CLI entry point — unified interface for cc-digest."""

import typer
from rich.console import Console

from cc_digest import __version__

app = typer.Typer(
    name="cc-digest",
    help="Extract, digest and search your Claude Code sessions.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"cc-digest {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True, help="Show version"
    ),
):
    """Extract, digest and search your Claude Code sessions with local LLMs."""
    pass


# Import subcommands — each registers itself on the app
from cc_digest.commands import extract, digest, search, stats  # noqa: E402, F401
