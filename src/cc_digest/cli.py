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


@app.command()
def serve(
    transport: str = typer.Option("stdio", "--transport", "-t", help="MCP transport: stdio"),
):
    """Start the MCP server for Claude Code integration.

    Requires: pip install cc-digest[mcp]
    """
    try:
        from cc_digest.mcp_server import create_server
    except ImportError:
        console.print(
            "[red]FastMCP is required.[/red] Install with: "
            "[bold]pip install cc-digest\\[mcp][/bold]"
        )
        raise typer.Exit(1)

    import logging
    import sys

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logging.getLogger("cc_digest").addHandler(handler)
    logging.getLogger("cc_digest").setLevel(logging.INFO)

    server = create_server()
    server.run(transport=transport)


# Import subcommands — each registers itself on the app
from cc_digest.commands import extract, digest, search, stats  # noqa: E402, F401
