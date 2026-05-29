"""Abstract base for LLM providers.

All providers must implement this interface so the rest of the system
can swap between Grok, OpenAI, Anthropic, local models, etc. without changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from dkplaylister.models import Curator, Playlist, StyleProfile


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
    ) -> str:
        """Generate a personalized submission pitch.

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
