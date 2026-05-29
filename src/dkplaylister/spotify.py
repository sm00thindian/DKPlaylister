"""Spotify Web API integration for playlist discovery.

Phase 1 stub. Full implementation will use spotipy with proper rate limiting,
curator extraction via regex on descriptions, and pagination.
"""

from __future__ import annotations

from typing import Any

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from dkplaylister.models import Playlist, SearchQuery


def get_client() -> spotipy.Spotify:
    """Return an authenticated Spotify client (client credentials flow for public data)."""
    # TODO: load from settings / env
    # For public playlist search, Client Credentials is sufficient.
    return spotipy.Spotify(auth_manager=SpotifyClientCredentials())


def search_playlists(query: SearchQuery) -> list[Playlist]:
    """Search Spotify for playlists matching the query.

    This is a stub. Real version will:
    - Combine keywords + genre into Spotify search queries
    - Paginate results (Spotify caps at ~50 per query)
    - Parse descriptions for emails / socials using regex
    - Filter by follower count
    - Store results via storage layer
    """
    client = get_client()

    # Example (will be expanded):
    # results = client.search(q="lofi submissions", type="playlist", limit=20)
    # Then transform to Playlist models...

    return []  # placeholder


def extract_curator_contacts(description: str) -> dict[str, str]:
    """Extract emails, @handles, and URLs from a playlist description.

    Future: use regex + validation.
    """
    # TODO: implement robust extraction
    return {}
