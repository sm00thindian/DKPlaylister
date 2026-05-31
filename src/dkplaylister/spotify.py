"""Spotify Web API integration for playlist discovery and enrichment.

Aligned with February 2026 Web API changes:
- Avoids all removed "Get Several X" and deprecated endpoints.
- Uses current supported endpoints only (e.g. GET /playlists/{id}).
- Prepared for stricter search limits (max limit=10).
"""

from __future__ import annotations

import os
import re
import time
from typing import Optional
from urllib.parse import urlparse

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

from dkplaylister.models import Curator, Platform, Playlist, PlaylistSource


def get_client() -> spotipy.Spotify:
    """
    Return an authenticated Spotify client (Client Credentials flow for public data).

    Supports both SPOTIFY_* and SPOTIPY_* environment variable names.
    """
    client_id = os.getenv("SPOTIFY_CLIENT_ID") or os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET") or os.getenv("SPOTIPY_CLIENT_SECRET")

    if not client_id or not client_secret:
        # Fall back to spotipy's default behavior (which will raise a clear error)
        return spotipy.Spotify(auth_manager=SpotifyClientCredentials())

    auth_manager = SpotifyClientCredentials(
        client_id=client_id,
        client_secret=client_secret
    )
    return spotipy.Spotify(auth_manager=auth_manager)


def check_spotify_connection() -> dict:
    """
    Lightweight health check for the Spotify client.

    Returns a dict with:
        - ok: bool
        - message: str
        - using_user_auth: bool (whether we're using an authenticated user token)
    """
    try:
        client = get_client()
        # Cheap public call
        _ = _handle_rate_limit(client.search, q="test", type="playlist", limit=1)
        return {
            "ok": True,
            "message": "Spotify connection OK (public data)",
            "using_user_auth": False
        }
    except spotipy.SpotifyException as e:
        if e.http_status in (401, 403):
            return {
                "ok": False,
                "message": f"Spotify authentication problem: {e}",
                "using_user_auth": False
            }
        return {
            "ok": False,
            "message": f"Spotify error: {e}",
            "using_user_auth": False
        }
    except Exception as e:
        return {
            "ok": False,
            "message": f"Unexpected error checking Spotify: {e}",
            "using_user_auth": False
        }


def _handle_rate_limit(func, *args, **kwargs):
    """Simple retry wrapper that respects Spotify's Retry-After header on 429."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except spotipy.SpotifyException as e:
            if e.http_status == 429:
                retry_after = int(e.headers.get("Retry-After", 5))
                print(f"Rate limited by Spotify. Waiting {retry_after}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(retry_after)
            else:
                raise
    raise RuntimeError("Max retries exceeded due to rate limiting")


def get_oauth_client(
    scope: str | list[str] | None = None,
    open_browser: bool = True,
    cache_path: str | None = None,
) -> spotipy.Spotify:
    """
    Return a Spotify client authenticated via Authorization Code Flow.

    This enables user-specific actions (e.g. reading your own profile, email,
    library, following playlists, etc.).

    The first time you call this (or when the token is expired/invalid),
    it will open a browser window for you to log in and authorize the app.

    Args:
        scope: One or more Spotify scopes. Can be a space-separated string
               or a list of strings.
               Example: ["user-read-email", "user-read-private"]
        open_browser: Whether to automatically open the browser for login.
        cache_path: Path to store the OAuth token cache. Defaults to .spotify_cache
                    in the current directory.

    Returns:
        An authenticated spotipy.Spotify client.
    """
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

    if not client_id or not client_secret:
        raise ValueError(
            "SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set in your environment"
        )

    if isinstance(scope, list):
        scope = " ".join(scope)

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        cache_path=cache_path or os.getenv("SPOTIFY_CACHE_PATH", ".spotify_cache"),
        open_browser=open_browser,
    )

    return spotipy.Spotify(auth_manager=auth_manager)


def get_user_client(
    scopes: str | list[str] | None = None,
    open_browser: bool = True,
) -> spotipy.Spotify:
    """
    Convenience wrapper around get_oauth_client.

    Use this when you need an authenticated user context (Authorization Code Flow).
    This is the recommended function for user-authenticated operations.
    """
    return get_oauth_client(scope=scopes, open_browser=open_browser)


def parse_spotify_playlist_id(url_or_id: str) -> Optional[str]:
    """Extract playlist ID from a Spotify URL or return the ID if already clean."""
    if not url_or_id:
        return None

    # If it's already just an ID (22 characters, alphanumeric)
    if re.match(r"^[a-zA-Z0-9]{22}$", url_or_id):
        return url_or_id

    try:
        parsed = urlparse(url_or_id)
        if "spotify.com" in parsed.netloc and "/playlist/" in parsed.path:
            # Handle both /playlist/37i9dQZF1DXcBWIGoYBM5M and with query params
            parts = parsed.path.strip("/").split("/")
            if len(parts) >= 2 and parts[0] == "playlist":
                return parts[1].split("?")[0]
    except Exception:
        pass

    return None


def fetch_playlist(spotify_url_or_id: str) -> Optional[Playlist]:
    """
    Fetch rich data for a single Spotify playlist and return a Playlist model.

    This is the core enrichment function for the semi-automatic mining flow.
    Uses the current supported endpoint (GET /playlists/{id}).
    """
    playlist_id = parse_spotify_playlist_id(spotify_url_or_id)
    if not playlist_id:
        return None

    client = get_client()

    try:
        # Using fields parameter to request only what we need (good practice)
        sp_playlist = _handle_rate_limit(
            client.playlist,
            playlist_id,
            fields="id,name,description,followers.total,owner,external_urls.spotify,tracks.total"
        )
    except spotipy.SpotifyException as e:
        if e.http_status == 403:
            # 403s during discovery (both on playlists and user profiles) are very common
            # and expected. Do not print them.
            return None
        print(f"Spotify API error fetching playlist {playlist_id}: {e}")
        return None
    except Exception as e:
        # Only print unexpected errors
        if "403" not in str(e):
            print(f"Failed to fetch playlist {playlist_id}: {e}")
        return None

    # Build Playlist object
    playlist = Playlist(
        platform=Platform.SPOTIFY,
        external_id=sp_playlist["id"],
        name=sp_playlist.get("name", "Unknown Playlist"),
        url=sp_playlist["external_urls"]["spotify"],
        description=sp_playlist.get("description"),
        follower_count=sp_playlist.get("followers", {}).get("total"),
        track_count=sp_playlist.get("tracks", {}).get("total"),
        source=PlaylistSource.SPOTIFY_DIRECT,
    )

    # Curator + contact extraction (Options 1 + 3)
    curator, revealed_via = _build_curator_from_spotify_data(sp_playlist, playlist.description)
    if curator:
        playlist.curator = curator
    if revealed_via:
        playlist.contact_revealed_via = revealed_via

    return playlist


def enrich_playlist(playlist: Playlist) -> Playlist:
    """
    Enrich an existing Playlist object with fresh Spotify data.
    Useful when we already have a partial record (e.g. from Playlister import).
    """
    if playlist.platform != Platform.SPOTIFY:
        return playlist

    enriched = fetch_playlist(playlist.url or playlist.external_id)
    if enriched:
        # Preserve our internal fields (including any Playlister-specific contact signals)
        enriched.id = playlist.id
        enriched.source = playlist.source or PlaylistSource.SPOTIFY_DIRECT
        enriched.discovery_query = playlist.discovery_query
        enriched.notes = playlist.notes
        # If the original had stronger contact info from Playlister/manual, keep it
        if playlist.curator and not enriched.curator:
            enriched.curator = playlist.curator
        if playlist.contact_revealed_via and not enriched.contact_revealed_via:
            enriched.contact_revealed_via = playlist.contact_revealed_via
        return enriched

    return playlist


def extract_contacts_from_description(description: str) -> dict:
    """Basic contact extraction from playlist descriptions (kept for compatibility)."""
    if not description:
        return {}

    contacts = {}

    # Email
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", description)
    if email_match:
        contacts["email"] = email_match.group(0)

    # Instagram / Twitter / TikTok handles
    ig = re.search(r"(?:@|instagram\.com/)([a-zA-Z0-9_.]+)", description, re.I)
    if ig:
        contacts["instagram"] = ig.group(1)

    return contacts


def _build_curator_from_spotify_data(sp_playlist: dict, description: Optional[str] = None) -> tuple[Optional[Curator], Optional[str]]:
    """
    Best-effort curator construction from Spotify playlist response + description.

    Returns (curator, contact_revealed_via).
    This implements Option 1 (description mining) + Option 3 (Spotify user profile enrichment).
    """
    owner = sp_playlist.get("owner", {}) or {}
    curator = None
    revealed_via = None

    # Start with basic owner info from the playlist object
    name = owner.get("display_name")
    spotify_user_id = owner.get("id")

    if name or spotify_user_id:
        curator = Curator(name=name)

    # Option 1: Mine the description for explicit contact methods
    contacts = {}
    if description:
        contacts = extract_contacts_from_description(description)
        if contacts.get("email"):
            if not curator:
                curator = Curator()
            curator.email = contacts["email"]
            revealed_via = "description"
        if contacts.get("instagram"):
            if not curator:
                curator = Curator()
            curator.instagram = contacts["instagram"]
            if not revealed_via:
                revealed_via = "description"

    # Option 3: Enrich with public Spotify user profile (gives us the Spotify profile URL as a weak "website")
    if spotify_user_id and curator:
        try:
            client = get_client()
            user = _handle_rate_limit(client.user, spotify_user_id)
            if user:
                external = user.get("external_urls", {}) or {}
                profile_url = external.get("spotify")
                if profile_url:
                    curator.website = profile_url
                # Prefer the user-level display_name if better
                if user.get("display_name") and not curator.name:
                    curator.name = user.get("display_name")
        except spotipy.SpotifyException as e:
            # 403 is extremely common for user profiles (private/restricted accounts).
            # Treat as non-fatal and completely silent.
            if e.http_status != 403:
                print(f"Spotify user profile error for {spotify_user_id}: {e}")
        except Exception:
            # Any other unexpected error — also non-fatal
            pass

    # If we only got a name from Spotify owner (no real contact), still return it
    # but don't claim "revealed_via" unless we found something actionable.
    if curator and not revealed_via and curator.name:
        # We have a name but no actionable contact yet
        pass

    return curator, revealed_via
