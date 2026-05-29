"""DKPlaylister CLI - Main entrypoint."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from dkplaylister import __version__
from dkplaylister.llm import get_provider
from dkplaylister.models import Playlist, StyleProfile, Curator, PlaylistSource, Platform

app = typer.Typer(
    name="dkplaylister",
    help="Mine high-value playlists. Generate powerful Grok-powered pitches from your actual lyrics and style.",
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
    """DKPlaylister — Style-driven playlist mining + Grok-powered personalized pitch generation."""
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


# =============================================================================
# Real Pitch Generation Command (first working high-value feature)
# =============================================================================

# Embedded test data from the user (Atmospheric cinematic indie rock/folk)
TEST_STYLE_PROMPT = """Atmospheric cinematic indie rock / indie folk, expansive soundstage with room to breathe, mid-tempo to slow ballad (72-95 BPM), deeply reverb-drenched shimmering jangly atmospheric guitars with delicate fingerpicked arpeggios that build into rich layered tones and tasteful overdriven textures, lush dripping reverb and long ethereal delays on everything, warm pulsing bass, heavy room mics for natural organic depth.
Deep resonant baritone male vocals with warm rich low chest voice, raw earnest delivery full of gentle cracks and yearning emotion that can rise into grounded belted passages and lush harmonies. Wide hazy cinematic mix, swirling atmospheric textures, production that starts intimate and vulnerable then slowly swells into emotional waves of catharsis and warmth.
Richly textured guitars blending clarity, shimmer, and subtle dissonance. Dynamic builds from hushed intimacy to soaring emotional release. High-fidelity warm production with excellent depth and separation."""

TEST_SONG_TITLE = "If I Get My Say"
TEST_LYRICS = """[Verse 1]
Gravel crunches under worn-out boots
Every wrong turn that led me back to truth
Bitter coffee gone cold on the counter
Morning light cuts the silence like a wound
Calloused fingers trace these same cracked lines
On this old wooden table stained with time
Carrying every quiet failure
Like dust that refuses to leave behind

[Verse 2]
Your photo still lingers on the bedside table
From the night our whole world fell apart
I keep it turned down but I know every detail
It pulls like a current on my heart
Love slipped away like smoke through the screen door
Left me breathing in silence and blue
Now the weight of all these almosts keeps calling
To the version of us that still feels true

[Chorus]
If I get my say
I’d speak every word I swallowed down that day
Lay these heavy chains right here on the floor
If I get my say
I’d choose you
I’d choose you like I never did before

[Verse 3]
Life pressed hard against these ribs like cold wind
Cutting straight through a coat too torn to mend
Taught me how pressure can reshape broken things
Turn the hurt into something strong again
I wore the rust of every almost like armor
That slowly started cracking at the seams
But something in the quiet keeps on whispering
This ache don’t have to be the end of the dream

[Bridge]
No more hallway ghosts, no more what-ifs in the dark
I’d set this armor down slow, let the real light find my heart
The tremble when our fingers finally meet again
One honest breath, watch the healing begin
No more running from the truth we both deserve

[Final Chorus]
If I get my say
I’d speak every truth I buried where the fear used to stay
Let the healing move gentle through the cracks where I went wrong
If I get my say
I’d choose you
Yeah, if I get my say
I’m coming home

[Outro]
If I get my say…
If I get my say…
Wouldn’t waste another night without you in my arms
If I get my say…
I’m coming home"""


@app.command()
def pitch(
    song_title: str = typer.Option(TEST_SONG_TITLE, "--song", "-s", help="Song title"),
    style: Optional[str] = typer.Option(None, "--style", help="Path to style prompt file (uses built-in test style if omitted)"),
    playlist_url: str = typer.Option(
        "https://open.spotify.com/playlist/57Oh6iT1OjceyZVrE95Cv6",
        "--playlist", "-p",
        help="Spotify playlist URL to target"
    ),
    playlist_name: str = typer.Option("FUTUREPROOF PICKS", "--playlist-name", help="Playlist name (for context)"),
    format: str = typer.Option("email", "--format", "-f", help="email | instagram_dm | submission_form"),
    model: str = typer.Option("grok-3", "--model", help="Grok model to use"),
    save: bool = typer.Option(False, "--save", help="Save the generated pitch to a file"),
):
    """Generate a personalized submission pitch using Grok + your Style + Lyrics.

    This is the first real high-value feature. It uses your detailed music description
    and actual song lyrics to create context-aware pitches.
    """
    if not os.getenv("XAI_API_KEY"):
        console.print(
            Panel.fit(
                "[bold red]XAI_API_KEY not found[/]\n\n"
                "Add it to your .env file to use Grok pitch generation.\n"
                "Get a key at https://console.x.ai/",
                title="Missing API Key",
                border_style="red",
            )
        )
        raise typer.Exit(1)

    # Load style
    if style and Path(style).exists():
        style_prompt = Path(style).read_text()
    else:
        style_prompt = TEST_STYLE_PROMPT
        console.print("[dim]Using built-in test style (Atmospheric cinematic indie rock/folk)[/]")

    style_profile = StyleProfile(raw_prompt=style_prompt.strip(), name="Current")

    # Minimal playlist object for context
    target_playlist = Playlist(
        platform=Platform.SPOTIFY,
        external_id="example",
        name=playlist_name,
        url=playlist_url,
        source=PlaylistSource.PLAYLISTER,
        description="Cinematic / atmospheric indie-focused playlist (example from development)",
    )

    console.print(Panel.fit("Generating pitch with Grok...", border_style="blue"))

    try:
        provider = get_provider("grok", model=model)
        generated = provider.generate_pitch(
            style_profile=style_profile,
            song_title=song_title,
            lyrics=TEST_LYRICS,
            playlist=target_playlist,
            pitch_format=format,
        )
    except Exception as e:
        console.print(f"[red]Error generating pitch:[/] {e}")
        raise typer.Exit(1)

    # Display
    console.print("\n" + "=" * 60)
    console.print(Panel(Markdown(generated), title=f"Generated Pitch — {song_title}", border_style="green"))
    console.print("=" * 60 + "\n")

    if save:
        out_path = Path(f"pitch_{song_title.lower().replace(' ', '_')}.txt")
        out_path.write_text(generated)
        console.print(f"[green]Saved to[/] {out_path}")


if __name__ == "__main__":
    app()
