"""DKPlaylister CLI - Main entrypoint."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import typer
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from dkplaylister import __version__

# Always load .env from the project root when running CLI commands
load_dotenv()
from dkplaylister.llm import get_provider
from dkplaylister.models import Playlist, StyleProfile, Curator, PlaylistSource, Platform
from dkplaylister.scoring import (
    PlaylistScorer,
    ScoringConfig,
    save_scoring_config,
    load_scoring_config,
    list_scoring_configs,
)
import spotipy
from dkplaylister.spotify import fetch_playlist, get_client, get_user_client, _handle_rate_limit
from dkplaylister.storage import (
    BandRepository,
    SongRepository,
    PlaylistRepository,
    StyleProfileRepository,
)
from dkplaylister.models import Band, Song


def _import_playlist(
    url: str,
    source: str = "playlister",
    query: Optional[str] = None,
    name: Optional[str] = None,
    score_it: bool = True,
    verbose: bool = True,
    band_id: Optional[int] = None,   # Scope style selection to this band's latest style
    # Option 2: Rich Playlister/manual contact capture
    curator_email: Optional[str] = None,
    curator_instagram: Optional[str] = None,
    curator_website: Optional[str] = None,
    contact_notes: Optional[str] = None,
    contact_revealed_via: Optional[str] = None,
) -> Optional[int]:
    """
    Core logic to import a single playlist.
    Returns the database ID if successful, None otherwise.
    """
    repo = PlaylistRepository()
    style_repo = StyleProfileRepository()

    if verbose:
        console.print(f"[dim]Fetching {url}...[/]")

    playlist = fetch_playlist(url)
    if not playlist:
        if verbose:
            console.print(f"[red]  ✗ Could not fetch playlist from Spotify[/]")
        return None

    if name:
        playlist.name = name

    try:
        playlist.source = PlaylistSource(source.lower())
    except ValueError:
        playlist.source = PlaylistSource.PLAYLISTER
    playlist.discovery_query = query

    # Option 2: Attach explicit contact info from Playlister popup / manual entry
    if any([curator_email, curator_instagram, curator_website, contact_notes, contact_revealed_via]):
        from dkplaylister.models import Curator
        existing_curator = playlist.curator or Curator()
        if curator_email:
            existing_curator.email = curator_email
        if curator_instagram:
            existing_curator.instagram = curator_instagram
        if curator_website:
            existing_curator.website = curator_website
        if contact_notes:
            existing_curator.notes = contact_notes
        playlist.curator = existing_curator

        if contact_revealed_via:
            playlist.contact_revealed_via = contact_revealed_via
        elif "playlister" in str(playlist.source).lower():
            playlist.contact_revealed_via = "playlister_popup"

    if score_it:
        style = style_repo.get_latest(band_id=band_id)
        if style:
            try:
                scorer = PlaylistScorer(style)
                scorer.score(playlist)
                if verbose:
                    console.print(f"[dim]  Scored: {playlist.current_score.total_value_score}/100[/]")
            except Exception as e:
                if verbose:
                    console.print(f"[yellow]  Warning: Could not score ({e})[/]")
        elif verbose:
            console.print("[dim]  No Style Profile found — skipping scoring.[/]")

    db_playlist = repo.create_or_update(playlist)
    return db_playlist.id

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
    force: bool = typer.Option(False, "--force", help="Re-run migrations even on existing DB (safe)"),
):
    """Initialize (or repair) local database and run Alembic migrations.

    Safe to run multiple times. Creates data/ dir and DB if missing, then
    ensures schema is at head via Alembic (with legacy fallback).
    """
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    db_path = data_dir / "dkplaylister.db"
    existed = db_path.exists()

    # Always touch + run migrations (idempotent)
    db_path.touch(exist_ok=True)

    from dkplaylister.storage import get_session
    get_session(db_path)

    console.print(f"[green]✓[/] Database ready at [bold]{db_path}[/] " + ("(existing)" if existed else "(new)"))

    # Basic env validation (P0-5)
    from dotenv import load_dotenv
    load_dotenv()
    xai = bool(os.getenv("XAI_API_KEY"))
    sp_id = bool(os.getenv("SPOTIFY_CLIENT_ID"))
    sp_secret = bool(os.getenv("SPOTIFY_CLIENT_SECRET"))

    console.print("\n[bold]Environment check:[/]")
    console.print(f"  XAI_API_KEY: {'✓ present' if xai else '[yellow]MISSING[/] (required for Grok pitches)'}")
    console.print(f"  SPOTIFY_CLIENT_ID: {'✓ present' if sp_id else '[yellow]MISSING[/]'}")
    console.print(f"  SPOTIFY_CLIENT_SECRET: {'✓ present' if sp_secret else '[yellow]MISSING[/]'}")

    if not (xai and sp_id and sp_secret):
        console.print("\n[dim]Tip: copy .env.example to .env and fill credentials.[/]")
    console.print(
        "[dim]Next: run [bold]dkplaylister auth spotify --status[/] or [bold]dkplaylister doctor[/] for full health.[/]"
    )


@app.command()
def doctor():
    """Health check: database, schema, data counts, credentials, and auth status.

    Run this after init or when things feel off. Non-destructive.
    """
    console.print(Panel.fit("DKPlaylister Doctor — Phase 0 + Phase 1 Health Check", border_style="cyan"))

    # 1. DB + basic counts
    data_dir = Path("data")
    db_path = data_dir / "dkplaylister.db"
    db_ok = db_path.exists()

    console.print(f"\n[bold]Database:[/] {db_path} — {'✓ exists' if db_ok else '[red]MISSING[/]'}")

    if not db_ok:
        console.print("[yellow]Run `dkplaylister init` first.[/]")
        raise typer.Exit(1)

    try:
        from dkplaylister.storage import (
            get_session, BandRepository, StyleProfileRepository, SongRepository,
            AlbumRepository, PlaylistRepository, PitchRepository, SubmissionRepository
        )
        # Force a session (runs migrations if needed)
        get_session(db_path)
        band_repo = BandRepository()
        style_repo = StyleProfileRepository()
        song_repo = SongRepository()
        album_repo = AlbumRepository()
        pl_repo = PlaylistRepository()
        pitch_repo = PitchRepository()
        sub_repo = SubmissionRepository()

        bands = band_repo.list_all()
        default_band = band_repo.get_default()

        console.print(f"  Bands: {len(bands)}  (default: {default_band.name if default_band else 'none'})")
        for b in bands[:5]:
            styles = style_repo.list_all(band_id=b.id)
            songs = song_repo.list_by_band(b.id)
            console.print(f"    • {b.name} (ID {b.id}): {len(styles)} styles, {len(songs)} songs")

        targets = pl_repo.count()
        pitches = len(pitch_repo.list_by_band(bands[0].id)) if bands else 0  # sample one band
        console.print(f"  Playlist targets (global): {targets}")
        console.print(f"  Pitches (sample band): {pitches}")

        # Phase 1: Mining stats (H1)
        try:
            from dkplaylister.storage import MiningRunRepository
            mining_repo = MiningRunRepository()
            recent_mines = mining_repo.list_recent(5)
            console.print(f"  Mining Runs (recent): {len(recent_mines)}")
            if recent_mines:
                last = recent_mines[0]
                console.print(f"    Last: {last.style_profile_name or last.style_profile_id} → {last.playlists_found} found")
        except Exception:
            pass

    except Exception as e:
        console.print(f"[red]DB access error: {e}[/]")
        console.print("[dim]Try `dkplaylister init --force` or check alembic setup.[/]")

    # 2. Env
    from dotenv import load_dotenv
    load_dotenv()
    console.print("\n[bold]Environment (.env):[/]")
    checks = {
        "XAI_API_KEY": os.getenv("XAI_API_KEY"),
        "SPOTIFY_CLIENT_ID": os.getenv("SPOTIFY_CLIENT_ID"),
        "SPOTIFY_CLIENT_SECRET": os.getenv("SPOTIFY_CLIENT_SECRET"),
        "SPOTIFY_REDIRECT_URI": os.getenv("SPOTIFY_REDIRECT_URI"),
    }
    for k, v in checks.items():
        status = "✓" if v else "[yellow]MISSING[/]"
        console.print(f"  {k}: {status}")

    # 3. Spotify auth status (lightweight, no browser)
    console.print("\n[bold]Spotify Auth:[/]")
    try:
        from spotipy.oauth2 import SpotifyOAuth
        cache_path = Path.home() / ".cache" / "spotipy_token_cache.json"  # default spotipy location
        # Try common cache names used by the project
        candidates = [
            Path(".spotipy_cache"),
            Path.home() / ".cache" / "spotipy" / "token_cache.json",
            Path(os.getenv("SPOTIPY_CACHE_PATH", "")) if os.getenv("SPOTIPY_CACHE_PATH") else None,
        ]
        token_found = False
        for c in [p for p in candidates if p]:
            if c and c.exists():
                token_found = True
                console.print(f"  Token cache: ✓ found at {c}")
                break
        if not token_found:
            console.print("  Token cache: [yellow]none found[/]")
            console.print("  [dim]Run: dkplaylister auth spotify[/]")

        # Quick validation if we can
        if os.getenv("SPOTIFY_CLIENT_ID"):
            auth_manager = SpotifyOAuth(
                client_id=os.getenv("SPOTIFY_CLIENT_ID"),
                client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
                redirect_uri=os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback"),
                cache_path=str(Path(".spotipy_cache")),
                scope="user-read-private user-read-email user-top-read",
            )
            token = auth_manager.get_cached_token()
            if token and not auth_manager.is_token_expired(token):
                console.print("  Cached token: ✓ valid (not expired)")
            elif token:
                console.print("  Cached token: [yellow]expired (will refresh on use)[/]")
            else:
                console.print("  Cached token: [yellow]none or invalid[/]")
    except Exception as e:
        console.print(f"  [dim]Auth probe skipped ({e})[/]")

    # 4. Recommendations
    console.print("\n[bold]Recommendations:[/]")
    if not bands:
        console.print("  • Create your first band: sidebar in UI or `dkplaylister band create ...` (CLI)")
    if targets == 0:
        console.print("  • Import targets: `dkplaylister add <url>` or use Streamlit 'Process Playlister Imports'")
    console.print("  • Full UI: `streamlit run ui/streamlit_app.py`")
    console.print("  • Re-check after fixes: `dkplaylister doctor`")
    console.print(Panel.fit("Phase 0 foundation looks healthy when you see bands + styles + songs + scored targets.", border_style="green"))


@app.command()
def auth(
    service: str = typer.Argument(..., help="Service to authenticate (spotify)"),
    scopes: str = typer.Option(
        "user-read-private user-read-email user-top-read",
        "--scopes",
        "-s",
        help="Space-separated list of Spotify scopes to request",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force re-authentication even if a valid token exists"
    ),
    status: bool = typer.Option(
        False, "--status", help="Check current authentication status without opening browser"
    ),
):
    """
    Authenticate with Spotify using the Authorization Code Flow.

    This opens a browser window where you can log in and grant the requested permissions.
    Your tokens are cached locally (in .spotify_cache by default) so you don't have to
    log in every time.
    """
    if service.lower() != "spotify":
        console.print(f"[red]Unknown service: {service}[/]")
        raise typer.Exit(1)

    if status:
        _show_spotify_auth_status()
        return

    console.print("[bold]Starting Spotify Authorization Code Flow...[/]")

    requested_scopes = scopes.split() if scopes else None

    try:
        # This will open the browser if no valid cached token exists
        sp = get_user_client(scopes=requested_scopes, open_browser=True)

        # Force token refresh if --force was used
        if force:
            sp.auth_manager.get_access_token(as_dict=False)

        # Verify we can actually talk to the API
        user = sp.current_user()
        display_name = user.get("display_name") or user.get("id")
        email = user.get("email", "hidden (no user-read-email scope)")

        console.print(
            Panel.fit(
                f"[green]✓ Successfully authenticated with Spotify![/]\n\n"
                f"User: [bold]{display_name}[/]\n"
                f"Email: {email}\n"
                f"User ID: {user.get('id')}\n"
                f"Requested scopes: {scopes or '(none)'}",
                title="Spotify Authentication Successful",
                border_style="green",
            )
        )

    except Exception as e:
        console.print(
            Panel(
                f"[red]Authentication failed:[/]\n\n{str(e)}\n\n"
                "Common issues:\n"
                "• SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET not set in .env\n"
                "• Redirect URI in your Spotify app settings doesn't match SPOTIFY_REDIRECT_URI\n"
                "• Browser popup was blocked",
                title="Spotify Auth Error",
                border_style="red",
            )
        )
        raise typer.Exit(1)


def _show_spotify_auth_status():
    """Check and display current Spotify auth status without triggering login."""
    from spotipy.oauth2 import SpotifyOAuth

    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
    cache_path = os.getenv("SPOTIFY_CACHE_PATH", ".spotify_cache")

    if not client_id or not client_secret:
        console.print("[red]SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET are not set.[/]")
        return

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        cache_path=cache_path,
    )

    token_info = auth_manager.get_cached_token()

    if not token_info:
        console.print("[yellow]No Spotify token found in cache.[/]")
        console.print("Run [bold]dkplaylister auth spotify[/] to log in.")
        return

    # Check if token is still valid
    if auth_manager.is_token_expired(token_info):
        console.print("[yellow]Cached token exists but is expired.[/]")
        console.print("Run [bold]dkplaylister auth spotify[/] to refresh.")
        return

    try:
        sp = spotipy.Spotify(auth_manager=auth_manager)
        user = sp.current_user()
        display_name = user.get("display_name") or user.get("id")

        console.print(
            Panel.fit(
                f"[green]✓ Spotify authentication is active[/]\n\n"
                f"User: [bold]{display_name}[/]\n"
                f"User ID: {user.get('id')}\n"
                f"Token expires in: {token_info.get('expires_in', 'unknown')} seconds",
                title="Spotify Auth Status",
                border_style="green",
            )
        )
    except Exception as e:
        console.print(f"[red]Token exists but appears invalid:[/] {e}")


@app.command()
def export(
    format: str = typer.Option("csv", "--format", "-f", help="csv | excel | json"),
    min_score: Optional[float] = typer.Option(None, "--min-score", help="Only export targets above this score"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path (defaults based on format)"),
):
    """Export your current playlist targets (with scores) for review or campaigns."""
    from dkplaylister.utils import export_to_excel

    repo = PlaylistRepository()
    targets = repo.list_all(min_score=min_score)

    if not targets:
        console.print("[yellow]No targets to export.[/]")
        raise typer.Exit(1)

    # Prepare simple rows for export
    rows = []
    for t in targets:
        score = t.current_score.total_value_score if t.current_score else None
        rows.append({
            "id": t.id,
            "name": t.name,
            "url": str(t.url),
            "followers": t.follower_count,
            "score": score,
            "source": t.source.value,
            "discovery_query": t.discovery_query or "",
            "notes": t.notes or "",
        })

    if output is None:
        ext = "xlsx" if format == "excel" else format
        output = Path(f"dkplaylister_targets.{ext}")

    if format == "excel":
        export_to_excel(rows, output)
    elif format == "csv":
        import pandas as pd
        pd.DataFrame(rows).to_csv(output, index=False)
    elif format == "json":
        import json
        output.write_text(json.dumps(rows, indent=2, default=str))
    else:
        console.print(f"[red]Unsupported format: {format}[/]")
        raise typer.Exit(1)

    console.print(f"[green]✓ Exported {len(rows)} targets to {output}[/]")


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
# Style Profile Commands
# =============================================================================

style_app = typer.Typer(help="Manage your music Style Profiles (the foundation of DKPlaylister)")
app.add_typer(style_app, name="style")


@style_app.command("set")
def style_set(
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="Path to a text file containing your style prompt"),
    name: str = typer.Option("Default", "--name", "-n", help="Name for this style profile"),
    band_id: Optional[int] = typer.Option(None, "--band", help="Band this style belongs to"),
    stdin: bool = typer.Option(False, "--stdin", help="Read style prompt from standard input"),
):
    """Save a new Style Profile from a file or stdin.

    This is the most important command — your detailed music description powers
    discovery, scoring, and high-quality pitch generation.
    """
    repo = StyleProfileRepository()
    band_repo = BandRepository()

    if file:
        if not file.exists():
            console.print(f"[red]File not found:[/] {file}")
            raise typer.Exit(1)
        raw_prompt = file.read_text().strip()
    elif stdin:
        console.print("[dim]Paste your style description below. Press Ctrl+D (Unix) or Ctrl+Z (Windows) when done.[/]")
        raw_prompt = sys.stdin.read().strip()
    else:
        console.print("[yellow]Please provide either --file or --stdin[/]")
        raise typer.Exit(1)

    if not raw_prompt:
        console.print("[red]Style prompt cannot be empty.[/]")
        raise typer.Exit(1)

    # If no band provided, try to use default band
    if band_id is None:
        default_band = band_repo.get_default()
        if default_band:
            band_id = default_band.id
            console.print(f"[dim]Using default band: {default_band.name} (ID {band_id})[/]")

    profile = StyleProfile(raw_prompt=raw_prompt, name=name, band_id=band_id)
    db_profile = repo.create(profile)

    console.print(
        Panel.fit(
            f"[green]✓[/] Style Profile saved (ID: {db_profile.id})\n"
            f"Name: {db_profile.name}\n"
            f"Band ID: {db_profile.band_id or 'None (global)'}\n"
            f"Length: {len(raw_prompt)} characters",
            title="Style Profile Created",
            border_style="green",
        )
    )


@style_app.command("show")
def style_show(
    profile_id: Optional[int] = typer.Argument(None, help="Style Profile ID (shows latest if omitted)"),
    band_id: Optional[int] = typer.Option(None, "--band", help="Show latest for this band"),
):
    """Display a saved Style Profile."""
    repo = StyleProfileRepository()

    if profile_id:
        profile = repo.get_by_id(profile_id)
    else:
        profile = repo.get_latest(band_id=band_id)

    if not profile:
        console.print("[yellow]No Style Profiles found. Use [bold]dkplaylister style set[/] first.[/]")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold]ID:[/] {profile.id}\n"
        f"[bold]Band ID:[/] {profile.band_id or '— (global)'}\n"
        f"[bold]Name:[/] {profile.name}\n"
        f"[bold]Version:[/] {profile.version}\n"
        f"[bold]Updated:[/] {profile.updated_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"{profile.raw_prompt}",
        title=f"Style Profile #{profile.id}",
        border_style="cyan"
    ))


@style_app.command("list")
def style_list(band_id: Optional[int] = typer.Option(None, "--band", help="Filter by band ID")):
    """List saved Style Profiles (optionally for a specific band)."""
    repo = StyleProfileRepository()
    profiles = repo.list_all(band_id=band_id)

    if not profiles:
        console.print("[yellow]No Style Profiles found for the given criteria.[/]")
        return

    title = f"Style Profiles for Band {band_id}" if band_id else "Your Style Profiles"
    table = Table(title=title)
    table.add_column("ID", style="cyan", justify="right")
    table.add_column("Band", justify="right")
    table.add_column("Name")
    table.add_column("Updated", style="dim")
    table.add_column("Prompt Length", justify="right")

    for p in profiles:
        table.add_row(
            str(p.id),
            str(p.band_id) if p.band_id else "—",
            p.name,
            p.updated_at.strftime("%Y-%m-%d %H:%M"),
            f"{len(p.raw_prompt)} chars",
        )

    console.print(table)


@style_app.command("expand")
def style_expand(
    style_id: Optional[int] = typer.Option(None, "--style-id", help="Specific Style Profile ID"),
    band_id: Optional[int] = typer.Option(None, "--band", help="Use latest style for this band"),
    use_latest: bool = typer.Option(True, "--latest/--no-latest", help="Use the most recent style for the band"),
):
    """(Phase 1) Expand a Style Profile into discovery queries, genres, and search terms using Grok.

    This is the foundation for intelligent mining. The output can later feed the `mine` command.
    """
    from dkplaylister.llm import get_provider

    repo = StyleProfileRepository()

    if style_id:
        style = repo.get_by_id(style_id)
    else:
        style = repo.get_latest(band_id=band_id)

    if not style:
        console.print("[red]No Style Profile found. Use --style-id or make sure you have a saved style.[/]")
        raise typer.Exit(1)

    console.print(f"[bold]Expanding style:[/] {style.name} (ID {style.id})")

    try:
        provider = get_provider("grok")
        expansion = provider.expand_style_for_discovery(style)

        console.print(Panel.fit(
            f"[bold]Primary Genres:[/] {', '.join(expansion.primary_genres) or '—'}\n"
            f"[bold]Sub-genres:[/] {', '.join(expansion.sub_genres) or '—'}\n"
            f"[bold]Moods:[/] {', '.join(expansion.moods) or '—'}\n"
            f"[bold]Similar Artists:[/] {', '.join(expansion.similar_artists) or '—'}",
            title="Discovery Profile",
            border_style="cyan"
        ))

        if expansion.search_queries:
            console.print("\n[bold]Recommended Search Queries:[/]")
            for q in expansion.search_queries:
                console.print(f"  • {q}")

        if expansion.explanation:
            console.print(f"\n[dim]{expansion.explanation}[/]")

    except Exception as e:
        console.print(f"[red]Expansion failed: {e}[/]")


# =============================================================================
# Scoring Config Management
# =============================================================================

scoring_app = typer.Typer(help="Manage saved scoring weight profiles")
app.add_typer(scoring_app, name="scoring")


@scoring_app.command("save")
def scoring_save(
    name: str = typer.Argument(..., help="Name for this scoring profile"),
    fit: float = typer.Option(0.30, "--fit", help="Weight for style fit"),
    activity: float = typer.Option(0.25, "--activity", help="Weight for playlist activity"),
    openness: float = typer.Option(0.15, "--openness"),
    followers: float = typer.Option(0.12, "--followers"),
    contact: float = typer.Option(0.10, "--contact"),
):
    """Save a custom scoring weight profile."""
    cfg = ScoringConfig(
        weight_fit=fit,
        weight_activity=activity,
        weight_openness=openness,
        weight_followers=followers,
        weight_contact=contact,
    )
    path = save_scoring_config(name, cfg)
    console.print(f"[green]✓[/] Saved scoring profile '{name}' to {path}")


@scoring_app.command("list")
def scoring_list():
    """List saved scoring profiles."""
    names = list_scoring_configs()
    if not names:
        console.print("[yellow]No saved scoring profiles yet.[/]")
        return
    for n in names:
        console.print(f"• {n}")


@scoring_app.command("show")
def scoring_show(name: str):
    """Show details of a saved scoring profile."""
    try:
        cfg = load_scoring_config(name)
        console.print(Panel(str(cfg), title=f"Scoring Profile: {name}"))
    except FileNotFoundError:
        console.print(f"[red]Profile '{name}' not found.[/]")


# =============================================================================
# Band Management (Phase 1 of Data Model v2)
# =============================================================================

band_app = typer.Typer(help="Manage bands/artists")
app.add_typer(band_app, name="band")


@band_app.command("create")
def band_create(
    name: str = typer.Argument(..., help="Band/artist name"),
    slug: Optional[str] = typer.Option(None, "--slug", help="URL/folder friendly slug (auto-generated if omitted)"),
    notes: Optional[str] = typer.Option(None, "--notes", help="Optional notes"),
):
    """Create a new band."""
    repo = BandRepository()

    if slug is None:
        slug = name.lower().replace(" ", "-").replace("_", "-")

    # Check for duplicate slug
    existing = repo.get_by_slug(slug)
    if existing:
        console.print(f"[red]A band with slug '{slug}' already exists (ID {existing.id}).[/]")
        raise typer.Exit(1)

    band = Band(name=name, slug=slug, notes=notes)
    db_band = repo.create(band)

    console.print(
        Panel.fit(
            f"[green]✓[/] Band created (ID: {db_band.id})\n"
            f"Name: {db_band.name}\n"
            f"Slug: {db_band.slug}",
            title="Band Created",
            border_style="green",
        )
    )


@band_app.command("list")
def band_list():
    """List all bands."""
    repo = BandRepository()
    bands = repo.list_all()

    if not bands:
        console.print("[yellow]No bands found. Create one with [bold]dkplaylister band create[/].[/]")
        return

    table = Table(title="Bands")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Name")
    table.add_column("Slug")
    table.add_column("Notes")

    for b in bands:
        table.add_row(str(b.id), b.name, b.slug, (b.notes or "")[:50])

    console.print(table)


@band_app.command("show")
def band_show(band_id: int = typer.Argument(..., help="Band ID")):
    """Show details for a specific band."""
    repo = BandRepository()
    band = repo.get_by_id(band_id)

    if not band:
        console.print(f"[red]Band {band_id} not found.[/]")
        raise typer.Exit(1)

    console.print(Panel(
        f"**Name:** {band.name}\n"
        f"**Slug:** {band.slug}\n"
        f"**Notes:** {band.notes or '—'}\n"
        f"**Created:** {band.created_at.strftime('%Y-%m-%d')}",
        title=f"Band #{band.id}",
        border_style="cyan",
    ))


@band_app.command("set-default")
def band_set_default(band_id: int = typer.Argument(..., help="Band ID to set as default")):
    """Set a band as the default for commands that don't specify --band."""
    repo = BandRepository()
    success = repo.set_default(band_id)

    if success:
        console.print(f"[green]✓[/] Band {band_id} is now the default.")
    else:
        console.print(f"[red]Band {band_id} not found.[/]")
        raise typer.Exit(1)


# =============================================================================
# Song / Lyrics Management (Phase 1 of Data Model v2)
# =============================================================================

song_app = typer.Typer(help="Manage songs and lyrics per band")
app.add_typer(song_app, name="song")


@song_app.command("add")
def song_add(
    band_id: int = typer.Option(..., "--band", help="Band ID"),
    title: str = typer.Option(..., "--title", "-t", help="Song title"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File containing lyrics"),
    notes: Optional[str] = typer.Option(None, "--notes", help="Optional notes"),
):
    """Add a new song with lyrics to a band."""
    repo = SongRepository()

    if file:
        if not file.exists():
            console.print(f"[red]File not found: {file}[/]")
            raise typer.Exit(1)
        lyrics = file.read_text()
    else:
        console.print("[dim]Enter lyrics (end with Ctrl+D or Ctrl+Z):[/]")
        lyrics = sys.stdin.read().strip()

    if not lyrics:
        console.print("[red]Lyrics cannot be empty.[/]")
        raise typer.Exit(1)

    song = Song(band_id=band_id, title=title, lyrics=lyrics, notes=notes)
    db_song = repo.create(song)

    console.print(
        Panel.fit(
            f"[green]✓[/] Song added (ID: {db_song.id})\n"
            f"Title: {db_song.title}\n"
            f"Band ID: {db_song.band_id}\n"
            f"Lyrics length: {len(lyrics)} chars",
            title="Song Added",
            border_style="green",
        )
    )


@song_app.command("list")
def song_list(band_id: int = typer.Option(..., "--band", help="Band ID")):
    """List songs for a band."""
    repo = SongRepository()
    songs = repo.list_by_band(band_id)

    if not songs:
        console.print(f"[yellow]No songs found for band {band_id}.[/]")
        return

    table = Table(title=f"Songs for Band {band_id}")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Title")
    table.add_column("Lyrics Length")
    table.add_column("Notes")

    for s in songs:
        table.add_row(
            str(s.id),
            s.title,
            str(len(s.lyrics)),
            (s.notes or "")[:40],
        )

    console.print(table)


@song_app.command("show")
def song_show(song_id: int = typer.Argument(..., help="Song ID")):
    """Show a song with its lyrics."""
    repo = SongRepository()
    song = repo.get_by_id(song_id)

    if not song:
        console.print(f"[red]Song {song_id} not found.[/]")
        raise typer.Exit(1)

    console.print(Panel(
        f"**Title:** {song.title}\n"
        f"**Band ID:** {song.band_id}\n"
        f"**Notes:** {song.notes or '—'}\n\n"
        f"**Lyrics:**\n{song.lyrics}",
        title=f"Song #{song.id}",
        border_style="cyan",
    ))


# =============================================================================
# Database / Migration Helpers (Phase 0)
# =============================================================================

db_app = typer.Typer(help="Database and migration utilities (Phase 0)")
app.add_typer(db_app, name="db")


@db_app.command("migrate-legacy-styles")
def db_migrate_legacy_styles(band_id: Optional[int] = typer.Option(None, "--band", help="Target band ID (creates default if omitted)")):
    """Assign existing styles that have no band to a band (Phase 0 migration)."""
    band_repo = BandRepository()
    style_repo = StyleProfileRepository()

    if band_id is None:
        default_band = band_repo.get_or_create_default()
        band_id = default_band.id
        console.print(f"[dim]Using/created default band: {default_band.name} (ID {band_id})[/]")

    count = style_repo.migrate_legacy_styles_to_band(band_id)
    console.print(f"[green]✓[/] Migrated {count} legacy styles to band {band_id}.")


@db_app.command("clear-targets")
def db_clear_targets(
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip interactive confirmation"),
):
    """Permanently delete ALL saved playlist targets (the scored Playlister/Spotify results).

    This is useful when you want a completely fresh set of targets scored against
    your current style and songs (e.g. after refining your style prompt or adding new songs).
    """
    repo = PlaylistRepository()
    current_count = repo.count()

    if current_count == 0:
        console.print("[yellow]No playlist targets to clear.[/]")
        return

    if not yes:
        console.print(f"[bold red]WARNING:[/] This will permanently delete all {current_count} playlist targets.")
        console.print("This action cannot be undone (though you can always re-import from Playlister).")
        if not typer.confirm("Are you sure you want to proceed?"):
            console.print("Aborted.")
            raise typer.Exit()

    deleted = repo.clear_all()
    console.print(f"[green]✓ Cleared {deleted} playlist targets.[/]")
    console.print("[dim]You can now re-import fresh results from Playlister using `add` or `import`.[/]")


# =============================================================================
# Mining / Ingestion Commands (Semi-automatic flow)
# =============================================================================

@app.command()
def add(
    url: str = typer.Argument(..., help="Spotify playlist URL"),
    source: str = typer.Option("playlister", "--source", help="playlister | spotify | manual"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="The search term used on Playlister (for provenance)"),
    name: Optional[str] = typer.Option(None, "--name", help="Override playlist name"),
    score_it: bool = typer.Option(True, "--score/--no-score", help="Automatically score against latest StyleProfile"),
    band_id: Optional[int] = typer.Option(None, "--band", help="Band ID to scope style lookup for scoring"),
    # Option 2: Capture contact details shown in DistroKid Playlister popup (highly recommended)
    curator_email: Optional[str] = typer.Option(None, "--curator-email", help="Email from Playlister popup"),
    curator_instagram: Optional[str] = typer.Option(None, "--curator-instagram", help="IG handle from Playlister popup"),
    curator_website: Optional[str] = typer.Option(None, "--curator-website", "--contact-url", help="bit.ly / form / website from Playlister popup"),
    contact_notes: Optional[str] = typer.Option(None, "--contact-notes", help="Any extra notes about contacting this curator"),
    contact_revealed_via: Optional[str] = typer.Option(None, "--contact-via", help="playlister_popup | description | manual"),
):
    """Add a single playlist (typically from Playlister) into your targets database.

    For importing many playlists at once, use `dkplaylister import` instead.

    Use the --curator-* flags when you have the popup details from Playlister.
    This captures the actual contact method the curator chose to share.
    """
    playlist_id = _import_playlist(
        url=url,
        source=source,
        query=query,
        name=name,
        score_it=score_it,
        verbose=True,
        band_id=band_id,
        curator_email=curator_email,
        curator_instagram=curator_instagram,
        curator_website=curator_website,
        contact_notes=contact_notes,
        contact_revealed_via=contact_revealed_via,
    )

    if playlist_id is None:
        raise typer.Exit(1)

    # Re-fetch for nice output
    repo = PlaylistRepository()
    playlist = repo.get_by_id(playlist_id)

    console.print(
        Panel.fit(
            f"[green]✓[/] Added/updated playlist (ID: {playlist_id})\n"
            f"Name: {playlist.name}\n"
            f"Followers: {playlist.follower_count or 'N/A'}\n"
            f"Source: {source} | Query: {query or 'N/A'}",
            title="Playlist Added",
            border_style="green",
        )
    )


@app.command("import")
def import_playlists(
    urls: list[str] = typer.Argument(None, help="One or more Spotify playlist URLs"),
    file: Optional[Path] = typer.Option(None, "--file", "-f", help="File containing one Spotify URL per line"),
    source: str = typer.Option("playlister", "--source", help="playlister | spotify | manual"),
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Playlister search term (applied to all imported playlists)"),
    score_it: bool = typer.Option(True, "--score/--no-score", help="Score all imported playlists"),
    band_id: Optional[int] = typer.Option(None, "--band", help="Band ID to scope style lookup for scoring (uses default band if omitted)"),
    # Option 2: Same rich contact flags available for bulk (applied to every URL in the batch)
    curator_email: Optional[str] = typer.Option(None, "--curator-email", help="Email from Playlister popup (applied to all)"),
    curator_instagram: Optional[str] = typer.Option(None, "--curator-instagram", help="IG handle from Playlister popup (applied to all)"),
    curator_website: Optional[str] = typer.Option(None, "--curator-website", "--contact-url", help="bit.ly/form/website (applied to all)"),
    contact_notes: Optional[str] = typer.Option(None, "--contact-notes", help="Notes (applied to all in batch)"),
    contact_revealed_via: Optional[str] = typer.Option("playlister_popup", "--contact-via", help="playlister_popup | description | manual"),
):
    """
    Bulk import playlists (ideal for results from Playlister.com).

    You can pass URLs directly or use --file with a text file (one URL per line).

    When importing from Playlister, use the --curator-* flags (or --contact-via)
    to record the actual contact method shown in the Playlister popup for every item.

    Examples:
      dkplaylister import https://open.spotify.com/playlist/xxx --query "Indie Cinematic"
      dkplaylister import --file my-playlister-results.txt --query "Cinematic" --curator-email foo@bar.com
    """
    all_urls: list[str] = []

    if file:
        if not file.exists():
            console.print(f"[red]File not found: {file}[/]")
            raise typer.Exit(1)
        all_urls.extend([line.strip() for line in file.read_text().splitlines() if line.strip() and not line.strip().startswith("#")])

    if urls:
        all_urls.extend(urls)

    if not all_urls:
        console.print("[yellow]No URLs provided. Use positional arguments or --file.[/]")
        raise typer.Exit(1)

    console.print(f"[bold]Importing {len(all_urls)} playlist(s)...[/]\n")

    success = 0
    failed = 0
    skipped = 0

    for i, url in enumerate(all_urls, 1):
        console.print(f"[{i}/{len(all_urls)}] {url}")

        # Check for duplicates early
        repo = PlaylistRepository()
        # Simple check - we can improve later
        existing = [p for p in repo.list_all() if str(p.url) == url]
        if existing:
            console.print("  [dim]→ Already in database, skipping[/]")
            skipped += 1
            continue

        playlist_id = _import_playlist(
            url=url,
            source=source,
            query=query,
            score_it=score_it,
            verbose=False,
            band_id=band_id,
            curator_email=curator_email,
            curator_instagram=curator_instagram,
            curator_website=curator_website,
            contact_notes=contact_notes,
            contact_revealed_via=contact_revealed_via,
        )

        if playlist_id:
            success += 1
            console.print(f"  [green]✓ Imported (ID: {playlist_id})[/]")
        else:
            failed += 1
            console.print("  [red]✗ Failed[/]")

    console.print("\n" + "=" * 50)
    console.print(f"[bold]Import complete[/]")
    console.print(f"  Success: {success}")
    console.print(f"  Failed:  {failed}")
    console.print(f"  Skipped (duplicates): {skipped}")


@app.command("targets")
def targets_list(
    min_score: Optional[float] = typer.Option(None, "--min-score", help="Only show playlists above this score"),
    limit: int = typer.Option(20, "--limit", "-l"),
):
    """List your saved playlist targets, sorted by value."""
    repo = PlaylistRepository()
    targets = repo.list_all(min_score=min_score)[:limit]

    if not targets:
        console.print("[yellow]No targets found. Use [bold]dkplaylister import[/] or [bold]add[/] to bring in playlists from Playlister.[/]")
        return

    table = Table(title=f"Your Targets (showing {len(targets)})")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Name")
    table.add_column("Score", justify="right")
    table.add_column("Followers", justify="right")
    table.add_column("Contact")
    table.add_column("Source / Query")

    for t in targets:
        score_str = f"{t.current_score.total_value_score:.0f}" if t.current_score else "—"
        source_str = t.source.value
        if t.discovery_query:
            source_str += f" ({t.discovery_query})"

        contact_str = t.contact_summary
        if t.has_contact_info:
            contact_str = f"[green]{contact_str}[/]"
        else:
            contact_str = f"[dim]{contact_str}[/]"

        table.add_row(
            str(t.id),
            t.name[:40] + ("..." if len(t.name) > 40 else ""),
            score_str,
            f"{t.follower_count:,}" if t.follower_count else "—",
            contact_str,
            source_str,
        )

    console.print(table)


# =============================================================================
# Scoring Command
# =============================================================================

@app.command()
def score(
    playlist_url: str = typer.Argument(..., help="Spotify playlist URL to score"),
    playlist_name: Optional[str] = typer.Option(None, "--name", "-n", help="Playlist name (optional but helpful)"),
    style_id: Optional[int] = typer.Option(None, "--style-id", help="Specific Style Profile ID"),
    band_id: Optional[int] = typer.Option(None, "--band", help="Band ID to scope the style lookup"),
    use_latest: bool = typer.Option(True, "--latest/--no-latest", help="Use latest saved Style Profile"),
    show_breakdown: bool = typer.Option(True, "--breakdown/--no-breakdown", help="Show detailed score breakdown"),
    # Quick weight overrides for experimentation
    fit_weight: Optional[float] = typer.Option(None, "--fit-weight", help="Override fit weight (0.0-1.0)"),
    activity_weight: Optional[float] = typer.Option(None, "--activity-weight", help="Override activity weight"),
):
    """Score a playlist against your Style Profile using the new prioritization engine.

    This is the core intelligence of DKPlaylister — it tells you how valuable a
    playlist is likely to be *for your specific music*.
    """
    repo = StyleProfileRepository()

    # Get style
    if style_id:
        style = repo.get_by_id(style_id)
    else:
        style = repo.get_latest(band_id=band_id)

    if not style:
        console.print("[red]No Style Profile found. Run [bold]dkplaylister style set[/] first.[/]")
        raise typer.Exit(1)

    # Create minimal Playlist object
    target = Playlist(
        platform=Platform.SPOTIFY,
        external_id="scored",
        name=playlist_name or "Unknown Playlist",
        url=playlist_url,
        description=None,
        source=PlaylistSource.SPOTIFY_DIRECT,
    )

    console.print(f"[dim]Scoring against Style Profile #{style.id} ({style.name})...[/]")

    try:
        config = ScoringConfig()

        # Apply quick CLI overrides if provided
        if fit_weight is not None:
            config.weight_fit = fit_weight
        if activity_weight is not None:
            config.weight_activity = activity_weight

        scorer = PlaylistScorer(style, config=config)
        breakdown = scorer.score(target)
    except Exception as e:
        console.print(f"[red]Scoring failed:[/] {e}")
        raise typer.Exit(1)

    # Display results
    console.print(Panel(
        f"[bold]Total Value Score:[/] [cyan]{breakdown.total_value_score}/100[/]\n\n"
        f"{breakdown.explanation}",
        title=f"Score for {target.name}",
        border_style="cyan",
    ))

    if show_breakdown:
        table = Table(title="Detailed Breakdown")
        table.add_column("Factor", style="bold")
        table.add_column("Score", justify="right")
        table.add_column("Weight", justify="right")
        table.add_column("Contribution", justify="right")

        cfg = ScoringConfig()
        factors = [
            ("Activity", breakdown.activity_score, cfg.weight_activity),
            ("Fit (Style Match)", breakdown.fit_score, cfg.weight_fit),
            ("Submission Openness", breakdown.openness_score, cfg.weight_openness),
            ("Follower Reach", breakdown.follower_score, cfg.weight_followers),
            ("Contact Quality", breakdown.contact_quality_score, cfg.weight_contact),
            ("Your History", breakdown.personal_history_bonus, cfg.weight_history),
            ("Risk Penalty", -breakdown.risk_penalty, -cfg.risk_penalty_weight),
        ]

        for name, score, weight in factors:
            contrib = round(score * weight * 100, 1)
            table.add_row(
                name,
                f"{score:.2f}",
                f"{weight:.0%}",
                f"{contrib:+.1f}",
            )

        console.print(table)


# =============================================================================
# Phase 1: Discovery / Mining Command
# =============================================================================

@app.command()
def mine(
    band_id: Optional[int] = typer.Option(None, "--band", help="Band to use for style expansion"),
    limit: int = typer.Option(25, "--limit", "-l", help="Maximum number of candidates to evaluate"),
    min_score: Optional[float] = typer.Option(None, "--min-score", help="Only show results above this score"),
    auto_import: bool = typer.Option(False, "--import", help="Automatically import all results above min_score"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview queries and estimated candidates without calling Spotify (Phase 1)"),
    queries_file: Optional[Path] = typer.Option(None, "--queries-file", help="File with one search query per line (overrides LLM expansion for full control)"),
):
    """(Phase 1) Discover new playlist targets using your Style Profile.

    Expands your style into smart search queries, searches Spotify, enriches,
    scores, and presents ranked candidates. Records full MiningRun for history.

    Use --dry-run to preview queries without API calls.
    """
    from dkplaylister.llm import get_provider
    from dkplaylister.scoring import PlaylistScorer, ScoringConfig

    style_repo = StyleProfileRepository()
    style = style_repo.get_latest(band_id=band_id)

    if not style:
        console.print("[red]No Style Profile found for this band. Create one first with `style set`.[/]")
        raise typer.Exit(1)

    console.print(f"[bold]Mining with style:[/] {style.name} (ID {style.id})")

    # 1. Expand + queries (full-featured support)
    from dkplaylister.discovery import expand_style_for_discovery, run_discovery_mining

    expansion = expand_style_for_discovery(style, llm_provider=get_provider("grok"))

    if queries_file:
        if not queries_file.exists():
            console.print(f"[red]Queries file not found: {queries_file}[/]")
            raise typer.Exit(1)
        queries = [line.strip() for line in queries_file.read_text().splitlines() if line.strip()]
        console.print(f"[bold]Using {len(queries)} queries from {queries_file}[/]")
    else:
        queries = expansion.search_queries or [style.raw_prompt[:80]]
        console.print(f"[dim]Using {len(queries)} expanded search queries...[/]")

    if dry_run:
        console.print(Panel.fit(
            "\n".join(f"  • {q}" for q in queries[:10]),
            title="Dry Run — Search Queries (no API calls made)",
            border_style="yellow"
        ))
        console.print(f"[dim]Would search for up to ~{limit} candidates. Re-run without --dry-run to execute.[/]")
        return

    # 2. Use the shared discovery mining engine (full-featured + DRY)
    mining_result = run_discovery_mining(
        style=style,
        queries=queries,
        limit=limit,
        min_score=min_score,
        llm_provider=get_provider("grok"),
    )

    candidates = mining_result["candidates"]
    queries = mining_result["queries_used"]
    query_stats = mining_result["query_stats"]
    expansion = mining_result["expansion"]

    if query_stats:
        console.print(f"[dim]Per-query candidates: {query_stats}[/]")

    if not candidates:
        console.print("[yellow]No candidates found. Try a different style or broader queries.[/]")
        return

    if not candidates:
        console.print("[yellow]No candidates met the minimum score threshold.[/]")
        return

    # candidates from run_discovery_mining are already scored + filtered
    scored = [(pl, getattr(getattr(pl, "current_score", None), "total_value_score", 0)) for pl in candidates]

    # 4. Display results
    table = Table(title=f"Mining Results for {style.name} (showing {len(scored)})")
    table.add_column("Score", justify="right", style="cyan")
    table.add_column("Name")
    table.add_column("Followers", justify="right")
    table.add_column("URL", style="dim")

    for pl, score in scored[:30]:
        table.add_row(
            f"{score:.0f}",
            pl.name[:45] + ("..." if len(pl.name) > 45 else ""),
            f"{pl.follower_count:,}" if pl.follower_count else "—",
            str(pl.url),
        )

    console.print(table)

    # 5. Optional auto-import
    imported = 0
    if auto_import:
        for pl, score in scored:
            try:
                PlaylistRepository().create_or_update(pl)
                imported += 1
            except Exception:
                pass
        console.print(f"\n[green]Auto-imported {imported} playlists.[/]")
    else:
        console.print(f"\n[dim]Use `dkplaylister add <url>` or the UI to import promising targets.[/]")

    # 6. Record MiningRun (Phase 1 hardening - H1)
    try:
        from dkplaylister.storage import MiningRunRepository
        from dkplaylister.models import MiningRun, OperatingMode

        top_score = scored[0][1] if scored else None

        run = MiningRun(
            band_id=band_id or (getattr(style, 'band_id', None)),
            style_profile_id=style.id,
            style_profile_name=style.name,
            operating_mode=OperatingMode.SEMI_AUTOMATIC,
            queries_used=queries,
            min_followers=0,
            expansion_explanation=getattr(expansion, 'explanation', None),
            playlists_found=len(candidates),
            playlists_imported=imported,
            top_score=top_score,
            notes=f"Per-query: {query_stats}" if query_stats else None,
            completed_at=datetime.utcnow(),
        )
        MiningRunRepository().create(run)
        console.print(f"[dim]MiningRun recorded (ID {run.id if hasattr(run, 'id') else 'new'}). Use `dkplaylister mining history` to view.[/]")
    except Exception as e:
        console.print(f"[yellow]Could not record MiningRun: {e}[/]")


# =============================================================================
# Phase 1: Mining History Commands (H1)
# =============================================================================

@app.command("mining")
def mining_app(
    subcommand: str = typer.Argument("history", help="history | show"),
    run_id: Optional[int] = typer.Argument(None, help="Run ID for 'show'"),
    band_id: Optional[int] = typer.Option(None, "--band", help="Filter history by band"),
    limit: int = typer.Option(20, "--limit", "-l"),
):
    """Phase 1 mining session history and details."""
    from dkplaylister.storage import MiningRunRepository

    repo = MiningRunRepository()

    if subcommand == "history":
        if band_id:
            runs = repo.list_by_band(band_id, limit=limit)
            title = f"Mining Runs for Band {band_id}"
        else:
            runs = repo.list_recent(limit=limit)
            title = "Recent Mining Runs"

        if not runs:
            console.print("[yellow]No mining runs recorded yet. Run `dkplaylister mine` first.[/]")
            return

        table = Table(title=title)
        table.add_column("ID", justify="right", style="cyan")
        table.add_column("Band", justify="right")
        table.add_column("Style")
        table.add_column("Found", justify="right")
        table.add_column("Imported", justify="right")
        table.add_column("Top Score", justify="right")
        table.add_column("When")

        for r in runs:
            table.add_row(
                str(r.id),
                str(r.band_id) if r.band_id else "—",
                r.style_profile_name or str(r.style_profile_id),
                str(r.playlists_found),
                str(r.playlists_imported),
                f"{r.top_score:.0f}" if r.top_score else "—",
                r.started_at.strftime("%Y-%m-%d %H:%M"),
            )
        console.print(table)

    elif subcommand == "show" and run_id:
        run = repo.get_by_id(run_id)
        if not run:
            console.print(f"[red]MiningRun {run_id} not found.[/]")
            raise typer.Exit(1)

        console.print(Panel.fit(
            f"[bold]Style:[/] {run.style_profile_name} (ID {run.style_profile_id})\n"
            f"[bold]Band:[/] {run.band_id or '—'}\n"
            f"[bold]Queries Used:[/]\n" + "\n".join(f"  • {q}" for q in run.queries_used[:8]) + "\n"
            f"[bold]Results:[/] {run.playlists_found} found, {run.playlists_imported} imported\n"
            f"[bold]Top Score:[/] {run.top_score}\n"
            f"[bold]Started:[/] {run.started_at}\n"
            f"[bold]Explanation:[/] {run.expansion_explanation or '—'}",
            title=f"MiningRun #{run.id}",
            border_style="cyan"
        ))
    else:
        console.print("[yellow]Usage: dkplaylister mining history [--band X] or dkplaylister mining show <run_id>[/]")


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


# =============================================================================
# Real Pitch Generation Command (first working high-value feature)
# =============================================================================

@app.command()
def pitch(
    song_title: str = typer.Option(None, "--song", "-s", help="Song title (or use --song-id)"),
    song_id: Optional[int] = typer.Option(None, "--song-id", help="Use a saved Song by ID"),
    style_id: Optional[int] = typer.Option(None, "--style-id", help="Use a specific saved Style Profile by ID"),
    style_file: Optional[str] = typer.Option(None, "--style-file", help="Path to a style prompt file (overrides saved profiles)"),
    use_latest: bool = typer.Option(True, "--latest/--no-latest", help="Use the most recently saved Style Profile (default)"),
    band_id: Optional[int] = typer.Option(None, "--band", help="Band context (for future multi-band support)"),
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

    repo = StyleProfileRepository()
    song_repo = SongRepository()

    # Determine which style to use (priority: explicit file > style_id > latest saved > built-in test data)
    if style_file and Path(style_file).exists():
        style_prompt = Path(style_file).read_text().strip()
        style_profile = StyleProfile(raw_prompt=style_prompt, name=Path(style_file).stem)
        console.print(f"[dim]Using style from file: {style_file}[/]")
    elif style_id:
        style_profile = repo.get_by_id(style_id)
        if not style_profile:
            console.print(f"[red]No Style Profile found with ID {style_id}[/]")
            raise typer.Exit(1)
        console.print(f"[dim]Using saved Style Profile #{style_id} ({style_profile.name})[/]")
    elif use_latest:
        style_profile = repo.get_latest(band_id=band_id)
        if style_profile:
            console.print(f"[dim]Using latest saved Style Profile #{style_profile.id} ({style_profile.name})[/]")
        else:
            style_profile = None

    # Fallback to built-in test data
    if not style_profile:
        style_profile = StyleProfile(raw_prompt=TEST_STYLE_PROMPT.strip(), name="Built-in Test Style (Atmospheric Cinematic)")
        console.print("[yellow]No saved Style Profiles found. Using built-in test style.[/]")

    # Handle song
    song_lyrics = TEST_LYRICS
    final_song_title = song_title or TEST_SONG_TITLE

    if song_id:
        song = song_repo.get_by_id(song_id)
        if not song:
            console.print(f"[red]Song ID {song_id} not found.[/]")
            raise typer.Exit(1)
        final_song_title = song.title
        song_lyrics = song.lyrics
        console.print(f"[dim]Using saved Song #{song_id}: {song.title}[/]")

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
            song_title=final_song_title,
            lyrics=song_lyrics,
            playlist=target_playlist,
            pitch_format=format,
        )
    except Exception as e:
        console.print(f"[red]Error generating pitch:[/] {e}")
        raise typer.Exit(1)

    # Display
    console.print("\n" + "=" * 60)
    console.print(Panel(Markdown(generated), title=f"Generated Pitch — {final_song_title}", border_style="green"))
    console.print("=" * 60 + "\n")

    if save:
        out_path = Path(f"pitch_{final_song_title.lower().replace(' ', '_')}.txt")
        out_path.write_text(generated)
        console.print(f"[green]Saved to[/] {out_path}")


if __name__ == "__main__":
    app()
