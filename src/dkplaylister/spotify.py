"""Spotify Web API integration for playlist discovery and enrichment."""

from __future__ import annotations

import os
import re
from typing import Optional
from urllib.parse import urlparse

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth

from dkplaylister.models import Curator, Platform, Playlist, PlaylistSource


def get_client() -> spotipy.Spotify:
    """Return an authenticated Spotify client (Client Credentials flow for public data)."""
    return spotipy.Spotify(auth_manager=SpotifyClientCredentials())


def get_oauth_client(scope: str = None) -> spotipy.Spotify:
    """
    Return a Spotify client using Authorization Code flow (for user-specific actions).

    This is not used yet, but prepared for future features (e.g. accessing user's own data).
    Requires SPOTIFY_REDIRECT_URI to be set.
    """
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

    if not client_id or not client_secret:
        raise ValueError("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set")

    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=scope,
        cache_path=os.getenv("SPOTIFY_CACHE_PATH", ".spotify_cache"),
    )
    return spotipy.Spotify(auth_manager=auth_manager)


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
    """
    playlist_id = parse_spotify_playlist_id(spotify_url_or_id)
    if not playlist_id:
        return None

    client = get_client()

    try:
        sp_playlist = client.playlist(playlist_id, fields="id,name,description,followers.total,owner,external_urls.spotify,tracks.total")
    except Exception as e:
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

    # Owner / basic curator info
    owner = sp_playlist.get("owner", {})
    if owner:
        curator = Curator(
            name=owner.get("display_name"),
        )
        # We can try to get more curator info later
        playlist.curator = curator

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
        # Preserve our internal fields
        enriched.id = playlist.id
        enriched.source = playlist.source or PlaylistSource.SPOTIFY_DIRECT
        enriched.discovery_query = playlist.discovery_query
        enriched.notes = playlist.notes
        return enriched

    return playlist


def extract_contacts_from_description(description: str) -> dict:
    """Basic contact extraction from playlist descriptions."""
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
