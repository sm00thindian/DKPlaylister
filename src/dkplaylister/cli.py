"""DKPlaylister CLI - Main entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from dkplaylister import __version__

app = typer.Typer(
    name="dkplaylister",
    help="Find playlists to submit your music to. Promote your tracks ethically and efficiently.",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print(f"DKPlaylister v{__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
):
    """DKPlaylister — Playlist discovery & submission tracking for independent musicians."""
    pass


@app.command()
def search(
    keywords: Optional[str] = typer.Option(
        None, "--keywords", "-k", help="Comma-separated keywords (e.g. submissions,accepting,demo)"
    ),
    genre: Optional[str] = typer.Option(
        None, "--genre", "-g", help="Target genre (lofi, hiphop, indie, etc.)"
    ),
    min_followers: int = typer.Option(
        500, "--min-followers", help="Minimum playlist followers"
    ),
    limit: int = typer.Option(20, "--limit", "-l", help="Max results to fetch"),
    platform: str = typer.Option("spotify", "--platform", help="spotify | youtube"),
):
    """Search for playlists accepting submissions (Phase 1: stub)."""
    console.print(
        Panel.fit(
            "[bold yellow]🚧 Search command is a stub in v0.1[/]\n\n"
            "Full Spotify API integration + curator extraction coming in the next milestone.\n"
            "For now, use this to explore the CLI structure.",
            title="DKPlaylister Search",
            border_style="yellow",
        )
    )

    # Placeholder table
    table = Table(title="Example Results (stub)")
    table.add_column("Playlist", style="cyan")
    table.add_column("Followers", justify="right")
    table.add_column("Contact?", style="green")
    table.add_row("lofi beats 2024", "124k", "email in desc")
    table.add_row("Chill Indie Picks", "67k", "IG @curator")
    console.print(table)
    console.print("\n[dim]Tip: Run [bold]dkplaylister init[/] to set up your local database.[/]")


@app.command()
def init(
    force: bool = typer.Option(False, "--force", help="Overwrite existing config/db"),
):
    """Initialize local database and config for DKPlaylister."""
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    db_path = data_dir / "dkplaylister.db"
    if db_path.exists() and not force:
        console.print(f"[yellow]Database already exists at {db_path}[/]")
        console.print("Use --force to reinitialize.")
        raise typer.Exit(1)

    # In future: run migrations
    db_path.touch()
    console.print(f"[green]✓[/] Initialized database at [bold]{db_path}[/]")
    console.print(
        "[dim]Next steps: copy .env.example → .env, add your Spotify credentials, "
        "then run [bold]dkplaylister auth spotify[/][/]"
    )


@app.command()
def auth(
    service: str = typer.Argument(..., help="Service to authenticate (spotify)"),
):
    """Authenticate with external services (Spotify, etc.)."""
    if service.lower() == "spotify":
        console.print(
            Panel(
                "Spotify OAuth flow will be implemented here using spotipy.\n\n"
                "1. Ensure SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are in your .env\n"
                "2. Run this command to open browser for authorization",
                title="Spotify Auth (stub)",
                border_style="blue",
            )
        )
    else:
        console.print(f"[red]Unknown service: {service}[/]")
        raise typer.Exit(1)


@app.command()
def export(
    format: str = typer.Option("csv", "--format", "-f", help="csv | excel | json"),
    status: Optional[str] = typer.Option(None, "--status", help="Filter by submission status"),
):
    """Export your playlist/submission data for campaigns."""
    console.print(f"[yellow]Export to {format} (stub) — coming soon.[/]")


@app.command()
def stats():
    """Show statistics on your outreach efforts."""
    table = Table(title="Your DKPlaylister Stats (stub)")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Playlists tracked", "0")
    table.add_row("Submissions sent", "0")
    table.add_row("Response rate", "—")
    console.print(table)


if __name__ == "__main__":
    app()
