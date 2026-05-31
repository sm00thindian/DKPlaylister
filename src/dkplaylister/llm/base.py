"""Abstract base for LLM providers.

All providers must implement this interface so the rest of the system
can swap between Grok, OpenAI, Anthropic, local models, etc. without changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from dkplaylister.models import Curator, Playlist, StyleProfile, StyleDiscoveryExpansion


class LLMProvider(ABC):
    """Pluggable LLM provider interface."""

    name: str
    model: str

    @abstractmethod
    def generate_pitch(
        self,
        style_profile: StyleProfile,
        song_title: str,
        lyrics: Optional[str],
        playlist: Playlist,
        curator: Optional[Curator] = None,
        pitch_format: str = "email",
        extra_instructions: Optional[str] = None,
        artist_name: Optional[str] = None,
        song_streaming_links: Optional[dict[str, str]] = None,
    ) -> str:
        """Generate a personalized submission pitch.

        The pitch should feel like it's coming from this specific artist to this specific playlist's audience,
        referencing the song's themes/lyrics and the artist's style.

        If `curator` is None, implementations should fall back to `playlist.curator` when present.

        Returns the raw generated text (user can edit afterward).
        """
        raise NotImplementedError

    @abstractmethod
    def score_playlist_fit(
        self,
        style_profile: StyleProfile,
        playlist: Playlist,
    ) -> float:
        """Return a 0.0–1.0 fit score between the artist's style and the playlist."""
        raise NotImplementedError

    def close(self) -> None:
        """Optional cleanup (e.g. closing clients)."""
        pass

    @abstractmethod
    def expand_style_for_discovery(
        self,
        style_profile: StyleProfile,
    ) -> StyleDiscoveryExpansion:
        """
        Expand a StyleProfile into structured discovery signals.

        Used by Phase 1 mining to turn a rich style description into actionable
        search queries, genres, moods, and similar artists for Spotify/Playlister discovery.
        """
        raise NotImplementedError
